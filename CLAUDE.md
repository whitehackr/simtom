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

**Async Streaming**: All data generation uses `AsyncGenerator` for memory-efficient streaming of large datasets with configurable rates (1-1000 records/second).

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
```bash
# Test live API
curl https://simtom-production.up.railway.app/generators

# Stream BNPL data
curl -X POST https://simtom-production.up.railway.app/stream/bnpl \
  -H "Content-Type: application/json" \
  -d '{"rate_per_second": 2.0, "total_records": 5, "seed": 42}'
```

For detailed arrival pattern examples, see [README.md](README.md).

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