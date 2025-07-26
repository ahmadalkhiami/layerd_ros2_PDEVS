"""
RMW (ROS Middleware) layer implementation.
Interfaces between RCL and DDS layers.
"""

from pypdevs.DEVS import AtomicDEVS, CoupledDEVS
from pypdevs.infinity import INFINITY
import random
import time
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
import uuid

from core import (
    Message, MessageType, QoSProfile, RMWQoSProfile,
    PublisherHandle, SubscriptionHandle,
    trace_logger, context_manager, config,
    system_state
)
from dds import DDSParticipant, type_registry, TransportType, TransportMessage


@dataclass
class RMWPublisher:
    """RMW publisher implementation"""
    handle: int
    topic: str
    type_name: str
    qos: RMWQoSProfile
    dds_writer_guid: Optional[str] = None
    node_name: str = ""


@dataclass
class RMWSubscription:
    """RMW subscription implementation"""
    handle: int
    topic: str
    type_name: str
    qos: RMWQoSProfile
    dds_reader_guid: Optional[str] = None
    node_name: str = ""
    callback: Optional[callable] = None


class RMWLayer(CoupledDEVS):
    """
    RMW Layer - Interfaces between RCL and DDS.
    This is now a coupled DEVS containing RMW implementation and DDS participant.
    """
    
    def __init__(self, name: str = "RMWLayer"):
        CoupledDEVS.__init__(self, name)
        
        # Create DDS participant
        self.dds_participant = self.addSubModel(
            DDSParticipant("RMWParticipant", config.dds.domain_id)
        )
        
        # Create RMW implementation
        self.rmw_impl = self.addSubModel(RMWImplementation())
        
        # External ports for RCL interface
        self.rcl_pub_in = self.addInPort("rcl_pub_in")
        self.rcl_sub_out = self.addOutPort("rcl_sub_out")
        self.graph_event_out = self.addOutPort("graph_event_out")
        
        # External ports for DDS interface
        self.dds_data_in = self.addInPort("dds_data_in")
        self.dds_data_out = self.addOutPort("dds_data_out")
        
        # Connect RMW to DDS
        self.connectPorts(self.rmw_impl.dds_out, self.dds_participant.data_in)
        self.connectPorts(self.dds_participant.data_out, self.rmw_impl.dds_in)
        
        # Connect DDS participant to external ports
        self.connectPorts(self.dds_data_in, self.dds_participant.data_in)
        self.connectPorts(self.dds_participant.data_out, self.dds_data_out)
        
        # Connect external ports to RMW implementation
        self.connectPorts(self.rcl_pub_in, self.rmw_impl.rcl_pub_in)
        self.connectPorts(self.rmw_impl.rcl_sub_out, self.rcl_sub_out)
        self.connectPorts(self.rmw_impl.graph_event_out, self.graph_event_out)
        
    def __lt__(self, other):
        """Compare layers by name for DEVS simulator"""
        return self.name < other.name


