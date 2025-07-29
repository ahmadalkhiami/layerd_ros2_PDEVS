"""
Main ROS2 DEVS simulation system composition.
"""

from pypdevs.DEVS import CoupledDEVS
from pypdevs.simulator import Simulator

from .config import config
from core import context_manager, trace_logger
from qos.policies import QoSProfile, QoSReliabilityPolicy, QoSDurabilityPolicy, QoSHistoryPolicy
from rmw import RMWLayer
from rcl import RCLLayer
from rclcpp import RCLCPPLayer
from application import (
    Publisher, Subscriber,
    LifecycleNode, LifecycleManager,
    ActionServer, ActionClient
)
from dds.transport import TransportMultiplexer
from dds.participant import DDSParticipant

class ROS2System(CoupledDEVS):
    """
    Complete ROS2 system with proper layered architecture.
    """
    
    def __init__(self, name: str = "ROS2System"):
        CoupledDEVS.__init__(self, name)
        
        # Create layers (bottom-up)
        self._create_dds_layer()
        self._create_rmw_layer()
        self._create_rcl_layer()
        self._create_rclcpp_layer()
        self._create_application_layer()
        
        # Connect layers
        self._connect_layers()
        
        # Configure system based on config
        self._configure_system()
        
    def _create_dds_layer(self):
        """Create DDS layer components"""
        # DDS participant for domain
        self.dds_participant = self.addSubModel(
            DDSParticipant("SystemDDSParticipant", config.dds.domain_id)
        )
        
        # Transport layer
        self.transport = self.addSubModel(TransportMultiplexer())
        
        # Connect DDS to transport
        self.connectPorts(self.dds_participant.data_out, self.transport.data_in)
        self.connectPorts(self.transport.data_out, self.dds_participant.data_in)
        
    def _create_rmw_layer(self):
        """Create RMW layer"""
        self.rmw_layer = self.addSubModel(RMWLayer())
        
    def _create_rcl_layer(self):
        """Create RCL layer"""
        self.rcl_layer = self.addSubModel(RCLLayer())
        
    def _create_rclcpp_layer(self):
        """Create RCLCPP layer"""
        self.rclcpp_layer = self.addSubModel(RCLCPPLayer())
        
    def _create_application_layer(self):
        """Create application components based on configuration"""
        # Create map server if enabled
        if config.enable_map_server:
            self._create_map_server()
            
        # Create robot state publisher if enabled
        if config.enable_robot_state_publisher:
            self._create_robot_state_publisher()
            
        # Create joint state publisher if enabled
        if config.enable_joint_state_publisher:
            self._create_joint_state_publisher()
            
        # Create laser scanner if enabled
        if config.enable_laser_scanner:
            self._create_laser_scanner()
            
    def _create_map_server(self):
        """Create map server node"""
        # QoS profile for map server
        map_qos = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1
        )
        
        # Map server publisher
        self.map_server = self.addSubModel(
            Publisher(
                name="MapServer",
                node_name="dummy_map_serve",
                topic="/map",
                qos_profile=map_qos,
                publish_rate_hz=1.0
            )
        )
        
    def _create_robot_state_publisher(self):
        """Create robot state publisher node"""
        # QoS profile for robot state
        state_qos = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1
        )
        
        # Robot state publisher
        self.robot_state_pub = self.addSubModel(
            Publisher(
                name="RobotStatePublisher",
                node_name="robot_state_publisher",
                topic="/robot_description",
                qos_profile=state_qos,
                publish_rate_hz=1.0
            )
        )
        
        # Joint state subscriber
        self.robot_state_sub = self.addSubModel(
            Subscriber(
                name="RobotStateSubscriber",
                node_name="robot_state_publisher",
                topic="/joint_states",
                qos_profile=state_qos
            )
        )
        
    def _create_joint_state_publisher(self):
        """Create joint state publisher node"""
        # QoS profile for joint states
        joint_qos = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.VOLATILE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1
        )
        
        # Joint state publisher
        self.joint_state_pub = self.addSubModel(
            Publisher(
                name="JointStatePublisher",
                node_name="dummy_joint_sta",
                topic="/joint_states",
                qos_profile=joint_qos,
                publish_rate_hz=10.0
            )
        )
        
    def _create_laser_scanner(self):
        """Create laser scanner node"""
        # QoS profile for laser scan
        scan_qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=5
        )
        
        # Laser scanner publisher
        self.laser_pub = self.addSubModel(
            Publisher(
                name="LaserScanner",
                node_name="dummy_laser",
                topic="/scan",
                qos_profile=scan_qos,
                publish_rate_hz=20.0
            )
        )
        
    def _connect_layers(self):
        """Connect all layers together"""
        # Connect transport to RMW's DDS interface
        self.connectPorts(self.rmw_layer.dds_data_out, self.transport.data_in)
        self.connectPorts(self.transport.data_out, self.rmw_layer.dds_data_in)
        
        # Connect RMW to RCL
        self.connectPorts(self.rmw_layer.rcl_sub_out, self.rcl_layer.rmw_sub_in)
        self.connectPorts(self.rcl_layer.rmw_pub_out, self.rmw_layer.rcl_pub_in)
        
        # Connect RCL to RCLCPP
        self.connectPorts(self.rcl_layer.rclcpp_data_out, self.rclcpp_layer.rcl_data_in)
        self.connectPorts(self.rclcpp_layer.rcl_cmd_out, self.rcl_layer.rclcpp_cmd_in)
        
        # Connect application components to RCLCPP layer
        self._connect_application_components()
        
    def _connect_application_components(self):
        """Connect application components to RCLCPP layer"""
        # Connect map server if it exists
        if hasattr(self, 'map_server'):
            self.connectPorts(self.map_server.rclcpp_out, self.rclcpp_layer.app_pub_in)
            
        # Connect robot state publisher if it exists
        if hasattr(self, 'robot_state_pub'):
            self.connectPorts(self.robot_state_pub.rclcpp_out, self.rclcpp_layer.app_pub_in)
        if hasattr(self, 'robot_state_sub'):
            self.connectPorts(self.rclcpp_layer.app_sub_out, self.robot_state_sub.rclcpp_in)
            
        # Connect joint state publisher if it exists
        if hasattr(self, 'joint_state_pub'):
            self.connectPorts(self.joint_state_pub.rclcpp_out, self.rclcpp_layer.app_pub_in)
            
        # Connect laser scanner if it exists
        if hasattr(self, 'laser_pub'):
            self.connectPorts(self.laser_pub.rclcpp_out, self.rclcpp_layer.app_pub_in)
            
        # Connect graph events from RMW to RCLCPP
        self.connectPorts(self.rmw_layer.graph_event_out, self.rclcpp_layer.graph_event_in)
        
    def _configure_system(self):
        """Configure system based on configuration"""
        # Enable parameter services if configured
        if config.enable_parameter_services:
            self._setup_parameter_services()
            
        # Enable diagnostics if configured
        if config.enable_diagnostics:
            self._setup_diagnostics()
            
    def _setup_parameter_services(self):
        """Setup parameter services for all nodes"""
        pass  # Implementation details omitted for brevity
        
    def _setup_diagnostics(self):
        """Setup diagnostics for all nodes"""
        pass  # Implementation details omitted for brevity


