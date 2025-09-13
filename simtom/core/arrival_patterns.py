"""
Arrival pattern implementations for realistic traffic simulation.

This module provides different arrival patterns for simulating user traffic:
- Uniform: Fixed intervals (current behavior)
- Poisson: Random intervals with constant average rate
- NHPP: Non-homogeneous Poisson with time-varying rates
- Burst: Flash sale / event-driven traffic spikes

Current implementation supports daily cycles with configurable time compression.

TODO: Future enhancements
- Weekly patterns (weekend vs weekday traffic)
- Seasonal patterns (Black Friday, Christmas, etc.)
- Multi-timezone support for global e-commerce
- Custom pattern definition via configuration files
"""

import asyncio
import math
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, List
import random
import numpy as np


class ArrivalPattern(str, Enum):
    """Available arrival patterns for traffic simulation."""
    UNIFORM = "uniform"      # Fixed intervals (backward compatible)
    POISSON = "poisson"      # Random intervals, constant average rate
    NHPP = "nhpp"           # Non-homogeneous Poisson with daily patterns
    BURST = "burst"         # Flash sale / event-driven spikes
    
    # TODO: Future patterns
    # WEEKLY = "weekly"      # Weekly cycles (weekend peaks)
    # SEASONAL = "seasonal"  # Annual cycles (holidays, seasons)
    # MIXED = "mixed"        # Combination of multiple patterns


class ArrivalPatternCalculator:
    """
    Calculates inter-arrival times based on specified patterns.
    
    Supports daily cycle simulation with configurable time compression.
    The time_compression parameter determines how much real time represents
    in the simulation (e.g., 24.0 means 1 hour real = 1 day simulated).
    """
    
    def __init__(self, start_time: datetime, time_compression: float = 1.0):
        """
        Initialize arrival pattern calculator.
        
        Args:
            start_time: Simulation start time
            time_compression: Time acceleration factor (1.0 = real time)
        """
        self.start_time = start_time
        self.time_compression = time_compression
        self.records_generated = 0
        
        # TODO: Add support for timezone-aware calculations
        # TODO: Add configuration for different daily patterns by region
    
    def get_simulated_time(self) -> datetime:
        """
        Get current simulated time based on compression factor.
        
        Returns:
            Current time in the compressed simulation timeline
        """
        elapsed_real = (datetime.now() - self.start_time).total_seconds()
        elapsed_simulated = elapsed_real * self.time_compression
        return self.start_time + timedelta(seconds=elapsed_simulated)
    
    def get_daily_rate_multiplier(self, hour: int, peak_hours: List[int]) -> float:
        """
        Calculate rate multiplier based on hour of day.
        
        Creates realistic daily traffic patterns with:
        - Low traffic: 2-6 AM (0.2x base rate)
        - Morning peak: 8-10 AM (2.0x base rate)
        - Lunch peak: 12-14 PM (3.0x base rate)  
        - Evening peak: 19-21 PM (4.0x base rate)
        - Custom peaks: User-specified hours (5.0x base rate)
        
        Args:
            hour: Hour of day (0-23)
            peak_hours: List of custom peak hours
            
        Returns:
            Rate multiplier (0.2 to 5.0)
        """
        # Custom peak hours get highest priority
        if hour in peak_hours:
            return 5.0
            
        # Pre-defined daily patterns
        if 2 <= hour <= 6:      # Night lull
            return 0.2
        elif 8 <= hour <= 10:   # Morning commute
            return 2.0
        elif 12 <= hour <= 14:  # Lunch rush
            return 3.0
        elif 19 <= hour <= 21:  # Evening peak
            return 4.0
        else:                   # Normal hours
            return 1.0
    
    async def next_interval(
        self, 
        pattern: ArrivalPattern, 
        base_rate: float,
        config: Dict[str, Any]
    ) -> float:
        """
        Calculate next inter-arrival time based on pattern.
        
        Args:
            pattern: Arrival pattern type
            base_rate: Base arrivals per second
            config: Pattern-specific configuration
            
        Returns:
            Seconds to wait until next arrival
        """
        self.records_generated += 1
        
        if pattern == ArrivalPattern.UNIFORM:
            return await self._uniform_interval(base_rate)
            
        elif pattern == ArrivalPattern.POISSON:
            return await self._poisson_interval(base_rate)
            
        elif pattern == ArrivalPattern.NHPP:
            return await self._nhpp_interval(base_rate, config)
            
        elif pattern == ArrivalPattern.BURST:
            return await self._burst_interval(base_rate, config)
            
        else:
            # Fallback to uniform for unknown patterns
            return await self._uniform_interval(base_rate)
    
    async def _uniform_interval(self, base_rate: float) -> float:
        """Uniform arrivals - fixed intervals (backward compatible)."""
        return 1.0 / base_rate
    
    async def _poisson_interval(self, base_rate: float) -> float:
        """Poisson arrivals - exponentially distributed intervals."""
        return np.random.exponential(1.0 / base_rate)
    
    async def _nhpp_interval(self, base_rate: float, config: Dict[str, Any]) -> float:
        """
        Non-homogeneous Poisson process with daily patterns.
        
        Rate varies based on time of day using daily multipliers.
        """
        sim_time = self.get_simulated_time()
        peak_hours = config.get('peak_hours', [12, 19])
        
        # Calculate time-varying rate
        daily_multiplier = self.get_daily_rate_multiplier(sim_time.hour, peak_hours)
        current_rate = base_rate * daily_multiplier
        
        # Generate Poisson interval with current rate
        return np.random.exponential(1.0 / current_rate)
    
    async def _burst_interval(self, base_rate: float, config: Dict[str, Any]) -> float:
        """
        Burst pattern for flash sales and events.
        
        Creates clusters of rapid arrivals followed by quiet periods.
        """
        burst_intensity = config.get('burst_intensity', 2.0)
        burst_probability = config.get('burst_probability', 0.1)
        
        # Decide if we're in a burst or normal period
        if random.random() < burst_probability:
            # Burst period - much higher rate
            burst_rate = base_rate * burst_intensity
            return np.random.exponential(1.0 / burst_rate)
        else:
            # Normal period - slightly lower base rate to compensate
            normal_rate = base_rate * 0.8
            return np.random.exponential(1.0 / normal_rate)

    # TODO: Future pattern implementations
    
    # async def _weekly_interval(self, base_rate: float, config: Dict[str, Any]) -> float:
    #     """Weekly patterns with weekend vs weekday differences."""
    #     pass
    
    # async def _seasonal_interval(self, base_rate: float, config: Dict[str, Any]) -> float:
    #     """Seasonal patterns for holidays and events."""
    #     pass
    
    # async def _mixed_interval(self, base_rate: float, config: Dict[str, Any]) -> float:
    #     """Combination of multiple patterns."""
    #     pass