class RMWImplementation(AtomicDEVS):
    """RMW implementation"""
    
    def __init__(self, name: str = "RMWImpl"):
        AtomicDEVS.__init__(self, name)
        
        # State
        self.state = {
            'phase': 'idle',
            'initialized': False,
            'publishers': {},  # handle -> RMWPublisher
            'subscriptions': {},  # handle -> RMWSubscription
            'pending_operations': [],
            'handle_counter': 1000
        }
        
        # Ports - RCL interface
        self.rcl_pub_in = self.addInPort("rcl_pub_in")
        self.rcl_sub_out = self.addOutPort("rcl_sub_out")
        
        # Ports - DDS interface
        self.dds_out = self.addOutPort("dds_out")
        self.dds_in = self.addInPort("dds_in")
        
        # Graph events
        self.graph_event_out = self.addOutPort("graph_event_out")
        
        # Register context
        self.context_key = context_manager.register_component(
            "rmw_impl",
            "rmw",
            "ros2_core"
        )
        
    def __lt__(self, other):
        """Compare implementations by name for DEVS simulator"""
        return self.name < other.name
        
    def timeAdvance(self):
        if self.state['phase'] == 'idle' and not self.state['initialized']:
            return 0.01
            
        elif self.state['pending_operations']:
            # Process operations with minimal delay
            return 0.0001
            
        return INFINITY
        
    def outputFnc(self):
        if self.state['phase'] == 'idle' and not self.state['initialized']:
            trace_logger.log_event(
                "rmw_init",
                {},
                self.context_key
            )
            
        elif self.state['pending_operations']:
            op = self.state['pending_operations'][0]
            
            # Process based on operation type
            if op['type'] == 'create_publisher':
                return self._create_publisher(op)
                
            elif op['type'] == 'create_subscription':
                return self._create_subscription(op)
                
            elif op['type'] == 'publish':
                return self._publish(op)
                
        return {}
        
    def intTransition(self):
        if self.state['phase'] == 'idle' and not self.state['initialized']:
            self.state['initialized'] = True
            
        elif self.state['pending_operations']:
            self.state['pending_operations'].pop(0)
            
        return self.state
        
    def extTransition(self, inputs):
        # Handle RCL commands
        if self.rcl_pub_in in inputs:
            rcl_cmd = inputs[self.rcl_pub_in]
            if isinstance(rcl_cmd, dict):
                self.state['pending_operations'].append(rcl_cmd)
                
        # Handle DDS responses
        if self.dds_in in inputs:
            dds_msg = inputs[self.dds_in]
            self._handle_dds_response(dds_msg)
            
        return self.state
        
    def _create_publisher(self, op: Dict) -> Dict:
        """Create publisher"""
        handle = self._next_handle()
        
        # Create publisher info
        pub = RMWPublisher(
            handle=handle,
            topic=op['topic'],
            type_name=op.get('type_name', 'std_msgs/String'),
            qos=op.get('qos', RMWQoSProfile()),
            node_name=op.get('node_name', '')
        )
        
        self.state['publishers'][handle] = pub
        
        # Create DDS writer
        writer = self.dds_participant.create_writer(
            pub.topic,
            pub.type_name,
            pub.qos
        )
        pub.dds_writer_guid = writer.guid
        
        trace_logger.log_event(
            "rmw_publisher_init",
            {
                "handle": handle,
                "topic": pub.topic,
                "node": pub.node_name
            },
            self.context_key
        )
        
        # Generate graph event
        self._generate_graph_event(
            "publisher_created",
            pub.topic,
            pub.node_name
        )
        
        return {}
        
    def _create_subscription(self, op: Dict) -> Dict:
        """Create subscription"""
        handle = self._next_handle()
        
        # Create subscription info
        sub = RMWSubscription(
            handle=handle,
            topic=op['topic'],
            type_name=op.get('type_name', 'std_msgs/String'),
            qos=op.get('qos', RMWQoSProfile()),
            node_name=op.get('node_name', ''),
            callback=op.get('callback')
        )
        
        self.state['subscriptions'][handle] = sub
        
        # Create DDS reader
        reader = self.dds_participant.create_reader(
            sub.topic,
            sub.type_name,
            sub.qos,
            lambda msg: self._on_dds_data_available(sub, msg)
        )
        sub.dds_reader_guid = reader.guid
        
        trace_logger.log_event(
            "rmw_subscription_init",
            {
                "handle": handle,
                "topic": sub.topic,
                "node": sub.node_name
            },
            self.context_key
        )
        
        # Generate graph event
        self._generate_graph_event(
            "subscription_created",
            sub.topic,
            sub.node_name
        )
        
        return {}
        
    def _publish(self, op: Dict) -> Dict:
        """Publish message"""
        msg = op['message']
        pub = self._find_publisher_for_topic(msg.topic)
        
        if pub:
            # Create transport message
            transport_msg = TransportMessage(
                source_guid=pub.dds_writer_guid,
                destination_guids=[],  # DDS will handle routing
                payload=type_registry.serialize(msg.__class__.__name__, msg),
                size_bytes=len(msg.serialized_data) if msg.serialized_data else 0,
                transport_type=TransportType.UDP_MULTICAST
            )
            
            trace_logger.log_event(
                "rmw_publish",
                {
                    "message_id": msg.id,
                    "topic": msg.topic,
                    "size": transport_msg.size_bytes
                },
                self.context_key
            )
            
            return {self.dds_out: transport_msg}
            
        return {}
        
    def _find_publisher_for_topic(self, topic: str) -> Optional[RMWPublisher]:
        """Find publisher for topic"""
        for pub in self.state['publishers'].values():
            if pub.topic == topic:
                return pub
        return None
        
    def _handle_dds_response(self, response: Dict):
        """Handle response from DDS layer"""
        if response.get('type') == 'data':
            # Find matching subscription
            topic = response.get('topic')
            for sub in self.state['subscriptions'].values():
                if sub.topic == topic:
                    # Check QoS compatibility
                    msg = response['message']
                    compatible, reason = self._check_qos_delivery(msg, sub)
                    
                    if compatible:
                        # Deliver to subscription
                        self._on_dds_data_available(sub, msg)
                    else:
                        trace_logger.log_event(
                            "rmw_qos_incompatible",
                            {
                                "topic": topic,
                                "reason": reason
                            },
                            self.context_key
                        )
                        
    def _handle_dds_data(self, dds_msg: Dict):
        """Handle data from DDS layer"""
        if isinstance(dds_msg, TransportMessage):
            # Find matching subscription
            for sub in self.state['subscriptions'].values():
                if sub.dds_reader_guid in dds_msg.destination_guids:
                    # Deserialize and deliver
                    msg = type_registry.deserialize(
                        sub.type_name,
                        dds_msg.payload
                    )
                    self._on_dds_data_available(sub, msg)
                    
    def _on_dds_data_available(self, subscription: RMWSubscription, msg: Message):
        """Handle received DDS data"""
        trace_logger.log_event(
            "rmw_take",
            {
                "message_id": msg.id,
                "topic": subscription.topic
            },
            self.context_key
        )
        
        # Forward to RCL
        return {self.rcl_sub_out: {
            'type': 'message_delivery',
            'subscription_handle': subscription.handle,
            'message': msg
        }}
        
    def _check_qos_delivery(self, msg: Message, sub: RMWSubscription) -> Tuple[bool, str]:
        """Check if message can be delivered based on QoS"""
        if not msg.qos_profile or not sub.qos:
            return True, ""
            
        # Check reliability
        if (sub.qos.reliability == QoSReliabilityPolicy.RELIABLE and
            msg.qos_profile.reliability != QoSReliabilityPolicy.RELIABLE):
            return False, "reliability mismatch"
            
        # Check durability
        if (sub.qos.durability == QoSDurabilityPolicy.TRANSIENT_LOCAL and
            msg.qos_profile.durability == QoSDurabilityPolicy.VOLATILE):
            return False, "durability mismatch"
            
        return True, ""
        
    def _generate_graph_event(self, event_type: str, topic: str, node_name: str):
        """Generate graph discovery event"""
        event = {
            'type': event_type,
            'topic': topic,
            'node': node_name,
            'timestamp': time.time()
        }
        return {self.graph_event_out: event}
        
    def _next_handle(self) -> int:
        """Generate next handle"""
        handle = self.state['handle_counter']
        self.state['handle_counter'] += 1
        return handle
        
    def get_publisher_count(self, topic: str) -> int:
        """Get number of publishers for topic"""
        return sum(1 for p in self.state['publishers'].values() if p.topic == topic)
        
    def get_subscription_count(self, topic: str) -> int:
        """Get number of subscriptions for topic"""
        return sum(1 for s in self.state['subscriptions'].values() if s.topic == topic)