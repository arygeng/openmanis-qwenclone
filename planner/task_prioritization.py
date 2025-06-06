"""
Task prioritization framework for Manus AI Clone
Implements advanced task scheduling and priority rules
"""

import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, List, Optional, Union, Callable

from core.event_processor import EventType
from .task_planner import TaskPlanner # Import TaskPlanner from local module
from .plan_types import ExecutionPlan, ExecutionStep, TaskPriority, PlanStatus # Import types from new module

class PriorityRuleType(Enum):
    """Types of priority rules"""
    STATIC = "static"
    DYNAMIC = "dynamic"
    CONTEXTUAL = "contextual"
    TIME_BASED = "time_based"


class PriorityRule:
    """
    Base class for priority rules
    """
    def __init__(self, 
                 rule_id: str,
                 description: str,
                 priority: TaskPriority,
                 rule_type: PriorityRuleType):
        self.rule_id = rule_id
        self.description = description
        self.priority = priority
        self.rule_type = rule_type
        self.created_at = datetime.now().isoformat()
        self.last_modified = self.created_at

    def apply(self, plan: ExecutionPlan) -> ExecutionPlan:
        """
        Apply the priority rule to an execution plan
        
        Args:
            plan: Execution plan to modify
            
        Returns:
            Modified execution plan with updated priorities
        """
        # Should be implemented by subclasses
        return plan

    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary representation"""
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "priority": self.priority.value,
            "rule_type": self.rule_type.value,
            "created_at": self.created_at,
            "last_modified": self.last_modified
        }


class StaticPriorityRule(PriorityRule):
    """
    Static priority rule that applies fixed priorities
    """
    def __init__(self, 
                 rule_id: str,
                 description: str,
                 priority: TaskPriority,
                 step_ids: List[str]):
        super().__init__(rule_id, description, priority, PriorityRuleType.STATIC)
        self.step_ids = step_ids

    def apply(self, plan: ExecutionPlan) -> ExecutionPlan:
        """
        Apply static priority to specific steps
        
        Args:
            plan: Execution plan to modify
            
        Returns:
            Modified execution plan with updated priorities
        """
        # Create a new plan to avoid modifying original
        new_plan = ExecutionPlan(
            task_description=plan.task_description,
            metadata=plan.metadata
        )
        
        # Copy all steps but update priority for matching IDs
        for step in plan.steps:
            if step.step_id in self.step_ids:
                new_step = ExecutionStep(
                    step_id=step.step_id,
                    description=step.description,
                    tool_name=step.tool_name,
                    parameters=step.parameters,
                    priority=self.priority
                )
                new_step.status = step.status
                new_step.start_time = step.start_time
                new_step.end_time = step.end_time
                new_plan.add_step(new_step)
            else:
                new_plan.add_step(step)
                
        return new_plan

    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary representation"""
        data = super().to_dict()
        data["step_ids"] = self.step_ids
        return data


