"""
Simulation module for ROS2 DEVS simulation.
Provides system composition, validation, and analysis tools.
"""

from .system import (
    ROS2System,
    MinimalSystem,
    create_system
)

from .validator import (
    ValidationResult,
    ValidationCheck,
    TraceValidator,
    PerformanceValidator
)

from .analyzer import (
    SimulationAnalyzer
)

__all__ = [
    # System
    'ROS2System', 'MinimalSystem', 'create_system',
    
    # Validation
    'ValidationResult', 'ValidationCheck', 'TraceValidator', 'PerformanceValidator',
    
    # Analysis
    'SimulationAnalyzer'
]