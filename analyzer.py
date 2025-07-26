"""
Result analysis for ROS2 DEVS simulation.
"""

from typing import List, Dict, Any, Tuple
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict
import pandas as pd

from core import TraceEvent, trace_logger


class SimulationAnalyzer:
    """
    Analyzes simulation results and generates reports.
    """
    
    def __init__(self):
        self.traces = []
        self.statistics = {}
        
    def load_traces(self, traces: List[TraceEvent]):
        """Load traces for analysis"""
        self.traces = traces
        self._compute_statistics()
        
    def _compute_statistics(self):
        """Compute basic statistics from traces"""
        self.statistics = {
            'total_events': len(self.traces),
            'duration': self.traces[-1].timestamp if self.traces else 0,
            'event_types': defaultdict(int),
            'nodes': set(),
            'topics': set()
        }
        
        for trace in self.traces:
            self.statistics['event_types'][trace.event_name] += 1
            
            # Extract nodes
            if 'node_name' in trace.fields:
                self.statistics['nodes'].add(trace.fields['node_name'])
            elif 'node' in trace.fields:
                self.statistics['nodes'].add(trace.fields['node'])
                
            # Extract topics
            if 'topic_name' in trace.fields:
                self.statistics['topics'].add(trace.fields['topic_name'])
            elif 'topic' in trace.fields:
                self.statistics['topics'].add(trace.fields['topic'])
                
    def generate_summary(self) -> str:
        """Generate summary report"""
        report = ["ROS2 DEVS Simulation Analysis", "="*50, ""]
        
        # Basic statistics
        report.append(f"Total Events: {self.statistics['total_events']}")
        report.append(f"Simulation Duration: {self.statistics['duration']:.3f} seconds")
        report.append(f"Active Nodes: {len(self.statistics['nodes'])}")
        report.append(f"Active Topics: {len(self.statistics['topics'])}")
        report.append("")
        
        # Event type distribution
        report.append("Event Type Distribution:")
        report.append("-"*30)
        
        sorted_events = sorted(self.statistics['event_types'].items(), 
                             key=lambda x: x[1], reverse=True)
        
        for event_type, count in sorted_events[:10]:  # Top 10 events
            percentage = (count / self.statistics['total_events']) * 100
            report.append(f"  {event_type}: {count} ({percentage:.1f}%)")
            
        # Message flow analysis
        message_stats = self._analyze_message_flow()
        if message_stats:
            report.append("")
            report.append("Message Flow Statistics:")
            report.append("-"*30)
            report.append(f"  Total Messages Published: {message_stats['published']}")
            report.append(f"  Total Messages Delivered: {message_stats['delivered']}")
            report.append(f"  Delivery Rate: {message_stats['delivery_rate']:.1%}")
            report.append(f"  Average Latency: {message_stats['avg_latency']:.3f}ms")
            
        return "\n".join(report)
        
    def _analyze_message_flow(self) -> Dict[str, Any]:
        """Analyze message flow statistics"""
        published = 0
        delivered = 0
        latencies = []
        
        message_publish_times = {}
        
        for trace in self.traces:
            if 'rclcpp_publish' in trace.event_name:
                msg_id = trace.fields.get('message_id')
                if msg_id:
                    published += 1
                    message_publish_times[msg_id] = trace.timestamp
                    
            elif 'callback_start' in trace.event_name:
                msg_id = trace.fields.get('message_id')
                if msg_id:
                    delivered += 1
                    if msg_id in message_publish_times:
                        latency = (trace.timestamp - message_publish_times[msg_id]) * 1000
                        latencies.append(latency)
                        
        if published == 0:
            return {}
            
        return {
            'published': published,
            'delivered': delivered,
            'delivery_rate': delivered / published if published > 0 else 0,
            'avg_latency': sum(latencies) / len(latencies) if latencies else 0,
            'max_latency': max(latencies) if latencies else 0,
            'min_latency': min(latencies) if latencies else 0
        }
        
    def plot_event_timeline(self, save_path: str = None):
        """Plot event timeline"""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Group events by type
        event_groups = defaultdict(list)
        for trace in self.traces:
            event_groups[trace.event_name].append(trace.timestamp)
            
        # Plot each event type
        y_pos = 0
        colors = plt.cm.tab20(np.linspace(0, 1, len(event_groups)))
        
        for (event_type, timestamps), color in zip(event_groups.items(), colors):
            ax.scatter(timestamps, [y_pos] * len(timestamps), 
                      label=event_type, s=10, alpha=0.6, color=color)
            y_pos += 1
            
        ax.set_xlabel('Time (seconds)')
        ax.set_yticks(range(len(event_groups)))
        ax.set_yticklabels(list(event_groups.keys()))
        ax.set_title('ROS2 Event Timeline')
        ax.grid(True, alpha=0.3)
        
        # Add legend if not too many event types
        if len(event_groups) <= 10:
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()
            
    def plot_message_latency_distribution(self, save_path: str = None):
        """Plot message latency distribution"""
        latencies = []
        
        message_times = {}
        for trace in self.traces:
            if 'rclcpp_publish' in trace.event_name:
                msg_id = trace.fields.get('message_id')
                if msg_id:
                    message_times[msg_id] = trace.timestamp
            elif 'callback_start' in trace.event_name:
                msg_id = trace.fields.get('message_id')
                if msg_id and msg_id in message_times:
                    latency = (trace.timestamp - message_times[msg_id]) * 1000
                    latencies.append(latency)
                    
        if not latencies:
            print("No latency data available")
            return
            
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # Histogram
        ax1.hist(latencies, bins=50, edgecolor='black', alpha=0.7)
        ax1.set_xlabel('Latency (ms)')
        ax1.set_ylabel('Count')
        ax1.set_title('Message Latency Distribution')
        ax1.grid(True, alpha=0.3)
        
        # Add statistics
        stats_text = f"Mean: {np.mean(latencies):.2f}ms\n"
        stats_text += f"Median: {np.median(latencies):.2f}ms\n"
        stats_text += f"95th percentile: {np.percentile(latencies, 95):.2f}ms"
        ax1.text(0.7, 0.9, stats_text, transform=ax1.transAxes,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        # CDF
        sorted_latencies = np.sort(latencies)
        cdf = np.arange(1, len(sorted_latencies) + 1) / len(sorted_latencies)
        ax2.plot(sorted_latencies, cdf, linewidth=2)
        ax2.set_xlabel('Latency (ms)')
        ax2.set_ylabel('CDF')
        ax2.set_title('Cumulative Distribution')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()
            
    def plot_throughput_over_time(self, window_size: float = 1.0, save_path: str = None):
        """Plot message throughput over time"""
        # Collect publish events by topic
        topic_publishes = defaultdict(list)
        
        for trace in self.traces:
            if 'rmw_publish' in trace.event_name:
                topic = trace.fields.get('topic', 'unknown')
                topic_publishes[topic].append(trace.timestamp)
                
        if not topic_publishes:
            print("No publish data available")
            return
            
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Calculate throughput for each topic
        for topic, timestamps in topic_publishes.items():
            if len(timestamps) < 2:
                continue
                
            timestamps = sorted(timestamps)
            
            # Calculate throughput in sliding windows
            window_starts = np.arange(0, timestamps[-1], window_size/2)
            throughputs = []
            window_centers = []
            
            for start in window_starts:
                end = start + window_size
                count = sum(1 for t in timestamps if start <= t < end)
                if count > 0:
                    throughputs.append(count / window_size)
                    window_centers.append(start + window_size/2)
                    
            ax.plot(window_centers, throughputs, label=topic, linewidth=2)
            
        ax.set_xlabel('Time (seconds)')
        ax.set_ylabel('Messages/second')
        ax.set_title(f'Message Throughput Over Time (window={window_size}s)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()
            
    def export_to_csv(self, filepath: str):
        """Export traces to CSV for external analysis"""
        data = []
        
        for trace in self.traces:
            row = {
                'timestamp': trace.timestamp,
                'event_name': trace.event_name,
                'cpu_id': trace.context.cpu_id,
                'thread_id': trace.context.thread_id,
                'process_id': trace.context.process_id,
                'component': trace.context.component_name
            }
            
            # Add fields
            for key, value in trace.fields.items():
                row[f'field_{key}'] = str(value)
                
            data.append(row)
            
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)
        print(f"Exported {len(data)} events to {filepath}")
        
    def compare_with_reference(self, reference_traces: List[TraceEvent]) -> Dict[str, Any]:
        """Compare simulation traces with reference traces"""
        comparison = {
            'event_count_diff': len(self.traces) - len(reference_traces),
            'common_events': 0,
            'unique_to_simulation': set(),
            'unique_to_reference': set(),
            'timing_differences': []
        }
        
        # Create event maps
        sim_events = {trace.event_name for trace in self.traces}
        ref_events = {trace.event_name for trace in reference_traces}
        
        comparison['common_events'] = len(sim_events & ref_events)
        comparison['unique_to_simulation'] = sim_events - ref_events
        comparison['unique_to_reference'] = ref_events - sim_events
        
        return comparison