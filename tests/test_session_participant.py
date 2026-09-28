"""Tests for Session, Participant, and the mirpsych() entry point."""
import csv
import os
import shutil

import numpy as np
import pytest

from mirpsych.mirpsych import (
    Stimulus, Session, Participant, mirpsych, _folder_has_subdirs,
)


# ── Session: loading ────────────────────────────────────────

def test_session_loads_audio_only_sorted(session_folder):
    sess = Session(session_folder)
    assert len(sess) == 2
    names = [s.audio_file_name for s in sess.items]
    assert names == ["01_alpha.wav", "02_beta.wav"]     # sorted, no notes.txt


def test_session_natural_sort(tmp_path, sine_wav):
    # Upgrade: '10_song' used to sort before '2_song'
    for name in ("10_c.wav", "2_a.wav", "1_b.wav"):
        shutil.copy(sine_wav, tmp_path / name)
    sess = Session(str(tmp_path))
    assert [s.audio_file_name for s in sess.items] == ["1_b.wav", "2_a.wav", "10_c.wav"]


def test_session_loads_aif(tmp_path, sine_wav):
    # Upgrade: .aif (the common spelling) was rejected; only .aiff was listed
    import soundfile as sf
    y, sr = sf.read(sine_wav)
    sf.write(str(tmp_path / "song.aif"), y, sr, format="AIFF")
    sess = Session(str(tmp_path))
    assert [s.audio_file_name for s in sess.items] == ["song.aif"]
    assert sess.items[0].duration == pytest.approx(2.0, abs=1e-2)


def test_session_skips_unreadable_file(session_folder, capsys):
    # Regression (#4): corrupt files are skipped at load with a message
    with open(os.path.join(session_folder, "03_broken.wav"), "w") as f:
        f.write("garbage bytes")
    sess = Session(session_folder)
    out = capsys.readouterr().out
    assert len(sess) == 2
    assert "[Skipped] 03_broken.wav" in out


def test_session_non_directory_raises(sine_wav):
    with pytest.raises(ValueError):
        Session(sine_wav)


def test_session_repr(session_folder):
    assert "count=2" in repr(Session(session_folder))


# ── Session: indexing / selection ───────────────────────────

def test_session_getitem_one_based(session_folder):
    sess = Session(session_folder)
    assert sess[1].audio_file_name == "01_alpha.wav"
    assert sess[2].audio_file_name == "02_beta.wav"


def test_session_getitem_out_of_range_falls_back(session_folder, capsys):
    sess = Session(session_folder)
    item = sess[99]
    assert item.audio_file_name == "01_alpha.wav"
    assert "out of range" in capsys.readouterr().out


def test_session_getitem_string_match(session_folder):
    sess = Session(session_folder)
    assert sess["beta"].audio_file_name == "02_beta.wav"


def test_session_getitem_string_ambiguous(session_folder):
    with pytest.raises(ValueError):
        Session(session_folder)["wav"]                  # matches both


def test_session_getitem_string_missing(session_folder):
    with pytest.raises(KeyError):
        Session(session_folder)["zzz"]


def test_session_getitem_bad_type(session_folder):
    with pytest.raises(TypeError):
        Session(session_folder)[1.5]


def test_empty_session_selection_raises(tmp_path):
    # Regression: used to IndexError through the fallback path
    sess = Session(str(tmp_path))
    assert len(sess) == 0
    with pytest.raises(ValueError):
        sess[1]
    with pytest.raises(ValueError):
        sess(1)


def test_session_call_updates_shell_ns(session_folder, capsys):
    sess = Session(session_folder)
    ns = {}
    sess._shell_ns = ns
    sess(2)
    assert ns["stimulus"].audio_file_name == "02_beta.wav"


def test_session_call_no_ns_is_safe(session_folder, capsys):
    Session(session_folder)(1)                          # just prints


# ── Session: save ───────────────────────────────────────────

