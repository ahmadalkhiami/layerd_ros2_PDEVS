"""
RCL Timer management implementation.
"""

import time
from typing import Dict, List, Optional, Tuple
import heapq

from core import trace_logger


class Timer:
    """RCL timer"""
    
    def __init__(self, handle: int, period_ns: int):
        self.handle = handle
        self.period_ns = period_ns
        self.last_call_time = time.time()
        self.is_ready = False
        self.is_canceled = False
        
    def is_ready_to_call(self, current_time: float) -> bool:
        """Check if timer is ready to be called"""
        if self.is_canceled:
            return False
            
        elapsed_ns = (current_time - self.last_call_time) * 1e9
        return elapsed_ns >= self.period_ns
        
    def call(self):
        """Call the timer"""
        self.last_call_time = time.time()
        self.is_ready = False
        
    def cancel(self):
        """Cancel the timer"""
        self.is_canceled = True
        
    def reset(self):
        """Reset the timer"""
        self.last_call_time = time.time()
        self.is_canceled = False


class TimerManager:
    """Manages RCL timers"""
    
    def __init__(self):
        self.timers: Dict[int, Timer] = {}
        self.timer_heap: List[Tuple[float, int]] = []  # (next_call_time, handle)
        
    def add_timer(self, handle: int, period_s: float):
        """Add a new timer"""
        timer = Timer(handle, int(period_s * 1e9))
        self.timers[handle] = timer
        
        # Add to heap
        next_call = time.time() + period_s
        heapq.heappush(self.timer_heap, (next_call, handle))
        
        trace_logger.log_event(
            "rcl_timer_added",
            {
                "timer_handle": f"0x{handle:X}",
                "period_ms": period_s * 1000
            }
        )
        
    def remove_timer(self, handle: int):
        """Remove a timer"""
        if handle in self.timers:
            self.timers[handle].cancel()
            del self.timers[handle]
            
            trace_logger.log_event(
                "rcl_timer_removed",
                {"timer_handle": f"0x{handle:X}"}
            )
            
    def get_next_expiration(self) -> Optional[float]:
        """Get next timer expiration time"""
        # Clean up canceled timers from heap
        while self.timer_heap:
            next_time, handle = self.timer_heap[0]
            
            if handle not in self.timers or self.timers[handle].is_canceled:
                heapq.heappop(self.timer_heap)
                continue
                
            return next_time
            
        return None
        
    def get_expired_timers(self) -> List[int]:
        """Get list of expired timer handles"""
        current_time = time.time()
        expired = []
        
        while self.timer_heap:
            next_time, handle = self.timer_heap[0]
            
            if next_time > current_time:
                break
                
            heapq.heappop(self.timer_heap)
            
            if handle in self.timers and not self.timers[handle].is_canceled:
                timer = self.timers[handle]
                if timer.is_ready_to_call(current_time):
                    expired.append(handle)
                    timer.call()
                    
                    # Re-add to heap for next call
                    next_call = current_time + (timer.period_ns / 1e9)
                    heapq.heappush(self.timer_heap, (next_call, handle))
                    
        return expired
        
    def update(self):
        """Update timer states"""
        # This could be used for more complex timer management
        pass