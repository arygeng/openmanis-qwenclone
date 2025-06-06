"""
Defines common types for task planning and execution.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional

class TaskPriority(Enum):
    """Task priority levels"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4

class PlanStatus(Enum):
    """Plan execution status"""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskMetadata:
    """
    Metadata container for task planning
    """
    def __init__(self,
                 created_by: str,
                 source_type: str,
                 context_size: int = 0,
                 estimated_complexity: float = 0.0):
        self.created_by = created_by
        self.source_type = source_type
        self.context_size = context_size
        self.estimated_complexity = estimated_complexity
        self.created_at = datetime.now().isoformat()

class ExecutionStep:
    """
    Represents a single step in an execution plan
    """
    def __init__(self,
                 step_id: str,
                 description: str,
                 tool_name: Optional[str] = None,
                 parameters: Optional[Dict[str, Any]] = None,
                 priority: TaskPriority = TaskPriority.MEDIUM):
        self.step_id = step_id
        self.description = description
        self.tool_name = tool_name
        self.parameters = parameters or {}
        self.priority = priority.value if isinstance(priority, TaskPriority) else priority
        self.status = PlanStatus.PENDING
        self.start_time = None
        self.end_time = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert step to dictionary representation"""
        return {
            "step_id": self.step_id,
            "description": self.description,
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "priority": self.priority,
            "status": self.status.value if isinstance(self.status, PlanStatus) else self.status, # Ensure enum is converted
            "start_time": self.start_time,
            "end_time": self.end_time
        }

class ExecutionPlan:
    """
    Container for execution plans with multiple steps
    """
    def __init__(self,
                 task_description: str,
                 metadata: Optional[TaskMetadata] = None):
        self.plan_id = str(uuid.uuid4())
        self.task_description = task_description
        self.metadata = metadata
        self.steps: List[ExecutionStep] = []
        self.status = PlanStatus.PENDING
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at

    def add_step(self, step: ExecutionStep) -> None:
        """Add a new step to the plan"""
        self.steps.append(step)
        self.updated_at = datetime.now().isoformat()

    def update_step_status(self, step_id: str, status: PlanStatus) -> bool:
        """Update status of a specific step"""
        for step in self.steps:
            if step.step_id == step_id:
                step.status = status # Store as enum
                self.updated_at = datetime.now().isoformat()
                return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert plan to dictionary representation"""
        return {
            "plan_id": self.plan_id,
            "task_description": self.task_description,
            "metadata": self.metadata.__dict__ if self.metadata else None,
            "status": self.status.value if isinstance(self.status, PlanStatus) else self.status, # Ensure enum is converted
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "steps": [step.to_dict() for step in self.steps]
        }