def test_session_save_writes_all_rows(session_folder, tmp_path):
    sess = Session(session_folder)
    sess.save(output_path=str(tmp_path))
    analysis = [d for d in os.listdir(tmp_path) if d.startswith("Analysis_")][0]
    csv_file = os.listdir(tmp_path / analysis)[0]
    with open(tmp_path / analysis / csv_file) as f:
        rows = list(csv.DictReader(f))
    assert [r["filename"] for r in rows] == ["01_alpha.wav", "02_beta.wav"]


# ── Session: batch processing (injected — no ML) ────────────

def test_process_all_items_computes_both_scores(session_folder, inject_rhythm):
    # Regression (#3): batch path must produce the meter-aware score too
    sess = Session(session_folder)
    for s in sess.items:
        inject_rhythm(s, dur=2.0)
    sess._process_all_items(do_separate=True)
    for s in sess.items:
        assert s.toussaint_syncopation_score is not None
        assert s.toussaint_syncopation_score_meter is not None


# ── process_and_save argument order ─────────────────────────
# Regression: README documents process_and_save("output_folder"), but the
# first positional parameter used to be `index`, so the path was looked up
# as a song/session name (KeyError).

@pytest.fixture
def no_classify(monkeypatch):
    """Skip Essentia/CREPE so process_and_save runs without ML models."""
    monkeypatch.setattr(Stimulus, "classify", lambda self: None)


def test_session_process_and_save_positional_path(session_folder, tmp_path,
                                                   inject_rhythm, no_classify):
    sess = Session(session_folder)
    for s in sess.items:
        inject_rhythm(s, dur=2.0)               # no BEAT THIS! / Demucs
    sess.process_and_save(str(tmp_path))
    _, rows = _read_saved_csv(str(tmp_path))
    assert [r["filename"] for r in rows] == ["01_alpha.wav", "02_beta.wav"]


def test_session_process_and_save_legacy_index_order(session_folder, tmp_path,
                                                     inject_rhythm, no_classify):
    # Old calls like process_and_save(2, "out") keep working
    sess = Session(session_folder)
    for s in sess.items:
        inject_rhythm(s, dur=2.0)
    sess.process_and_save(2, str(tmp_path))
    _, rows = _read_saved_csv(str(tmp_path))
    assert [r["filename"] for r in rows] == ["02_beta.wav"]


def test_participant_process_and_save_positional_path(participant_folder, tmp_path,
                                                       inject_rhythm, no_classify):
    p = Participant(participant_folder)
    for sess in p.sessions:
        for s in sess.items:
            inject_rhythm(s, dur=2.0)
    path = p.process_and_save(str(tmp_path))
    assert path is not None and path.startswith(str(tmp_path))
    _, rows = _read_saved_csv(str(tmp_path))
    rows = [r for r in rows if r.get("session")]  # drop blank separator row
    assert [r["session"] for r in rows] == ["sess_a", "sess_b"]


# ── timeseries export ───────────────────────────────────────

def test_session_save_timeseries(session_folder, tmp_path):
    # Regression: listed in session.help() but did not exist
    sess = Session(session_folder)
    for s in sess.items:
        s._compute_spectral_if_needed()
    sess.save_timeseries(output_path=str(tmp_path))
    analysis = [d for d in os.listdir(tmp_path) if d.startswith("Analysis_")][0]
    assert sorted(os.listdir(tmp_path / analysis)) == [
        "01_alpha_timeseries.npz", "02_beta_timeseries.npz"]


def test_participant_timeseries_keeps_same_song_from_each_session(tmp_path, sine_wav):
    # Regression: the same song in two sessions was exported to ONE .npz
    root = tmp_path / "participant"
    for sess in ("week1", "week2"):
        (root / sess).mkdir(parents=True)
        shutil.copy(sine_wav, root / sess / "song.wav")
    out = tmp_path / "out"
    Participant(str(root)).partial_process_save(output_path=str(out), spectral=True,
                                                timeseries=True)
    analysis = [d for d in os.listdir(out) if d.startswith("Analysis_")][0]
    npz = sorted(f for f in os.listdir(out / analysis) if f.endswith(".npz"))
    assert npz == ["week1_song_timeseries.npz", "week2_song_timeseries.npz"]


