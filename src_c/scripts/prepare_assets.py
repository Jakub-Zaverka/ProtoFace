"""PlatformIO preflight: avoid uploading an incomplete filesystem image."""
Import("env")
from pathlib import Path

root = Path(env.subst("$PROJECT_DIR"))
required = [root / "data/faces/eye.bmp", root / "data/static/index.html",
            root / "data/transitions/mouth--mouth_speak.mph"]
for path in required:
    if not path.is_file():
        raise RuntimeError("Missing asset: {}. Run scripts/sync_assets.py".format(path))
