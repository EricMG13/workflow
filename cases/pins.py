"""Shared pin manifest for the owner and chart oracles (stdlib only).

    python3 -I cases/pins.py            write cases/PINS.json: sorted {path: sha256} for
                                        cases/*-owner/{manifest,submissions,expected}.json,
                                        cases/*-owner/*-view-tree.json,
                                        cases/*-owner/builder/build.py, cases/charts/*-expected.json,
                                        cases/charts/expected.json, cases/charts/builder/*.py and src/deploy_vii/methodology.json
    python3 -I cases/pins.py --check    exit 1 and name every path that differs, is missing or is unlisted

Module tests read the hashes from cases/PINS.json instead of repeating them; a re-pin is one regenerated file.
"""

import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "cases" / "PINS.json"
PATTERNS = (
    "cases/*-owner/manifest.json",
    "cases/*-owner/submissions.json",
    "cases/*-owner/expected.json",
    "cases/*-owner/*-view-tree.json",
    "cases/*-owner/builder/build.py",
    "cases/charts/*-expected.json",
    "cases/charts/expected.json",
    "cases/charts/builder/*.py",
    "src/deploy_vii/methodology.json",
)


def current():
    paths = sorted({p for pattern in PATTERNS for p in ROOT.glob(pattern)})
    return {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths
    }


def main(argv):
    if argv not in ([], ["--check"]):
        print("usage: pins.py [--check]", file=sys.stderr)
        return 2
    pins = current()
    if not argv:
        OUT.write_text(json.dumps(pins, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {OUT.relative_to(ROOT)}: {len(pins)} paths")
        return 0
    recorded = json.loads(OUT.read_text(encoding="utf-8"))
    drift = [
        f"{k}: {recorded.get(k, 'unlisted')} -> {pins.get(k, 'missing')}"
        for k in sorted(set(recorded) | set(pins))
        if recorded.get(k) != pins.get(k)
    ]
    print("\n".join(drift) if drift else f"cases/PINS.json matches {len(pins)} paths")
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
