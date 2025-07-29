"""
Action-related messages for ROS2 DEVS simulation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, List
import uuid
import time

from core import Message, MessageType


class GoalStatus(Enum):
    """Action goal status"""
    STATUS_UNKNOWN = 0
    STATUS_ACCEPTED = 1
    STATUS_EXECUTING = 2
    STATUS_CANCELING = 3
    STATUS_SUCCEEDED = 4
    STATUS_CANCELED = 5
    STATUS_ABORTED = 6


@dataclass
class ActionGoal(Message):
    """Action goal message"""
    goal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_type: str = ""
    goal_data: dict = field(default_factory=dict)
    client_node: str = ""
    
    def __post_init__(self):
        super().__init__()
        self.type = MessageType.ACTION_GOAL
        self.timestamp = time.time()


@dataclass
class ActionGoalStatus(Message):
    """Action goal status message"""
    goal_id: str = ""
    status: GoalStatus = GoalStatus.STATUS_UNKNOWN
    
    def __post_init__(self):
        super().__init__()
        self.type = MessageType.DATA


@dataclass
class ActionFeedback(Message):
    """Action feedback message"""
    goal_id: str = ""
    action_type: str = ""
    feedback_data: dict = field(default_factory=dict)
    progress_percent: float = 0.0
    
    def __post_init__(self):
        super().__init__()
        self.type = MessageType.ACTION_FEEDBACK
        self.timestamp = time.time()


@dataclass
class ActionResult(Message):
    """Action result message"""
    goal_id: str = ""
    action_type: str = ""
    status: GoalStatus = GoalStatus.STATUS_UNKNOWN
    result_data: dict = field(default_factory=dict)
    error_message: str = ""
    
    def __post_init__(self):
        super().__init__()
        self.type = MessageType.ACTION_RESULT
        self.timestamp = time.time()


@dataclass
class CancelGoalRequest(Message):
    """Request to cancel an action goal"""
    goal_id: str = ""
    
    def __post_init__(self):
        super().__init__()
        self.type = MessageType.SERVICE_REQUEST


@dataclass
class CancelGoalResponse(Message):
    """Response to cancel goal request"""
    goals_canceling: list = field(default_factory=list)
    
    def __post_init__(self):
        super().__init__()
        self.type = MessageType.SERVICE_RESPONSE


# Example action type definitions

@dataclass
class NavigateToPoseGoal(ActionGoal):
    """Navigate to pose action goal"""
    pose_x: float = 0.0
    pose_y: float = 0.0
    pose_theta: float = 0.0
    max_velocity: float = 1.0
    
    def __post_init__(self):
        super().__init__()
        self.action_type = "NavigateToPose"
        self.goal_data = {
            "pose": {"x": self.pose_x, "y": self.pose_y, "theta": self.pose_theta},
            "max_velocity": self.max_velocity
        }


@dataclass
class NavigateToPoseFeedback(ActionFeedback):
    """Navigate to pose action feedback"""
    current_pose_x: float = 0.0
    current_pose_y: float = 0.0
    distance_remaining: float = 0.0
    estimated_time_remaining: float = 0.0
    
    def __post_init__(self):
        super().__init__()
        self.action_type = "NavigateToPose"
        self.feedback_data = {
            "current_pose": {"x": self.current_pose_x, "y": self.current_pose_y},
            "distance_remaining": self.distance_remaining,
            "estimated_time_remaining": self.estimated_time_remaining
        }
        if self.distance_remaining > 0:
            self.progress_percent = max(0, 100 - self.distance_remaining * 10)


@dataclass
class NavigateToPoseResult(ActionResult):
    """Navigate to pose action result"""
    final_pose_x: float = 0.0
    final_pose_y: float = 0.0
    final_pose_theta: float = 0.0
    total_elapsed_time: float = 0.0
    
    def __post_init__(self):
        super().__init__()
        self.action_type = "NavigateToPose"
        self.result_data = {
            "final_pose": {
                "x": self.final_pose_x,
                "y": self.final_pose_y,
                "theta": self.final_pose_theta
            },
            "total_elapsed_time": self.total_elapsed_time
        }


@dataclass
class GoalStatusMessage(Message):
    """Action goal status message"""
    goal_id: str = ""
    status: GoalStatus = GoalStatus.STATUS_UNKNOWN
    
    def __post_init__(self):
        super().__init__()
        self.type = MessageType.DATA


@dataclass
class GoalStatusArray(Message):
    """Array of goal statuses"""
    status_list: List[GoalStatusMessage] = field(default_factory=list)
    
    def __post_init__(self):
        super().__init__()
        self.type = MessageType.DATA


@dataclass
class SendGoalRequest(Message):
    """Request to send a goal"""
    goal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal: Any = None
    
    def __post_init__(self):
        super().__init__()
        self.type = MessageType.SERVICE_REQUEST


@dataclass
class SendGoalResponse(Message):
    """Response to send goal request"""
    accepted: bool = False
    stamp: float = field(default_factory=time.time)
    
    def __post_init__(self):
        super().__init__()
        self.type = MessageType.SERVICE_RESPONSE


@dataclass
class GetResultRequest(Message):
    """Request to get action result"""
    goal_id: str = ""
    
    def __post_init__(self):
        super().__init__()
        self.type = MessageType.SERVICE_REQUEST


@dataclass
class GetResultResponse(Message):
    """Response with action result"""
    status: GoalStatus = GoalStatus.STATUS_UNKNOWN
    result: Any = None
    
    def __post_init__(self):
        super().__init__()
        self.type = MessageType.SERVICE_RESPONSE


@dataclass
class NavigateToPoseActionGoal(ActionGoal):
    """NavigateToPose action goal"""
    pose_x: float = 0.0
    pose_y: float = 0.0
    pose_theta: float = 0.0
    
    def __post_init__(self):
        super().__init__()
        self.action_type = "NavigateToPose"
        self.goal_data = {
            "pose": {
                "x": self.pose_x,
                "y": self.pose_y,
                "theta": self.pose_theta
            }
        }


@dataclass
class NavigateToPoseActionResult(ActionResult):
    """NavigateToPose action result"""
    final_pose_x: float = 0.0
    final_pose_y: float = 0.0
    final_pose_theta: float = 0.0
    
    def __post_init__(self):
        super().__init__()
        self.action_type = "NavigateToPose"
        self.result_data = {
            "final_pose": {
                "x": self.final_pose_x,
                "y": self.final_pose_y,
                "theta": self.final_pose_theta
            }
        }


@dataclass
class NavigateToPoseActionFeedback(ActionFeedback):
    """NavigateToPose action feedback"""
    current_pose_x: float = 0.0
    current_pose_y: float = 0.0
    distance_remaining: float = 0.0
    
    def __post_init__(self):
        super().__init__()
        self.action_type = "NavigateToPose"
        self.feedback_data = {
            "current_pose": {
                "x": self.current_pose_x,
                "y": self.current_pose_y
            },
            "distance_remaining": self.distance_remaining
        }


@dataclass
class FibonacciActionGoal(ActionGoal):
    """Fibonacci action goal"""
    order: int = 0
    
    def __post_init__(self):
        super().__init__()
        self.action_type = "Fibonacci"
        self.goal_data = {"order": self.order}


@dataclass
class FibonacciActionResult(ActionResult):
    """Fibonacci action result"""
    sequence: List[int] = field(default_factory=list)
    
    def __post_init__(self):
        super().__init__()
        self.action_type = "Fibonacci"
        self.result_data = {"sequence": self.sequence}


@dataclass
class FibonacciActionFeedback(ActionFeedback):
    """Fibonacci action feedback"""
    sequence: List[int] = field(default_factory=list)
    
    def __post_init__(self):
        super().__init__()
        self.action_type = "Fibonacci"
        self.feedback_data = {"sequence": self.sequence}
        self.progress_percent = len(self.sequence) * 100 / self.goal_data.get("order", 1) if self.goal_data else 0
