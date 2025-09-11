import pytest
from unittest.mock import AsyncMock
from typing import Dict, Any

from simtom.core.generator import BaseGenerator, GeneratorConfig, NoiseType, DriftType


class TestGenerator(BaseGenerator):
    async def generate_record(self) -> Dict[str, Any]:
        return {"id": self._records_generated, "value": 42}


@pytest.mark.asyncio
async def test_base_generator_stream():
    config = GeneratorConfig(rate_per_second=10.0, total_records=3)
    generator = TestGenerator(config)
    
    records = []
    async for record in generator.stream():
        records.append(record)
    
    assert len(records) == 3
    assert records[0]["id"] == 0
    assert records[1]["id"] == 1
    assert records[2]["id"] == 2
    
    for record in records:
        assert "_timestamp" in record
        assert "_record_id" in record
        assert "_generator" in record
        assert record["_generator"] == "TestGenerator"


@pytest.mark.asyncio
async def test_generator_config_validation():
    # Valid config
    config = GeneratorConfig(rate_per_second=5.0)
    assert config.rate_per_second == 5.0
    
    # Invalid rate (too high)
    with pytest.raises(ValueError):
        GeneratorConfig(rate_per_second=2000.0)
    
    # Invalid rate (too low) 
    with pytest.raises(ValueError):
        GeneratorConfig(rate_per_second=0.05)


def test_noise_and_drift_enums():
    assert NoiseType.GAUSSIAN == "gaussian"
    assert DriftType.LINEAR == "linear"
    
    config = GeneratorConfig(
        noise_type=NoiseType.GAUSSIAN,
        drift_type=DriftType.SUDDEN
    )
    assert config.noise_type == NoiseType.GAUSSIAN
    assert config.drift_type == DriftType.SUDDEN