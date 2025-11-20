"""Generate detailed cost analysis in JSON and CSV formats."""
import sys
import os
import json
import csv
from datetime import datetime
from typing import Dict, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config.settings import settings
from src.infrastructure.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


# Cost constants (USD)
COSTS = {
    "openai": {
        "embedding_text_embedding_3_large": 0.00013,  # per 1K tokens
        "completion_gpt4": 0.03,  # per 1K tokens (input)
        "completion_gpt35": 0.0015,  # per 1K tokens (input)
    },
    "aws": {
        "s3_storage": 0.023,  # per GB/month
        "s3_requests": 0.0004,  # per 1K PUT requests
        "s3_data_transfer_out": 0.09,  # per GB (first 10TB)
        "ecs_fargate_vcpu": 0.04048,  # per vCPU/hour
        "ecs_fargate_memory": 0.004445,  # per GB/hour
        "ecr_storage": 0.10,  # per GB/month
        "cloudwatch_logs": 0.50,  # per GB ingested
        "cloudwatch_storage": 0.03,  # per GB/month
        "secrets_manager": 0.40,  # per secret/month
        "alb": 0.0225,  # per ALB-hour
        "alb_lcu": 0.008,  # per LCU-hour
    },
}


def estimate_embedding_tokens(text: str) -> int:
    """Estimate token count (rough approximation: 1 token ≈ 4 characters)."""
    return len(text) // 4


def calculate_openai_costs(
    embedding_requests: int = 0,
    avg_text_length: int = 100,
    completion_requests: int = 0,
    avg_completion_tokens: int = 1000,
) -> Dict[str, float]:
    """Calculate OpenAI API costs.
    
    Args:
        embedding_requests: Number of embedding requests
        avg_text_length: Average text length in characters
        completion_requests: Number of completion requests
        avg_completion_tokens: Average completion tokens per request
        
    Returns:
        Dictionary with cost breakdown
    """
    embedding_tokens = embedding_requests * estimate_embedding_tokens(" " * avg_text_length)
    embedding_cost = (embedding_tokens / 1000) * COSTS["openai"]["embedding_text_embedding_3_large"]
    
    completion_tokens = completion_requests * avg_completion_tokens
    completion_cost = (completion_tokens / 1000) * COSTS["openai"]["completion_gpt35"]
    
    return {
        "embedding_requests": embedding_requests,
        "embedding_tokens": embedding_tokens,
        "embedding_cost_usd": round(embedding_cost, 2),
        "completion_requests": completion_requests,
        "completion_tokens": completion_tokens,
        "completion_cost_usd": round(completion_cost, 2),
        "total_openai_cost_usd": round(embedding_cost + completion_cost, 2),
    }


def calculate_aws_costs(
    s3_storage_gb: float = 1.0,
    s3_requests: int = 1000,
    s3_transfer_gb: float = 0.1,
    ecs_vcpu: float = 1.0,
    ecs_memory_gb: float = 2.0,
    ecs_hours: float = 730,  # 24/7 for a month
    ecr_storage_gb: float = 0.5,
    cloudwatch_logs_gb: float = 1.0,
    cloudwatch_storage_gb: float = 1.0,
    secrets_count: int = 1,
    alb_hours: float = 730,
    alb_lcu_hours: float = 100,
) -> Dict[str, float]:
    """Calculate AWS infrastructure costs.
    
    Args:
        s3_storage_gb: S3 storage in GB
        s3_requests: Number of S3 requests
        s3_transfer_gb: Data transfer out in GB
        ecs_vcpu: ECS vCPU allocation
        ecs_memory_gb: ECS memory in GB
        ecs_hours: ECS running hours
        ecr_storage_gb: ECR storage in GB
        cloudwatch_logs_gb: CloudWatch logs ingested in GB
        cloudwatch_storage_gb: CloudWatch storage in GB
        secrets_count: Number of secrets
        alb_hours: ALB running hours
        alb_lcu_hours: ALB LCU hours
        
    Returns:
        Dictionary with cost breakdown
    """
    s3_cost = (s3_storage_gb * COSTS["aws"]["s3_storage"]) + \
              (s3_requests / 1000 * COSTS["aws"]["s3_requests"]) + \
              (s3_transfer_gb * COSTS["aws"]["s3_data_transfer_out"])
    
    ecs_cost = (ecs_vcpu * ecs_hours * COSTS["aws"]["ecs_fargate_vcpu"]) + \
               (ecs_memory_gb * ecs_hours * COSTS["aws"]["ecs_fargate_memory"])
    
    ecr_cost = ecr_storage_gb * COSTS["aws"]["ecr_storage"]
    
    cloudwatch_cost = (cloudwatch_logs_gb * COSTS["aws"]["cloudwatch_logs"]) + \
                      (cloudwatch_storage_gb * COSTS["aws"]["cloudwatch_storage"])
    
    secrets_cost = secrets_count * COSTS["aws"]["secrets_manager"]
    
    alb_cost = (alb_hours * COSTS["aws"]["alb"]) + \
               (alb_lcu_hours * COSTS["aws"]["alb_lcu"])
    
    return {
        "s3_storage_gb": s3_storage_gb,
        "s3_requests": s3_requests,
        "s3_transfer_gb": s3_transfer_gb,
        "s3_cost_usd": round(s3_cost, 2),
        "ecs_vcpu": ecs_vcpu,
        "ecs_memory_gb": ecs_memory_gb,
        "ecs_hours": ecs_hours,
        "ecs_cost_usd": round(ecs_cost, 2),
        "ecr_storage_gb": ecr_storage_gb,
        "ecr_cost_usd": round(ecr_cost, 2),
        "cloudwatch_logs_gb": cloudwatch_logs_gb,
        "cloudwatch_storage_gb": cloudwatch_storage_gb,
        "cloudwatch_cost_usd": round(cloudwatch_cost, 2),
        "secrets_count": secrets_count,
        "secrets_cost_usd": round(secrets_cost, 2),
        "alb_hours": alb_hours,
        "alb_lcu_hours": alb_lcu_hours,
        "alb_cost_usd": round(alb_cost, 2),
        "total_aws_cost_usd": round(s3_cost + ecs_cost + ecr_cost + cloudwatch_cost + secrets_cost + alb_cost, 2),
    }


