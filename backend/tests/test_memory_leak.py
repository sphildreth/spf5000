import gc
import io
import resource
import sys
import tracemalloc
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.repositories.asset_repository import AssetRepository
from app.services.asset_ingest_service import AssetIngestService


def generate_test_image(path: Path, color: str = "blue"):
    """Generate a simple test image."""
    img = Image.new("RGB", (1920, 1080), color=color)
    img.save(path)


def _peak_rss_kb() -> int:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return int(value / 1024)
    return int(value)


def _image_upload(
    name: str, color: tuple[int, int, int], size: tuple[int, int] = (1920, 1080)
) -> tuple[str, io.BytesIO, str]:
    buffer = io.BytesIO()
    image = Image.new("RGB", size, color=color)
    image.save(buffer, format="JPEG")
    buffer.seek(0)
    return (name, buffer, "image/jpeg")


def test_no_memory_leaks_db_and_image(fresh_client: TestClient, tmp_path: Path):
    """
    Proves that repeated image ingestion, resizing, and DB operations
    do not leak memory in the backend.
    """
    # Start tracking memory allocations
    tracemalloc.start()

    # 1. Warm-up phase
    # This initializes global caches, DB connections, and first-time imports
    # so they don't skew the leak measurement.
    test_img = tmp_path / "warmup.jpg"
    generate_test_image(test_img)

    # We will upload this image multiple times via the API or service directly
    # To test the whole stack, let's use the API if possible, or the service.
    # Service is better isolated.

    asset_repo = AssetRepository()
    from app.repositories.settings_repository import SettingsRepository

    settings_repo = SettingsRepository()
    service = AssetIngestService(asset_repo, settings_repo)

    for _ in range(5):
        # ingest_file takes path
        service.ingest_file(
            source_id="test",
            collection_ids=[],
            source_path=test_img,
            imported_from_path=str(test_img),
        )

    gc.collect()
    snapshot1 = tracemalloc.take_snapshot()

    # 2. Measurement phase
    # Do it 50 times. If there is a leak, it will grow significantly.
    iterations = 50
    test_img2 = tmp_path / "leak_test.jpg"
    generate_test_image(test_img2, color="green")

    for i in range(iterations):
        service.ingest_file(
            source_id="test",
            collection_ids=[],
            source_path=test_img2,
            imported_from_path=str(test_img2),
            original_filename=f"leak_{i}.jpg",
        )

        # also read the DB to test DB reads
        all_assets = asset_repo.list_assets()
        assert len(all_assets) > 0

    gc.collect()
    snapshot2 = tracemalloc.take_snapshot()

    # Compare snapshots
    top_stats = snapshot2.compare_to(snapshot1, "lineno")

    # Sum the difference in size (bytes)
    total_diff = sum(stat.size_diff for stat in top_stats)

    tracemalloc.stop()

    # Allow some very small variance (e.g., 200KB) for Python's internal caches,
    # but a real leak (50 copies of a 1920x1080 image or DB leak) would be many MBs.
    # 500 KB tolerance
    assert total_diff < 500 * 1024, (
        f"Memory leak detected: {total_diff / 1024:.2f} KB leaked over {iterations} iterations."
    )


def test_api_memory_leak(fresh_client: TestClient, tmp_path: Path):
    """
    Test for memory leaks over API endpoints (backend processing).
    """
    tracemalloc.start()

    # Warm-up API calls
    for _ in range(5):
        resp = fresh_client.get("/api/health")
        assert resp.status_code == 200
        resp = fresh_client.get("/api/display/playlist")

    gc.collect()
    snapshot1 = tracemalloc.take_snapshot()

    # Measurement phase
    iterations = 100
    for _ in range(iterations):
        resp = fresh_client.get("/api/health")
        assert resp.status_code == 200
        resp = fresh_client.get("/api/display/playlist")
        assert resp.status_code in (
            200,
            404,
            401,
            403,
        )  # might be protected or not found, just testing processing leak

    gc.collect()
    snapshot2 = tracemalloc.take_snapshot()

    top_stats = snapshot2.compare_to(snapshot1, "lineno")
    total_diff = sum(stat.size_diff for stat in top_stats)

    tracemalloc.stop()

    # Allow 500 KB tolerance for internal Python/TestClient caches.
    # Real leaks would be multi-megabytes.
    assert total_diff < 500 * 1024, (
        f"Memory leak detected in API processing: {total_diff / 1024:.2f} KB leaked."
    )


def test_ingest_file_requests_heap_trim(
    fresh_client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    del fresh_client
    trim_calls: list[bool] = []
    monkeypatch.setattr(
        "app.services.asset_ingest_service.trim_process_heap",
        lambda: trim_calls.append(True) or True,
    )

    test_img = tmp_path / "trim-check.jpg"
    generate_test_image(test_img)

    asset_repo = AssetRepository()
    from app.repositories.settings_repository import SettingsRepository

    service = AssetIngestService(asset_repo, SettingsRepository())
    result = service.ingest_file(
        source_id="test",
        collection_ids=[],
        source_path=test_img,
        imported_from_path=str(test_img),
    )

    assert result.created is True
    assert trim_calls == [True]


def test_playlist_requests_keep_rss_growth_bounded(test_client: TestClient) -> None:
    colors = [
        (255, 0, 0),
        (0, 255, 0),
        (0, 0, 255),
        (255, 255, 0),
        (255, 0, 255),
        (0, 255, 255),
    ]
    uploads = [
        ("files", _image_upload(f"rss-{index}.jpg", color))
        for index, color in enumerate(colors, start=1)
    ]

    try:
        upload_response = test_client.post(
            "/api/assets/upload",
            data={"collection_id": "default-collection"},
            files=uploads,
        )
    finally:
        for _, (_, handle, _) in uploads:
            handle.close()

    assert upload_response.status_code == 201

    for _ in range(5):
        playlist_response = test_client.get("/api/display/playlist")
        assert playlist_response.status_code == 200
        assert len(playlist_response.json()["items"]) == len(colors)

    gc.collect()
    baseline_rss_kb = _peak_rss_kb()

    for _ in range(100):
        playlist_response = test_client.get("/api/display/playlist")
        assert playlist_response.status_code == 200
        assert len(playlist_response.json()["items"]) == len(colors)

    gc.collect()
    rss_growth_kb = _peak_rss_kb() - baseline_rss_kb
    assert rss_growth_kb < 20 * 1024, (
        f"RSS growth exceeded budget after repeated playlist requests: "
        f"{rss_growth_kb / 1024:.2f} MB"
    )
