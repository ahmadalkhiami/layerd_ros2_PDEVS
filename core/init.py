"""
Core module for ROS2 DEVS simulation.
Provides fundamental types, context management, tracing, and configuration.
"""

from .dataTypes import (
    # Message types
    MessageType,
    Message,
    MessageHeader,
    
    # QoS policies
    QoSReliabilityPolicy,
    QoSDurabilityPolicy,
    QoSHistoryPolicy,
    QoSLivelinessPolicy,
    QoSOwnershipPolicy,
    QoSProfile,
    RMWQoSProfile,
    
    # Handles
    NodeHandle,
    PublisherHandle,
    SubscriptionHandle,
    TimerHandle,
    ServiceHandle,
    GuardConditionHandle,
    
    # Executor
    ExecutorType,
    WaitSet,
    
    # System
    SystemState,
    system_state
)

from .context import (
    ExecutionContext,
    ContextManager,
    context_manager
)

from .trace import (
    TraceLevel,
    TraceEvent,
    TraceFilter,
    TraceLogger,
    trace_logger,
    
    # Convenience functions
    trace_rcl_init,
    trace_node_init,
    trace_publisher_init,
    trace_subscription_init,
    trace_publish,
    trace_callback_start,
    trace_callback_end
)

from simulation.config import (
    NetworkConfig,
    ExecutorConfig,
    DDSConfig,
    MemoryConfig,
    LoggingConfig,
    SimulationConfig,
    ConfigPresets,
    config
)

__all__ = [
    # Types
    'MessageType', 'Message', 'MessageHeader',
    'QoSReliabilityPolicy', 'QoSDurabilityPolicy', 'QoSHistoryPolicy',
    'QoSLivelinessPolicy', 'QoSOwnershipPolicy', 'QoSProfile', 'RMWQoSProfile',
    'NodeHandle', 'PublisherHandle', 'SubscriptionHandle', 'TimerHandle',
    'ServiceHandle', 'GuardConditionHandle',
    'ExecutorType', 'WaitSet',
    'SystemState', 'system_state',
    
    # Context
    'ExecutionContext', 'ContextManager', 'context_manager',
    
    # Trace
    'TraceLevel', 'TraceEvent', 'TraceFilter', 'TraceLogger', 'trace_logger',
    'trace_rcl_init', 'trace_node_init', 'trace_publisher_init',
    'trace_subscription_init', 'trace_publish', 'trace_callback_start',
    'trace_callback_end',
    
    # Config
    'NetworkConfig', 'ExecutorConfig', 'DDSConfig', 'MemoryConfig',
    'LoggingConfig', 'SimulationConfig', 'ConfigPresets', 'config'
]