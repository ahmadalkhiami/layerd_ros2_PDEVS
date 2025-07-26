"""
QoS policy definitions for ROS2 DEVS simulation.
Implements complete DDS QoS specification.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import time

from core import (
    QoSReliabilityPolicy, QoSDurabilityPolicy, QoSHistoryPolicy,
    QoSLivelinessPolicy, QoSOwnershipPolicy
)


@dataclass
class DeadlineQosPolicy:
    """DDS Deadline QoS Policy"""
    period: float = float('inf')  # seconds
    
    def is_compatible_with(self, other: 'DeadlineQosPolicy') -> bool:
        """Check compatibility (offered <= requested)"""
        return self.period <= other.period


@dataclass
class DestinationOrderQosPolicy:
    """DDS Destination Order QoS Policy"""
    kind: str = "BY_RECEPTION_TIMESTAMP"  # or "BY_SOURCE_TIMESTAMP"


@dataclass
class DurabilityQosPolicy:
    """DDS Durability QoS Policy"""
    kind: QoSDurabilityPolicy = QoSDurabilityPolicy.VOLATILE
    
    def is_compatible_with(self, other: 'DurabilityQosPolicy') -> bool:
        """Check compatibility (offered >= requested)"""
        levels = {
            QoSDurabilityPolicy.VOLATILE: 0,
            QoSDurabilityPolicy.TRANSIENT_LOCAL: 1,
            QoSDurabilityPolicy.TRANSIENT: 2,
            QoSDurabilityPolicy.PERSISTENT: 3
        }
        return levels[self.kind] >= levels[other.kind]


@dataclass
class DurabilityServiceQosPolicy:
    """DDS Durability Service QoS Policy"""
    service_cleanup_delay: float = 0.0  # seconds
    history_kind: QoSHistoryPolicy = QoSHistoryPolicy.KEEP_LAST
    history_depth: int = 1
    max_samples: int = -1
    max_instances: int = -1
    max_samples_per_instance: int = -1


@dataclass
class EntityFactoryQosPolicy:
    """DDS Entity Factory QoS Policy"""
    autoenable_created_entities: bool = True


@dataclass
class GroupDataQosPolicy:
    """DDS Group Data QoS Policy"""
    value: bytes = b""


@dataclass
class HistoryQosPolicy:
    """DDS History QoS Policy"""
    kind: QoSHistoryPolicy = QoSHistoryPolicy.KEEP_LAST
    depth: int = 10
    
    def is_compatible_with(self, other: 'HistoryQosPolicy') -> bool:
        """Check compatibility"""
        if self.kind == QoSHistoryPolicy.KEEP_ALL and other.kind != QoSHistoryPolicy.KEEP_ALL:
            return False
        if self.kind == QoSHistoryPolicy.KEEP_LAST and other.kind == QoSHistoryPolicy.KEEP_LAST:
            return self.depth >= other.depth
        return True


@dataclass
class LatencyBudgetQosPolicy:
    """DDS Latency Budget QoS Policy"""
    duration: float = 0.0  # seconds


@dataclass
class LifespanQosPolicy:
    """DDS Lifespan QoS Policy"""
    duration: float = float('inf')  # seconds
    
    def is_compatible_with(self, other: 'LifespanQosPolicy') -> bool:
        """Check compatibility (offered >= requested)"""
        return self.duration >= other.duration


@dataclass
class LivelinessQosPolicy:
    """DDS Liveliness QoS Policy"""
    kind: QoSLivelinessPolicy = QoSLivelinessPolicy.AUTOMATIC
    lease_duration: float = float('inf')  # seconds
    
    def is_compatible_with(self, other: 'LivelinessQosPolicy') -> bool:
        """Check compatibility"""
        levels = {
            QoSLivelinessPolicy.AUTOMATIC: 0,
            QoSLivelinessPolicy.MANUAL_BY_TOPIC: 1,
            QoSLivelinessPolicy.MANUAL_BY_PARTICIPANT: 2
        }
        if levels[self.kind] < levels[other.kind]:
            return False
        return self.lease_duration <= other.lease_duration


@dataclass
class OwnershipQosPolicy:
    """DDS Ownership QoS Policy"""
    kind: QoSOwnershipPolicy = QoSOwnershipPolicy.SHARED
    
    def is_compatible_with(self, other: 'OwnershipQosPolicy') -> bool:
        """Check compatibility (must match exactly)"""
        return self.kind == other.kind


@dataclass
class OwnershipStrengthQosPolicy:
    """DDS Ownership Strength QoS Policy"""
    value: int = 0


@dataclass
class PartitionQosPolicy:
    """DDS Partition QoS Policy"""
    name: List[str] = None
    
    def __post_init__(self):
        if self.name is None:
            self.name = []
            
    def matches(self, other: 'PartitionQosPolicy') -> bool:
        """Check if partitions match (with wildcards)"""
        if not self.name and not other.name:
            return True
        
        for my_partition in self.name:
            for other_partition in other.name:
                if self._partition_matches(my_partition, other_partition):
                    return True
        return False
        
    def _partition_matches(self, pattern: str, name: str) -> bool:
        """Check if partition name matches pattern (supports * wildcard)"""
        if '*' not in pattern:
            return pattern == name
            
        # Simple wildcard matching
        parts = pattern.split('*')
        if not name.startswith(parts[0]):
            return False
        if not name.endswith(parts[-1]):
            return False
        return True


@dataclass
class PresentationQosPolicy:
    """DDS Presentation QoS Policy"""
    access_scope: str = "INSTANCE_PRESENTATION_QOS"  # TOPIC, GROUP
    coherent_access: bool = False
    ordered_access: bool = False


@dataclass
class ReaderDataLifecycleQosPolicy:
    """DDS Reader Data Lifecycle QoS Policy"""
    autopurge_nowriter_samples_delay: float = float('inf')
    autopurge_disposed_samples_delay: float = float('inf')


@dataclass
class ReliabilityQosPolicy:
    """DDS Reliability QoS Policy"""
    kind: QoSReliabilityPolicy = QoSReliabilityPolicy.RELIABLE
    max_blocking_time: float = 0.1  # seconds
    
    def is_compatible_with(self, other: 'ReliabilityQosPolicy') -> bool:
        """Check compatibility (offered >= requested)"""
        if other.kind == QoSReliabilityPolicy.RELIABLE and self.kind == QoSReliabilityPolicy.BEST_EFFORT:
            return False
        return True


@dataclass
class ResourceLimitsQosPolicy:
    """DDS Resource Limits QoS Policy"""
    max_samples: int = 5000
    max_instances: int = 5000
    max_samples_per_instance: int = 5000


@dataclass
class TimeBasedFilterQosPolicy:
    """DDS Time Based Filter QoS Policy"""
    minimum_separation: float = 0.0  # seconds


@dataclass
class TopicDataQosPolicy:
    """DDS Topic Data QoS Policy"""
    value: bytes = b""


@dataclass
class TransportPriorityQosPolicy:
    """DDS Transport Priority QoS Policy"""
    value: int = 0


@dataclass
class UserDataQosPolicy:
    """DDS User Data QoS Policy"""
    value: bytes = b""


@dataclass
class WriterDataLifecycleQosPolicy:
    """DDS Writer Data Lifecycle QoS Policy"""
    autodispose_unregistered_instances: bool = True
