#!/bin/zsh
# ─────────────────────────────────────────────────────────────────────────────
#  mireasy installer — double-click me in Finder.
#
#  Installs everything mireasy needs on an Apple Silicon Mac (macOS 15+),
#  checks its own work, and writes everything it does to install_log.txt
#  (same folder). Safe to run again at any time.
#
#  Stuck? Email install_log.txt to the mireasy author.
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR" 2>/dev/null
LOG="$SCRIPT_DIR/install_log.txt"
MARKER="$SCRIPT_DIR/.mireasy_installed"
LOCK="$SCRIPT_DIR/.mireasy_install.lock"
ENV_NAME="mireasy"
MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.pkg"
export CONDA_ALWAYS_YES="true"      # no hidden y/n prompt may stall the install
# conda >= 25.7 refuses non-interactive runs until Anaconda's channel Terms of
# Service are accepted — even when (like mireasy) every package comes from the
# community conda-forge channel instead. This is Anaconda's own variable for
# automated installs; the installer discloses it on screen before installing.
export CONDA_PLUGINS_AUTO_ACCEPT_TOS="yes"

# ── tiny UI helpers ─────────────────────────────────────────────────────────
say()  { print -- "$@" }
ok()   { print -- "  ✓ $@" }
bad()  { print -- "  ✗ $@" }
rule() { print -- "──────────────────────────────────────────────────────────" }

pause_and_exit() {
    # Every exit path ends here so the last message never vanishes with the
    # window (some Terminal profiles auto-close on clean exit).
    local code=$1
    print
    if [[ -t 0 ]]; then
        read -r "?Press Return to close this window. "
    fi
    exit $code
}

