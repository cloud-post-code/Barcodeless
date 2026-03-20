from io import BytesIO

from PIL import Image, ImageEnhance


def load_image(image_bytes: bytes) -> Image.Image:
    return Image.open(BytesIO(image_bytes)).convert("RGB")


def center_crop(image: Image.Image, ratio: float) -> Image.Image:
    w, h = image.size
    new_w, new_h = int(w * ratio), int(h * ratio)
    left = (w - new_w) // 2
    top = (h - new_h) // 2
    return image.crop((left, top, left + new_w, top + new_h))


def adjust_brightness(image: Image.Image, factor: float) -> Image.Image:
    return ImageEnhance.Brightness(image).enhance(factor)


def get_image_variants(image: Image.Image) -> dict[str, Image.Image]:
    """Generate multiple visual variants of an image for robust embedding.

    Each variant captures different aspects of the product, improving
    recall under varying real-world conditions (lighting, framing).
    """
    return {
        "full": image,
        "center_crop_80": center_crop(image, 0.80),
        "center_crop_60": center_crop(image, 0.60),
        "bright": adjust_brightness(image, 1.25),
        "dark": adjust_brightness(image, 0.75),
    }


def compress_image(image_bytes: bytes, max_size: int = 1024, quality: int = 85) -> bytes:
    """Resize and compress an image before storage."""
    img = load_image(image_bytes)
    img.thumbnail((max_size, max_size), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()
