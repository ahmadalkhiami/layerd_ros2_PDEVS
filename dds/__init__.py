"""
DDS (Data Distribution Service) layer for ROS2 DEVS simulation.
Implements DDS domain participants, discovery, transport, and serialization.
"""



from .discovery import (
    ParticipantInfo,
    EndpointInfo,
    DiscoveryMessage,
    DiscoveryDatabase
)

from .transport import (
    TransportType,
    TransportMessage,
    SharedMemoryTransport,
    NetworkTransport,
    TransportMultiplexer,
    TransportRouter
)

from .serialization import (
    CDREncapsulation,
    CDRSerializer,
    TypeRegistry,
    type_registry
)

__all__ = [
    # Participant
    'DDSEntity', 'DataWriter', 'DataReader', 'DDSParticipant',
    
    # Discovery
    'ParticipantInfo', 'EndpointInfo', 'DiscoveryMessage', 'DiscoveryDatabase',
    
    # Transport
    'TransportType', 'TransportMessage', 'SharedMemoryTransport',
    'NetworkTransport', 'TransportMultiplexer', 'TransportRouter',
    
    # Serialization
    'CDREncapsulation', 'CDRSerializer', 'TypeRegistry', 'type_registry'
]