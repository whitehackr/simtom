"""SIMTOM - Realistic data simulator for ML system testing."""

__version__ = "0.1.0"
__author__ = "Kev Waithaka"
__description__ = "A realistic data simulator for ML system testing"

from .core.generator import BaseGenerator, GeneratorConfig

__all__ = ["BaseGenerator", "GeneratorConfig"]