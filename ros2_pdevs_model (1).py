#!/usr/bin/env python3
"""
Layered ROS2 Publisher-Subscriber System Simulation using PythonPDEVS
WITH proper layered architecture: Application → rclcpp → rcl → rmw
AND working message flow from publishers to subscribers
"""

from pypdevs.DEVS import *
from pypdevs.simulator import Simulator
import random
import time
import math
from dataclasses import dataclass
from typing import Dict, Optional, List
from enum import Enum
import copy

# =============================================================================
# CONFIGURATION
# =============================================================================

class SimulationConfig:
    """Global simulation configuration"""
    TRACE_TIMER_EVENTS = False  # Set to True to trace timer events like original
    SIMULATE_SERVICES = True    # Set to False to disable service simulation
    REALISTIC_TAKES = True      # Set to True for realistic failed takes
    RMW_TAKE_SUCCESS_RATE = 0.363  # Match real trace: 36.3% success rate

# =============================================================================
# SYSTEM CONTEXT AND OVERHEAD
# =============================================================================

class SystemContext:
    """Manages system-level context including CPU, memory, and network state"""
    def __init__(self):
        self.cpu_load = 0.0  # 0.0 to 1.0
        self.memory_pressure = 0.0  # 0.0 to 1.0
        self.network_latency_ms = 0.1  # Base network latency
        self.context_switches = 0
        self.last_cpu_assignments = {}  # Track last CPU for each thread
        
    def update_system_load(self):
        """Simulate dynamic system load changes"""
        self.cpu_load = min(1.0, max(0.0, self.cpu_load + random.gauss(0, 0.1)))
        self.memory_pressure = min(1.0, max(0.0, self.memory_pressure + random.gauss(0, 0.05)))
        self.network_latency_ms = max(0.1, self.network_latency_ms + random.gauss(0, 0.2))
        
    def get_context_switch_overhead(self):
        """Calculate context switch overhead"""
        base_overhead = random.gauss(0.02, 0.005)  # Base 20μs ± 5μs
        load_factor = 1.0 + self.cpu_load  # Higher load increases overhead
        self.context_switches += 1
        return base_overhead * load_factor
        
    def get_scheduling_delay(self):
        """Calculate scheduling delay based on system load"""
        base_delay = random.expovariate(1.0/0.01)  # Base 10μs average
        load_factor = 1.0 + (self.cpu_load * 2)  # Load has stronger effect on scheduling
        return base_delay * load_factor
        
    def assign_cpu(self, thread_id):
        """Simulate CPU assignment with affinity"""
        if thread_id in self.last_cpu_assignments:
            # 80% chance to keep same CPU
            if random.random() < 0.8:
                return self.last_cpu_assignments[thread_id]
        
        cpu_id = random.randint(0, 4)  # 5 CPUs (0-4)
        self.last_cpu_assignments[thread_id] = cpu_id
        return cpu_id

class SystemOverhead:
    """Calculates system-level overheads and delays"""
    def __init__(self, system_context: SystemContext):
        self.context = system_context
        self.cache_miss_rate = 0.1
        self.page_fault_rate = 0.01
        
    def calculate_overhead(self, operation_type: str) -> float:
        """Calculate total overhead for an operation"""
        total_overhead = 0.0
        
        # Base operation overhead
        if operation_type == "publish":
            total_overhead += random.gauss(0.0001, 0.00002)  # 100μs ± 20μs
        elif operation_type == "subscribe":
            total_overhead += random.gauss(0.00015, 0.00003)  # 150μs ± 30μs
        elif operation_type == "callback":
            total_overhead += random.gauss(0.0002, 0.00004)  # 200μs ± 40μs
            
        # Add context switch overhead if needed
        if random.random() < 0.3:  # 30% chance of context switch
            total_overhead += self.context.get_context_switch_overhead()
            
        # Add scheduling delay
        total_overhead += self.context.get_scheduling_delay()
            
        # Memory effects
        if random.random() < self.cache_miss_rate:
            total_overhead += random.gauss(0.0001, 0.00002)  # Cache miss: 100μs ± 20μs
        if random.random() < self.page_fault_rate:
            total_overhead += random.gauss(0.001, 0.0002)  # Page fault: 1ms ± 200μs
            
        # System load effect
        total_overhead *= (1.0 + self.context.cpu_load)
            
        return total_overhead

# Create global system context and overhead calculator
system_context = SystemContext()
system_overhead = SystemOverhead(system_context)

# =============================================================================
# QoS Policy System
# =============================================================================

class ReliabilityPolicy(Enum):
    RELIABLE = "RELIABLE"
    BEST_EFFORT = "BEST_EFFORT"

class DurabilityPolicy(Enum):
    TRANSIENT_LOCAL = "TRANSIENT_LOCAL"
    VOLATILE = "VOLATILE"

class HistoryPolicy(Enum):
    KEEP_LAST = "KEEP_LAST"
    KEEP_ALL = "KEEP_ALL"

@dataclass
class QoSProfile:
    """ROS2 QoS Profile configuration"""
    reliability: ReliabilityPolicy = ReliabilityPolicy.RELIABLE
    durability: DurabilityPolicy = DurabilityPolicy.VOLATILE
    history: HistoryPolicy = HistoryPolicy.KEEP_LAST
    depth: int = 10
    deadline_ms: float = 1000.0  # milliseconds
    lifespan_ms: float = 10000.0  # milliseconds
    
    def __str__(self):
        return f"QoS(rel={self.reliability.value}, dur={self.durability.value}, hist={self.history.value}:{self.depth})"

class QoSManager:
    """Manages QoS policies and their effects on message delivery"""
    
    @staticmethod
    def should_deliver_message(qos_profile: QoSProfile, msg_age_ms: float, 
                             delivery_attempts: int = 0) -> tuple[bool, str]:
        """Determine if message should be delivered based on QoS policies"""
        # Network conditions affect delivery probability
        network_reliability = max(0.5, 1.0 - (system_context.network_latency_ms / 100.0))
        
        # Check message lifespan with network jitter
        effective_age = msg_age_ms + random.gauss(0, system_context.network_latency_ms * 0.1)
        if effective_age > qos_profile.lifespan_ms:
            return False, "lifespan_exceeded"
        
        # Check deadline with network conditions
        deadline_violated = effective_age > qos_profile.deadline_ms
        
        # DDS-like reliability behavior
        if qos_profile.reliability == ReliabilityPolicy.RELIABLE:
            if deadline_violated:
                # Simulate DDS retries
                if delivery_attempts < 3:  # Max 3 retries
                    if random.random() < network_reliability:
                        return True, "deadline_missed_but_reliable_retry"
                    return False, "reliable_retry_needed"
                return True, "deadline_missed_but_reliable_final"
            return True, "reliable_delivery"
        else:
            # Best effort with network conditions
            if deadline_violated:
                return False, "deadline_missed"
            
            # Network quality affects success rate
            success_rate = network_reliability * (0.95 - (delivery_attempts * 0.1))
            if random.random() < success_rate:
                return True, "best_effort_success"
            return False, "best_effort_dropped"

    @staticmethod
    def calculate_network_latency(qos_profile: QoSProfile) -> float:
        """Calculate network transmission latency based on QoS and system state"""
        base_latency = system_context.network_latency_ms / 1000.0  # Convert to seconds
        
        # Add QoS-specific overhead
        if qos_profile.reliability == ReliabilityPolicy.RELIABLE:
            base_latency *= 1.2  # 20% overhead for reliable transport
        
        # Add system load effect
        base_latency *= (1.0 + system_context.cpu_load * 0.5)
        
        # Add random network jitter
        jitter = random.gauss(0, base_latency * 0.1)
        
        return max(0.0001, base_latency + jitter)  # Minimum 100μs

    @staticmethod
    def should_store_historical(qos_profile: QoSProfile) -> bool:
        """Determine if message should be stored for late joiners"""
        if qos_profile.durability == DurabilityPolicy.TRANSIENT_LOCAL:
            # Consider memory pressure
            if system_context.memory_pressure > 0.9:  # High memory pressure
                return random.random() > system_context.memory_pressure
            return True
        return False

