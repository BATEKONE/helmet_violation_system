import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main():
    app_path = ROOT / "ui" / "app.py"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(app_path),
            "--server.headless",
            "true",
        ],
        cwd=str(ROOT),
        check=True,
    )


if __name__ == "__main__":
    main()
