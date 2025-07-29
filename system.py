"""
Main ROS2 DEVS simulation system composition.
"""

from pypdevs.DEVS import CoupledDEVS
from pypdevs.simulator import Simulator

from core import (
    config, context_manager, trace_logger,
    QoSProfile, QoSReliabilityPolicy, QoSDurabilityPolicy, QoSHistoryPolicy
)
from dds import DDSParticipant, TransportMultiplexer
from rmw import RMWLayer
from rcl import RCLLayer
from rclcpp import RCLCPPLayer
from application import (
    Publisher, Subscriber, 
    LifecycleNode, LifecycleManager,
    ActionServer, ActionClient
)


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
        # Example: Create a simple talker-listener system
        self._create_talker_listener()
        
        # Create lifecycle demo if enabled
        if config.enable_lifecycle_nodes:
            self._create_lifecycle_demo()
            
        # Create action demo if enabled
        if config.enable_actions:
            self._create_action_demo()
            
    def _create_talker_listener(self):
        """Create simple talker-listener demo"""
        # QoS profiles
        reliable_qos = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.VOLATILE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10
        )
        
        # Talker (publisher)
        self.talker = self.addSubModel(
            Publisher(
                name="Talker",
                node_name="talker_node",
                topic="/chatter",
                qos_profile=reliable_qos,
                publish_rate_hz=1.0
            )
        )
        
        # Listener (subscriber)
        self.listener = self.addSubModel(
            Subscriber(
                name="Listener",
                node_name="listener_node",
                topic="/chatter",
                qos_profile=reliable_qos
            )
        )
        
    def _create_lifecycle_demo(self):
        """Create lifecycle node demonstration"""
        # Create lifecycle nodes
        self.camera_node = self.addSubModel(
            LifecycleNode(
                name="CameraNode",
                node_name="camera_driver"
            )
        )
        
        self.perception_node = self.addSubModel(
            LifecycleNode(
                name="PerceptionNode",
                node_name="perception_pipeline"
            )
        )
        
        # Create lifecycle manager
        self.lifecycle_manager = self.addSubModel(
            LifecycleManager(
                name="SystemLifecycleManager",
                managed_nodes=["camera_driver", "perception_pipeline"]
            )
        )
        
        # Connect lifecycle components
        self.connectPorts(
            self.lifecycle_manager.transition_out,
            self.camera_node.transition_in
        )
        self.connectPorts(
            self.lifecycle_manager.transition_out,
            self.perception_node.transition_in
        )
        
        self.connectPorts(
            self.camera_node.transition_out,
            self.lifecycle_manager.result_in
        )
        self.connectPorts(
            self.perception_node.transition_out,
            self.lifecycle_manager.result_in
        )
        
    def _create_action_demo(self):
        """Create action server/client demonstration"""
        # Navigation action server
        self.nav_server = self.addSubModel(
            ActionServer(
                name="NavigationServer",
                node_name="navigation_controller",
                action_name="navigate_to_pose"
            )
        )
        
        # Navigation action client
        self.nav_client = self.addSubModel(
            ActionClient(
                name="NavigationClient",
                node_name="mission_planner",
                action_name="navigate_to_pose"
            )
        )
        
        # Connect action components
        self.connectPorts(self.nav_client.goal_out, self.nav_server.goal_in)
        self.connectPorts(self.nav_client.cancel_out, self.nav_server.cancel_in)
        self.connectPorts(self.nav_server.goal_response_out, self.nav_client.goal_response_in)
        self.connectPorts(self.nav_server.feedback_out, self.nav_client.feedback_in)
        self.connectPorts(self.nav_server.result_out, self.nav_client.result_in)
        
    def _connect_layers(self):
        """Connect the layers properly"""
        # RMW ↔ RCL
        self.connectPorts(self.rmw_layer.rcl_sub_out, self.rcl_layer.rmw_sub_in)
        self.connectPorts(self.rcl_layer.rmw_pub_out, self.rmw_layer.rcl_pub_in)
        
        # RCL ↔ RCLCPP
        self.connectPorts(self.rcl_layer.rclcpp_data_out, self.rclcpp_layer.rcl_data_in)
        self.connectPorts(self.rclcpp_layer.rcl_cmd_out, self.rcl_layer.rclcpp_cmd_in)
        
        # RCLCPP ↔ Application
        # Connect publishers
        self.connectPorts(self.talker.rclcpp_out, self.rclcpp_layer.app_pub_in)
        
        # Connect subscribers
        self.connectPorts(self.rclcpp_layer.app_sub_out, self.listener.rclcpp_in)
        
        # Graph events
        self.connectPorts(self.rmw_layer.graph_event_out, self.rclcpp_layer.graph_event_in)
        
    def _configure_system(self):
        """Configure system based on global configuration"""
        # Set up trace filtering if needed
        if config.logging.trace_filter_patterns:
            trace_logger.set_filter_patterns(config.logging.trace_filter_patterns)
            
        if config.logging.exclude_patterns:
            trace_logger.set_exclude_patterns(config.logging.exclude_patterns)
            
        # Set console output based on config
        trace_logger.console_output = config.logging.trace_to_console
        
        # Set file output based on config
        if config.logging.trace_to_file:
            trace_logger.enable_file_output(config.logging.trace_file_path)


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