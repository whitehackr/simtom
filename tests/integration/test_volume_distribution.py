"""End-to-end tests for statistical volume distribution system.

Tests the complete 4-factor statistical model (DOW + WOM + MOY + Special Events + Noise)
across both historical and current-date generation modes.
"""

import pytest
from datetime import date, datetime, timedelta
import collections
import statistics
from typing import List, Dict

from simtom.generators.ecommerce.bnpl import BNPLConfig, BNPLGenerator


class TestHistoricalVolumeDistribution:
    """Test realistic daily volume variation in historical mode."""

    @pytest.mark.asyncio
    async def test_black_friday_volume_spike(self):
        """Black Friday should generate significantly more records than baseline."""
        config = BNPLConfig(
            base_daily_volume=100,
            start_date=date(2024, 11, 28),  # Thursday before Black Friday
            end_date=date(2024, 11, 30),    # Saturday after
            volume_variation_enabled=True,
            seed=42
        )

        generator = BNPLGenerator(config)
        timestamps = generator._historical_timestamps
        date_counts = collections.Counter([ts.date() for ts in timestamps])

        # Black Friday should have significant boost
        black_friday = date(2024, 11, 29)
        thursday = date(2024, 11, 28)
        saturday = date(2024, 11, 30)

        bf_count = date_counts[black_friday]
        thu_count = date_counts[thursday]
        sat_count = date_counts[saturday]

        # Black Friday should be 1.5x+ higher than surrounding days
        assert bf_count > thu_count * 1.5, f"Black Friday ({bf_count}) should be 1.5x+ Thursday ({thu_count})"
        assert bf_count > sat_count * 1.5, f"Black Friday ({bf_count}) should be 1.5x+ Saturday ({sat_count})"

        # Expected multiplier: Friday(1.25) × November(1.1) × BlackFriday(1.6) = 2.2x
        expected_range = (180, 250)  # 100 × 2.2 ± noise
        assert expected_range[0] <= bf_count <= expected_range[1], f"Black Friday count {bf_count} outside expected range {expected_range}"

    @pytest.mark.asyncio
    async def test_christmas_volume_suppression(self):
        """Christmas Day should generate minimal records."""
        config = BNPLConfig(
            base_daily_volume=100,
            start_date=date(2024, 12, 24),  # Christmas Eve
            end_date=date(2024, 12, 26),    # Day after Christmas
            volume_variation_enabled=True,
            seed=42
        )

        generator = BNPLGenerator(config)
        timestamps = generator._historical_timestamps
        date_counts = collections.Counter([ts.date() for ts in timestamps])

        christmas_day = date(2024, 12, 25)
        christmas_eve = date(2024, 12, 24)
        boxing_day = date(2024, 12, 26)

        xmas_count = date_counts[christmas_day]
        eve_count = date_counts[christmas_eve]
        boxing_count = date_counts[boxing_day]

        # Christmas Day should be dramatically lower
        assert xmas_count < eve_count * 0.5, f"Christmas Day ({xmas_count}) should be <50% of Christmas Eve ({eve_count})"
        assert xmas_count < boxing_count * 0.5, f"Christmas Day ({xmas_count}) should be <50% of Boxing Day ({boxing_count})"

        # Expected: Wednesday(1.05) × December(1.2) × Christmas(0.1) × Week3(1.1) = ~0.14x
        expected_range = (8, 20)  # Very low volume
        assert expected_range[0] <= xmas_count <= expected_range[1], f"Christmas count {xmas_count} outside expected range {expected_range}"

    @pytest.mark.asyncio
    async def test_weekend_reduction(self):
        """Weekends should consistently show reduced volume."""
        config = BNPLConfig(
            base_daily_volume=100,
            start_date=date(2024, 6, 10),  # Monday
            end_date=date(2024, 6, 16),    # Sunday (full week)
            volume_variation_enabled=True,
            seed=42
        )

        generator = BNPLGenerator(config)
        timestamps = generator._historical_timestamps
        date_counts = collections.Counter([ts.date() for ts in timestamps])

        # Separate weekdays vs weekend
        weekday_counts = []
        weekend_counts = []

        for date_obj, count in date_counts.items():
            if date_obj.weekday() >= 5:  # Saturday/Sunday
                weekend_counts.append(count)
            else:  # Monday-Friday
                weekday_counts.append(count)

        avg_weekday = statistics.mean(weekday_counts)
        avg_weekend = statistics.mean(weekend_counts)

        # Weekend should be consistently lower
        assert avg_weekend < avg_weekday * 0.9, f"Weekend avg ({avg_weekend:.1f}) should be <90% of weekday avg ({avg_weekday:.1f})"

        # All weekend days should be individually lower than weekday average
        for weekend_count in weekend_counts:
            assert weekend_count < avg_weekday, f"Weekend day ({weekend_count}) should be < weekday average ({avg_weekday:.1f})"

    @pytest.mark.asyncio
    async def test_january_post_holiday_low(self):
        """January should show post-holiday volume reduction."""
        config = BNPLConfig(
            base_daily_volume=100,
            start_date=date(2024, 1, 8),   # Skip New Year effects
            end_date=date(2024, 1, 14),    # Mid-January week
            volume_variation_enabled=True,
            seed=42
        )

        generator = BNPLGenerator(config)
        timestamps = generator._historical_timestamps
        date_counts = collections.Counter([ts.date() for ts in timestamps])

        total_records = sum(date_counts.values())
        days = len(date_counts)
        daily_average = total_records / days

        # January should average ~75% of baseline (0.75 month multiplier)
        expected_range = (65, 85)  # 75 ± noise
        assert expected_range[0] <= daily_average <= expected_range[1], f"January average {daily_average:.1f} outside expected range {expected_range}"

    @pytest.mark.asyncio
    async def test_paycheck_cycle_effects(self):
        """First and third weeks should show higher volume (paycheck cycles)."""
        config = BNPLConfig(
            base_daily_volume=100,
            start_date=date(2024, 4, 1),   # April (neutral month)
            end_date=date(2024, 4, 30),    # Full month
            volume_variation_enabled=True,
            seed=42
        )

        generator = BNPLGenerator(config)
        timestamps = generator._historical_timestamps
        date_counts = collections.Counter([ts.date() for ts in timestamps])

        # Group by week of month
        week_totals = {1: 0, 2: 0, 3: 0, 4: 0}
        week_days = {1: 0, 2: 0, 3: 0, 4: 0}

        for date_obj, count in date_counts.items():
            day = date_obj.day
            if day <= 7:
                week = 1
            elif day <= 14:
                week = 2
            elif day <= 21:
                week = 3
            else:
                week = 4

            week_totals[week] += count
            week_days[week] += 1

        # Calculate averages
        week_avgs = {week: week_totals[week] / week_days[week] for week in week_totals}

        # Weeks 1 and 3 should be higher than weeks 2 and 4
        assert week_avgs[1] > week_avgs[2], f"Week 1 avg ({week_avgs[1]:.1f}) should be > Week 2 ({week_avgs[2]:.1f})"
        assert week_avgs[3] > week_avgs[2], f"Week 3 avg ({week_avgs[3]:.1f}) should be > Week 2 ({week_avgs[2]:.1f})"
        assert week_avgs[3] > week_avgs[4], f"Week 3 avg ({week_avgs[3]:.1f}) should be > Week 4 ({week_avgs[4]:.1f})"

    @pytest.mark.asyncio
    async def test_volume_variation_disabled(self):
        """When disabled, should return to uniform distribution."""
        config = BNPLConfig(
            base_daily_volume=100,
            start_date=date(2024, 11, 28),  # Include Black Friday
            end_date=date(2024, 11, 30),
            volume_variation_enabled=False,  # Disabled
            seed=42
        )

        generator = BNPLGenerator(config)
        timestamps = generator._historical_timestamps
        date_counts = collections.Counter([ts.date() for ts in timestamps])

        # All days should have similar counts (uniform distribution)
        counts = list(date_counts.values())
        min_count = min(counts)
        max_count = max(counts)

        # Should be relatively uniform (within 10%)
        variation = (max_count - min_count) / min_count
        assert variation < 0.15, f"With variation disabled, daily counts should be uniform. Variation: {variation:.2f}"


