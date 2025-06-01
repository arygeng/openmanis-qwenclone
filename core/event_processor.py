"""
Event processing system for Manus AI Clone
Handles event stream processing and prioritization
"""

import logging
from enum import Enum
from typing import Dict, Any, List, Optional

from core.types import AgentState

class EventType(Enum):
    """System event types"""
    USER_MESSAGE = "user_message"
    TOOL_ACTION = "tool_action"
    EXECUTION_RESULT = "execution_result"
    PLAN_UPDATE = "plan_update"
    ERROR_EVENT = "error"
    SYSTEM_STATUS = "system_status"


class EventProcessor:
    """
    Processes system events with priority-based routing
    """
    def __init__(self):
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        
        # Event handlers by type
        self.handlers = {}
        
        # Event priority queue
        self.event_queue = []

    async def process_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a system event through the event stream
        
        Args:
            event: Event dictionary containing type and data
            
        Returns:
            Processed event result
        """
        try:
            self.logger.info(f"Processing event: {event}")
            
            # Validate event format
            if not await self._validate_event(event):
                raise ValueError("Invalid event format")
            
            # Add to event history
            await self._add_to_history(event)
            
            # Route event based on type
            return await self._route_event(event)
            
        except Exception as e:
            self.logger.error(f"Error processing event: {str(e)}")
            raise

    async def _validate_event(self, event: Dict[str, Any]) -> bool:
        """
        Validate event structure and content
        
        Args:
            event: Event dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ["type", "data", "source", "timestamp"]
        
        # Check required fields
        for field in required_fields:
            if field not in event:
                self.logger.error(f"Missing required field: {field}")
                return False
        
        # Validate event type
        try:
            EventType(event["type"])
        except ValueError:
            self.logger.error(f"Invalid event type: {event['type']}")
            return False
        
        return True

    async def _add_to_history(self, event: Dict[str, Any]) -> None:
        """
        Add event to processing history
        
        Args:
            event: Event to store in history
        """
        # Implementation will depend on storage system
        self.logger.debug(f"Adding event to history: {event}")

    async def _route_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route event to appropriate handler
        
        Args:
            event: Event to route
            
        Returns:
            Processing result
        """
        event_type = event["type"]
        
        # Get handler for this event type
        handlers = self.handlers.get(event_type, [])
        
        # If no handlers, return default response
        if not handlers:
            self.logger.warning(f"No handlers for event type: {event_type}")
            return {
                "status": "success",
                "output": f"Unhandled event type: {event_type}",
                "context_used": []
            }
        
        # Execute all handlers for this event type
        results = []
        for handler in handlers:
            try:
                result = await handler.handle(event)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Error in handler {handler}: {str(e)}")
                results.append({
                    "status": "error",
                    "error": str(e)
                })
        
        # Return combined results
        return {
            "status": "success",
            "output": results,
            "context_used": []
        }

    def register_handler(self, event_type: str, handler: Any) -> None:
        """
        Register a handler for a specific event type
        
        Args:
            event_type: Type of event to handle
            handler: Handler object or function
        """
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)

    async def get_event_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent event history
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of recent events
        """
        # Implementation will depend on storage system
        return self.event_queue[-limit:]