class TimeBasedPriorityRule(PriorityRule):
    """
    Priority rule that applies time-based adjustments
    """
    def __init__(self, 
                 rule_id: str,
                 description: str,
                 base_priority: TaskPriority,
                 start_time: str,
                 end_time: str):
        super().__init__(rule_id, description, base_priority, PriorityRuleType.TIME_BASED)
        self.start_time = start_time  # Format: "HH:MM"
        self.end_time = end_time    # Format: "HH:MM"

    def apply(self, plan: ExecutionPlan) -> ExecutionPlan:
        """
        Apply time-based priority adjustment
        
        Args:
            plan: Execution plan to modify
            
        Returns:
            Modified execution plan with updated priorities
        """
        # Get current time
        current_hour = datetime.now().hour
        current_minute = datetime.now().minute
        current_time = current_hour * 60 + current_minute
        
        # Parse rule times
        start_hour, start_minute = map(int, self.start_time.split(":"))
        end_hour, end_minute = map(int, self.end_time.split(":"))
        
        start_total = start_hour * 60 + start_minute
        end_total = end_hour * 60 + end_minute
        
        # Check if current time is within range
        is_active = False
        if start_total <= end_total:
            is_active = start_total <= current_time <= end_total
        else:  # Handle overnight ranges
            is_active = current_time >= start_total or current_time <= end_total
            
        # If not active, return plan unchanged
        if not is_active:
            return plan
            
        # Create a new plan with adjusted priorities
        new_plan = ExecutionPlan(
            task_description=plan.task_description,
            metadata=plan.metadata
        )
        
        # Adjust priority for all steps
        for step in plan.steps:
            new_step = ExecutionStep(
                step_id=step.step_id,
                description=step.description,
                tool_name=step.tool_name,
                parameters=step.parameters,
                priority=self.priority
            )
            new_step.status = step.status
            new_step.start_time = step.start_time
            new_step.end_time = step.end_time
            new_plan.add_step(new_step)
            
        return new_plan

    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary representation"""
        data = super().to_dict()
        data["start_time"] = self.start_time
        data["end_time"] = self.end_time
        return data


class ContextualPriorityRule(PriorityRule):
    """
    Priority rule that applies context-based adjustments
    """
    def __init__(self, 
                 rule_id: str,
                 description: str,
                 priority: TaskPriority,
                 context_matcher: Dict[str, Any]):
        super().__init__(rule_id, description, priority, PriorityRuleType.CONTEXTUAL)
        self.context_matcher = context_matcher

    def apply(self, plan: ExecutionPlan) -> ExecutionPlan:
        """
        Apply priority based on plan context
        
        Args:
            plan: Execution plan to modify
            
        Returns:
            Modified execution plan with updated priorities
        """
        # Check if plan context matches our matcher
        if not self._context_matches(plan):
            return plan
            
        # Create a new plan with adjusted priorities
        new_plan = ExecutionPlan(
            task_description=plan.task_description,
            metadata=plan.metadata
        )
        
        # Adjust priority for all steps
        for step in plan.steps:
            new_step = ExecutionStep(
                step_id=step.step_id,
                description=step.description,
                tool_name=step.tool_name,
                parameters=step.parameters,
                priority=self.priority
            )
            new_step.status = step.status
            new_step.start_time = step.start_time
            new_step.end_time = step.end_time
            new_plan.add_step(new_step)
            
        return new_plan

    def _context_matches(self, plan: ExecutionPlan) -> bool:
        """
        Check if plan context matches our criteria
        
        Args:
            plan: Plan to check
            
        Returns:
            True if context matches
        """
        # No context means no match
        if not plan.metadata:
            return False
            
        # Empty matcher means always match
        if not self.context_matcher:
            return True
            
        # Check each key in our matcher
        for key, value in self.context_matcher.items():
            if not hasattr(plan.metadata, key):
                return False
                
            if getattr(plan.metadata, key) != value:
                return False
                
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary representation"""
        data = super().to_dict()
        data["context_matcher"] = self.context_matcher
        return data


