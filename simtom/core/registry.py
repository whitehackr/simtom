from typing import Dict, Type, List, Optional
import importlib
import pkgutil
from pathlib import Path

from .generator import BaseGenerator, GeneratorConfig


class PluginRegistry:
    _instance: Optional["PluginRegistry"] = None
    _generators: Dict[str, Type[BaseGenerator]] = {}
    
    def __new__(cls) -> "PluginRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def register(cls, name: str, generator_class: Type[BaseGenerator]) -> None:
        if not issubclass(generator_class, BaseGenerator):
            raise ValueError(f"Generator {generator_class} must inherit from BaseGenerator")
        cls._generators[name] = generator_class
    
    @classmethod
    def get_generator(cls, name: str) -> Optional[Type[BaseGenerator]]:
        return cls._generators.get(name)
    
    @classmethod
    def list_generators(cls) -> List[str]:
        return list(cls._generators.keys())
    
    @classmethod
    def create_generator(cls, name: str, config: GeneratorConfig) -> BaseGenerator:
        generator_class = cls.get_generator(name)
        if generator_class is None:
            raise ValueError(f"Unknown generator: {name}")
        return generator_class(config)
    
    @classmethod
    def discover_generators(cls, package_path: str = "simtom.generators") -> None:
        try:
            package = importlib.import_module(package_path)
            package_dir = Path(package.__file__).parent
            
            # Walk through all Python modules in the generators package
            for _, module_name, _ in pkgutil.iter_modules([str(package_dir)]):
                module_path = f"{package_path}.{module_name}"
                try:
                    importlib.import_module(module_path)
                except ImportError as e:
                    # Log but don't fail - some modules might have optional dependencies
                    continue
                    
        except ImportError:
            # Package doesn't exist yet - that's okay
            pass


def register_generator(name: str):
    def decorator(cls: Type[BaseGenerator]) -> Type[BaseGenerator]:
        PluginRegistry.register(name, cls)
        return cls
    return decorator