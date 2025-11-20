from typing import Dict, Any
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    checks: Dict[str, Any]

