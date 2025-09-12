from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, Optional, List
from enum import Enum
import asyncio
import math
import numpy as np
from datetime import datetime

from pydantic import BaseModel, Field

from .arrival_patterns import ArrivalPattern, ArrivalPatternCalculator


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
    # Core generation parameters
    rate_per_second: float = Field(default=1.0, ge=0.1, le=1000.0)
    total_records: Optional[int] = Field(default=None, ge=1)
    
    # Arrival pattern configuration
    arrival_pattern: ArrivalPattern = Field(default=ArrivalPattern.UNIFORM)
    peak_hours: List[int] = Field(default_factory=lambda: [12, 19])  # Lunch and dinner peaks
    burst_intensity: float = Field(default=2.0, ge=1.0, le=10.0)
    burst_probability: float = Field(default=0.1, ge=0.0, le=1.0)
    
    # Data quality parameters  
    noise_type: NoiseType = Field(default=NoiseType.NONE)
    noise_level: float = Field(default=0.0, ge=0.0, le=1.0)
    drift_type: DriftType = Field(default=DriftType.NONE)
    drift_strength: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Time and determinism
    seed: Optional[int] = Field(default=None)
    start_time: datetime = Field(default_factory=datetime.utcnow)
    time_compression: float = Field(default=1.0, ge=0.1, le=1000.0)
    
    # TODO: Future arrival pattern parameters
    # weekend_multiplier: float = Field(default=0.7, ge=0.1, le=5.0)  # Weekend vs weekday traffic
    # seasonal_events: List[str] = Field(default_factory=list)        # ["black_friday", "christmas"]
    # timezone: str = Field(default="UTC")                            # For global e-commerce patterns


class BaseGenerator(ABC):
    def __init__(self, config: GeneratorConfig):
        self.config = config
        self._records_generated = 0
        
        # Initialize arrival pattern calculator
        self.arrival_calculator = ArrivalPatternCalculator(
            start_time=config.start_time,
            time_compression=config.time_compression
        )
        
    @property
    def name(self) -> str:
        return self.__class__.__name__
        
    @abstractmethod
    async def generate_record(self) -> Dict[str, Any]:
        pass
    
    async def apply_noise(self, record: Dict[str, Any]) -> Dict[str, Any]:
        if self.config.noise_type == NoiseType.NONE:
            return record
        
        # Apply noise to numerical fields only
        noisy_record = record.copy()
        
        for key, value in record.items():
            if isinstance(value, (int, float)) and not key.startswith('_'):
                noisy_record[key] = self._apply_noise_to_value(value, self.config.noise_type, self.config.noise_level)
        
        return noisy_record
    
    def _apply_noise_to_value(self, value: float, noise_type: NoiseType, noise_level: float) -> float:
        """Apply specific noise type to a numerical value."""
        
        if noise_type == NoiseType.GAUSSIAN:
            # Gaussian noise: value + N(0, σ) where σ = value * noise_level
            std_dev = abs(value) * noise_level
            noise = np.random.normal(0, std_dev)
            return value + noise
            
        elif noise_type == NoiseType.UNIFORM:
            # Uniform noise: value ± (value * noise_level * random[-1,1])
            max_noise = abs(value) * noise_level
            noise = np.random.uniform(-max_noise, max_noise)
            return value + noise
            
        elif noise_type == NoiseType.OUTLIERS:
            # Occasional outliers: 95% normal, 5% extreme values
            if np.random.random() < 0.05:
                # Create outlier: multiply by 2-5x
                multiplier = np.random.uniform(2.0, 5.0) * np.random.choice([-1, 1])
                return value * multiplier
            else:
                # Small gaussian noise for normal cases
                std_dev = abs(value) * (noise_level * 0.1)
                noise = np.random.normal(0, std_dev)
                return value + noise
        
        return value
    
    async def apply_drift(self, record: Dict[str, Any]) -> Dict[str, Any]:
        if self.config.drift_type == DriftType.NONE:
            return record
            
        # Calculate time elapsed since start (for drift calculation)
        time_elapsed = datetime.utcnow() - self.config.start_time
        time_factor = time_elapsed.total_seconds() / 3600.0  # Hours elapsed
        
        # Apply time compression
        compressed_time_factor = time_factor * self.config.time_compression
        
        # Apply drift to numerical fields
        drifted_record = record.copy()
        
        for key, value in record.items():
            if isinstance(value, (int, float)) and not key.startswith('_'):
                drifted_record[key] = self._apply_drift_to_value(
                    value, self.config.drift_type, self.config.drift_strength, compressed_time_factor
                )
        
        return drifted_record
    
    def _apply_drift_to_value(self, value: float, drift_type: DriftType, drift_strength: float, time_factor: float) -> float:
        """Apply specific drift pattern to a numerical value."""
        
        if drift_type == DriftType.LINEAR:
            # Linear drift: value increases/decreases steadily over time
            # Direction randomly chosen per value (some increase, some decrease)
            direction = 1 if hash(str(value)) % 2 == 0 else -1
            drift_amount = value * drift_strength * time_factor * direction * 0.1
            return value + drift_amount
            
        elif drift_type == DriftType.SEASONAL:
            # Seasonal drift: cyclical pattern (like holiday shopping)
            # Complete cycle every 24 compressed hours (1 year if compression = 365)
            cycle_position = (time_factor % 24) / 24 * 2 * math.pi
            seasonal_factor = math.sin(cycle_position) * drift_strength
            return value * (1 + seasonal_factor)
            
        elif drift_type == DriftType.SUDDEN:
            # Sudden drift: step change after certain time
            # Change occurs at 25% of generation time
            sudden_threshold = 6.0  # 6 hours compressed time
            if time_factor > sudden_threshold:
                direction = 1 if hash(str(value)) % 2 == 0 else -1
                sudden_change = value * drift_strength * direction
                return value + sudden_change
            else:
                return value
                
        elif drift_type == DriftType.GRADUAL:
            # Gradual drift: exponential change that levels off
            # Approaches drift_strength as asymptote
            growth_rate = 0.1  # How quickly it approaches the limit
            drift_factor = drift_strength * (1 - math.exp(-growth_rate * time_factor))
            direction = 1 if hash(str(value)) % 2 == 0 else -1
            return value * (1 + drift_factor * direction)
        
        return value
    
    async def stream(self) -> AsyncGenerator[Dict[str, Any], None]:        
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
            
            # Calculate next arrival time based on pattern
            arrival_config = {
                'peak_hours': self.config.peak_hours,
                'burst_intensity': self.config.burst_intensity,
                'burst_probability': self.config.burst_probability
            }
            
            delay = await self.arrival_calculator.next_interval(
                self.config.arrival_pattern,
                self.config.rate_per_second,
                arrival_config
            )
            
            await asyncio.sleep(delay)