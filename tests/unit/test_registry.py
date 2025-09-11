import pytest
from typing import Dict, Any

from simtom.core.generator import BaseGenerator, GeneratorConfig
from simtom.core.registry import PluginRegistry, register_generator


class MockGenerator(BaseGenerator):
    async def generate_record(self) -> Dict[str, Any]:
        return {"mock": True}


def test_plugin_registry_singleton():
    registry1 = PluginRegistry()
    registry2 = PluginRegistry()
    assert registry1 is registry2


def test_register_generator_decorator():
    @register_generator("test_mock")
    class DecoratedGenerator(BaseGenerator):
        async def generate_record(self) -> Dict[str, Any]:
            return {"decorated": True}
    
    generator_class = PluginRegistry.get_generator("test_mock")
    assert generator_class is DecoratedGenerator


def test_registry_operations():
    # Clear registry for clean test
    PluginRegistry._generators.clear()
    
    # Register a generator
    PluginRegistry.register("mock", MockGenerator)
    
    # Test list generators
    generators = PluginRegistry.list_generators()
    assert "mock" in generators
    
    # Test get generator
    generator_class = PluginRegistry.get_generator("mock")
    assert generator_class is MockGenerator
    
    # Test create generator
    config = GeneratorConfig()
    generator = PluginRegistry.create_generator("mock", config)
    assert isinstance(generator, MockGenerator)
    assert generator.config is config


def test_registry_error_handling():
    # Test unknown generator
    with pytest.raises(ValueError, match="Unknown generator"):
        PluginRegistry.create_generator("unknown", GeneratorConfig())
    
    # Test invalid generator class
    class NotAGenerator:
        pass
    
    with pytest.raises(ValueError, match="must inherit from BaseGenerator"):
        PluginRegistry.register("invalid", NotAGenerator)