# ── hidden / system folders ─────────────────────────────────

@pytest.mark.parametrize("junk", [".ipynb_checkpoints", "__MACOSX"])
def test_hidden_subfolder_does_not_make_participant(tmp_path, sine_wav, junk):
    # Regression: a session folder containing e.g. .ipynb_checkpoints/ was
    # loaded as a participant, and its songs were ignored
    shutil.copy(sine_wav, tmp_path / "song.wav")
    (tmp_path / junk).mkdir()
    obj = mirpsych(str(tmp_path))
    assert isinstance(obj, Session) and len(obj) == 1


def test_participant_ignores_hidden_folders(participant_folder):
    os.makedirs(os.path.join(participant_folder, ".ipynb_checkpoints"))
    os.makedirs(os.path.join(participant_folder, "__MACOSX"))
    p = Participant(participant_folder)
    assert [os.path.basename(s.folder_path) for s in p.sessions] == ["sess_a", "sess_b"]


def test_session_ignores_macos_resource_files(session_folder, capsys):
    # '._song.wav' AppleDouble files (external drives, zips) are skipped silently
    with open(os.path.join(session_folder, "._01_alpha.wav"), "wb") as f:
        f.write(b"\x00\x05\x16\x07 not audio")
    sess = Session(session_folder)
    assert len(sess) == 2
    assert "[Skipped]" not in capsys.readouterr().out


# ── Session / Participant averages ──────────────────────────

def test_session_average_fluctuation_and_irregularity(session_folder):
    sess = Session(session_folder)
    avg_f = sess.average_fluctuation
    avg_i = sess.average_irregularity
    assert avg_f == pytest.approx(np.mean([s.fluctuation for s in sess.items]))
    assert avg_i == pytest.approx(np.mean([s.irregularity for s in sess.items]))
    # First access cached the per-song values
    assert all(s._fluctuation is not None for s in sess.items)
    assert all(s._irregularity is not None for s in sess.items)


def test_empty_session_averages_are_nan(tmp_path):
    sess = Session(str(tmp_path))
    assert np.isnan(sess.average_fluctuation)
    assert np.isnan(sess.average_irregularity)


def test_participant_averages(participant_folder):
    p = Participant(participant_folder)
    songs = [s for sess in p.sessions for s in sess.items]
    assert p.average_fluctuation == pytest.approx(
        np.mean([s.fluctuation for s in songs]))
    assert p.average_irregularity == pytest.approx(
        np.mean([s.irregularity for s in songs]))


def test_empty_participant_averages_are_nan(tmp_path):
    p = Participant(str(tmp_path))
    assert np.isnan(p.average_fluctuation)
    assert np.isnan(p.average_irregularity)


# ── partial_process_save (Session / Participant) ────────────

def _read_saved_csv(out_dir):
    analysis = [d for d in os.listdir(out_dir) if d.startswith("Analysis_")][0]
    csv_file = os.listdir(os.path.join(out_dir, analysis))[0]
    with open(os.path.join(out_dir, analysis, csv_file)) as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def test_session_partial_process_save_rhythm(session_folder, tmp_path, inject_rhythm):
    # rhythm = beats/BPM only (fast path — no syncopation columns)
    sess = Session(session_folder)
    for s in sess.items:
        inject_rhythm(s, dur=2.0)               # no BEAT THIS! needed
    sess.partial_process_save(output_path=str(tmp_path), rhythm=True)
    header, rows = _read_saved_csv(str(tmp_path))
    assert "bpm" in header
    assert "syncopation_score" not in header
    assert "genre" not in header                # unselected group not computed


def test_session_partial_process_save_syncopation(session_folder, tmp_path, inject_rhythm):
    sess = Session(session_folder)
    for s in sess.items:
        inject_rhythm(s, dur=2.0)               # drums injected -> no Demucs
    sess.partial_process_save(output_path=str(tmp_path), syncopation=True)
    header, rows = _read_saved_csv(str(tmp_path))
    assert "syncopation_score" in header and "syncopation_score_meter" in header
    assert all(r["syncopation_score"] != "" for r in rows)
    assert "genre" not in header