def generate_cost_analysis(
    scenarios: List[Dict[str, any]] = None,
    output_json: str = "data/reports/cost_analysis.json",
    output_csv: str = "data/reports/cost_analysis.csv",
) -> None:
    """Generate cost analysis for different scenarios.
    
    Args:
        scenarios: List of scenario dictionaries with parameters
        output_json: Path to save JSON report
        output_csv: Path to save CSV report
    """
    logger.info("Generating cost analysis")
    
    if scenarios is None:
        scenarios = [
            {
                "name": "Current Setup (Local)",
                "description": "Local development setup",
                "embedding_requests": 200,  # Initial embeddings
                "completion_requests": 0,
                "s3_storage_gb": 0.1,
                "s3_requests": 100,
                "ecs_hours": 0,
                "ecs_vcpu": 0,
                "ecs_memory_gb": 0,
            },
            {
                "name": "Small Scale (1K requests/day)",
                "description": "1,000 requests per day, ~30K/month",
                "embedding_requests": 200,  # Initial + occasional refresh
                "completion_requests": 0,
                "s3_storage_gb": 1.0,
                "s3_requests": 1000,
                "s3_transfer_gb": 0.5,
                "ecs_hours": 730,
                "ecs_vcpu": 1.0,
                "ecs_memory_gb": 2.0,
            },
            {
                "name": "Medium Scale (10K requests/day)",
                "description": "10,000 requests per day, ~300K/month",
                "embedding_requests": 200,
                "completion_requests": 0,
                "s3_storage_gb": 5.0,
                "s3_requests": 10000,
                "s3_transfer_gb": 5.0,
                "ecs_hours": 730,
                "ecs_vcpu": 2.0,
                "ecs_memory_gb": 4.0,
                "cloudwatch_logs_gb": 10.0,
                "cloudwatch_storage_gb": 5.0,
            },
            {
                "name": "Large Scale (100K requests/day)",
                "description": "100,000 requests per day, ~3M/month",
                "embedding_requests": 200,
                "completion_requests": 0,
                "s3_storage_gb": 20.0,
                "s3_requests": 100000,
                "s3_transfer_gb": 50.0,
                "ecs_hours": 730,
                "ecs_vcpu": 4.0,
                "ecs_memory_gb": 8.0,
                "cloudwatch_logs_gb": 100.0,
                "cloudwatch_storage_gb": 50.0,
                "alb_lcu_hours": 1000,
            },
        ]
    
    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    
    results = []
    for scenario in scenarios:
        openai_costs = calculate_openai_costs(
            embedding_requests=scenario.get("embedding_requests", 0),
            completion_requests=scenario.get("completion_requests", 0),
        )
        
        aws_costs = calculate_aws_costs(
            s3_storage_gb=scenario.get("s3_storage_gb", 1.0),
            s3_requests=scenario.get("s3_requests", 1000),
            s3_transfer_gb=scenario.get("s3_transfer_gb", 0.1),
            ecs_vcpu=scenario.get("ecs_vcpu", 1.0),
            ecs_memory_gb=scenario.get("ecs_memory_gb", 2.0),
            ecs_hours=scenario.get("ecs_hours", 730),
            cloudwatch_logs_gb=scenario.get("cloudwatch_logs_gb", 1.0),
            cloudwatch_storage_gb=scenario.get("cloudwatch_storage_gb", 1.0),
            alb_lcu_hours=scenario.get("alb_lcu_hours", 100),
        )
        
        total_cost = openai_costs["total_openai_cost_usd"] + aws_costs["total_aws_cost_usd"]
        
        result = {
            "scenario": scenario["name"],
            "description": scenario.get("description", ""),
            "generated_at": datetime.now().isoformat(),
            **openai_costs,
            **aws_costs,
            "total_cost_usd": round(total_cost, 2),
        }
        results.append(result)
    
    # Save JSON
    report = {
        "generated_at": datetime.now().isoformat(),
        "cost_constants": COSTS,
        "scenarios": results,
        "summary": {
            "min_cost": min(r["total_cost_usd"] for r in results),
            "max_cost": max(r["total_cost_usd"] for r in results),
            "avg_cost": sum(r["total_cost_usd"] for r in results) / len(results),
        },
    }
    
    with open(output_json, "w") as f:
        json.dump(report, f, indent=2)
    
    logger.info("Cost analysis JSON saved", file=output_json)
    
    # Save CSV
    if results:
        fieldnames = list(results[0].keys())
        with open(output_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        
        logger.info("Cost analysis CSV saved", file=output_csv)
    
    print(f"\nCost Analysis Summary:")
    print(f"Scenarios analyzed: {len(results)}")
    print(f"Min cost: ${min(r['total_cost_usd'] for r in results):.2f}/month")
    print(f"Max cost: ${max(r['total_cost_usd'] for r in results):.2f}/month")
    print(f"Reports saved to: {output_json} and {output_csv}")


def main():
    """Main function to generate cost analysis."""
    generate_cost_analysis()


if __name__ == "__main__":
    main()

