"""
Tool interface system for Manus AI Clone
Implements standardized tool adapters with security validation
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Union, Callable

from core.types import SecurityException, PermissionLevel
from security.permission_validator import SecurityContext

class ToolType(Enum):
    """Types of available tools"""
    MESSAGE = "message_tool"
    FILE = "file_tool"
    SHELL = "shell_tool"
    BROWSER = "browser_tool"
    KNOWLEDGE = "knowledge_tool"


class ToolStatus(Enum):
    """Tool operational status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    DISABLED = "disabled"


class ExecutionResult:
    """
    Container for tool execution results
    """
    def __init__(self, 
                 tool_name: str,
                 success: bool,
                 output: Any,
                 error: Optional[str] = None,
                 execution_time: float = 0.0):
        self.result_id = str(uuid.uuid4())
        self.tool_name = tool_name
        self.success = success
        self.output = output
        self.error = error
        self.execution_time = execution_time
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation"""
        return {
            "result_id": self.result_id,
            "tool_name": self.tool_name,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp
        }


class ToolMetadata:
    """
    Metadata container for tool information
    """
    def __init__(self, 
                 name: str,
                 description: str,
                 version: str,
                 author: str,
                 license_type: str):
        self.name = name
        self.description = description
        self.version = version
        self.author = author
        self.license_type = license_type
        self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary representation"""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "license_type": self.license_type,
            "created_at": self.created_at
        }


class ToolParameter:
    """
    Definition of a tool parameter with validation rules
    """
    def __init__(self, 
                 name: str,
                 param_type: type,
                 required: bool = True,
                 default_value: Optional[Any] = None,
                 description: str = ""):
        self.name = name
        self.param_type = param_type
        self.required = required
        self.default_value = default_value
        self.description = description

    def validate(self, value: Any) -> bool:
        """
        Validate a parameter value
        
        Args:
            value: Value to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Skip validation if value is None and not required
        if value is None and not self.required:
            return True
            
        # Type check
        if not isinstance(value, self.param_type):
            return False
            
        # Additional validation based on type
        if self.param_type == str:
            # String specific validation
            if hasattr(self, "max_length") and len(value) > self.max_length:  # type: ignore
                return False
                
        elif self.param_type == int or self.param_type == float:
            # Numeric specific validation
            if hasattr(self, "min_value") and value < self.min_value:  # type: ignore
                return False
            if hasattr(self, "max_value") and value > self.max_value:  # type: ignore
                return False
                
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert parameter definition to dictionary"""
        return {
            "name": self.name,
            "param_type": self.param_type.__name__,
            "required": self.required,
            "default_value": self.default_value,
            "description": self.description
        }


