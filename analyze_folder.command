#!/bin/zsh
# ─────────────────────────────────────────────────────────────────────────────
#  easymir batch analysis — double-click me, drag your audio folder in, and
#  walk away. Every song is fully analyzed (tempo, syncopation, loudness,
#  key, genre, mood, …) and saved as a CSV. No questions asked.
#  (Run install.command first if you haven't.)
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR" 2>/dev/null
ENV_NAME="easymir"
MARKER="$SCRIPT_DIR/.easymir_installed"
LOG="$SCRIPT_DIR/analyze_log.txt"

pause_and_exit() {
    print
    if [[ -t 0 ]]; then
        read -r "?Press Return to close this window. "
    fi
    exit $1
}

# ── find the easymir environment directly (immune to PATH / dual-conda) ──
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
    print "easymir is not installed yet (or the installation didn't finish)."
    print "Please double-click  install.command  in this folder first."
    pause_and_exit 1
fi

# ── ask for the folder (drag & drop friendly) ──
print "──────────────────────────────────────────────────────────"
print " easymir — automatic batch analysis"
print "──────────────────────────────────────────────────────────"
print ""
print " Drag the FOLDER with your audio files into this window,"
print " then press Return. Everything will be analyzed and saved"
print " as a CSV — no further questions."
print ""

target=""
while [[ -z "$target" ]]; do
    # plain read on purpose: it strips the backslashes Finder adds when you
    # drag paths containing spaces ("My\ Music" -> "My Music")
    read "target? → "
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
print " Analyzing EVERYTHING — this is the full pipeline (drum separation,"
print " beat tracking, genre, mood, key, …). It takes roughly as long as"
print " the audio itself: a 10-song session can take 30–60 minutes."
print " Keep the laptop open and plugged in; go get a coffee."
print ""
print " Progress is also written to analyze_log.txt (this folder)."
print "──────────────────────────────────────────────────────────"

# The whole point of this script is zero questions: auto-answer the drum-
# separation confirmation, run process_and_save on whatever was dragged in
# (a song, a session folder, or a participant folder), save CSV here.
PYCODE='
import builtins, sys
builtins.input = lambda *a: "y"          # auto-confirm (batch mode)
from easymir.easymir import easymir
obj = easymir(sys.argv[1])
obj.process_and_save(output_path=sys.argv[2])
'
caffeinate -i "$ENV_PY" -c "$PYCODE" "$target" "$SCRIPT_DIR" 2>&1 | tee "$LOG"
rc=${pipestatus[1]}

print "──────────────────────────────────────────────────────────"
if (( rc == 0 )); then
    print " ✓ Done. Your results (CSV) are in the newest Analysis_… folder"
    print "   inside: $SCRIPT_DIR"
    print ""
    if [[ -t 0 ]]; then
        read -t 15 -r "?This window will close in 15 seconds (or press Return). "
    fi
    exit 0
else
    print " ✗ Something went wrong (see the messages above)."
    print "   The full log is analyze_log.txt in this folder — you can"
    print "   drag it into an email to the easymir author."
    pause_and_exit $rc
fi
