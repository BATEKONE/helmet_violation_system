import os
from pathlib import Path

import kagglehub

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("KAGGLEHUB_CACHE", str(ROOT / "datasets" / "kaggle_cache"))

path = kagglehub.dataset_download("hozngvan/helmet-detection")
print("Dataset downloaded to:", path)
