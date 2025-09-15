# Contributing to simtom

We welcome contributions to simtom! This guide will help you get started with contributing to the project.

## 🚀 Quick Start for Contributors

### Prerequisites

- Python 3.9 or higher
- Poetry (recommended) or pip
- Git

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/simtom.git
   cd simtom
   ```

2. **Install Dependencies**
   ```bash
   # With Poetry (recommended)
   poetry install --with dev
   poetry shell

   # Or with pip
   pip install -e ".[dev]"
   ```

3. **Run Tests**
   ```bash
   pytest
   ```

4. **Start Development Server**
   ```bash
   python scripts/run_server.py
   ```

## 🏗️ Project Structure

Understanding the architecture helps you contribute effectively:

```
simtom/
├── core/              # Stable abstractions (rarely change)
│   ├── generator.py      # BaseGenerator abstract class
│   ├── registry.py       # Plugin discovery system
│   └── entities.py       # Core data models
├── generators/        # Extensible data generators (add here!)
│   └── ecommerce/
│       ├── base.py       # Common ecommerce patterns
│       └── bnpl.py       # BNPL-specific generator
├── api/               # FastAPI web layer
│   ├── main.py          # Application factory
│   ├── routes.py        # HTTP endpoints
│   └── models.py        # Pydantic request/response models
├── scenarios/         # Time-based scenario modeling
└── utils/             # Shared utilities
```

## 🔧 Development Workflow

### 1. Creating a New Generator

This is the most common contribution. Here's how to add a new data generator:

#### Step 1: Create the Generator Class

```python
# simtom/generators/finance/credit_cards.py
from typing import Dict, Any
from simtom.core.generator import BaseGenerator, register_generator

@register_generator("credit_cards")
class CreditCardGenerator(BaseGenerator):
    """Generates realistic credit card transaction data."""

    async def generate_record(self) -> Dict[str, Any]:
        return {
            "transaction_id": str(self.faker.uuid4()),
            "card_number": self.faker.credit_card_number(),
            "amount": round(self.faker.pyfloat(min_value=1, max_value=2000), 2),
            "merchant": self.faker.company(),
            "merchant_category": self.faker.random_element([
                "grocery", "gas", "restaurant", "retail", "online"
            ]),
            "timestamp": self.faker.date_time_this_year().isoformat(),
            "fraud_probability": self.faker.pyfloat(min_value=0, max_value=1),
            "customer_id": str(self.faker.uuid4()),
        }
```

#### Step 2: Add Configuration (Optional)

```python
from pydantic import BaseModel, Field

class CreditCardConfig(BaseModel):
    fraud_rate: float = Field(0.1, description="Percentage of fraudulent transactions")
    high_value_threshold: float = Field(500.0, description="Threshold for high-value transactions")

@register_generator("credit_cards")
class CreditCardGenerator(BaseGenerator):
    def __init__(self, config: GeneratorConfig, generator_config: CreditCardConfig = None):
        super().__init__(config)
        self.generator_config = generator_config or CreditCardConfig()
```

#### Step 3: Write Tests

```python
# tests/generators/test_credit_cards.py
import pytest
from simtom.core.generator import GeneratorConfig
from simtom.generators.finance.credit_cards import CreditCardGenerator

@pytest.mark.asyncio
async def test_credit_card_generation():
    config = GeneratorConfig(total_records=10, seed=42)
    generator = CreditCardGenerator(config)

    records = []
    async for record in generator.stream():
        records.append(record)

    assert len(records) == 10
    assert all("transaction_id" in record for record in records)
    assert all("amount" in record for record in records)
    assert all(isinstance(record["amount"], float) for record in records)

@pytest.mark.asyncio
async def test_credit_card_reproducibility():
    config = GeneratorConfig(total_records=5, seed=42)

    # Generate twice with same seed
    gen1 = CreditCardGenerator(config)
    records1 = [r async for r in gen1.stream()]

    gen2 = CreditCardGenerator(config)
    records2 = [r async for r in gen2.stream()]

    # Should be identical
    assert records1 == records2
```

#### Step 4: Update Documentation

Add your generator to the table in `README.md`:

```markdown
| Generator | Description | Use Case |
|-----------|-------------|----------|
| `bnpl` | Buy-Now-Pay-Later transactions with risk scoring | Credit risk, fraud detection |
| `credit_cards` | Credit card transactions with fraud indicators | Fraud detection, spending analysis |
```

### 2. Improving Existing Generators

When enhancing existing generators:

- **Maintain backward compatibility**: Existing code should continue to work
- **Add configuration options**: Use Pydantic models for new parameters
- **Update tests**: Ensure new features are tested
- **Document changes**: Update docstrings and README
- **Historical data support**: Consider adding `start_date`/`end_date` support for ML training datasets

### 3. API Enhancements

For FastAPI route improvements:

- **Follow OpenAPI standards**: Use proper response models
- **Add input validation**: Leverage Pydantic for request validation
- **Include error handling**: Return appropriate HTTP status codes
- **Update API docs**: Ensure Swagger docs are accurate

## 🧪 Testing Guidelines

### Test Structure

```
tests/
├── unit/              # Unit tests for individual components
│   ├── test_generator.py
│   ├── test_registry.py
│   └── test_entities.py
├── generators/        # Generator-specific tests
│   ├── test_bnpl_generator.py
│   └── test_credit_cards.py
└── integration/       # End-to-end API tests
    └── test_api.py
