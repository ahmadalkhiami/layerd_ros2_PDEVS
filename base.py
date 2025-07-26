"""
Base message types for ROS2 DEVS simulation.
"""

from dataclasses import dataclass, field
from typing import Any, Optional, List
import time

from core import Message, MessageType, MessageHeader


@dataclass
class StdMsgsString(Message):
    """std_msgs/String message type"""
    data: str = ""
    
    def __post_init__(self):
        super().__init__()
        self.type = MessageType.DATA
        

@dataclass
class StdMsgsInt32(Message):
    """std_msgs/Int32 message type"""
    data: int = 0
    
    def __post_init__(self):
        super().__init__()
        self.type = MessageType.DATA
        

@dataclass
class StdMsgsFloat64(Message):
    """std_msgs/Float64 message type"""
    data: float = 0.0
    
    def __post_init__(self):
        super().__init__()
        self.type = MessageType.DATA
        

@dataclass
class StdMsgsBool(Message):
    """std_msgs/Bool message type"""
    data: bool = False
    
    def __post_init__(self):
        super().__init__()
        self.type = MessageType.DATA
        

@dataclass
class StdMsgsHeader(MessageHeader):
    """std_msgs/Header message type"""
    stamp: float = field(default_factory=time.time)
    frame_id: str = ""
    

@dataclass
class GeometryMsgsTwist(Message):
    """geometry_msgs/Twist message type"""
    linear_x: float = 0.0
    linear_y: float = 0.0
    linear_z: float = 0.0
    angular_x: float = 0.0
    angular_y: float = 0.0
    angular_z: float = 0.0
    
    def __post_init__(self):
        super().__init__()
        self.type = MessageType.DATA
        

@dataclass
class GeometryMsgsPose(Message):
    """geometry_msgs/Pose message type"""
    position_x: float = 0.0
    position_y: float = 0.0
    position_z: float = 0.0
    orientation_x: float = 0.0
    orientation_y: float = 0.0
    orientation_z: float = 0.0
    orientation_w: float = 1.0
    
    def __post_init__(self):
        super().__init__()
        self.type = MessageType.DATA
        

@dataclass
class SensorMsgsLaserScan(Message):
    """sensor_msgs/LaserScan message type"""
    header: StdMsgsHeader = field(default_factory=StdMsgsHeader)
    angle_min: float = -1.57
    angle_max: float = 1.57
    angle_increment: float = 0.01
    time_increment: float = 0.0
    scan_time: float = 0.1
    range_min: float = 0.1
    range_max: float = 10.0
    ranges: List[float] = field(default_factory=list)
    intensities: List[float] = field(default_factory=list)
    
    def __post_init__(self):
        super().__init__()
        self.type = MessageType.DATA
        

@dataclass
class SensorMsgsJointState(Message):
    """sensor_msgs/JointState message type"""
    header: StdMsgsHeader = field(default_factory=StdMsgsHeader)
    name: List[str] = field(default_factory=list)
    position: List[float] = field(default_factory=list)
    velocity: List[float] = field(default_factory=list)
    effort: List[float] = field(default_factory=list)
    
    def __post_init__(self):
        super().__init__()
        self.type = MessageType.DATA
        

@dataclass
class NavMsgsOccupancyGrid(Message):
    """nav_msgs/OccupancyGrid message type"""
    header: StdMsgsHeader = field(default_factory=StdMsgsHeader)
    info_map_load_time: float = 0.0
    info_resolution: float = 0.05
    info_width: int = 0
    info_height: int = 0
    info_origin_position_x: float = 0.0
    info_origin_position_y: float = 0.0
    info_origin_position_z: float = 0.0
    info_origin_orientation_x: float = 0.0
    info_origin_orientation_y: float = 0.0
    info_origin_orientation_z: float = 0.0
    info_origin_orientation_w: float = 1.0
    data: List[int] = field(default_factory=list)
    
    def __post_init__(self):
        super().__init__()
        self.type = MessageType.DATA