# =============================================================================
#  Message Classes
# =============================================================================

class ROS2Message:
    """ ROS2 message with node context"""
    def __init__(self, message_id, data="Hello World", timestamp=0.0,
                 qos_profile: QoSProfile = None, topic_name="/topic",
                 source_node=None, source_process=None):
        self.message_id = message_id
        self.data = data
        self.timestamp = timestamp
        self.publish_time = 0.0
        self.take_time = 0.0
        self.qos_profile = qos_profile or QoSProfile()
        self.delivery_attempts = 0
        self.deadline_missed = False
        self.topic_name = topic_name
        self.source_node = source_node
        self.source_process = source_process
        self.destination_node = None  # NEW: track destination node

class TimerMessage:
    """Timer callback message"""
    def __init__(self, timer_id, period_ms=100.0):
        self.timer_id = timer_id
        self.period_ms = period_ms
        self.timestamp = time.time()

# =============================================================================
# Dynamic Context-Aware Trace Logger
# =============================================================================

@dataclass
class ExecutionContext:
    """Represents the execution context of a ROS2 component"""
    vtid: int          # Virtual Thread ID
    procname: str      # Process Name (NO TRUNCATION)
    vpid: int          # Virtual Process ID  
    cpu_id: int        # CPU Core ID
    node_name: str     # ROS2 Node Name

class ContextManager:
    """Manages execution contexts for different ROS2 components"""
    
    def __init__(self):
        self.contexts: Dict[str, ExecutionContext] = {}
        self.process_counter = 6900
        self.thread_counter = 1
        self.cpu_cores = [0, 1, 2, 3, 4]
        
    def register_node_context(self, node_name: str, process_name: str = None) -> ExecutionContext:
        """Register execution context for a ROS2 node"""
        if process_name is None:
            process_name = node_name
            
        context = ExecutionContext(
            vtid=self._get_next_thread_id(),
            procname=process_name,
            vpid=self._get_next_process_id(),
            cpu_id=random.choice(self.cpu_cores),
            node_name=node_name
        )
        
        self.contexts[f"node_{node_name}"] = context
        return context
    
    def register_publisher_context(self, node_name: str, topic_name: str) -> ExecutionContext:
        """Register execution context for a publisher"""
        node_key = f"node_{node_name}"
        if node_key not in self.contexts:
            self.register_node_context(node_name)
        
        context = ExecutionContext(
            vtid=self._get_next_thread_id(),
            procname=node_name,
            vpid=self.contexts[node_key].vpid,
            cpu_id=random.choice(self.cpu_cores),
            node_name=f"{node_name}_{topic_name}_pub"
        )
        
        self.contexts[f"pub_{node_name}_{topic_name}"] = context
        return context
    
    def register_subscriber_context(self, node_name: str, topic_name: str) -> ExecutionContext:
        """Register execution context for a subscriber"""
        node_key = f"node_{node_name}"
        if node_key not in self.contexts:
            self.register_node_context(node_name)
        
        context = ExecutionContext(
            vtid=self._get_next_thread_id(),
            procname=node_name,
            vpid=self.contexts[node_key].vpid,
            cpu_id=random.choice(self.cpu_cores),
            node_name=f"{node_name}_{topic_name}_sub"
        )
        
        self.contexts[f"sub_{node_name}_{topic_name}"] = context
        return context
    
    def register_timer_context(self, node_name: str, timer_name: str) -> ExecutionContext:
        """Register execution context for a timer"""
        node_key = f"node_{node_name}"
        if node_key not in self.contexts:
            self.register_node_context(node_name)
        
        context = ExecutionContext(
            vtid=self._get_next_thread_id(),
            procname=node_name,
            vpid=self.contexts[node_key].vpid,
            cpu_id=random.choice(self.cpu_cores),
            node_name=f"{node_name}_{timer_name}"
        )
        
        self.contexts[f"timer_{node_name}_{timer_name}"] = context
        return context
    
    def register_middleware_context(self, component_name: str, layer: str = "rmw") -> ExecutionContext:
        """Register execution context for middleware components"""
        # Use first node's vpid for middleware components
        vpid = list(self.contexts.values())[0].vpid if self.contexts else self._get_next_process_id()
        
        context = ExecutionContext(
            vtid=self._get_next_thread_id(),
            procname=list(self.contexts.values())[0].procname if self.contexts else "system",
            vpid=vpid,
            cpu_id=random.choice(self.cpu_cores),
            node_name=component_name
        )
        
        self.contexts[f"{layer}_{component_name}"] = context
        return context
    
    def register_system_context(self) -> ExecutionContext:
        """Register system initialization context"""
        context = ExecutionContext(
            vtid=self._get_next_thread_id(),
            procname="system",
            vpid=self._get_next_process_id(),
            cpu_id=random.choice(self.cpu_cores),
            node_name="system_init"
        )
        
        self.contexts["system"] = context
        return context
    
    def register_executor_context(self, executor_name: str = "main_executor") -> ExecutionContext:
        """Register execution context for executor"""
        # Use first node's process info
        base_context = list(self.contexts.values())[0] if self.contexts else None
        
        context = ExecutionContext(
            vtid=self._get_next_thread_id(),
            procname=base_context.procname if base_context else "ros2_executor",
            vpid=base_context.vpid if base_context else self._get_next_process_id(),
            cpu_id=random.choice(self.cpu_cores),
            node_name=executor_name
        )
        
        self.contexts["executor"] = context
        return context
    
    def get_context(self, component_key: str) -> Optional[ExecutionContext]:
        """Get execution context for a component"""
        return self.contexts.get(component_key)
    
    def _get_next_thread_id(self) -> int:
        tid = 6900 + self.thread_counter
        self.thread_counter += 1
        return tid
    
    def _get_next_process_id(self) -> int:
        pid = self.process_counter
        self.process_counter += 1
        return pid

