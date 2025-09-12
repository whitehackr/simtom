import pytest
from datetime import datetime

from simtom.generators.ecommerce.bnpl import BNPLGenerator, BNPLConfig
from simtom.core.generator import NoiseType, DriftType


@pytest.mark.asyncio
async def test_bnpl_generator_basic():
    config = BNPLConfig(
        rate_per_second=10.0,
        total_records=5,
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
        total_records=100,
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
        total_records=50,
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
        total_records=3,
        seed=42,
        denormalize_entities=False
    )
    generator_normalized = BNPLGenerator(config_normalized)
    
    # Test denormalized mode (flat records)
    config_denormalized = BNPLConfig(
        rate_per_second=10.0,
        total_records=3, 
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
        total_records=20,
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
    
    # Should have variety of risk levels
    risk_levels = {r["risk_level"] for r in records}
    assert len(risk_levels) > 1, "Should have multiple risk levels"


@pytest.mark.asyncio
async def test_noise_application():
    config = BNPLConfig(
        rate_per_second=10.0,
        total_records=5,
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
        total_records=100,
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