class DynamicPriorityRule(PriorityRule):
    """
    Priority rule that uses dynamic evaluation function
    """
    def __init__(self, 
                 rule_id: str,
                 description: str,
                 priority: TaskPriority,
                 evaluator: Callable[[ExecutionPlan], bool]):
        super().__init__(rule_id, description, priority, PriorityRuleType.DYNAMIC)
        self.evaluator = evaluator
        
        # Store evaluator as string (would need serialization in real use)
        try:
            self.evaluator_str = evaluator.__doc__ or "lambda plan: False"
        except Exception:
            self.evaluator_str = "lambda plan: False"

    def apply(self, plan: ExecutionPlan) -> ExecutionPlan:
        """
        Apply priority based on dynamic evaluation
        
        Args:
            plan: Execution plan to modify
            
        Returns:
            Modified execution plan with updated priorities
        """
        # Check if plan should have priority applied
        if not self.evaluator(plan):
            return plan
            
        # Create a new plan with adjusted priorities
        new_plan = ExecutionPlan(
            task_description=plan.task_description,
            metadata=plan.metadata
        )
        
        # Adjust priority for all steps
        for step in plan.steps:
            new_step = ExecutionStep(
                step_id=step.step_id,
                description=step.description,
                tool_name=step.tool_name,
                parameters=step.parameters,
                priority=self.priority
            )
            new_step.status = step.status
            new_step.start_time = step.start_time
            new_step.end_time = step.end_time
            new_plan.add_step(new_step)
            
        return new_plan

    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary representation"""
        data = super().to_dict()
        data["evaluator"] = self.evaluator_str
        return data


class PriorityOptimizer:
    """
    Optimizes plan priorities using multiple strategies
    """
    def __init__(self):
        self.rules = {}
        self.default_strategy = "simple_weighted"
        
        # Priority weights for different factors
        self.weights = {
            "urgency": 0.4,
            "complexity": 0.3,
            "dependencies": 0.2,
            "resource_availability": 0.1
        }

    def optimize_plan(self, 
                     plan: ExecutionPlan,
                     strategy: str = "") -> ExecutionPlan:
        """
        Optimize plan priorities using specified strategy
        
        Args:
            plan: Execution plan to optimize
            strategy: Optimization strategy to use
            
        Returns:
            Optimized execution plan
        """
        strategy = strategy or self.default_strategy
        
        if strategy == "simple_weighted":
            return self._optimize_simple_weighted(plan)
        elif strategy == "dependency_aware":
            return self._optimize_dependency_aware(plan)
        elif strategy == "resource_optimized":
            return self._optimize_resource_aware(plan)
        else:
            return plan

    def _optimize_simple_weighted(self, plan: ExecutionPlan) -> ExecutionPlan:
        """
        Optimize plan using simple weighted average of factors
        
        Args:
            plan: Execution plan to optimize
            
        Returns:
            Optimized execution plan
        """
        # Calculate scores for each step
        scores = [self._calculate_score(step) for step in plan.steps]
        
        # Sort steps by score (higher first)
        scored_steps = sorted(zip(scores, plan.steps), key=lambda x: x[0], reverse=True)
        
        # Create new plan with optimized order
        new_plan = ExecutionPlan(
            task_description=plan.task_description,
            metadata=plan.metadata
        )
        
        # Add steps in new order
        for _, step in scored_steps:
            new_plan.add_step(step)
            
        return new_plan

    def _calculate_score(self, step: ExecutionStep) -> float:
        """
        Calculate optimization score for a step
        
        Args:
            step: Step to evaluate
            
        Returns:
            Score between 0 and 1 (higher is more important)
        """
        # This would be enhanced with actual logic
        # For now, just return a basic score
        return 0.5

    def _optimize_dependency_aware(self, plan: ExecutionPlan) -> ExecutionPlan:
        """
        Optimize plan considering dependencies between steps
        
        Args:
            plan: Execution plan to optimize
            
        Returns:
            Optimized execution plan
        """
        # In real implementation, would analyze dependencies
        # For now, just return original plan
        return plan

    def _optimize_resource_aware(self, plan: ExecutionPlan) -> ExecutionPlan:
        """
        Optimize plan considering resource availability
        
        Args:
            plan: Execution plan to optimize
            
        Returns:
            Optimized execution plan
        """
        # In real implementation, would consider resource usage
        # For now, just return original plan
        return plan

    def add_rule(self, rule: PriorityRule) -> None:
        """
        Add a new priority rule
        
        Args:
            rule: Rule to add
        """
        self.rules[rule.rule_id] = rule

    def remove_rule(self, rule_id: str) -> None:
        """
        Remove a priority rule
        
        Args:
            rule_id: ID of rule to remove
        """
        if rule_id in self.rules:
            del self.rules[rule_id]

    def apply_rules(self, plan: ExecutionPlan) -> ExecutionPlan:
        """
        Apply all priority rules to a plan
        
        Args:
            plan: Execution plan to modify
            
        Returns:
            Modified execution plan with all rules applied
        """
        current_plan = plan
        
        # Apply each rule in sequence
        for rule in self.rules.values():
            current_plan = rule.apply(current_plan)
            
        return current_plan

    def set_weights(self, weights: Dict[str, float]) -> None:
        """
        Set weights for optimization factors
        
        Args:
            weights: Dictionary of factor weights
        """
        self.weights.update(weights)


class TaskPrioritizer(TaskPlanner):
    """
    Enhanced task planner with advanced prioritization capabilities
    """
    def __init__(self):
        super().__init__()
        
        # Priority optimizer
        self.optimizer = PriorityOptimizer()
        
        # Default strategy
        self.default_strategy = "simple_weighted"

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
        # Create basic plan with parent class
        plan = super().create_plan(task_description, source, context)
        
        # Optimize plan priorities
        optimized_plan = self.optimizer.optimize_plan(plan, self.default_strategy)
        
        # Apply priority rules
        final_plan = self.optimizer.apply_rules(optimized_plan)
        
        return final_plan

    def add_static_priority_rule(self, 
                              description: str,
                              priority: TaskPriority,
                              step_ids: List[str]) -> str:
        """
        Add a static priority rule
        
        Args:
            description: Rule description
            priority: Priority level
            step_ids: Steps to apply to
            
        Returns:
            ID of new rule
        """
        rule_id = str(uuid.uuid4())
        rule = StaticPriorityRule(
            rule_id=rule_id,
            description=description,
            priority=priority,
            step_ids=step_ids
        )
        self.optimizer.add_rule(rule)
        return rule_id

    def add_time_based_priority_rule(self, 
                                   description: str,
                                   priority: TaskPriority,
                                   start_time: str,
                                   end_time: str) -> str:
        """
        Add a time-based priority rule
        
        Args:
            description: Rule description
            priority: Priority level
            start_time: Start time (HH:MM format)
            end_time: End time (HH:MM format)
            
        Returns:
            ID of new rule
        """
        rule_id = str(uuid.uuid4())
        rule = TimeBasedPriorityRule(
            rule_id=rule_id,
            description=description,
            priority=priority,
            start_time=start_time,
            end_time=end_time
        )
        self.optimizer.add_rule(rule)
        return rule_id

    def add_contextual_priority_rule(self, 
                                   description: str,
                                   priority: TaskPriority,
                                   context_matcher: Dict[str, Any]) -> str:
        """
        Add a contextual priority rule
        
        Args:
            description: Rule description
            priority: Priority level
            context_matcher: Dictionary of context requirements
            
        Returns:
            ID of new rule
        """
        rule_id = str(uuid.uuid4())
        rule = ContextualPriorityRule(
            rule_id=rule_id,
            description=description,
            priority=priority,
            context_matcher=context_matcher
        )
        self.optimizer.add_rule(rule)
        return rule_id

    def add_dynamic_priority_rule(self, 
                               description: str,
                               priority: TaskPriority,
                               evaluator: Callable[[ExecutionPlan], bool]) -> str:
        """
        Add a dynamic priority rule
        
        Args:
            description: Rule description
            priority: Priority level
            evaluator: Function to determine application
            
        Returns:
            ID of new rule
        """
        rule_id = str(uuid.uuid4())
        rule = DynamicPriorityRule(
            rule_id=rule_id,
            description=description,
            priority=priority,
            evaluator=evaluator
        )
        self.optimizer.add_rule(rule)
        return rule_id

    def get_optimizer_status(self) -> Dict[str, Any]:
        """Get status of the priority optimizer"""
        return {
            "rule_count": len(self.optimizer.rules),
            "strategies": ["simple_weighted", "dependency_aware", "resource_optimized"],
            "default_strategy": self.default_strategy,
            "weights": self.optimizer.weights
        }