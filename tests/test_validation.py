"""
Comprehensive test suite for ROS2 DEVS validation.
Tests various validation scenarios and edge cases.
"""

import sys
import os
import unittest
import tempfile
import json
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulation.enhanced_validator import (
    EnhancedValidator, ValidationLevel, ValidationCategory
)

class TestEnhancedValidator(unittest.TestCase):
    """Test cases for enhanced validation framework"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.validator = EnhancedValidator(ValidationLevel.COMPREHENSIVE)
        
        # Sample valid traces
        self.valid_traces = [
            {"event": "rcl_node_init", "node_name": "dummy_map_serve", "timestamp": 0.0},
            {"event": "rcl_node_init", "node_name": "robot_state_publisher", "timestamp": 0.1},
            {"event": "rcl_node_init", "node_name": "dummy_joint_sta", "timestamp": 0.2},
            {"event": "rclcpp_publish", "topic": "/map", "node_name": "dummy_map_serve", "timestamp": 1.0},
            {"event": "rclcpp_publish", "topic": "/robot_description", "node_name": "robot_state_publisher", "timestamp": 1.1},
            {"event": "rclcpp_publish", "topic": "/joint_states", "node_name": "dummy_joint_sta", "timestamp": 1.2},
            {"event": "rclcpp_publish", "topic": "/scan", "node_name": "dummy_laser", "timestamp": 1.3},
            {"event": "subscription", "topic": "/joint_states", "node_name": "robot_state_publisher", "timestamp": 1.4},
            {"event": "rmw_take", "topic": "/joint_states", "timestamp": 1.5},
            {"event": "rclcpp_publish", "topic": "/map", "node_name": "dummy_map_serve", "timestamp": 2.0},
            {"event": "rclcpp_publish", "topic": "/joint_states", "node_name": "dummy_joint_sta", "timestamp": 2.1},
            {"event": "rclcpp_publish", "topic": "/scan", "node_name": "dummy_laser", "timestamp": 2.2},
        ]
        
        # Sample invalid traces (missing required nodes)
        self.invalid_traces = [
            {"event": "rcl_node_init", "node_name": "some_node", "timestamp": 0.0},
            {"event": "rclcpp_publish", "topic": "/some_topic", "node_name": "some_node", "timestamp": 1.0},
        ]
        
        # Sample traces with timing violations
        self.timing_violation_traces = [
            {"event": "rcl_node_init", "node_name": "dummy_map_serve", "timestamp": 0.0},
            {"event": "rcl_node_init", "node_name": "robot_state_publisher", "timestamp": 0.1},
            {"event": "rcl_node_init", "node_name": "dummy_joint_sta", "timestamp": 0.2},
            {"event": "rclcpp_publish", "topic": "/map", "node_name": "dummy_map_serve", "timestamp": 1.0},
            {"event": "rclcpp_publish", "topic": "/map", "node_name": "dummy_map_serve", "timestamp": 5.0},  # Too slow
            {"event": "rclcpp_publish", "topic": "/joint_states", "node_name": "dummy_joint_sta", "timestamp": 1.2},
            {"event": "rclcpp_publish", "topic": "/joint_states", "node_name": "dummy_joint_sta", "timestamp": 1.3},
            {"event": "rclcpp_publish", "topic": "/scan", "node_name": "dummy_laser", "timestamp": 1.3},
            {"event": "rclcpp_publish", "topic": "/scan", "node_name": "dummy_laser", "timestamp": 1.4},
        ]
    
    def test_basic_validation_level(self):
        """Test basic validation level"""
        basic_validator = EnhancedValidator(ValidationLevel.BASIC)
        results = basic_validator.validate(self.valid_traces)
        
        self.assertEqual(results["validation_level"], "basic")
        self.assertGreater(results["total_rules"], 0)
        self.assertGreaterEqual(results["passed_rules"], 0)
    
    def test_standard_validation_level(self):
        """Test standard validation level"""
        standard_validator = EnhancedValidator(ValidationLevel.STANDARD)
        results = standard_validator.validate(self.valid_traces)
        
        self.assertEqual(results["validation_level"], "standard")
        self.assertGreater(results["total_rules"], 0)
    
    def test_comprehensive_validation_level(self):
        """Test comprehensive validation level"""
        comprehensive_validator = EnhancedValidator(ValidationLevel.COMPREHENSIVE)
        results = comprehensive_validator.validate(self.valid_traces)
        
        self.assertEqual(results["validation_level"], "comprehensive")
        self.assertGreater(results["total_rules"], 0)
    
    def test_valid_traces_validation(self):
        """Test validation with valid traces"""
        results = self.validator.validate(self.valid_traces)
        
        # Should pass most checks
        self.assertGreater(results["passed_rules"], 0)
        self.assertGreaterEqual(results["success_rate"], 0.5)
    
    def test_invalid_traces_validation(self):
        """Test validation with invalid traces"""
        results = self.validator.validate(self.invalid_traces)
        
        # Should fail some checks
        self.assertGreater(results["failed_rules"], 0)
    
    def test_timing_violations(self):
        """Test timing violation detection"""
        results = self.validator.validate(self.timing_violation_traces)
        
        # Should detect timing violations
        failed_results = [r for r in results["results"] if not r["passed"]]
        timing_violations = [r for r in failed_results if "timing" in r["message"].lower()]
        
        self.assertGreater(len(timing_violations), 0)
    
    def test_node_initialization_validation(self):
        """Test node initialization validation"""
        results = self.validator.validate(self.valid_traces)
        
        # Check for node initialization results
        node_results = [r for r in results["results"] if "node_initialization_order" in r["rule_name"]]
        self.assertGreater(len(node_results), 0)
    
    def test_required_topics_validation(self):
        """Test required topics validation"""
        results = self.validator.validate(self.valid_traces)
        
        # Check for required topics results
        topic_results = [r for r in results["results"] if "required_topics_exist" in r["rule_name"]]
        self.assertGreater(len(topic_results), 0)
    
    def test_message_flow_validation(self):
        """Test message flow validation"""
        results = self.validator.validate(self.valid_traces)
        
        # Check for message flow results
        flow_results = [r for r in results["results"] if "message_flow_patterns" in r["rule_name"]]
        self.assertGreater(len(flow_results), 0)
    
    def test_latency_validation(self):
        """Test latency validation"""
        # Create traces with latency data
        latency_traces = self.valid_traces + [
            {"event": "rmw_take", "topic": "/map", "timestamp": 1.05},
            {"event": "rmw_take", "topic": "/joint_states", "timestamp": 1.25},
        ]
        
        results = self.validator.validate(latency_traces)
        
        # Check for latency results
        latency_results = [r for r in results["results"] if "latency_bounds" in r["rule_name"]]
        self.assertGreater(len(latency_results), 0)
    
    def test_throughput_validation(self):
        """Test throughput validation"""
        results = self.validator.validate(self.valid_traces)
        
        # Check for throughput results
        throughput_results = [r for r in results["results"] if "throughput_requirements" in r["rule_name"]]
        self.assertGreater(len(throughput_results), 0)
    
    def test_error_handling_validation(self):
        """Test error handling validation"""
        # Create traces with error events
        error_traces = self.valid_traces + [
            {"event": "error_event", "message": "Test error", "timestamp": 1.5},
        ]
        
        results = self.validator.validate(error_traces)
        
        # Check for error handling results
        error_results = [r for r in results["results"] if "error_handling" in r["rule_name"]]
        self.assertGreater(len(error_results), 0)
    
    def test_validation_summary(self):
        """Test validation summary generation"""
        results = self.validator.validate(self.valid_traces)
        
        summary = results["summary"]
        
        self.assertIn("total_checks", summary)
        self.assertIn("passed", summary)
        self.assertIn("failed", summary)
        self.assertIn("success_rate", summary)
        self.assertIn("categories", summary)
    
    def test_save_results(self):
        """Test saving validation results to file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            results = self.validator.validate(self.valid_traces)
            self.validator.save_results(tmp_path)
            
            # Check that file was created and contains valid JSON
            with open(tmp_path, 'r') as f:
                saved_data = json.load(f)
            
            self.assertIn("validation_level", saved_data)
            self.assertIn("results", saved_data)
            self.assertIn("summary", saved_data)
            
        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_print_summary(self):
        """Test printing validation summary"""
        results = self.validator.validate(self.valid_traces)
        
        # This should not raise an exception
        self.validator.print_summary()
    
    def test_empty_traces(self):
        """Test validation with empty traces"""
        results = self.validator.validate([])
        
        self.assertEqual(results["total_rules"], len(self.validator.rules))
        self.assertGreaterEqual(results["failed_rules"], 0)
    
    def test_malformed_traces(self):
        """Test validation with malformed traces"""
        malformed_traces = [
            {"event": "rcl_node_init"},  # Missing required fields
            {"timestamp": 1.0},  # Missing event
            {},  # Empty event
        ]
        
        results = self.validator.validate(malformed_traces)
        
        # Should handle gracefully
        self.assertIsInstance(results, dict)
        self.assertIn("validation_level", results)
    
    def test_validation_categories(self):
        """Test that all validation categories are covered"""
        results = self.validator.validate(self.valid_traces)
        
        categories_found = set()
        for result in results["results"]:
            categories_found.add(result["category"])
        
        # Should have multiple categories
        self.assertGreater(len(categories_found), 1)
        
        # Should include expected categories
        expected_categories = {"structure", "behavior", "performance"}
        self.assertTrue(any(cat in categories_found for cat in expected_categories))


