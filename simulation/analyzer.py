"""
Analysis tools for ROS2 DEVS simulation.
"""

from typing import List, Dict, Any
from pathlib import Path
import json

class SimulationAnalyzer:
    """Analyzes simulation results and generates reports"""
    
    def __init__(self):
        self.traces = []
        self.results = {}
        
    def analyze(self, traces: List[Dict]):
        """Analyze simulation traces"""
        self.traces = traces
        
        # Analyze node behavior
        self._analyze_nodes()
        
        # Analyze message patterns
        self._analyze_messages()
        
        # Analyze timing
        self._analyze_timing()
        
    def _analyze_nodes(self):
        """Analyze node behavior and interactions"""
        # Track nodes and their activities
        nodes = {}
        
        for event in self.traces:
            if "node_name" in event:
                node_name = event["node_name"]
                if node_name not in nodes:
                    nodes[node_name] = {
                        "publishers": set(),
                        "subscribers": set(),
                        "services": set(),
                        "parameters": set()
                    }
                    
                # Track node activities
                if "topic" in event:
                    if "publish" in event.get("event", ""):
                        nodes[node_name]["publishers"].add(event["topic"])
                    elif "subscription" in event.get("event", ""):
                        nodes[node_name]["subscribers"].add(event["topic"])
                        
                if "service_name" in event:
                    nodes[node_name]["services"].add(event["service_name"])
                    
                if "parameter" in event:
                    nodes[node_name]["parameters"].add(event["parameter"])
                    
        self.results["nodes"] = {
            name: {
                "publishers": list(info["publishers"]),
                "subscribers": list(info["subscribers"]),
                "services": list(info["services"]),
                "parameters": list(info["parameters"])
            }
            for name, info in nodes.items()
        }
        
    def _analyze_messages(self):
        """Analyze message flow patterns"""
        # Track messages by topic
        topics = {}
        
        for event in self.traces:
            if "topic" in event:
                topic = event["topic"]
                if topic not in topics:
                    topics[topic] = {
                        "publish_count": 0,
                        "subscribe_count": 0,
                        "publishers": set(),
                        "subscribers": set()
                    }
                    
                # Count messages
                if "publish" in event.get("event", ""):
                    topics[topic]["publish_count"] += 1
                    if "node_name" in event:
                        topics[topic]["publishers"].add(event["node_name"])
                        
                elif "subscription" in event.get("event", ""):
                    topics[topic]["subscribe_count"] += 1
                    if "node_name" in event:
                        topics[topic]["subscribers"].add(event["node_name"])
                        
        self.results["topics"] = {
            topic: {
                "publish_count": info["publish_count"],
                "subscribe_count": info["subscribe_count"],
                "publishers": list(info["publishers"]),
                "subscribers": list(info["subscribers"])
            }
            for topic, info in topics.items()
        }
        
    def _analyze_timing(self):
        """Analyze timing patterns"""
        # Track timing information
        timing = {
            "init_duration": 0,
            "total_duration": 0,
            "callback_durations": [],
            "publish_intervals": {}
        }
        
        # Find initialization phase
        init_events = [
            event for event in self.traces
            if "init" in event.get("event", "").lower()
        ]
        if init_events:
            first_init = min(float(event.get("timestamp", 0)) for event in init_events)
            last_init = max(float(event.get("timestamp", 0)) for event in init_events)
            timing["init_duration"] = last_init - first_init
            
        # Calculate total duration
        if self.traces:
            first_event = min(float(event.get("timestamp", 0)) for event in self.traces)
            last_event = max(float(event.get("timestamp", 0)) for event in self.traces)
            timing["total_duration"] = last_event - first_event
            
        # Analyze callback durations
        for i, event in enumerate(self.traces):
            if "callback_start" in event.get("event", ""):
                # Find matching end
                for j in range(i+1, len(self.traces)):
                    if "callback_end" in self.traces[j].get("event", ""):
                        duration = float(self.traces[j].get("timestamp", 0)) - float(event.get("timestamp", 0))
                        timing["callback_durations"].append(duration)
                        break
                        
        # Calculate publish intervals by topic
        for topic in self.results.get("topics", {}):
            publish_times = []
            for event in self.traces:
                if (event.get("topic") == topic and 
                    "publish" in event.get("event", "")):
                    publish_times.append(float(event.get("timestamp", 0)))
                    
            if len(publish_times) > 1:
                intervals = [
                    publish_times[i+1] - publish_times[i]
                    for i in range(len(publish_times)-1)
                ]
                timing["publish_intervals"][topic] = {
                    "min": min(intervals),
                    "max": max(intervals),
                    "avg": sum(intervals) / len(intervals)
                }
                
        self.results["timing"] = timing
        
    def save_results(self, output_dir: str):
        """Save analysis results"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Save full results
        with open(output_path / "analysis.json", "w") as f:
            json.dump(self.results, f, indent=2)
            
        # Save summary
        with open(output_path / "summary.txt", "w") as f:
            f.write(self._generate_summary())