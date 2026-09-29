"""Tests for easymir/play.py and easymir/plot.py.

The GUI windows (Tk + audio device) cannot be driven headlessly — those are
manual-test territory. Here we cover the pure helpers and the public API
surface so refactors that break imports/signatures fail fast.
"""
import inspect

import pytest


# ── pure helpers ────────────────────────────────────────────

def test_format_time():
    from easymir.play import _format_time
    assert _format_time(0) == "0:00"
    assert _format_time(5) == "0:05"
    assert _format_time(65) == "1:05"
    assert _format_time(59.9) == "0:59"      # truncates, not rounds
    assert _format_time(600) == "10:00"
    assert _format_time(3599) == "59:59"


# ── figure construction (headless — window display is mocked) ──

@pytest.fixture
def captured_figure(monkeypatch):
    """Capture the Figure passed to _show_figure instead of opening a window."""
    shown = []
    monkeypatch.setattr("easymir.plot._show_figure",
                        lambda fig, title="": shown.append(fig))
    return shown


def test_plot_waveform_builds_figure(sine_wav, captured_figure):
    from easymir.easymir import Stimulus
    from easymir.plot import plot_waveform
    plot_waveform(Stimulus(sine_wav))
    assert len(captured_figure) == 1
    ax = captured_figure[0].axes[0]
    assert "sine_440.wav" in ax.get_title()
    assert ax.get_xlabel() == "Time (s)"


def test_session_boxplot_builds_panels(session_folder, captured_figure):
    from easymir.easymir import Session
    from easymir.plot import plot_session_boxplots
    sess = Session(session_folder)
    for i, s in enumerate(sess.items):        # inject so no models/prompts run
        s._bpm = 118.0 + i
        s.toussaint_syncopation_score = 20 + i
    plot_session_boxplots(sess)
    assert len(captured_figure) == 1
    titles = [ax.get_title() for ax in captured_figure[0].axes]
    assert titles == ["LUFS", "BPM", "Syncopation"]


def test_figures_are_not_pyplot_managed(sine_wav, captured_figure):
    # Regression (#18): figures must not register with pyplot's figure
    # manager — that coupling was why the backend had to be forced to Agg
    import matplotlib.pyplot as plt
    from easymir.easymir import Stimulus
    from easymir.plot import plot_waveform
    before = plt.get_fignums()
    plot_waveform(Stimulus(sine_wav))
    assert plt.get_fignums() == before        # nothing leaked into pyplot


# ── API surface (regression against accidental renames) ─────

def test_play_module_api():
    import easymir.play as play
    for name in ("play_audio", "play_interactive",
                 "sonify_beats", "sonify_beats_and_onsets"):
        assert callable(getattr(play, name)), f"play.{name} missing"


def test_plot_module_api():
    import easymir.plot as plot
    for name in ("plot_beats", "plot_waveform", "plot_beats_and_onsets",
                 "plot_interactive", "plot_session_boxplots",
                 "plot_spectrogram", "plot_pitch"):
        assert callable(getattr(plot, name)), f"plot.{name} missing"


def test_play_interactive_signature():
    from easymir.play import play_interactive
    params = inspect.signature(play_interactive).parameters
    assert list(params) == ["stimulus", "xlim", "ylim"]


def test_plot_spectrogram_scales_documented():
    from easymir.plot import plot_spectrogram
    params = inspect.signature(plot_spectrogram).parameters
    assert params["scale"].default == "mel"


def test_stimulus_gui_methods_exist(sine_wav):
    from easymir.easymir import Stimulus
    s = Stimulus(sine_wav)
    for name in ("play", "plot", "plot_beats", "plot_waveform", "plot_onsets",
                 "sonify_beats", "sonify_onsets"):
        assert callable(getattr(s, name))
