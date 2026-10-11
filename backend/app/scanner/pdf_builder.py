"""Mehrseitige Bilder zu einer PDF zusammenführen."""

from __future__ import annotations

from pathlib import Path

from PIL import Image


def images_to_pdf(image_paths: list[Path], output_path: Path) -> None:
    """Schreibt eine mehrseitige PDF aus PNG/BMP/TIFF-Dateien."""
    if not image_paths:
        raise ValueError("Mindestens ein Bild wird für die PDF benötigt.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    opened: list[Image.Image] = []
    try:
        for path in image_paths:
            image = Image.open(path)
            if image.mode in ("RGBA", "P"):
                image = image.convert("RGB")
            elif image.mode == "L":
                image = image.convert("RGB")
            opened.append(image)

        first, *rest = opened
        save_kwargs: dict = {"save_all": True, "append_images": rest} if rest else {}
        first.save(output_path, format="PDF", resolution=300.0, **save_kwargs)
    finally:
        for image in opened:
            image.close()
