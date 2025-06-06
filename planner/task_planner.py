"""
Task planning system for Manus AI Clone
Implements plan creation and prioritization framework
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from core.event_processor import EventType
from .plan_types import TaskPriority, PlanStatus, TaskMetadata, ExecutionStep, ExecutionPlan


class TaskPlanner:
    """
    Main task planning system implementing dynamic plan creation
    """
    def __init__(self):
        # Priority rules by event type
        self.priority_rules = {
            EventType.USER_MESSAGE: TaskPriority.MEDIUM,
            EventType.SYSTEM_STATUS: TaskPriority.LOW,
            EventType.ERROR_EVENT: TaskPriority.HIGH
        }
        
        # Active plans registry
        self.active_plans = {}

    def create_plan(self, 
                   task_description: str, 
                   source: str = "manual",
                   context: Optional[Dict[str, Any]] = None) -> ExecutionPlan:
        """
        Create a new execution plan based on task description
        
        Args:
            task_description: Description of task to accomplish
            source: Source of the task (manual, system, etc.)
            context: Additional context for plan creation
            
        Returns:
            Created execution plan
        """
        # Create metadata
        metadata = TaskMetadata(
            created_by=source,
            source_type="user_input" if source == "manual" else "system",
            context_size=len(context) if context else 0,
            estimated_complexity=self._estimate_complexity(task_description)
        )
        
        # Create execution plan
        plan = ExecutionPlan(
            task_description=task_description,
            metadata=metadata
        )
        
        # Generate plan based on context and task
        generated_steps = self._generate_steps(
            task_description, 
            context or {}
        )
        
        # Add steps to plan
        for step in generated_steps:
            plan.add_step(step)
        
        # Register plan
        self.active_plans[plan.plan_id] = plan
        
        return plan

    def _estimate_complexity(self, task_description: str) -> float:
        """
        Estimate complexity of a task based on description
        
        Args:
            task_description: Description of task to analyze
            
        Returns:
            Complexity score between 0 and 1
        """
        # Simple complexity estimation based on length and keywords
        complexity = len(task_description) / 1000
        
        # Add points for complex terms
        complex_keywords = ["analyze", "research", "calculate", "compare"]
        for keyword in complex_keywords:
            if keyword in task_description.lower():
                complexity = min(complexity + 0.2, 1.0)
        
        return max(0.1, complexity)  # Minimum complexity threshold

    def _generate_steps(self, 
                       task_description: str,
                       context: Dict[str, Any]) -> List[ExecutionStep]:
        """
        Generate execution steps based on task description and context
        
        Args:
            task_description: Description of task to break down
            context: Additional context for step generation
            
        Returns:
            List of execution steps
        """
        # This is a placeholder - will be enhanced with actual logic later
        # For now, create a simple default plan
        return [
            ExecutionStep(
                step_id=str(uuid.uuid4()),
                description="Analyze task requirements",
                priority=TaskPriority.MEDIUM
            ),
            ExecutionStep(
                step_id=str(uuid.uuid4()),
                description="Select appropriate tools",
                priority=TaskPriority.MEDIUM
            ),
            ExecutionStep(
                step_id=str(uuid.uuid4()),
                description="Execute selected actions",
                priority=TaskPriority.MEDIUM
            ),
            ExecutionStep(
                step_id=str(uuid.uuid4()),
                description="Submit results to user",
                priority=TaskPriority.MEDIUM
            )
        ]

    def prioritize_tasks(self, 
                        tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prioritize tasks based on defined rules
        
        Args:
            tasks: List of tasks to prioritize
            
        Returns:
            List of tasks in priority order
        """
        # Sort tasks by priority (lower number = higher priority)
        return sorted(
            tasks, 
            key=lambda x: self.priority_rules.get(
                x.get("event_type", EventType.SYSTEM_STATUS), 
                TaskPriority.MEDIUM
            ).value
        )

    def add_priority_rule(self, 
                         event_type: EventType, 
                         priority: TaskPriority) -> None:
        """
        Add a priority rule for specific event types
        
        Args:
            event_type: Type of event to apply rule to
            priority: Priority level (1=highest)
        """
        self.priority_rules[event_type] = priority

    def get_plan_status(self, plan_id: str) -> Dict[str, Any]:
        """
        Get current status of a plan
        
        Args:
            plan_id: Unique identifier for the plan
            
        Returns:
            Status information about the plan
        """
        if plan_id not in self.active_plans:
            raise ValueError(f"Plan {plan_id} not found")
            
        plan = self.active_plans[plan_id]
        completed_steps = sum(1 for step in plan.steps if step.status == PlanStatus.COMPLETED)
        failed_steps = sum(1 for step in plan.steps if step.status == PlanStatus.FAILED)
        
        return {
            "plan_id": plan_id,
            "status": plan.status.value,
            "total_steps": len(plan.steps),
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "completion_percentage": (completed_steps / len(plan.steps)) * 100 if plan.steps else 0,
            "created_at": plan.created_at,
            "updated_at": plan.updated_at
        }