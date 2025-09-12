# SIMTOM

**Realistic data simulator for ML system testing with time-compressed scenarios and controlled drift**

SIMTOM is an extensible data generation platform that creates realistic streaming data for machine learning model training and testing. Features include configurable arrival patterns, noise injection, drift simulation, and time compression for accelerated development cycles.

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

### Installation
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

## 🚦 Arrival Patterns

### Uniform (Default)
Fixed intervals - predictable for testing
```bash
curl -X POST /stream/bnpl -d '{
  "rate_per_second": 2.0,
  "arrival_pattern": "uniform"
}'
```

### Poisson
Random intervals with realistic variability
```bash
curl -X POST /stream/bnpl -d '{
  "rate_per_second": 2.0,
  "arrival_pattern": "poisson" 
}'
```

### NHPP (Non-Homogeneous Poisson)
Daily traffic patterns with peak hours
```bash
curl -X POST /stream/bnpl -d '{
  "rate_per_second": 1.0,
  "arrival_pattern": "nhpp",
  "peak_hours": [12, 19],
  "time_compression": 24.0
}'
```

### Burst
Flash sale and event-driven spikes
```bash
curl -X POST /stream/bnpl -d '{
  "rate_per_second": 2.0,
  "arrival_pattern": "burst",
  "burst_intensity": 3.0,
  "burst_probability": 0.6
}'
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

## 🔧 Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `rate_per_second` | Arrival rate (0.1-1000) | 1.0 |  
| `arrival_pattern` | Traffic pattern | "uniform" |
| `peak_hours` | NHPP peak hours | [12, 19] |
| `burst_intensity` | Burst multiplier | 2.0 |
| `time_compression` | Time acceleration | 1.0 |
| `noise_type` | Data quality | "none" |
| `drift_type` | Model drift | "none" |
| `seed` | Deterministic output | null |

## 🏗️ Architecture

- **Plugin System**: Auto-discovery of generators
- **Memory Efficient**: O(1) streaming regardless of dataset size  
- **Entity Consistency**: LRU registries maintain referential integrity
- **FastAPI**: Modern async web framework
- **Pydantic**: Type-safe configuration validation

## 🧪 Use Cases

- **ML Model Training**: Realistic arrival patterns for better model performance
- **Load Testing**: Simulate traffic spikes and patterns
- **Feature Engineering**: Rich, consistent data for pipeline development  
- **System Testing**: Controlled drift and noise injection
- **Research**: Reproducible datasets with deterministic seeding

## 📚 Documentation

- [Development Guide](CLAUDE.md) - Architecture and development commands
- [Live API Docs](https://simtom-production.up.railway.app/docs) - Interactive OpenAPI docs

## 🤝 Contributing

SIMTOM is designed for community extension. Add new generators by:

1. Inherit from `BaseGenerator`
2. Implement `async def generate_record()`  
3. Add `@register_generator("name")` decorator
4. Place in `simtom/generators/` - auto-discovered!

## 📄 License

MIT License - see [LICENSE](LICENSE) file.
