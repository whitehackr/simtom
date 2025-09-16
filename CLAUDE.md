# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Server Management
- **Start development server**: `python scripts/run_server.py` 
- **Run with uvicorn directly**: `uvicorn simtom.api:app --reload --host 0.0.0.0 --port 8000`

### Testing
- **Run all tests**: `pytest`
- **Run unit tests**: `pytest tests/unit/`
- **Run with coverage**: `pytest --cov=simtom`

### Code Quality
- **Format code**: `black .`
- **Lint code**: `ruff check .`
- **Type checking**: `mypy simtom/`

### Dependency Management  
- **Install dependencies**: `poetry install`
- **Add new dependency**: `poetry add <package>`
- **Add dev dependency**: `poetry add --group dev <package>`

## Architecture Overview

### Core Components

**`simtom/core/`** - Stable abstractions that define system contracts
- `generator.py`: `BaseGenerator` abstract class and `GeneratorConfig` - the foundation everything builds on
- `registry.py`: `PluginRegistry` singleton for auto-discovery and management of data generators

**`simtom/generators/`** - Plugin architecture for extensible data generation  
- Uses `@register_generator()` decorator for auto-registration
- Each generator inherits from `BaseGenerator` and implements `generate_record()`

**`simtom/api/`** - FastAPI web layer for HTTP streaming
- `main.py`: Application factory with lifecycle management
- `routes.py`: Streaming endpoints using `StreamingResponse`
- `models.py`: Pydantic request/response models

### Key Design Patterns

**Plugin Architecture**: New generators are automatically discovered and registered at startup without code changes to core system.

**Async Streaming**: All data generation uses `AsyncGenerator` for memory-efficient streaming. Historical mode uses day-per-second delivery (1 days in 1 second). Current-date mode uses configurable rates (1-1000 records/second).

**Configuration as Code**: `GeneratorConfig` uses Pydantic for type-safe validation with clear error messages for invalid parameters.

**Separation of Concerns**: Clean boundaries between web layer (FastAPI), business logic (generators), and core abstractions.

## API Endpoints

### Local Development
- `GET /`: Health check with generator count
- `GET /generators`: List available generators with schemas  
- `POST /stream/{generator_name}`: Start streaming data with configuration

### Live Production (Railway)
- **Base URL**: `https://simtom-production.up.railway.app`
- `GET /`: Health check with generator count
- `GET /generators`: List available generators with schemas
- `POST /stream/bnpl`: Stream BNPL risk data with configuration

### Example Usage

#### Real-time Streaming (Live Data)
```bash
# Test live API
curl https://simtom-production.up.railway.app/generators

# Stream live BNPL data (current timestamps)
curl -X POST https://simtom-production.up.railway.app/stream/bnpl \
  -H "Content-Type: application/json" \
  -d '{"rate_per_second": 2.0, "max_records": 5, "seed": 42}'
```

#### Historical Data Generation (For ML Training)
```bash
# Generate 3 months of historical BNPL data with realistic patterns
curl -X POST https://simtom-production.up.railway.app/stream/bnpl \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-06-01",
    "end_date": "2024-09-01",
    "base_daily_volume": 400,
    "seed": 42,
    "include_holiday_patterns": true
  }'

# Fast bulk generation for large datasets
curl -X POST https://simtom-production.up.railway.app/stream/bnpl \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "base_daily_volume": 1000,
    "seed": 42
  }' > bnpl_2024_data.jsonl
```

## Development Workflow

### Adding New Generators
1. Create generator class inheriting from `BaseGenerator`
2. Implement `async def generate_record(self) -> Dict[str, Any]`
3. Add `@register_generator("name")` decorator
4. Place in `simtom/generators/` (auto-discovered)

### Testing Strategy
- Unit tests in `tests/unit/` for core components
- Integration tests in `tests/integration/` for API endpoints
- Generator-specific tests in `tests/generators/`

### Error Handling
- Use Pydantic validation for configuration errors
- Return proper HTTP status codes (404 for unknown generators)
- Graceful degradation for missing optional dependencies

## Performance Considerations

- Generators use async/await for non-blocking I/O
- Streaming responses prevent memory buildup
- Plugin discovery happens once at startup, not per request
- Rate limiting built into base generator (configurable delay)