class TestCurrentDateModeRates:
    """Test dynamic rate adjustment in current-date mode."""

    def test_base_daily_volume_auto_calculation(self):
        """base_daily_volume should auto-calculate realistic streaming rate."""
        config = BNPLConfig(
            base_daily_volume=8640,  # Should give 0.1 rec/sec
            volume_variation_enabled=True,
            seed=42
        )

        generator = BNPLGenerator(config)
        base_rate = config.get_effective_rate()
        multiplier = generator.get_current_day_rate_multiplier()

        # Base rate should be base_daily_volume / 86400
        expected_base = 8640 / 86400  # = 0.1
        assert abs(base_rate - expected_base) < 0.001, f"Expected base rate {expected_base}, got {base_rate}"

        # Multiplier should vary based on current day factors
        assert 0.5 <= multiplier <= 3.0, f"Multiplier {multiplier:.3f} should be in reasonable range"

        final_rate = base_rate * multiplier
        assert final_rate > 0, f"Final rate {final_rate} should be positive"

    def test_explicit_rate_per_second(self):
        """rate_per_second should override auto-calculation."""
        config = BNPLConfig(
            base_daily_volume=1000,    # This should be ignored
            rate_per_second=0.5,       # This should be used
            volume_variation_enabled=True,
            seed=42
        )

        generator = BNPLGenerator(config)
        base_rate = config.get_effective_rate()
        multiplier = generator.get_current_day_rate_multiplier()

        # Should use explicit rate
        assert base_rate == 0.5, f"Expected explicit rate 0.5, got {base_rate}"

        # Multiplier should still apply
        final_rate = base_rate * multiplier
        assert final_rate != base_rate, f"Multiplier should affect final rate"

    def test_rate_multiplier_consistency(self):
        """Rate multiplier should be consistent for same day/seed."""
        config = BNPLConfig(
            base_daily_volume=1000,
            volume_variation_enabled=True,
            seed=42
        )

        generator = BNPLGenerator(config)

        # Multiple calls should return same multiplier
        mult1 = generator.get_current_day_rate_multiplier()
        mult2 = generator.get_current_day_rate_multiplier()
        mult3 = generator.get_current_day_rate_multiplier()

        assert mult1 == mult2 == mult3, f"Rate multiplier should be consistent: {mult1}, {mult2}, {mult3}"

    def test_volume_variation_disabled_current_mode(self):
        """Disabled variation should return 1.0 multiplier in current-date mode."""
        config = BNPLConfig(
            base_daily_volume=1000,
            volume_variation_enabled=False,  # Disabled
            seed=42
        )

        generator = BNPLGenerator(config)
        multiplier = generator.get_current_day_rate_multiplier()

        assert multiplier == 1.0, f"Disabled variation should give 1.0 multiplier, got {multiplier}"