class TraceLogger:
    """TraceLogger with dynamic context management"""
    
    def __init__(self):
        self.start_time = time.time()
        self.traces = []
        self.last_timestamp = 0.0
        self.context_manager = ContextManager()
        
    def log_event(self, event_name: str, fields: str, context_key: str = None, 
                  custom_context: ExecutionContext = None):
        """Log an event with proper execution context"""
        
        if custom_context:
            context = custom_context
        elif context_key:
            context = self.context_manager.get_context(context_key)
            if not context:
                raise ValueError(f"Unknown context key: {context_key}")
        else:
            context = ExecutionContext(6907, "default_proc", 6907, 2, "default")
        
        current_time = time.time() - self.start_time
        timestamp = self._format_timestamp(current_time)
        delta = self._calculate_delta(current_time)
        
        # Occasionally change CPU (matches real behavior)
        if random.random() < 0.03:
            context.cpu_id = random.choice([0, 1, 2, 3, 4])
        
        # Format procname with quotes properly
        procname_str = f'procname = "{context.procname}"'
        
        trace_line = (
            f"[{timestamp}] ({delta}) student-jetson ros2:{event_name}: "
            f"{{ cpu_id = {context.cpu_id} }}, "
            f"{{ {procname_str}, vtid = {context.vtid}, vpid = {context.vpid} }}, "
            f"{fields}"
        )
        
        self.traces.append(trace_line)
        print(trace_line)
        
    def _format_timestamp(self, current_time: float) -> str:
        hours = int(current_time // 3600) + 18
        minutes = int((current_time % 3600) // 60) + 44
        seconds = int(current_time % 60)
        nanoseconds = int((current_time % 1) * 1000000000)
        
        if nanoseconds >= 1000000000:
            nanoseconds -= 1000000000
            seconds += 1
            
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{nanoseconds:09d}"
    
    def _calculate_delta(self, current_time: float) -> str:
        if self.last_timestamp == 0.0:
            delta = "+?.?????????"
        else:
            delta_val = current_time - self.last_timestamp
            delta = f"+{delta_val:.9f}"
            
        self.last_timestamp = current_time
        return delta
    
    def register_system_context(self) -> str:
        context = self.context_manager.register_system_context()
        return "system"
    
    def register_node_context(self, node_name: str, process_name: str = None) -> str:
        context = self.context_manager.register_node_context(node_name, process_name)
        return f"node_{node_name}"
    
    def register_timer_context(self, node_name: str, timer_name: str) -> str:
        context = self.context_manager.register_timer_context(node_name, timer_name)
        return f"timer_{node_name}_{timer_name}"
    
    def register_publisher_context(self, node_name: str, topic_name: str) -> str:
        context = self.context_manager.register_publisher_context(node_name, topic_name)
        return f"pub_{node_name}_{topic_name}"
    
    def register_subscriber_context(self, node_name: str, topic_name: str) -> str:
        context = self.context_manager.register_subscriber_context(node_name, topic_name)
        return f"sub_{node_name}_{topic_name}"
    
    def register_middleware_context(self, component_name: str, layer: str = "rmw") -> str:
        context = self.context_manager.register_middleware_context(component_name, layer)
        return f"{layer}_{component_name}"
    
    def register_executor_context(self, executor_name: str = "main_executor") -> str:
        context = self.context_manager.register_executor_context(executor_name)
        return "executor"
    
    def save_traces(self, filename: str = "ros2_traces.csv"):
        with open(filename, 'w') as f:
            for trace in self.traces:
                f.write(trace + '\n')

# Global trace logger
trace_logger = TraceLogger()

# =============================================================================
# SYSTEM INITIALIZER
# =============================================================================

class SystemInitializer(AtomicDEVS):
    """ROS2 System Initializer - generates rcl_init event"""
    def __init__(self, name="SystemInit"):
        AtomicDEVS.__init__(self, name)
        self.state = {"phase": "uninitialized", "initialized": False}
        
        # Register system context
        self.context_key = trace_logger.register_system_context()
        
    def __lt__(self, other):
        return self.name < other.name
        
    def timeAdvance(self):
        if self.state["phase"] == "uninitialized":
            return 0.0
        return float('inf')
        
    def outputFnc(self):
        if self.state["phase"] == "uninitialized":
            trace_logger.log_event("rcl_init", 
                f'{{ context_handle = 0x{random.randint(0xAAAAA0000000, 0xAAAAAFFFFFFF):X}, '
                f'version = "4.1.1" }}',
                context_key=self.context_key)
        return {}
        
    def intTransition(self):
        if self.state["phase"] == "uninitialized":
            self.state["phase"] = "initialized"
            self.state["initialized"] = True
        return self.state

# =============================================================================
# APPLICATION LAYER
# =============================================================================

class Publisher(AtomicDEVS):
    """Publisher that includes node context in messages"""
    def __init__(self, name="Publisher", node_name="publisher_node",
                 topic_name="/topic", qos_profile: QoSProfile = None):
        AtomicDEVS.__init__(self, name)
        self.node_name = node_name
        self.topic_name = topic_name if topic_name.startswith('/') else '/' + topic_name
        self.qos_profile = qos_profile or QoSProfile()
        self.state = {"phase": "idle", "message_counter": 0, "initialized": False}

        # Register publisher execution context
        self.context_key = trace_logger.register_publisher_context(node_name, topic_name)

        # Ports
        self.outport = self.addOutPort("to_pub_rclcpp")
        
    def __lt__(self, other):
        return self.name < other.name
        
    def timeAdvance(self):
        if self.state["phase"] == "idle" and not self.state["initialized"]:
            return 0.05  
        elif self.state["phase"] == "publishing":
            # Frequency depends on QoS reliability
            if self.qos_profile.reliability == ReliabilityPolicy.RELIABLE:
                return 0.1  # 10Hz for reliable
            else:
                return 0.05  # 20Hz for best effort
        return float('inf')

    def outputFnc(self):
        if self.state["phase"] == "idle" and not self.state["initialized"]:
            # Include node_handle and publisher_handle
            trace_logger.log_event("rclcpp_callback_register",
                                   f'{{ symbol = "publish_{self.topic_name}" }}',
                                   context_key=self.context_key)
            trace_logger.log_event("rcl_publisher_init",
                                   f'{{ publisher_handle = 0x{random.randint(0xFFFFD0000000, 0xFFFFDFFFFFFF):X}, '
                                   f'node_handle = 0x{random.randint(0xAAAAA0000000, 0xAAAAAFFFFFFF):X}, '
                                   f'topic_name = "{self.topic_name}", qos = "{self.qos_profile}" }}',
                                   context_key=self.context_key)
        elif self.state["phase"] == "publishing":
            msg = ROS2Message(
                message_id=self.state["message_counter"],
                timestamp=self.time_next,
                qos_profile=self.qos_profile,
                topic_name=self.topic_name,
                source_node=self.node_name,
                source_process=self.node_name
            )
            return {self.outport: msg}
        return {}
        
    def intTransition(self):
        if self.state["phase"] == "idle" and not self.state["initialized"]:
            self.state["initialized"] = True
            self.state["phase"] = "publishing"
        elif self.state["phase"] == "publishing":
            self.state["message_counter"] += 1
        return self.state

class Subscriber(AtomicDEVS):
    """Subscriber application with QoS policies and working callbacks"""
    def __init__(self, name="Subscriber", node_name="subscriber_node", 
                 topic_name="/topic", qos_profile: QoSProfile = None):
        AtomicDEVS.__init__(self, name)
        self.node_name = node_name
        self.topic_name = topic_name if topic_name.startswith('/') else '/' + topic_name
        self.qos_profile = qos_profile or QoSProfile()
        self.state = {
            "phase": "idle", 
            "initialized": False, 
            "message_history": [], 
            "deadline_violations": 0,
            "current_message": None
        }
        
        # Register subscriber execution context
        self.context_key = trace_logger.register_subscriber_context(node_name, topic_name)
        
        # Ports
        self.inport = self.addInPort("from_sub_rclcpp")
        
    def __lt__(self, other):
        return self.name < other.name
        
    def timeAdvance(self):
        if self.state["phase"] == "idle" and not self.state["initialized"]:
            return 0.05
        elif self.state["phase"] == "executing_callback":
            # Realistic callback duration: 200-400μs
            base_duration = random.gauss(300, 80)  # 300μs ± 80μs
            if self.qos_profile.reliability == ReliabilityPolicy.RELIABLE:
                base_duration += 100
            return max(50, base_duration) / 1000000  # Convert to seconds
        return float('inf')
        
    def outputFnc(self):
        if self.state["phase"] == "idle" and not self.state["initialized"]:
            # Register callback
            trace_logger.log_event("rclcpp_callback_register", 
                                 f'{{ symbol = "subscribe_{self.topic_name}" }}', 
                                 context_key=self.context_key)
            trace_logger.log_event("rcl_subscription_init", 
                                 f'{{ topic_name = "{self.topic_name}", qos = "{self.qos_profile}" }}', 
                                 context_key=self.context_key)
        return {}
        
    def intTransition(self):
        if self.state["phase"] == "idle" and not self.state["initialized"]:
            self.state["initialized"] = True
        elif self.state["phase"] == "executing_callback":
            # Generate callback_end event
            trace_logger.log_event("callback_end", 
                                 f'{{ message_id = {self.state["current_message"].message_id} }}', 
                                 context_key=self.context_key)
            self.state["phase"] = "idle"
            self.state["current_message"] = None
        return self.state
        
    def extTransition(self, inputs):
        if self.inport in inputs:
            msg = inputs[self.inport]
            if isinstance(msg, ROS2Message):
                # Check QoS constraints
                msg_age = (self.time_next[0] - msg.timestamp[0]) * 1000
                
                # Only log deadline violations if configured
                if msg_age > self.qos_profile.deadline_ms and not SimulationConfig.REALISTIC_TAKES:
                    self.state["deadline_violations"] += 1
                    msg.deadline_missed = True
                    trace_logger.log_event("rclcpp_subscription_deadline_missed", 
                                         f'{{ message_id = {msg.message_id}, age_ms = {msg_age:.2f} }}', 
                                         context_key=self.context_key)
                
                # Manage message history
                if self.qos_profile.history == HistoryPolicy.KEEP_LAST:
                    if len(self.state["message_history"]) >= self.qos_profile.depth:
                        self.state["message_history"].pop(0)
                
                self.state["message_history"].append(msg)
                self.state["current_message"] = msg
                self.state["phase"] = "executing_callback"
                
                # Generate callback_start event
                trace_logger.log_event("callback_start", 
                                     f'{{ message_id = {msg.message_id} }}', 
                                     context_key=self.context_key)
        return self.state

class Timer(AtomicDEVS):
    """ROS2 Timer with periodic callbacks"""
    def __init__(self, name="Timer", node_name="timer_node", timer_name="main_timer", 
                 period_ms=100.0):
        AtomicDEVS.__init__(self, name)
        self.node_name = node_name
        self.timer_name = timer_name
        self.period_ms = period_ms
        self.state = {"phase": "idle", "callback_count": 0, "initialized": False}
        
        # Register timer execution context
        self.context_key = trace_logger.register_timer_context(node_name, timer_name)
        
        # Ports
        self.outport = self.addOutPort("timer_callback")
        
    def __lt__(self, other):
        return self.name < other.name
        
    def timeAdvance(self):
        if self.state["phase"] == "idle" and not self.state["initialized"]:
            return 0.05
        elif self.state["phase"] == "waiting":
            return self.period_ms / 1000.0
        elif self.state["phase"] == "executing_callback":
            duration = random.gauss(150, 50)
            return max(20, duration) / 1000000
        return float('inf')
        
    def outputFnc(self):
        if self.state["phase"] == "idle" and not self.state["initialized"]:
            if SimulationConfig.TRACE_TIMER_EVENTS:
                trace_logger.log_event("rcl_timer_init", 
                                     f'{{ period = {self.period_ms}, timer_handle = 0x{random.randint(0x10000000, 0xFFFFFFFF):X} }}', 
                                     context_key=self.context_key)
                trace_logger.log_event("rclcpp_timer_callback_added", "{ }", context_key=self.context_key)
                trace_logger.log_event("rclcpp_timer_link_node", f'{{ node_name = "{self.node_name}" }}', context_key=self.context_key)
        elif self.state["phase"] == "waiting":
            if SimulationConfig.TRACE_TIMER_EVENTS:
                trace_logger.log_event("rcl_timer_call", 
                                     f'{{ timer_handle = 0x{random.randint(0x10000000, 0xFFFFFFFF):X} }}', 
                                     context_key=self.context_key)
            return {self.outport: TimerMessage(self.timer_name, self.period_ms)}
        return {}
        
    def intTransition(self):
        if self.state["phase"] == "idle" and not self.state["initialized"]:
            self.state["initialized"] = True
            self.state["phase"] = "waiting"
        elif self.state["phase"] == "waiting":
            self.state["phase"] = "executing_callback"
        elif self.state["phase"] == "executing_callback":
            if SimulationConfig.TRACE_TIMER_EVENTS:
                trace_logger.log_event("rclcpp_timer_callback_start", "{ }", context_key=self.context_key)
                trace_logger.log_event("rclcpp_timer_callback_end", "{ }", context_key=self.context_key)
            self.state["callback_count"] += 1
            self.state["phase"] = "waiting"
        return self.state

class Node(AtomicDEVS):
    """ROS2 Node that manages publishers, subscribers, timers"""
    def __init__(self, name="Node", node_name="ros2_node"):
        AtomicDEVS.__init__(self, name)
        self.node_name = node_name
        self.state = {
            "phase": "inactive", 
            "lifecycle_state": "unconfigured",
            "pending_operations": []
        }
        
        # Register node execution context
        self.context_key = trace_logger.register_node_context(node_name)
        
        # Ports
        self.timer_inport = self.addInPort("from_timers")
        
    def __lt__(self, other):
        return self.name < other.name
        
    def timeAdvance(self):
        if self.state["phase"] == "inactive":
            return 0.1
        elif self.state["phase"] == "configuring":
            return 0.05
        elif self.state["phase"] == "activating":
            return 0.02
        elif self.state["phase"] == "active":
            return 1.0
        elif self.state["phase"] == "processing_callback":
            duration = random.gauss(200, 75)
            return max(30, duration) / 1000000
        return float('inf')
        
    def outputFnc(self):
        if self.state["phase"] == "inactive":
            trace_logger.log_event("rcl_node_init", 
                                 f'{{ node_name = "{self.node_name}", namespace = "/" }}', 
                                 context_key=self.context_key)
        return {}
        
    def intTransition(self):
        if self.state["phase"] == "inactive":
            self.state["phase"] = "active"
            self.state["lifecycle_state"] = "active"
        elif self.state["phase"] == "processing_callback":
            self.state["phase"] = "active"
        return self.state
        
    def extTransition(self, inputs):
        if self.timer_inport in inputs:
            timer_msg = inputs[self.timer_inport]
            if isinstance(timer_msg, TimerMessage):
                self.state["phase"] = "processing_callback"
                if SimulationConfig.TRACE_TIMER_EVENTS:
                    trace_logger.log_event("rclcpp_node_timer_callback", 
                                         f'{{ node_name = "{self.node_name}", timer_id = "{timer_msg.timer_id}" }}', 
                                         context_key=self.context_key)
        return self.state

# =============================================================================
# SERVICE SUPPORT 
# =============================================================================

class Service(AtomicDEVS):
    """ROS2 Service model"""
    def __init__(self, name="Service", node_name="node", service_type="get_parameters"):
        AtomicDEVS.__init__(self, name)
        self.node_name = node_name
        self.service_type = service_type
        self.service_name = f"/{node_name}/{service_type}"
        self.state = {"phase": "idle", "initialized": False}
        
        # Use node's context
        self.context_key = f"node_{node_name}"
        
    def __lt__(self, other):
        return self.name < other.name
        
    def timeAdvance(self):
        if not self.state["initialized"]:
            return 0.1
        return float('inf')
        
    def outputFnc(self):
        if not self.state["initialized"]:
            trace_logger.log_event("rcl_service_init",
                f'{{ service_name = "{self.service_name}" }}',
                context_key=self.context_key)
            trace_logger.log_event("rclcpp_service_callback_added",
                f'{{ service_name = "{self.service_name}" }}',
                context_key=self.context_key)
            trace_logger.log_event("rclcpp_callback_register",
                f'{{ symbol = "service_{self.service_type}" }}',
                context_key=self.context_key)
        return {}
        
    def intTransition(self):
        if not self.state["initialized"]:
            self.state["initialized"] = True
        return self.state

# =============================================================================
# RCLCPP LAYER ( message processing)
# =============================================================================

class RclcppLayer(AtomicDEVS):
    """ rclcpp layer that properly handles all rclcpp operations"""
    def __init__(self, name="RclcppLayer"):
        AtomicDEVS.__init__(self, name)
        self.state = {
            "phase": "idle",
            "pending_operations": [],
            "initialized_entities": set()
        }

        # Generic ports for all operations
        self.pub_inputs = {}  # Dictionary of publisher input ports
        self.sub_outputs = {}  # Dictionary of subscriber output ports

        # To/from RCL layer
        self.to_rcl = self.addOutPort("to_rcl")
        self.from_rcl = self.addInPort("from_rcl")

    def add_publisher_port(self, topic_name):
        """Add a publisher input port for a topic"""
        port_name = f"pub_{topic_name.replace('/', '_')}"
        self.pub_inputs[topic_name] = self.addInPort(port_name)
        return self.pub_inputs[topic_name]

    def add_subscriber_port(self, topic_name):
        """Add a subscriber output port for a topic"""
        port_name = f"sub_{topic_name.replace('/', '_')}"
        self.sub_outputs[topic_name] = self.addOutPort(port_name)
        return self.sub_outputs[topic_name]

    def __lt__(self, other):
        return self.name < other.name

    def timeAdvance(self):
        if self.state["pending_operations"]:
            return 0.0005  # Process operations quickly
        return float('inf')

    def outputFnc(self):
        if self.state["pending_operations"]:
            op_type, msg, source_port = self.state["pending_operations"][0]

            if op_type == "publish":
                # Use the message's source node context
                context_key = f"pub_{msg.source_node}_{msg.topic_name}"

                trace_logger.log_event("rclcpp_publish",
                                       f'{{ message_id = {msg.message_id}, topic = "{msg.topic_name}" }}',
                                       context_key=context_key)

                # Initialize subscription if first time
                entity_key = f"sub_{msg.topic_name}"
                if entity_key not in self.state["initialized_entities"]:
                    trace_logger.log_event("rclcpp_subscription_init", "{ }", context_key=context_key)
                    trace_logger.log_event("rclcpp_subscription_callback_added", "{ }", context_key=context_key)
                    self.state["initialized_entities"].add(entity_key)

                # Forward to RCL layer
                return {self.to_rcl: msg}

            elif op_type == "take":
                # Message coming from RCL layer to subscriber
                context_key = f"sub_{msg.destination_node}_{msg.topic_name}"

                trace_logger.log_event("rclcpp_take",
                                       f'{{ message = 0x{random.randint(0x1000, 0xFFFF):X} }}',
                                       context_key=context_key)

                # Route to appropriate subscriber
                if msg.topic_name in self.sub_outputs:
                    return {self.sub_outputs[msg.topic_name]: msg}

        return {}

    def intTransition(self):
        if self.state["pending_operations"]:
            self.state["pending_operations"].pop(0)
        return self.state

    def extTransition(self, inputs):
        # Handle publisher inputs
        for topic, port in self.pub_inputs.items():
            if port in inputs:
                msg = inputs[port]
                self.state["pending_operations"].append(("publish", msg, port))

        # Handle RCL inputs (messages coming back for subscribers)
        if self.from_rcl in inputs:
            msg = inputs[self.from_rcl]
            self.state["pending_operations"].append(("take", msg, self.from_rcl))

        return self.state

# =============================================================================
# RCL LAYER ( message forwarding)
# =============================================================================

class RclLayer(AtomicDEVS):
    """ RCL layer that properly forwards messages to RMW"""
    def __init__(self, name="RclLayer"):
        AtomicDEVS.__init__(self, name)
        self.state = {
            "phase": "idle",
            "pending_operations": []
        }

        # Ports
        self.from_rclcpp = self.addInPort("from_rclcpp")
        self.to_rclcpp = self.addOutPort("to_rclcpp")
        self.to_rmw = self.addOutPort("to_rmw")
        self.from_rmw = self.addInPort("from_rmw")

    def __lt__(self, other):
        return self.name < other.name

    def timeAdvance(self):
        if self.state["pending_operations"]:
            return 0.0003  # Fast processing
        return float('inf')

    def outputFnc(self):
        if self.state["pending_operations"]:
            op_type, msg, direction = self.state["pending_operations"][0]

            if direction == "down" and op_type == "publish":
                # Publishing: rclcpp → rcl → rmw
                context_key = f"pub_{msg.source_node}_{msg.topic_name}"

                trace_logger.log_event("rcl_publish",
                                       f'{{ message_id = {msg.message_id}, '
                                       f'publisher_handle = 0x{random.randint(0xFFFFD0000000, 0xFFFFDFFFFFFF):X}, '
                                       f'node_handle = 0x{random.randint(0xAAAAA0000000, 0xAAAAAFFFFFFF):X} }}',
                                       context_key=context_key)

                # Actually forward message to RMW layer
                return {self.to_rmw: msg}

            elif direction == "up" and op_type == "take":
                # Taking: rmw → rcl → rclcpp
                context_key = f"sub_{msg.destination_node}_{msg.topic_name}"

                trace_logger.log_event("rcl_take",
                                       f'{{ message = 0x{random.randint(0x1000, 0xFFFF):X} }}',
                                       context_key=context_key)

                return {self.to_rclcpp: msg}

        return {}

    def intTransition(self):
        if self.state["pending_operations"]:
            self.state["pending_operations"].pop(0)
        return self.state

    def extTransition(self, inputs):
        if self.from_rclcpp in inputs:
            # Message going down from rclcpp to rmw
            msg = inputs[self.from_rclcpp]
            self.state["pending_operations"].append(("publish", msg, "down"))

        if self.from_rmw in inputs:
            # Message coming up from rmw to rclcpp
            msg = inputs[self.from_rmw]
            self.state["pending_operations"].append(("take", msg, "up"))

        return self.state

# =============================================================================
# RMW LAYER (message delivery)
# =============================================================================

class RmwLayer(AtomicDEVS):
    """ RMW layer with working DDS behavior and message delivery"""
    def __init__(self, name="RmwLayer"):
        AtomicDEVS.__init__(self, name)
        self.state = {
            "phase": "idle",
            "pending_pub_msgs": [],
            "published_msgs": [],
            "failed_deliveries": [],
            "subscriber_contexts": {},
            "rmw_publishers": {},  # Track RMW publishers
            "take_attempts": 0,
            "successful_takes": 0
        }

        # Ports
        self.inport_pub = self.addInPort("from_rcl")
        self.outport_sub = self.addOutPort("to_rcl")
        
    def register_subscriber(self, topic_name, node_name):
        """Register subscriber with DDS discovery"""
        if topic_name not in self.state["subscriber_contexts"]:
            self.state["subscriber_contexts"][topic_name] = []
        self.state["subscriber_contexts"][topic_name].append(node_name)
        
        # Log subscriber registration
        sub_context_key = f"sub_{node_name}_{topic_name}"
        trace_logger.log_event("rmw_subscription_init",
            f'{{ topic_name = "{topic_name}", '
            f'rmw_subscription_handle = 0x{random.randint(0xAAAAA0000000, 0xAAAAAFFFFFFF):X}, '
            f'gid = [ {", ".join(f"[{i}] = {random.randint(0, 255)}" for i in range(24))} ] }}',
            context_key=sub_context_key)

    def __lt__(self, other):
        return self.name < other.name

    def timeAdvance(self):
        if self.state["phase"] == "publishing" and self.state["pending_pub_msgs"]:
            return 0.0001  # Fast publishing
        elif self.state["phase"] == "delivering" and self.state["published_msgs"]:
            return 0.001   # Simulate delivery attempts
        elif self.state["phase"] == "idle" and (self.state["published_msgs"] or self.state["failed_deliveries"]):
            return 0.0005  # Fast retry
        return float('inf')

    def outputFnc(self):
        if self.state["phase"] == "publishing" and self.state["pending_pub_msgs"]:
            msg = self.state["pending_pub_msgs"][0]
            msg.publish_time = self.time_next

            # Use publisher's node context
            pub_context_key = f"pub_{msg.source_node}_{msg.topic_name}"

            # Generate rmw_publisher_init if first time for this topic
            if msg.topic_name not in self.state["rmw_publishers"]:
                gid = [random.randint(0, 255) for _ in range(24)]
                gid[0] = 1  # Standard DDS GID format
                gid[1] = 15
                
                trace_logger.log_event("rmw_publisher_init",
                                       f'{{ rmw_publisher_handle = 0x{random.randint(0xAAAAA0000000, 0xAAAAAFFFFFFF):X}, '
                                       f'gid = [ {", ".join(f"[{i}] = {v}" for i, v in enumerate(gid))} ] }}',
                                       context_key=pub_context_key)
                self.state["rmw_publishers"][msg.topic_name] = True

            # Generate rmw_publish event
            trace_logger.log_event("rmw_publish",
                                   f'{{ message = 0x{random.randint(0xFFFFD0000000, 0xFFFFDFFFFFFF):X} }}',
                                   context_key=pub_context_key)

            self.state["published_msgs"].append(msg)
            return {}

        elif self.state["phase"] == "delivering" and self.state["published_msgs"]:
            msg = self.state["published_msgs"][0]
            subscriber_nodes = self.state["subscriber_contexts"].get(msg.topic_name, [])

            if subscriber_nodes:
                # Pick a subscriber to attempt delivery
                sub_node = random.choice(subscriber_nodes)
                sub_context_key = f"sub_{sub_node}_{msg.topic_name}"
                
                self.state["take_attempts"] += 1
                
                # Generate realistic rmw_take events with success/failure
                success_rate = SimulationConfig.RMW_TAKE_SUCCESS_RATE
                taken = 1 if random.random() < success_rate else 0
                
                if taken:
                    self.state["successful_takes"] += 1
                    
                trace_logger.log_event("rmw_take",
                    f'{{ rmw_subscription_handle = 0x{random.randint(0xAAAAA0000000, 0xAAAAAFFFFFFF):X}, '
                    f'message = 0x{random.randint(0xFFFF00000000, 0xFFFFFFFFFFFF):X}, '
                    f'source_timestamp = {msg.publish_time[0] if hasattr(msg.publish_time, "__getitem__") else msg.publish_time:.9f}, '
                    f'taken = {taken} }}',
                    context_key=sub_context_key)

                if taken:
                    # Successful delivery - send to subscriber
                    msg.destination_node = sub_node
                    self.state["published_msgs"].remove(msg)
                    return {self.outport_sub: msg}
                else:
                    # Failed take - try again later
                    if msg.delivery_attempts < 5:  # Max retries
                        msg.delivery_attempts += 1
                        return {}
                    else:
                        # Give up on this message
                        self.state["published_msgs"].remove(msg)
                        return {}
            else:
                # No subscribers - drop message
                self.state["published_msgs"].remove(msg)
                return {}

        return {}
        
    def intTransition(self):
        if self.state["phase"] == "publishing" and self.state["pending_pub_msgs"]:
            self.state["pending_pub_msgs"].pop(0)
            if not self.state["pending_pub_msgs"]:
                self.state["phase"] = "idle"
        elif self.state["phase"] == "delivering":
            self.state["phase"] = "idle"
        elif self.state["phase"] == "idle":
            if self.state["published_msgs"]:
                self.state["phase"] = "delivering"
            elif self.state["pending_pub_msgs"]:
                self.state["phase"] = "publishing"
        return self.state
        
    def extTransition(self, inputs):
        if self.inport_pub in inputs:
            msg = inputs[self.inport_pub]
            if isinstance(msg, ROS2Message):
                self.state["pending_pub_msgs"].append(msg)
                if self.state["phase"] == "idle":
                    self.state["phase"] = "publishing"
        return self.state

# =============================================================================
# EXECUTOR MODEL
# =============================================================================

class Executor(AtomicDEVS):
    """Executor that runs in the context of nodes it's serving"""
    def __init__(self, name="Executor", node_contexts=None):
        AtomicDEVS.__init__(self, name)
        self.state = {
            "phase": "waiting",
            "cycle_count": 0,
            "current_node_index": 0,
            "node_contexts": node_contexts or []
        }

        # Register executor context
        self.context_key = trace_logger.register_executor_context("single_threaded")
        
    def __lt__(self, other):
        return self.name < other.name

    def timeAdvance(self):
        if self.state["phase"] == "waiting":
            return random.uniform(0.005, 0.025)
        elif self.state["phase"] == "getting_ready":
            return 0.0008
        elif self.state["phase"] == "executing":
            return random.uniform(0.001, 0.006)
        return float('inf')

    def outputFnc(self):
        # Rotate through nodes
        if self.state["node_contexts"]:
            current_node = self.state["node_contexts"][self.state["current_node_index"]]
            node_context_key = f"node_{current_node}"
        else:
            node_context_key = "executor"

        if self.state["phase"] == "waiting":
            trace_logger.log_event("rclcpp_executor_wait_for_work",
                                   "{ }",
                                   context_key=node_context_key)
        elif self.state["phase"] == "getting_ready":
            trace_logger.log_event("rclcpp_executor_get_next_ready",
                                   "{ }",
                                   context_key=node_context_key)
        elif self.state["phase"] == "executing":
            trace_logger.log_event("rclcpp_executor_execute",
                                   f'{{ handle = 0x{random.randint(0x10000000, 0xFFFFFFFF):X} }}',
                                   context_key=node_context_key)
        return {}

    def intTransition(self):
        if self.state["phase"] == "waiting":
            self.state["phase"] = "getting_ready"
        elif self.state["phase"] == "getting_ready":
            rand_val = random.random()
            if rand_val < 0.3:
                self.state["phase"] = "executing"
            else:
                self.state["phase"] = "waiting"
                # Move to next node
                if self.state["node_contexts"]:
                    self.state["current_node_index"] = (self.state["current_node_index"] + 1) % len(self.state["node_contexts"])
            self.state["cycle_count"] += 1
        elif self.state["phase"] == "executing":
            self.state["phase"] = "waiting"
        return self.state

# =============================================================================
#  LAYERED SYSTEM
# =============================================================================

class LayeredROS2System(CoupledDEVS):
    """ system with working end-to-end message flow"""
    def __init__(self, name="LayeredROS2System"):
        CoupledDEVS.__init__(self, name)

        # === SYSTEM INITIALIZATION ===
        self.system_init = self.addSubModel(SystemInitializer())

        # === NODES ===
        self.map_server_node = self.addSubModel(Node("MapServerNode", "dummy_map_server"))
        self.laser_node = self.addSubModel(Node("LaserNode", "dummy_laser"))
        self.joint_state_node = self.addSubModel(Node("JointStateNode", "dummy_joint_states"))
        self.robot_state_node = self.addSubModel(Node("RobotStateNode", "robot_state_publisher"))

        # === QOS PROFILES ===
        map_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )

        scan_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        joint_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=5
        )

        # === APPLICATION LAYER ===
        # Publishers
        self.map_publisher = self.addSubModel(
            Publisher("MapPublisher", "dummy_map_server", "/map", map_qos)
        )
        self.scan_publisher = self.addSubModel(
            Publisher("ScanPublisher", "dummy_laser", "/scan", scan_qos)
        )
        self.joint_publisher = self.addSubModel(
            Publisher("JointPublisher", "dummy_joint_states", "/joint_states", joint_qos)
        )

        # System topic publishers
        self.rosout_pub_map = self.addSubModel(
            Publisher("RosoutPubMap", "dummy_map_server", "/rosout", map_qos)
        )
        self.rosout_pub_robot = self.addSubModel(
            Publisher("RosoutPubRobot", "robot_state_publisher", "/rosout", map_qos)
        )
        self.param_pub_map = self.addSubModel(
            Publisher("ParamPubMap", "dummy_map_server", "/parameter_events", map_qos)
        )
        self.param_pub_robot = self.addSubModel(
            Publisher("ParamPubRobot", "robot_state_publisher", "/parameter_events", map_qos)
        )

        # Subscribers
        self.joint_subscriber = self.addSubModel(
            Subscriber("JointSubscriber", "robot_state_publisher", "/joint_states", joint_qos)
        )
        self.param_sub_map = self.addSubModel(
            Subscriber("ParamSubMap", "dummy_map_server", "/parameter_events", map_qos)
        )
        self.param_sub_robot = self.addSubModel(
            Subscriber("ParamSubRobot", "robot_state_publisher", "/parameter_events", map_qos)
        )
        self.param_sub_laser = self.addSubModel(
            Subscriber("ParamSubLaser", "dummy_laser", "/parameter_events", map_qos)
        )

        # === LAYERS ===
        # Single RCLCPP layer for all operations
        self.rclcpp_layer = self.addSubModel(RclcppLayer("RclcppLayer"))

        # Configure RCLCPP layer ports for all topics
        topics = ["/map", "/scan", "/joint_states", "/rosout", "/parameter_events"]
        for topic in topics:
            self.rclcpp_layer.add_publisher_port(topic)
            self.rclcpp_layer.add_subscriber_port(topic)

        # Single RCL layer for all operations
        self.rcl_layer = self.addSubModel(RclLayer("RclLayer"))

        #  RMW layer
        self.rmw_layer = self.addSubModel(RmwLayer("RmwLayer"))

        # Register subscribers with RMW layer
        self.rmw_layer.register_subscriber("/joint_states", "robot_state_publisher")
        self.rmw_layer.register_subscriber("/parameter_events", "dummy_map_server")
        self.rmw_layer.register_subscriber("/parameter_events", "robot_state_publisher")
        self.rmw_layer.register_subscriber("/parameter_events", "dummy_laser")

        # === EXECUTOR ===
        self.executor = self.addSubModel(
            Executor("Executor",
                     node_contexts=["dummy_map_server", "robot_state_publisher",
                                    "dummy_laser", "dummy_joint_states"])
        )

        # === SERVICES ===
        if SimulationConfig.SIMULATE_SERVICES:
            service_types = ["get_parameters", "set_parameters", "list_parameters",
                             "describe_parameters", "get_parameter_types", "set_parameters_atomically"]

            for node_name in ["dummy_map_server", "robot_state_publisher"]:
                for service_type in service_types:
                    service = self.addSubModel(
                        Service(f"{node_name}_{service_type}_service", node_name, service_type)
                    )

        # === TIMERS ===
        self.map_timer = self.addSubModel(
            Timer("MapTimer", "dummy_map_server", "map_timer", 1000.0)  # 1Hz
        )
        self.scan_timer = self.addSubModel(
            Timer("ScanTimer", "dummy_laser", "scan_timer", 25.0)  # 40Hz
        )
        self.joint_timer = self.addSubModel(
            Timer("JointTimer", "dummy_joint_states", "joint_timer", 33.0)  # ~30Hz
        )

        # === CONNECTIONS ===

        # Connect publishers to RCLCPP layer
        self.connectPorts(self.map_publisher.outport, self.rclcpp_layer.pub_inputs["/map"])
        self.connectPorts(self.scan_publisher.outport, self.rclcpp_layer.pub_inputs["/scan"])
        self.connectPorts(self.joint_publisher.outport, self.rclcpp_layer.pub_inputs["/joint_states"])
        self.connectPorts(self.rosout_pub_map.outport, self.rclcpp_layer.pub_inputs["/rosout"])
        self.connectPorts(self.rosout_pub_robot.outport, self.rclcpp_layer.pub_inputs["/rosout"])
        self.connectPorts(self.param_pub_map.outport, self.rclcpp_layer.pub_inputs["/parameter_events"])
        self.connectPorts(self.param_pub_robot.outport, self.rclcpp_layer.pub_inputs["/parameter_events"])

        # Connect RCLCPP layer to subscribers
        self.connectPorts(self.rclcpp_layer.sub_outputs["/joint_states"], self.joint_subscriber.inport)
        self.connectPorts(self.rclcpp_layer.sub_outputs["/parameter_events"], self.param_sub_map.inport)
        self.connectPorts(self.rclcpp_layer.sub_outputs["/parameter_events"], self.param_sub_robot.inport)
        self.connectPorts(self.rclcpp_layer.sub_outputs["/parameter_events"], self.param_sub_laser.inport)

        # Connect layers properly: RCLCPP ↔ RCL ↔ RMW
        self.connectPorts(self.rclcpp_layer.to_rcl, self.rcl_layer.from_rclcpp)
        self.connectPorts(self.rcl_layer.to_rclcpp, self.rclcpp_layer.from_rcl)
        self.connectPorts(self.rcl_layer.to_rmw, self.rmw_layer.inport_pub)
        self.connectPorts(self.rmw_layer.outport_sub, self.rcl_layer.from_rmw)

        # Connect timers to nodes
        self.connectPorts(self.map_timer.outport, self.map_server_node.timer_inport)
        self.connectPorts(self.scan_timer.outport, self.laser_node.timer_inport)
        self.connectPorts(self.joint_timer.outport, self.joint_state_node.timer_inport)

