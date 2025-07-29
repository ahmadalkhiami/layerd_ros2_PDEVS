"""
RCLCPP layer implementation.
Provides C++ client library functionality.
"""

from pypdevs.DEVS import AtomicDEVS
from pypdevs.infinity import INFINITY
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
import random

from core import (
    Message, MessageType, QoSProfile,
    trace_logger, context_manager
)
from simulation.config import config


@dataclass
class PublisherInfo:
    """Information about a publisher"""
    node_name: str = ""
    topic: str = ""
    qos_profile: Optional[QoSProfile] = None
    handle: Optional[int] = None


@dataclass
class SubscriptionInfo:
    """Information about a subscription"""
    node_name: str = ""
    topic: str = ""
    qos_profile: Optional[QoSProfile] = None
    callback: Optional[Callable] = None
    handle: Optional[int] = None


@dataclass
class RCLCPPInterface:
    """Interface for RCLCPP layer operations"""
    node_name: str = ""
    interface_type: str = ""  # 'publisher', 'subscription', 'service', 'client'
    topic_or_service: str = ""
    qos_profile: Optional[QoSProfile] = None
    callback: Optional[Callable] = None
    handle: Optional[int] = None


class RCLCPPLayer(AtomicDEVS):
    """
    RCLCPP Layer - C++ client library interface.
    Manages high-level ROS2 operations.
    """
    
    def __init__(self, name: str = "RCLCPPLayer"):
        AtomicDEVS.__init__(self, name)
        
        # State
        self.state = {
            'phase': 'idle',
            'initialized': False,
            'nodes': {},  # node_name -> node_info
            'pending_operations': [],
            'executor_active': False,
            'pending_publishers': [],  # Publishers waiting for node handle
            'pending_subscriptions': []  # Subscriptions waiting for node handle
        }
        
        # Ports - Application interface
        self.app_pub_in = self.addInPort("app_pub_in")
        self.app_sub_out = self.addOutPort("app_sub_out")
        
        # Ports - RCL interface  
        self.rcl_cmd_out = self.addOutPort("rcl_cmd_out")
        self.rcl_data_in = self.addInPort("rcl_data_in")
        
        # Graph discovery port
        self.graph_event_in = self.addInPort("graph_event_in")
        
        # Register context
        self.context_key = context_manager.register_component(
            "rclcpp_layer",
            "rclcpp",
            "ros2_core"
        )
        
    def __lt__(self, other):
        """Compare layers by name for DEVS simulator"""
        return self.name < other.name
        
    def timeAdvance(self):
        if self.state['phase'] == 'idle' and not self.state['initialized']:
            return 0.01
            
        elif self.state['pending_operations']:
            # Process operations with minimal delay
            return 0.0001
            
        elif self.state['executor_active']:
            # Executor spin period
            return config.executor.spin_period_us / 1e6
            
        return INFINITY
        
    def outputFnc(self):
        if self.state['phase'] == 'idle' and not self.state['initialized']:
            trace_logger.log_event(
                "rclcpp_init",
                {},
                self.context_key
            )
            
        elif self.state['pending_operations']:
            op = self.state['pending_operations'][0]
            
            # Process based on operation type
            if op['type'] == 'create_node':
                return self._create_node(op)
                
            elif op['type'] == 'create_publisher':
                # Check if node exists and has handle
                node_name = op['node_name']
                if node_name not in self.state['nodes']:
                    # Create node first
                    self.state['pending_publishers'].append(op)
                    return self._create_node({'node_name': node_name})
                elif 'handle' not in self.state['nodes'][node_name]:
                    # Wait for node handle
                    self.state['pending_publishers'].append(op)
                    return {}
                else:
                    # Node exists and has handle
                    return self._create_publisher(op)
                
            elif op['type'] == 'create_subscription':
                # Check if node exists and has handle
                node_name = op['node_name']
                if node_name not in self.state['nodes']:
                    # Create node first
                    self.state['pending_subscriptions'].append(op)
                    return self._create_node({'node_name': node_name})
                elif 'handle' not in self.state['nodes'][node_name]:
                    # Wait for node handle
                    self.state['pending_subscriptions'].append(op)
                    return {}
                else:
                    # Node exists and has handle
                    return self._create_subscription(op)
                
            elif op['type'] == 'publish':
                return self._publish(op)
                
        elif self.state['executor_active']:
            # Executor work
            trace_logger.log_event(
                "rclcpp_executor_spin_some",
                {"nodes": len(self.state['nodes'])},
                self.context_key
            )
            
        return {}
        
    def intTransition(self):
        if self.state['phase'] == 'idle' and not self.state['initialized']:
            self.state['initialized'] = True
            self.state['executor_active'] = True
            
        elif self.state['pending_operations']:
            self.state['pending_operations'].pop(0)
            
        return self.state
        
    def extTransition(self, inputs):
        # Handle application publisher input
        if self.app_pub_in in inputs:
            app_msg = inputs[self.app_pub_in]
            if isinstance(app_msg, dict):
                self.state['pending_operations'].append(app_msg)
                
        # Handle RCL data input
        if self.rcl_data_in in inputs:
            rcl_data = inputs[self.rcl_data_in]
            self._handle_rcl_data(rcl_data)
            
        # Handle graph events
        if self.graph_event_in in inputs:
            graph_event = inputs[self.graph_event_in]
            self._handle_graph_event(graph_event)
            
        return self.state
        
    def _create_node(self, op: Dict) -> Dict:
        """Create a node"""
        node_name = op['node_name']
        
        if node_name not in self.state['nodes']:
            self.state['nodes'][node_name] = {
                'publishers': {},
                'subscriptions': {},
                'services': {},
                'timers': {}
            }
            
        trace_logger.log_event(
            "rclcpp_node_init",
            {"node_name": node_name},
            self.context_key
        )
        
        # Forward to RCL
        return {self.rcl_cmd_out: {
            'type': 'create_node',
            'node_name': node_name
        }}
        
    def _create_publisher(self, op: Dict) -> Dict:
        """Create a publisher"""
        node_name = op['node_name']
        topic = op['topic']
        node_info = self.state['nodes'][node_name]
        
        # Register publisher
        node_info['publishers'][topic] = {
            'qos': op.get('qos'),
            'handle': None
        }
        
        trace_logger.log_event(
            "rclcpp_publisher_init",
            {
                "node_name": node_name,
                "topic": topic
            },
            self.context_key
        )
        
        # Forward to RCL
        return {self.rcl_cmd_out: {
            'type': 'create_publisher',
            'node_handle': node_info['handle'],
            'topic': topic,
            'qos': op.get('qos')
        }}
        
    def _create_subscription(self, op: Dict) -> Dict:
        """Create a subscription"""
        node_name = op['node_name']
        topic = op['topic']
        node_info = self.state['nodes'][node_name]
        
        # Register subscription
        node_info['subscriptions'][topic] = {
            'qos': op.get('qos'),
            'callback': op.get('callback'),
            'handle': None
        }
        
        trace_logger.log_event(
            "rclcpp_subscription_init",
            {
                "node_name": node_name,
                "topic": topic
            },
            self.context_key
        )
        
        # Forward to RCL
        return {self.rcl_cmd_out: {
            'type': 'create_subscription',
            'node_handle': node_info['handle'],
            'topic': topic,
            'qos': op.get('qos'),
            'callback': op.get('callback')
        }}
        
    def _publish(self, op: Dict) -> Dict:
        """Publish a message"""
        message = op['message']
        publisher_handle = op['publisher_handle']
        
        trace_logger.log_event(
            "rclcpp_publish",
            {
                "message_id": message.id,
                "topic": message.topic
            },
            self.context_key
        )
        
        # Forward to RCL
        return {self.rcl_cmd_out: {
            'type': 'publish',
            'publisher_handle': publisher_handle,
            'message': message
        }}
        
    def _handle_rcl_data(self, data: Dict):
        """Handle data from RCL layer"""
        if data.get('type') == 'node_created':
            # Store node handle
            node_name = data['node_name']
            node_handle = data['node_handle']
            if node_name in self.state['nodes']:
                self.state['nodes'][node_name]['handle'] = node_handle
                
                # Process pending publishers for this node
                for pub in self.state['pending_publishers'][:]:
                    if pub['node_name'] == node_name:
                        self.state['pending_operations'].append(pub)
                        self.state['pending_publishers'].remove(pub)
                        
                # Process pending subscriptions for this node
                for sub in self.state['pending_subscriptions'][:]:
                    if sub['node_name'] == node_name:
                        self.state['pending_operations'].append(sub)
                        self.state['pending_subscriptions'].remove(sub)
                        
        elif data.get('type') == 'publisher_created':
            # Store publisher handle and forward to application
            publisher_handle = data['publisher_handle']
            topic = data['topic']
            
            # Find the node that owns this publisher
            for node_name, node_info in self.state['nodes'].items():
                if topic in node_info['publishers']:
                    node_info['publishers'][topic]['handle'] = publisher_handle
                    # Forward to application
                    self.state['pending_operations'].append({
                        'type': 'publisher_created',
                        'publisher_handle': publisher_handle,
                        'topic': topic
                    })
                    break
                        
        elif data.get('type') == 'message_delivery':
            # Deliver message to application
            message = data['message']
            
            trace_logger.log_event(
                "rclcpp_take",
                {
                    "message_id": message.id,
                    "topic": message.topic
                },
                self.context_key
            )
            
            # Send to application subscriber
            self.state['pending_operations'].append({
                'type': 'deliver_to_app',
                'message': message
            })
            
    def _handle_graph_event(self, event: Dict):
        """Handle graph discovery event"""
        trace_logger.log_event(
            "rclcpp_graph_event",
            {
                "event_type": event.get('event_type', 'unknown'),
                "entity": event.get('entity_name', 'unknown')
            },
            self.context_key
        )