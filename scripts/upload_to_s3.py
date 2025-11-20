import sys
import os
import glob
import boto3
from datetime import datetime

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from src.data.ingestion import load_from_local, save_to_s3  # noqa: E402
from src.config.settings import settings  # noqa: E402
from src.infrastructure.logging import setup_logging, get_logger  # noqa: E402

setup_logging()
logger = get_logger(__name__)


def upload_data_to_s3():
    logger.info("Uploading data to S3", bucket=settings.s3_bucket)

    local_file = "transactions.csv"
    if not os.path.exists(local_file):
        logger.error("Local file not found", file=local_file)
        return

    logger.info("Loading local file", file=local_file)
    df = load_from_local(local_file)

    s3_key = f"{settings.s3_prefix}/raw/transactions.csv"
    logger.info("Uploading to S3", key=s3_key)
    save_to_s3(df, s3_key)

    logger.info("Data uploaded successfully", s3_key=s3_key)


def upload_artifacts_to_s3():
    logger.info("Uploading artifacts to S3", bucket=settings.s3_bucket)

    artifacts_dir = "data/artifacts"
    if not os.path.exists(artifacts_dir):
        logger.error("Artifacts directory not found", dir=artifacts_dir)
        return

    s3_client = boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )

    version = datetime.now().strftime("%Y%m%d")

    files_to_upload = [
        (
            "collaborative_model.pkl",
            f"models/collaborative/{version}/collaborative_model.pkl"
        ),
        ("user_catalog.json", f"catalogs/{version}/user_catalog.json"),
        ("product_catalog.json", f"catalogs/{version}/product_catalog.json"),
    ]

    embedding_files = glob.glob(f"{artifacts_dir}/embeddings_*.npy")
    if embedding_files:
        latest_embedding = max(embedding_files)
        embedding_name = os.path.basename(latest_embedding)
        files_to_upload.append(
            (embedding_name, f"embeddings/{version}/{embedding_name}")
        )

    index_files = glob.glob(f"{artifacts_dir}/faiss_index_*.pkl")
    if index_files:
        latest_index = max(index_files)
        index_name = os.path.basename(latest_index)
        files_to_upload.append(
            (index_name, f"indices/{version}/{index_name}")
        )

    for local_file, s3_key in files_to_upload:
        local_path = os.path.join(artifacts_dir, local_file)
        if os.path.exists(local_path):
            full_s3_key = f"{settings.s3_prefix}/{s3_key}"
            logger.info(
                "Uploading artifact",
                local=local_path,
                s3_key=full_s3_key
            )
            s3_client.upload_file(
                local_path, settings.s3_bucket, full_s3_key
            )
            logger.info("Artifact uploaded", s3_key=full_s3_key)
        else:
            logger.warning("File not found, skipping", file=local_path)

    logger.info("All artifacts uploaded successfully")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Upload data or artifacts to S3"
    )
    parser.add_argument(
        "--data", action="store_true", help="Upload raw data"
    )
    parser.add_argument(
        "--artifacts", action="store_true", help="Upload ML artifacts"
    )
    parser.add_argument(
        "--all", action="store_true", help="Upload everything"
    )

    args = parser.parse_args()

    if args.all or args.data:
        upload_data_to_s3()

    if args.all or args.artifacts:
        upload_artifacts_to_s3()

    if not (args.all or args.data or args.artifacts):
        parser.print_help()


if __name__ == "__main__":
    main()
