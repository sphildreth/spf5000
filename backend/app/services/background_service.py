"""Background fill color derivation from display variant images.

Derives a dominant color and a two-stop gradient from a JPEG display variant.
Colors are deliberately subdued/muted so they serve as tasteful letterbox fills
that don't visually compete with the photo.
"""
from __future__ import annotations

import logging
from pathlib import Path

from app.models.asset import AssetBackground

LOGGER = logging.getLogger(__name__)

VALID_BACKGROUND_FILL_MODES: frozenset[str] = frozenset(
    {
        "black",
        "dominant_color",
        "gradient",
        "blurred_backdrop",
        "mirrored_edges",
        "soft_vignette",
        "palette_wash",
        "adaptive_auto",
    }
)
DEFAULT_BACKGROUND_FILL_MODE: str = "black"

# Resize to this before sampling — keeps CPU cost negligible.
_SAMPLE_SIZE = (64, 64)


def _subdue_rgb(r: int, g: int, b: int) -> tuple[int, int, int]:
    """Return a tasteful, subdued version of an RGB colour.

    Strategy: desaturate 45 % toward luma, then darken 30 % toward near-black.
    This keeps the hue recognisable while preventing bright colours from
    distracting from the photo.
    """
    luma = int(0.299 * r + 0.587 * g + 0.114 * b)
    # Desaturate toward luma
    dr = int(r * 0.55 + luma * 0.45)
    dg = int(g * 0.55 + luma * 0.45)
    db = int(b * 0.55 + luma * 0.45)
    # Darken toward near-black (20, 20, 20)
    dark = 20
    blend = 0.70
    return (
        max(0, min(255, int(dr * blend + dark * (1.0 - blend)))),
        max(0, min(255, int(dg * blend + dark * (1.0 - blend)))),
        max(0, min(255, int(db * blend + dark * (1.0 - blend)))),
    )


def _avg_rgb(pixels: list[tuple[int, int, int]]) -> tuple[int, int, int]:
    n = len(pixels)
    if n == 0:
        return (0, 0, 0)
    return (
        sum(p[0] for p in pixels) // n,
        sum(p[1] for p in pixels) // n,
        sum(p[2] for p in pixels) // n,
    )


def _to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"


def derive_background_meta(image_path: Path) -> AssetBackground:
    """Open *image_path* and derive subdued background colours.

    Raises any PIL exception so callers can apply a safe fallback.
    """
    from PIL import Image  # local import — PIL is optional in some test contexts

    with Image.open(image_path) as img:
        sample = img.convert("RGB").resize(_SAMPLE_SIZE, Image.Resampling.LANCZOS)
        w, h = sample.size
        pixels: list[tuple[int, int, int]] = list(sample.get_flattened_data())  # type: ignore[arg-type]

    # Dominant colour — overall average
    dominant = _subdue_rgb(*_avg_rgb(pixels))

    # Gradient colours — left-half and right-half averages give a
    # left-to-right tonal progression that complements horizontal slides.
    left = [pixels[y * w + x] for y in range(h) for x in range(w // 2)]
    right = [pixels[y * w + x] for y in range(h) for x in range(w // 2, w)]

    grad_start = _subdue_rgb(*_avg_rgb(left))
    grad_end = _subdue_rgb(*_avg_rgb(right))

    return AssetBackground(
        dominant_color=_to_hex(*dominant),
        gradient_colors=[_to_hex(*grad_start), _to_hex(*grad_end)],
    )


def background_meta_from_dict(data: dict[str, object]) -> AssetBackground:
    """Reconstruct an :class:`AssetBackground` from its serialised dict form."""
    return AssetBackground(
        dominant_color=str(data.get("dominant_color", "")),
        gradient_colors=[str(c) for c in (data.get("gradient_colors") or [])],
    )