class TestAPIValidationAndEdgeCases:
    """Test API validation and edge cases."""

    def test_historical_mode_ignores_rate_per_second(self):
        """Historical mode should work regardless of rate_per_second setting."""
        config = BNPLConfig(
            base_daily_volume=50,
            rate_per_second=999.0,  # This should be ignored
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 3),
            volume_variation_enabled=True,
            seed=42
        )

        generator = BNPLGenerator(config)
        timestamps = generator._historical_timestamps

        # Should generate based on base_daily_volume, not rate
        assert len(timestamps) > 100, f"Should generate realistic volumes, got {len(timestamps)}"

        # In historical mode, rate_per_second is used for streaming, not volume calculation
        streaming_rate = config.get_effective_rate()
        assert streaming_rate == 999.0, f"Historical mode should use explicit rate for streaming: {streaming_rate}"

    def test_zero_base_daily_volume_edge_case(self):
        """Very low base volume should still work."""
        config = BNPLConfig(
            base_daily_volume=1,  # Minimum
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 1),
            volume_variation_enabled=True,
            seed=42
        )

        generator = BNPLGenerator(config)
        timestamps = generator._historical_timestamps

        # Should generate at least 1 record per day
        assert len(timestamps) >= 1, f"Should generate at least 1 record, got {len(timestamps)}"

    def test_high_volume_scenario(self):
        """High volume scenario should work without overflow."""
        config = BNPLConfig(
            base_daily_volume=10000,  # High volume
            start_date=date(2024, 11, 29),  # Black Friday
            end_date=date(2024, 11, 29),
            volume_variation_enabled=True,
            seed=42
        )

        generator = BNPLGenerator(config)
        timestamps = generator._historical_timestamps

        # Should handle high volumes
        assert len(timestamps) > 15000, f"High volume Black Friday should generate 15K+ records, got {len(timestamps)}"
        assert len(timestamps) < 50000, f"Should not be unreasonably high, got {len(timestamps)}"

    def test_long_date_range(self):
        """Full year should complete without issues."""
        config = BNPLConfig(
            base_daily_volume=100,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            volume_variation_enabled=True,
            seed=42
        )

        generator = BNPLGenerator(config)
        timestamps = generator._historical_timestamps

        # Should generate reasonable total (with variation)
        days = 366  # 2024 is leap year
        expected_range = (25000, 45000)  # 100 * 366 ± seasonal variation
        assert expected_range[0] <= len(timestamps) <= expected_range[1], f"Year total {len(timestamps)} outside expected range {expected_range}"

        # Should be chronologically ordered
        assert timestamps == sorted(timestamps), "Timestamps should be chronologically ordered"

        # Should span full year
        first_date = timestamps[0].date()
        last_date = timestamps[-1].date()
        assert first_date == date(2024, 1, 1), f"Should start on Jan 1, got {first_date}"
        assert last_date == date(2024, 12, 31), f"Should end on Dec 31, got {last_date}"


