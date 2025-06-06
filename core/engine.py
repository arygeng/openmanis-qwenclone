# Core Engine Implementation for Manus AI Clone
"""
Implements the agentic loop architecture with event stream processing
"""

import asyncio
from typing import Dict, Any, List, Optional, TYPE_CHECKING # Added TYPE_CHECKING
import json
import time
import logging
from core.logging import get_logger
from config.settings import settings, Settings # Added Settings import
from system_integration.component_connector import ComponentConnector
from core.interfaces import IEngine # Or wherever IEngine is defined

from core.types import AgentState, SecurityException, PermissionLevel
from core.message_router import MessageRouter
from core.event_processor import EventProcessor
# from planner.task_planner import TaskPlanner # Will be fetched from connector
# from knowledge.memory_system import MemorySystem # Will be fetched from connector
from knowledge.knowledge_base import KnowledgeBase # Will be fetched from connector # Uncommented
from security.permission_validator import PermissionValidator # Will be fetched from connector
from planner.plan_types import PlanStatus # For managing ExecutionPlan status
from security.permission_validator import SecurityContext # For explicit permission validation
# from planner.task_planner import TaskPlanner # Moved to TYPE_CHECKING
from knowledge.memory_system import MemorySystem

# Tool imports
# from tools.tool_interface import ToolAdapter # Tools are fetched from connector - Moved to TYPE_CHECKING
from tools.manus_tools import manus_tools # Already here, though we might instantiate tools individually
from tools.message_tool import MessageTool # Added
from tools.file_tool import FileTool # Added
from tools.shell_tool import ShellTool # Added
from tools.browser_tool import BrowserTool # Added
from tools.knowledge_tool import KnowledgeTool # Added


