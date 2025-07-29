"""
RCL (ROS Client Library) layer implementation.
Provides C API-like interface for ROS2 functionality.
"""

from pypdevs.DEVS import AtomicDEVS
from pypdevs.infinity import INFINITY
import time
from typing import Dict, List, Optional, Any
import uuid

from simulation.config import config
from core.trace import trace_logger
from core.context import context_manager
from core.dataTypes import NodeHandle, PublisherHandle, SubscriptionHandle, TimerHandle, ServiceHandle, QoSProfile
from rcl.parameter import ParameterServer, Parameter, ParameterType
from rcl.timer import TimerManager

class RCLContext:
    """RCL context - represents a ROS2 context"""
    def __init__(self):
        self.handle = int(uuid.uuid4().int >> 96)  # Generate handle
        self.is_initialized = False
        self.nodes: Dict[int, NodeHandle] = {}
        self.domain_id = config.dds.domain_id
        

class RCLLayer(AtomicDEVS):
    """
    RCL Layer - Provides core ROS2 functionality.
    Fixed to properly handle all RCL operations.
    """
    
    def __init__(self, name: str = "RCLLayer"):
        AtomicDEVS.__init__(self, name)
        
        # State
        self.state = {
            'phase': 'uninitialized',
            'context': None,
            'nodes': {},           # handle -> NodeHandle
            'publishers': {},      # handle -> PublisherHandle
            'subscriptions': {},   # handle -> SubscriptionHandle
            'timers': {},         # handle -> TimerHandle
            'services': {},       # handle -> ServiceHandle
            'pending_operations': [],
            'handle_counter': 1000
        }
        
        # Components
        self.parameter_server = ParameterServer()
        self.timer_manager = TimerManager()
        
        # Ports
        self.rclcpp_cmd_in = self.addInPort("from_rclcpp")
        self.rclcpp_data_out = self.addOutPort("to_rclcpp")
        self.rmw_pub_out = self.addOutPort("to_rmw")
        self.rmw_sub_in = self.addInPort("from_rmw")
        
        # Parameter ports
        self.param_request_in = self.addInPort("param_requests")
        self.param_response_out = self.addOutPort("param_responses")
        
        # Register context
        self.context_key = context_manager.register_component(
            "rcl_layer",
            "rcl",
            "ros2_core"
        )
        
    def _next_handle(self) -> int:
        """Generate next unique handle"""
        handle = self.state['handle_counter']
        self.state['handle_counter'] += 1
        return handle
        
    def __lt__(self, other):
        """Compare layers by name for DEVS simulator"""
        return self.name < other.name
        
    def timeAdvance(self):
        if self.state['phase'] == 'uninitialized':
            return 0.01
            
        elif self.state['pending_operations']:
            # Process operations quickly
            return 0.0001
            
        # Check for timer expirations
        next_timer = self.timer_manager.get_next_expiration()
        if next_timer is not None:
            return max(0, next_timer - time.time())
            
        return INFINITY
        
    def outputFnc(self):
        if self.state['phase'] == 'uninitialized' and not self.state['context']:
            # Initialize RCL context
            self.state['context'] = RCLContext()
            
            trace_logger.log_event(
                "rcl_init",
                {
                    "context_handle": f"0x{self.state['context'].handle:X}",
                    "version": "4.1.1"
                },
                self.context_key
            )
            
        elif self.state['pending_operations']:
            op = self.state['pending_operations'][0]
            return self._process_operation(op)
            
        # Check for timer callbacks
        expired_timers = self.timer_manager.get_expired_timers()
        if expired_timers:
            timer_handle = expired_timers[0]
            if timer_handle in self.state['timers']:
                timer = self.state['timers'][timer_handle]
                
                trace_logger.log_event(
                    "rcl_timer_call",
                    {
                        "timer_handle": f"0x{timer_handle:X}",
                        "period_ns": timer.period_ns
                    },
                    self.context_key
                )
                
                # Send timer callback to rclcpp
                return {self.rclcpp_data_out: {
                    'type': 'timer_callback',
                    'timer_handle': timer_handle,
                    'node_handle': timer.node_handle.handle_id
                }}
                
        return {}
        
    def intTransition(self):
        if self.state['phase'] == 'uninitialized' and self.state['context']:
            self.state['context'].is_initialized = True
            self.state['phase'] = 'active'
            
        elif self.state['pending_operations']:
            self.state['pending_operations'].pop(0)
            
        # Update timer manager
        self.timer_manager.update()
        
        return self.state
        
    def extTransition(self, inputs):
        # Handle RCLCPP commands
        if self.rclcpp_cmd_in in inputs:
            cmd = inputs[self.rclcpp_cmd_in]
            self.state['pending_operations'].append(cmd)
            
        # Handle RMW data
        if self.rmw_sub_in in inputs:
            msg = inputs[self.rmw_sub_in]
            # Forward to RCLCPP
            self.state['pending_operations'].append({
                'type': 'deliver_message',
                'message': msg
            })
            
        # Handle parameter requests
        if self.param_request_in in inputs:
            param_req = inputs[self.param_request_in]
            self._handle_parameter_request(param_req)
            
        return self.state
        
    def _process_operation(self, op: Dict) -> Dict:
        """Process an RCL operation"""
        op_type = op.get('type')
        
        if op_type == 'create_node':
            return self._create_node(op)
            
        elif op_type == 'create_publisher':
            return self._create_publisher(op)
            
        elif op_type == 'create_subscription':
            return self._create_subscription(op)
            
        elif op_type == 'create_timer':
            return self._create_timer(op)
            
        elif op_type == 'create_service':
            return self._create_service(op)
            
        elif op_type == 'publish':
            return self._publish_message(op)
            
        elif op_type == 'deliver_message':
            return self._deliver_message(op)
            
        return {}
        
    def _create_node(self, op: Dict) -> Dict:
        """Create RCL node"""
        node_name = op['node_name']
        namespace = op.get('namespace', '/')
        
        handle = self._next_handle()
        node = NodeHandle(
            name=node_name,
            namespace=namespace,
            handle_id=handle,
            context_handle=self.state['context'].handle
        )
        
        self.state['nodes'][handle] = node
        self.state['context'].nodes[handle] = node
        
        trace_logger.log_event(
            "rcl_node_init",
            {
                "node_handle": f"0x{handle:X}",
                "node_name": node_name,
                "namespace": namespace
            },
            self.context_key
        )
        
        return {self.rclcpp_data_out: {
            'type': 'node_created',
            'node_handle': handle,
            'node_name': node_name
        }}
        
    def _create_publisher(self, op: Dict) -> Dict:
        """Create RCL publisher"""
        node_handle = op['node_handle']
        topic = op['topic']
        qos = op.get('qos', QoSProfile())
        
        if node_handle not in self.state['nodes']:
            return {}
            
        handle = self._next_handle()
        publisher = PublisherHandle(
            node_handle=self.state['nodes'][node_handle],
            topic=topic,
            qos_profile=qos.to_rmw_qos() if hasattr(qos, 'to_rmw_qos') else qos,
            handle_id=handle
        )
        
        self.state['publishers'][handle] = publisher
        
        trace_logger.log_event(
            "rcl_publisher_init",
            {
                "publisher_handle": f"0x{handle:X}",
                "node_handle": f"0x{node_handle:X}",
                "topic_name": topic,
                "qos": str(qos)
            },
            self.context_key
        )
        
        return {self.rclcpp_data_out: {
            'type': 'publisher_created',
            'publisher_handle': handle,
            'topic': topic
        }}
        
    def _create_subscription(self, op: Dict) -> Dict:
        """Create RCL subscription"""
        node_handle = op['node_handle']
        topic = op['topic']
        qos = op.get('qos', QoSProfile())
        callback = op.get('callback')
        
        if node_handle not in self.state['nodes']:
            return {}
            
        handle = self._next_handle()
        subscription = SubscriptionHandle(
            node_handle=self.state['nodes'][node_handle],
            topic=topic,
            qos_profile=qos.to_rmw_qos() if hasattr(qos, 'to_rmw_qos') else qos,
            handle_id=handle,
            callback=callback
        )
        
        self.state['subscriptions'][handle] = subscription
        
        trace_logger.log_event(
            "rcl_subscription_init",
            {
                "subscription_handle": f"0x{handle:X}",
                "node_handle": f"0x{node_handle:X}",
                "topic_name": topic,
                "qos": str(qos)
            },
            self.context_key
        )
        
        return {self.rclcpp_data_out: {
            'type': 'subscription_created',
            'subscription_handle': handle,
            'topic': topic
        }}
        
    def _create_timer(self, op: Dict) -> Dict:
        """Create RCL timer"""
        node_handle = op['node_handle']
        period_ns = op['period_ns']
        callback = op.get('callback')
        
        if node_handle not in self.state['nodes']:
            return {}
            
        handle = self._next_handle()
        timer = TimerHandle(
            node_handle=self.state['nodes'][node_handle],
            period_ns=period_ns,
            callback=callback,
            handle_id=handle
        )
        
        self.state['timers'][handle] = timer
        self.timer_manager.add_timer(handle, period_ns / 1e9)  # Convert to seconds
        
        trace_logger.log_event(
            "rcl_timer_init",
            {
                "timer_handle": f"0x{handle:X}",
                "period_ns": period_ns
            },
            self.context_key
        )
        
        return {self.rclcpp_data_out: {
            'type': 'timer_created',
            'timer_handle': handle
        }}
        
    def _publish_message(self, op: Dict) -> Dict:
        """Publish message through RCL"""
        publisher_handle = op['publisher_handle']
        message = op['message']
        
        if publisher_handle not in self.state['publishers']:
            return {}
            
        publisher = self.state['publishers'][publisher_handle]
        
        # Set message metadata
        message.topic = publisher.topic
        
        trace_logger.log_event(
            "rcl_publish",
            {
                "message_id": message.id,
                "publisher_handle": f"0x{publisher_handle:X}",
                "node_handle": f"0x{publisher.node_handle.handle_id:X}"
            },
            self.context_key
        )
        
        # Forward to RMW
        return {self.rmw_pub_out: message}
        
    def _deliver_message(self, op: Dict) -> Dict:
        """Deliver message to subscription"""
        message = op['message']
        
        # Find matching subscriptions
        for sub_handle, subscription in self.state['subscriptions'].items():
            if subscription.topic == message.topic:
                trace_logger.log