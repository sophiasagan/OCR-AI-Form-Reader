from __future__ import annotations

import base64
import io
import os
import shutil

from PIL import Image, ImageEnhance, ImageFilter

# On Windows, Poppler binaries are not on PATH by default.
# Set POPPLER_PATH in your environment (or .env) to the bin/ folder, e.g.:
#   POPPLER_PATH=C:\poppler\Library\bin
_POPPLER_PATH: str | None = os.environ.get("POPPLER_PATH") or shutil.which("pdftoppm") and None


def _find_poppler_path() -> str | None:
    env = os.environ.get("POPPLER_PATH")
    if env:
        return env
    # If pdftoppm is already on PATH (Linux/Mac/Railway), pass nothing
    if shutil.which("pdftoppm"):
        return None
    # Common Windows install locations as fallback (winget installs per-user)
    winget_base = os.path.expandvars(
        r"%LOCALAPPDATA%\Microsoft\WinGet\Packages"
    )
    candidates = [
        r"C:\poppler\Library\bin",
        r"C:\Program Files\poppler\Library\bin",
        r"C:\tools\poppler\Library\bin",
    ]
    # Scan winget package directory for any poppler version
    if os.path.isdir(winget_base):
        for entry in os.listdir(winget_base):
            if entry.startswith("oschwartz10612.Poppler"):
                bin_path = os.path.join(winget_base, entry)
                # descend into e.g. poppler-25.07.0/Library/bin
                for sub in os.listdir(bin_path):
                    candidate = os.path.join(bin_path, sub, "Library", "bin")
                    if os.path.isfile(os.path.join(candidate, "pdftoppm.exe")):
                        return candidate
    for path in candidates:
        if os.path.isfile(os.path.join(path, "pdftoppm.exe")):
            return path
    return None


def convert_to_image(file_bytes: bytes, filename: str) -> Image.Image:
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        try:
            from pdf2image import convert_from_bytes
        except ImportError as exc:
            raise RuntimeError(
                "pdf2image is not installed. Run: pip install pdf2image\n"
                "PDF support also requires Poppler. See README for installation."
            ) from exc

        poppler_path = _find_poppler_path()
        try:
            pages = convert_from_bytes(
                file_bytes,
                first_page=1,
                last_page=1,
                dpi=300,
                poppler_path=poppler_path,
            )
        except Exception as exc:
            if "poppler" in str(exc).lower() or "pdftoppm" in str(exc).lower():
                raise RuntimeError(
                    "Poppler is required for PDF conversion but was not found.\n"
                    "Windows: download from https://github.com/oschwartz10612/poppler-windows/releases\n"
                    "  then set POPPLER_PATH=C:\\poppler\\Library\\bin in your .env\n"
                    "Linux:   sudo apt-get install poppler-utils\n"
                    "Mac:     brew install poppler"
                ) from exc
            raise
        return pages[0]
    return Image.open(io.BytesIO(file_bytes)).convert("RGB")


def _deskew(image: Image.Image) -> Image.Image:
    # Pillow has no native deskew; use a lightweight shear-correction heuristic
    # via the image's own ORT data when available, otherwise return as-is.
    # Full deskew (e.g. via scikit-image rotate) can be wired in here later
    # without changing the public API.
    return image


def enhance_scan(image: Image.Image) -> Image.Image:
    image = _deskew(image)
    # Sharpness before contrast so edge clarity is preserved
    image = ImageEnhance.Sharpness(image).enhance(2.0)
    image = ImageEnhance.Contrast(image).enhance(1.8)
    image = ImageEnhance.Brightness(image).enhance(1.1)
    # Mild unsharp mask to recover detail lost in photocopying
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