# =============================================================================
# Main Simulation with Analysis
# =============================================================================

def analyze_results(model: LayeredROS2System):
    """ analysis comparing with real trace patterns"""
    traces = trace_logger.traces
    
    # event counting
    event_counts = {}
    for trace in traces:
        match = trace.split("ros2:")[1].split(":")[0]
        event_counts[match] = event_counts.get(match, 0) + 1
    
    # Key metrics matching real trace analysis
    rmw_publishes = event_counts.get("rmw_publish", 0)
    rmw_takes = event_counts.get("rmw_take", 0) 
    callbacks = event_counts.get("callback_start", 0) + event_counts.get("callback_end", 0)
    
    print("\n📊 MODEL ANALYSIS")
    print("=" * 70)
    
    print("\n1. Critical Events Status:")
    print("-" * 50)
    print(f"✅ rmw_publish events: {rmw_publishes}")
    print(f"✅ rmw_take events: {rmw_takes}")
    print(f"✅ callback events: {callbacks}")
    print(f"✅ rclcpp_publish: {event_counts.get('rclcpp_publish', 0)}")
    print(f"✅ rcl_publish: {event_counts.get('rcl_publish', 0)}")
    
    # Calculate success metrics like real trace
    if rmw_takes > 0:
        # Count successful takes by looking for taken=1 in traces
        successful_takes = sum(1 for trace in traces if "rmw_take" in trace and "taken = 1" in trace)
        success_rate = (successful_takes / rmw_takes) * 100
        print(f"\n2. Message Delivery Analysis:")
        print(f"   Take success rate: {success_rate:.1f}%")
        print(f"   Successful takes: {successful_takes}")
        print(f"   Failed takes: {rmw_takes - successful_takes}")
    
    print("\n3. Event Type Summary:")
    print("-" * 50)
    for event, count in sorted(event_counts.items()):
        if count > 0:
            print(f"{event}: {count}")
    
    print("\n🎯 VALIDATION RESULTS:")
    validation_score = 0
    total_checks = 5
    
    if rmw_publishes > 0:
        print("✅ RMW publish events generated")
        validation_score += 1
    if rmw_takes > 0:
        print("✅ RMW take events generated") 
        validation_score += 1
    if callbacks > 0:
        print("✅ Callback events generated")
        validation_score += 1
    if event_counts.get("rclcpp_publish", 0) > 0:
        print("✅ RCLCPP publish events generated")
        validation_score += 1
    if event_counts.get("rcl_publish", 0) > 0:
        print("✅ RCL publish events generated")
        validation_score += 1
    
    print(f"\n🏆 VALIDATION SCORE: {validation_score}/{total_checks} ({validation_score/total_checks*100:.0f}%)")
    
    if validation_score == total_checks:
        print("🎉 EXCELLENT! All critical message flow events are working!")
    elif validation_score >= 3:
        print("🎯 GOOD! Major components working, minor issues remain")
    else:
        print("⚠️ NEEDS WORK: Critical message flow still broken")