if TYPE_CHECKING:
    from planner.task_planner import TaskPlanner
    from tools.tool_interface import ToolAdapter # Moved here
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
    def __init__(self, connector: ComponentConnector, settings: Settings):
        self.connector = connector
        self.settings = settings
        self.state = AgentState.IDLE
        self.message_router = MessageRouter() # Assuming this is still locally managed or simple enough
        self.event_processor = EventProcessor() # Assuming this is still locally managed

        # Components like planner, memory, security validator, and tools will be fetched from the connector.
        # self.planner = TaskPlanner() # Removed
        # self.memory = MemorySystem() # Removed
        # self.security = PermissionValidator() # Removed
        # self.tool_interface = ... # Tools are fetched individually

        # Event stream - chronological list of all events
        self.event_stream = []
        
        # Execution context
        self.current_plan_object = None # Stores the ExecutionPlan object from TaskPlanner
        self.execution_history = []
        self.pending_events = []
        self.current_task_description = None # Stores the high-level task description
        
        # Working language (default English)
        self.working_language = "English" # This could come from settings
        
        # Initialize logger
        self.logger = get_logger(__name__)
        self.logger.info("AgenticLoop initialized with connector and settings")

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
            self.logger.info(f"New event added to stream: {new_event.get('type', 'Unknown')} (ID: {event_with_timestamp['id']})")
            
            # 1. ANALYZE EVENTS
            self.logger.debug("Starting event analysis phase")
            self.state = AgentState.PROCESSING
            self.logger.info(f"State transition to {self.state.value}")
            analysis = await self._analyze_events()
            self.logger.debug(f"Event analysis completed: {analysis}")
            
            # 2. SELECT TOOLS
            if analysis['requires_action']:
                self.logger.info("Action required based on event analysis")
                tool_selection = await self._select_tool(analysis) # tool_selection now includes 'step_id'
                
                # 3. WAIT FOR EXECUTION (execute the selected tool)
                # Check if a tool instance or tool name is provided
                selected_tool_identifier = tool_selection.get('tool_name') or tool_selection.get('tool') if tool_selection else None
                if tool_selection and (tool_selection.get('tool_instance') or selected_tool_identifier):
                    self.logger.info(f"Tool selected for execution: {selected_tool_identifier or tool_selection.get('tool_instance').__class__.__name__} for step {tool_selection.get('step_id')}")
                    # Extract session_id and ip_address from the event
                    session_id = new_event.get('session_id')
                    ip_address = new_event.get('ip_address')
                    execution_result = await self._execute_tool(tool_selection, session_id, ip_address)
                    self.logger.debug(f"Tool execution result: {execution_result}")

                    # Update step status in the plan
                    step_id = tool_selection.get('step_id')
                    if step_id and self.current_plan_object:
                        new_status = PlanStatus.COMPLETED if execution_result.get('success') else PlanStatus.FAILED
                        self.current_plan_object.update_step_status(step_id, new_status)
                        self.logger.info(f"Step {step_id} status updated to {new_status.value}")
                        # Check if all steps are done to update overall plan status
                        self._update_overall_plan_status()

                    # Add execution result as Observation event
                    observation_event = {
                        'type': 'Observation',
                        'content': execution_result,
                        'related_action': tool_selection,
                        'timestamp': time.time(),
                        'id': len(self.event_stream)
                    }
                    self.event_stream.append(observation_event)
                    self.logger.info(f"Observation event added to stream (ID: {observation_event['id']})")
                    
                    # 4. ITERATE - Check if task (plan) is complete
                    if self._is_task_complete(): # Pass execution_result if needed by old logic, but new logic uses self.current_plan_object
                        self.logger.info("Task (plan) determined to be complete.")
                        # 5. SUBMIT RESULTS
                        await self._submit_results()
                        # 6. ENTER STANDBY
                        self.state = AgentState.IDLE
                        self.logger.info(f"State transition to {self.state.value}")
                        return {
                            'status': 'task_complete',
                            'result': execution_result, # Or a summary of the plan
                            'message': 'Task completed successfully'
                        }
                    else:
                        self.logger.info("Task (plan) not complete, continuing iteration or new step.")
                        # Continue iteration
                        return {
                            'status': 'iteration_complete', # Or 'step_complete_plan_active'
                            'result': execution_result,
                            'next_iteration': True # This implies the loop will call process_event_stream again or select next tool
                        }
                # Condition for abstract steps (tool_selection exists, but no executable tool instance or name)
                elif tool_selection and not (tool_selection.get('tool_instance') or selected_tool_identifier):
                    self.logger.info(f"Plan step {tool_selection.get('step_id')} has no tool (abstract step), marking as complete and iterating.")
                    # Handle plan steps without tools (e.g., abstract steps)
                    step_id = tool_selection.get('step_id')
                    if step_id and self.current_plan_object:
                        self.current_plan_object.update_step_status(step_id, PlanStatus.COMPLETED) # Or a custom status
                        self._update_overall_plan_status()
                    if self._is_task_complete():
                         await self._submit_results()
                         self.state = AgentState.IDLE
                         return {'status': 'task_complete', 'message': 'Task completed (abstract steps).'}
                    return {'status': 'iteration_complete', 'message': 'Abstract step processed.', 'next_iteration': True}
                else:
                    self.logger.info("No tool selected, entering standby")
                    # No tool selected, enter standby
                    self.state = AgentState.IDLE
                    self.logger.info(f"State transition to {self.state.value}")
                    return {
                        'status': 'no_action_needed',
                        'message': 'Analysis complete, no action required'
                    }
            else:
                self.logger.info("No action required after analysis")
                # No action required
                self.state = AgentState.IDLE
                self.logger.info(f"State transition to {self.state.value}")
                return {
                    'status': 'analysis_complete',
                    'message': 'Event processed, no action required'
                }
                
        except Exception as e:
            self.logger.error(f"Error processing event stream: {str(e)}", exc_info=True)
            self.state = AgentState.ERROR
            self.logger.info(f"State transition to {self.state.value} due to error")
            error_event = {
                'type': 'Error',
                'content': str(e),
                'timestamp': time.time(),
                'id': len(self.event_stream)
            }
            self.event_stream.append(error_event)
            self.logger.info(f"Error event added to stream (ID: {error_event['id']})")
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
        self.logger.debug("Analyzing event stream for user needs and state")
        # Get recent events (last 10 for context)
        recent_events = self.event_stream[-10:] if len(self.event_stream) > 10 else self.event_stream
        self.logger.debug(f"Current event stream (last {len(recent_events)} events): {recent_events}") # More detailed log
        self.logger.debug(f"Analyzing {len(recent_events)} recent events out of {len(self.event_stream)} total")
        
        # Find latest user message
        latest_user_message = None
        for event in reversed(recent_events):
            # Handle 'Message' type from user source (e.g., internal system messages)
            if event.get('type') == 'Message' and event.get('source') == 'user':
                latest_user_message = event # content is directly in event['content']
                self.logger.info(f"Found latest user message (Type: Message, ID {event.get('id', 'N/A')}): {latest_user_message.get('content', 'Unknown')}")
                self.logger.debug(f"Full latest_user_message event (Type: Message): {latest_user_message}")
                break
            # Handle 'user_message' type (e.g., from API)
            elif event.get('type') == 'user_message':
                # Adapt the event structure to match what downstream logic expects for 'latest_user_message'
                # Specifically, ensure 'content' and 'user_id' are top-level keys if they aren't already.
                message_content = event.get('data', {}).get('message')
                user_id = event.get('user_id') # Already top-level based on docs
                if message_content is not None:
                    latest_user_message = {
                        **event, # Bring over other fields like id, timestamp, source ('api')
                        'content': message_content, # Ensure 'content' key exists
                        'user_id': user_id # Ensure 'user_id' key exists
                    }
                    self.logger.info(f"Found latest user message (Type: user_message, ID {event.get('id', 'N/A')}): {message_content}")
                    self.logger.debug(f"Adapted latest_user_message event (Type: user_message): {latest_user_message}")
                    break
        if not latest_user_message:
            self.logger.debug("No user message found in recent events for analysis.")
        
        # Check for incomplete tasks (active plan)
        has_incomplete_task = bool(self.current_plan_object and self.current_plan_object.status == PlanStatus.ACTIVE)
        if has_incomplete_task:
            self.logger.info(f"Active plan detected: {self.current_plan_object.task_description}")
        
        # Check for errors that need handling
        recent_errors = [e for e in recent_events if e.get('type') == 'Error']
        if recent_errors:
            self.logger.warning(f"Recent errors detected in event stream: {len(recent_errors)} errors")

        is_simple_conversational_message = False
        if latest_user_message:
            # 'content' should now be reliably present at the top level of latest_user_message
            user_message_content_for_analysis = latest_user_message.get('content', '')
            self.logger.debug(f"Analyzing user message content for simplicity: '{user_message_content_for_analysis}'")
            normalized_message_for_analysis = user_message_content_for_analysis.lower()
            self.logger.debug(f"Normalized message for simplicity check: '{normalized_message_for_analysis}'")
            
            simple_greetings_list = ["hello", "hi", "hey", "greetings", "hello zaddy", "good morning", "good afternoon", "good evening"]
            is_greeting = normalized_message_for_analysis in simple_greetings_list
            is_short_message = len(user_message_content_for_analysis.split()) <= 2 # Using original content for word count
            
            self.logger.debug(f"Simplicity check details: is_greeting={is_greeting} (checked against {simple_greetings_list}), is_short_message={is_short_message} (word count: {len(user_message_content_for_analysis.split())})")

            if is_greeting or is_short_message:
                is_simple_conversational_message = True
                self.logger.info(f"Event analysis: Identified simple conversational message: '{user_message_content_for_analysis}'")
                self.logger.debug(f"is_simple_conversational_message set to True for '{user_message_content_for_analysis}'")
            else:
                self.logger.debug(f"is_simple_conversational_message set to False for '{user_message_content_for_analysis}'")
        
        analysis_result = {
            'latest_user_message': latest_user_message, # This will be the adapted event if type was 'user_message'
            'has_incomplete_task': has_incomplete_task,
            'recent_errors': recent_errors,
            # Ensure requires_action is true if it's a simple message OR other conditions met
            'requires_action': bool(is_simple_conversational_message or latest_user_message or has_incomplete_task or recent_errors),
            'is_simple_conversational_message': is_simple_conversational_message,
            'event_count': len(self.event_stream),
            'analysis_timestamp': time.time()
        }
        self.logger.debug(f"Analysis result: Action required = {analysis_result['requires_action']}, Simple message = {analysis_result['is_simple_conversational_message']}")
        return analysis_result

    async def _select_tool(self, analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Choose next tool call based on current state, task planning, relevant knowledge
        """
        self.logger.debug("Starting tool selection process")
        self.logger.debug(f"Tool selection based on analysis: {analysis}")

        # Prioritize simple conversational messages directly to MessageTool
        if analysis.get('is_simple_conversational_message') and analysis.get('requires_action'):
            user_message_event = analysis['latest_user_message']
            user_message_content = user_message_event['content']
            user_id = user_message_event.get('user_id')
            
            if not user_id:
                self.logger.warning(f"user_id not found in simple user_message_event (content: '{user_message_content[:50]}...'), using 'default_user'. Event: {user_message_event}")
                user_id = 'default_user'

            message_tool_instance = self.connector.get_component('message_tool')
            if not message_tool_instance:
                self.logger.error("MessageTool not found in connector. Cannot route simple message. Falling back to notification.")
                return {
                    'tool': 'message_notify_user', # Fallback to a generic notification tool name
                    'tool_name': 'message_notify_user',
                    'parameters': {'text': "System error: MessageTool unavailable for simple reply."},
                    'reason': 'error_message_tool_missing_for_simple_reply',
                    'step_id': None
                }
            
            self.logger.info(f"Prioritized selection: Routing simple conversational message directly to MessageTool instance for user_id: '{user_id}'")
            self.logger.debug(f"Selected MessageTool instance for simple message: '{user_message_content}'. Parameters: {{'message': '{user_message_content}', 'user_id': '{user_id}'}}")
            return {
                'tool_instance': message_tool_instance,
                'tool_name': 'message_tool', # Keep name for logging and consistency
                'parameters': {'message': user_message_content, 'user_id': user_id},
                'reason': 'direct_simple_user_message_response',
                'step_id': None
            }

        # If we have a new user message (not simple, or simple handling was off) and no active plan, proceed with planning
        # Ensure this condition does not inadvertently catch simple messages if the above block fails to return
        elif analysis['latest_user_message'] and not analysis['has_incomplete_task'] and not analysis.get('is_simple_conversational_message'):
            self.logger.debug("Condition met: Latest user message exists and no incomplete task. Considering planning.")
            user_message_event = analysis['latest_user_message'] # This is now the (potentially adapted) event
            user_message_content = user_message_event['content'] # Content is now reliably at this key
            user_id = user_message_event.get('user_id') # user_id is also reliably at this key

            if not user_id: # Fallback
                self.logger.warning(f"user_id not found in user_message_event (content: '{user_message_content[:50]}...'), using 'default_user'. Event: {user_message_event}")
                user_id = 'default_user'

            self.logger.info(f"New user request (non-simple) from user_id '{user_id}': '{user_message_content}', proceeding with task planning.")
            self.current_task_description = user_message_content # This is correct, use the actual message content
            self.logger.debug(f"Attempting to create plan for task: {self.current_task_description}")
            
            # Create a new plan using TaskPlanner from connector
            planner = self.connector.get_component("planner")
            if not planner:
                self.logger.error("TaskPlanner not found in connector.")
                self.logger.debug("Selected 'message_notify_user' due to missing planner.")
                return {'tool': 'message_notify_user', 'parameters': {'text': "System error: Planner unavailable."}, 'reason': 'error_planner_missing'}

                # Context for the planner (can be more sophisticated)
                plan_context = {
                    'user_message': user_message_content,
                    'event_stream_tail': self.event_stream[-5:] # Pass recent events
                }
                try:
                    # Assuming create_plan is synchronous as per planner/task_planner.py
                    # If it were async: self.current_plan_object = await planner.create_plan(...)
                    self.current_plan_object = planner.create_plan(
                        task_description=self.current_task_description,
                        source="user_request",
                        context=plan_context
                    )
                    self.current_plan_object.status = PlanStatus.ACTIVE # Mark plan as active
                    self.logger.info(f"New plan created (ID: {self.current_plan_object.plan_id}) for task: {self.current_task_description}")
                    self.logger.debug(f"Plan created (ID: {self.current_plan_object.plan_id}). Will select first step from this plan.")
                except Exception as e:
                    self.logger.error(f"Error creating plan: {str(e)}", exc_info=True)
                    self.logger.debug(f"Selected 'message_notify_user' due to error creating plan: {str(e)}")
                    return {'tool': 'message_notify_user', 'parameters': {'text': f"Error creating plan: {str(e)}"}, 'reason': 'error_planning'}

                # Acknowledge user (optional, or could be first step of the plan)
                # For now, let's assume the plan's first step will handle interaction or be an action.
                # The logic below will pick the first step from the newly created plan.

        # If we have an active plan, find the next step
        if self.current_plan_object and self.current_plan_object.status == PlanStatus.ACTIVE:
            self.logger.info(f"Continuing work on active plan: {self.current_plan_object.task_description}")
            self.logger.debug("Condition met: Active plan exists. Looking for next pending step.")
            next_step_to_execute = None
            for step in self.current_plan_object.steps:
                if step.status == PlanStatus.PENDING:
                    next_step_to_execute = step
                    break
            
            if next_step_to_execute:
                self.logger.info(f"Next step from plan: {next_step_to_execute.description} (Tool: {next_step_to_execute.tool_name})")
                self.logger.debug(f"Selecting tool '{next_step_to_execute.tool_name}' with params {next_step_to_execute.parameters} for step_id '{next_step_to_execute.step_id}' from plan.")
                # Mark step as active (or about to be processed)
                # self.current_plan_object.update_step_status(next_step_to_execute.step_id, PlanStatus.ACTIVE) # Do this after selection, before execution
                return {
                    'tool': next_step_to_execute.tool_name, # Can be None if abstract step
                    'parameters': next_step_to_execute.parameters,
                    'reason': 'executing_plan_step',
                    'step_id': next_step_to_execute.step_id
                }
            else:
                # No pending steps, plan might be considered complete or stuck
                self.logger.info(f"No more pending steps in plan {self.current_plan_object.plan_id}.")
                self.logger.debug("No pending step found in the active plan.")
                # This state should ideally be caught by _is_task_complete after last step execution
                # If we reach here, it means all steps are non-PENDING.
                # If not COMPLETED, it might be an issue or the plan is done.
                if not any(s.status == PlanStatus.FAILED for s in self.current_plan_object.steps):
                     self.current_plan_object.status = PlanStatus.COMPLETED # Mark plan complete if all steps processed
                # Fall through to error handling or no action.
        
        # Handle errors (if not handled by a plan step)
        if analysis['recent_errors']:
            self.logger.debug("Condition met: Recent errors exist. Considering error handling.")
            # This could also be a trigger for replanning or a specific error handling plan
            error_content = analysis['recent_errors'][-1]['content']
            self.logger.warning(f"Handling recent error: {error_content}")
            self.logger.debug(f"Selecting 'message_notify_user' for error: {error_content}")
            # Potentially create a new plan for error recovery or use a default tool
            return {
                'tool': 'message_notify_user', # Default error handler tool
                'parameters': {
                    'text': f"I encountered an error: {error_content}. Let me assess the situation."
                },
                'reason': 'error_recovery_notification'
                # No step_id here as it's outside a plan or a new error plan would be made
            }
        
        self.logger.debug("No specific tool selected by planner or for initial ack/error.")
        self.logger.debug("No conditions met for tool selection. Returning None.")
        return None # No action to take

    async def _execute_tool(self, tool_selection: Dict[str, Any], session_id: Optional[str], ip_address: Optional[str]) -> Dict[str, Any]:
        """
        Execute the selected tool and return results, using ComponentConnector.
        """
        tool_instance = tool_selection.get('tool_instance')
        # Tool name can come from 'tool_name' (new path for simple message) or 'tool' (planner path)
        tool_name_from_selection = tool_selection.get('tool_name') or tool_selection.get('tool')
        
        parameters = tool_selection.get('parameters', {})
        step_id = tool_selection.get('step_id')

        if not tool_instance and not tool_name_from_selection:
            self.logger.warning(f"No tool instance or tool name provided in tool_selection for step {step_id}. Cannot execute. Selection: {tool_selection}")
            # Construct a minimal result_payload for history recording before returning
            result_payload_error = {'success': False, 'error': 'No tool instance or name specified for execution.', 'tool': None}
            self.execution_history.append({'action': tool_selection, 'result': result_payload_error, 'timestamp': time.time()})
            return result_payload_error

        # Determine the effective tool name for logging and action events.
        # If tool_instance is provided, tool_name_from_selection should also be set by _select_tool.
        # If only tool_name_from_selection is provided (planner), that's our effective name.
        effective_tool_name = tool_name_from_selection
        if not effective_tool_name and tool_instance: # Should ideally not happen if _select_tool sets both
            effective_tool_name = tool_instance.__class__.__name__
            self.logger.warning(f"Tool name was missing but instance provided; using class name: {effective_tool_name}")
        elif not effective_tool_name: # Should be caught by the check above
             effective_tool_name = "UnknownToolInExecute" # Fallback
             self.logger.error(f"Critical: effective_tool_name could not be determined. Selection: {tool_selection}")


        self.logger.info(f"Executing tool: {effective_tool_name} with parameters: {parameters} for step {step_id}")
        
        action_event = {
            'type': 'Action',
            'tool': effective_tool_name, # Use effective_tool_name for the event
            'parameters': parameters,
            'reason': tool_selection.get('reason', 'unknown'),
            'step_id': step_id,
            'timestamp': time.time(),
            'id': len(self.event_stream)
        }
        self.event_stream.append(action_event)
        self.logger.debug(f"Action event added to stream (ID: {action_event['id']})")
        
        result_payload: Dict[str, Any] = {'success': False, 'error': 'Tool execution failed unexpectedly.', 'tool': effective_tool_name}
        try:
            if not tool_instance: # If instance wasn't passed directly (e.g., from planner using 'tool' key for name)
                if not tool_name_from_selection: # This case should have been caught earlier
                    self.logger.error(f"Critical error: tool_instance is None and tool_name_from_selection is None. Cannot fetch component. Selection: {tool_selection}")
                    result_payload = {'success': False, 'error': 'Internal error: Tool name missing for component fetch.', 'tool': effective_tool_name}
                    self.execution_history.append({'action': tool_selection, 'result': result_payload, 'timestamp': time.time()})
                    return result_payload
                
                tool_instance = self.connector.get_component(tool_name_from_selection)
                if not tool_instance:
                    self.logger.error(f"Tool '{tool_name_from_selection}' not found in ComponentConnector.")
                    result_payload = {'success': False, 'error': f"Tool '{tool_name_from_selection}' not found.", 'tool': tool_name_from_selection}
                    self.execution_history.append({'action': tool_selection, 'result': result_payload, 'timestamp': time.time()})
                    return result_payload
            
            # At this point, tool_instance should be valid.
            validator = self.connector.get_component("security_validator")
            agent_context = None
            if validator:
                # Ensure agent_context is created if validator exists, even if tool has no permission_level (for consistency or future use)
                agent_context = SecurityContext(user_id="agent_system", roles=["agent_executor"], session_id=session_id, ip_address=ip_address)
                if hasattr(tool_instance, 'permission_level'):
                    operation_details = {
                        "type": "tool_execution_request",
                        "tool_name": effective_tool_name, # Use effective_tool_name
                        "parameters": parameters
                    }
                    required_permission = getattr(tool_instance, 'permission_level', PermissionLevel.READ)

                    if not validator.validate_operation(operation_details, agent_context, permission_level=required_permission):
                        self.logger.warning(f"Permission denied by validator for tool {effective_tool_name}.")
                        raise SecurityException(f"Permission denied for tool {effective_tool_name}")
            else:
                self.logger.warning("PermissionValidator not found in connector. Skipping explicit validation.")
            
            self.logger.debug(f"Attempting to execute tool instance: {effective_tool_name}")
            execution_output = await tool_instance.execute(parameters, context=agent_context)

            result_payload = {
                'success': execution_output.success,
                'output': execution_output.output,
                'error': execution_output.error,
                'tool': effective_tool_name # Use effective_tool_name
            }
            self.logger.info(f"Tool execution completed: {effective_tool_name} with success: {execution_output.success}")
            self.logger.debug(f"Full result for {effective_tool_name}: {result_payload}")

        except SecurityException as se:
            self.logger.error(f"SecurityException during tool execution ({effective_tool_name}): {str(se)}", exc_info=True)
            result_payload = {'success': False, 'error': str(se), 'tool': effective_tool_name}
        except Exception as e:
            self.logger.error(f"Error during tool execution ({effective_tool_name}): {str(e)}", exc_info=True)
            result_payload = {'success': False, 'error': str(e), 'tool': effective_tool_name}
        
        # Record in execution history
        self.execution_history.append({
            'action': tool_selection,
            'result': result_payload,
            'timestamp': time.time()
        })
        self.logger.debug("Execution result recorded in history")
        
        return result_payload

    def _is_task_complete(self) -> bool: # Removed execution_result argument
        """
        Determine if the current task (plan) is complete.
        """
        self.logger.debug("Checking if current task (plan) is complete")
        if self.current_plan_object:
            if self.current_plan_object.status == PlanStatus.COMPLETED:
                self.logger.info(f"Plan {self.current_plan_object.plan_id} is marked COMPLETED.")
                return True
            if self.current_plan_object.status == PlanStatus.FAILED:
                self.logger.info(f"Plan {self.current_plan_object.plan_id} is marked FAILED.")
                return True # A failed plan is also "done" in terms of processing by the loop

            # If plan is ACTIVE, check if all steps are done
            if self.current_plan_object.status == PlanStatus.ACTIVE:
                all_steps_processed = True
                for step in self.current_plan_object.steps:
                    if step.status == PlanStatus.PENDING or step.status == PlanStatus.ACTIVE:
                        all_steps_processed = False
                        break
                if all_steps_processed:
                    self.logger.info(f"All steps in plan {self.current_plan_object.plan_id} are processed. Marking plan complete.")
                    # Determine if overall plan was success or failure based on steps
                    if any(s.status == PlanStatus.FAILED for s in self.current_plan_object.steps):
                        self.current_plan_object.status = PlanStatus.FAILED
                    else:
                        self.current_plan_object.status = PlanStatus.COMPLETED
                    return True
        elif not self.current_task_description: # No active task description means nothing to do
             self.logger.debug("No current task description or plan, considering task complete (idle).")
             return True

        self.logger.debug("Task (plan) not yet complete.")
        return False

    async def _submit_results(self):
        """
        Submit final results to user and mark task (plan) as complete.
        """
        if self.current_plan_object:
            self.logger.info(f"Submitting results for plan: {self.current_plan_object.task_description} (ID: {self.current_plan_object.plan_id})")
            # Plan status should already be COMPLETED or FAILED by _is_task_complete or _update_overall_plan_status
            
            memory = self.connector.get_component("memory_system")
            if memory:
                status_message = "completed successfully" if self.current_plan_object.status == PlanStatus.COMPLETED else "failed"
                await memory.add_conversation_turn( # Assuming add_conversation_turn is async
                    "system",
                    f"Task '{self.current_plan_object.task_description}' {status_message}."
                )
                self.logger.debug("Task completion status recorded in memory.")
            else:
                self.logger.warning("MemorySystem not found in connector. Cannot record task completion.")
            
            # Reset current plan and task description for next interaction
            self.current_plan_object = None
            self.current_task_description = None
        elif self.current_task_description : # Should not happen if plan was created
             self.logger.warning(f"Attempting to submit results for task '{self.current_task_description}' but no plan object exists.")
             self.current_task_description = None


    def _update_overall_plan_status(self):
        """Helper to update the main plan status based on its steps."""
        if not self.current_plan_object:
            return

        all_steps_done = True
        any_step_failed = False
        for step in self.current_plan_object.steps:
            if step.status == PlanStatus.PENDING or step.status == PlanStatus.ACTIVE:
                all_steps_done = False
                break
            if step.status == PlanStatus.FAILED:
                any_step_failed = True
        
        if all_steps_done:
            if any_step_failed:
                self.current_plan_object.status = PlanStatus.FAILED
                self.logger.info(f"Overall plan {self.current_plan_object.plan_id} status updated to FAILED.")
            else:
                self.current_plan_object.status = PlanStatus.COMPLETED
                self.logger.info(f"Overall plan {self.current_plan_object.plan_id} status updated to COMPLETED.")
        # If not all steps are done, plan remains ACTIVE (or its initial PENDING if not started)

    async def process_message(self, message: str) -> Dict[str, Any]:
        """
        Process a user message through the agent loop
        
        Args:
            message: User message string
            
        Returns:
            Response dictionary
        """
        self.logger.info(f"Processing user message: {message}")
        event = {
            'type': 'Message',
            'content': message,
            'source': 'user'
        }
        
        result = await self.process_event_stream(event)
        self.logger.debug(f"User message processing result: {result}")
        return result

    async def start(self):
        """Start the agentic loop"""
        self.logger.info("Starting agentic loop")
        self.state = AgentState.IDLE
        self.logger.info(f"State set to {self.state.value}")
        
    async def stop(self):
        """Stop the agentic loop"""
        self.logger.info("Stopping agentic loop")
        self.state = AgentState.IDLE
        self.logger.info(f"State set to {self.state.value}")
        
    def get_status(self) -> Dict[str, Any]:
        """Get current loop status"""
        self.logger.debug("Retrieving agentic loop status")
        status = {
            "state": self.state.value,
            "event_stream_length": len(self.event_stream),
            "execution_history_length": len(self.execution_history),
            "current_task_description": self.current_task_description,
            "current_plan_id": self.current_plan_object.plan_id if self.current_plan_object else None,
            "current_plan_status": self.current_plan_object.status.value if self.current_plan_object else None,
            "working_language": self.working_language
        }
        self.logger.debug(f"Current status: {status}")
        return status


class ManusAIEngine(IEngine): # Add IEngine here
    """
    Main Manus AI Engine that orchestrates all components
    """

    def __init__(self, settings: Settings): # Added settings argument
        self.logger = get_logger(__name__)
        self.logger.info("Initializing ManusAIEngine")
        self.settings = settings

        # Initialize Component Connector
        self.component_connector = ComponentConnector()

        # Instantiate core components
        # AgenticLoop now requires connector and settings
        self.agentic_loop = AgenticLoop(self.component_connector, self.settings)
        self.task_planner = TaskPlanner() # This instance is registered with connector
        self.permission_validator = PermissionValidator() # This instance is registered with connector
        self.memory_system = MemorySystem()
        self.knowledge_base = KnowledgeBase()

        # Instantiate tools
        self.message_tool = MessageTool()
        self.file_tool = FileTool()
        self.shell_tool = ShellTool()
        self.browser_tool = BrowserTool()
        self.knowledge_tool = KnowledgeTool(knowledge_base=self.knowledge_base) # Modified instantiation
        # Note: manus_tools from tools.manus_tools seems to be a registry.
        # The task implies instantiating individual tool classes.
        # We'll register these instances. AgenticLoop currently uses the global manus_tools.
        # This might need further refactoring if AgenticLoop should use connector-managed tools.

        # Register components
        self.component_connector.register_component("engine_loop", self.agentic_loop) # Changed "engine" to "engine_loop" to avoid conflict if ManusAIEngine itself is registered
        self.component_connector.register_component("planner", self.task_planner)
        self.component_connector.register_component("security_validator", self.permission_validator)
        self.component_connector.register_component("memory_system", self.memory_system)
        self.component_connector.register_component("knowledge_base", self.knowledge_base)
        
        self.component_connector.register_component("message_tool", self.message_tool)
        self.component_connector.register_component("file_tool", self.file_tool)
        self.component_connector.register_component("shell_tool", self.shell_tool)
        self.component_connector.register_component("browser_tool", self.browser_tool)
        self.component_connector.register_component("knowledge_tool", self.knowledge_tool)
        
        # For ComponentConnector's setup_core_connections to work with its current hardcoded names,
        # we might need to register ManusAIEngine itself as "engine" or adjust setup_core_connections.
        # For now, let's assume "engine_loop" is the primary processing unit for connections.
        # If ManusAIEngine needs to be the "engine" for the connector, we'd register `self`
        # self.component_connector.register_component("engine", self)


        # Setup connections
        # The existing setup_core_connections expects "engine", "planner", "validator", "tool_manager"
        # We've registered "engine_loop", "planner", "security_validator".
        # "tool_manager" is not explicitly instantiated here as a single manager class,
        # but individual tools are. This part might need refinement based on how
        # ComponentConnector.setup_core_connections is intended to link tools.
        # For now, we call it. It might partially succeed or do nothing if expected names aren't present.
        self.logger.info("Setting up core component connections...")
        connection_ids = self.component_connector.setup_core_connections()
        self.logger.info(f"Core connections established: {connection_ids}")

        self.state = AgentState.IDLE
        self.logger.info("ManusAIEngine initialized with all components registered and connections attempted.")

    async def start(self):
        """Start the engine"""
        self.logger.info("Starting ManusAIEngine")
        self.state = AgentState.IDLE
        await self.agentic_loop.start()
        self.logger.info("ManusAIEngine started")
        
    async def stop(self):
        """Stop the engine"""
        self.logger.info("Stopping ManusAIEngine")
        await self.agentic_loop.stop()
        self.state = AgentState.IDLE
        self.logger.info("ManusAIEngine stopped")
        
    async def process_message(self, message: str) -> Dict[str, Any]:
        """Process a user message"""
        self.logger.info(f"ManusAIEngine processing message: {message}")
        result = await self.agentic_loop.process_message(message)
        self.logger.debug(f"ManusAIEngine message processing result: {result}")
        return result
        
    def get_status(self) -> Dict[str, Any]:
        """Get engine status"""
        self.logger.debug("Retrieving ManusAIEngine status")
        status = {
            "state": self.state.value,
            "loop_status": self.agentic_loop.get_status()
        }
        self.logger.debug(f"ManusAIEngine status: {status}")
        return status

    async def process_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process an event through the agentic loop"""
        self.logger.info(f"ManusAIEngine processing event: {event.get('type', 'Unknown')}")
        # Ensure self.agentic_loop is the correct instance of AgenticLoop
        # and process_event_stream is the correct method to call.
        result = await self.agentic_loop.process_event_stream(event)
        self.logger.debug(f"ManusAIEngine event processing result: {result}")
        return result

    def set_validator(self, validator: Any) -> None:
        # Implementation
        self.permission_validator = validator # Example
        self.logger.info("Validator set on ManusAIEngine")

    def set_monitor_callback(self, callback: Any) -> None:
        # Implementation
        self._monitor_callback = callback # Example
        self.logger.info("Monitor callback set on ManusAIEngine")

    def handle_security_event(self, event: Dict[str, Any]) -> None:
        # Implementation
        self.logger.info(f"ManusAIEngine handling security event: {event}")