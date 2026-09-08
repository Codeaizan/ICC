from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path

import nibabel as nib
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset


def normalize_ct(ct: np.ndarray) -> np.ndarray:
    clipped = np.clip(ct.astype(np.float32), -20.0, 100.0)
    return (clipped + 20.0) / 120.0


class AISDSliceDataset(Dataset):
    def __init__(self, manifest: str | Path, split: str, max_cases: int | None = None):
        with Path(manifest).open(newline="", encoding="utf-8") as handle:
            rows = [row for row in csv.DictReader(handle) if row["split"] == split]
        if max_cases is not None:
            rows = rows[:max_cases]
        self.slices: list[tuple[str, str, int]] = []
        for row in rows:
            ct_image = nib.load(row["ct_path"])
            for index in range(ct_image.shape[2]):
                self.slices.append((row["ct_path"], row["lesion_path"], index))

    def __len__(self) -> int:
        return len(self.slices)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        ct_path, mask_path, slice_index = self.slices[index]
        ct = nib.load(ct_path).get_fdata(dtype=np.float32)
        mask = nib.load(mask_path).get_fdata()
        image = normalize_ct(ct[:, :, slice_index])
        mirrored = np.flip(image, axis=0).copy()
        difference = np.clip((mirrored - image) / np.maximum(mirrored, 0.05), 0.0, 1.0)
        target = np.isin(mask[:, :, slice_index], [1, 2, 3, 5]).astype(np.float32)
        return torch.from_numpy(np.stack((image, mirrored, difference))), torch.from_numpy(target[None, ...])


class DoubleConv(nn.Module):
    def __init__(self, input_channels: int, output_channels: int):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Conv2d(input_channels, output_channels, 3, padding=1),
            nn.InstanceNorm2d(output_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(output_channels, output_channels, 3, padding=1),
            nn.InstanceNorm2d(output_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.layers(x)


class SmallUNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.down1 = DoubleConv(3, 16)
        self.down2 = DoubleConv(16, 32)
        self.down3 = DoubleConv(32, 64)
        self.pool = nn.MaxPool2d(2)
        self.up2 = DoubleConv(64 + 32, 32)
        self.up1 = DoubleConv(32 + 16, 16)
        self.head = nn.Conv2d(16, 1, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        first = self.down1(x)
        second = self.down2(self.pool(first))
        bottleneck = self.down3(self.pool(second))
        up_second = nn.functional.interpolate(bottleneck, size=second.shape[-2:], mode="bilinear", align_corners=False)
        up_second = self.up2(torch.cat((up_second, second), dim=1))
        up_first = nn.functional.interpolate(up_second, size=first.shape[-2:], mode="bilinear", align_corners=False)
        return self.head(self.up1(torch.cat((up_first, first), dim=1)))


def dice_from_logits(logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    prediction = (torch.sigmoid(logits) > 0.5).float()
    intersection = (prediction * target).sum(dim=(1, 2, 3))
    denominator = prediction.sum(dim=(1, 2, 3)) + target.sum(dim=(1, 2, 3))
    return ((2.0 * intersection + 1.0) / (denominator + 1.0)).mean()


def run_epoch(model, loader, optimizer, device, training: bool, scaler: torch.amp.GradScaler | None = None) -> float:
    model.train(training)
    total_dice = 0.0
    batches = 0
    for images, targets in loader:
        images, targets = images.to(device), targets.to(device)
        with torch.set_grad_enabled(training):
            with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=scaler is not None):
                logits = model(images)
                loss = nn.functional.binary_cross_entropy_with_logits(logits, targets)
            if training:
                optimizer.zero_grad()
                if scaler is None:
                    loss.backward()
                    optimizer.step()
                else:
                    scaler.scale(loss).backward()
                    scaler.step(optimizer)
                    scaler.update()
        total_dice += float(dice_from_logits(logits.detach(), targets))
        batches += 1
    return total_dice / max(batches, 1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a small AISD 2D lesion segmentation baseline")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", default="outputs/model")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--max-cases", type=int)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--device", choices=("auto", "cuda", "cpu"), default="auto")
    parser.add_argument("--no-amp", action="store_true", help="disable mixed precision")
    parser.add_argument("--seed", type=int, default=20260908)
    args = parser.parse_args()
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.set_num_threads(6)
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available")
    device = torch.device("cuda" if args.device == "auto" and torch.cuda.is_available() else args.device if args.device != "auto" else "cpu")
    train_data = AISDSliceDataset(args.manifest, "train", args.max_cases)
    validation_data = AISDSliceDataset(args.manifest, "validation", args.max_cases)
    train_loader = DataLoader(train_data, batch_size=args.batch_size, shuffle=True, num_workers=args.workers, pin_memory=device.type == "cuda")
    validation_loader = DataLoader(validation_data, batch_size=args.batch_size, shuffle=False, num_workers=args.workers, pin_memory=device.type == "cuda")
    model = SmallUNet().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda" and not args.no_amp)
    amp_scaler = scaler if scaler.is_enabled() else None
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    history = []
    best_validation_dice = -1.0
    for epoch in range(1, args.epochs + 1):
        train_dice = run_epoch(model, train_loader, optimizer, device, True, amp_scaler)
        validation_dice = run_epoch(model, validation_loader, optimizer, device, False)
        row = {"epoch": epoch, "train_dice": train_dice, "validation_dice": validation_dice}
        history.append(row)
        print(json.dumps(row), flush=True)
        if validation_dice > best_validation_dice:
            best_validation_dice = validation_dice
            torch.save(model.state_dict(), output / "best_small_unet.pt")
    torch.save(model.state_dict(), output / "small_unet.pt")
    (output / "history.json").write_text(json.dumps({"device": str(device), "amp": amp_scaler is not None, "history": history}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()