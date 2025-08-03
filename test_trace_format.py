#!/usr/bin/env python3
"""
Test script to verify ROS2 trace format
"""

import sys
import os

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.trace import trace_logger

def test_trace_format():
    """Test that trace format matches ROS2 format exactly"""
    
    print("Testing ROS2 trace format...")
    
    # Clear any existing events
    trace_logger.clear()
    
    # Test various event types
    trace_logger.log_rcl_init()
    trace_logger.log_rcl_node_init("test_node")
    trace_logger.log_rcl_publisher_init(topic_name="/test_topic")
    trace_logger.log_rclcpp_publish(1, "/test_topic")
    trace_logger.log_rcl_publish(1)
    trace_logger.log_rmw_publish()
    trace_logger.log_rmw_take()
    trace_logger.log_callback_start()
    trace_logger.log_callback_end()
    trace_logger.log_rclcpp_executor_wait_for_work()
    trace_logger.log_rclcpp_executor_get_next_ready()
    trace_logger.log_rclcpp_executor_execute()
    trace_logger.log_rclcpp_executor_spin_some()
    
    # Save to file
    trace_logger.save_traces("test_format.csv")
    
    print("Trace file generated: test_format.csv")
    print("Please check the format matches ROS2 tracing format exactly.")

if __name__ == "__main__":
    test_trace_format() 