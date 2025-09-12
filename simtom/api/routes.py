from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import List
import json
import asyncio

from .models import GeneratorRequest, GeneratorInfo, StreamResponse, HealthResponse
from ..core.registry import PluginRegistry
from ..core.generator import GeneratorConfig

router = APIRouter()


@router.get("/", response_model=HealthResponse)
async def health_check():
    generators_count = len(PluginRegistry.list_generators())
    return HealthResponse(generators_available=generators_count)


@router.get("/generators", response_model=List[GeneratorInfo])
async def list_generators():
    generator_names = PluginRegistry.list_generators()
    generators_info = []
    
    for name in generator_names:
        generator_class = PluginRegistry.get_generator(name)
        if generator_class:
            generators_info.append(GeneratorInfo(
                name=name,
                description=generator_class.__doc__,
                config_schema=GeneratorConfig.model_json_schema()
            ))
    
    return generators_info


@router.post("/stream/{generator_name}")
async def stream_data(generator_name: str, config: GeneratorConfig):
    try:
        generator = PluginRegistry.create_generator(generator_name, config)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    async def generate_stream():
        async for record in generator.stream():
            yield f"data: {json.dumps(record)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )