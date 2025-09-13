"""
Unit tests for arrival pattern implementations.

Tests all arrival patterns including uniform, poisson, NHPP, and burst patterns
with various configurations and time compression scenarios.
"""

import asyncio
import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch

from simtom.core.arrival_patterns import (
    ArrivalPattern, 
    ArrivalPatternCalculator
)


class TestArrivalPatternCalculator:
    """Test the arrival pattern calculator with various patterns."""
    
    @pytest.fixture
    def calculator(self):
        """Create a basic arrival pattern calculator."""
        start_time = datetime(2025, 1, 1, 12, 0, 0)  # Noon start
        return ArrivalPatternCalculator(start_time=start_time, time_compression=1.0)
    
    @pytest.fixture
    def compressed_calculator(self):
        """Create calculator with time compression for daily patterns."""
        start_time = datetime(2025, 1, 1, 12, 0, 0)  # Noon start
        return ArrivalPatternCalculator(start_time=start_time, time_compression=24.0)
    
    @pytest.mark.asyncio
    async def test_uniform_pattern_fixed_intervals(self, calculator):
        """Test uniform pattern produces exact fixed intervals."""
        base_rate = 2.0
        config = {}
        
        # Generate multiple intervals
        intervals = []
        for _ in range(5):
            interval = await calculator.next_interval(
                ArrivalPattern.UNIFORM, base_rate, config
            )
            intervals.append(interval)
        
        # All intervals should be exactly 1/rate
        expected_interval = 1.0 / base_rate
        for interval in intervals:
            assert abs(interval - expected_interval) < 1e-10
    
    @pytest.mark.asyncio
    async def test_poisson_pattern_random_intervals(self, calculator):
        """Test Poisson pattern produces variable intervals with correct average."""
        base_rate = 4.0
        config = {}
        
        # Generate many intervals to test statistical properties
        intervals = []
        for _ in range(100):
            interval = await calculator.next_interval(
                ArrivalPattern.POISSON, base_rate, config
            )
            intervals.append(interval)
        
        # Check statistical properties
        mean_interval = np.mean(intervals)
        expected_mean = 1.0 / base_rate
        
        # Mean should be close to expected (within 20% for 100 samples)
        assert abs(mean_interval - expected_mean) < expected_mean * 0.2
        
        # Standard deviation should be approximately equal to mean (exponential property)
        std_interval = np.std(intervals)
        assert abs(std_interval - expected_mean) < expected_mean * 0.3
        
        # All intervals should be positive
        assert all(interval > 0 for interval in intervals)
    
    def test_daily_rate_multiplier_peak_hours(self, calculator):
        """Test daily rate multiplier handles peak hours correctly."""
        peak_hours = [12, 19]  # Lunch and dinner
        
        # Peak hours should have highest multiplier
        assert calculator.get_daily_rate_multiplier(12, peak_hours) == 5.0
        assert calculator.get_daily_rate_multiplier(19, peak_hours) == 5.0
        
        # Night hours should have lowest multiplier
        assert calculator.get_daily_rate_multiplier(3, peak_hours) == 0.2
        assert calculator.get_daily_rate_multiplier(5, peak_hours) == 0.2
        
        # Morning rush should be elevated
        assert calculator.get_daily_rate_multiplier(9, peak_hours) == 2.0
        
        # Evening rush should be high
        assert calculator.get_daily_rate_multiplier(20, peak_hours) == 4.0
        
        # Normal hours should be baseline
        assert calculator.get_daily_rate_multiplier(16, peak_hours) == 1.0
        assert calculator.get_daily_rate_multiplier(18, peak_hours) == 1.0
    
    def test_daily_rate_multiplier_custom_peaks(self, calculator):
        """Test daily rate multiplier with custom peak hours."""
        custom_peaks = [10, 14, 22]  # Custom business hours
        
        # All custom peaks should have highest priority
        for peak_hour in custom_peaks:
            assert calculator.get_daily_rate_multiplier(peak_hour, custom_peaks) == 5.0
        
        # Standard patterns should still apply for non-peak hours
        assert calculator.get_daily_rate_multiplier(4, custom_peaks) == 0.2  # Night lull
    
    @pytest.mark.asyncio 
    async def test_nhpp_pattern_time_varying_rates(self, compressed_calculator):
        """Test NHPP pattern varies rates based on simulated time."""
        base_rate = 2.0
        config = {'peak_hours': [15]}  # 3pm peak
        
        # Mock current time to be during peak hour (3pm)
        peak_time = datetime(2025, 1, 1, 15, 0, 0)
        with patch.object(compressed_calculator, 'get_simulated_time', return_value=peak_time):
            # Generate intervals during peak time
            peak_intervals = []
            for _ in range(20):
                interval = await compressed_calculator.next_interval(
                    ArrivalPattern.NHPP, base_rate, config
                )
                peak_intervals.append(interval)
        
        # Mock current time to be during normal hour (4pm) 
        normal_time = datetime(2025, 1, 1, 16, 0, 0)
        with patch.object(compressed_calculator, 'get_simulated_time', return_value=normal_time):
            # Generate intervals during normal time
            normal_intervals = []
            for _ in range(20):
                interval = await compressed_calculator.next_interval(
                    ArrivalPattern.NHPP, base_rate, config
                )
                normal_intervals.append(interval)
        
        # Peak intervals should be generally shorter than normal intervals
        peak_mean = np.mean(peak_intervals)
        normal_mean = np.mean(normal_intervals)
        
        # Peak rate is 5x higher, so intervals should be ~5x shorter
        assert peak_mean < normal_mean
        assert normal_mean / peak_mean > 2.0  # At least 2x difference
    
    @pytest.mark.asyncio
    async def test_burst_pattern_intensity_effect(self, calculator):
        """Test burst pattern creates faster intervals during bursts."""
        base_rate = 1.0
        high_burst_config = {
            'burst_intensity': 5.0,
            'burst_probability': 1.0  # Always burst
        }
        normal_config = {
            'burst_intensity': 1.0, 
            'burst_probability': 0.0  # Never burst
        }
        
        # Generate intervals with high burst probability
        burst_intervals = []
        for _ in range(20):
            interval = await calculator.next_interval(
                ArrivalPattern.BURST, base_rate, high_burst_config
            )
            burst_intervals.append(interval)
        
        # Generate intervals with no burst
        normal_intervals = []
        for _ in range(20):
            interval = await calculator.next_interval(
                ArrivalPattern.BURST, base_rate, normal_config
            )
            normal_intervals.append(interval)
        
        # Burst intervals should be generally shorter
        burst_mean = np.mean(burst_intervals) 
        normal_mean = np.mean(normal_intervals)
        
        assert burst_mean < normal_mean
        assert normal_mean / burst_mean > 2.0  # Significant difference
    
    @pytest.mark.asyncio
    async def test_burst_pattern_probability_effect(self, calculator):
        """Test burst probability affects frequency of fast intervals."""
        base_rate = 2.0
        
        # High burst probability should produce more short intervals
        high_prob_config = {
            'burst_intensity': 3.0,
            'burst_probability': 0.8
        }
        
        # Low burst probability should produce more normal intervals  
        low_prob_config = {
            'burst_intensity': 3.0,
            'burst_probability': 0.1
        }
        
        # Generate samples for both configurations
        high_prob_intervals = []
        low_prob_intervals = []
        
        for _ in range(50):
            interval = await calculator.next_interval(
                ArrivalPattern.BURST, base_rate, high_prob_config
            )
            high_prob_intervals.append(interval)
            
            interval = await calculator.next_interval(
                ArrivalPattern.BURST, base_rate, low_prob_config
            )
            low_prob_intervals.append(interval)
        
        # High probability should have lower mean interval
        high_prob_mean = np.mean(high_prob_intervals)
        low_prob_mean = np.mean(low_prob_intervals)
        
        assert high_prob_mean < low_prob_mean
    
    @pytest.mark.asyncio
    async def test_unknown_pattern_fallback(self, calculator):
        """Test unknown patterns fall back to uniform."""
        base_rate = 3.0
        config = {}
        
        # Use invalid pattern (should fallback to uniform)
        interval = await calculator.next_interval(
            "invalid_pattern", base_rate, config
        )
        
        # Should produce uniform interval
        expected_interval = 1.0 / base_rate
        assert abs(interval - expected_interval) < 1e-10
    
    def test_simulated_time_calculation(self, calculator):
        """Test simulated time calculation with compression."""
        # Mock current time to be 1 hour after start
        future_time = calculator.start_time + timedelta(hours=1)
        
        with patch('simtom.core.arrival_patterns.datetime') as mock_datetime:
            mock_datetime.now.return_value = future_time
            
            # With no compression, should be 1 hour later
            calculator.time_compression = 1.0
            sim_time = calculator.get_simulated_time()
            assert sim_time == future_time
            
            # With 24x compression, should be 24 hours later  
            calculator.time_compression = 24.0
            sim_time = calculator.get_simulated_time()
            expected_time = calculator.start_time + timedelta(hours=24)
            assert sim_time == expected_time
    
    @pytest.mark.asyncio
    async def test_all_patterns_positive_intervals(self, calculator):
        """Test all patterns produce positive intervals."""
        patterns = [
            ArrivalPattern.UNIFORM,
            ArrivalPattern.POISSON, 
            ArrivalPattern.NHPP,
            ArrivalPattern.BURST
        ]
        
        base_rate = 5.0
        config = {
            'peak_hours': [12],
            'burst_intensity': 2.0,
            'burst_probability': 0.5
        }
        
        for pattern in patterns:
            intervals = []
            for _ in range(10):
                interval = await calculator.next_interval(pattern, base_rate, config)
                intervals.append(interval)
            
            # All intervals must be positive
            assert all(interval > 0 for interval in intervals), f"Pattern {pattern} produced non-positive interval"
            
            # No intervals should be unreasonably large (> 10 seconds at 5/sec rate)
            assert all(interval < 10.0 for interval in intervals), f"Pattern {pattern} produced unreasonably large interval"


# TODO: Future tests for enhanced patterns
# class TestFuturePatterns:
#     """Tests for future arrival pattern implementations."""
#     
#     @pytest.mark.asyncio
#     async def test_weekly_pattern_weekend_effect(self, calculator):
#         """Test weekly patterns with weekend vs weekday differences."""
#         pass
#     
#     @pytest.mark.asyncio  
#     async def test_seasonal_pattern_holiday_spikes(self, calculator):
#         """Test seasonal patterns for holidays and events."""
#         pass
#     
#     @pytest.mark.asyncio
#     async def test_mixed_pattern_combinations(self, calculator):
#         """Test combination of multiple patterns."""
#         pass