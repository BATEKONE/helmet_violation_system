import argparse
import os
from pathlib import Path

import torch
import yaml
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent.parent


def resolve_dataset_yaml(data_yaml: Path) -> Path:
    with open(data_yaml, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    dataset_root = Path(cfg["path"])
    if not dataset_root.is_absolute():
        dataset_root = (ROOT / dataset_root).resolve()

    cfg["path"] = str(dataset_root)

    resolved = ROOT / "configs" / "helmet_dataset.resolved.yaml"
    with open(resolved, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)

    return resolved


def parse_args():
    p = argparse.ArgumentParser(description="Обучение YOLOv8 (шлемы). На сервере без GPU задайте --device cpu и меньший --batch.")
    p.add_argument("--data", type=Path, default=ROOT / "configs" / "helmet_dataset.yaml", help="YAML датасета")
    p.add_argument("--weights", type=str, default="yolov8s.pt", help="Стартовые веса (файл или имя из hub ultralytics)")
    p.add_argument("--epochs", type=int, default=10)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--batch", type=int, default=None, help="По умолчанию: 16 на GPU, 4 на CPU")
    p.add_argument("--workers", type=int, default=None, help="По умолчанию: min(8, cpu_count) на GPU, 2 на CPU")
    p.add_argument("--device", type=str, default=None, help="cpu, 0, cuda:0 … По умолчанию: GPU если есть, иначе cpu")
    p.add_argument("--project", type=Path, default=ROOT / "runs")
    p.add_argument("--name", type=str, default="helmet_detector")
    p.add_argument("--patience", type=int, default=15)
    return p.parse_args()


def main():
    args = parse_args()
    if args.device is None:
        device = 0 if torch.cuda.is_available() else "cpu"
    else:
        device = args.device

    if args.batch is None:
        on_cpu = device == "cpu" or (isinstance(device, str) and device.lower() == "cpu")
        batch = 4 if on_cpu else 16
    else:
        batch = args.batch

    if args.workers is None:
        cpu_n = os.cpu_count() or 4
        workers = min(8, cpu_n) if device != "cpu" else min(2, cpu_n)
    else:
        workers = args.workers

    data_yaml = resolve_dataset_yaml(args.data.resolve())

    model = YOLO(str(args.weights))
    model.train(
        data=str(data_yaml),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=batch,
        device=device,
        workers=workers,
        project=str(args.project.resolve()),
        name=args.name,
        exist_ok=True,
        patience=args.patience,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=10,
        translate=0.1,
        scale=0.2,
        fliplr=0.5,
        mosaic=1.0,
        pretrained=True,
    )
    best = args.project / args.name / "weights" / "best.pt"
    print(f"\nГотово. Обученная модель (один файл): {best.resolve()}\n")


if __name__ == "__main__":
    main()
