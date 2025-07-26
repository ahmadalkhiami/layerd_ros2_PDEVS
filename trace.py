"""
Trace logging system for ROS2 DEVS simulation.
"""

import time
import json
import os
import platform
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime

from .context import context_manager


@dataclass
class TraceEvent:
    """Trace event with LTTng-like format"""
    timestamp: float
    event_name: str
    context_key: str
    data: Dict[str, Any]
    
    def to_lttng_format(self, delta: float = 0.0) -> str:
        """Format event in LTTng-like format"""
        # Format timestamp
        dt = datetime.fromtimestamp(self.timestamp)
        timestamp_str = dt.strftime("%H:%M:%S.%f")
        
        # Format delta
        delta_str = f"+{delta*1000:.3f}ms" if delta > 0 else "+0.000ms"
        
        # Get hostname
        hostname = platform.node()
        
        # Format data
        data_str = " ".join(f"{k}={v}" for k, v in self.data.items())
        
        return (f"[{timestamp_str}] ({delta_str}) {hostname} "
                f"{self.event_name}: {data_str}")
    
    def to_json(self) -> Dict[str, Any]:
        """Convert event to JSON format"""
        return {
            'timestamp': self.timestamp,
            'event': self.event_name,
            'context': self.context_key,
            'data': self.data
        }


class TraceLogger:
    """Trace logger for ROS2 components"""
    
    def __init__(self):
        self.events: List[TraceEvent] = []
        self.start_time = time.time()
        self.enabled = True
        self.console_output = True
        self.file_output = False
        self.file_path = "ros2_trace.log"
        self.filter_patterns = []
        self.exclude_patterns = []
        
    def enable(self):
        """Enable trace logging"""
        self.enabled = True
        
    def disable(self):
        """Disable trace logging"""
        self.enabled = False
        
    def set_console_output(self, enabled: bool):
        """Enable/disable console output"""
        self.console_output = enabled
        
    def enable_file_output(self, file_path: str):
        """Enable trace output to file"""
        self.file_output = True
        self.file_path = file_path
        # Write header
        with open(self.file_path, 'w') as f:
            f.write(f"# ROS2 DEVS Simulation Trace\n")
            f.write(f"# Start time: {time.ctime()}\n")
            f.write("#\n")
            
    def set_filter_patterns(self, patterns: List[str]):
        """Set event name patterns to include"""
        self.filter_patterns = patterns
        
    def set_exclude_patterns(self, patterns: List[str]):
        """Set event name patterns to exclude"""
        self.exclude_patterns = patterns
        
    def log_event(self, event_name: str, data: Dict[str, Any], 
                  context_key: Optional[str] = None):
        """Log a trace event"""
        if not self.enabled:
            return
            
        # Check filters
        if self.filter_patterns and not any(p in event_name 
                                          for p in self.filter_patterns):
            return
            
        if any(p in event_name for p in self.exclude_patterns):
            return
            
        # Create event
        event = TraceEvent(
            timestamp=time.time(),
            event_name=event_name,
            context_key=context_key or "global",
            data=data
        )
        
        # Store event
        self.events.append(event)
        
        # Calculate time delta
        delta = event.timestamp - self.start_time
        
        # Console output
        if self.console_output:
            print(event.to_lttng_format(delta))
            
        # File output
        if self.file_output:
            with open(self.file_path, 'a') as f:
                f.write(event.to_lttng_format(delta) + '\n')
                
    def get_events(self, start_time: Optional[float] = None,
                  end_time: Optional[float] = None) -> List[TraceEvent]:
        """Get events in time range"""
        if start_time is None:
            start_time = self.start_time
        if end_time is None:
            end_time = time.time()
            
        return [e for e in self.events 
                if start_time <= e.timestamp <= end_time]
                
    def get_events_by_name(self, event_name: str) -> List[TraceEvent]:
        """Get events by name"""
        return [e for e in self.events if e.event_name == event_name]
        
    def get_events_by_context(self, context_key: str) -> List[TraceEvent]:
        """Get events by context"""
        return [e for e in self.events if e.context_key == context_key]
        
    def clear(self):
        """Clear all events"""
        self.events.clear()
        self.start_time = time.time()
        
    def save_to_file(self, file_path: str):
        """Save all events to file"""
        with open(file_path, 'w') as f:
            json.dump([e.to_json() for e in self.events], f, indent=2)
            
    def save_json(self, file_path: str):
        """Save traces in JSON format for analysis"""
        data = {
            'metadata': {
                'start_time': self.start_time,
                'duration': time.time() - self.start_time,
                'total_events': len(self.events)
            },
            'events': [e.to_json() for e in self.events],
            'statistics': self.get_statistics()
        }
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
            
    def load_from_file(self, file_path: str):
        """Load events from file"""
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        self.events = []
        for event_data in data:
            event = TraceEvent(
                timestamp=event_data['timestamp'],
                event_name=event_data['event'],
                context_key=event_data['context'],
                data=event_data['data']
            )
            self.events.append(event)
            
        if self.events:
            self.start_time = min(e.timestamp for e in self.events)
            
    def get_statistics(self) -> Dict[str, Any]:
        """Get trace statistics"""
        if not self.events:
            return {
                'total_events': 0,
                'duration': 0,
                'events_per_second': 0
            }
            
        start = min(e.timestamp for e in self.events)
        end = max(e.timestamp for e in self.events)
        duration = end - start
        
        return {
            'total_events': len(self.events),
            'duration': duration,
            'events_per_second': len(self.events) / duration if duration > 0 else 0,
            'event_types': len(set(e.event_name for e in self.events)),
            'contexts': len(set(e.context_key for e in self.events))
        }


# Global trace logger instance
trace_logger = TraceLogger()