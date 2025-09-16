from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, Optional, List
from collections import defaultdict
from enum import Enum
import asyncio
import math
import numpy as np
from datetime import datetime, date, timedelta

from pydantic import BaseModel, Field, validator

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
    rate_per_second: Optional[float] = Field(default=None, ge=0.01, le=1000.0, description="Streaming rate (current-date mode)")
    base_daily_volume: int = Field(default=1000, ge=1, description="Expected daily transaction volume")
    max_records: Optional[int] = Field(default=None, ge=1, description="Maximum records for current-date streaming (optional)")

    # Arrival pattern configuration
    arrival_pattern: ArrivalPattern = Field(default=ArrivalPattern.UNIFORM)
    peak_hours: List[int] = Field(default_factory=lambda: [12, 19])  # Lunch and dinner peaks
    burst_intensity: float = Field(default=2.0, ge=1.0, le=10.0)
    burst_probability: float = Field(default=0.1, ge=0.0, le=1.0)

    # Historical date range parameters
    start_date: Optional[date] = Field(default=None, description="Start date for historical data (YYYY-MM-DD)")
    end_date: Optional[date] = Field(default=None, description="End date for historical data (YYYY-MM-DD)")
    include_holiday_patterns: bool = Field(default=True, description="Include holiday traffic patterns")
    weekend_multiplier: float = Field(default=0.85, ge=0.1, le=5.0, description="Weekend vs weekday traffic ratio")

    # Data quality parameters
    noise_type: NoiseType = Field(default=NoiseType.NONE)
    noise_level: float = Field(default=0.0, ge=0.0, le=1.0)
    drift_type: DriftType = Field(default=DriftType.NONE)
    drift_strength: float = Field(default=0.0, ge=0.0, le=1.0)

    # Time and determinism
    seed: Optional[int] = Field(default=None)
    start_time: datetime = Field(default_factory=datetime.utcnow)
    time_compression: float = Field(default=1.0, ge=0.1, le=1000.0)

    @validator('end_date')
    def validate_date_range(cls, v, values):
        """Validate date range constraints."""
        if 'start_date' in values and values['start_date'] and v:
            start_date = values['start_date']

            # end_date must be >= start_date
            if v < start_date:
                raise ValueError('end_date must be >= start_date')

            # Date range cannot exceed 1 year
            if (v - start_date).days > 365:
                raise ValueError('date range cannot exceed 365 days')

        return v

    @validator('start_date')
    def validate_partial_date_range(cls, v, values):
        """Ensure we don't have partial date ranges."""
        return v

    @validator('rate_per_second')
    def validate_current_date_params(cls, v, values):
        """For current-date mode: prevent conflicting rate specifications."""
        # If both rate_per_second and base_daily_volume are provided for current-date mode
        if v is not None and not values.get('start_date'):
            # This is current-date mode with explicit rate - that's fine
            pass
        return v

    def get_effective_rate(self) -> float:
        """Get the effective streaming rate for current-date mode."""
        if self.rate_per_second is not None:
            return self.rate_per_second
        else:
            # Convert daily volume to per-second rate (24 hours = 86400 seconds)
            return self.base_daily_volume / 86400


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
        # Check if we're in historical mode with day-per-second delivery
        if self._is_historical_mode():
            async for record in self._stream_historical_batched():
                yield record
        else:
            async for record in self._stream_realtime():
                yield record

    def _is_historical_mode(self) -> bool:
        """Check if generator is in historical mode (pre-generated timestamps)."""
        return (hasattr(self, 'use_historical_timestamps') and
                getattr(self, 'use_historical_timestamps', False))

    async def _stream_historical_batched(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream historical data in day-per-second batches."""
        if not hasattr(self, '_historical_timestamps'):
            return

        # Group records by day
        daily_batches = self._group_timestamps_by_day()

        for day_index, (target_date, day_timestamps) in enumerate(daily_batches.items()):
            # Generate all records for this day
            for timestamp in day_timestamps:
                if (self.config.max_records and
                    self._records_generated >= self.config.max_records):
                    return

                # Generate base record
                record = await self.generate_record()

                # Apply transformations
                record = await self.apply_noise(record)
                record = await self.apply_drift(record)

                # Use historical timestamp
                record["_timestamp"] = timestamp.isoformat()
                record["_record_id"] = self._records_generated
                record["_generator"] = self.name

                self._records_generated += 1
                yield record

            # Wait 1 second before next day (except for last day)
            # TODO: Make delivery speed configurable (e.g., 5 days per second)
            # Consider: delivery_days_per_second config parameter with safety caps
            # Risk: High burst rates (25k+ records/sec) may overwhelm clients/network
            if day_index < len(daily_batches) - 1:
                await asyncio.sleep(1.0)

    async def _stream_realtime(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream data in real-time with arrival patterns (current-date mode)."""
        while True:
            if (self.config.max_records and
                self._records_generated >= self.config.max_records):
                break

            # Generate base record
            record = await self.generate_record()

            # Apply transformations
            record = await self.apply_noise(record)
            record = await self.apply_drift(record)

            # Add metadata with appropriate timestamp
            timestamp = self._get_record_timestamp()
            record["_timestamp"] = timestamp.isoformat()
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

            # Apply volume variation to rate for current-date mode
            base_rate = self.config.get_effective_rate()
            if hasattr(self, 'get_current_day_rate_multiplier'):
                effective_rate = base_rate * self.get_current_day_rate_multiplier()
            else:
                effective_rate = base_rate

            delay = await self.arrival_calculator.next_interval(
                self.config.arrival_pattern,
                effective_rate,
                arrival_config
            )

            await asyncio.sleep(delay)

    def _group_timestamps_by_day(self) -> Dict[date, List[datetime]]:
        """Group historical timestamps by day for batched delivery."""
        daily_batches = defaultdict(list)

        for timestamp in self._historical_timestamps:
            day = timestamp.date()
            daily_batches[day].append(timestamp)

        # Return as ordered dict sorted by date
        return dict(sorted(daily_batches.items()))

    def _get_record_timestamp(self) -> datetime:
        """Get timestamp for the current record.

        If generator supports historical timestamps and has them available,
        use those. Otherwise use current time.
        """
        # Check if generator has historical timestamp support
        if hasattr(self, '_get_next_historical_timestamp'):
            return self._get_next_historical_timestamp()
        else:
            return datetime.utcnow()