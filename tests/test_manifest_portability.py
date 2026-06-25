"""The manifest must contain no user-specific home paths (portability)."""
from pathlib import Path

import yaml

MANIFEST = Path(__file__).resolve().parent.parent / "manifests" / "tools.yaml"


def test_manifest_has_no_hardcoded_home_paths():
    raw = MANIFEST.read_text()
    assert "/home/pwnedlabs" not in raw, "manifest still has /home/pwnedlabs literal"


def test_cloudfox_path_is_home_relative():
    data = yaml.safe_load(MANIFEST.read_text())
    cloudfox = next(t for t in data["tools"] if t["name"] == "cloudfox")
    assert cloudfox["path"].startswith("~/"), cloudfox["path"]
