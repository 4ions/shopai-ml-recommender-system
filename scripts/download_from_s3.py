import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.ingestion import load_from_s3, save_to_local
from src.config.settings import settings
from src.infrastructure.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def download_data_from_s3():
    logger.info("Downloading data from S3", bucket=settings.s3_bucket)

    s3_key = f"{settings.s3_prefix}/raw/transactions.csv"
    logger.info("Downloading from S3", key=s3_key)

    try:
        df = load_from_s3(s3_key)
        local_file = "transactions.csv"
        logger.info("Saving to local file", file=local_file)
        save_to_local(df, local_file, format="csv")
        logger.info("Data downloaded successfully", rows=len(df))
    except Exception as e:
        logger.error("Error downloading data", error=str(e))
        raise


def download_artifacts_from_s3(version: str = None):
    logger.info("Downloading artifacts from S3", bucket=settings.s3_bucket, version=version)

    import boto3
    import glob

    s3_client = boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )

    if version is None:
        logger.info("No version specified, listing available versions")
        prefix = f"{settings.s3_prefix}/models/collaborative/"
        response = s3_client.list_objects_v2(Bucket=settings.s3_bucket, Prefix=prefix, Delimiter="/")
        
        if "CommonPrefixes" in response:
            versions = [cp["Prefix"].split("/")[-2] for cp in response["CommonPrefixes"]]
            if versions:
                version = max(versions)
                logger.info("Using latest version", version=version)
            else:
                logger.error("No versions found")
                return
        else:
            logger.error("No models found in S3")
            return

    artifacts_dir = "data/artifacts"
    os.makedirs(artifacts_dir, exist_ok=True)

    files_to_download = [
        (f"models/collaborative/{version}/collaborative_model.pkl", "collaborative_model.pkl"),
        (f"catalogs/{version}/user_catalog.json", "user_catalog.json"),
        (f"catalogs/{version}/product_catalog.json", "product_catalog.json"),
    ]

    embedding_prefix = f"{settings.s3_prefix}/embeddings/{version}/"
    response = s3_client.list_objects_v2(Bucket=settings.s3_bucket, Prefix=embedding_prefix)
    if "Contents" in response:
        embedding_files = [obj["Key"] for obj in response["Contents"] if obj["Key"].endswith(".npy")]
        if embedding_files:
            latest_embedding = max(embedding_files)
            files_to_download.append((latest_embedding, os.path.basename(latest_embedding)))

    index_prefix = f"{settings.s3_prefix}/indices/{version}/"
    response = s3_client.list_objects_v2(Bucket=settings.s3_bucket, Prefix=index_prefix)
    if "Contents" in response:
        index_files = [obj["Key"] for obj in response["Contents"] if obj["Key"].endswith(".pkl")]
        if index_files:
            latest_index = max(index_files)
            files_to_download.append((latest_index, os.path.basename(latest_index)))

    for s3_key, local_file in files_to_download:
        full_s3_key = f"{settings.s3_prefix}/{s3_key}" if not s3_key.startswith(settings.s3_prefix) else s3_key
        local_path = os.path.join(artifacts_dir, local_file)
        
        logger.info("Downloading artifact", s3_key=full_s3_key, local=local_path)
        try:
            s3_client.download_file(settings.s3_bucket, full_s3_key, local_path)
            logger.info("Artifact downloaded", local=local_path)
        except Exception as e:
            logger.warning("Failed to download artifact", s3_key=full_s3_key, error=str(e))

    logger.info("Artifacts download completed")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Download data or artifacts from S3")
    parser.add_argument("--data", action="store_true", help="Download raw data")
    parser.add_argument("--artifacts", action="store_true", help="Download ML artifacts")
    parser.add_argument("--version", type=str, help="Version to download (default: latest)")
    parser.add_argument("--all", action="store_true", help="Download everything")

    args = parser.parse_args()

    if args.all or args.data:
        download_data_from_s3()

    if args.all or args.artifacts:
        download_artifacts_from_s3(version=args.version)

    if not (args.all or args.data or args.artifacts):
        parser.print_help()


if __name__ == "__main__":
    main()


