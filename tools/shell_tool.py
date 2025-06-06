"""
Shell tool adapter for Manus AI Clone
Implements secure command execution with sandboxing
"""

import re
import subprocess  # Added
import shlex     # Added
from typing import Dict, Any, Optional, List, Union
from core.logging import get_logger # Added for logging

from core.event_processor import EventType
from tools.tool_interface import ToolAdapter, ToolType, ToolMetadata, ExecutionResult, SecurityContext, PermissionLevel

class ShellTool(ToolAdapter):
    """
    Adapter for secure shell command execution
    """
    def __init__(self):
        self.logger = get_logger(__name__) # Added for logging
        self.logger.info("Initializing ShellTool") # Added for logging
        # Create tool metadata
        metadata = ToolMetadata(
            name="shell_tool",
            description="Execute shell commands securely using subprocess",
            version="1.1.0", # Version updated
            author="Manus AI Clone Team",
            license_type="MIT"
        )
        
        # Initialize base class
        super().__init__(
            tool_type=ToolType.SHELL,
            metadata=metadata,
            permission_level=PermissionLevel.ADMIN
        )
        
        # Shell-specific configuration
        self.sandbox_config = {
            "memory_limit": 512 * 1024 * 1024,  # bytes (512MB) - For future advanced sandbox
            "cpu_limit": 1.0,  # CPU time in seconds - For future advanced sandbox
            "network_access": False, # For future advanced sandbox
            "filesystem_readonly": True, # For future advanced sandbox
            "timeout": 30.0,  # seconds
            "max_output_size": 1 * 1024 * 1024  # 1MB, added
        }
        
        self.max_execution_time: float = self.sandbox_config["timeout"]
        self.max_output_size: int = self.sandbox_config["max_output_size"]

        # Blocked commands (exact command names)
        self.blocked_commands: List[str] = [
            "rm", "mkfs", "dd", "chmod", "chown", # Basic dangerous commands
            "reboot", "shutdown", "halt", "poweroff", "fdisk", "mkswap", "swapon", "swapoff"
        ]
        
        # Allowed commands (exact command names)
        # If empty, all non-blocked commands are allowed.
        # If populated, only these (and not blocked) are allowed.
        self.allowed_commands: List[str] = [
            "echo", "cat", "grep", "find", "ls", "pwd", "df", "free", "uname", "head", "tail", "wc", "sort", "uniq"
        ]

        # Sequences indicative of dangerous shell operations in the raw command string
        self.dangerous_command_sequences: List[str] = [
            ";", "&&", "||", "|", "`", "$("
        ]

    def _validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        Validate shell command parameters
        
        Args:
            parameters: Parameters to validate
            
        Returns:
            True if valid, False otherwise
        """
        self.logger.debug(f"Validating parameters: {parameters}")
        # Check required parameter
        if "command" not in parameters:
            self.logger.warning("Parameter validation failed: 'command' not in parameters.")
            return False
            
        # Validate command format
        if not isinstance(parameters["command"], str):
            self.logger.warning("Parameter validation failed: 'command' is not a string.")
            return False
            
        # Validate working directory if present
        if "working_dir" in parameters:
            if not isinstance(parameters["working_dir"], str) or not self._validate_path(parameters["working_dir"]):
                self.logger.warning(f"Parameter validation failed: Invalid 'working_dir': {parameters['working_dir']}")
                return False
            
        # Validate command against security rules
        if not self._validate_command(parameters["command"]):
            # _validate_command will log its own reasons
            return False
            
        self.logger.debug("Parameters validated successfully.")
        return True

    def _validate_command(self, command: str) -> bool:
        """
        Validate command against allowed/blocked lists and dangerous patterns.
        
        Args:
            command: Command string to validate
            
        Returns:
            True if command is allowed, False otherwise.
        """
        self.logger.debug(f"Validating command: '{command}'")
        # 1. Check for dangerous character sequences in the raw command string
        for seq in self.dangerous_command_sequences:
            if seq in command:
                self.logger.warning(f"Command validation failed: Dangerous sequence '{seq}' found in command: '{command}'.")
                return False

        # 2. Parse the command using shlex
        try:
            command_parts = shlex.split(command)
            self.logger.debug(f"Command parsed by shlex: {command_parts}")
        except ValueError as e:
            self.logger.warning(f"Command validation failed: Malformed command string (shlex error: {e}) for command: '{command}'.")
            return False

        if not command_parts:
            self.logger.warning("Command validation failed: Empty command after parsing.")
            return False

        base_command = command_parts[0]
        self.logger.debug(f"Base command identified: '{base_command}'")

        # 3. Check against blocked commands
        if base_command in self.blocked_commands:
            self.logger.warning(f"Command validation failed: Command '{base_command}' is in blocked_commands list.")
            return False
            
        # 4. Check against allowed commands (if the list is not empty)
        if self.allowed_commands: # Only enforce if allowed_commands is populated
            if base_command not in self.allowed_commands:
                self.logger.warning(f"Command validation failed: Command '{base_command}' not in allowed_commands list: {self.allowed_commands}")
                return False
                
        # Potentially: Further validation on arguments in command_parts if needed
        self.logger.debug(f"Command '{command}' validated successfully.")
        return True

    def _validate_path(self, path: str) -> bool:
        """
        Validate file paths in shell commands
        
        Args:
            path: Path to validate
            
        Returns:
            True if path is valid and accessible
        """
        self.logger.debug(f"Validating path for shell execution: '{path}'")
        # Prevent path traversal attacks
        if ".." in path:
            self.logger.warning(f"Path validation failed: '..' detected in path '{path}'.")
            return False
            
        # Allow only specific directories
        allowed_prefixes = ["/sandbox", "/tmp"] # This should ideally be configurable or more robust
        if not any(path.startswith(prefix) for prefix in allowed_prefixes):
            self.logger.warning(f"Path validation failed: Path '{path}' does not start with allowed prefixes: {allowed_prefixes}.")
            return False
        
        self.logger.debug(f"Path '{path}' validated successfully for shell execution.")
        return True

    def _execute_direct(self, parameters: Dict[str, Any]) -> ExecutionResult:
        """
        Execute command directly using subprocess.run()
        
        Args:
            parameters: Dictionary containing command details.
                        Assumes 'command' key is present and validated.
            
        Returns:
            Execution result
        """
        self.logger.info(f"Executing shell command: '{parameters['command']}' in working_dir: '{parameters.get('working_dir')}'")
        command_str: str = parameters["command"]
        working_dir: Optional[str] = parameters.get("working_dir") # Uses system default if None

        # If a specific working_dir is provided, validate it (already done by _validate_parameters, but good for direct calls)
        if working_dir is not None and not self._validate_path(working_dir):
            self.logger.error(f"Shell execution failed: Invalid or disallowed working directory '{working_dir}'.")
            return ExecutionResult(
                tool_name=self.metadata.name,
                success=False,
                output=None,
                error=f"Invalid or disallowed working directory: {working_dir}"
            )

        try:
            # The command string itself has been validated by _validate_command
            # (called via _validate_parameters by the base ToolAdapter.execute method).
            # We split it here again for subprocess.run.
            try:
                command_parts = shlex.split(command_str)
                self.logger.debug(f"Command for subprocess: {command_parts}")
            except ValueError as e: # Should be caught by _validate_command, but as safeguard:
                self.logger.error(f"Shell execution failed: Command parsing error (shlex) for '{command_str}': {e}", exc_info=True)
                return ExecutionResult(
                    tool_name=self.metadata.name,
                    success=False,
                    output={"command_executed": command_str, "working_dir": working_dir},
                    error=f"Command parsing failed (shlex) during execution prep: {str(e)}"
                )
            
            if not command_parts: # Also should be caught by _validate_command
                 self.logger.error(f"Shell execution failed: Empty command after parsing '{command_str}'.")
                 return ExecutionResult(
                    tool_name=self.metadata.name,
                    success=False,
                    output={"command_executed": command_str, "working_dir": working_dir},
                    error="Empty command after parsing for execution."
                )
            
            self.logger.info(f"Running command: {command_parts} in CWD: {working_dir or 'default'}")
            process = subprocess.run(
                command_parts,
                capture_output=True,
                text=True,
                timeout=self.max_execution_time,
                cwd=working_dir, # subprocess.run handles None cwd as current process's cwd
                check=False # We handle return code manually
            )
            self.logger.debug(f"Command '{command_parts[0]}' completed with return code {process.returncode}.")

            stdout_data = process.stdout[:self.max_output_size] if process.stdout else ""
            stderr_data = process.stderr[:self.max_output_size] if process.stderr else ""
            
            if len(process.stdout) > self.max_output_size:
                self.logger.warning(f"Stdout for command '{command_str}' was truncated from {len(process.stdout)} to {self.max_output_size} bytes.")
                stdout_data += "\n[...output truncated...]"
            if len(process.stderr) > self.max_output_size:
                self.logger.warning(f"Stderr for command '{command_str}' was truncated from {len(process.stderr)} to {self.max_output_size} bytes.")
                stderr_data += "\n[...error output truncated...]"

            result_output = {
                "command_executed": command_str,
                "return_code": process.returncode,
                "stdout": stdout_data,
                "stderr": stderr_data,
                "working_dir": working_dir if working_dir is not None else "default (current)"
            }
            self.logger.debug(f"Raw execution output: stdout length {len(stdout_data)}, stderr length {len(stderr_data)}")

            if process.returncode == 0:
                self.logger.info(f"Command '{command_str}' executed successfully.")
                return ExecutionResult(
                    tool_name=self.metadata.name,
                    success=True,
                    output=result_output
                )
            else:
                error_detail = f"Command failed with return code {process.returncode}."
                self.logger.warning(f"Command '{command_str}' failed. Return code: {process.returncode}. Stderr: {stderr_data[:200]}")
                return ExecutionResult(
                    tool_name=self.metadata.name,
                    success=False,
                    output=result_output,
                    error=error_detail
                )

        except subprocess.TimeoutExpired as e:
            self.logger.warning(f"Command '{command_str}' timed out after {self.max_execution_time} seconds.", exc_info=True)
            stdout_data = e.stdout.decode(errors='ignore')[:self.max_output_size] if isinstance(e.stdout, bytes) else (e.stdout[:self.max_output_size] if e.stdout else "")
            stderr_data = e.stderr.decode(errors='ignore')[:self.max_output_size] if isinstance(e.stderr, bytes) else (e.stderr[:self.max_output_size] if e.stderr else "")
            return ExecutionResult(
                tool_name=self.metadata.name,
                success=False,
                output={
                    "command_executed": command_str,
                    "stdout": stdout_data,
                    "stderr": stderr_data,
                    "return_code": -1, # Custom code for timeout
                    "working_dir": working_dir if working_dir is not None else "default (current)"
                },
                error=f"Command timed out after {self.max_execution_time} seconds."
            )
        except FileNotFoundError: # Command executable not found
            self.logger.error(f"Shell execution failed: Command not found '{command_parts[0] if command_parts else command_str}'.", exc_info=True)
            return ExecutionResult(
                tool_name=self.metadata.name,
                success=False,
                output={"command_executed": command_str, "working_dir": working_dir if working_dir is not None else "default (current)"},
                error=f"Command not found: {command_parts[0] if command_parts else command_str}"
            )
        except PermissionError as e: # OS-level permission error executing the command
             self.logger.error(f"Shell execution failed: Permission denied for command '{command_str}': {e}", exc_info=True)
             return ExecutionResult(
                tool_name=self.metadata.name,
                success=False,
                output={"command_executed": command_str, "working_dir": working_dir if working_dir is not None else "default (current)"},
                error=f"Permission denied during command execution: {str(e)}"
            )
        except Exception as e: # Catch-all for other subprocess or unexpected errors
            self.logger.error(f"Unexpected error executing shell command '{command_str}': {e}", exc_info=True)
            return ExecutionResult(
                tool_name=self.metadata.name,
                success=False,
                output={"command_executed": command_str, "working_dir": working_dir if working_dir is not None else "default (current)"},
                error=f"An unexpected error occurred: {str(e)}"
            )

    def execute_shell_command(self,
                              command: str,
                             working_dir: str = "/sandbox",
                             context: Optional[SecurityContext] = None) -> ExecutionResult:
        """
        Direct API for executing shell commands
        
        Args:
            command: Shell command to execute
            working_dir: Working directory for execution
            context: Security context for operation validation
            
        Returns:
            Execution result
        """
        self.logger.info(f"execute_shell_command API called. Command: '{command}', WD: '{working_dir}'")
        # Build parameters dictionary
        parameters = {
            "command": command,
            "working_dir": working_dir
        }
        
        # Execute through main execution path
        result = self.execute(parameters, context)
        if result.success:
            self.logger.info(f"Shell command executed successfully via API. Output: {result.output.get('return_code')}")
        else:
            self.logger.error(f"Shell command execution failed via API. Error: {result.error}")
        return result

    def set_sandbox_config(self,
                         memory_limit: Optional[int] = None,
                         cpu_limit: Optional[float] = None,
                         network_access: Optional[bool] = None,
                         filesystem_readonly: Optional[bool] = None,
                         timeout: Optional[float] = None,
                         max_output_size: Optional[int] = None) -> None:
        """
        Configure sandbox settings.
        Note: memory_limit, cpu_limit, network_access, filesystem_readonly are for
        potential future advanced sandboxing (e.g., Docker).
        timeout and max_output_size directly affect subprocess.run behavior.
        
        Args:
            memory_limit: Maximum memory usage in bytes
            cpu_limit: Maximum CPU time in seconds
            network_access: Whether network access is allowed
            filesystem_readonly: Whether filesystem is read-only
            timeout: Maximum execution time in seconds for subprocess
            max_output_size: Maximum size for stdout/stderr in bytes
        """
        self.logger.info(f"Updating ShellTool sandbox configuration: timeout={timeout}, max_output_size={max_output_size}, etc.")
        if memory_limit is not None:
            self.sandbox_config["memory_limit"] = memory_limit
            self.logger.debug(f"Sandbox memory_limit set to {memory_limit}")
        if cpu_limit is not None:
            self.sandbox_config["cpu_limit"] = cpu_limit
            self.logger.debug(f"Sandbox cpu_limit set to {cpu_limit}")
        if network_access is not None:
            self.sandbox_config["network_access"] = network_access
            self.logger.debug(f"Sandbox network_access set to {network_access}")
        if filesystem_readonly is not None:
            self.sandbox_config["filesystem_readonly"] = filesystem_readonly
            self.logger.debug(f"Sandbox filesystem_readonly set to {filesystem_readonly}")
        if timeout is not None:
            self.sandbox_config["timeout"] = timeout
            self.max_execution_time = timeout
            self.logger.debug(f"Sandbox timeout and max_execution_time set to {timeout}")
        if max_output_size is not None:
            self.sandbox_config["max_output_size"] = max_output_size
            self.max_output_size = max_output_size # Ensure instance attribute is also updated
            self.logger.debug(f"Sandbox max_output_size set to {max_output_size}")
        self.logger.info("ShellTool sandbox configuration updated.")

    def add_blocked_command(self, command_name: str) -> None:
        """
        Add a new command name to the blocked list.
        
        Args:
            command_name: Exact command name to block (e.g., "rm").
        """
        if command_name and command_name not in self.blocked_commands:
            self.blocked_commands.append(command_name)
            self.logger.info(f"Command '{command_name}' added to blocked_commands list.")
        elif not command_name:
            self.logger.warning("Attempted to add an empty command name to blocked_commands.")
        else:
            self.logger.debug(f"Command '{command_name}' is already in blocked_commands list.")


    def add_allowed_command(self, command_name: str) -> None:
        """
        Add a new command name to the allowed list.
        
        Args:
            command_name: Exact command name to allow (e.g., "ls").
        """
        if command_name and command_name not in self.allowed_commands:
            self.allowed_commands.append(command_name)
            self.logger.info(f"Command '{command_name}' added to allowed_commands list.")
        elif not command_name:
            self.logger.warning("Attempted to add an empty command name to allowed_commands.")
        else:
            self.logger.debug(f"Command '{command_name}' is already in allowed_commands list.")

    def remove_allowed_command(self, command_name: str) -> None:
        """
        Remove a command name from the allowed list.
        
        Args:
            command_name: Command name to remove.
        """
        if command_name in self.allowed_commands:
            self.allowed_commands.remove(command_name)
            self.logger.info(f"Command '{command_name}' removed from allowed_commands list.")
        else:
            self.logger.debug(f"Command '{command_name}' not found in allowed_commands list for removal.")

    def remove_blocked_command(self, command_name: str) -> None:
        """
        Remove a command name from the blocked list.
        
        Args:
            command_name: Command name to remove from blocked list.
        """
        if command_name in self.blocked_commands:
            self.blocked_commands.remove(command_name)
            self.logger.info(f"Command '{command_name}' removed from blocked_commands list.")
        else:
            self.logger.debug(f"Command '{command_name}' not found in blocked_commands list for removal.")