"""
Timer-related messages for ROS2 DEVS simulation.
"""

from dataclasses import dataclass
import time

from core import Message, MessageType


@dataclass
class TimerEvent(Message):
    """Timer event message"""
    timer_id: str = ""
    period_ms: float = 0.0
    expected_trigger_time: float = 0.0
    actual_trigger_time: float = 0.0
    
    def __post_init__(self):
        super().__init__()
        self.type = MessageType.DATA
        self.actual_trigger_time = time.time()
        
    def calculate_jitter_ms(self) -> float:
        """Calculate timer jitter in milliseconds"""
        if self.expected_trigger_time > 0:
            return abs(self.actual_trigger_time - self.expected_trigger_time) * 1000
        return 0.0
        

@dataclass
class ClockMessage(Message):
    """ROS2 Clock message for /clock topic"""
    clock_sec: int = 0
    clock_nanosec: int = 0
    
    def __post_init__(self):
        super().__init__()
        self.type = MessageType.DATA
        self.topic = "/clock"
        
    @classmethod
    def from_timestamp(cls, timestamp: float) -> 'ClockMessage':
        """Create clock message from timestamp"""
        sec = int(timestamp)
        nanosec = int((timestamp - sec) * 1e9)
        return cls(clock_sec=sec, clock_nanosec=nanosec)
        
    def to_timestamp(self) -> float:
        """Convert to timestamp"""
        return self.clock_sec + self.clock_nanosec / 1e9