class ToolAdapter:
    """
    Base class for tool adapters with security validation
    """
    def __init__(self, 
                 tool_type: ToolType,
                 metadata: ToolMetadata,
                 permission_level: PermissionLevel = PermissionLevel.EXECUTE):
        # Tool identification
        self.tool_id = str(uuid.uuid4())
        self.tool_type = tool_type
        self.metadata = metadata
        
        # Security configuration
        self.required_permission = permission_level
        self.security_context = None
        
        # Execution settings
        self.status = ToolStatus.ACTIVE
        self.max_execution_time = 30.0  # seconds
        self.max_memory_usage = 512 * 1024 * 1024  # bytes (512MB)
        self.sandboxed = True
        
        # Statistics
        self.usage_count = 0
        self.total_execution_time = 0.0
        self.last_used = None

    def execute(self, 
               parameters: Dict[str, Any],
               context: SecurityContext) -> ExecutionResult:
        """
        Execute the tool with given parameters
        
        Args:
            parameters: Dictionary of tool-specific parameters
            context: Security context for operation validation
            
        Returns:
            Execution result with status and output
        """
        # Start time tracking
        start_time = datetime.now()
        
        try:
            # Input validation
            if not self._validate_parameters(parameters):
                raise ValueError("Invalid parameters")
                
            # Security validation
            if not self._validate_permissions(context):
                raise SecurityException("Access denied")
                
            # Security context activation
            self.security_context = context
            
            # Execute in sandbox if enabled
            if self.sandboxed:
                result = self._execute_in_sandbox(parameters)
            else:
                result = self._execute_direct(parameters)
                
            # Update statistics
            execution_time = (datetime.now() - start_time).total_seconds()
            self.usage_count += 1
            self.total_execution_time += execution_time
            self.last_used = datetime.now().isoformat()
            
            return result
            
        except Exception as e:
            # Log error and return failure result
            return ExecutionResult(
                tool_name=self.metadata.name,
                success=False,
                output=None,
                error=str(e),
                execution_time=(datetime.now() - start_time).total_seconds()
            )

    def _validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        Validate input parameters against defined schema
        
        Args:
            parameters: Parameters to validate
            
        Returns:
            True if valid, False otherwise
        """
        # This should be implemented by subclasses
        return True

    def _validate_permissions(self, context: SecurityContext) -> bool:
        """
        Validate user permissions for this tool
        
        Args:
            context: Security context
            
        Returns:
            True if authorized, False otherwise
        """
        # Check if user has required permission level
        return context.validator.check_user_permission(
            context.roles,
            self.tool_type.value,
            self.required_permission
        )

    def _execute_in_sandbox(self, parameters: Dict[str, Any]) -> ExecutionResult:
        """
        Execute tool in sandboxed environment
        
        Args:
            parameters: Tool-specific parameters
            
        Returns:
            Execution result
        """
        # Implementation will use Docker or other sandboxing
        # For now, just call direct execution
        return self._execute_direct(parameters)

    def _execute_direct(self, parameters: Dict[str, Any]) -> ExecutionResult:
        """
        Direct execution without sandboxing
        
        Args:
            parameters: Tool-specific parameters
            
        Returns:
            Execution result
        """
        # Should be implemented by subclasses
        return ExecutionResult(
            tool_name=self.metadata.name,
            success=False,
            output=None,
            error="Execution not implemented",
            execution_time=0.0
        )

    def get_metadata(self) -> Dict[str, Any]:
        """Get complete tool metadata"""
        return {
            "tool_id": self.tool_id,
            "tool_type": self.tool_type.value,
            "metadata": self.metadata.to_dict(),
            "status": self.status.value,
            "usage_stats": {
                "count": self.usage_count,
                "total_time": self.total_execution_time,
                "last_used": self.last_used
            }
        }

    def set_sandbox_config(self, 
                         max_time: float = 30.0,
                         max_memory: int = 512 * 1024 * 1024) -> None:
        """
        Configure sandbox settings
        
        Args:
            max_time: Maximum execution time in seconds
            max_memory: Maximum memory usage in bytes
        """
        self.max_execution_time = max_time
        self.max_memory_usage = max_memory

    def add_parameter_rule(self, 
                        parameter_name: str, 
                        rule_type: type, 
                        required: bool = True,
                        min_value: Optional[Any] = None,
                        max_value: Optional[Any] = None,
                        max_length: Optional[int] = None) -> None:
        """
        Add parameter validation rules
        
        Args:
            parameter_name: Name of parameter to add rules for
            rule_type: Expected type for parameter
            required: Whether parameter is required
            min_value: Minimum allowed value (for numeric types)
            max_value: Maximum allowed value (for numeric types)
            max_length: Maximum length (for string types)
        """
        # Should be implemented by subclasses
        pass

    def get_status(self) -> Dict[str, Any]:
        """Get current tool status and statistics"""
        return {
            "tool_id": self.tool_id,
            "tool_type": self.tool_type.value,
            "status": self.status.value,
            "usage_count": self.usage_count,
            "avg_execution_time": self.total_execution_time / self.usage_count if self.usage_count else 0,
            "last_used": self.last_used,
            "sandbox_config": {
                "max_execution_time": self.max_execution_time,
                "max_memory_usage": self.max_memory_usage,
                "sandboxed": self.sandboxed
            }
        }