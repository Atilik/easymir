"""Environment health: the package must import and work regardless of import
order, and without optional system libraries it doesn't strictly need."""
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run(code, **env):
    # Start from a clean OpenMP state: scikit-learn/threadpoolctl (imported
    # earlier in this pytest process) set KMP_DUPLICATE_LIB_OK, which would
    # hide the crash a fresh user process gets
    base = {k: v for k, v in os.environ.items() if k != "KMP_DUPLICATE_LIB_OK"}
    return subprocess.run([sys.executable, "-W", "ignore", "-c", code], cwd=REPO,
                          env={**base, **env},
                          capture_output=True, text=True, timeout=300)


def test_importing_torch_first_does_not_crash():
    # Regression: conda-forge numpy + pip torch loaded two OpenMP runtimes, and
    # importing torch before numpy aborted the process (OMP Error #15).
    # Fails in environments built before the fix — rebuild from environment.yml.
    r = _run("import torch; import numpy; import rewardio.rewardio; print('ok')")
    assert r.returncode == 0, f"exit {r.returncode}: {r.stderr[-1500:]}"
    assert "ok" in r.stdout


def test_analysis_works_without_portaudio(tmp_path):
    # Linux machines without the PortAudio system library can't import
    # sounddevice — that must only disable playback, not the whole package
    (tmp_path / "sounddevice.py").write_text(
        "raise OSError('PortAudio library not found')\n")
    code = ("import rewardio.rewardio, rewardio.play as p\n"
            "try:\n"
            "    p._sounddevice()\n"
            "except RuntimeError as e:\n"
            "    print('playback:', e)\n")
    r = _run(code, PYTHONPATH=str(tmp_path))
    assert r.returncode == 0, r.stderr[-1500:]
    assert "libportaudio2" in r.stdout
