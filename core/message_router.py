"""
Message routing system for Manus AI Clone
Implements message routing between components
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, TYPE_CHECKING # Added TYPE_CHECKING

from core.event_processor import EventProcessor
from security.permission_validator import PermissionValidator, SecurityContext
# from tools.tool_interface import ToolAdapter # Moved to TYPE_CHECKING

if TYPE_CHECKING:
    from tools.tool_interface import ToolAdapter # Moved here

class MessageRouter:
    """
    Routes messages between components with security validation
    """
    def __init__(self):
        # Message queue
        self.message_queue = []  # type: List[Dict[str, Any]]
        
        # Message routing
        self.routes = {}  # type: Dict[str, Dict[str, str]]
        
        # Component references
        self.event_processor = None  # type: Optional[EventProcessor] # Assuming EventProcessor is fine
        self.tool_adapter = None  # type: Optional['ToolAdapter'] # Changed to string literal
        self.permission_validator = None  # type: Optional[PermissionValidator] # Assuming PermissionValidator is fine
        
        # Configuration
        self.max_queue_size = 1000
        self.default_route = "default"

    def route_message(self, 
                     source: str,
                     target: str,
                     message: Dict[str, Any],
                     context: SecurityContext) -> Dict[str, Any]:
        """
        Route a message from source to target
        
        Args:
            source: Source component
            target: Target component
            message: Message to route
            context: Security context
            
        Returns:
            Response from target
        """
        # Validate message format
        if not self._validate_message(message):
            raise ValueError("Invalid message format")
            
        # Check security context
        if not self._check_security(source, target, message, context):
            raise PermissionError("Access denied")
            
        # Apply transformations if needed
        transformed_message = self._apply_transformations(source, target, message)
        
        # Add routing info
        message_id = str(uuid.uuid4())
        routed_message = {
            "id": message_id,
            "source": source,
            "target": target,
            "content": transformed_message,
            "timestamp": datetime.now().isoformat(),
            "status": "routed"
        }
        
        # Store message in queue
        self.message_queue.append(routed_message)
        
        # Process the queue
        return self._process_queue()

    def _validate_message(self, message: Dict[str, Any]) -> bool:
        """
        Validate message structure
        
        Args:
            message: Message to validate
            
        Returns:
            True if valid
        """
        # Basic message validation
        required_fields = ["type", "content"]
        return all(field in message for field in required_fields)

    def _check_security(self, 
                       source: str,
                       target: str,
                       message: Dict[str, Any],
                       context: SecurityContext) -> bool:
        """
        Check security permissions for message routing
        
        Args:
            source: Source component
            target: Target component
            message: Message being routed
            context: Security context
            
        Returns:
            True if permitted
        """
        # In real implementation would check actual permissions
        return True

    def _apply_transformations(self, 
                              source: str,
                              target: str,
                              message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply any necessary transformations to the message
        
        Args:
            source: Source component
            target: Target component
            message: Original message
            
        Returns:
            Transformed message
        """
        # In real implementation, would apply specific transformations
        return message

    def _process_queue(self) -> Dict[str, Any]:
        """Process messages in the queue"""
        # Would implement actual processing logic
        return {
            "status": "success",
            "processed": len(self.message_queue)
        }

    def set_event_processor(self, processor: EventProcessor) -> None:
        """
        Set event processor for message processing
        
        Args:
            processor: Event processor instance
        """
        self.event_processor = processor

    def set_tool_adapter(self, adapter: 'ToolAdapter') -> None: # Changed to string literal
        """
        Set tool adapter for message processing
        
        Args:
            adapter: Tool adapter instance
        """
        self.tool_adapter = adapter

    def set_permission_validator(self, validator: PermissionValidator) -> None:
        """
        Set permission validator for security checks
        
        Args:
            validator: Permission validator instance
        """
        self.permission_validator = validator

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get message queue statistics"""
        return {
            "queue_size": len(self.message_queue),
            "max_size": self.max_queue_size,
            "last_processed": datetime.now().isoformat()
        }

    def clear_queue(self) -> None:
        """Clear all messages from the queue"""
        self.message_queue = []