@pytest.mark.integration
class TestEndToEndScenarios:
    """Complete end-to-end scenarios testing the full system."""

    @pytest.mark.asyncio
    async def test_ecommerce_annual_pattern(self):
        """Test realistic e-commerce annual pattern with all factors."""
        config = BNPLConfig(
            base_daily_volume=1000,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            volume_variation_enabled=True,
            seed=42
        )

        generator = BNPLGenerator(config)
        timestamps = generator._historical_timestamps
        date_counts = collections.Counter([ts.date() for ts in timestamps])

        # Test key business patterns
        # 1. January should be low (post-holiday)
        jan_dates = [d for d in date_counts.keys() if d.month == 1 and d.day > 2]  # Skip New Year
        jan_avg = statistics.mean([date_counts[d] for d in jan_dates])
        assert jan_avg < 850, f"January average {jan_avg:.1f} should be low"

        # 2. November should be elevated (pre-holiday shopping)
        nov_dates = [d for d in date_counts.keys() if d.month == 11]
        nov_avg = statistics.mean([date_counts[d] for d in nov_dates])
        assert nov_avg > 1050, f"November average {nov_avg:.1f} should be elevated"

        # 3. Black Friday should be peak
        black_friday = date(2024, 11, 29)
        bf_count = date_counts[black_friday]
        assert bf_count > 1500, f"Black Friday {bf_count} should be peak"

        # 4. Christmas should be minimal
        christmas = date(2024, 12, 25)
        xmas_count = date_counts[christmas]
        assert xmas_count < 200, f"Christmas {xmas_count} should be minimal"

        # 5. Weekend pattern should be consistent
        weekend_counts = [count for date_obj, count in date_counts.items() if date_obj.weekday() >= 5]
        weekday_counts = [count for date_obj, count in date_counts.items() if date_obj.weekday() < 5]

        weekend_avg = statistics.mean(weekend_counts)
        weekday_avg = statistics.mean(weekday_counts)
        assert weekend_avg < weekday_avg * 0.9, f"Weekends ({weekend_avg:.1f}) should be lower than weekdays ({weekday_avg:.1f})"

    @pytest.mark.asyncio
    async def test_ml_training_data_quality(self):
        """Test that generated data has ML-appropriate characteristics."""
        config = BNPLConfig(
            base_daily_volume=500,
            max_records=100,  # Limit to 100 records for ML testing
            start_date=date(2024, 6, 1),
            end_date=date(2024, 8, 31),  # Summer period
            volume_variation_enabled=True,
            seed=42
        )

        generator = BNPLGenerator(config)

        # Generate actual records using direct method for faster testing
        records = []
        for _ in range(100):
            record = await generator.generate_record()
            # Get historical timestamp if available, otherwise use current time
            if hasattr(generator, '_get_next_historical_timestamp'):
                timestamp = generator._get_next_historical_timestamp()
            else:
                from datetime import datetime
                timestamp = datetime.utcnow()
            record['_timestamp'] = timestamp.isoformat()
            records.append(record)

        # Test ML-relevant characteristics
        risk_scores = [r['risk_score'] for r in records]
        amounts = [r['amount'] for r in records]
        timestamps = [r['_timestamp'] for r in records]  # Use '_timestamp' field

        # 1. Risk scores should have good distribution
        assert 0 <= min(risk_scores) <= max(risk_scores) <= 1.0, "Risk scores should be in [0,1] range"
        assert statistics.stdev(risk_scores) > 0.1, "Risk scores should have meaningful variation"

        # 2. Amounts should be realistic
        assert all(a > 0 for a in amounts), "All amounts should be positive"
        assert statistics.mean(amounts) > 100, "Average amount should be reasonable for BNPL"

        # 3. Should have appropriate default rate
        defaults = sum(1 for r in records if r['will_default'])
        default_rate = defaults / len(records)
        assert 0.01 <= default_rate <= 0.15, f"Default rate {default_rate:.3f} should be realistic"

        # 4. Timestamps should use historical range
        from datetime import datetime
        for ts in timestamps:
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            assert date(2024, 6, 1) <= ts.date() <= date(2024, 8, 31), f"Timestamp {ts.date()} outside expected range"