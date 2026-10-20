"""Chạy nhanh không cần cài đặt:  python run.py [generate|run] [tuỳ chọn]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
from salesanalysis.cli import main  # noqa: E402

if __name__ == "__main__":
    main(sys.argv[1:] or ["run"])
