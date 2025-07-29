"""
System creation utilities.
"""

from simulation.system import ROS2System


def create_system(system_type: str):
    """Create ROS2 system based on type"""
    if system_type == "minimal":
        # Create minimal system with single publisher-subscriber
        return ROS2System("MinimalROS2")
        
    elif system_type == "dummy_robot":
        # Create system matching real dummy robot traces
        # The ROS2System constructor will handle all the component creation
        # based on the global config settings
        system = ROS2System("DummyRobotROS2")
        return system
        
    else:
        raise ValueError(f"Unknown system type: {system_type}")

__all__ = ['create_system']