"""Routes for serving reports."""
import os
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from typing import Optional

from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


def _generate_eda_report_from_s3() -> bool:
    """Generate EDA report from S3 data.
    
    Reads processed data from S3, generates the EDA report, and saves it to S3.
    This allows generating reports completely in the cloud without local files.
    
    Returns:
        True if report was generated successfully, False otherwise
    """
    try:
        logger.info("Generating EDA report from S3 data")
        
        # Import here to avoid circular dependencies
        import pandas as pd
        import json
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        import matplotlib.pyplot as plt
        import seaborn as sns
        from datetime import datetime
        
        from src.data.ingestion import load_from_s3, load_from_local
        from src.data.validation import get_data_quality_report
        from src.config.settings import settings
        
        # Set style
        sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = (12, 6)
        
        # Try to load from S3 first, then local
        processed_data_path = f"{settings.s3_prefix}/processed/ratings.parquet"
        local_data_path = "data/processed/ratings.parquet"
        
        try:
            logger.info("Loading processed data from S3", s3_key=processed_data_path)
            df = load_from_s3(processed_data_path)
        except Exception as e:
            logger.warning("Failed to load from S3, trying local", error=str(e))
            if os.path.exists(local_data_path):
                df = load_from_local(local_data_path)
            else:
                logger.error("No processed data found in S3 or local")
                return False
        
        logger.info("Data loaded successfully", rows=len(df))
        
        # Create reports directory
        reports_dir = "data/reports"
        os.makedirs(reports_dir, exist_ok=True)
        figures_dir = os.path.join(reports_dir, "figures")
        os.makedirs(figures_dir, exist_ok=True)
        
        # Generate JSON report
        logger.info("Generating EDA JSON report")
        report = {
            "generated_at": datetime.now().isoformat(),
            "data_quality": get_data_quality_report(df, data_type="transactions"),
            "summary": {
                "total_rows": len(df),
                "unique_users": df["user_id"].nunique(),
                "unique_products": df["product_id"].nunique(),
                "date_range": {
                    "min": str(df["timestamp"].min()) if "timestamp" in df.columns else None,
                    "max": str(df["timestamp"].max()) if "timestamp" in df.columns else None,
                },
            },
            "rating_distribution": df["rating"].value_counts().to_dict() if "rating" in df.columns else {},
            "top_users": df["user_id"].value_counts().head(10).to_dict(),
            "top_products": df["product_id"].value_counts().head(10).to_dict(),
        }
        
        json_path = os.path.join(reports_dir, "eda_report.json")
        with open(json_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        logger.info("JSON report generated", path=json_path)
        
        # Generate HTML report (simplified version)
        logger.info("Generating EDA HTML report")
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>EDA Report - ShopAI ML Recommender System</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
        .summary-card {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; border-left: 4px solid #4CAF50; }}
        .summary-card h3 {{ margin: 0 0 10px 0; color: #333; font-size: 14px; }}
        .summary-card p {{ margin: 0; font-size: 24px; font-weight: bold; color: #4CAF50; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:hover {{ background-color: #f5f5f5; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Exploratory Data Analysis Report</h1>
        <p><strong>Generated:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        <h2>Summary Statistics</h2>
        <div class="summary">
            <div class="summary-card"><h3>Total Rows</h3><p>{len(df):,}</p></div>
            <div class="summary-card"><h3>Unique Users</h3><p>{df['user_id'].nunique():,}</p></div>
            <div class="summary-card"><h3>Unique Products</h3><p>{df['product_id'].nunique():,}</p></div>
        </div>
        <h2>Top 10 Most Active Users</h2>
        <table>
            <tr><th>User ID</th><th>Interactions</th></tr>
"""
        
        top_users = df["user_id"].value_counts().head(10)
        for user_id, count in top_users.items():
            html_content += f"<tr><td>{user_id}</td><td>{count:,}</td></tr>\n"
        
        html_content += """
        </table>
        <h2>Top 10 Most Popular Products</h2>
        <table>
            <tr><th>Product ID</th><th>Interactions</th></tr>
"""
        
        top_products = df["product_id"].value_counts().head(10)
        for product_id, count in top_products.items():
            html_content += f"<tr><td>{product_id}</td><td>{count:,}</td></tr>\n"
        
        html_content += """
        </table>
    </div>
</body>
</html>
"""
        
        html_path = os.path.join(reports_dir, "eda_report.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info("HTML report generated", path=html_path)
        
        # Upload to S3
        try:
            import boto3
            s3_client = boto3.client(
                "s3",
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
            )
            
            # Upload HTML
            s3_key = f"{settings.s3_prefix}/reports/eda_report.html"
            s3_client.upload_file(html_path, settings.s3_bucket, s3_key)
            logger.info("Uploaded HTML report to S3", s3_key=s3_key)
            
            # Upload JSON
            s3_key = f"{settings.s3_prefix}/reports/eda_report.json"
            s3_client.upload_file(json_path, settings.s3_bucket, s3_key)
            logger.info("Uploaded JSON report to S3", s3_key=s3_key)
        
        except Exception as e:
            logger.warning("Failed to upload reports to S3", error=str(e))
            # Continue anyway, report is generated locally
        
        logger.info("EDA report generated successfully")
        return True
        
    except Exception as e:
        logger.error("Error generating EDA report", error=str(e), exc_info=True)
        return False


@router.get("/eda", response_class=HTMLResponse)
async def get_eda_report(generate_if_missing: bool = True):
    """Get EDA HTML report.
    
    Returns the Exploratory Data Analysis report in HTML format.
    If report doesn't exist and generate_if_missing=True, generates it automatically
    from S3 data.
    
    Args:
        generate_if_missing: If True, generates the report automatically if not found.
            Default: True
    """
    report_path = Path("data/reports/eda_report.html")
    
    if not report_path.exists():
        logger.info("EDA report not found locally, trying to download from S3")
        try:
            from src.api.download_artifacts import download_report_from_s3
            download_report_from_s3("eda_report.html")
        except Exception as e:
            logger.warning("Failed to download report from S3", error=str(e))
        
        # If still doesn't exist and generate_if_missing is True, generate it
        if not report_path.exists() and generate_if_missing:
            logger.info("Report not found, generating automatically from S3 data")
            success = _generate_eda_report_from_s3()
            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to generate EDA report. Please check logs and ensure processed data exists in S3."
                )
        
        # Check again after generation
        if not report_path.exists():
            raise HTTPException(
                status_code=404,
                detail="EDA report not found and could not be generated. Please ensure processed data exists in S3."
            )
    
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # Fix image paths to be relative to the API endpoint
        html_content = html_content.replace(
            'src="figures/',
            'src="/api/v1/reports/eda/figures/'
        )
        
        return HTMLResponse(content=html_content)
    except Exception as e:
        logger.error("Error reading EDA report", error=str(e))
        raise HTTPException(status_code=500, detail=f"Error reading report: {str(e)}")


@router.get("/eda/figures/{filename}")
async def get_eda_figure(filename: str):
    """Get EDA report figure/image.
    
    Args:
        filename: Name of the figure file (e.g., rating_distribution.png)
    """
    figure_path = Path(f"data/reports/figures/{filename}")
    
    if not figure_path.exists():
        logger.warning("Figure not found", path=str(figure_path))
        raise HTTPException(status_code=404, detail=f"Figure not found: {filename}")
    
    # Determine content type based on extension
    content_type = "image/png"
    if filename.endswith(".jpg") or filename.endswith(".jpeg"):
        content_type = "image/jpeg"
    elif filename.endswith(".svg"):
        content_type = "image/svg+xml"
    
    return FileResponse(
        path=str(figure_path),
        media_type=content_type,
        filename=filename
    )


@router.post("/eda/generate")
async def generate_eda_report_endpoint(background_tasks: BackgroundTasks):
    """Generate EDA report from S3 data.
    
    This endpoint triggers the generation of the EDA report by reading
    processed data from S3, generating the report, and saving it to S3.
    
    Returns immediately and generates the report in the background.
    """
    logger.info("EDA report generation requested")
    
    # Run in background to avoid timeout
    background_tasks.add_task(_generate_eda_report_from_s3)
    
    return JSONResponse(
        content={
            "message": "EDA report generation started",
            "status": "processing",
            "note": "Report will be available at /api/v1/reports/eda once generation completes"
        },
        status_code=202
    )


@router.get("/eda/json")
async def get_eda_json(generate_if_missing: bool = True):
    """Get EDA report in JSON format.
    
    Returns the Exploratory Data Analysis report in JSON format.
    If report doesn't exist and generate_if_missing=True, generates it automatically.
    
    Args:
        generate_if_missing: If True, generates the report automatically if not found.
            Default: True
    """
    import json
    
    report_path = Path("data/reports/eda_report.json")
    
    if not report_path.exists():
        logger.info("EDA JSON report not found, trying to download from S3")
        try:
            from src.api.download_artifacts import download_report_from_s3
            download_report_from_s3("eda_report.json")
        except Exception as e:
            logger.warning("Failed to download JSON report from S3", error=str(e))
        
        # If still doesn't exist and generate_if_missing is True, generate it
        if not report_path.exists() and generate_if_missing:
            logger.info("JSON report not found, generating automatically from S3 data")
            success = _generate_eda_report_from_s3()
            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to generate EDA report. Please check logs and ensure processed data exists in S3."
                )
        
        if not report_path.exists():
            raise HTTPException(
                status_code=404,
                detail="EDA JSON report not found and could not be generated."
            )
    
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error("Error reading EDA JSON report", error=str(e))
        raise HTTPException(status_code=500, detail=f"Error reading report: {str(e)}")

