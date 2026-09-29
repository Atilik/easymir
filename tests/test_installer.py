"""Guards for the double-click installer assets (install.command,
run_easymir.command, INSTALLATION.md). All offline and fast.

The GitHub Download-ZIP is simulated with `git archive` — if the exec bits are
missing INSIDE the archive, a downloaded installer won't be double-clickable.
"""
import os
import subprocess
import zipfile

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMMANDS = ["install.command", "run_easymir.command"]


@pytest.mark.parametrize("name", COMMANDS)
def test_command_scripts_are_valid_zsh(name):
    r = subprocess.run(["zsh", "-n", os.path.join(REPO, name)],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize("name", COMMANDS)
def test_command_scripts_executable_in_zip(name, tmp_path):
    # `git archive` uses the committed/staged file modes — same as GitHub's ZIP.
    # Uncommitted new files aren't in HEAD yet, so archive the working tree
    # copy explicitly via a temporary index? Simpler: check the filesystem bit
    # AND, when the file is in HEAD, the archived mode.
    assert os.access(os.path.join(REPO, name), os.X_OK), \
        f"{name} lost its executable bit on disk (chmod +x it)"

    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", name],
                             cwd=REPO, capture_output=True, timeout=60)
    if tracked.returncode != 0:
        pytest.skip(f"{name} not committed yet — archive check applies after commit")

    zpath = tmp_path / "archive.zip"
    subprocess.run(["git", "archive", "--format=zip", "-o", str(zpath), "HEAD"],
                   cwd=REPO, check=True, timeout=120)
    with zipfile.ZipFile(zpath) as z:
        info = z.getinfo(name)
        mode = (info.external_attr >> 16) & 0o777
    assert mode & 0o111, \
        f"{name} is not executable inside the ZIP (mode {oct(mode)}) — " \
        f"run: git update-index --chmod=+x {name}"


def _read(name):
    with open(os.path.join(REPO, name), encoding="utf-8") as f:
        return f.read()


def test_installer_has_required_safeguards():
    s = _read("install.command")
    # diagnostics header for emailable logs
    for needle in ("sw_vers", "uname", "df -g", "install_log.txt"):
        assert needle in s, f"missing diagnostics piece: {needle}"
    # no hidden interactive conda prompts, incl. the 2025 ToS gate
    assert "CONDA_ALWAYS_YES" in s
    assert "CONDA_PLUGINS_AUTO_ACCEPT_TOS" in s
    # conda must be invoked as the discovered base's BINARY (caffeinate can't
    # run shell functions and would fall back to whatever PATH offers)
    assert '"$CONDA_BIN" env create' in s
    assert "caffeinate -i conda " not in s
    # every exit funnels through the pause so the last message stays visible
    assert "pause_and_exit" in s and "Press Return to close" in s
    # never uses the fragile patterns the red-team flagged
    assert "set -e" not in s and "exec > >(" not in s
    # long steps keep the laptop awake
    assert "caffeinate" in s


def test_runner_has_required_safeguards():
    s = _read("run_easymir.command")
    assert "envs/easymir/bin/python" in s.replace('"$ENV_NAME"', "easymir") \
        or "$ENV_NAME/bin/python" in s          # env resolved directly
    assert "install.command" in s               # points novices to the installer
    assert "Press Return to close" in s
    assert "caffeinate" in s


def test_env_yml_is_compile_free_and_git_free():
    # Regression: madmom compiled on user machines (failed on a fresh macOS 26:
    # SDK/linker mismatch), and git-URL deps need git, which fresh Macs lack.
    # Both now ship as bundled wheels.
    yml = _read("environment.yml")
    assert "git+" not in yml, "a git dependency crept back into environment.yml"
    for wheel in ("wheels/madmom-0.17.dev0-cp311-cp311-macosx_11_0_arm64.whl",
                  "wheels/beat_this-1.1.0-py3-none-any.whl"):
        assert f"./{wheel}" in yml, f"environment.yml no longer installs {wheel}"
        assert os.path.isfile(os.path.join(REPO, wheel)), f"{wheel} missing from repo"


def test_installer_has_no_compiler_steps():
    s = _read("install.command")
    for forbidden in ("xcode-select", "pkgutil", "xcrun"):
        assert forbidden not in s, \
            f"install.command references {forbidden} — the compiler-free design regressed"


def test_installation_md_mentions_the_moving_parts():
    s = _read("INSTALLATION.md")
    for needle in ("install.command", "run_easymir.command", "install_log.txt",
                   "Open Anyway", "Move to Trash", "easymir-main",
                   "Apple Silicon", "macOS 15"):
        assert needle in s, f"INSTALLATION.md no longer mentions: {needle}"


def test_readme_links_installation_md():
    assert "INSTALLATION.md" in _read("README.md")
