"""
Doc-drift guard: every attribute that README.md, DOCUMENTATION.md and the
help() texts tell users to type must actually exist. Catches renames like
`stimuli` -> `session` or `.toussaint_sync_score` before users do.
"""
import os
import re

import pytest

from rewardio.rewardio import Stimulus, Session, Participant
from rewardio.core import stimulus_help, session_help, participant_help

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# `stimulus.bpm`, `session.help()`, `s.save_timeseries()`, ...
PREFIXED = re.compile(r"\b(stimulus|session|participant|s)\.([A-Za-z_]\w*)")
# `.duration`, `.pitch_mean/std`, `.pitch_time/freq/conf` — a dot that is not
# preceded by a name, number or bracket (so "BS.1770" or "0.5" don't match)
BARE = re.compile(r"(?<![\w)\]])\.([A-Za-z_][\w/]*)")


def _expand(token):
    """'zcr_mean/std' -> ['zcr_mean', 'zcr_std'];
    'pitch_time/freq/conf' -> ['pitch_time', 'pitch_freq', 'pitch_conf']."""
    first, *alts = token.split("/")
    stem = first.rsplit("_", 1)[0]
    return [first] + [f"{stem}_{alt}" for alt in alts if alt]


def _read(name):
    with open(os.path.join(REPO, name), encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def objects(sine_wav, session_folder, participant_folder):
    s = Stimulus(sine_wav)
    return {"stimulus": s, "s": s,
            "session": Session(session_folder),
            "participant": Participant(participant_folder)}


def _missing(pairs, objects):
    # dir() lists attributes and properties without evaluating them
    return sorted({f"{who}.{name}" for who, name in pairs
                   if name not in dir(objects[who])})


def test_readme_uses_shell_variable_names():
    # Regression: README said `stimuli(3)` / `stimuli.help()`, but the shell
    # defines `session`. Checks `name(3)`, `name("x")` and `name.method(`.
    calls = re.findall(r"`([a-z_]\w*)(?:\((?:\d+|\"[^\"]*\")\)|\.\w+\()",
                       _read("README.md"))
    assert len(calls) > 10
    assert set(calls) <= {"stimulus", "session", "participant"}


def test_readme_names_exist(objects):
    pairs = PREFIXED.findall(_read("README.md"))
    assert len(pairs) > 20                       # sanity: the parser found them
    assert _missing(pairs, objects) == []


def test_documentation_names_exist(objects):
    text = _read("DOCUMENTATION.md")
    pairs = PREFIXED.findall(text)
    # The feature tables list Stimulus attributes as `.name`
    for line in text.splitlines():
        if line.startswith("|"):
            pairs += [("stimulus", n) for token in BARE.findall(line)
                      for n in _expand(token)]
    assert len(pairs) > 40
    assert _missing(pairs, objects) == []


@pytest.mark.parametrize("who, helper", [
    ("stimulus", stimulus_help),
    ("session", session_help),
    ("participant", participant_help),
])
def test_help_names_exist(objects, capsys, who, helper):
    helper(objects[who])
    pairs = []
    for line in capsys.readouterr().out.splitlines():
        # Only the name column: ".save_timeseries(path)  : Save ... as .npz"
        name_column = re.split(r"\s[-:]\s|-\s", line, maxsplit=1)[0]
        pairs += [(who, n) for token in BARE.findall(name_column)
                  for n in _expand(token)]
    assert len(pairs) > 5
    assert _missing(pairs, objects) == []
