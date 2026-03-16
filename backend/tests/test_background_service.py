"""Unit tests for the background colour derivation service."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app.models.asset import AssetBackground
from app.services.background_service import (
    DEFAULT_BACKGROUND_FILL_MODE,
    VALID_BACKGROUND_FILL_MODES,
    background_meta_from_dict,
    derive_background_meta,
)


def _write_solid_jpeg(path: Path, color: tuple[int, int, int], size: tuple[int, int] = (200, 150)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", size, color=color)
    img.save(path, format="JPEG")


class TestValidBackgroundFillModes:
    def test_valid_modes_set(self) -> None:
        assert VALID_BACKGROUND_FILL_MODES == {
            "black",
            "dominant_color",
            "gradient",
            "blurred_backdrop",
            "mirrored_edges",
            "soft_vignette",
            "palette_wash",
            "adaptive_auto",
        }

    def test_default_is_black(self) -> None:
        assert DEFAULT_BACKGROUND_FILL_MODE == "black"


class TestDeriveBackgroundMeta:
    def test_solid_red_image(self, tmp_path: Path) -> None:
        img_path = tmp_path / "red.jpg"
        _write_solid_jpeg(img_path, (200, 30, 30))
        bg = derive_background_meta(img_path)

        assert isinstance(bg, AssetBackground)
        assert bg.ready is True
        # Dominant colour is a CSS hex string
        assert bg.dominant_color.startswith("#")
        assert len(bg.dominant_color) == 7
        # Gradient is 2 colours
        assert len(bg.gradient_colors) == 2
        for c in bg.gradient_colors:
            assert c.startswith("#")
            assert len(c) == 7

    def test_subdued_colours_are_darker_than_source(self, tmp_path: Path) -> None:
        """Derived colours should be noticeably darker/more muted than the raw image."""
        img_path = tmp_path / "bright.jpg"
        _write_solid_jpeg(img_path, (255, 200, 50))  # bright yellow
        bg = derive_background_meta(img_path)

        # Parse hex back to RGB
        dom = bg.dominant_color
        r = int(dom[1:3], 16)
        g = int(dom[3:5], 16)
        b = int(dom[5:7], 16)
        # Subdued — should be significantly darker than the source
        assert r < 200 and g < 200 and b < 200

    def test_solid_black_image(self, tmp_path: Path) -> None:
        img_path = tmp_path / "black.jpg"
        _write_solid_jpeg(img_path, (0, 0, 0))
        bg = derive_background_meta(img_path)
        assert bg.ready is True
        # Near-black image → dominant colour is still valid hex
        assert bg.dominant_color.startswith("#")

    def test_gradient_start_and_end_reflect_left_right_halves(self, tmp_path: Path) -> None:
        """Left half red, right half blue → gradient colours should differ."""
        img = Image.new("RGB", (100, 100), (200, 10, 10))
        right = Image.new("RGB", (50, 100), (10, 10, 200))
        img.paste(right, (50, 0))
        img_path = tmp_path / "split.jpg"
        img.save(img_path, format="JPEG")

        bg = derive_background_meta(img_path)
        left_c = bg.gradient_colors[0]
        right_c = bg.gradient_colors[1]
        # They should differ because the halves are different colours
        assert left_c != right_c

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(Exception):
            derive_background_meta(tmp_path / "nonexistent.jpg")


class TestBackgroundMetaFromDict:
    def test_round_trip(self) -> None:
        data = {
            "dominant_color": "#1a2b3c",
            "gradient_colors": ["#111111", "#222222"],
        }
        bg = background_meta_from_dict(data)
        assert bg.dominant_color == "#1a2b3c"
        assert bg.gradient_colors == ["#111111", "#222222"]
        assert bg.ready is True

    def test_empty_dict_gives_not_ready(self) -> None:
        bg = background_meta_from_dict({})
        assert bg.ready is False

    def test_partial_dict(self) -> None:
        bg = background_meta_from_dict({"dominant_color": "#abcdef"})
        assert bg.dominant_color == "#abcdef"
        assert bg.gradient_colors == []
        assert bg.ready is False


class TestAssetBackgroundModel:
    def test_ready_when_populated(self) -> None:
        bg = AssetBackground(dominant_color="#112233", gradient_colors=["#000011", "#001100"])
        assert bg.ready is True

    def test_not_ready_when_empty(self) -> None:
        bg = AssetBackground()
        assert bg.ready is False

    def test_not_ready_when_only_one_gradient_color(self) -> None:
        bg = AssetBackground(dominant_color="#112233", gradient_colors=["#000011"])
        assert bg.ready is False
