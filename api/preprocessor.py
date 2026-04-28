from __future__ import annotations

import base64
import io
import os

from PIL import Image, ImageEnhance, ImageFilter


def convert_to_image(file_bytes: bytes, filename: str) -> Image.Image:
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        import fitz  # PyMuPDF — ships its own renderer, no system deps needed
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        page = doc[0]
        # 300 DPI equivalent: default user-space unit is 72pt, so scale by 300/72
        mat = fitz.Matrix(300 / 72, 300 / 72)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        return Image.open(io.BytesIO(pix.tobytes("ppm"))).convert("RGB")
    return Image.open(io.BytesIO(file_bytes)).convert("RGB")


def _deskew(image: Image.Image) -> Image.Image:
    # Pillow has no native deskew; stub kept so the pipeline shape is stable.
    # Full deskew (scikit-image rotate) can replace this without touching callers.
    return image


def enhance_scan(image: Image.Image) -> Image.Image:
    image = _deskew(image)
    # Sharpness before contrast so edge clarity is preserved
    image = ImageEnhance.Sharpness(image).enhance(2.0)
    image = ImageEnhance.Contrast(image).enhance(1.8)
    image = ImageEnhance.Brightness(image).enhance(1.1)
    image = image.filter(ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))
    return image


def to_base64(image: Image.Image, fmt: str = "JPEG") -> str:
    buf = io.BytesIO()
    image.save(buf, format=fmt, quality=95)
    return base64.standard_b64encode(buf.getvalue()).decode()


def prepare_image(file_bytes: bytes, filename: str) -> tuple[str, str]:
    """Full pipeline: raw bytes → enhanced → base64 string.

    Returns (base64_data, media_type) ready for the Claude vision API.
    """
    image = convert_to_image(file_bytes, filename)
    image = enhance_scan(image)
    return to_base64(image), "image/jpeg"
