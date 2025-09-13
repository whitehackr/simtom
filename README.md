# simtom

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Live Demo](https://img.shields.io/badge/demo-live-brightgreen)](https://simtom-production.up.railway.app)

**Realistic data simulator for ML system testing with time-compressed scenarios and controlled drift**

SIMTOM is an extensible data generation platform that creates realistic streaming data for machine learning model training and testing. Features include configurable arrival patterns, noise injection, drift simulation, and time compression for accelerated development cycles.

## Why simtom?

**The Problem**: Your ML model works in dev but fails in production. Unit tests use toy data. Load testing (Locust, wrk) only tests performance, not model behavior. Real production data is risky, regulated, or unavailable.

**The Solution**: simtom generates statistically realistic synthetic data with controlled patterns, drift, and edge cases. Test your ML models with production-like scenarios without production risks.

**Different from load testing**: While Locust tests "can your API handle 1000 requests?", simtom tests "does your fraud model still work when spending patterns change seasonally?"

## 🚀 Live API

**Production Endpoint**: `https://simtom-production.up.railway.app`

```bash
# Quick test
curl https://simtom-production.up.railway.app/generators

# Stream sample data
curl -X POST https://simtom-production.up.railway.app/stream/bnpl \
  -H "Content-Type: application/json" \
  -d '{"rate_per_second": 2.0, "total_records": 3}'
```

## ⚡ Key Features

- **🎯 Realistic Traffic Patterns**: Uniform, Poisson, NHPP, and Burst arrival patterns
- **📊 Rich Data Generation**: BNPL transactions with risk scoring and customer profiles
- **⏱️ Time Compression**: Simulate days/weeks of data in minutes
- **🔧 Plugin Architecture**: Easy extension with custom generators
- **📡 Real-time Streaming**: Server-sent events with configurable rates
- **🧪 ML-Ready**: Built-in noise, drift, and deterministic seeding

## 📋 Quick Start

### Try the Live API
```bash
# Check health and available generators
curl https://simtom-production.up.railway.app/

# List all available generators
curl https://simtom-production.up.railway.app/generators

# Stream BNPL synthetic data
curl -X POST https://simtom-production.up.railway.app/stream/bnpl \
  -H "Content-Type: application/json" \
  -d '{"rate_per_second": 2.0, "total_records": 5, "seed": 42}'
```

### Local Installation

```bash
git clone https://github.com/whitehackr/simtom.git
cd simtom
poetry install
```

### Run Locally
```bash
poetry run python scripts/run_server.py
curl http://localhost:8000/generators
```

### Basic Usage

```python
from simtom.generators.ecommerce.bnpl import BNPLGenerator
from simtom.core.generator import GeneratorConfig

# Configure generator
config = GeneratorConfig(
    rate_per_second=10.0,
    total_records=1000,
    seed=42
)

# Generate synthetic BNPL data
generator = BNPLGenerator(config)
async for record in generator.stream():
    print(record)  # Process each synthetic transaction
```

## 🚦 Arrival Patterns

### Uniform (Default)
Fixed intervals - predictable for testing
```bash
curl -X POST https://simtom-production.up.railway.app/stream/bnpl \
  -H "Content-Type: application/json" \
  -d '{
  "rate_per_second": 2.0,
  "arrival_pattern": "uniform"
}'
```

### Poisson
Random intervals with realistic variability
```bash
curl -X POST https://simtom-production.up.railway.app/stream/bnpl \
  -H "Content-Type: application/json" \
  -d '{
  "rate_per_second": 2.0,
  "arrival_pattern": "poisson"
}'
```

### NHPP (Non-Homogeneous Poisson)
Daily traffic patterns with peak hours
```bash
curl -X POST https://simtom-production.up.railway.app/stream/bnpl \
  -H "Content-Type: application/json" \
  -d '{
  "rate_per_second": 1.0,
  "arrival_pattern": "nhpp",
  "peak_hours": [12, 19],
  "time_compression": 24.0
}'
```

### Burst
Flash sale and event-driven spikes
```bash
curl -X POST https://simtom-production.up.railway.app/stream/bnpl \
  -H "Content-Type: application/json" \
  -d '{
  "rate_per_second": 2.0,
  "arrival_pattern": "burst",
  "burst_intensity": 3.0,
  "burst_probability": 0.6
}'
```

## 🏗️ Architecture

### Core Principles

- **Plugin Architecture**: Auto-discovery of data generators via decorators
- **Async Streaming**: Memory-efficient generation of large datasets
- **Type Safety**: Pydantic models for configuration and validation
- **Extensibility**: Add new generators without touching core code

### Architecture Highlights

- **Plugin System**: Auto-discovery of generators
- **Memory Efficient**: O(1) streaming regardless of dataset size
- **Entity Consistency**: LRU registries maintain referential integrity
- **FastAPI**: Modern async web framework
- **Pydantic**: Type-safe configuration validation

### Component Overview

```
simtom/
├── core/           # Stable abstractions
│   ├── generator.py    # BaseGenerator + GeneratorConfig
│   ├── registry.py     # Plugin auto-discovery
│   └── entities.py     # Core data models
├── generators/     # Pluggable data generators
│   └── ecommerce/
│       └── bnpl.py     # BNPL risk data generator
├── api/            # FastAPI web layer
│   ├── main.py         # Application factory
│   ├── routes.py       # Streaming endpoints
│   └── models.py       # Request/response schemas
└── scenarios/      # Time-based scenario modeling
```

### Plugin System

New generators are automatically registered:

```python
@register_generator("my_generator")
class MyGenerator(BaseGenerator):
    async def generate_record(self) -> Dict[str, Any]:
        return {"id": uuid4(), "value": random.random()}
```

## 📊 Sample Data

BNPL transactions include 40+ fields:
```json
{
  "transaction_id": "txn_00000001",
  "customer_id": "cust_000001",
  "amount": 485.61,
  "risk_score": 0.85,
  "risk_level": "high",
  "installment_count": 4,
  "customer_age_bracket": "25-34",
  "product_category": "electronics",
  "device_type": "mobile",
  "payment_provider": "afterpay"
}
```

## 📊 Available Generators

| Generator | Description | Use Case |
|-----------|-------------|----------|
| `bnpl` | Buy-Now-Pay-Later transactions with risk scoring | Credit risk, fraud detection |

## 🔧 Configuration

### Generator Configuration

```python
from simtom.core.generator import GeneratorConfig

config = GeneratorConfig(
    rate_per_second=1.0,     # Records per second (1-1000)
    total_records=None,      # Infinite if None
    seed=42,                 # Reproducible randomness
    time_compression=1.0     # Real-time = 1.0, faster = > 1.0
)
```

### Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `rate_per_second` | Arrival rate (0.1-1000) | 1.0 |
| `arrival_pattern` | Traffic pattern | "uniform" |
| `peak_hours` | NHPP peak hours | [12, 19] |
| `burst_intensity` | Burst multiplier | 2.0 |
| `burst_probability` | Burst occurrence probability | 0.3 |
| `time_compression` | Time acceleration | 1.0 |
| `noise_type` | Data quality | "none" |
| `drift_type` | Model drift | "none" |
| `seed` | Deterministic output | null |
| `total_records` | Maximum records to generate | null |

### Environment Variables

```bash
# API Configuration
SIMTOM_HOST=0.0.0.0
SIMTOM_PORT=8000
SIMTOM_LOG_LEVEL=info

# Redis (optional, for caching)
REDIS_URL=redis://localhost:6379
```

## 🧪 Use Cases

- **ML Model Training**: Realistic arrival patterns for better model performance
- **Load Testing**: Simulate traffic spikes and patterns
- **Feature Engineering**: Rich, consistent data for pipeline development
- **System Testing**: Controlled drift and noise injection
- **Research**: Reproducible datasets with deterministic seeding

### Scenario: BNPL Fraud Detection

```python
import asyncio
from simtom.generators.ecommerce.bnpl import BNPLGenerator

async def test_fraud_model():
    # Generate baseline data
    baseline_config = GeneratorConfig(seed=42, total_records=1000)
    baseline_gen = BNPLGenerator(baseline_config)

    # Train model on baseline
    baseline_data = [record async for record in baseline_gen.stream()]
    model = train_fraud_model(baseline_data)

    # Test with drift scenario
    drift_config = GeneratorConfig(
        seed=123,  # Different seed = different patterns
        total_records=200
    )
    drift_gen = BNPLGenerator(drift_config)

    # Evaluate model performance
    async for record in drift_gen.stream():
        prediction = model.predict(record)
        actual = record['default_risk']
        # Track accuracy degradation
```

## 🚀 Deployment

### Docker

```bash
docker build -t simtom .
docker run -p 8000:8000 simtom
```

### Railway

```bash
# Connect to Railway
railway login
railway link

# Deploy
railway up
```

## 🤝 Contributing

SIMTOM is designed for community extension. Add new generators by:

1. Inherit from `BaseGenerator`
2. Implement `async def generate_record()`
3. Add `@register_generator("name")` decorator
4. Place in `simtom/generators/` - auto-discovered!

### Adding New Generators

1. **Create Generator Class**
   ```python
   # simtom/generators/finance/credit_cards.py
   from simtom.core.generator import BaseGenerator, register_generator

   @register_generator("credit_cards")
   class CreditCardGenerator(BaseGenerator):
       async def generate_record(self) -> Dict[str, Any]:
           return {
               "card_number": self.faker.credit_card_number(),
               "amount": self.faker.pyfloat(min_value=1, max_value=1000),
               "merchant": self.faker.company()
           }
   ```

2. **Add Tests**
   ```python
   # tests/generators/test_credit_cards.py
   async def test_credit_card_generation():
       config = GeneratorConfig(total_records=10)
       generator = CreditCardGenerator(config)
       records = [r async for r in generator.stream()]
       assert len(records) == 10
       assert all("card_number" in r for r in records)
   ```

3. **Update Documentation**: Add to generator table above

### Development Setup

```bash
# Install development dependencies
poetry install --with dev

# Run tests
pytest

# Code formatting
black .
ruff check .

# Type checking
mypy simtom/
```

### Code Quality Standards

- **Type Hints**: All public APIs must have type annotations
- **Async First**: Use `async/await` for I/O operations
- **Testing**: >90% test coverage required
- **Documentation**: Docstrings for all public methods

## 📈 Performance

### Benchmarks

| Records/sec | Memory Usage | CPU Usage |
|-------------|--------------|-----------|
| 10          | ~50MB       | ~5%       |
| 100         | ~75MB       | ~15%      |
| 1000        | ~150MB      | ~40%      |

### Optimization Tips

- Use appropriate `rate_per_second` for your use case
- Set `total_records` to avoid infinite streams
- Consider Redis caching for repeated scenarios
- Use Docker limits in production

## 🐛 Troubleshooting

### Common Issues

**Generator Not Found**
```python
# Error: Generator 'my_gen' not found
# Solution: Ensure @register_generator decorator is used
```

**High Memory Usage**
```python
# Issue: Memory grows over time
# Solution: Set total_records limit or use streaming processing
async for record in generator.stream():
    process_record(record)  # Process immediately, don't accumulate
```

**Slow Generation**
```python
# Issue: Generation too slow
# Solution: Increase rate_per_second or check async usage
config = GeneratorConfig(rate_per_second=100)  # Faster
```

## 📚 Advanced Usage

### Custom Time Scenarios

```python
# Simulate Black Friday traffic spike
config = GeneratorConfig(
    time_compression=24.0,  # 1 hour = 24 hours of data
    rate_per_second=50.0    # Higher transaction volume
)
```

### Data Drift Simulation

```python
# Gradual drift over time
configs = [
    GeneratorConfig(seed=42),    # Baseline
    GeneratorConfig(seed=43),    # Month 1
    GeneratorConfig(seed=44),    # Month 2
]

for config in configs:
    generator = BNPLGenerator(config)
    # Test model performance degradation
```

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙋‍♂️ Support

- **Issues**: [GitHub Issues](https://github.com/whitehackr/simtom/issues)
- **Discussions**: [GitHub Discussions](https://github.com/whitehackr/simtom/discussions)
- **Live Demo**: [https://simtom-production.up.railway.app](https://simtom-production.up.railway.app)

---

**Built for ML Engineers, by ML Engineers** 🤖
