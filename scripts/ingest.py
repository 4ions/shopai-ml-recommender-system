import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.ingestion import load_from_local, load_from_s3, save_to_local, save_to_s3
from src.data.validation import validate_transactions, get_data_quality_report
from src.data.transformation import clean_data
from src.config.settings import settings
from src.infrastructure.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def main(source: str = "s3", output_location: str = "local"):
    """
    Main ingestion pipeline that reads data from S3 or local, processes it, and saves it.
    
    Args:
        source: Source of data - "s3" or "local" (default: "s3")
        output_location: Where to save processed data - "s3" or "local" (default: "local")
    """
    logger.info("Starting data ingestion pipeline", source=source, output_location=output_location)

    input_file = "transactions.csv"
    s3_key = f"{settings.s3_prefix}/raw/transactions.csv"
    output_file = "data/processed/ratings.parquet"
    s3_output_key = f"{settings.s3_prefix}/processed/ratings.parquet"

    # Load data from S3 or local
    if source == "s3":
        logger.info("Loading data from S3", s3_key=s3_key, bucket=settings.s3_bucket)
        try:
            df = load_from_s3(s3_key)
            logger.info("Data loaded from S3", rows=len(df))
        except Exception as e:
            logger.error("Failed to load from S3, falling back to local", error=str(e))
            if os.path.exists(input_file):
                logger.info("Loading from local fallback", input_file=input_file)
                df = load_from_local(input_file)
            else:
                raise FileNotFoundError(f"Neither S3 nor local file found: {s3_key} or {input_file}")
    else:
        logger.info("Loading data from local", input_file=input_file)
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Local file not found: {input_file}")
        df = load_from_local(input_file)

    logger.info("Validating data")
    df = validate_transactions(df)

    logger.info("Cleaning data")
    df = clean_data(df)

    logger.info("Generating quality report")
    quality_report = get_data_quality_report(df, data_type="transactions")
    logger.info("Data quality report", report=quality_report)

    # Save processed data
    if output_location == "s3":
        logger.info("Saving processed data to S3", s3_key=s3_output_key)
        save_to_s3(df, s3_output_key)
    else:
        logger.info("Saving processed data locally", output_file=output_file)
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        save_to_local(df, output_file, format="parquet")

    logger.info("Ingestion pipeline completed", output_file=output_file, rows=len(df))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Data ingestion pipeline")
    parser.add_argument(
        "--source",
        type=str,
        default="s3",
        choices=["s3", "local"],
        help="Source of data: 's3' or 'local' (default: 's3')"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="local",
        choices=["s3", "local"],
        help="Output location: 's3' or 'local' (default: 'local')"
    )
    args = parser.parse_args()
    
    main(source=args.source, output_location=args.output)


if __name__ == "__main__":
    main()