class MinimalSystem(CoupledDEVS):
    """
    Minimal ROS2 system for testing.
    """
    
    def __init__(self, name: str = "MinimalROS2"):
        CoupledDEVS.__init__(self, name)
        
        # Create transport layer
        self.transport = self.addSubModel(TransportMultiplexer())
        
        # Create minimal layer stack
        self.rmw = self.addSubModel(RMWLayer("MinimalRMWLayer"))
        self.rcl = self.addSubModel(RCLLayer())
        self.rclcpp = self.addSubModel(RCLCPPLayer())
        
        # Create single publisher-subscriber pair
        qos = QoSProfile()
        
        self.publisher = self.addSubModel(
            Publisher("TestPub", "test_node", "/test", qos, 10.0)
        )
        
        self.subscriber = self.addSubModel(
            Subscriber("TestSub", "test_node", "/test", qos)
        )
        
        # Connect transport to RMW's DDS interface
        self.connectPorts(self.rmw.dds_data_out, self.transport.data_in)
        self.connectPorts(self.transport.data_out, self.rmw.dds_data_in)
        
        # Connect RMW to RCL
        self.connectPorts(self.rmw.rcl_sub_out, self.rcl.rmw_sub_in)
        self.connectPorts(self.rcl.rmw_pub_out, self.rmw.rcl_pub_in)
        
        # Connect RCL to RCLCPP
        self.connectPorts(self.rcl.rclcpp_data_out, self.rclcpp.rcl_data_in)
        self.connectPorts(self.rclcpp.rcl_cmd_out, self.rcl.rclcpp_cmd_in)
        
        # Connect application
        self.connectPorts(self.publisher.rclcpp_out, self.rclcpp.app_pub_in)
        self.connectPorts(self.rclcpp.app_sub_out, self.subscriber.rclcpp_in)
        
        # Connect graph events
        self.connectPorts(self.rmw.graph_event_out, self.rclcpp.graph_event_in)
        
    def __lt__(self, other):
        """Compare systems by name for DEVS simulator"""
        return self.name < other.name


def create_system(system_type: str = "full") -> CoupledDEVS:
    """
    Factory function to create different system configurations.
    
    Args:
        system_type: Type of system to create ("full", "minimal", "custom")
        
    Returns:
        Configured ROS2 DEVS system
    """
    if system_type == "minimal":
        return MinimalSystem()
    elif system_type == "full":
        return ROS2System()
    else:
        raise ValueError(f"Unknown system type: {system_type}")