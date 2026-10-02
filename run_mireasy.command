#!/bin/zsh
# ─────────────────────────────────────────────────────────────────────────────
#  mireasy — double-click me, then drag your audio folder into this window.
#  (Run install.command first if you haven't.)
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR" 2>/dev/null
ENV_NAME="mireasy"
MARKER="$SCRIPT_DIR/.mireasy_installed"

pause_and_exit() {
    print
    if [[ -t 0 ]]; then
        read -r "?Press Return to close this window. "
    fi
    exit $1
}

# ── find the mireasy environment directly (immune to PATH / dual-conda) ──
ENV_PY=""
for cand in "$HOME/miniconda3" "$HOME/anaconda3" "$HOME/opt/miniconda3" \
            "$HOME/opt/anaconda3" /opt/miniconda3 /opt/anaconda3 \
            /opt/homebrew/Caskroom/miniconda/base /opt/homebrew/anaconda3; do
    if [[ -x "$cand/envs/$ENV_NAME/bin/python" ]]; then
        ENV_PY="$cand/envs/$ENV_NAME/bin/python"
        break
    fi
done

if [[ -z "$ENV_PY" || ! -f "$MARKER" ]]; then
    print "mireasy is not installed yet (or the installation didn't finish)."
    print "Please double-click  install.command  in this folder first."
    pause_and_exit 1
fi

# ── ask for the folder (drag & drop friendly) ──
print "──────────────────────────────────────────────────────────"
print " mireasy"
print "──────────────────────────────────────────────────────────"
print ""
print " Drag the FOLDER with your audio files into this window,"
print " then press Return."
print " (You can also drag a single audio file.)"
print ""

target=""
while [[ -z "$target" ]]; do
    # plain read on purpose: it strips the backslashes Finder adds when you
    # drag paths containing spaces ("My\ Music" -> "My Music")
    read "target? → "
    # trim surrounding whitespace (drag & drop adds a trailing space)
    target="${target#"${target%%[![:space:]]*}"}"
    target="${target%"${target##*[![:space:]]}"}"
    if [[ -z "$target" ]]; then
        print "   (nothing received — drag the folder in, then press Return)"
    elif [[ ! -e "$target" ]]; then
        print "   Hmm, I can't find: $target"
        print "   Please drag the folder itself into this window."
        target=""
    fi
done

print ""
print " Analyzing… (keep this window open; the laptop stays awake)"
print " Results (CSV files) will be saved in an Analysis_… folder inside:"
print "   $SCRIPT_DIR"
print "──────────────────────────────────────────────────────────"

caffeinate -i "$ENV_PY" -m mireasy "$target"
rc=$?

print "──────────────────────────────────────────────────────────"
if (( rc == 0 )); then
    print " Done. Your results are in the Analysis_… folder inside:"
    print "   $SCRIPT_DIR"
else
    print " mireasy reported a problem (see the messages above)."
fi
pause_and_exit $rc