# ── the whole install, logged via tee at the bottom ─────────────────────────
main() {
    rule
    say "mireasy installer"
    rule

    # Diagnostics header — makes a single emailed log diagnosable
    say "Log started : $(date)"
    say "macOS       : $(sw_vers -productVersion) ($(sw_vers -buildVersion))"
    say "Hardware    : $(uname -m) / arm64-capable: $(sysctl -n hw.optional.arm64 2>/dev/null || echo '?')"
    say "Rosetta     : $(sysctl -n sysctl.proc_translated 2>/dev/null || echo 0)"
    say "Free disk   : $(df -g / | awk 'NR==2 {print $4}') GB"
    say "Folder      : $SCRIPT_DIR"
    rule

    # ── concurrency lock (double double-click protection) ──
    if ! mkdir "$LOCK" 2>/dev/null; then
        bad "Another copy of this installer seems to be running already."
        say "  If you are sure it is not, delete the folder"
        say "  $LOCK  and double-click me again."
        return 1
    fi
    trap 'rmdir "$LOCK" 2>/dev/null' EXIT INT TERM

    # ── batched cheap pre-flight checks: report everything at once ──
    local problems=0

    # 1. Apple Silicon (Rosetta-aware)
    if [[ "$(sysctl -n hw.optional.arm64 2>/dev/null)" != "1" ]]; then
        bad "This Mac has an Intel processor. mireasy needs an Apple Silicon"
        say "    Mac (M1 or newer, 2021+). Sorry — this machine can't run it."
        problems=1
    elif [[ "$(sysctl -n sysctl.proc_translated 2>/dev/null)" == "1" ]]; then
        bad "Terminal is running in Rosetta (Intel-compatibility) mode."
        say "    Fix: Finder → Applications → Utilities → right-click Terminal →"
        say "    Get Info → UN-check 'Open using Rosetta', reopen, run me again."
        problems=1
    else
        ok "Apple Silicon Mac"
    fi

    # 2. macOS version (numeric, so 15.10 and 26.x compare correctly)
    local macver=$(sw_vers -productVersion)
    local macmajor=${macver%%.*}
    if (( macmajor < 15 )); then
        bad "macOS $macver is too old — mireasy needs macOS 15 (Sequoia) or newer."
        say "     → Apple menu → System Settings → General → Software Update"
        problems=1
    else
        ok "macOS $macver"
    fi

    # 3. Disk space — nothing compiles and no developer tools are needed:
    #    every hard-to-build component ships as a prebuilt wheel in wheels/
    local need_gb=6
    local free_gb=$(df -g / | awk 'NR==2 {print $4}')
    if (( free_gb < need_gb )); then
        bad "Only ${free_gb} GB free — mireasy needs about ${need_gb} GB."
        say "    Free some space (empty the Trash, delete old downloads), run me again."
        problems=1
    else
        ok "${free_gb} GB free disk space"
    fi

    # 4. This script must sit inside the mireasy folder, and it must be readable
    if [[ ! -e "$SCRIPT_DIR/environment.yml" ]]; then
        if ! ls "$SCRIPT_DIR" >/dev/null 2>&1; then
            bad "macOS is blocking Terminal from reading this folder."
            say "    Fix: System Settings → Privacy & Security → Files & Folders →"
            say "    Terminal → allow the folder, then run me again."
        else
            bad "I can't find environment.yml next to me."
            say "    Please keep install.command INSIDE the mireasy folder you"
            say "    unzipped (don't move it to the Desktop), then run it from there."
        fi
        problems=1
    else
        ok "mireasy folder looks complete"
    fi

    # 6. Internet — the actual hosts we need (campus proxies surface here)
    local host bad_hosts=""
    for host in repo.anaconda.com conda.anaconda.org pypi.org essentia.upf.edu; do
        curl -sI --max-time 10 "https://$host" >/dev/null 2>&1 || bad_hosts="$bad_hosts $host"
    done
    if [[ -n "$bad_hosts" ]]; then
        bad "Can't reach:$bad_hosts"
        say "    Check your Wi-Fi. On university networks, a login portal or"
        say "    firewall may be blocking these — try a different network."
        problems=1
    else
        ok "Internet connection"
    fi

    if (( problems )); then
        rule
        bad "Please fix the point(s) above, then double-click me again."
        return 1
    fi

    # (No Xcode / Command Line Tools step: nothing compiles and nothing needs
    #  git — the two non-PyPI dependencies ship as prebuilt wheels in wheels/.)

    # ── find conda (never trusts PATH — also survives 'reopen Terminal' misses) ──
    rule
    local base="" cand
    local candidates=(
        "$HOME/miniconda3" "$HOME/anaconda3" "$HOME/opt/miniconda3" "$HOME/opt/anaconda3"
        /opt/miniconda3 /opt/anaconda3 /opt/homebrew/Caskroom/miniconda/base /opt/homebrew/anaconda3
    )
    # Prefer a base that already contains our env (repairs/two-conda machines)
    for cand in $candidates; do
        [[ -x "$cand/envs/$ENV_NAME/bin/python" && -f "$cand/etc/profile.d/conda.sh" ]] && { base="$cand"; break }
    done
    if [[ -z "$base" ]]; then
        for cand in $candidates; do
            [[ -f "$cand/etc/profile.d/conda.sh" ]] && { base="$cand"; break }
        done
    fi

    if [[ -z "$base" ]]; then
        say "One more program is needed first: Miniconda (a free scientific"
        say "Python). Please:"
        say "  1. Open this link:  $MINICONDA_URL"
        say "  2. Double-click the downloaded file, click through with defaults."
        say "  3. Then double-click me (install.command) again."
        return 0
    fi
    if [[ "$(file -b "$base/bin/python" 2>/dev/null)" != *arm64* ]]; then
        bad "The Miniconda at $base is the Intel version — it can't install mireasy."
        say "    Please install the Apple Silicon version instead:"
        say "    $MINICONDA_URL"
        say "    then double-click me again."
        return 1
    fi
    ok "Found Miniconda at $base"
    # Always call this base's own conda binary. (Sourcing conda.sh defines a
    # shell FUNCTION, which wrappers like caffeinate cannot run — they would
    # silently pick up a different conda from PATH instead.)
    local CONDA_BIN="$base/bin/conda"
    local ENV_PY="$base/envs/$ENV_NAME/bin/python"

    # ── the mireasy environment (marker-gated, deterministic recreate) ──
    rule
    if [[ -f "$MARKER" && -x "$ENV_PY" ]] && "$ENV_PY" -c "import mireasy" >/dev/null 2>&1; then
        ok "mireasy is already installed — running a quick health check…"
    else
        if [[ -d "$base/envs/$ENV_NAME" ]]; then
            say "Found a previous incomplete installation — rebuilding it cleanly…"
            "$CONDA_BIN" env remove -n "$ENV_NAME" -y >/dev/null 2>&1
        fi
        say "Installing the mireasy environment. This downloads ~2 GB and takes"
        say "5–15 minutes. Lots of text will scroll by — that is NORMAL."
        say "Keep the laptop OPEN and PLUGGED IN. Don't close this window."
        say ""
        say "(Note: this step accepts conda's standard Terms of Service, which"
        say " conda requires for automated installs: anaconda.com/legal)"
        rule
        if ! caffeinate -i "$CONDA_BIN" env create -f environment.yml; then
            say ""
            say "First attempt failed — cleaning caches and trying once more"
            say "(this usually fixes interrupted downloads)…"
            "$CONDA_BIN" clean --all -y >/dev/null 2>&1
            "$CONDA_BIN" env remove -n "$ENV_NAME" -y >/dev/null 2>&1
            if ! caffeinate -i "$CONDA_BIN" env create -f environment.yml; then
                rule
                bad "The installation failed twice."
                say "    Please email install_log.txt (in this folder) to the"
                say "    mireasy author — it contains everything needed to help you."
                return 1
            fi
        fi
        ok "Environment installed"
    fi

    # ── the AI models (retry once; failure blocks the success banner) ──
    rule
    say "Fetching the analysis models (~45 MB; already-present files are skipped)…"
    if ! caffeinate -i "$ENV_PY" download_models.py; then
        say "  Retrying the model download once…"
        if ! caffeinate -i "$ENV_PY" download_models.py; then
            rule
            bad "Everything is installed EXCEPT the models (a download problem)."
            say "    Re-run me on a better internet connection to finish."
            return 1
        fi
    fi
    ok "Models ready"

    # ── self-test: the install is only 'done' when the test suite says so ──
    rule
    say "Checking everything works (about half a minute)…"
    if ! caffeinate -i "$ENV_PY" run_tests.py -q; then
        rule
        bad "The self-check found a problem."
        say "    Please email install_log.txt (in this folder) to the mireasy"
        say "    author — it contains everything needed to help you."
        return 1
    fi
    date > "$MARKER"

    rule
    say ""
    say "  ✓✓✓  mireasy is ready!  ✓✓✓"
    say ""
    say "  To analyze music: double-click  run_mireasy.command  (in this"
    say "  folder) and drag your audio folder into the window it opens."
    say ""
    rule
    return 0
}

main 2>&1 | tee "$LOG"
rc=${pipestatus[1]}
pause_and_exit $rc
