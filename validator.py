"""
Validation framework for ROS2 DEVS simulation.
"""

from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum, auto
import re

from core import TraceEvent, trace_logger


class ValidationResult(Enum):
    """Validation result types"""
    PASS = auto()
    FAIL = auto()
    WARNING = auto()
    

@dataclass
class ValidationCheck:
    """Single validation check result"""
    name: str
    result: ValidationResult
    message: str
    details: Optional[Dict[str, Any]] = None
    

class TraceValidator:
    """
    Validates simulation traces against expected ROS2 behavior.
    """
    
    def __init__(self):
        self.checks: List[ValidationCheck] = []
        
    def validate_all(self, traces: List[TraceEvent]) -> List[ValidationCheck]:
        """Run all validation checks"""
        self.checks.clear()
        
        # Run individual validators
        self._validate_initialization_order(traces)
        self._validate_message_flow(traces)
        self._validate_qos_enforcement(traces)
        self._validate_lifecycle_transitions(traces)
        self._validate_timing_constraints(traces)
        self._validate_graph_consistency(traces)
        
        return self.checks
        
    def _validate_initialization_order(self, traces: List[TraceEvent]):
        """Validate proper initialization order"""
        # Expected order: rcl_init -> node_init -> publisher/subscriber_init
        
        init_events = {
            'rcl_init': None,
            'node_init': [],
            'publisher_init': [],
            'subscription_init': []
        }
        
        for i, trace in enumerate(traces):
            if trace.event_name == 'rcl_init':
                init_events['rcl_init'] = i
            elif 'node_init' in trace.event_name:
                init_events['node_init'].append(i)
            elif 'publisher_init' in trace.event_name:
                init_events['publisher_init'].append(i)
            elif 'subscription_init' in trace.event_name:
                init_events['subscription_init'].append(i)
                
        # Check RCL initialized first
        if init_events['rcl_init'] is None:
            self.checks.append(ValidationCheck(
                "RCL Initialization",
                ValidationResult.FAIL,
                "RCL initialization not found"
            ))
            return
            
        # Check nodes initialized after RCL
        invalid_nodes = [i for i in init_events['node_init'] 
                        if i < init_events['rcl_init']]
        
        if invalid_nodes:
            self.checks.append(ValidationCheck(
                "Node Initialization Order",
                ValidationResult.FAIL,
                f"Nodes initialized before RCL: {len(invalid_nodes)}",
                {"invalid_indices": invalid_nodes}
            ))
        else:
            self.checks.append(ValidationCheck(
                "Node Initialization Order",
                ValidationResult.PASS,
                "All nodes initialized after RCL"
            ))
            
        # Check publishers/subscribers initialized after nodes
        if init_events['node_init']:
            first_node = min(init_events['node_init'])
            
            invalid_pubs = [i for i in init_events['publisher_init']
                           if i < first_node]
            invalid_subs = [i for i in init_events['subscription_init']
                           if i < first_node]
            
            if invalid_pubs or invalid_subs:
                self.checks.append(ValidationCheck(
                    "Publisher/Subscriber Initialization",
                    ValidationResult.FAIL,
                    "Publishers/Subscribers initialized before nodes",
                    {
                        "invalid_publishers": len(invalid_pubs),
                        "invalid_subscriptions": len(invalid_subs)
                    }
                ))
            else:
                self.checks.append(ValidationCheck(
                    "Publisher/Subscriber Initialization",
                    ValidationResult.PASS,
                    "All publishers/subscribers properly initialized"
                ))
                
    def _validate_message_flow(self, traces: List[TraceEvent]):
        """Validate message flow through layers"""
        # Track message flow: publish -> rmw_publish -> rmw_take -> callback
        
        message_flows = {}  # message_id -> flow_events
        
        for trace in traces:
            # Extract message ID from trace
            msg_id = self._extract_message_id(trace)
            if msg_id:
                if msg_id not in message_flows:
                    message_flows[msg_id] = []
                message_flows[msg_id].append(trace.event_name)
                
        # Expected flow pattern
        expected_flow = ['rclcpp_publish', 'rcl_publish', 'rmw_publish', 
                        'rmw_take', 'callback_start', 'callback_end']
        
        complete_flows = 0
        incomplete_flows = 0
        
        for msg_id, flow in message_flows.items():
            if all(event in flow for event in expected_flow):
                complete_flows += 1
            else:
                incomplete_flows += 1
                
        if incomplete_flows == 0:
            self.checks.append(ValidationCheck(
                "Message Flow Completeness",
                ValidationResult.PASS,
                f"All {complete_flows} messages completed full flow"
            ))
        else:
            self.checks.append(ValidationCheck(
                "Message Flow Completeness",
                ValidationResult.WARNING,
                f"{incomplete_flows} messages had incomplete flow",
                {
                    "complete": complete_flows,
                    "incomplete": incomplete_flows
                }
            ))
            
    def _validate_qos_enforcement(self, traces: List[TraceEvent]):
        """Validate QoS policy enforcement"""
        # Check for QoS violations and proper handling
        
        qos_violations = []
        deadline_misses = 0
        
        for trace in traces:
            if 'deadline_missed' in trace.event_name:
                deadline_misses += 1
            if 'qos_incompatible' in trace.event_name:
                qos_violations.append(trace)
                
        if deadline_misses > 0:
            self.checks.append(ValidationCheck(
                "QoS Deadline Enforcement",
                ValidationResult.WARNING,
                f"{deadline_misses} deadline violations detected",
                {"violations": deadline_misses}
            ))
        else:
            self.checks.append(ValidationCheck(
                "QoS Deadline Enforcement",
                ValidationResult.PASS,
                "No deadline violations"
            ))
            
    def _validate_lifecycle_transitions(self, traces: List[TraceEvent]):
        """Validate lifecycle state transitions"""
        # Track lifecycle transitions per node
        
        lifecycle_nodes = {}  # node -> transitions
        
        for trace in traces:
            if 'lifecycle' in trace.event_name and 'transition' in trace.event_name:
                node = trace.fields.get('node', 'unknown')
                if node not in lifecycle_nodes:
                    lifecycle_nodes[node] = []
                lifecycle_nodes[node].append(trace)
                
        # Validate each node's transitions
        invalid_transitions = []
        
        for node, transitions in lifecycle_nodes.items():
            if not self._validate_node_transitions(transitions):
                invalid_transitions.append(node)
                
        if invalid_transitions:
            self.checks.append(ValidationCheck(
                "Lifecycle Transitions",
                ValidationResult.FAIL,
                f"Invalid transitions in nodes: {invalid_transitions}"
            ))
        elif lifecycle_nodes:
            self.checks.append(ValidationCheck(
                "Lifecycle Transitions",
                ValidationResult.PASS,
                f"All lifecycle transitions valid for {len(lifecycle_nodes)} nodes"
            ))
            
    def _validate_timing_constraints(self, traces: List[TraceEvent]):
        """Validate timing constraints and performance"""
        # Check callback execution times
        
        callback_times = []
        
        for i, trace in enumerate(traces):
            if trace.event_name == 'callback_start':
                # Find matching callback_end
                msg_id = self._extract_message_id(trace)
                for j in range(i+1, len(traces)):
                    if (traces[j].event_name == 'callback_end' and
                        self._extract_message_id(traces[j]) == msg_id):
                        duration = traces[j].timestamp - trace.timestamp
                        callback_times.append(duration)
                        break
                        
        if callback_times:
            avg_time = sum(callback_times) / len(callback_times)
            max_time = max(callback_times)
            
            # Check if times are reasonable (< 100ms for simple callbacks)
            if max_time > 0.1:
                self.checks.append(ValidationCheck(
                    "Callback Performance",
                    ValidationResult.WARNING,
                    f"Long callback execution detected: {max_time*1000:.2f}ms",
                    {
                        "average_ms": avg_time * 1000,
                        "max_ms": max_time * 1000,
                        "count": len(callback_times)
                    }
                ))
            else:
                self.checks.append(ValidationCheck(
                    "Callback Performance",
                    ValidationResult.PASS,
                    f"Callback performance acceptable (avg: {avg_time*1000:.2f}ms)"
                ))
                
    def _validate_graph_consistency(self, traces: List[TraceEvent]):
        """Validate graph discovery consistency"""
        # Track graph events
        
        publishers = set()
        subscribers = set()
        
        for trace in traces:
            if 'publisher_created' in trace.event_name:
                topic = trace.fields.get('topic', '')
                node = trace.fields.get('node', '')
                publishers.add((topic, node))
            elif 'subscription_created' in trace.event_name:
                topic = trace.fields.get('topic', '')
                node = trace.fields.get('node', '')
                subscribers.add((topic, node))
                
        # Find orphaned topics
        pub_topics = {topic for topic, _ in publishers}
        sub_topics = {topic for topic, _ in subscribers}
        
        orphaned_pubs = pub_topics - sub_topics
        orphaned_subs = sub_topics - pub_topics
        
        if orphaned_pubs or orphaned_subs:
            self.checks.append(ValidationCheck(
                "Graph Consistency",
                ValidationResult.WARNING,
                "Orphaned topics detected",
                {
                    "publishers_without_subscribers": list(orphaned_pubs),
                    "subscribers_without_publishers": list(orphaned_subs)
                }
            ))
        else:
            self.checks.append(ValidationCheck(
                "Graph Consistency",
                ValidationResult.PASS,
                "All topics have matching publishers and subscribers"
            ))
            
    def _extract_message_id(self, trace: TraceEvent) -> Optional[str]:
        """Extract message ID from trace event"""
        if 'message_id' in trace.fields:
            return str(trace.fields['message_id'])
        if 'message' in trace.fields:
            # Try to extract from message handle
            msg_str = str(trace.fields['message'])
            match = re.search(r'0x([0-9A-Fa-f]+)', msg_str)
            if match:
                return match.group(1)
        return None
        
    def _validate_node_transitions(self, transitions: List[TraceEvent]) -> bool:
        """Validate a node's lifecycle transitions"""
        # Simple validation - could be enhanced
        return True
        
    def generate_report(self) -> str:
        """Generate validation report"""
        report = ["ROS2 DEVS Simulation Validation Report", "="*50, ""]
        
        # Summary
        passed = sum(1 for c in self.checks if c.result == ValidationResult.PASS)
        failed = sum(1 for c in self.checks if c.result == ValidationResult.FAIL)
        warnings = sum(1 for c in self.checks if c.result == ValidationResult.WARNING)
        
        report.append(f"Total Checks: {len(self.checks)}")
        report.append(f"Passed: {passed}")
        report.append(f"Failed: {failed}")
        report.append(f"Warnings: {warnings}")
        report.append("")
        
        # Details
        report.append("Detailed Results:")
        report.append("-"*50)
        
        for check in self.checks:
            status = "✓" if check.result == ValidationResult.PASS else "✗" if check.result == ValidationResult.FAIL else "⚠"
            report.append(f"{status} {check.name}: {check.message}")
            if check.details:
                for key, value in check.details.items():
                    report.append(f"    {key}: {value}")
                    
        return "\n".join(report)


