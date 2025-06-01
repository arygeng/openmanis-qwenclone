# Core Engine Implementation for Manus AI Clone
"""
Implements the agentic loop architecture with event stream processing
"""

import asyncio
from typing import Dict, Any, List, Optional
import json
import time

from core.types import AgentState, SecurityException, PermissionLevel
from core.message_router import MessageRouter
from core.event_processor import EventProcessor
from planner.task_planner import TaskPlanner
from knowledge.memory_system import MemorySystem
from tools.tool_interface import ToolAdapter
from tools.manus_tools import manus_tools
from security.permission_validator import PermissionValidator


class AgenticLoop:
    """
    Implements the Manus AI agent loop:
    1. Analyze Events - Understand user needs and current state through event stream
    2. Select Tools - Choose next tool call based on current state, task planning, relevant knowledge
    3. Wait for Execution - Selected tool action executed by sandbox environment
    4. Iterate - Choose only one tool call per iteration, repeat until task completion
    5. Submit Results - Send results to user via message tools
    6. Enter Standby - Enter idle state when all tasks completed
    """
    def __init__(self):
        # Core components
        self.state = AgentState.IDLE
        self.message_router = MessageRouter()
        self.event_processor = EventProcessor()
        self.planner = TaskPlanner()
        self.memory = MemorySystem()
        # Initialize tool interface with default metadata
        from tools.tool_interface import ToolType, ToolMetadata
        default_metadata = ToolMetadata(
            name="Manus AI Tool Interface",
            description="Main tool interface for Manus AI Clone",
            version="1.0.0",
            author="Manus AI Clone",
            license_type="MIT"
        )
        self.tool_interface = ToolAdapter(ToolType.MESSAGE, default_metadata)
        self.security = PermissionValidator()
        
        # Event stream - chronological list of all events
        self.event_stream = []
        
        # Execution context
        self.current_plan = None
        self.execution_history = []
        self.pending_events = []
        self.current_task = None
        
        # Working language (default English)
        self.working_language = "English"

    async def process_event_stream(self, new_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process new event through the complete Manus AI agent loop
        
        Args:
            new_event: New event to add to stream (Message, Action, Observation, Plan, Knowledge, Datasource, etc.)
            
        Returns:
            Tool execution result or status update
        """
        try:
            # Add event to chronological stream
            event_with_timestamp = {
                **new_event,
                'timestamp': time.time(),
                'id': len(self.event_stream)
            }
            self.event_stream.append(event_with_timestamp)
            
            # 1. ANALYZE EVENTS
            self.state = AgentState.PROCESSING
            analysis = await self._analyze_events()
            
            # 2. SELECT TOOLS
            if analysis['requires_action']:
                tool_selection = await self._select_tool(analysis)
                
                # 3. WAIT FOR EXECUTION (execute the selected tool)
                if tool_selection:
                    execution_result = await self._execute_tool(tool_selection)
                    
                    # Add execution result as Observation event
                    observation_event = {
                        'type': 'Observation',
                        'content': execution_result,
                        'related_action': tool_selection,
                        'timestamp': time.time(),
                        'id': len(self.event_stream)
                    }
                    self.event_stream.append(observation_event)
                    
                    # 4. ITERATE - Check if task is complete
                    if self._is_task_complete(execution_result):
                        # 5. SUBMIT RESULTS
                        await self._submit_results()
                        # 6. ENTER STANDBY
                        self.state = AgentState.IDLE
                        return {
                            'status': 'task_complete',
                            'result': execution_result,
                            'message': 'Task completed successfully'
                        }
                    else:
                        # Continue iteration
                        return {
                            'status': 'iteration_complete',
                            'result': execution_result,
                            'next_iteration': True
                        }
                else:
                    # No tool selected, enter standby
                    self.state = AgentState.IDLE
                    return {
                        'status': 'no_action_needed',
                        'message': 'Analysis complete, no action required'
                    }
            else:
                # No action required
                self.state = AgentState.IDLE
                return {
                    'status': 'analysis_complete',
                    'message': 'Event processed, no action required'
                }
                
        except Exception as e:
            self.state = AgentState.ERROR
            error_event = {
                'type': 'Error',
                'content': str(e),
                'timestamp': time.time(),
                'id': len(self.event_stream)
            }
            self.event_stream.append(error_event)
            return {
                'status': 'error',
                'error': str(e),
                'event': new_event
            }

    async def _analyze_events(self) -> Dict[str, Any]:
        """
        Analyze event stream to understand user needs and current state
        Focus on latest user messages and execution results
        """
        # Get recent events (last 10 for context)
        recent_events = self.event_stream[-10:] if len(self.event_stream) > 10 else self.event_stream
        
        # Find latest user message
        latest_user_message = None
        for event in reversed(recent_events):
            if event.get('type') == 'Message' and event.get('source') == 'user':
                latest_user_message = event
                break
        
        # Check for incomplete tasks
        has_incomplete_task = self.current_task and not self.current_task.get('completed', False)
        
        # Check for errors that need handling
        recent_errors = [e for e in recent_events if e.get('type') == 'Error']
        
        return {
            'latest_user_message': latest_user_message,
            'has_incomplete_task': has_incomplete_task,
            'recent_errors': recent_errors,
            'requires_action': bool(latest_user_message or has_incomplete_task or recent_errors),
            'event_count': len(self.event_stream),
            'analysis_timestamp': time.time()
        }

    async def _select_tool(self, analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Choose next tool call based on current state, task planning, relevant knowledge
        """
        # If we have a new user message, start with acknowledgment
        if analysis['latest_user_message'] and not analysis['has_incomplete_task']:
            user_message = analysis['latest_user_message']['content']
            
            # Create new task from user message
            self.current_task = {
                'description': user_message,
                'created_at': time.time(),
                'completed': False,
                'steps': []
            }
            
            # First response: brief acknowledgment
            return {
                'tool': 'message_notify_user',
                'parameters': {
                    'text': f"I understand you want me to: {user_message}. Let me work on this for you."
                },
                'reason': 'acknowledge_user_request'
            }
        
        # If we have an incomplete task, continue working on it
        if analysis['has_incomplete_task']:
            # Use planner to determine next step
            plan_result = await self.planner.get_next_action(
                self.current_task, 
                self.execution_history
            )
            
            if plan_result:
                return {
                    'tool': plan_result.get('tool', 'message_notify_user'),
                    'parameters': plan_result.get('parameters', {'text': 'Working on your request...'}),
                    'reason': 'continue_task_execution'
                }
        
        # Handle errors
        if analysis['recent_errors']:
            return {
                'tool': 'message_notify_user',
                'parameters': {
                    'text': f"I encountered an error: {analysis['recent_errors'][-1]['content']}. Let me try a different approach."
                },
                'reason': 'error_recovery'
            }
        
        return None

    async def _execute_tool(self, tool_selection: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the selected tool and return results
        """
        tool_name = tool_selection['tool']
        parameters = tool_selection['parameters']
        
        # Add Action event to stream
        action_event = {
            'type': 'Action',
            'tool': tool_name,
            'parameters': parameters,
            'reason': tool_selection.get('reason', 'unknown'),
            'timestamp': time.time(),
            'id': len(self.event_stream)
        }
        self.event_stream.append(action_event)
        
        # Execute through Manus tools registry
        result = await manus_tools.execute_tool(tool_name, parameters)
        
        # Record in execution history
        self.execution_history.append({
            'action': tool_selection,
            'result': result,
            'timestamp': time.time()
        })
        
        return result

    def _is_task_complete(self, execution_result: Dict[str, Any]) -> bool:
        """
        Determine if the current task is complete based on execution result
        """
        # Simple completion logic - can be enhanced
        if execution_result.get('success') and self.current_task:
            # Check if this was a final message to user
            if execution_result.get('tool') == 'message_notify_user':
                return True
            
            # Check if this was an idle command
            if execution_result.get('tool') == 'idle':
                return True
        
        return False

    async def _submit_results(self):
        """
        Submit final results to user and mark task as complete
        """
        if self.current_task:
            self.current_task['completed'] = True
            self.current_task['completed_at'] = time.time()
            
            # Add task completion to memory
            await self.memory.add_conversation_turn(
                "system",
                f"Task completed: {self.current_task['description']}"
            )

    async def process_message(self, message: str) -> Dict[str, Any]:
        """
        Process a user message through the agent loop
        
        Args:
            message: User message string
            
        Returns:
            Response dictionary
        """
        event = {
            'type': 'Message',
            'content': message,
            'source': 'user'
        }
        
        return await self.process_event_stream(event)

    async def start(self):
        """Start the agentic loop"""
        self.state = AgentState.IDLE
        
    async def stop(self):
        """Stop the agentic loop"""
        self.state = AgentState.IDLE
        
    def get_status(self) -> Dict[str, Any]:
        """Get current loop status"""
        return {
            "state": self.state.value,
            "event_stream_length": len(self.event_stream),
            "execution_history_length": len(self.execution_history),
            "current_task": self.current_task,
            "working_language": self.working_language
        }


class ManusAIEngine:
    """
    Main Manus AI Engine that orchestrates all components
    """
    
    def __init__(self):
        self.agentic_loop = AgenticLoop()
        self.state = AgentState.IDLE
        
    async def start(self):
        """Start the engine"""
        self.state = AgentState.IDLE
        await self.agentic_loop.start()
        
    async def stop(self):
        """Stop the engine"""
        await self.agentic_loop.stop()
        self.state = AgentState.IDLE
        
    async def process_message(self, message: str) -> Dict[str, Any]:
        """Process a user message"""
        return await self.agentic_loop.process_message(message)
        
    def get_status(self) -> Dict[str, Any]:
        """Get engine status"""
        return {
            "state": self.state.value,
            "loop_status": self.agentic_loop.get_status()
        }