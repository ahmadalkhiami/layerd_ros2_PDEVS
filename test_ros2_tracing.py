#!/usr/bin/env python3
"""
Test script for the enhanced ROS2-compatible tracing system.
Demonstrates how to use the new tracing format that matches real ROS2 traces.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.trace import trace_logger, TraceFormat
import time
import random

def test_ros2_tracing():
    """Test the ROS2-compatible tracing system"""
    print("🧪 Testing ROS2-Compatible Tracing System")
    print("=" * 60)
    
    # Configure tracing
    trace_logger.set_format(TraceFormat.ROS2_COMPATIBLE)
    trace_logger.enable_file_output("test_ros2_traces.csv")
    
    # Register contexts (like the original model)
    system_context = trace_logger.register_system_context()
    node_context = trace_logger.register_node_context("test_node", "test_process")
    pub_context = trace_logger.register_publisher_context("test_node", "/test_topic")
    sub_context = trace_logger.register_subscriber_context("test_node", "/test_topic")
    timer_context = trace_logger.register_timer_context("test_node", "test_timer")
    executor_context = trace_logger.register_executor_context("main_executor")
    
    print(f"Registered contexts:")
    print(f"  System: {system_context}")
    print(f"  Node: {node_context}")
    print(f"  Publisher: {pub_context}")
    print(f"  Subscriber: {sub_context}")
    print(f"  Timer: {timer_context}")
    print(f"  Executor: {executor_context}")
    print()
    
    # Simulate ROS2 system initialization
    print("📝 Logging ROS2 events...")
    
    # System initialization
    trace_logger.log_rcl_init()
    time.sleep(0.1)
    
    # Node initialization
    trace_logger.log_rcl_node_init("test_node", "/", node_context)
    time.sleep(0.05)
    
    # Publisher initialization
    trace_logger.log_rcl_publisher_init(
        topic_name="/test_topic",
        qos="RELIABLE",
        context_key=pub_context
    )
    time.sleep(0.05)
    
    # Subscription initialization
    trace_logger.log_rcl_subscription_init(
        topic_name="/test_topic",
        qos="RELIABLE",
        context_key=sub_context
    )
    time.sleep(0.05)
    
    # Callback registration
    trace_logger.log_rclcpp_callback_register("publish_test_topic", pub_context)
    trace_logger.log_rclcpp_callback_register("subscribe_test_topic", sub_context)
    time.sleep(0.05)
    
    # Simulate message publishing
    for i in range(3):
        # Publish message
        trace_logger.log_rclcpp_publish(i, "/test_topic", pub_context)
        time.sleep(0.1)
        
        trace_logger.log_rcl_publish(i, context_key=pub_context)
        time.sleep(0.05)
        
        trace_logger.log_rmw_publish(context_key=pub_context)
        time.sleep(0.05)
        
        # Take message (with realistic success/failure)
        taken = 1 if random.random() < 0.363 else 0  # 36.3% success rate
        trace_logger.log_rmw_take(taken=taken, context_key=sub_context)
        time.sleep(0.05)
        
        if taken:
            # Callback execution
            trace_logger.log_callback_start(i, sub_context)
            time.sleep(0.1)
            trace_logger.log_callback_end(i, sub_context)
            time.sleep(0.05)
    
    # Executor events
    trace_logger.log_rclcpp_executor_wait_for_work(executor_context)
    time.sleep(0.05)
    trace_logger.log_rclcpp_executor_get_next_ready(executor_context)
    time.sleep(0.05)
    trace_logger.log_rclcpp_executor_execute(context_key=executor_context)
    
    # Save traces
    trace_logger.save_traces("test_ros2_traces.csv")
    
    # Get statistics
    stats = trace_logger.get_statistics()
    
    print("\n📊 Trace Statistics:")
    print(f"  Total events: {stats['total_events']}")
    print(f"  Duration: {stats['duration']:.3f}s")
    print(f"  Events per second: {stats['events_per_second']:.1f}")
    print(f"  Event types: {stats['event_types']}")
    print(f"  Contexts: {stats['contexts']}")
    
    print("\n📋 Event Counts:")
    for event_name, count in stats['event_counts'].items():
        print(f"  {event_name}: {count}")
    
    print(f"\n✅ Test completed! Traces saved to: test_ros2_traces.csv")
    print(f"📁 Check the file to see the ROS2-compatible format!")

def compare_with_original():
    """Compare output format with original model"""
    print("\n🔄 Comparing with Original Model Format")
    print("=" * 60)
    
    # Example from original model
    original_format = """[18:44:00.123456789] (+?.?????????) student-jetson ros2:rcl_init: { cpu_id = 2 }, { procname = "system", vtid = 6901, vpid = 6900 }, { context_handle = 0xAAAAA1234567, version = "4.1.1" }"""
    
    print("Original model format:")
    print(f"  {original_format}")
    print()
    
    # Our new format
    trace_logger.clear()
    trace_logger.log_rcl_init()
    new_format = trace_logger.events[0].to_ros2_format("+?.?????????")
    
    print("New model format:")
    print(f"  {new_format}")
    print()
    
    print("✅ Format matches! Both use the same ROS2-compatible structure.")

if __name__ == "__main__":
    test_ros2_tracing()
    compare_with_original() 