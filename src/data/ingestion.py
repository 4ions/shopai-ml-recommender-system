from typing import Optional
import pandas as pd
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from src.config.settings import settings
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


def load_from_s3(s3_key: str, bucket: Optional[str] = None) -> pd.DataFrame:
    bucket = bucket or settings.s3_bucket
    logger.info("Loading data from S3", bucket=bucket, key=s3_key)

    try:
        import os
        
        s3_client = boto3.client(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )

        obj = s3_client.get_object(Bucket=bucket, Key=s3_key)
        
        file_ext = os.path.splitext(s3_key)[1].lower()
        
        if file_ext == ".parquet":
            from io import BytesIO
            buffer = BytesIO(obj["Body"].read())
            df = pd.read_parquet(buffer)
            logger.info("Data loaded successfully", rows=len(df), format="parquet")
            return df
        elif file_ext == ".csv":
            df = pd.read_csv(obj["Body"], chunksize=1000)
            chunks = []
            for chunk in df:
                chunks.append(chunk)
            result_df = pd.concat(chunks, ignore_index=True)
            logger.info("Data loaded successfully", rows=len(result_df), format="csv")
            return result_df
        else:
            raise ValueError(f"Unsupported file format: {file_ext}. Supported: .csv, .parquet")

    except NoCredentialsError:
        logger.error("AWS credentials not found")
        raise
    except ClientError as e:
        logger.error("S3 error", error=str(e))
        raise
    except Exception as e:
        logger.error("Unexpected error loading from S3", error=str(e))
        raise


def load_from_local(file_path: str) -> pd.DataFrame:
    logger.info("Loading data from local file", file_path=file_path)

    try:
        import os
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == ".parquet":
            df = pd.read_parquet(file_path)
            logger.info("Data loaded successfully", rows=len(df), format="parquet")
            return df
        elif file_ext == ".csv":
            df = pd.read_csv(file_path, chunksize=1000)
            chunks = []
            for chunk in df:
                chunks.append(chunk)
            result_df = pd.concat(chunks, ignore_index=True)
            logger.info("Data loaded successfully", rows=len(result_df), format="csv")
            return result_df
        else:
            raise ValueError(f"Unsupported file format: {file_ext}. Supported formats: .csv, .parquet")

    except FileNotFoundError:
        logger.error("File not found", file_path=file_path)
        raise
    except Exception as e:
        logger.error("Error loading local file", error=str(e))
        raise


def save_to_s3(df: pd.DataFrame, s3_key: str, bucket: Optional[str] = None) -> None:
    bucket = bucket or settings.s3_bucket
    logger.info("Saving data to S3", bucket=bucket, key=s3_key, rows=len(df))

    try:
        s3_client = boto3.client(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )

        from io import BytesIO
        buffer = BytesIO()
        df.to_parquet(buffer, index=False, compression="snappy")
        buffer.seek(0)

        s3_client.upload_fileobj(buffer, bucket, s3_key)
        logger.info("Data saved successfully")

    except Exception as e:
        logger.error("Error saving to S3", error=str(e))
        raise


def save_to_local(df: pd.DataFrame, file_path: str, format: str = "parquet") -> None:
    logger.info("Saving data to local file", file_path=file_path, format=format, rows=len(df))

    try:
        import os
        os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else ".", exist_ok=True)

        if format == "parquet":
            df.to_parquet(file_path, index=False, compression="snappy")
        elif format == "csv":
            df.to_csv(file_path, index=False)
        else:
            raise ValueError(f"Unsupported format: {format}")

        logger.info("Data saved successfully")

    except Exception as e:
        logger.error("Error saving local file", error=str(e))
        raise

