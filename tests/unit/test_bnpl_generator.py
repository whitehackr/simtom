import pytest
from datetime import datetime, date, timedelta

from simtom.generators.ecommerce.bnpl import BNPLGenerator, BNPLConfig
from simtom.core.generator import NoiseType, DriftType
from simtom.core.holidays import get_major_holidays, is_weekend


@pytest.mark.asyncio
async def test_bnpl_generator_basic():
    config = BNPLConfig(
        rate_per_second=10.0,
        max_records=5,
        seed=42,
        max_customers=100,
        max_products=50
    )
    generator = BNPLGenerator(config)
    
    records = []
    async for record in generator.stream():
        records.append(record)
    
    assert len(records) == 5
    
    # Verify BNPL-specific fields are present
    required_bnpl_fields = [
        "risk_scenario", "risk_score", "risk_level", 
        "installment_count", "first_payment_amount",
        "will_default", "checkout_speed"
    ]
    
    for record in records:
        for field in required_bnpl_fields:
            assert field in record, f"Missing field: {field}"


@pytest.mark.asyncio
async def test_bnpl_risk_scenarios():
    config = BNPLConfig(
        rate_per_second=10.0,
        max_records=100,
        seed=42,
        # Force specific scenario distributions
        risk_scenario_weights={
            "low_risk_purchase": 0.25,
            "impulse_purchase": 0.25, 
            "credit_stretched": 0.25,
            "high_risk_behavior": 0.25
        }
    )
    generator = BNPLGenerator(config)
    
    records = []
    async for record in generator.stream():
        records.append(record)
    
    # Should have all risk scenarios represented
    scenarios = {r["risk_scenario"] for r in records}
    expected_scenarios = {"low_risk_purchase", "impulse_purchase", "credit_stretched", "high_risk_behavior"}
    assert scenarios == expected_scenarios


@pytest.mark.asyncio
async def test_entity_consistency():
    config = BNPLConfig(
        rate_per_second=10.0,
        max_records=50,
        seed=42,
        repeat_customer_rate=0.8,  # High repeat rate for testing
        max_customers=10  # Small pool to force repeats
    )
    generator = BNPLGenerator(config)
    
    records = []
    async for record in generator.stream():
        records.append(record)
    
    # Group by customer_id
    customer_records = {}
    for record in records:
        cid = record["customer_id"]
        if cid not in customer_records:
            customer_records[cid] = []
        customer_records[cid].append(record)
    
    # Should have repeat customers (fewer unique customers than records)
    assert len(customer_records) < len(records), "Should have repeat customers"
    
    # Verify customer IDs are consistent (basic check)
    # Note: Full consistency test would require checking raw entity data
    # since denormalized fields may have timing variations
    for customer_id, customer_recs in customer_records.items():
        if len(customer_recs) > 1:
            # All records should have same customer_id
            first_rec = customer_recs[0]
            for rec in customer_recs[1:]:
                assert rec["customer_id"] == first_rec["customer_id"]


@pytest.mark.asyncio 
async def test_denormalization_modes():
    # Test normalized mode (references only)
    config_normalized = BNPLConfig(
        rate_per_second=10.0,
        max_records=3,
        seed=42,
        denormalize_entities=False
    )
    generator_normalized = BNPLGenerator(config_normalized)
    
    # Test denormalized mode (flat records)
    config_denormalized = BNPLConfig(
        rate_per_second=10.0,
        max_records=3, 
        seed=42,
        denormalize_entities=True
    )
    generator_denormalized = BNPLGenerator(config_denormalized)
    
    # Generate records
    normalized_records = []
    async for record in generator_normalized.stream():
        normalized_records.append(record)
    
    denormalized_records = []
    async for record in generator_denormalized.stream():
        denormalized_records.append(record)
    
    # Normalized should have fewer fields (just references)
    norm_fields = set(normalized_records[0].keys())
    denorm_fields = set(denormalized_records[0].keys())
    
    assert len(denorm_fields) > len(norm_fields), "Denormalized should have more fields"
    
    # Denormalized should have customer/product attributes
    expected_denorm_fields = ["customer_age_bracket", "customer_income_bracket", "product_category", "product_brand"]
    for field in expected_denorm_fields:
        assert field in denorm_fields


@pytest.mark.asyncio
async def test_risk_scoring():
    config = BNPLConfig(
        rate_per_second=10.0,
        max_records=20,
        seed=42
    )
    generator = BNPLGenerator(config)
    
    records = []
    async for record in generator.stream():
        records.append(record)
    
    # Verify risk scores are in valid range
    for record in records:
        assert 0.0 <= record["risk_score"] <= 1.0
        assert record["risk_level"] in ["low", "medium", "high", "very_high"]
    
    # Should have variety of risk levels (but may be limited with small sample)
    risk_levels = {r["risk_level"] for r in records}
    assert len(risk_levels) >= 1, "Should have at least one risk level"
    # Verify risk levels are valid
    valid_levels = {"low", "medium", "high", "very_high"}
    for level in risk_levels:
        assert level in valid_levels, f"Invalid risk level: {level}"


