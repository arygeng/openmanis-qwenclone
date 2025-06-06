"""
File tool adapter for Manus AI Clone
Implements secure file operations with sandboxing
"""

import os
import re
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from core.logging import get_logger # Added for logging

from tools.tool_interface import ToolAdapter, ToolType, ToolMetadata, ExecutionResult, SecurityContext, PermissionLevel

class FileOperation(Enum):
    """Supported file operations"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    LIST = "list"
    CREATE = "create"  # Added create operation
    SEARCH = "search"


class FileTool(ToolAdapter):
    """
    Adapter for secure file operations with sandboxing
    """
    def __init__(self):
        self.logger = get_logger(__name__) # Added for logging
        self.logger.info("Initializing FileTool") # Added for logging
        # Create tool metadata
        metadata = ToolMetadata(
            name="file_tool",
            description="Secure file operations with sandboxed execution",
            version="1.0.0",
            author="Manus AI Clone Team",
            license_type="MIT"
        )
        
        # Initialize base class
        super().__init__(
            tool_type=ToolType.FILE,
            metadata=metadata,
            permission_level=PermissionLevel.WRITE
        )
        
        # File-specific configuration
        self.sandbox_root = str(Path("/app/sandbox_data/files").resolve()) # Ensure absolute path
        Path(self.sandbox_root).mkdir(parents=True, exist_ok=True) # Ensure sandbox root exists

        self.max_file_size = 10 * 1024 * 1024  # bytes (10MB)
        # Extensions allowed for writing/creating files
        self.allowed_extensions_for_write = [".txt", ".md", ".log"]
        # Extensions blocked for any operation
        self.blocked_extensions = [".exe", ".sh", ".bat", ".com", ".dll", ".so", ".pyc", ".jar", ".msi"]
        self.prohibited_patterns = [ # Patterns for filenames to block
            r".*\.env$",
            r".*\.pem$",
            r".*\.key$"
        ]
        # Paths relative to sandbox_root that are read-only
        self.read_only_paths = ["system/config/", "data/reference/"]
        # Allowed base directories for operations (absolute paths)
        self.allowed_directories = ["/app/sandbox_data", "/tmp"]

        # Add missing attributes from the reference implementation
        self.file_system = {}  # type: Dict[str, Dict[str, Any]] # Remains for now, unused by new logic
        self.usage_stats = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "last_reset": datetime.now().isoformat()
        }

    def _validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        Validate file operation parameters
        
        Args:
            parameters: Parameters to validate
            
        Returns:
            True if valid, False otherwise
        """
        self.logger.debug(f"Validating parameters: {parameters}")
        # Check required parameters
        if "operation" not in parameters:
            self.logger.warning("Parameter validation failed: 'operation' not in parameters.")
            return False
            
        # Validate operation type
        try:
            operation = FileOperation(parameters["operation"])
            self.logger.debug(f"Operation type: {operation.value}")
        except ValueError:
            self.logger.warning(f"Parameter validation failed: Invalid operation value '{parameters['operation']}'.")
            return False
            
        # Validate path parameter for operations that require it
        if operation in [FileOperation.READ, FileOperation.WRITE, FileOperation.DELETE, FileOperation.CREATE]:
            if "path" not in parameters:
                self.logger.warning(f"Parameter validation failed: 'path' not in parameters for operation {operation.value}.")
                return False
        
        # Operation-specific validation
        if operation == FileOperation.WRITE:
            if "content" not in parameters:
                self.logger.warning("Parameter validation failed: 'content' not in parameters for WRITE operation.")
                return False
            # Size check moved to _handle_write for actual content
            
        elif operation == FileOperation.SEARCH:
            if "pattern" not in parameters: # Path is optional for search, defaults to sandbox_root
                self.logger.warning("Parameter validation failed: 'pattern' not in parameters for SEARCH operation.")
                return False
        
        self.logger.debug("Parameters validated successfully.")
        return True

    def _validate_deletion(self, relative_path_str: str) -> bool:
        """
        Validate deletion operation against security rules (read-only paths).
        Args:
            relative_path_str: The user-provided relative path string.
        Returns:
            True if deletion is allowed, False otherwise.
        """
        for read_only_prefix in self.read_only_paths:
            if relative_path_str.startswith(read_only_prefix):
                self.logger.warning(f"Deletion validation failed: Path '{relative_path_str}' is in read-only paths.")
                return False
        self.logger.debug(f"Deletion validation successful for path: {relative_path_str}")
        return True

    def _validate_path(self, relative_path_str: str) -> Path:
        """
        Validates a user-provided relative path against security constraints.
        Args:
            relative_path_str: The user-provided relative path string.
        Returns:
            A resolved, absolute pathlib.Path object if valid.
        Raises:
            ValueError: If the path is invalid or violates security rules.
        """
        self.logger.debug(f"Validating path: '{relative_path_str}' relative to sandbox '{self.sandbox_root}'")
        if not relative_path_str or isinstance(relative_path_str, Path): # Ensure it's a string
             relative_path_str = str(relative_path_str)

        # Normalize and prevent empty or purely relative components like "." or ".." alone
        if relative_path_str == "." or relative_path_str == ".." or not relative_path_str.strip():
            self.logger.warning(f"Path validation failed: Path '{relative_path_str}' is empty or purely relative.")
            raise ValueError("Path cannot be empty or purely relative ('.' or '..').")
        
        # Construct the full path relative to the sandbox root
        # Path.joinpath is safer than string concatenation
        prospective_path = Path(self.sandbox_root).joinpath(relative_path_str)
        self.logger.debug(f"Prospective absolute path: {prospective_path}")

        # Resolve the path to get its canonical absolute form.
        # This handles '..' sequences and symbolic links.
        try:
            # strict=False allows resolving paths that don't exist yet (e.g. for write/create)
            # but intermediate directories must exist for resolve() to not fail if they are symlinks.
            # For our purpose, we care about the final intended location.
            resolved_path = prospective_path.resolve(strict=False)
            self.logger.debug(f"Resolved absolute path: {resolved_path}")
        except Exception as e: # Could be FileNotFoundError if a component is a broken symlink
            self.logger.error(f"Path resolution error for '{relative_path_str}': {e}", exc_info=True)
            raise ValueError(f"Path resolution error for '{relative_path_str}': {e}")

        # Security Check 1: Ensure the resolved path is within one of the allowed directories.
        is_within_allowed_dir = False
        for allowed_dir_str in self.allowed_directories:
            allowed_dir_path = Path(allowed_dir_str).resolve()
            if resolved_path == allowed_dir_path or \
               (resolved_path.is_absolute() and str(resolved_path).startswith(str(allowed_dir_path) + os.sep)):
                is_within_allowed_dir = True
                break
        
        if not is_within_allowed_dir:
            self.logger.warning(f"Path validation failed: Resolved path '{resolved_path}' for input '{relative_path_str}' is outside allowed directories: {self.allowed_directories}")
            raise ValueError(f"Path '{relative_path_str}' resolves to '{resolved_path}', which is outside the allowed directories.")

        # Security Check 2: Check for prohibited filename patterns.
        for pattern in self.prohibited_patterns:
            if re.search(pattern, resolved_path.name):
                self.logger.warning(f"Path validation failed: Path name '{resolved_path.name}' matches prohibited pattern '{pattern}'.")
                raise ValueError(f"Path '{relative_path_str}' (name: {resolved_path.name}) matches a prohibited pattern.")

        # Security Check 3: Check for blocked file extensions.
        if resolved_path.suffix and resolved_path.suffix.lower() in self.blocked_extensions:
            self.logger.warning(f"Path validation failed: Path '{relative_path_str}' has blocked extension '{resolved_path.suffix}'.")
            raise ValueError(f"Path '{relative_path_str}' has a blocked extension: {resolved_path.suffix}")
            
        # Path traversal check (double check, resolve should handle most)
        if ".." in str(prospective_path): # Check the user input before resolution too
             self.logger.warning(f"Path validation failed: Path traversal '..' detected in input '{prospective_path}'.")
             raise ValueError("Path traversal attempt detected ('..').")

        self.logger.debug(f"Path validation successful for '{relative_path_str}'. Resolved to: {resolved_path}")
        return resolved_path

    def _execute_direct(self, parameters: Dict[str, Any]) -> ExecutionResult:
        """
        Execute file operation based on parameters
        
        Args:
            parameters: Dictionary containing operation details
            
        Returns:
            Execution result
        """
        self.logger.info(f"Executing FileTool direct operation with parameters: {parameters}")
        self.usage_stats["total_operations"] += 1
        try:
            # Parse operation
            operation = FileOperation(parameters["operation"])
            self.logger.debug(f"Parsed operation: {operation.value}")
            
            # Common parameters
            path = parameters.get("path") # Path might be None for some ops, handled by specific handlers
            
            # Execute operation
            result: ExecutionResult
            if operation == FileOperation.READ:
                result = self._handle_read(parameters)
            elif operation == FileOperation.WRITE:
                result = self._handle_write(parameters)
            elif operation == FileOperation.DELETE:
                result = self._handle_delete(parameters)
            elif operation == FileOperation.LIST:
                result = self._handle_list(parameters)
            elif operation == FileOperation.CREATE:
                result = self._handle_create(parameters)
            elif operation == FileOperation.SEARCH:
                result = self._handle_search(parameters) # Remains simulated as per focus
            else:
                # Unknown operation
                self.logger.error(f"Unsupported operation requested: {operation.value}")
                result = ExecutionResult(
                    tool_name=self.metadata.name,
                    success=False,
                    output=None,
                    error=f"Unsupported operation: {operation.value}"
                )
            
            if result.success:
                self.usage_stats["successful_operations"] += 1
                self.logger.info(f"FileTool operation '{operation.value}' successful. Output: {result.output}")
            else:
                self.usage_stats["failed_operations"] += 1
                self.logger.warning(f"FileTool operation '{operation.value}' failed. Error: {result.error}")
            return result
            
        except ValueError as ve: # Catch validation errors specifically
            self.logger.warning(f"Validation error during FileTool execution: {str(ve)}", exc_info=True)
            self.usage_stats["failed_operations"] += 1
            return ExecutionResult(
                tool_name=self.metadata.name,
                success=False,
                output=None,
                error=f"Validation Error: {str(ve)}"
            )
        except FileNotFoundError as fnf:
            self.logger.warning(f"FileNotFoundError during FileTool execution: {str(fnf)}", exc_info=True)
            self.usage_stats["failed_operations"] += 1
            return ExecutionResult(
                tool_name=self.metadata.name,
                success=False,
                output=None,
                error=f"File Not Found: {str(fnf)}"
            )
        except PermissionError as pe:
            self.logger.warning(f"PermissionError during FileTool execution: {str(pe)}", exc_info=True)
            self.usage_stats["failed_operations"] += 1
            return ExecutionResult(
                tool_name=self.metadata.name,
                success=False,
                output=None,
                error=f"Permission Denied: {str(pe)}"
            )
        except Exception as e:
            self.logger.error(f"Unexpected error during FileTool execution: {str(e)}", exc_info=True)
            self.usage_stats["failed_operations"] += 1
            return ExecutionResult(
                tool_name=self.metadata.name,
                success=False,
                output=None,
                error=f"An unexpected error occurred: {str(e)}"
            )

    def _handle_read(self, params: Dict[str, Any]) -> ExecutionResult:
        """
        Handle file read operation
        Args:
            params: Operation parameters (must include "path")
        Returns:
            Execution result
        """
        self.logger.info(f"Handling READ operation for params: {params}")
        relative_path_str = params["path"]
        validated_path = self._validate_path(relative_path_str)
        self.logger.debug(f"Read operation for validated path: {validated_path}")

        if not validated_path.exists():
            self.logger.warning(f"Read failed: File not found at '{validated_path}' (original: '{relative_path_str}').")
            raise FileNotFoundError(f"File not found: {relative_path_str}")
        if not validated_path.is_file():
            self.logger.warning(f"Read failed: Path '{validated_path}' is not a file.")
            raise ValueError(f"Path is not a file: {relative_path_str}")

        try:
            content = validated_path.read_text(encoding="utf-8")
            self.logger.debug(f"Successfully read {len(content)} characters from '{validated_path}'.")
        except UnicodeDecodeError:
            self.logger.error(f"Read failed: Could not decode file '{validated_path}' as UTF-8.", exc_info=True)
            # Fallback for binary or non-UTF-8 files; could return bytes or error
            # For simplicity, we'll error here. A more robust tool might try other encodings or return bytes.
            raise ValueError(f"Could not decode file {relative_path_str} as UTF-8. Binary file or wrong encoding.")
        
        lines = content.splitlines()
        line_count = len(lines)

        start_line = params.get("start_line")
        end_line = params.get("end_line")
        self.logger.debug(f"Requested line range: start={start_line}, end={end_line}. Total lines: {line_count}")

        if start_line is not None or end_line is not None:
            start = int(start_line) -1 if start_line is not None else 0 # 1-indexed to 0-indexed
            end = int(end_line) if end_line is not None else line_count
            
            start = max(0, start)
            end = min(line_count, end)
            
            if start >= end :
                 content_slice = ""
                 self.logger.debug(f"Empty slice requested (start {start} >= end {end}).")
            else:
                 content_slice = "\n".join(lines[start:end])
                 self.logger.debug(f"Sliced content from line {start+1} to {end}. Length: {len(content_slice)} chars.")
        else:
            content_slice = content
            self.logger.debug("No slicing requested, returning full content.")
            
        return ExecutionResult(
            tool_name=self.metadata.name,
            success=True,
            output={
                "path": relative_path_str,
                "content": content_slice,
                "size": validated_path.stat().st_size, # Actual size
                "total_lines": line_count, # Total lines in original file
                "retrieved_lines": len(content_slice.splitlines()) if content_slice else 0
            }
        )

    def _handle_write(self, params: Dict[str, Any]) -> ExecutionResult:
        """
        Handle file write operation
        
        Args:
            params: Operation parameters (must include "path", "content")
        Returns:
            Execution result
        """
        self.logger.info(f"Handling WRITE operation for params: {params.get('path')}, content length: {len(params.get('content', ''))}")
        relative_path_str = params["path"]
        content = params["content"]
        # mode = params.get("mode", "w") # 'w' for overwrite/create, 'a' for append

        validated_path = self._validate_path(relative_path_str)
        self.logger.debug(f"Write operation for validated path: {validated_path}")

        # Check extension against allowed_extensions_for_write
        if validated_path.suffix.lower() not in self.allowed_extensions_for_write:
            self.logger.warning(f"Write failed: File extension '{validated_path.suffix}' not allowed. Allowed: {self.allowed_extensions_for_write}")
            raise ValueError(f"File extension {validated_path.suffix} is not allowed for writing. Allowed: {self.allowed_extensions_for_write}")

        # Validate content size (UTF-8 encoded size)
        content_bytes = content.encode('utf-8')
        if len(content_bytes) > self.max_file_size:
            self.logger.warning(f"Write failed: Content size {len(content_bytes)} bytes exceeds max {self.max_file_size} bytes.")
            raise ValueError(f"Content size ({len(content_bytes)} bytes) exceeds maximum allowed size ({self.max_file_size} bytes).")

        # Ensure parent directory exists
        parent_dir = validated_path.parent
        if not parent_dir.exists():
            self.logger.info(f"Parent directory '{parent_dir}' does not exist, attempting to create.")
            # This check ensures we are not creating directories outside sandbox implicitly
            # _validate_path should have already confirmed parent_dir is within sandbox if it were user-provided
            # Here, we are creating it if it's part of a valid path.
            try:
                parent_dir.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"Parent directory '{parent_dir}' created successfully.")
            except Exception as e:
                self.logger.error(f"Write failed: Could not create parent directory '{parent_dir}': {e}", exc_info=True)
                raise ValueError(f"Could not create parent directory {parent_dir}: {e}")
        elif not parent_dir.is_dir():
            self.logger.warning(f"Write failed: Parent path '{parent_dir}' is not a directory.")
            raise ValueError(f"Parent path {parent_dir} is not a directory.")

        # Actual file write
        validated_path.write_text(content, encoding="utf-8")
        self.logger.info(f"Successfully wrote {len(content_bytes)} bytes to '{validated_path}'.")
        
        return ExecutionResult(
            tool_name=self.metadata.name,
            success=True,
            output={
                "path": relative_path_str,
                "written_bytes": len(content_bytes),
                "message": f"File '{relative_path_str}' written successfully."
            }
        )

    def _handle_delete(self, params: Dict[str, Any]) -> ExecutionResult:
        """
        Handle file delete operation
        
        Args:
            params: Operation parameters (must include "path")
        Returns:
            Execution result
        """
        self.logger.info(f"Handling DELETE operation for params: {params}")
        relative_path_str = params["path"]
        validated_path = self._validate_path(relative_path_str)
        self.logger.debug(f"Delete operation for validated path: {validated_path}")

        if not validated_path.exists():
            self.logger.warning(f"Delete failed: File or directory not found at '{validated_path}'.")
            raise FileNotFoundError(f"File or directory not found: {relative_path_str}")
        
        if not validated_path.is_file(): # Assuming delete operation is for files only
            self.logger.warning(f"Delete failed: Path '{validated_path}' is not a file.")
            raise ValueError(f"Path is not a file, cannot delete: {relative_path_str}. For directory deletion, use a different operation if available.")

        # Validate deletion permissions against read_only_paths (using relative path)
        if not self._validate_deletion(relative_path_str):
            self.logger.warning(f"Delete failed: Deletion not allowed for '{relative_path_str}' (read-only).")
            raise PermissionError(f"Deletion not allowed for '{relative_path_str}' due to read-only restrictions.")
            
        validated_path.unlink() # Deletes the file
        self.logger.info(f"Successfully deleted file '{validated_path}'.")
        
        return ExecutionResult(
            tool_name=self.metadata.name,
            success=True,
            output={
                "path": relative_path_str,
                "message": f"File '{relative_path_str}' deleted successfully.",
                "deleted_at": datetime.now().isoformat()
            }
        )

    def _handle_list(self, params: Dict[str, Any]) -> ExecutionResult:
        """
        Handle file list operation
        
        Args:
            params: Operation parameters (optional "path", defaults to sandbox root)
        Returns:
            Execution result
        """
        self.logger.info(f"Handling LIST operation for params: {params}")
        relative_dir_str = params.get("path", ".") # Default to current sandbox directory
        validated_dir_path = self._validate_path(relative_dir_str)
        self.logger.debug(f"List operation for validated directory path: {validated_dir_path}")

        if not validated_dir_path.exists():
            self.logger.warning(f"List failed: Directory not found at '{validated_dir_path}'.")
            raise FileNotFoundError(f"Directory not found: {relative_dir_str}")
        if not validated_dir_path.is_dir():
            self.logger.warning(f"List failed: Path '{validated_dir_path}' is not a directory.")
            raise ValueError(f"Path is not a directory: {relative_dir_str}")

        items = []
        self.logger.debug(f"Iterating directory: {validated_dir_path}")
        for item_path in validated_dir_path.iterdir():
            # Further validation for each item path to ensure it's also within sandbox (should be by iterdir)
            # and not a blocked extension if we were to operate on it. For listing, just name and type is fine.
            try:
                # self._validate_path(str(item_path.relative_to(self.sandbox_root))) # Optional: validate each item
                item_stat = item_path.stat()
                item_info = {
                    "name": item_path.name,
                    "type": "directory" if item_path.is_dir() else "file",
                    "size": item_stat.st_size if item_path.is_file() else None,
                    "modified_at": datetime.fromtimestamp(item_stat.st_mtime).isoformat()
                }
                items.append(item_info)
                self.logger.debug(f"Listed item: {item_info}")
            except Exception as e:
                self.logger.warning(f"Could not stat or process item '{item_path.name}' during list: {e}", exc_info=True)
                # Skip items that can't be stat'd or fail validation if strict listing is on
                items.append({"name": item_path.name, "type": "unknown/inaccessible", "error": str(e)})

        self.logger.info(f"List operation successful for '{relative_dir_str}'. Found {len(items)} items.")
        return ExecutionResult(
            tool_name=self.metadata.name,
            success=True,
            output={
                "path": relative_dir_str,
                "items": items
            }
        )
        
    def _handle_create(self, params: Dict[str, Any]) -> ExecutionResult:
        """
        Handle file creation operation (creates an empty file).
        Args:
            params: Operation parameters (must include "path")
        Returns:
            Execution result
        """
        self.logger.info(f"Handling CREATE operation for params: {params}")
        relative_path_str = params["path"]
        validated_path = self._validate_path(relative_path_str)
        self.logger.debug(f"Create operation for validated path: {validated_path}")

        if validated_path.exists():
            self.logger.warning(f"Create failed: File or directory already exists at '{validated_path}'.")
            raise ValueError(f"File or directory already exists at '{relative_path_str}'. Cannot create.")

        # Check extension against allowed_extensions_for_write
        if validated_path.suffix.lower() not in self.allowed_extensions_for_write:
            self.logger.warning(f"Create failed: File extension '{validated_path.suffix}' not allowed. Allowed: {self.allowed_extensions_for_write}")
            raise ValueError(f"File extension {validated_path.suffix} is not allowed for creation. Allowed: {self.allowed_extensions_for_write}")

        # Ensure parent directory exists
        parent_dir = validated_path.parent
        if not parent_dir.exists():
            self.logger.info(f"Parent directory '{parent_dir}' for create does not exist, attempting to create.")
            try:
                parent_dir.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"Parent directory '{parent_dir}' created successfully for create.")
            except Exception as e:
                self.logger.error(f"Create failed: Could not create parent directory '{parent_dir}': {e}", exc_info=True)
                raise ValueError(f"Could not create parent directory {parent_dir}: {e}")
        elif not parent_dir.is_dir():
            self.logger.warning(f"Create failed: Parent path '{parent_dir}' is not a directory.")
            raise ValueError(f"Parent path {parent_dir} is not a directory.")
        
        # Create the empty file
        try:
            validated_path.touch(exist_ok=False) # exist_ok=False to ensure it's new
            self.logger.info(f"Successfully created empty file at '{validated_path}'.")
        except FileExistsError: # Should be caught by pre-check, but as a safeguard
             self.logger.warning(f"Create failed: File already exists at '{validated_path}' (race condition?).")
             raise ValueError(f"File already exists at '{relative_path_str}'. Cannot create.")


        return ExecutionResult(
            tool_name=self.metadata.name,
            success=True,
            output={
                "path": relative_path_str,
                "message": f"File '{relative_path_str}' created successfully.",
                "created_at": datetime.fromtimestamp(validated_path.stat().st_ctime).isoformat()
            }
        )

    def _handle_search(self, params: Dict[str, Any]) -> ExecutionResult:
        """
        Handle file search operation
        
        Args:
            params: Operation parameters
            
        Returns:
            Execution result
        """
        self.logger.info(f"Handling SEARCH operation for params: {params}")
        # Extract parameters
        pattern = params["pattern"]
        path_param = params.get("path") # User provided path or None
        
        # Determine search base path: if user provides a path, validate it. Otherwise, use sandbox_root.
        if path_param:
            search_base_path_str = path_param
            # _validate_path expects a relative path from sandbox_root, or an absolute path that will be checked.
            # If user gives 'my_subdir', it becomes sandbox_root/my_subdir.
            # If user gives '/sandbox/files/my_subdir', it's fine.
            # If user gives '/etc', it will be rejected by _validate_path.
            # For search, the path is the directory to search IN.
            validated_search_dir = self._validate_path(search_base_path_str)
            if not validated_search_dir.is_dir():
                self.logger.warning(f"Search path '{search_base_path_str}' is not a directory.")
                raise ValueError(f"Search path '{search_base_path_str}' is not a directory.")
            search_root_display = search_base_path_str # For output, use what user provided if valid
        else:
            # If no path is given, default to searching the entire sandbox_root
            validated_search_dir = Path(self.sandbox_root) # Already validated at init
            search_root_display = "." # Representing sandbox root relative
            self.logger.debug(f"No search path provided, defaulting to sandbox root: {self.sandbox_root}")

        self.logger.info(f"Simulating search for pattern '{pattern}' in directory '{validated_search_dir}'")
            
        # Simulate search results
        # In a real implementation, this would walk validated_search_dir, read files, and apply regex.
        # For now, it's a placeholder.
        simulated_results = []
        # Example: iterate through validated_search_dir, for each file, read and search.
        # This is complex, so keeping it simple as per "Remains simulated as per focus"
        if "example" in pattern.lower() and validated_search_dir.joinpath("example.txt").exists():
             simulated_results.append({
                 "file": str(validated_search_dir.joinpath("example.txt").relative_to(self.sandbox_root)), # Path relative to sandbox
                 "matches": [{"line": 10, "text": f"... text matching {pattern} ..."}]
             })

        return ExecutionResult(
            tool_name=self.metadata.name,
            success=True,
            output={
                "path": search_root_display, # The path user specified or "." for sandbox root
                "pattern": pattern,
                "results": simulated_results,
                "message": f"Search for '{pattern}' in '{search_root_display}' (simulated). Found {len(simulated_results)} files."
            }
        )

    def set_sandbox_config(self,
                             max_file_size: Optional[int] = None,
                             allowed_extensions_for_write: Optional[List[str]] = None,
                             blocked_extensions: Optional[List[str]] = None,
                             read_only_paths: Optional[List[str]] = None,
                             allowed_directories: Optional[List[str]] = None,
                             sandbox_root: Optional[str] = None) -> None:
        """
        Configure sandbox settings for file operations.
        Paths in allowed_directories should be absolute.
        read_only_paths are relative to the sandbox_root.
        """
        self.logger.info("Updating FileTool sandbox configuration.")
        if max_file_size is not None:
            self.logger.debug(f"Setting max_file_size to {max_file_size}")
            self.max_file_size = max_file_size
        if allowed_extensions_for_write is not None:
            self.allowed_extensions_for_write = [ext.lower() for ext in allowed_extensions_for_write]
            self.logger.debug(f"Setting allowed_extensions_for_write to {self.allowed_extensions_for_write}")
        if blocked_extensions is not None:
            self.blocked_extensions = [ext.lower() for ext in blocked_extensions]
            self.logger.debug(f"Setting blocked_extensions to {self.blocked_extensions}")
        if read_only_paths is not None:
            self.read_only_paths = read_only_paths
            self.logger.debug(f"Setting read_only_paths to {self.read_only_paths}")
        
        if sandbox_root is not None:
            old_sandbox_root = self.sandbox_root
            self.sandbox_root = str(Path(sandbox_root).resolve())
            Path(self.sandbox_root).mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Sandbox root changed from '{old_sandbox_root}' to '{self.sandbox_root}'")
            # If sandbox_root changes, allowed_directories might need update if it was solely based on old root
            if not allowed_directories: # If allowed_directories is not being set, update it to new root
                 self.allowed_directories = [self.sandbox_root]
                 self.logger.debug(f"allowed_directories reset to new sandbox_root: {self.allowed_directories}")


        if allowed_directories is not None:
            self.allowed_directories = [str(Path(p).resolve()) for p in allowed_directories]
            self.logger.debug(f"Setting allowed_directories to {self.allowed_directories}")
            # Ensure the current sandbox_root is itself an allowed directory or within one
            is_sandbox_root_allowed = any(
                self.sandbox_root.startswith(str(Path(ad).resolve())) for ad in self.allowed_directories
            )
            if not is_sandbox_root_allowed and self.sandbox_root not in self.allowed_directories:
                 # Add current sandbox_root if not covered by the new allowed_directories
                 self.allowed_directories.append(self.sandbox_root)
                 self.logger.info(f"Current sandbox_root '{self.sandbox_root}' added to allowed_directories.")
        self.logger.info("FileTool sandbox configuration updated.")

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for file operations"""
        self.logger.debug("Retrieving usage stats.")
        return self.usage_stats

    def reset_usage_stats(self) -> None:
        """Reset usage statistics"""
        self.logger.info("Resetting usage statistics.")
        self.usage_stats = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "last_reset": datetime.now().isoformat()
        }
        self.logger.debug(f"Usage stats reset. New stats: {self.usage_stats}")

    def get_file_stats(self, path: str) -> Dict[str, Any]:
        """
        Get statistics for a file
        
        Args:
            path: Path to get stats for
            
        Returns:
            Dictionary with file statistics
        """
        self.logger.info(f"Getting file stats for path: {path}")
        try:
            validated_path = self._validate_path(path) # Validate path first
            if not validated_path.exists():
                self.logger.warning(f"File stats: Path '{path}' does not exist.")
                return {"path": path, "exists": False, "error": "Path does not exist."}

            stat_info = validated_path.stat()
            stats = {
                "path": path, # Return user-provided relative path
                "absolute_path": str(validated_path),
                "exists": True,
                "is_directory": validated_path.is_dir(),
                "is_file": validated_path.is_file(),
                "size": stat_info.st_size,
                "modified_at": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                "created_at": datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
                "accessed_at": datetime.fromtimestamp(stat_info.st_atime).isoformat(),
            }
            self.logger.debug(f"File stats for '{path}': {stats}")
            return stats
        except ValueError as ve:
            self.logger.error(f"Error getting file stats for '{path}' (validation failed): {ve}", exc_info=True)
            return {"path": path, "exists": False, "error": f"Validation Error: {str(ve)}"}
        except Exception as e:
            self.logger.error(f"Error getting file stats for '{path}': {e}", exc_info=True)
            return {"path": path, "exists": False, "error": f"Unexpected error: {str(e)}"}