"""Read-only environment check; no installs or configuration changes."""
import importlib.util
import json
import shutil
import sys

if __name__ == "__main__":
    print(json.dumps({"python": sys.version, "executable": sys.executable,
        "python_supported": sys.version_info >= (3,10),
        "pypdf": importlib.util.find_spec("pypdf") is not None,
        "Pillow": importlib.util.find_spec("PIL") is not None,
        "pdftoppm": shutil.which("pdftoppm"), "curl": shutil.which("curl")},
        ensure_ascii=False, indent=2))
