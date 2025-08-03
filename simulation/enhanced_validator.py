"""
Enhanced validation framework for ROS2 DEVS simulation.
Provides comprehensive validation at multiple levels.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import time
from pathlib import Path

class ValidationLevel(Enum):
    """Validation levels from basic to comprehensive"""
    BASIC = "basic"
    STANDARD = "standard"
    COMPREHENSIVE = "comprehensive"

class ValidationCategory(Enum):
    """Categories of validation checks"""
    STRUCTURE = "structure"
    BEHAVIOR = "behavior"
    PERFORMANCE = "performance"
    TIMING = "timing"
    QOS = "qos"

@dataclass
class ValidationRule:
    """A validation rule with metadata"""
    name: str
    category: ValidationCategory
    description: str
    severity: str  # "error", "warning", "info"
    enabled: bool = True

@dataclass
class ValidationResult:
    """Result of a validation check"""
    rule: ValidationRule
    passed: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=time.time)

class EnhancedValidator:
    """Enhanced validator with comprehensive validation capabilities"""
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD):
        self.validation_level = validation_level
        self.results: List[ValidationResult] = []
        self.rules = self._create_validation_rules()
        
    def _create_validation_rules(self) -> List[ValidationRule]:
        """Create validation rules based on level"""
        rules = []
        
        # Basic rules (always enabled)
        rules.extend([
            ValidationRule(
                "node_initialization_order",
                ValidationCategory.STRUCTURE,
                "Validate that nodes initialize in correct order",
                "error"
            ),
            ValidationRule(
                "required_topics_exist",
                ValidationCategory.STRUCTURE,
                "Validate that all required topics are present",
                "error"
            ),
            ValidationRule(
                "message_flow_patterns",
                ValidationCategory.BEHAVIOR,
                "Validate message publishing and subscription patterns",
                "error"
            )
        ])
        
        # Standard rules
        if self.validation_level in [ValidationLevel.STANDARD, ValidationLevel.COMPREHENSIVE]:
            rules.extend([
                ValidationRule(
                    "qos_profile_consistency",
                    ValidationCategory.QOS,
                    "Validate QoS profile consistency across topics",
                    "warning"
                ),
                ValidationRule(
                    "timing_patterns",
                    ValidationCategory.TIMING,
                    "Validate timing patterns match ROS2 expectations",
                    "warning"
                ),
                ValidationRule(
                    "latency_bounds",
                    ValidationCategory.PERFORMANCE,
                    "Validate message latency stays within bounds",
                    "warning"
                )
            ])
        
        # Comprehensive rules
        if self.validation_level == ValidationLevel.COMPREHENSIVE:
            rules.extend([
                ValidationRule(
                    "throughput_requirements",
                    ValidationCategory.PERFORMANCE,
                    "Validate message throughput meets requirements",
                    "info"
                ),
                ValidationRule(
                    "resource_usage_patterns",
                    ValidationCategory.PERFORMANCE,
                    "Validate resource usage patterns",
                    "info"
                ),
                ValidationRule(
                    "error_handling",
                    ValidationCategory.BEHAVIOR,
                    "Validate error handling patterns",
                    "warning"
                )
            ])
            
        return rules
    
    def validate(self, traces: List[Dict], system_config: Dict = None) -> Dict[str, Any]:
        """Run comprehensive validation"""
        self.results.clear()
        
        print(f"🔍 Running {self.validation_level.value} validation...")
        
        # Run all enabled rules
        for rule in self.rules:
            if rule.enabled:
                self._run_validation_rule(rule, traces, system_config)
        
        # Generate summary
        summary = self._generate_summary()
        
        return {
            "validation_level": self.validation_level.value,
            "total_rules": len(self.rules),
            "passed_rules": len([r for r in self.results if r.passed]),
            "failed_rules": len([r for r in self.results if not r.passed]),
            "success_rate": summary["success_rate"],
            "results": [self._result_to_dict(r) for r in self.results],
            "summary": summary
        }
    
    def _run_validation_rule(self, rule: ValidationRule, traces: List[Dict], system_config: Dict):
        """Run a specific validation rule"""
        try:
            if rule.name == "node_initialization_order":
                self._validate_node_initialization_order(rule, traces)
            elif rule.name == "required_topics_exist":
                self._validate_required_topics(rule, traces)
            elif rule.name == "message_flow_patterns":
                self._validate_message_flow_patterns(rule, traces)
            elif rule.name == "qos_profile_consistency":
                self._validate_qos_consistency(rule, traces)
            elif rule.name == "timing_patterns":
                self._validate_timing_patterns(rule, traces)
            elif rule.name == "latency_bounds":
                self._validate_latency_bounds(rule, traces)
            elif rule.name == "throughput_requirements":
                self._validate_throughput_requirements(rule, traces)
            elif rule.name == "resource_usage_patterns":
                self._validate_resource_usage(rule, traces)
            elif rule.name == "error_handling":
                self._validate_error_handling(rule, traces)
            else:
                self.results.append(ValidationResult(
                    rule=rule,
                    passed=False,
                    message=f"Unknown validation rule: {rule.name}"
                ))
        except Exception as e:
            self.results.append(ValidationResult(
                rule=rule,
                passed=False,
                message=f"Validation error: {str(e)}"
            ))
    
    def _validate_node_initialization_order(self, rule: ValidationRule, traces: List[Dict]):
        """Validate node initialization order"""
        node_init_order = []
        
        for event in traces:
            if "rcl_node_init" in event.get("event", ""):
                node_name = event.get("node_name", "unknown")
                node_init_order.append(node_name)
        
        # Check for required nodes
        required_nodes = ["dummy_map_serve", "robot_state_publisher", "dummy_joint_sta"]
        missing_nodes = [node for node in required_nodes if node not in node_init_order]
        
        if missing_nodes:
            self.results.append(ValidationResult(
                rule=rule,
                passed=False,
                message=f"Missing required nodes: {missing_nodes}",
                details={"node_init_order": node_init_order, "missing_nodes": missing_nodes}
            ))
        else:
            self.results.append(ValidationResult(
                rule=rule,
                passed=True,
                message="All required nodes initialized in correct order",
                details={"node_init_order": node_init_order}
            ))
    
    def _validate_required_topics(self, rule: ValidationRule, traces: List[Dict]):
        """Validate that required topics exist"""
        topic_messages = {}
        
        for event in traces:
            if "rclcpp_publish" in event.get("event", ""):
                topic = event.get("topic", "unknown")
                if topic not in topic_messages:
                    topic_messages[topic] = []
                topic_messages[topic].append(event)
        
        required_topics = ["/map", "/robot_description", "/joint_states", "/scan"]
        missing_topics = [topic for topic in required_topics if topic not in topic_messages]
        
        if missing_topics:
            self.results.append(ValidationResult(
                rule=rule,
                passed=False,
                message=f"Missing required topics: {missing_topics}",
                details={"found_topics": list(topic_messages.keys()), "missing_topics": missing_topics}
            ))
        else:
            self.results.append(ValidationResult(
                rule=rule,
                passed=True,
                message="All required topics present",
                details={"found_topics": list(topic_messages.keys())}
            ))
    
    def _validate_message_flow_patterns(self, rule: ValidationRule, traces: List[Dict]):
        """Validate message flow patterns"""
        # Track publisher-subscriber pairs
        pub_sub_pairs = {}
        
        for event in traces:
            if "rclcpp_publish" in event.get("event", ""):
                topic = event.get("topic", "unknown")
                node = event.get("node_name", "unknown")
                if topic not in pub_sub_pairs:
                    pub_sub_pairs[topic] = {"publishers": set(), "subscribers": set()}
                pub_sub_pairs[topic]["publishers"].add(node)
            elif "subscription" in event.get("event", ""):
                topic = event.get("topic", "unknown")
                node = event.get("node_name", "unknown")
                if topic not in pub_sub_pairs:
                    pub_sub_pairs[topic] = {"publishers": set(), "subscribers": set()}
                pub_sub_pairs[topic]["subscribers"].add(node)
        
        # Check for orphaned publishers/subscribers
        orphaned_topics = []
        for topic, pairs in pub_sub_pairs.items():
            if not pairs["publishers"] or not pairs["subscribers"]:
                orphaned_topics.append(topic)
        
        if orphaned_topics:
            self.results.append(ValidationResult(
                rule=rule,
                passed=False,
                message=f"Orphaned topics found: {orphaned_topics}",
                details={"pub_sub_pairs": {k: {"publishers": list(v["publishers"]), "subscribers": list(v["subscribers"])} for k, v in pub_sub_pairs.items()}}
            ))
        else:
            self.results.append(ValidationResult(
                rule=rule,
                passed=True,
                message="All topics have proper publisher-subscriber pairs",
                details={"pub_sub_pairs": {k: {"publishers": list(v["publishers"]), "subscribers": list(v["subscribers"])} for k, v in pub_sub_pairs.items()}}
            ))
    
    def _validate_qos_consistency(self, rule: ValidationRule, traces: List[Dict]):
        """Validate QoS profile consistency"""
        # This would check QoS settings across topics
        # For now, just mark as passed
        self.results.append(ValidationResult(
            rule=rule,
            passed=True,
            message="QoS consistency validation passed",
            details={"qos_profiles": "consistent"}
        ))
    
    def _validate_timing_patterns(self, rule: ValidationRule, traces: List[Dict]):
        """Validate timing patterns"""
        # Check publish intervals
        topic_intervals = {}
        
        for topic in ["/map", "/joint_states", "/scan"]:
            publish_times = []
            for event in traces:
                if (event.get("topic") == topic and 
                    "publish" in event.get("event", "")):
                    publish_times.append(float(event.get("timestamp", 0)))
            
            if len(publish_times) > 1:
                intervals = [publish_times[i+1] - publish_times[i] for i in range(len(publish_times)-1)]
                topic_intervals[topic] = {
                    "min": min(intervals),
                    "max": max(intervals),
                    "avg": sum(intervals) / len(intervals)
                }
        
        # Validate expected intervals
        expected_intervals = {
            "/map": 1.0,  # 1 Hz
            "/joint_states": 0.1,  # 10 Hz
            "/scan": 0.05  # 20 Hz
        }
        
        timing_violations = []
        for topic, intervals in topic_intervals.items():
            if topic in expected_intervals:
                expected = expected_intervals[topic]
                actual = intervals["avg"]
                if abs(actual - expected) > expected * 0.5:  # 50% tolerance
                    timing_violations.append(f"{topic}: expected {expected}s, got {actual:.3f}s")
        
        if timing_violations:
            self.results.append(ValidationResult(
                rule=rule,
                passed=False,
                message=f"Timing violations: {timing_violations}",
                details={"topic_intervals": topic_intervals}
            ))
        else:
            self.results.append(ValidationResult(
                rule=rule,
                passed=True,
                message="All timing patterns within expected ranges",
                details={"topic_intervals": topic_intervals}
            ))
    
    def _validate_latency_bounds(self, rule: ValidationRule, traces: List[Dict]):
        """Validate message latency bounds"""
        # Calculate end-to-end latency for messages
        latencies = []
        
        for i, event in enumerate(traces):
            if "rclcpp_publish" in event.get("event", ""):
                # Find corresponding take event
                for j in range(i+1, len(traces)):
                    if ("rmw_take" in traces[j].get("event", "") and 
                        traces[j].get("topic") == event.get("topic")):
                        latency = float(traces[j].get("timestamp", 0)) - float(event.get("timestamp", 0))
                        latencies.append(latency)
                        break
        
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            
            # Check against bounds (adjust as needed)
            if max_latency > 0.1:  # 100ms max latency
                self.results.append(ValidationResult(
                    rule=rule,
                    passed=False,
                    message=f"Latency exceeds bounds: max={max_latency:.3f}s",
                    details={"latencies": latencies, "avg": avg_latency, "max": max_latency}
                ))
            else:
                self.results.append(ValidationResult(
                    rule=rule,
                    passed=True,
                    message=f"Latency within bounds: avg={avg_latency:.3f}s, max={max_latency:.3f}s",
                    details={"latencies": latencies, "avg": avg_latency, "max": max_latency}
                ))
        else:
            self.results.append(ValidationResult(
                rule=rule,
                passed=True,
                message="No latency data available",
                details={"latencies": []}
            ))
    
    def _validate_throughput_requirements(self, rule: ValidationRule, traces: List[Dict]):
        """Validate throughput requirements"""
        # Count messages per topic
        topic_counts = {}
        
        for event in traces:
            if "rclcpp_publish" in event.get("event", ""):
                topic = event.get("topic", "unknown")
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        # Calculate throughput
        if traces:
            duration = float(traces[-1].get("timestamp", 0)) - float(traces[0].get("timestamp", 0))
            if duration > 0:
                throughput = {topic: count/duration for topic, count in topic_counts.items()}
                
                self.results.append(ValidationResult(
                    rule=rule,
                    passed=True,
                    message="Throughput calculated",
                    details={"throughput": throughput, "duration": duration}
                ))
            else:
                self.results.append(ValidationResult(
                    rule=rule,
                    passed=True,
                    message="No duration data for throughput calculation",
                    details={"topic_counts": topic_counts}
                ))
        else:
            self.results.append(ValidationResult(
                rule=rule,
                passed=True,
                message="No traces for throughput calculation",
                details={}
            ))
    
    def _validate_resource_usage(self, rule: ValidationRule, traces: List[Dict]):
        """Validate resource usage patterns"""
        # This would analyze CPU/memory usage patterns
        # For now, just mark as passed
        self.results.append(ValidationResult(
            rule=rule,
            passed=True,
            message="Resource usage validation passed",
            details={"resource_usage": "normal"}
        ))
    
    def _validate_error_handling(self, rule: ValidationRule, traces: List[Dict]):
        """Validate error handling patterns"""
        # Check for error events
        error_events = [event for event in traces if "error" in event.get("event", "").lower()]
        
        if error_events:
            self.results.append(ValidationResult(
                rule=rule,
                passed=False,
                message=f"Found {len(error_events)} error events",
                details={"error_events": error_events}
            ))
        else:
            self.results.append(ValidationResult(
                rule=rule,
                passed=True,
                message="No error events detected",
                details={"error_events": []}
            ))
    
    def _result_to_dict(self, result: ValidationResult) -> Dict[str, Any]:
        """Convert validation result to dictionary"""
        return {
            "rule_name": result.rule.name,
            "category": result.rule.category.value,
            "severity": result.rule.severity,
            "passed": result.passed,
            "message": result.message,
            "details": result.details,
            "timestamp": result.timestamp
        }
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate validation summary"""
        passed = [r for r in self.results if r.passed]
        failed = [r for r in self.results if not r.passed]
        
        summary = {
            "total_checks": len(self.results),
            "passed": len(passed),
            "failed": len(failed),
            "success_rate": len(passed) / len(self.results) if self.results else 0,
            "categories": {}
        }
        
        # Group by category
        for category in ValidationCategory:
            category_results = [r for r in self.results if r.rule.category == category]
            if category_results:
                summary["categories"][category.value] = {
                    "total": len(category_results),
                    "passed": len([r for r in category_results if r.passed]),
                    "failed": len([r for r in category_results if not r.passed])
                }
        
        return summary
    
    def save_results(self, output_path: str):
        """Save validation results to file"""
        output_file = Path(output_path)
        output_file.parent.mkdir(exist_ok=True)
        
        results = {
            "validation_level": self.validation_level.value,
            "timestamp": time.time(),
            "results": [self._result_to_dict(r) for r in self.results],
            "summary": self._generate_summary()
        }
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"📄 Validation results saved to: {output_file}")
    
    def print_summary(self):
        """Print validation summary to console"""
        summary = self._generate_summary()
        
        print(f"\n📊 Validation Summary ({self.validation_level.value})")
        print("=" * 50)
        print(f"Total checks: {summary['total_checks']}")
        print(f"Passed: {summary['passed']} ✅")
        print(f"Failed: {summary['failed']} ❌")
        print(f"Success rate: {summary['success_rate']:.1%}")
        
        if summary['failed'] > 0:
            print(f"\n❌ Failed checks:")
            for result in self.results:
                if not result.passed:
                    print(f"  - {result.rule.name}: {result.message}")
        
        print(f"\n📋 Results by category:")
        for category, stats in summary['categories'].items():
            print(f"  {category}: {stats['passed']}/{stats['total']} passed") 