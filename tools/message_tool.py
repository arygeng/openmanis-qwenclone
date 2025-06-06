"""
Message tool adapter for Manus AI Clone
Implements secure messaging functionality with content filtering
"""

import re
import uuid
from typing import Dict, Any, Optional, List, Union, TYPE_CHECKING
from datetime import datetime
from core.logging import get_logger # Added for logging

from core.event_processor import EventType
# from tools.tool_interface import ToolAdapter, ToolType, ToolMetadata, ExecutionResult, SecurityContext, PermissionLevel # Moved to TYPE_CHECKING

if TYPE_CHECKING:
    from tools.tool_interface import ToolAdapter, ToolType, ToolMetadata, ExecutionResult, SecurityContext, PermissionLevel # Moved here

class MessageTool(ToolAdapter):
    """
    Adapter for messaging functionality with security validation
    """
    def __init__(self):
        self.logger = get_logger(__name__) # Added for logging
        self.logger.info("Initializing MessageTool") # Added for logging
        # Create tool metadata
        metadata = ToolMetadata(
            name="message_tool",
            description="Handles user messages and generates responses",
            version="1.0.0",
            author="Manus AI Clone Team",
            license_type="MIT"
        )
        
        # Initialize base class
        super().__init__(
            tool_type=ToolType.MESSAGE,
            metadata=metadata,
            permission_level=PermissionLevel.WRITE
        )
        
        # Message-specific configuration
        self.max_message_length = 10000  # characters
        self.prohibited_patterns = [
            r"password=.*",
            r"api_key=.*",
            r"secret=.*"
        ]
        self.supported_recipients = ["user", "system", "external"]
# Added as per Day 6 plan
        self.conversation_history: List[Dict[str, Any]] = []
        self.response_templates: Dict[str, str] = {
            "greeting": "Hello! How can I help you today?",
            "acknowledgment": "I understand. Let me help you with that.",
            "error": "I apologize, but I encountered an error: {error}"
        }

    def _validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        Validate message parameters as per Day 6 plan
        
        Args:
            parameters: Parameters to validate
            
        Returns:
            True if valid, False otherwise
        """
        self.logger.debug(f"Validating parameters: {parameters}")
        # Check required parameters as per Day 6 plan
        required_fields = ["message", "user_id"]
        if not all(field in parameters for field in required_fields):
            self.logger.warning(f"Parameter validation failed: Missing required fields. Expected: {required_fields}, Got: {list(parameters.keys())}")
            return False
        # Note: Original plan did not specify further validation for Phase 1 MessageTool
        self.logger.debug("Parameters validated successfully.")
        return True

    def _validate_content(self, text: str) -> bool:
        """
        Validate message content against prohibited patterns
        
        Args:
            text: Message text to validate
            
        Returns:
            True if valid, False otherwise
        """
        self.logger.debug(f"Validating content for prohibited patterns. Length: {len(text)}")
        # Check for prohibited patterns
        for pattern in self.prohibited_patterns:
            if re.search(pattern, text):
                self.logger.warning(f"Content validation failed: Prohibited pattern '{pattern}' found.")
                return False
        
        if len(text) > self.max_message_length:
            self.logger.warning(f"Content validation failed: Message length {len(text)} exceeds maximum {self.max_message_length}.")
            return False
            
        self.logger.debug("Content validated successfully.")
        return True

    def _generate_response(self, message: str, user_id: str) -> str:
        """
        Generate response to user message based on Day 6 plan
        """
        message_lower = message.lower()
        
        if any(greeting in message_lower for greeting in ["hello", "hi", "hey"]):
            return self.response_templates["greeting"]
        elif any(word in message_lower for word in ["help", "assist", "support"]):
            return "I'm here to help! What would you like me to do?" # Specific response from plan
        elif "?" in message:
            return "That's a great question. Let me think about that..." # Specific response from plan
        else:
            return self.response_templates["acknowledgment"]

    def _execute_direct(self, parameters: Dict[str, Any]) -> ExecutionResult:
        """
        Execute message processing as per Day 6 plan
        
        Args:
            parameters: Dictionary containing message details
            
        Returns:
            Execution result
        """
        self.logger.info(f"Executing MessageTool with parameters: {parameters}")
        try:
            message_text = parameters["message"] # Changed from 'text'
            user_id = parameters["user_id"]
            
            self.logger.debug(f"User '{user_id}' sent message: '{message_text}'")

            # Store user message in conversation history
            self.conversation_history.append({
                "user_id": user_id,
                "message": message_text,
                "timestamp": datetime.now().isoformat(),
                "type": "user"
            })
            self.logger.debug("User message added to conversation history.")
            
            # Generate response
            response_text = self._generate_response(message_text, user_id)
            self.logger.debug(f"Generated response: '{response_text}'")
            
            # Store assistant response in history
            self.conversation_history.append({
                "user_id": user_id,
                "message": response_text,
                "timestamp": datetime.now().isoformat(),
                "type": "assistant"
            })
            self.logger.debug("Assistant response added to conversation history.")
            
            result = ExecutionResult(
                tool_name=self.metadata.name,
                success=True,
                output={
                    "response": response_text,
                    "conversation_id": f"{user_id}_{len(self.conversation_history)}"
                }
            )
            self.logger.info(f"MessageTool execution successful. Response: {result.output}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error during MessageTool execution: {str(e)}", exc_info=True)
            return ExecutionResult(
                tool_name=self.metadata.name,
                success=False,
                output=None,
                error=str(e)
            )

    def send_message(self,
                    recipient: str,
                    text: str,
                    attachments: Optional[List[Dict[str, Any]]] = None,
                    context: Optional[SecurityContext] = None) -> ExecutionResult:
        """
        Direct API for sending messages
        
        Args:
            recipient: Target for the message
            text: Content of the message
            attachments: Optional list of attachments
            context: Security context for operation validation
            
        Returns:
            Execution result
        """
        self.logger.info(f"send_message called. Recipient: {recipient}, Text: {text[:50]}...")
        # Build parameters dictionary
        parameters = {
            "recipient": recipient,
            "text": text,
            "user_id": context.user_id if context else "unknown_user" # Assuming user_id is needed by _execute_direct
        }
        
        if attachments:
            parameters["attachments"] = attachments
            self.logger.debug(f"Attachments included: {len(attachments)}")
            
        # Execute through main execution path
        result = self.execute(parameters, context)
        if result.success:
            self.logger.info(f"Message sent successfully via send_message. Output: {result.output}")
        else:
            self.logger.error(f"Failed to send message via send_message. Error: {result.error}")
        return result

    def add_prohibited_pattern(self, pattern: str) -> None:
        """
        Add a new prohibited content pattern
        
        Args:
            pattern: Regular expression pattern to block
        """
        self.logger.info(f"Adding prohibited pattern: {pattern}")
        self.prohibited_patterns.append(pattern)

    def set_max_message_length(self, length: int) -> None:
        """
        Set maximum allowed message length
        
        Args:
            length: Maximum length in characters
        """
        self.logger.info(f"Setting max message length to: {length}")
        self.max_message_length = length