"""Validate the shareable skill and build a WorkBuddy ZIP without local data."""
from pathlib import Path
import ast
import hashlib
import json
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def main():
    if sys.version_info < (3, 10):
        raise SystemExit("Python 3.10+ required")
    version = (ROOT / "VERSION").read_text().strip()
    assert re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version), "Invalid VERSION"
    skill = (ROOT / "SKILL.md").read_text()
    assert skill.startswith("---\nname: gusu-building-review\n")
    assert "\ndescription:" in skill.split("---", 2)[1]
    files = [ROOT / "SKILL.md", ROOT / "requirements.txt", ROOT / "VERSION", ROOT / "CHANGELOG.md"]
    for directory in ("assets", "references", "scripts"):
        files += [p for p in (ROOT / directory).rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"]
    for p in files:
        assert not p.is_symlink(), f"Symlink not allowed: {p}"
        text = p.read_text(encoding="utf-8")
        assert not re.search(r"/Users/|C:\\Users\\|BEGIN .*PRIVATE KEY", text), f"Private data marker: {p}"
        if p.suffix == ".py":
            ast.parse(text, filename=str(p))
        if p.suffix == ".json":
            json.loads(text)
        if p.suffix == ".md":
            for target in re.findall(r"\]\(([^)]+)\)", text):
                if "://" in target or target.startswith("#") or not re.search(r"\.(md|json|txt|py)$", target.split("#")[0]):
                    continue
                assert (p.parent / target.split("#")[0]).exists(), f"Broken reference: {p}: {target}"
    subprocess.run([sys.executable, str(ROOT / "scripts/tests/test_online_review.py")], check=True)
    out = ROOT / "dist"
    out.mkdir(exist_ok=True)
    archive = out / "gusu-building-review-workbuddy.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(files):
            z.write(p, "gusu-building-review/" + str(p.relative_to(ROOT)))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (out / "SHA256SUMS").write_text(digest + "  " + archive.name + "\n")
    print(f"Built version {version}: {archive.name} ({len(files)} files)")

if __name__ == "__main__":
    main()
