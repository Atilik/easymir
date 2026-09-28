"""Tests for rewardio/separate.py.

Default tests exercise the fast paths: input validation and audio loading
(no model). The real Demucs separation runs only with REWARDIO_RUN_SLOW=1 AND
a cached model checkpoint.
"""
import glob
import os
import shutil
import subprocess
import sys

import librosa
import numpy as np
import pytest
import soundfile as sf

from rewardio.separate import separate, _load_audio
from conftest import make_clicks, RUN_SLOW

SLOW = pytest.mark.skipif(
    not (RUN_SLOW and glob.glob(os.path.join(
        os.path.expanduser("~"), ".cache", "torch", "hub", "checkpoints", "*.th"))),
    reason="set REWARDIO_RUN_SLOW=1 (and have htdemucs cached) to run Demucs",
)


@pytest.fixture
def ffmpeg(monkeypatch):
    """Put the env's ffmpeg on PATH (as `conda activate` does) — .m4a
    decoding goes through it. Skips if no ffmpeg is available."""
    env_bin = os.path.dirname(sys.executable)
    if os.path.exists(os.path.join(env_bin, "ffmpeg")):
        monkeypatch.setenv("PATH", env_bin + os.pathsep + os.environ.get("PATH", ""))
    exe = shutil.which("ffmpeg")
    if exe is None:
        pytest.skip("ffmpeg not available")
    return exe


@pytest.fixture
def clicks_48k(tmp_path):
    """3 s stereo click track at 48 kHz (clicks every 0.5 s)."""
    y = make_clicks(np.arange(0.25, 2.75, 0.5), 3.0, sr=48000)
    p = str(tmp_path / "clicks_48k.wav")
    sf.write(p, np.stack([y, y], axis=1), 48000)
    return p


@pytest.fixture
def clicks_m4a(tmp_path, clicks_48k, ffmpeg):
    p = str(tmp_path / "clicks.m4a")
    subprocess.run([ffmpeg, "-loglevel", "error", "-y", "-i", clicks_48k,
                    "-c:a", "aac", p], check=True)
    return p


# ── validation (fast, no model) ─────────────────────────────

def test_separate_rejects_unknown_target(sine_wav):
    # Regression (#1 first-pass): substring matching allowed typos through;
    # validation now happens before any audio/model loading.
    with pytest.raises(ValueError, match="Unknown target source"):
        separate(sine_wav, target_source="drum")


def test_separate_rejects_none_target(sine_wav):
    with pytest.raises(ValueError):
        separate(sine_wav, target_source=None)


def test_separate_rejects_unsupported_extension(tmp_path):
    bad = tmp_path / "audio.txt"
    bad.write_text("nope")
    with pytest.raises(ValueError, match="Unknown target source|Unsupported audio format"):
        separate(str(bad), target_source="drums")


# ── audio loading for the model (fast, no model) ────────────

def test_load_audio_resamples_to_model_rate(clicks_48k):
    # Regression: 48 kHz audio was fed to the 44.1 kHz model unresampled
    wav = _load_audio(clicks_48k, 44100, 2)
    assert wav.dtype.is_floating_point and wav.shape == (2, 3 * 44100)


def test_load_audio_mono_becomes_stereo(sine_wav):
    wav = _load_audio(sine_wav, 44100, 2)
    assert wav.shape[0] == 2
    assert np.array_equal(wav[0].numpy(), wav[1].numpy())


def test_load_audio_m4a(clicks_m4a):
    # Regression: .m4a could not be decoded on the separation path
    wav = _load_audio(clicks_m4a, 44100, 2)
    assert wav.shape[0] == 2
    assert abs(wav.shape[1] - 3 * 44100) < 0.1 * 44100    # AAC adds a little padding


# ── full separation (slow, model required) ──────────────────

@SLOW
def test_separate_drums_end_to_end(click_wav):
    target, accompaniment, sr = separate(click_wav, target_source="drums")
    assert isinstance(target, np.ndarray) and target.ndim == 1
    assert isinstance(accompaniment, np.ndarray) and accompaniment.ndim == 1
    assert len(target) == len(accompaniment)
    assert sr > 0


@SLOW
def test_separate_48k_at_model_rate(clicks_48k):
    target, accompaniment, sr = separate(clicks_48k, target_source="drums")
    assert sr == 44100 and len(target) == 3 * 44100
    # The stems must add back up to the input — proves rate and timing are
    # right, independent of which stem Demucs puts the clicks in
    mix, _ = librosa.load(clicks_48k, sr=44100, mono=True)
    assert np.corrcoef(mix, target + accompaniment)[0, 1] > 0.9


@SLOW
def test_separate_m4a(clicks_m4a):
    target, accompaniment, sr = separate(clicks_m4a, target_source="drums")
    assert sr == 44100 and len(target) == len(accompaniment) > 0


@SLOW
def test_separate_loop_stable_multithreaded(click_wav):
    # Regression: torch used to be pinned to 1 thread over a segfault fear in
    # loops. Re-verified stable multi-threaded — this guards that in CI-like
    # runs. Stems are not bit-reproducible (true at any thread count), but
    # their shape and rough energy must agree.
    import torch
    assert torch.get_num_threads() > 1        # the pin must stay gone
    a, _, _ = separate(click_wav, target_source="drums")
    b, _, _ = separate(click_wav, target_source="drums")
    assert a.shape == b.shape
    assert np.corrcoef(a, b)[0, 1] > 0.99
