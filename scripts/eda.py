import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
import json
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns

from src.data.ingestion import load_from_local
from src.data.validation import get_data_quality_report
from src.infrastructure.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)


def generate_eda_report(df: pd.DataFrame, output_file: str = "data/reports/eda_report.json") -> None:
    """Generate EDA report in JSON format.
    
    Args:
        df: DataFrame with transaction data
        output_file: Path to save JSON report
    """
    logger.info("Generating EDA report", output_file=output_file)
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
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
    
    with open(output_file, "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    logger.info("EDA report generated", output_file=output_file)
    print(f"\nEDA Report Summary:")
    print(f"Total rows: {report['summary']['total_rows']}")
    print(f"Unique users: {report['summary']['unique_users']}")
    print(f"Unique products: {report['summary']['unique_products']}")
    print(f"Report saved to: {output_file}")


def generate_eda_html_report(df: pd.DataFrame, output_file: str = "data/reports/eda_report.html") -> None:
    """Generate EDA report in HTML format with visualizations.
    
    Args:
        df: DataFrame with transaction data
        output_file: Path to save HTML report
    """
    logger.info("Generating EDA HTML report", output_file=output_file)
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Create figures directory
    figures_dir = os.path.join(os.path.dirname(output_file), "figures")
    os.makedirs(figures_dir, exist_ok=True)
    
    html_parts = []
    html_parts.append("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>EDA Report - ShopAI ML Recommender System</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            h1 { color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }
            h2 { color: #555; margin-top: 30px; }
            .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
            .summary-card { background-color: #f9f9f9; padding: 15px; border-radius: 5px; border-left: 4px solid #4CAF50; }
            .summary-card h3 { margin: 0 0 10px 0; color: #333; font-size: 14px; }
            .summary-card p { margin: 0; font-size: 24px; font-weight: bold; color: #4CAF50; }
            table { width: 100%; border-collapse: collapse; margin: 20px 0; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background-color: #4CAF50; color: white; }
            tr:hover { background-color: #f5f5f5; }
            img { max-width: 100%; height: auto; margin: 20px 0; border: 1px solid #ddd; border-radius: 5px; }
            .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #777; text-align: center; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Exploratory Data Analysis Report</h1>
            <p><strong>Generated:</strong> """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
    """)
    
    # Summary statistics
    html_parts.append("<h2>Summary Statistics</h2>")
    html_parts.append('<div class="summary">')
    html_parts.append(f'<div class="summary-card"><h3>Total Rows</h3><p>{len(df):,}</p></div>')
    html_parts.append(f'<div class="summary-card"><h3>Unique Users</h3><p>{df["user_id"].nunique():,}</p></div>')
    html_parts.append(f'<div class="summary-card"><h3>Unique Products</h3><p>{df["product_id"].nunique():,}</p></div>')
    if "rating" in df.columns:
        html_parts.append(f'<div class="summary-card"><h3>Avg Rating</h3><p>{df["rating"].mean():.2f}</p></div>')
    html_parts.append("</div>")
    
    # Rating distribution
    if "rating" in df.columns:
        html_parts.append("<h2>Rating Distribution</h2>")
        rating_counts = df["rating"].value_counts().sort_index()
        
        # Create bar chart
        plt.figure(figsize=(10, 6))
        rating_counts.plot(kind='bar', color='#4CAF50')
        plt.title('Rating Distribution', fontsize=16, fontweight='bold')
        plt.xlabel('Rating', fontsize=12)
        plt.ylabel('Count', fontsize=12)
        plt.xticks(rotation=0)
        plt.tight_layout()
        chart_path = os.path.join(figures_dir, "rating_distribution.png")
        plt.savefig(chart_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        html_parts.append(f'<img src="figures/rating_distribution.png" alt="Rating Distribution">')
        
        # Table
        html_parts.append("<table>")
        html_parts.append("<tr><th>Rating</th><th>Count</th><th>Percentage</th></tr>")
        for rating, count in rating_counts.items():
            pct = (count / len(df)) * 100
            html_parts.append(f"<tr><td>{rating}</td><td>{count:,}</td><td>{pct:.2f}%</td></tr>")
        html_parts.append("</table>")
    
    # Top users
    html_parts.append("<h2>Top 10 Most Active Users</h2>")
    top_users = df["user_id"].value_counts().head(10)
    html_parts.append("<table>")
    html_parts.append("<tr><th>User ID</th><th>Interactions</th></tr>")
    for user_id, count in top_users.items():
        html_parts.append(f"<tr><td>{user_id}</td><td>{count:,}</td></tr>")
    html_parts.append("</table>")
    
    # Top products
    html_parts.append("<h2>Top 10 Most Popular Products</h2>")
    top_products = df["product_id"].value_counts().head(10)
    html_parts.append("<table>")
    html_parts.append("<tr><th>Product ID</th><th>Interactions</th></tr>")
    for product_id, count in top_products.items():
        html_parts.append(f"<tr><td>{product_id}</td><td>{count:,}</td></tr>")
    html_parts.append("</table>")
    
    # Time series if timestamp available
    if "timestamp" in df.columns:
        html_parts.append("<h2>Activity Over Time</h2>")
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["date"] = df["timestamp"].dt.date
        daily_counts = df.groupby("date").size()
        
        plt.figure(figsize=(14, 6))
        daily_counts.plot(kind='line', color='#4CAF50', linewidth=2)
        plt.title('Daily Interactions Over Time', fontsize=16, fontweight='bold')
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Number of Interactions', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        chart_path = os.path.join(figures_dir, "time_series.png")
        plt.savefig(chart_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        html_parts.append(f'<img src="figures/time_series.png" alt="Time Series">')
    
    # Footer
    html_parts.append("""
            <div class="footer">
                <p>Generated by ShopAI ML Recommender System</p>
            </div>
        </div>
    </body>
    </html>
    """)
    
    # Write HTML file
    with open(output_file, "w") as f:
        f.write("\n".join(html_parts))
    
    logger.info("EDA HTML report generated", output_file=output_file)
    print(f"HTML report saved to: {output_file}")


def main():
    """Main EDA pipeline that generates both JSON and HTML reports."""
    logger.info("Starting EDA pipeline")
    
    input_file = "data/processed/ratings.parquet"
    if not os.path.exists(input_file):
        logger.error("Processed data not found", file=input_file)
        logger.info("Running ingestion first...")
        from scripts.ingest import main as ingest_main
        ingest_main()
    
    logger.info("Loading processed data", file=input_file)
    df = load_from_local(input_file)
    
    logger.info("Generating EDA reports")
    generate_eda_report(df)
    generate_eda_html_report(df)
    
    logger.info("EDA pipeline completed")


if __name__ == "__main__":
    main()

