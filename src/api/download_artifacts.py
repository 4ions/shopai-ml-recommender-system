import os
import boto3
from typing import Optional
from src.config.settings import settings
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


def download_report_from_s3(filename: str) -> None:
    """Download a report file from S3.
    
    Args:
        filename: Name of the report file (e.g., "eda_report.html")
    """
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    from src.config.settings import settings
    
    logger.info("Downloading report from S3", filename=filename, bucket=settings.s3_bucket)
    
    try:
        s3_client = boto3.client(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        
        s3_key = f"{settings.s3_prefix}/reports/{filename}"
        local_path = f"data/reports/{filename}"
        
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        s3_client.download_file(settings.s3_bucket, s3_key, local_path)
        logger.info("Report downloaded successfully", filename=filename, local_path=local_path)
        
    except NoCredentialsError:
        logger.warning("AWS credentials not found, skipping S3 download")
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            logger.warning("Report not found in S3", filename=filename)
        else:
            logger.warning("S3 error downloading report", filename=filename, error=str(e))
    except Exception as e:
        logger.warning("Unexpected error downloading report from S3", filename=filename, error=str(e))


def download_artifacts_from_s3() -> None:
    if settings.environment != "production":
        logger.info("Not in production, skipping S3 download")
        return

    s3_client = boto3.client(
        "s3",
        region_name=settings.aws_region,
    )

    artifacts_dir = "data/artifacts"
    os.makedirs(artifacts_dir, exist_ok=True)

    artifacts_to_download = [
        "collaborative_model.pkl",
        "user_catalog.json",
        "product_catalog.json",
    ]

    import glob
    index_files = glob.glob(f"{artifacts_dir}/faiss_index_*.pkl")
    if not index_files:
        s3_client.list_objects_v2(
            Bucket=settings.s3_bucket,
            Prefix=f"{settings.s3_prefix}/indices/",
        )
        prefix = f"{settings.s3_prefix}/indices/"
        response = s3_client.list_objects_v2(
            Bucket=settings.s3_bucket,
            Prefix=prefix,
        )
        if "Contents" in response:
            index_files_s3 = [
                obj["Key"]
                for obj in response["Contents"]
                if obj["Key"].endswith(".pkl")
            ]
            if index_files_s3:
                latest_index_s3 = max(index_files_s3)
                artifacts_to_download.append(
                    (latest_index_s3, os.path.basename(latest_index_s3))
                )

    for artifact in artifacts_to_download:
        if isinstance(artifact, tuple):
            s3_key, local_name = artifact
        else:
            s3_key = f"{settings.s3_prefix}/artifacts/{artifact}"
            local_name = artifact

        local_path = os.path.join(artifacts_dir, local_name)
        full_s3_key = f"{settings.s3_prefix}/artifacts/{artifact}" if not isinstance(artifact, tuple) else s3_key

        try:
            logger.info("Downloading artifact", s3_key=full_s3_key, local=local_path)
            s3_client.download_file(settings.s3_bucket, full_s3_key, local_path)
            logger.info("Artifact downloaded", local=local_path)
        except Exception as e:
            logger.warning("Failed to download artifact", s3_key=full_s3_key, error=str(e))

