from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, Optional
from enum import Enum
import asyncio
from datetime import datetime

from pydantic import BaseModel, Field


class NoiseType(str, Enum):
    NONE = "none"
    GAUSSIAN = "gaussian" 
    UNIFORM = "uniform"
    OUTLIERS = "outliers"


class DriftType(str, Enum):
    NONE = "none"
    LINEAR = "linear"
    SEASONAL = "seasonal"
    SUDDEN = "sudden"
    GRADUAL = "gradual"


class GeneratorConfig(BaseModel):
    rate_per_second: float = Field(default=1.0, ge=0.1, le=1000.0)
    total_records: Optional[int] = Field(default=None, ge=1)
    noise_type: NoiseType = Field(default=NoiseType.NONE)
    noise_level: float = Field(default=0.0, ge=0.0, le=1.0)
    drift_type: DriftType = Field(default=DriftType.NONE)
    drift_strength: float = Field(default=0.0, ge=0.0, le=1.0)
    seed: Optional[int] = Field(default=None)
    start_time: datetime = Field(default_factory=datetime.utcnow)
    time_compression: float = Field(default=1.0, ge=0.1, le=1000.0)


class BaseGenerator(ABC):
    def __init__(self, config: GeneratorConfig):
        self.config = config
        self._records_generated = 0
        
    @property
    def name(self) -> str:
        return self.__class__.__name__
        
    @abstractmethod
    async def generate_record(self) -> Dict[str, Any]:
        pass
    
    async def apply_noise(self, record: Dict[str, Any]) -> Dict[str, Any]:
        if self.config.noise_type == NoiseType.NONE:
            return record
        
        # Apply noise based on configuration
        # Implementation will vary based on noise type
        return record
    
    async def apply_drift(self, record: Dict[str, Any]) -> Dict[str, Any]:
        if self.config.drift_type == DriftType.NONE:
            return record
            
        # Apply drift based on configuration and time elapsed
        # Implementation will vary based on drift type
        return record
    
    async def stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        delay = 1.0 / self.config.rate_per_second
        
        while True:
            if (self.config.total_records and 
                self._records_generated >= self.config.total_records):
                break
                
            # Generate base record
            record = await self.generate_record()
            
            # Apply transformations
            record = await self.apply_noise(record)
            record = await self.apply_drift(record)
            
            # Add metadata
            record["_timestamp"] = datetime.utcnow().isoformat()
            record["_record_id"] = self._records_generated
            record["_generator"] = self.name
            
            self._records_generated += 1
            yield record
            
            await asyncio.sleep(delay)