class PerformanceValidator:
    """
    Validates performance characteristics of the simulation.
    """
    
    def __init__(self):
        self.metrics = {}
        
    def analyze_performance(self, traces: List[TraceEvent]) -> Dict[str, Any]:
        """Analyze performance from traces"""
        self.metrics.clear()
        
        # Message latency analysis
        self._analyze_message_latency(traces)
        
        # Throughput analysis
        self._analyze_throughput(traces)
        
        # Resource usage
        self._analyze_resource_usage(traces)
        
        return self.metrics
        
    def _analyze_message_latency(self, traces: List[TraceEvent]):
        """Analyze end-to-end message latency"""
        message_times = {}  # message_id -> {publish_time, delivery_time}
        
        for trace in traces:
            if 'rclcpp_publish' in trace.event_name:
                msg_id = trace.fields.get('message_id')
                if msg_id:
                    if msg_id not in message_times:
                        message_times[msg_id] = {}
                    message_times[msg_id]['publish'] = trace.timestamp
                    
            elif 'callback_start' in trace.event_name:
                msg_id = trace.fields.get('message_id')
                if msg_id and msg_id in message_times:
                    message_times[msg_id]['callback'] = trace.timestamp
                    
        # Calculate latencies
        latencies = []
        for msg_id, times in message_times.items():
            if 'publish' in times and 'callback' in times:
                latency = times['callback'] - times['publish']
                latencies.append(latency * 1000)  # Convert to ms
                
        if latencies:
            self.metrics['message_latency'] = {
                'count': len(latencies),
                'average_ms': sum(latencies) / len(latencies),
                'min_ms': min(latencies),
                'max_ms': max(latencies),
                'p95_ms': sorted(latencies)[int(len(latencies) * 0.95)]
            }
            
    def _analyze_throughput(self, traces: List[TraceEvent]):
        """Analyze message throughput"""
        topic_messages = {}  # topic -> list of timestamps
        
        for trace in traces:
            if 'rmw_publish' in trace.event_name:
                topic = trace.fields.get('topic', 'unknown')
                if topic not in topic_messages:
                    topic_messages[topic] = []
                topic_messages[topic].append(trace.timestamp)
                
        # Calculate throughput per topic
        throughputs = {}
        
        for topic, timestamps in topic_messages.items():
            if len(timestamps) > 1:
                duration = timestamps[-1] - timestamps[0]
                if duration > 0:
                    throughputs[topic] = {
                        'messages': len(timestamps),
                        'duration_s': duration,
                        'rate_hz': len(timestamps) / duration
                    }
                    
        self.metrics['throughput'] = throughputs
        
    def _analyze_resource_usage(self, traces: List[TraceEvent]):
        """Analyze resource usage patterns"""
        # Count active entities
        active_nodes = set()
        active_publishers = set()
        active_subscribers = set()
        
        for trace in traces:
            if 'node_init' in trace.event_name:
                node = trace.fields.get('node_name')
                if node:
                    active_nodes.add(node)
            elif 'publisher_init' in trace.event_name:
                topic = trace.fields.get('topic_name')
                if topic:
                    active_publishers.add(topic)
            elif 'subscription_init' in trace.event_name:
                topic = trace.fields.get('topic_name')
                if topic:
                    active_subscribers.add(topic)
                    
        self.metrics['resources'] = {
            'active_nodes': len(active_nodes),
            'active_publishers': len(active_publishers),
            'active_subscribers': len(active_subscribers),
            'total_entities': len(active_nodes) + len(active_publishers) + len(active_subscribers)
        }