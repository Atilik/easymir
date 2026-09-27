"""Tests for the package entry points: imports, `python -m rewardio`, and the shell."""
import os
import shutil
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ── package imports ─────────────────────────────────────────

def test_package_exports():
    # Regression: DOCUMENTATION's `from rewardio import ...` used to fail
    # (no __init__.py)
    from rewardio import Stimulus, Session, Participant
    import rewardio.rewardio as core
    assert Stimulus is core.Stimulus
    assert Session is core.Session
    assert Participant is core.Participant


def test_package_unknown_attribute_raises():
    import rewardio
    with pytest.raises(AttributeError):
        rewardio.NotAThing


def test_submodule_import_is_lightweight():
    # Lazy exports: importing a light submodule must not drag in the ML stack
    code = ("import sys, rewardio, rewardio.dsp; "
            "print('torch' in sys.modules, 'essentia' in sys.modules)")
    r = subprocess.run([sys.executable, "-c", code], cwd=REPO,
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr[-2000:]
    assert r.stdout.strip().endswith("False False")


# ── main() ──────────────────────────────────────────────────

@pytest.fixture
def run_main(monkeypatch):
    """Run rewardio's CLI main() with the terminal clear and the interactive
    console replaced by recorders. Returns (exit_code, namespace, events)."""
    import rewardio.rewardio as core
    captured = {}
    events = []

    def fake_clear():
        events.append("clear")
        print("<<CLEAR>>")

    def fake_interact(banner=None, local=None, **kw):
        events.append("interact")
        captured["ns"] = local

    monkeypatch.setattr(core, "clear", fake_clear)
    monkeypatch.setattr("code.interact", fake_interact)

    def _run(args):
        rc = core.main(args)
        return rc, captured.get("ns"), events
    return _run


def test_main_without_args_prints_usage(run_main, capsys):
    rc, ns, events = run_main([])
    assert rc == 1
    assert "Usage: python -m rewardio" in capsys.readouterr().out
    assert events == []                        # nothing loaded, no shell


def test_main_clears_before_loading(participant_folder, sine_wav, run_main, capsys):
    # Regression: clear() used to run AFTER loading and wiped the warnings
    shutil.copy(sine_wav, os.path.join(participant_folder, "loose.wav"))
    rc, ns, events = run_main([participant_folder])
    out = capsys.readouterr().out
    assert rc == 0 and events == ["clear", "interact"]
    assert out.index("<<CLEAR>>") < out.index("Ignoring 1 audio file(s)")


def test_main_participant_namespace(participant_folder, run_main, capsys):
    from rewardio.rewardio import Participant, Session, Stimulus
    rc, ns, _ = run_main([participant_folder])
    assert isinstance(ns["participant"], Participant)
    assert isinstance(ns["session"], Session)
    assert isinstance(ns["stimulus"], Stimulus)


def test_main_session_namespace(session_folder, run_main, capsys):
    from rewardio.rewardio import Session
    rc, ns, _ = run_main([session_folder])
    assert isinstance(ns["session"], Session)
    assert ns["stimulus"].audio_file_name == "01_alpha.wav"
    assert "participant" not in ns


def test_main_single_file_namespace(sine_wav, run_main, capsys):
    # Regression: `session` used to be bound to the song itself, and the
    # banner advertised session(1), which raised TypeError
    rc, ns, _ = run_main([sine_wav])
    out = capsys.readouterr().out
    assert ns["stimulus"].audio_file_name == "sine_440.wav"
    assert "session" not in ns
    assert "session(1)" not in out and "stimulus.help()" in out


# ── `python -m rewardio` (the README's run command) ─────────

def test_python_dash_m_rewardio(sine_wav):
    # Regression: README's old `python rewardio.py` failed with ImportError.
    # stdin is empty, so the shell starts and exits immediately.
    r = subprocess.run([sys.executable, "-W", "ignore", "-m", "rewardio", sine_wav],
                       cwd=REPO, stdin=subprocess.DEVNULL,
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr[-2000:]
    assert 'Stimulus("sine_440.wav")' in r.stdout