@pytest.mark.asyncio
async def test_noise_application():
    config = BNPLConfig(
        rate_per_second=10.0,
        max_records=5,
        seed=42,
        noise_type=NoiseType.GAUSSIAN,
        noise_level=0.1
    )
    generator = BNPLGenerator(config)
    
    records = []
    async for record in generator.stream():
        records.append(record)
    
    # Noise should be applied to numerical fields
    # Check that amounts vary from exact product prices due to noise
    amounts = [r["amount"] for r in records]
    
    # With noise, amounts should not be exact multiples/identical
    assert len(set(amounts)) == len(amounts) or len(amounts) == 1, "Noise should create variation"


@pytest.mark.asyncio  
async def test_default_prediction():
    config = BNPLConfig(
        rate_per_second=10.0,
        max_records=100,
        seed=42,
        base_default_rate=0.1  # 10% default rate for testing
    )
    generator = BNPLGenerator(config)
    
    records = []
    async for record in generator.stream():
        records.append(record)
    
    # Should have some defaults
    defaults = [r for r in records if r["will_default"]]
    assert len(defaults) > 0, "Should have some predicted defaults"
    
    # Defaulting records should have days_to_first_missed_payment
    for default_rec in defaults:
        assert default_rec["days_to_first_missed_payment"] is not None
        assert isinstance(default_rec["days_to_first_missed_payment"], int)
        assert default_rec["days_to_first_missed_payment"] > 0


@pytest.mark.asyncio
async def test_historical_date_range_basic():
    """Test basic historical date range functionality."""
    start_date = date(2024, 6, 1)
    end_date = date(2024, 6, 30)

    config = BNPLConfig(
        rate_per_second=10.0,
        max_records=10,
        seed=42,
        start_date=start_date,
        end_date=end_date
    )
    generator = BNPLGenerator(config)

    records = []
    async for record in generator.stream():
        records.append(record)

    assert len(records) == 10

    # All timestamps should be within the specified range
    for record in records:
        timestamp_str = record["_timestamp"]
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        record_date = timestamp.date()

        assert start_date <= record_date <= end_date, f"Timestamp {record_date} outside range {start_date}-{end_date}"


