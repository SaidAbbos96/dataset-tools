


from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "files" / "src"
OUT_DIR = ROOT / "files" / "finish"
OUT_DIR.mkdir(parents=True, exist_ok=True)
SRC_DIR.mkdir(parents=True, exist_ok=True)