#!/usr/bin/env python3
"""Regenerate PWA / OG PNGs from the ChessMate favicon (replaces CRA React logos)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "chess_mate" / "frontend" / "public"
SOURCE = PUBLIC / "ChessMate_favicon_no_bg.ico"

OUTPUTS = {
    "logo192.png": 192,
    "logo512.png": 512,
    "apple-touch-icon.png": 180,
    "chessmate-og.png": 630,
}


def _load_source() -> Image.Image:
    image = Image.open(SOURCE)
    return image.convert("RGBA")


def _save_square(image: Image.Image, size: int, path: Path) -> None:
    resized = image.resize((size, size), Image.Resampling.LANCZOS)
    resized.save(path, format="PNG", optimize=True)


def _save_og(image: Image.Image, path: Path) -> None:
    width, height = 1200, 630
    canvas = Image.new("RGBA", (width, height), (79, 70, 229, 255))
    icon_size = 320
    icon = image.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
    offset = ((width - icon_size) // 2, (height - icon_size) // 2)
    canvas.paste(icon, offset, icon)
    canvas.convert("RGB").save(path, format="PNG", optimize=True)


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"Missing favicon source: {SOURCE}")

    image = _load_source()
    for filename, size in OUTPUTS.items():
        path = PUBLIC / filename
        if filename == "chessmate-og.png":
            _save_og(image, path)
        else:
            _save_square(image, size, path)
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
