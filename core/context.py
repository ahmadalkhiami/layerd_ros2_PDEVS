"""
Execution context management for ROS2 components.
Handles thread contexts, process mapping, and CPU affinity.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Set, List, Any
import threading
import os
import random


@dataclass(frozen=True)  # Make the dataclass immutable and hashable
class ExecutionContext:
    """Execution context for a ROS2 component"""
    thread_id: int
    process_name: str
    process_id: int
    cpu_id: int
    component_name: str
    numa_node: int = 0
    priority: int = 20  # Linux nice value
    
    def __str__(self) -> str:
        return (f"Context(tid={self.thread_id}, pid={self.process_id}, "
                f"cpu={self.cpu_id}, component={self.component_name})")


class ContextManager:
    """Manages execution contexts with proper thread safety"""
    
    def __init__(self, num_cpus: int = 4):
        self._lock = threading.Lock()
        self._contexts: Dict[str, ExecutionContext] = {}
        self._thread_counter = 1000
        self._process_counter = 5000
        self._cpu_affinity_map: Dict[int, Set[str]] = {i: set() for i in range(num_cpus)}
        self._num_cpus = num_cpus
        
        # Process hierarchy tracking
        self._process_tree: Dict[int, Set[int]] = {}  # parent_pid -> child_pids
        self._component_processes: Dict[str, int] = {}  # component_type -> pid
        
    def create_process_context(self, process_name: str, 
                             parent_pid: Optional[int] = None) -> int:
        """Create a new process context"""
        with self._lock:
            pid = self._next_process_id()
            
            if parent_pid and parent_pid in self._process_tree:
                self._process_tree[parent_pid].add(pid)
            else:
                self._process_tree[pid] = set()
            
            return pid
    
    def register_component(self, component_name: str, 
                          component_type: str,
                          process_name: Optional[str] = None,
                          cpu_affinity: Optional[List[int]] = None,
                          inherit_from: Optional[str] = None) -> ExecutionContext:
        """Register a component with smart context assignment"""
        with self._lock:
            # Determine process context
            if inherit_from and inherit_from in self._contexts:
                parent_ctx = self._contexts[inherit_from]
                pid = parent_ctx.process_id
                proc_name = parent_ctx.process_name
            elif process_name:
                proc_name = process_name
                if component_type in self._component_processes:
                    pid = self._component_processes[component_type]
                else:
                    pid = self._next_process_id()
                    self._component_processes[component_type] = pid
            else:
                proc_name = f"{component_type}_process"
                pid = self._next_process_id()
            
            # CPU assignment with load balancing
            if cpu_affinity:
                cpu_id = self._select_cpu_from_affinity(cpu_affinity)
            else:
                cpu_id = self._select_least_loaded_cpu()
            
            # Create context
            context = ExecutionContext(
                thread_id=self._next_thread_id(),
                process_name=proc_name,
                process_id=pid,
                cpu_id=cpu_id,
                component_name=component_name,
                numa_node=cpu_id // (self._num_cpus // 2)  # Simple NUMA mapping
            )
            
            self._contexts[component_name] = context
            self._cpu_affinity_map[cpu_id].add(component_name)
            
            return context
    
    def get_context(self, component_name: str) -> Optional[ExecutionContext]:
        """Get context for a component"""
        with self._lock:
            return self._contexts.get(component_name)
    
    def migrate_component(self, component_name: str, new_cpu_id: int):
        """Migrate component to different CPU"""
        with self._lock:
            if component_name in self._contexts:
                context = self._contexts[component_name]
                old_cpu = context.cpu_id
                
                # Update CPU affinity map
                self._cpu_affinity_map[old_cpu].discard(component_name)
                self._cpu_affinity_map[new_cpu_id].add(component_name)
                
                # Update context
                context.cpu_id = new_cpu_id
                context.numa_node = new_cpu_id // (self._num_cpus // 2)
    
    def get_cpu_load(self, cpu_id: int) -> int:
        """Get number of components on a CPU"""
        with self._lock:
            return len(self._cpu_affinity_map.get(cpu_id, set()))
    
    def get_process_tree(self) -> Dict[int, Set[int]]:
        """Get process hierarchy"""
        with self._lock:
            return self._process_tree.copy()
    
    def _next_thread_id(self) -> int:
        """Generate next thread ID"""
        tid = self._thread_counter
        self._thread_counter += 1
        return tid
    
    def _next_process_id(self) -> int:
        """Generate next process ID"""
        pid = self._process_counter
        self._process_counter += 1
        return pid
    
    def _select_least_loaded_cpu(self) -> int:
        """Select CPU with least components"""
        min_load = float('inf')
        selected_cpu = 0
        
        for cpu_id in range(self._num_cpus):
            load = len(self._cpu_affinity_map[cpu_id])
            if load < min_load:
                min_load = load
                selected_cpu = cpu_id
        
        return selected_cpu
    
    def _select_cpu_from_affinity(self, affinity: List[int]) -> int:
        """Select CPU from affinity list based on load"""
        loads = [(cpu, len(self._cpu_affinity_map[cpu])) 
                 for cpu in affinity if cpu < self._num_cpus]
        
        if not loads:
            return self._select_least_loaded_cpu()
        
        # Select CPU with minimum load from affinity list
        return min(loads, key=lambda x: x[1])[0]
    
    def create_node_context(self, node_name: str) -> str:
        """Convenience method for node registration"""
        ctx = self.register_component(
            component_name=f"node_{node_name}",
            component_type="node",
            process_name=node_name
        )
        return f"node_{node_name}"
    
    def create_executor_context(self, executor_name: str, 
                              num_threads: int = 1) -> List[str]:
        """Create contexts for executor threads"""
        contexts = []
        
        # Create main executor context
        main_ctx = self.register_component(
            component_name=f"executor_{executor_name}",
            component_type="executor",
            process_name=f"{executor_name}_executor"
        )
        contexts.append(f"executor_{executor_name}")
        
        # Create worker thread contexts
        for i in range(num_threads - 1):
            worker_ctx = self.register_component(
                component_name=f"executor_{executor_name}_worker_{i}",
                component_type="executor_worker",
                inherit_from=f"executor_{executor_name}"
            )
            contexts.append(f"executor_{executor_name}_worker_{i}")
        
        return contexts
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get context manager statistics"""
        with self._lock:
            return {
                'total_contexts': len(self._contexts),
                'total_processes': len(self._component_processes),
                'cpu_distribution': {
                    cpu: len(components) 
                    for cpu, components in self._cpu_affinity_map.items()
                },
                'process_types': list(self._component_processes.keys())
            }


# Global context manager instance
context_manager = ContextManager(num_cpus=os.cpu_count() or 4)