def test_participant_partial_process_save_spectral(participant_folder, tmp_path):
    p = Participant(participant_folder)
    path = p.partial_process_save(output_path=str(tmp_path), spectral=True)
    assert path is not None
    header, rows = _read_saved_csv(str(tmp_path))
    assert "spectral_centroid_mean" in header and "session" in header
    assert "bpm" not in header and "genre" not in header


def test_session_partial_no_groups_hint(session_folder, tmp_path, capsys):
    sess = Session(session_folder)
    sess.partial_process_save(output_path=str(tmp_path))
    assert "No feature group selected" in capsys.readouterr().out
    header, rows = _read_saved_csv(str(tmp_path))
    assert "loudness_lufs" in header            # basics still saved
    assert len(rows) == 2


# ── Participant ─────────────────────────────────────────────

def test_participant_loads_sessions(participant_folder):
    p = Participant(participant_folder)
    assert p.n_sessions == 2 and len(p) == 2


def test_participant_non_directory_raises(sine_wav):
    with pytest.raises(ValueError):
        Participant(sine_wav)


def test_participant_getitem_and_string(participant_folder):
    p = Participant(participant_folder)
    assert os.path.basename(p[1].folder_path) == "sess_a"
    assert os.path.basename(p["b"].folder_path) == "sess_b"
    with pytest.raises(KeyError):
        p["zzz"]


def test_empty_participant_selection_raises(tmp_path):
    p = Participant(str(tmp_path))
    with pytest.raises(ValueError):
        p[1]


def test_participant_call_updates_ns(participant_folder):
    p = Participant(participant_folder)
    ns = {}
    p._shell_ns = ns
    p(2)
    assert os.path.basename(ns["session"].folder_path) == "sess_b"
    assert ns["stimulus"].audio_file_name == "sess_b_song.wav"


def test_participant_save_adds_session_column(participant_folder, tmp_path):
    p = Participant(participant_folder)
    path = p.save(output_path=str(tmp_path))
    assert path is not None                             # regression: propagated return
    with open(path) as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames[0] == "session"        # upgrade: first column
        rows = list(reader)
    assert rows[0]["session"] == "sess_a"
    assert all(v in ("", None) for v in rows[1].values())   # blank separator row
    assert rows[2]["session"] == "sess_b"


def test_participant_repr(participant_folder):
    assert "sessions=2" in repr(Participant(participant_folder))


# ── mirpsych() entry point ──────────────────────────────────

def test_mirpsych_file_returns_stimulus(sine_wav):
    assert isinstance(mirpsych(sine_wav), Stimulus)


def test_mirpsych_bad_extension_raises(tmp_path):
    bad = tmp_path / "doc.txt"
    bad.write_text("hi")
    with pytest.raises(ValueError):
        mirpsych(str(bad))


def test_mirpsych_flat_folder_returns_session(session_folder):
    assert isinstance(mirpsych(session_folder), Session)


def test_mirpsych_nested_folder_returns_participant(participant_folder):
    assert isinstance(mirpsych(participant_folder), Participant)


def test_mirpsych_missing_path_raises():
    with pytest.raises(FileNotFoundError):
        mirpsych("/no/such/path")


def test_mirpsych_mixed_folder_warns(participant_folder, sine_wav, capsys):
    # Regression (#7): loose top-level audio must be called out
    shutil.copy(sine_wav, os.path.join(participant_folder, "loose.wav"))
    obj = mirpsych(participant_folder)
    out = capsys.readouterr().out
    assert isinstance(obj, Participant)
    assert "Ignoring 1 audio file(s)" in out


def test_folder_has_subdirs(tmp_path):
    assert not _folder_has_subdirs(str(tmp_path))
    (tmp_path / "sub").mkdir()
    assert _folder_has_subdirs(str(tmp_path))
