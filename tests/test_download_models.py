"""Tests for download_models.py (repo root, not part of the package).

Network tests — gated behind MIREASY_RUN_SLOW=1 like the model tests, so the
default suite stays offline-safe. Catches upstream URL rot at essentia.upf.edu
before a fresh user does.
"""
import importlib.util
import io
import json
import os
import urllib.request
from contextlib import redirect_stdout

import pytest

from conftest import RUN_SLOW

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NETWORK = pytest.mark.skipif(
    not RUN_SLOW, reason="set MIREASY_RUN_SLOW=1 to run network tests")


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "download_models", os.path.join(REPO, "download_models.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_script_lists_all_files_genre_expects():
    # Offline consistency check: every model genre.py will look for must be
    # in the download list (drift here = FileNotFoundError for fresh users)
    dm = _load_script()
    listed = {name for _, name in dm.FILES}
    from mireasy import genre
    expected = {os.path.basename(genre._EFFNET_PATH),
                os.path.basename(genre._CREPE_PATH)}
    for base in genre._HEAD_FILES.values():
        expected.add(f"{base}.pb")
        expected.add(f"{base}.json")
    assert expected <= listed


@NETWORK
def test_all_model_urls_alive():
    dm = _load_script()
    for path, name in dm.FILES:
        req = urllib.request.Request(f"{dm.BASE}/{path}", method="HEAD")
        with urllib.request.urlopen(req, timeout=30) as resp:
            assert resp.status == 200, name
            assert int(resp.headers.get("Content-Length", 0)) > 0, name


@NETWORK
def test_download_and_skip_logic(tmp_path):
    # Real download of the smallest file (a label .json), then the skip path
    dm = _load_script()
    dm.MODELS_DIR = str(tmp_path)
    dm.FILES = [f for f in dm.FILES if f[1].endswith(".json")][:1]

    buf = io.StringIO()
    with redirect_stdout(buf):
        assert dm.main() == 0
    name = dm.FILES[0][1]
    assert "[get ]" in buf.getvalue()
    with open(tmp_path / name) as f:
        assert "classes" in json.load(f)          # valid Essentia label file

    buf = io.StringIO()
    with redirect_stdout(buf):
        assert dm.main() == 0                     # second run: skip, still ok
    assert "[skip]" in buf.getvalue()