def main():
    print("🚀 Starting ROS2 DEVS Simulation")
    print("   WITH complete end-to-end message flow:")
    print("   ✅ RCL → RMW connection")
    print("   ✅ Working rmw_publish events")
    print("   ✅ Realistic rmw_take with 36.3% success rate")
    print("   ✅ Full subscriber callback execution")
    print("=" * 70)
    
    # Configure simulation for realistic behavior
    SimulationConfig.TRACE_TIMER_EVENTS = False
    SimulationConfig.SIMULATE_SERVICES = True
    SimulationConfig.REALISTIC_TAKES = True
    
    # Create and initialize the  system model
    model = LayeredROS2System("LayeredROS2")
    
    # Create and configure simulator
    sim = Simulator(model)
    sim.setClassicDEVS()
    #sim.setVerbose()
    
    # Run simulation
    print("Running simulation for 3 seconds...")
    sim.setTerminationTime(3.0)
    
    try:
        sim.simulate()
        print("\n✅ Simulation completed successfully!")
    except Exception as e:
        print(f"\n❌ Simulation error: {str(e)}")
        return
    
    # Save and analyze traces
    trace_logger.save_traces("ros2_traces.csv")
    print(f"\n📁 traces saved to: ros2_traces.csv")
    print(f"📊 Generated {len(trace_logger.traces)} trace events")
    
    # Run analysis
    analyze_results(model)

if __name__ == "__main__":
    main()