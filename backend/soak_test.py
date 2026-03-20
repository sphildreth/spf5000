import argparse
import gc
import os
import shutil
import tempfile
import time
import tracemalloc
from pathlib import Path

# Set up environment variables before importing app modules
# to ensure it uses the temporary directory for safety
temp_dir = tempfile.mkdtemp(prefix="spf5000_soak_")
os.environ["SPF5000_DATA_DIR"] = temp_dir
os.environ["SPF5000_CACHE_DIR"] = os.path.join(temp_dir, "cache")
os.environ["SPF5000_LOG_DIR"] = os.path.join(temp_dir, "logs")
os.environ["SPF5000_DATABASE_PATH"] = os.path.join(temp_dir, "spf5000.ddb")

from PIL import Image

from app.core.config import settings
from app.db.bootstrap import bootstrap_database
from app.db.connection import get_connection
from app.repositories.asset_repository import AssetRepository
from app.repositories.settings_repository import SettingsRepository
from app.services.asset_ingest_service import AssetIngestService


def generate_test_image(path: Path, color: str = "blue"):
    img = Image.new("RGB", (1920, 1080), color=color)
    img.save(path)


def setup_app():
    # Override settings explicitly just in case env vars didn't catch
    settings.data_dir = Path(temp_dir)
    settings.cache_dir = Path(os.environ["SPF5000_CACHE_DIR"])
    settings.log_dir = Path(os.environ["SPF5000_LOG_DIR"])
    settings.database_path = Path(os.environ["SPF5000_DATABASE_PATH"])

    # Initialize DB schema
    bootstrap_database()


def run_soak_test(iterations: int, log_interval: int = 100, delay: float = 0.0):
    setup_app()

    asset_repo = AssetRepository()
    settings_repo = SettingsRepository()
    service = AssetIngestService(asset_repo, settings_repo)

    test_img = Path(temp_dir) / "soak_test.jpg"
    generate_test_image(test_img, color="red")

    print(
        f"Starting soak test with {iterations} iterations and {delay}s delay between iterations..."
    )
    print(f"Temporary data directory: {temp_dir}")
    print("-" * 50)

    tracemalloc.start()

    # Warmup
    for _ in range(5):
        service.ingest_file(
            source_id="soak",
            collection_ids=[],
            source_path=test_img,
            imported_from_path=str(test_img),
            original_filename="warmup.jpg",
        )
        asset_repo.list_assets()

    gc.collect()
    start_snapshot = tracemalloc.take_snapshot()
    start_time = time.time()

    try:
        for i in range(1, iterations + 1):
            # To avoid the ingest_file short-circuiting on checksum,
            # generate unique images
            loop_img = Path(temp_dir) / f"soak_{i}.jpg"
            # Randomizing dimension slightly to guarantee unique checksums
            img_width = 1920 + (i % 100)
            img = Image.new("RGB", (img_width, 1080), color="blue")
            img.save(loop_img)

            # 1. Image and DB Write
            result = service.ingest_file(
                source_id="soak",
                collection_ids=[],
                source_path=loop_img,
                imported_from_path=str(loop_img),
                original_filename=f"soak_{i}.jpg",
            )

            # 2. DB Read
            assets = asset_repo.list_assets()

            # 3. DB Cleanup isn't natively available via delete_asset,
            # so we just keep the loop tight and ignore the small list_assets growth.
            # We'll just limit to list_assets() size 5 by popping manually in DB via direct SQL,
            # or just accept list growth. Actually, list_assets growth is tiny.
            # We can run an ad-hoc delete.
            from app.db.connection import get_connection

            with get_connection() as conn:
                conn.execute("DELETE FROM assets WHERE id = ?", (result.asset.id,))
                conn.execute(
                    "DELETE FROM asset_variants WHERE asset_id = ?", (result.asset.id,)
                )
                conn.commit()

            if i % log_interval == 0:
                gc.collect()
                current, peak = tracemalloc.get_traced_memory()
                elapsed = time.time() - start_time
                print(
                    f"Iteration {i:5d}/{iterations} | "
                    f"Memory: {current / 1024 / 1024:.3f} MB (Peak: {peak / 1024 / 1024:.3f} MB) | "
                    f"Assets in DB: {len(assets)} | "
                    f"Elapsed: {elapsed:.1f}s"
                )

            if delay > 0:
                time.sleep(delay)

    except KeyboardInterrupt:
        print("\nSoak test interrupted by user.")

    finally:
        gc.collect()
        end_snapshot = tracemalloc.take_snapshot()

        print("-" * 50)
        print("Comparing memory allocation (End vs Start)...")
        top_stats = end_snapshot.compare_to(start_snapshot, "lineno")
        total_diff = sum(stat.size_diff for stat in top_stats)

        print(f"Total tracked memory difference: {total_diff / 1024:.2f} KB")

        tracemalloc.stop()

        print(f"Cleaning up temporary directory {temp_dir}...")
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("Cleanup complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SPF5000 Soak Test")
    parser.add_argument(
        "--iterations", type=int, default=1000, help="Number of iterations to run"
    )
    parser.add_argument("--interval", type=int, default=100, help="Logging interval")
    parser.add_argument(
        "--delay", type=float, default=0.0, help="Delay in seconds between iterations"
    )
    args = parser.parse_args()

    run_soak_test(args.iterations, args.interval, args.delay)