class TestValidationScenarios(unittest.TestCase):
    """Test specific validation scenarios"""
    
    def test_real_world_scenario(self):
        """Test a realistic ROS2 system scenario"""
        # Simulate a realistic ROS2 system
        realistic_traces = [
            # System initialization
            {"event": "rcl_init", "timestamp": 0.0},
            
            # Node initialization
            {"event": "rcl_node_init", "node_name": "dummy_map_serve", "timestamp": 0.1},
            {"event": "rcl_node_init", "node_name": "robot_state_publisher", "timestamp": 0.2},
            {"event": "rcl_node_init", "node_name": "dummy_joint_sta", "timestamp": 0.3},
            {"event": "rcl_node_init", "node_name": "dummy_laser", "timestamp": 0.4},
            
            # Publisher initialization
            {"event": "rcl_publisher_init", "topic": "/map", "node_name": "dummy_map_serve", "timestamp": 0.5},
            {"event": "rcl_publisher_init", "topic": "/robot_description", "node_name": "robot_state_publisher", "timestamp": 0.6},
            {"event": "rcl_publisher_init", "topic": "/joint_states", "node_name": "dummy_joint_sta", "timestamp": 0.7},
            {"event": "rcl_publisher_init", "topic": "/scan", "node_name": "dummy_laser", "timestamp": 0.8},
            
            # Subscription initialization
            {"event": "rcl_subscription_init", "topic": "/joint_states", "node_name": "robot_state_publisher", "timestamp": 0.9},
            
            # Message publishing (with proper timing)
            {"event": "rclcpp_publish", "topic": "/map", "node_name": "dummy_map_serve", "timestamp": 1.0},
            {"event": "rclcpp_publish", "topic": "/robot_description", "node_name": "robot_state_publisher", "timestamp": 1.1},
            {"event": "rclcpp_publish", "topic": "/joint_states", "node_name": "dummy_joint_sta", "timestamp": 1.2},
            {"event": "rclcpp_publish", "topic": "/scan", "node_name": "dummy_laser", "timestamp": 1.3},
            
            # Message consumption
            {"event": "rmw_take", "topic": "/joint_states", "timestamp": 1.4},
            {"event": "callback_start", "topic": "/joint_states", "timestamp": 1.5},
            {"event": "callback_end", "topic": "/joint_states", "timestamp": 1.6},
            
            # Continue with proper intervals
            {"event": "rclcpp_publish", "topic": "/map", "node_name": "dummy_map_serve", "timestamp": 2.0},
            {"event": "rclcpp_publish", "topic": "/joint_states", "node_name": "dummy_joint_sta", "timestamp": 2.1},
            {"event": "rclcpp_publish", "topic": "/scan", "node_name": "dummy_laser", "timestamp": 2.2},
        ]
        
        validator = EnhancedValidator(ValidationLevel.COMPREHENSIVE)
        results = validator.validate(realistic_traces)
        
        # Should pass most validations
        self.assertGreater(results["success_rate"], 0.7)
        self.assertGreater(results["passed_rules"], results["failed_rules"])
    
    def test_performance_degradation_scenario(self):
        """Test detection of performance degradation"""
        # Create traces with performance issues
        degraded_traces = [
            {"event": "rcl_node_init", "node_name": "dummy_map_serve", "timestamp": 0.0},
            {"event": "rcl_node_init", "node_name": "robot_state_publisher", "timestamp": 0.1},
            {"event": "rcl_node_init", "node_name": "dummy_joint_sta", "timestamp": 0.2},
            
            # Normal timing initially
            {"event": "rclcpp_publish", "topic": "/map", "node_name": "dummy_map_serve", "timestamp": 1.0},
            {"event": "rclcpp_publish", "topic": "/joint_states", "node_name": "dummy_joint_sta", "timestamp": 1.1},
            
            # Degraded timing later
            {"event": "rclcpp_publish", "topic": "/map", "node_name": "dummy_map_serve", "timestamp": 5.0},  # 4s delay
            {"event": "rclcpp_publish", "topic": "/joint_states", "node_name": "dummy_joint_sta", "timestamp": 5.1},
        ]
        
        validator = EnhancedValidator(ValidationLevel.STANDARD)
        results = validator.validate(degraded_traces)
        
        # Should detect timing violations
        failed_results = [r for r in results["results"] if not r["passed"]]
        timing_violations = [r for r in failed_results if "timing" in r["message"].lower()]
        
        self.assertGreater(len(timing_violations), 0)


if __name__ == "__main__":
    # Create tests directory if it doesn't exist
    tests_dir = Path(__file__).parent
    tests_dir.mkdir(exist_ok=True)
    
    # Run tests
    unittest.main(verbosity=2) 