```

### Writing Good Tests

1. **Test Reproducibility**
   ```python
   # Always test that same seed produces same results
   config = GeneratorConfig(seed=42, total_records=10)
   gen1 = MyGenerator(config)
   gen2 = MyGenerator(config)

   records1 = [r async for r in gen1.stream()]
   records2 = [r async for r in gen2.stream()]
   assert records1 == records2
   ```

2. **Test Data Quality**
   ```python
   # Ensure generated data meets quality standards
   async def test_data_quality():
       records = [r async for r in generator.stream()]

       # No null values in required fields
       assert all(record["id"] is not None for record in records)

       # Realistic value ranges
       assert all(0 <= record["amount"] <= 10000 for record in records)

       # Proper data types
       assert all(isinstance(record["timestamp"], str) for record in records)
   ```

3. **Test Edge Cases**
   ```python
   # Test boundary conditions
   async def test_edge_cases():
       # Zero records
       config = GeneratorConfig(total_records=0)
       generator = MyGenerator(config)
       records = [r async for r in generator.stream()]
       assert len(records) == 0

       # High rate
       config = GeneratorConfig(rate_per_second=1000, total_records=10)
       # Should not crash or timeout
   ```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=simtom --cov-report=html

# Run specific test file
pytest tests/generators/test_bnpl_generator.py

# Run with verbose output
pytest -v

# Run async tests only
pytest -k "async"
```

## 📝 Code Quality Standards

### Code Formatting

We use automated code formatting:

```bash
# Format code
black simtom/ tests/

# Check formatting
black --check simtom/ tests/

# Lint code
ruff check simtom/ tests/

# Fix linting issues
ruff check --fix simtom/ tests/
```

### Type Checking

All code must pass type checking:

```bash
# Type check
mypy simtom/

# Type check specific file
mypy simtom/generators/ecommerce/bnpl.py
```

### Documentation Standards

1. **Docstrings**: All public classes and methods must have docstrings
   ```python
   class MyGenerator(BaseGenerator):
       """Generates synthetic data for X use case.

       This generator creates realistic X data with configurable
       parameters for testing ML models in Y scenarios.

       Args:
           config: Generator configuration
           generator_config: X-specific configuration options
       """

       async def generate_record(self) -> Dict[str, Any]:
           """Generate a single synthetic record.

           Returns:
               Dictionary containing synthetic X data with fields:
               - id: Unique identifier
               - field1: Description of field1
               - field2: Description of field2
           """
   ```

2. **Type Hints**: All public APIs must have complete type annotations
   ```python
   from typing import Dict, Any, Optional, List

   async def process_data(
       records: List[Dict[str, Any]],
       config: Optional[ProcessingConfig] = None
   ) -> Dict[str, float]:
       """Process records and return metrics."""
   ```

## 🚀 Submitting Changes

### Before Submitting

Run the complete test suite:

```bash
# Install pre-commit hooks (recommended)
pre-commit install

# Run all checks
pytest
black --check .
ruff check .
mypy simtom/
```

### Pull Request Process

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/add-credit-card-generator
   ```

2. **Make Changes**
   - Write code following our standards
   - Add comprehensive tests
   - Update documentation

3. **Test Thoroughly**
   ```bash
   pytest --cov=simtom
   black --check .
   ruff check .
   mypy simtom/
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add credit card transaction generator

   - Implements CreditCardGenerator with fraud indicators
   - Adds configurable fraud rate and merchant categories
   - Includes comprehensive test suite
   - Updates documentation with new generator"
   ```

5. **Submit PR**
   - Clear description of changes
   - Link to any related issues
   - Include example usage if adding new features

### Commit Message Format

We follow conventional commits:

```
type(scope): brief description

More detailed explanation if needed.

- bullet points for key changes
- reference any issues: fixes #123
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding tests
- `refactor`: Code refactoring
- `perf`: Performance improvements

## 🐛 Reporting Issues

### Bug Reports

Include:
- **Environment**: Python version, OS, simtom version
- **Reproduction steps**: Minimal code to reproduce
- **Expected vs actual behavior**
- **Error messages**: Full stack traces

### Feature Requests

Include:
- **Use case**: What problem does this solve?
- **Proposed solution**: How should it work?
- **Alternatives considered**: Other approaches you've considered

## 🎯 Areas for Contribution

### High Priority

1. **New Generators**
   - Financial: Insurance claims, loan applications
   - Healthcare: Patient records, clinical trials
   - Retail: Inventory, customer behavior
   - IoT: Sensor data, device telemetry

2. **Advanced Features**
   - Time-series patterns (seasonality, trends)
   - Cross-record relationships (customer journeys)
   - Geographic data patterns
   - Anomaly injection for testing

3. **Performance**
   - Memory optimization for large datasets
   - Parallel generation
   - Caching strategies

### Medium Priority

1. **Integrations**
   - Apache Kafka producer
   - Apache Pulsar integration
   - Database connectors
   - Cloud storage exports

2. **Monitoring**
   - Generation metrics
   - Performance dashboards
   - Health checks

## 💬 Getting Help

- **GitHub Discussions**: Ask questions, share ideas
- **Issues**: Report bugs, request features
- **Code Review**: Learn from PR feedback

## 🏆 Recognition

Contributors are recognized in:
- README contributors section
- Release notes
- Annual contributor highlights

Thank you for contributing to simtom! 🎉