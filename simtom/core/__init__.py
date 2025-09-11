"""Core SIMTOM components - stable abstractions."""

from .generator import BaseGenerator, GeneratorConfig
from .registry import PluginRegistry

__all__ = ["BaseGenerator", "GeneratorConfig", "PluginRegistry"]