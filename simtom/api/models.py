from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from ..core.generator import GeneratorConfig, NoiseType, DriftType


class GeneratorRequest(BaseModel):
    generator_name: str = Field(..., description="Name of the generator to use")
    config: GeneratorConfig = Field(..., description="Generator configuration")


class GeneratorInfo(BaseModel):
    name: str
    description: Optional[str] = None
    config_schema: Dict[str, Any]


class StreamResponse(BaseModel):
    status: str
    message: str
    stream_id: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "0.1.0"
    generators_available: int = 0