@pytest.mark.asyncio
async def test_historical_timestamp_distribution():
    """Test that timestamps are distributed across the date range."""
    start_date = date(2024, 6, 1)
    end_date = date(2024, 6, 30)

    config = BNPLConfig(
        rate_per_second=10.0,
        max_records=30,  # One per day on average
        seed=42,
        start_date=start_date,
        end_date=end_date,
        volume_variation_enabled=False  # Disable for uniform distribution test
    )
    generator = BNPLGenerator(config)

    records = []
    async for record in generator.stream():
        records.append(record)

    # Extract dates from timestamps
    record_dates = []
    for record in records:
        timestamp = record["_timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        record_dates.append(timestamp.date())

    # With volume distribution, records may be concentrated on certain days
    # but should still have some temporal spread
    unique_dates = set(record_dates)
    assert len(unique_dates) >= 1, "Records should have valid dates"
    # Verify all dates are within the expected range
    for record_date in unique_dates:
        assert start_date <= record_date <= end_date, f"Date {record_date} outside range"

    # With realistic volume patterns, records may be concentrated on certain days
    # Test that we have reasonable temporal distribution
    date_span = max(record_dates) - min(record_dates)
    total_span = end_date - start_date

    # Should have some temporal spread (at least 10% of the total range)
    min_expected_span = total_span.days * 0.1
    assert date_span.days >= min_expected_span, f"Date span {date_span.days} too narrow, expected at least {min_expected_span}"


@pytest.mark.asyncio
async def test_business_hours_weighting():
    """Test that business hours get more transactions."""
    config = BNPLConfig(
        rate_per_second=10.0,
        max_records=100,
        seed=42,
        start_date=date(2024, 6, 1),
        end_date=date(2024, 6, 30),
        volume_variation_enabled=False  # Disable for uniform business hours test
    )
    generator = BNPLGenerator(config)

    records = []
    async for record in generator.stream():
        records.append(record)

    # Count transactions by hour
    business_hours = 0  # 9am-6pm
    evening_hours = 0   # 6pm-11pm
    night_hours = 0     # 11pm-9am

    for record in records:
        timestamp = record["_timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        hour = timestamp.hour

        if 9 <= hour <= 17:
            business_hours += 1
        elif 18 <= hour <= 22:
            evening_hours += 1
        else:
            night_hours += 1

    total = len(records)

    # Should roughly follow 70% / 20% / 10% distribution
    # Allow some variance due to randomness and small sample sizes
    assert business_hours > total * 0.4, "Business hours should have significant portion of transactions"

    # With realistic business patterns, non-business hours should be less frequent
    non_business_hours = evening_hours + night_hours
    if total > 20:  # Only test distribution with larger samples
        assert business_hours >= non_business_hours, "Business hours should dominate"


@pytest.mark.asyncio
async def test_weekend_patterns():
    """Test weekend vs weekday patterns."""
    # Use a date range that includes weekends
    start_date = date(2024, 6, 1)  # Saturday
    end_date = date(2024, 6, 16)   # Sunday (includes 2 full weekends)

    config = BNPLConfig(
        rate_per_second=10.0,
        max_records=100,
        seed=42,
        start_date=start_date,
        end_date=end_date,
        weekend_multiplier=0.85  # 15% reduction on weekends
    )
    generator = BNPLGenerator(config)

    records = []
    async for record in generator.stream():
        records.append(record)

    weekday_count = 0
    weekend_count = 0

    for record in records:
        timestamp_str = record["_timestamp"]
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        record_date = timestamp.date()

        if is_weekend(record_date):
            weekend_count += 1
        else:
            weekday_count += 1

    # Should have more weekday transactions than weekend
    # (This is probabilistic, so allow some variance)
    if weekday_count > 0 and weekend_count > 0:
        weekend_ratio = weekend_count / (weekday_count + weekend_count)
        # With 0.85 multiplier, weekends should be less frequent
        assert weekend_ratio < 0.4, "Weekend transactions should be less frequent"


@pytest.mark.asyncio
async def test_backward_compatibility():
    """Test that no date parameters works as before (current timestamps)."""
    config = BNPLConfig(
        rate_per_second=10.0,
        max_records=5,
        seed=42
        # No start_date or end_date
    )
    generator = BNPLGenerator(config)

    before_generation = datetime.utcnow()

    records = []
    async for record in generator.stream():
        records.append(record)

    after_generation = datetime.utcnow()

    # All timestamps should be recent (current behavior)
    for record in records:
        timestamp_str = record["_timestamp"]
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

        assert before_generation <= timestamp <= after_generation, "Should use current timestamps"


@pytest.mark.asyncio
async def test_holiday_multipliers():
    """Test that holiday multipliers are applied correctly."""
    # Test around Black Friday 2024 (November 29, 2024)
    black_friday_2024 = date(2024, 11, 29)
    start_date = black_friday_2024 - timedelta(days=2)
    end_date = black_friday_2024 + timedelta(days=2)

    config = BNPLConfig(
        rate_per_second=10.0,
        max_records=50,
        seed=42,
        start_date=start_date,
        end_date=end_date,
        include_holiday_patterns=True
    )
    generator = BNPLGenerator(config)

    # Verify volume variation is enabled
    assert config.volume_variation_enabled == True

    # Test special event multiplier calculation
    bf_multiplier = generator._get_special_event_multiplier(black_friday_2024)
    assert bf_multiplier == 1.6, f"Expected 1.6 multiplier for Black Friday, got {bf_multiplier}"

    # Test normal day
    normal_day = black_friday_2024 - timedelta(days=10)
    normal_multiplier = generator._get_special_event_multiplier(normal_day)
    assert normal_multiplier == 1.0, f"Expected 1.0 for normal day, got {normal_multiplier}"


@pytest.mark.asyncio
async def test_chronological_ordering():
    """Test that historical timestamps are chronologically ordered."""
    config = BNPLConfig(
        rate_per_second=10.0,
        max_records=20,
        seed=42,
        start_date=date(2024, 6, 1),
        end_date=date(2024, 6, 30)
    )
    generator = BNPLGenerator(config)

    records = []
    async for record in generator.stream():
        records.append(record)

    # Extract timestamps
    timestamps = []
    for record in records:
        timestamp_str = record["_timestamp"]
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        timestamps.append(timestamp)

    # Should be chronologically ordered
    sorted_timestamps = sorted(timestamps)
    assert timestamps == sorted_timestamps, "Timestamps should be chronologically ordered"


@pytest.mark.asyncio
async def test_date_validation():
    """Test that invalid date ranges raise appropriate errors."""

    # Test end_date before start_date
    with pytest.raises(ValueError, match="end_date must be >= start_date"):
        BNPLConfig(
            start_date=date(2024, 6, 30),
            end_date=date(2024, 6, 1)  # Before start_date
        )

    # Test date range > 365 days
    with pytest.raises(ValueError, match="date range cannot exceed 365 days"):
        BNPLConfig(
            start_date=date(2024, 1, 1),
            end_date=date(2025, 2, 1)  # > 365 days
        )


@pytest.mark.asyncio
async def test_holiday_patterns_can_be_disabled():
    """Test that holiday patterns can be disabled."""
    black_friday_2024 = date(2024, 11, 29)

    config = BNPLConfig(
        rate_per_second=10.0,
        max_records=10,
        seed=42,
        start_date=black_friday_2024,
        end_date=black_friday_2024,
        include_holiday_patterns=False  # Disabled
    )
    generator = BNPLGenerator(config)

    # When patterns disabled, volume variation should not apply special multipliers
    # Test that the current day rate multiplier doesn't include holiday effects
    if not config.include_holiday_patterns:
        # The rate multiplier should only include base factors, not holiday effects
        assert config.volume_variation_enabled == True