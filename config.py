"""
System configuration for ROS2 DEVS simulation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import os
import yaml
from pathlib import Path


@dataclass
class NetworkConfig:
    """Network configuration"""
    # Transport settings
    transport: str = "shared_memory"  # shared_memory, udp, tcp
    
    # Latency settings (microseconds)
    localhost_latency_us: float = 50.0
    lan_latency_us: float = 200.0
    wan_latency_us: float = 10000.0
    
    # Bandwidth limits (Mbps)
    localhost_bandwidth_mbps: float = 10000.0  # 10 Gbps
    lan_bandwidth_mbps: float = 1000.0  # 1 Gbps
    wan_bandwidth_mbps: float = 100.0  # 100 Mbps
    
    # Packet loss rates
    localhost_loss_rate: float = 0.0
    lan_loss_rate: float = 0.001  # 0.1%
    wan_loss_rate: float = 0.01  # 1%
    
    # MTU settings
    mtu: int = 1500
    jumbo_frames: bool = False
    
    # DDS specific
    multicast_enabled: bool = True
    unicast_enabled: bool = True
    
    def get_latency_us(self, connection_type: str) -> float:
        """Get latency for connection type"""
        return {
            'localhost': self.localhost_latency_us,
            'lan': self.lan_latency_us,
            'wan': self.wan_latency_us
        }.get(connection_type, self.lan_latency_us)


@dataclass
class ExecutorConfig:
    """Executor configuration"""
    # Thread pool settings
    default_num_threads: int = 4
    max_threads: int = 16
    thread_priority: int = 20  # Linux nice value
    
    # Scheduling
    use_cpu_affinity: bool = True
    dedicated_executor_threads: bool = False
    
    # Callback groups
    reentrant_callbacks: bool = False
    mutually_exclusive_groups: bool = True
    
    # Performance
    spin_period_us: int = 100  # Spin period in microseconds
    use_events_executor: bool = False


@dataclass
class DDSConfig:
    """DDS configuration"""
    # Vendor
    vendor: str = "CycloneDDS"  # CycloneDDS, FastDDS, ConnextDDS
    
    # Discovery
    discovery_multicast_address: str = "239.255.0.1"
    discovery_port: int = 7400
    discovery_period_ms: int = 300
    
    # Participant
    domain_id: int = 0
    participant_lease_duration_ms: int = 10000
    
    # Transport
    enable_shared_memory: bool = True
    enable_security: bool = False
    
    # Resource limits
    max_participants: int = 1000
    max_readers: int = 5000
    max_writers: int = 5000
    
    # Serialization
    use_cdr: bool = True
    use_xcdr2: bool = False


@dataclass
class MemoryConfig:
    """Memory configuration"""
    # Allocator settings
    use_tlsf_allocator: bool = True
    preallocate_messages: bool = True
    message_pool_size: int = 1000
    
    # Buffer sizes
    rcl_buffer_size: int = 16384  # 16 KB
    rmw_buffer_size: int = 65536  # 64 KB
    dds_buffer_size: int = 262144  # 256 KB
    
    # Zero-copy settings
    enable_zero_copy: bool = True
    zero_copy_threshold: int = 4096  # bytes
    
    # Memory limits
    max_memory_mb: int = 1024
    enable_memory_profiling: bool = False


@dataclass
class LoggingConfig:
    """Logging configuration"""
    # Trace settings
    enable_trace: bool = True
    trace_to_console: bool = True
    trace_to_file: bool = True
    trace_file_path: str = "ros2_trace.log"
    
    # Log levels
    default_log_level: str = "INFO"
    component_log_levels: Dict[str, str] = field(default_factory=dict)
    
    # Performance logging
    log_performance_metrics: bool = True
    metrics_interval_ms: int = 1000
    
    # Filtering
    trace_filter_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)


@dataclass
class SimulationConfig:
    """Main simulation configuration"""
    # Simulation settings
    simulation_time_seconds: float = 10.0
    use_sim_time: bool = True
    time_scale: float = 1.0  # 1.0 = real-time, 2.0 = 2x speed
    
    # Component settings
    enable_lifecycle_nodes: bool = True
    enable_actions: bool = True
    enable_services: bool = True
    enable_parameters: bool = True
    enable_graph_discovery: bool = True
    
    # Performance settings
    enable_performance_tracking: bool = True
    enable_overhead_simulation: bool = True
    realistic_message_drops: bool = True
    
    # Sub-configurations
    network: NetworkConfig = field(default_factory=NetworkConfig)
    executor: ExecutorConfig = field(default_factory=ExecutorConfig)
    dds: DDSConfig = field(default_factory=DDSConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    @classmethod
    def from_yaml(cls, filepath: str) -> 'SimulationConfig':
        """Load configuration from YAML file"""
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)
        
        # Parse sub-configurations
        config = cls()
        
        if 'simulation' in data:
            for key, value in data['simulation'].items():
                if hasattr(config, key):
                    setattr(config, key, value)
        
        if 'network' in data:
            config.network = NetworkConfig(**data['network'])
        
        if 'executor' in data:
            config.executor = ExecutorConfig(**data['executor'])
        
        if 'dds' in data:
            config.dds = DDSConfig(**data['dds'])
        
        if 'memory' in data:
            config.memory = MemoryConfig(**data['memory'])
        
        if 'logging' in data:
            config.logging = LoggingConfig(**data['logging'])
        
        return config
    
    def to_yaml(self, filepath: str):
        """Save configuration to YAML file"""
        data = {
            'simulation': {
                'simulation_time_seconds': self.simulation_time_seconds,
                'use_sim_time': self.use_sim_time,
                'time_scale': self.time_scale,
                'enable_lifecycle_nodes': self.enable_lifecycle_nodes,
                'enable_actions': self.enable_actions,
                'enable_services': self.enable_services,
                'enable_parameters': self.enable_parameters,
                'enable_graph_discovery': self.enable_graph_discovery,
                'enable_performance_tracking': self.enable_performance_tracking,
                'enable_overhead_simulation': self.enable_overhead_simulation,
                'realistic_message_drops': self.realistic_message_drops
            },
            'network': self.network.__dict__,
            'executor': self.executor.__dict__,
            'dds': self.dds.__dict__,
            'memory': self.memory.__dict__,
            'logging': self.logging.__dict__
        }
        
        with open(filepath, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)


# Default configuration presets
class ConfigPresets:
    """Configuration presets for different scenarios"""
    
    @staticmethod
    def development() -> SimulationConfig:
        """Development configuration with all features enabled"""
        config = SimulationConfig()
        config.enable_performance_tracking = True
        config.logging.trace_to_console = True
        config.logging.default_log_level = "DEBUG"
        return config
    
    @staticmethod
    def production() -> SimulationConfig:
        """Production configuration optimized for performance"""
        config = SimulationConfig()
        config.enable_performance_tracking = False
        config.logging.trace_to_console = False
        config.logging.default_log_level = "WARNING"
        config.memory.enable_zero_copy = True
        config.network.transport = "shared_memory"
        return config
    
    @staticmethod
    def testing() -> SimulationConfig:
        """Testing configuration with predictable behavior"""
        config = SimulationConfig()
        config.realistic_message_drops = False
        config.network.localhost_loss_rate = 0.0
        config.time_scale = 10.0  # 10x speed for faster tests
        return config
    
    @staticmethod
    def benchmark() -> SimulationConfig:
        """Benchmark configuration for performance testing"""
        config = SimulationConfig()
        config.enable_overhead_simulation = False
        config.logging.enable_trace = False
        config.memory.enable_memory_profiling = True
        config.enable_performance_tracking = True
        return config


# Global configuration instance
config = SimulationConfig()

# Load from environment or file
config_file = os.environ.get('ROS2_DEVS_CONFIG')
if config_file and Path(config_file).exists():
    config = SimulationConfig.from_yaml(config_file)
