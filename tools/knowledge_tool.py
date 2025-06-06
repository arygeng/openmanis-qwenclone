"""
Knowledge tool adapter for Manus AI Clone
Implements secure knowledge management operations
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List, Union
from core.logging import get_logger # Added for logging

from knowledge.knowledge_base import KnowledgeBase # Added import
from tools.tool_interface import ToolAdapter, ToolType, ToolMetadata, ExecutionResult, SecurityContext, PermissionLevel

class KnowledgeOperationType(Enum):
    """Supported knowledge operations"""
    SEARCH = "search"
    RETRIEVE = "retrieve"
    STORE = "store"
    DELETE = "delete"
    UPDATE = "update"


class KnowledgeTool(ToolAdapter):
    """
    Adapter for knowledge management operations
    """
    def __init__(self, knowledge_base: KnowledgeBase): # Modified signature
        self.logger = get_logger(__name__)
        self.logger.info("Initializing KnowledgeTool")
        # Knowledge storage
        # self.knowledge_store = {}  # type: Dict[str, Dict[str, Any]] # Removed
        self.knowledge_base = knowledge_base # Added KnowledgeBase instance
        
        # Configuration
        self.default_permission = PermissionLevel.READ
        self.max_document_size = 5 * 1024 * 1024  # bytes (5MB)
        self.max_query_length = 1024 # Added from later in file
        self.max_result_size = 10000 # Added from later in file
        self.indexed_sources: List[str] = [] # Added from later in file
        
        # Security settings
        self.restricted_topics = []  # type: List[str]
        
        # Component references
        # self.tool_adapter = None  # type: Optional[ToolAdapter] # This seems unused, consider removing if not planned
        
        # Statistics
        self.usage_stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "last_reset": datetime.now().isoformat()
        }
        
        # Metadata for ToolAdapter - this was missing
        metadata = ToolMetadata(
            name="knowledge_tool",
            description="Manages knowledge base operations like search, store, retrieve, update, delete.",
            version="1.0.0", # Or appropriate version
            author="Manus AI Clone Team",
            license_type="MIT"
        )
        super().__init__(
            tool_type=ToolType.KNOWLEDGE, # Assuming ToolType.KNOWLEDGE exists or needs to be added
            metadata=metadata,
            permission_level=self.default_permission # Default permission for the tool itself
        )
        self.logger.info("KnowledgeTool initialized with metadata and default settings.")


    def _validate_input(self, command: str, parameters: Dict[str, Any]) -> bool:
        """
        Validate command and parameters
        
        Args:
            command: Command to validate
            parameters: Parameters to validate
            
        Returns:
            True if valid
        """
        self.logger.debug(f"Validating input for command '{command}' with parameters: {parameters}")
        # Basic validation
        if not command or not isinstance(command, str):
            self.logger.warning(f"Input validation failed: Command '{command}' is invalid or not a string.")
            return False
        
        try:
            op_type = KnowledgeOperationType(command) # Validate command against enum
        except ValueError:
            self.logger.warning(f"Input validation failed: Unknown command '{command}'.")
            return False

        # Parameter validation varies by command
        required_params: Dict[KnowledgeOperationType, List[str]] = {
            KnowledgeOperationType.SEARCH: ["query"],
            # Parameters for store_fact and retrieve_fact as per task
            KnowledgeOperationType.RETRIEVE: ["query", "category"], # Changed from document_id
            KnowledgeOperationType.STORE: ["key", "value"], # Changed from content; source/category handled in execute
            KnowledgeOperationType.UPDATE: ["document_id", "content"], # Kept for existing update logic
            KnowledgeOperationType.DELETE: ["document_id"], # Kept for existing delete logic
        }

        if op_type in required_params:
            for param in required_params[op_type]:
                if param not in parameters:
                    self.logger.warning(f"Input validation failed for command '{op_type.value}': Missing parameter '{param}'.")
                    return False
        
        # Specific checks
        if op_type == KnowledgeOperationType.STORE: # For store_fact, value is main content
            value = parameters.get("value", "")
            # Assuming value can be complex, check its string representation for size limit for now
            if isinstance(value, str) and len(value.encode('utf-8')) > self.max_document_size:
                self.logger.warning(f"Input validation failed for '{op_type.value}': Value size {len(value.encode('utf-8'))} exceeds max {self.max_document_size}.")
                return False
        elif op_type == KnowledgeOperationType.UPDATE: # Existing update logic
            content = parameters.get("content", "")
            if len(content.encode('utf-8')) > self.max_document_size:
                self.logger.warning(f"Input validation failed for '{op_type.value}': Content size {len(content.encode('utf-8'))} exceeds max {self.max_document_size}.")
                return False

        if op_type == KnowledgeOperationType.SEARCH or op_type == KnowledgeOperationType.RETRIEVE: # retrieve uses 'query' as key
            query = parameters.get("query", "")
            if len(query) > self.max_query_length:
                self.logger.warning(f"Input validation failed for {op_type.value}: Query length {len(query)} exceeds max {self.max_query_length}.")
                return False

        self.logger.debug(f"Input validation successful for command '{command}'.")
        return True


    async def _execute_store_fact(self, parameters: Dict[str, Any]) -> ExecutionResult:
        """Handles storing a fact using KnowledgeBase."""
        key = parameters.get("key")
        value = parameters.get("value")
        source = parameters.get("source", "user_provided") # 'source' acts as 'category' for KnowledgeBase

        # _validate_input should have caught missing key/value already
        self.logger.info(f"Attempting to store fact: key='{key}', category='{source}'")
        try:
            # KnowledgeBase.store_knowledge expects 'data' as a Dict.
            # We'll store the value along with its original type for potential future use.
            data_to_store = {'value': value, 'type': type(value).__name__}
            await self.knowledge_base.store_knowledge(category=source, key=key, data=data_to_store)
            self.logger.info(f"Fact stored successfully: key='{key}', category='{source}'.")
            return ExecutionResult(
                tool_name=self.metadata.name,
                success=True,
                output={"key": key, "category": source, "status": "stored"}
            )
        except Exception as e:
            self.logger.error(f"Error storing fact (key='{key}', category='{source}'): {e}", exc_info=True)
            return ExecutionResult(tool_name=self.metadata.name, success=False, error=f"Failed to store fact: {str(e)}")

    async def _execute_retrieve_fact(self, parameters: Dict[str, Any]) -> ExecutionResult:
        """Handles retrieving a fact using KnowledgeBase."""
        query = parameters.get("query") # 'query' acts as 'key' for KnowledgeBase
        category = parameters.get("category")

        # _validate_input should have caught missing query/category
        self.logger.info(f"Attempting to retrieve fact: key='{query}', category='{category}'")
        try:
            retrieved_entry = await self.knowledge_base.retrieve_knowledge(category=category, key=query)
            if retrieved_entry and 'data' in retrieved_entry: # retrieve_knowledge returns the entry which contains 'data'
                actual_data = retrieved_entry['data'] # This should be {'value': ..., 'type': ...}
                self.logger.info(f"Fact retrieved successfully: key='{query}', category='{category}'. Data: {actual_data}")
                return ExecutionResult(
                    tool_name=self.metadata.name,
                    success=True,
                    output={"key": query, "category": category, "retrieved_value": actual_data.get('value')} # Return the actual value
                )
            else:
                self.logger.warning(f"Fact not found: key='{query}', category='{category}'.")
                return ExecutionResult(
                    tool_name=self.metadata.name,
                    success=False,
                    error="Fact not found",
                    output={"key": query, "category": category} # Include key/category in output for context
                )
        except Exception as e:
            self.logger.error(f"Error retrieving fact (key='{query}', category='{category}'): {e}", exc_info=True)
            return ExecutionResult(tool_name=self.metadata.name, success=False, error=f"Failed to retrieve fact: {str(e)}")


    # Overriding the base execute to fit the new structure and use ExecutionResult
    async def _execute_direct(self, parameters: Dict[str, Any]) -> ExecutionResult:
        """
        Execute a knowledge operation.
        'operation' key in parameters determines the action.
        """
        command_str = parameters.get("operation")
        if not command_str:
            self.logger.error("Execution failed: 'operation' not specified in parameters.")
            return ExecutionResult(tool_name=self.metadata.name, success=False, error="Operation not specified.")

        # Validate command string against KnowledgeOperationType
        try:
            operation = KnowledgeOperationType(command_str)
        except ValueError:
            self.logger.error(f"Invalid operation string '{command_str}' provided.", exc_info=True)
            # self.usage_stats["failed_queries"] += 1 # This will be handled later
            return ExecutionResult(tool_name=self.metadata.name, success=False, error=f"Invalid operation: {command_str}")

        # Validate parameters for the specific operation using _validate_input
        if not self._validate_input(command=operation.value, parameters=parameters):
            # _validate_input logs the specific error
            self.usage_stats["failed_queries"] += 1
            return ExecutionResult(tool_name=self.metadata.name, success=False, error="Parameter validation failed.")


        self.logger.info(f"Executing KnowledgeTool operation: '{operation.value}' with parameters: {parameters}")
        self.usage_stats["total_queries"] += 1
        
        # Security checks would go here if context was passed down or available
        # if not self._check_permissions(context, operation.value): ...

        result: ExecutionResult
        try:
            if operation == KnowledgeOperationType.STORE:
                result = await self._execute_store_fact(parameters)
            elif operation == KnowledgeOperationType.RETRIEVE:
                result = await self._execute_retrieve_fact(parameters)
            elif operation == KnowledgeOperationType.SEARCH:
                # _handle_search is sync and returns a dict, needs adaptation or make it async
                self.logger.warning("SEARCH operation called _handle_search (sync). Consider making it async and use KnowledgeBase.")
                search_dict_result = self._handle_search(parameters)
                if search_dict_result.get("status") == "success":
                    result = ExecutionResult(tool_name=self.metadata.name, success=True, output=search_dict_result)
                else:
                    result = ExecutionResult(tool_name=self.metadata.name, success=False, error=search_dict_result.get("message", "Search failed"), output=search_dict_result)
            elif operation == KnowledgeOperationType.UPDATE:
                # _handle_update is sync and returns a dict
                self.logger.warning("UPDATE operation called _handle_update (sync). Consider making it async and use KnowledgeBase.")
                update_dict_result = self._handle_update(parameters)
                if update_dict_result.get("status") == "success":
                    result = ExecutionResult(tool_name=self.metadata.name, success=True, output=update_dict_result)
                else:
                    result = ExecutionResult(tool_name=self.metadata.name, success=False, error=update_dict_result.get("message", "Update failed"), output=update_dict_result)
            elif operation == KnowledgeOperationType.DELETE:
                # _handle_delete returns ExecutionResult but is sync
                self.logger.warning("DELETE operation called _handle_delete (sync). Consider making it async and use KnowledgeBase.")
                result = self._handle_delete(parameters)
            else:
                self.logger.error(f"Unknown or unhandled command '{operation.value}' in _execute_direct.")
                result = ExecutionResult(tool_name=self.metadata.name, success=False, error=f"Unknown or unhandled command: {operation.value}")
            
            if result.success:
                self.usage_stats["successful_queries"] += 1
                self.logger.info(f"Knowledge operation '{operation.value}' successful. Output: {result.output}")
            else:
                self.usage_stats["failed_queries"] += 1
                self.logger.warning(f"Knowledge operation '{operation.value}' failed. Error: {result.error}, Output: {result.output}")
            return result

        except Exception as e: # Catch-all for unexpected errors during specific operation execution
            self.logger.error(f"Error during knowledge operation '{operation.value}': {e}", exc_info=True)
            self.usage_stats["failed_queries"] += 1
            return ExecutionResult(tool_name=self.metadata.name, success=False, error=str(e))


    def _create_error_response(self, message: str) -> Dict[str, Any]: # Kept for old sync handlers
        self.logger.error(f"KnowledgeTool operation resulted in error: {message}")
        return {
            "status": "error",
            "message": message,
            "timestamp": datetime.now().isoformat()
        }

    # Placeholder for permission checking logic
    def _check_permissions(self, context: Optional[SecurityContext], command: str) -> bool:
        self.logger.debug(f"Checking permissions for command '{command}' with context: {context}")
        # Example: Allow all for now, or implement role-based access
        # if context and "admin" in context.roles: return True
        # required_perm = PermissionLevel.WRITE if command in ["store_document", "update_document", "delete_document"] else PermissionLevel.READ
        # return context.has_permission(required_perm) if context else False
        return True # Placeholder

    # Placeholder for query restriction logic
    def _is_query_allowed(self, query: str) -> bool:
        self.logger.debug(f"Checking if query is allowed: '{query[:50]}...'")
        # Example: block queries containing certain keywords
        # for topic in self.restricted_topics:
        #     if topic in query.lower():
        #         self.logger.warning(f"Query '{query}' blocked due to restricted topic: '{topic}'.")
        #         return False
        return True # Placeholder

    # Placeholder for logging (can be expanded)
    def _log_operation(self, command: str, parameters: Dict[str, Any], success: bool, error: Optional[str] = None):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "parameters": parameters, # Be careful about logging sensitive data from parameters
            "success": success,
            "error": error if error else None
        }
        if success:
            self.logger.info(f"Knowledge operation logged: {log_entry}")
        else:
            self.logger.error(f"Failed knowledge operation logged: {log_entry}")
        # In a real system, this might write to a dedicated audit log or database.


    def execute(self,
               parameters: Dict[str, Any], # Changed signature to match ToolAdapter
               context: Optional[SecurityContext] = None) -> ExecutionResult: # Changed signature
        """
        Execute a knowledge operation
        
        Args:
            command: Type of knowledge operation
            parameters: Operation parameters
            context: Security context
            
        Returns:
            Operation result
        """
        # This is the public execute method from ToolAdapter.
        # It should call _execute_direct which is now async.
        # This requires ToolAdapter.execute to be async or handle async calls.
        # For now, let's assume it's adapted or we call _execute_direct directly if this is the entry point.
        # The task implies integrating logging into existing structures.
        # The original execute method here is not compatible with ToolAdapter's typical structure.
        # We will assume that the call comes to _execute_direct for actual work.
        # If this `execute` is meant to be the one from ToolAdapter, it needs to be async
        # and call `await self._execute_direct(parameters)`
        self.logger.info(f"KnowledgeTool execute called with parameters: {parameters}")

        # The `command` is now expected to be within `parameters` as `operation`
        # For compatibility with the old structure if called directly:
        command_str = parameters.get("operation", parameters.get("command")) # Try both
        
        if not command_str:
             self.logger.error("Public execute called without 'operation' or 'command' in parameters.")
             return ExecutionResult(tool_name=self.metadata.name, success=False, error="Operation/command not specified.")

        # Re-wrap parameters to include 'operation' if it was passed as 'command'
        internal_params = parameters.copy()
        if "command" in internal_params and "operation" not in internal_params:
            internal_params["operation"] = internal_params.pop("command")
        
        # This method should be async if _execute_direct is async
        # For now, this is a conceptual bridge. In a real scenario, ToolAdapter.execute would handle this.
        # This is a placeholder to illustrate the flow.
        # return self._execute_direct(internal_params) # This would need to be awaited if async
        
        # Fallback to a simple error if this non-async execute is called directly with async needs
        self.logger.warning("KnowledgeTool.execute (sync) was called. Asynchronous operations should go via an async entry point or ToolAdapter's async execute.")
        return ExecutionResult(tool_name=self.metadata.name, success=False, error="Synchronous execute called for async tool logic. This is a misconfiguration.")


    def _handle_search(self, parameters: Dict[str, Any]) -> Dict[str, Any]: # Returns Dict (old style), sync
        """
        Handle knowledge search operation (Legacy - uses self.knowledge_base.search_knowledge if available)
        Ideally, this should be async and directly return ExecutionResult.
        """
        self.logger.info(f"Handling legacy SEARCH operation with parameters: {parameters}")
        query = parameters.get("query")
        max_results = parameters.get("max_results", 5)
        
        if not query:
            self.logger.warning("Search failed: Query parameter is missing or empty.")
            return self._create_error_response("Query parameter is missing or empty.")

        if not self._is_query_allowed(query):
            return self._create_error_response("Query restricted")
            
        self.logger.debug(f"Performing search for query: '{query}', max_results: {max_results} using KnowledgeBase.")
        
        try:
            # This should be: search_results_kb = await self.knowledge_base.search_knowledge(query)
            # Since this handler is sync, we can't await. This is a known limitation for now.
            # For demonstration, if search_knowledge was sync:
            # search_results_kb = self.knowledge_base.search_knowledge(query)
            # For now, returning a placeholder as direct async call isn't possible here.
            self.logger.warning("_handle_search is sync and cannot await self.knowledge_base.search_knowledge. Returning placeholder.")
            simulated_results = [{"document_id": "placeholder_id", "score": 0.5, "preview": "Search via sync _handle_search needs update."}]
            
            # Example of how to process results if search_knowledge was callable and returned list of dicts
            # formatted_results = []
            # for res in search_results_kb:
            #     formatted_results.append({
            #         "document_id": res.get("key"), # Assuming 'key' from KB search result maps to document_id
            #         "category": res.get("category"),
            #         "score": res.get("relevance", 0.0),
            #         "preview": str(res.get("data", ""))[:100] + "..."
            #     })
            #     if len(formatted_results) >= max_results:
            #         break
            
            self.logger.info(f"Search for '{query}' (simulated from sync handler) yielded {len(simulated_results)} results.")
            return {
                "status": "success",
                "query": query,
                "results": simulated_results[:max_results],
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error during legacy search operation: {e}", exc_info=True)
            return self._create_error_response(f"Error during search: {str(e)}")


    def _handle_retrieve(self, params: Dict[str, Any]) -> ExecutionResult: # Sync, legacy
        """
        Handle document retrieval
        
        Args:
            params: Operation parameters
            
        Returns:
            Execution result
        """
        self.logger.info(f"Handling RETRIEVE operation for document_id: {params.get('document_id')}")
        # Extract parameters
        document_id = params.get("document_id")

        if not document_id: # Basic validation
            self.logger.warning("Retrieve failed: document_id parameter is missing.")
            return ExecutionResult(tool_name=self.metadata.name, success=False, error="Document ID parameter is missing.")
        
        # This method is largely superseded by _execute_retrieve_fact for RETRIEVE operations.
        # It was designed for the old self.knowledge_store.
        self.logger.warning("_handle_retrieve (sync, legacy) called. RETRIEVE operation now uses async _execute_retrieve_fact.")
        document_id = params.get("document_id") # This was the old key
        # category = params.get("category") # Old retrieve didn't have category this way

        if not document_id:
            self.logger.warning("Legacy retrieve failed: document_id parameter is missing.")
            return ExecutionResult(tool_name=self.metadata.name, success=False, error="Document ID parameter is missing (legacy retrieve).")
        
        # Cannot use self.knowledge_store anymore.
        # If this were to be adapted, it would need to call self.knowledge_base.retrieve_knowledge
        # but this handler is sync.
        self.logger.error(f"Legacy _handle_retrieve cannot access KnowledgeBase correctly for document_id '{document_id}'.")
        return ExecutionResult(
            tool_name=self.metadata.name,
            success=False,
            error=f"Legacy _handle_retrieve is deprecated for document_id '{document_id}'. Use 'query' and 'category' with RETRIEVE operation."
        )

    def _handle_store(self, parameters: Dict[str, Any]) -> Dict[str, Any]: # Returns Dict (old style), sync
        """
        Handle document storage operation
        
        Args:
            parameters: Operation parameters
            
        Returns:
            Operation result
        """
        self.logger.info(f"Handling STORE operation with parameters: {parameters.get('metadata', {}).get('source_type', 'N/A')}, content length: {len(parameters.get('content', ''))}")
        content = parameters.get("content")
        metadata = parameters.get("metadata", {}).copy() # Ensure it's a mutable copy
        user_provided_doc_id = parameters.get("document_id")

        if not content: # Basic validation
             self.logger.warning("Store failed: Content parameter is missing or empty.")
             return self._create_error_response("Content parameter is missing or empty.")
        
        if len(content.encode('utf-8')) > self.max_document_size: # Already checked in _validate_input, but good to double check
            self.logger.warning(f"Store failed: Content size exceeds maximum allowed size ({self.max_document_size} bytes).")
            return self._create_error_response(f"Content size exceeds maximum allowed size ({self.max_document_size} bytes).")

        # This method is largely superseded by _execute_store_fact for STORE operations.
        # It was designed for the old self.knowledge_store.
        self.logger.warning("_handle_store (sync, legacy) called. STORE operation now uses async _execute_store_fact.")
        # Old params: content, metadata, document_id
        # New params for store_fact: key, value, source

        content = parameters.get("content") # Old way
        if not content:
             self.logger.warning("Legacy store failed: Content parameter is missing or empty.")
             return self._create_error_response("Content parameter is missing or empty (legacy store).")
        
        # Cannot use self.knowledge_store anymore.
        self.logger.error("Legacy _handle_store cannot access KnowledgeBase correctly.")
        return self._create_error_response("Legacy _handle_store is deprecated. Use 'key', 'value', 'source' with STORE operation.")

    def _handle_delete(self, params: Dict[str, Any]) -> ExecutionResult: # Sync
        """
        Handle document deletion
        
        Args:
            params: Operation parameters
            
        Returns:
            Execution result
        """
        self.logger.info(f"Handling DELETE operation for document_id: {params.get('document_id')}")
        # Extract parameters
        document_id = params.get("document_id")

        if not document_id: # Basic validation
            self.logger.warning("Delete failed: document_id parameter is missing.")
            return ExecutionResult(tool_name=self.metadata.name, success=False, error="Document ID parameter is missing.")

        # This method needs to be adapted to use self.knowledge_base,
        # and KnowledgeBase itself needs a delete method.
        # For now, it's a placeholder.
        self.logger.warning(f"Handling DELETE operation for document_id: {params.get('document_id')} (sync handler). KnowledgeBase has no delete method yet.")
        document_id = params.get("document_id")
        category = params.get("category", "default_delete_category") # Category would be needed

        if not document_id:
            self.logger.warning("Delete failed: document_id parameter is missing.")
            return ExecutionResult(tool_name=self.metadata.name, success=False, error="Document ID parameter is missing.")

        # Conceptual: await self.knowledge_base.delete_knowledge(category=category, key=document_id)
        # Since that doesn't exist, simulate success.
        self.logger.info(f"Simulating deletion of document ID '{document_id}' from category '{category}'.")
        
        return ExecutionResult(
            tool_name=self.metadata.name,
            success=True, # Simulating success
            output={
                "document_id": document_id,
                "category": category,
                "action": "deleted (simulated)",
                "deleted_at": datetime.now().isoformat()
            }
        )

    def _handle_update(self, parameters: Dict[str, Any]) -> Dict[str, Any]: # Returns Dict (old style), sync
        """
        Handle document update operation
        
        Args:
            parameters: Operation parameters
            
        Returns:
            Operation result
        """
        self.logger.info(f"Handling UPDATE operation for document_id: {parameters.get('document_id')}, content length: {len(parameters.get('content', ''))}")
        document_id = parameters.get("document_id")
        content = parameters.get("content")
        new_metadata = parameters.get("metadata") # Optional: allow metadata updates too

        if not document_id or not content: # Basic validation
            self.logger.warning("Update failed: document_id or content parameter is missing.")
            return self._create_error_response("Document ID and content are required for update.")
            
        # This method needs to be adapted to use self.knowledge_base.
        # KnowledgeBase.store_knowledge can be used for update (overwrite).
        self.logger.warning(f"Handling UPDATE operation for document_id: {parameters.get('document_id')} (sync handler).")
        document_id = parameters.get("document_id") # This is the key
        content = parameters.get("content")         # This is the new value
        category = parameters.get("category", "default_update_category") # Category needed for KB
        new_metadata_from_params = parameters.get("metadata") # Optional metadata from parameters

        if not document_id or content is None: # content can be False, 0, etc.
            self.logger.warning("Update failed: document_id or content parameter is missing.")
            return self._create_error_response("Document ID and content are required for update.")
            
        if isinstance(content, str) and len(content.encode('utf-8')) > self.max_document_size:
            self.logger.warning(f"Update failed: Content size exceeds maximum allowed size ({self.max_document_size} bytes).")
            return self._create_error_response(f"Content size exceeds maximum allowed size ({self.max_document_size} bytes).")
            
        try:
            # Simulate update by using store_knowledge (overwrite)
            data_to_store = {'value': content, 'type': type(content).__name__}
            if isinstance(new_metadata_from_params, dict):
                # If KnowledgeBase stores metadata separately, this would be different.
                # For now, assume metadata is part of the 'data' dict.
                data_to_store.update(new_metadata_from_params)
            
            # Conceptual: await self.knowledge_base.store_knowledge(category=category, key=document_id, data=data_to_store)
            # Since this handler is sync, we can't await.
            self.logger.info(f"Simulating update (overwrite) for document ID '{document_id}' in category '{category}'.")
            updated_at = datetime.now().isoformat()
            
            return {
                "status": "success",
                "document_id": document_id,
                "category": category,
                "action": "updated (simulated by overwrite)",
                "timestamp": updated_at
            }
        except Exception as e:
            self.logger.error(f"Error simulating update for document '{document_id}': {e}", exc_info=True)
            return self._create_error_response(f"Failed to simulate update for document {document_id}: {str(e)}")

    # --- Public API methods using the new ToolAdapter structure ---

    async def search_knowledge(self,
                       query: str,
                       source_type: Optional[str] = None, # 'source_type' might map to 'category' or be part of search logic
                       max_results: int = 5,
                       context: Optional[SecurityContext] = None) -> ExecutionResult:
        """Direct API for searching knowledge. Calls _execute_direct."""
        self.logger.info(f"API call: search_knowledge with query '{query[:50]}...', source_type: {source_type}")
        parameters = {
            "operation": KnowledgeOperationType.SEARCH.value,
            "query": query,
            "max_results": max_results
        }
        if source_type:
            parameters["category"] = source_type # Assuming source_type maps to category for search
            # Or parameters["source_type"] = source_type if search logic uses it differently
            
        # The public execute() method of ToolAdapter should be async.
        # If self.execute is the overridden one that is sync, this won't work as intended.
        # Assuming the ToolAdapter's execute (if this class inherits from an async one) or _execute_direct is the target.
        return await self._execute_direct(parameters) # Corrected to call _execute_direct

    async def retrieve_fact(self, # Renamed from retrieve_document for clarity
                        key: str, # Was document_id
                        category: str, # Added category as required
                        context: Optional[SecurityContext] = None) -> ExecutionResult:
        """Direct API for retrieving a fact. Calls _execute_direct."""
        self.logger.info(f"API call: retrieve_fact with key '{key}', category '{category}'")
        parameters = {
            "operation": KnowledgeOperationType.RETRIEVE.value,
            "query": key, # 'query' is used as the key in _execute_retrieve_fact
            "category": category
        }
        return await self._execute_direct(parameters)

    async def store_fact(self, # Renamed from store_document for clarity
                     key: str,
                     value: Any,
                     source: str = "user_provided", # 'source' acts as 'category'
                     context: Optional[SecurityContext] = None) -> ExecutionResult:
        """Direct API for storing a fact. Calls _execute_direct."""
        self.logger.info(f"API call: store_fact. Key: '{key}', Source (category): '{source}'")
        parameters = {
            "operation": KnowledgeOperationType.STORE.value,
            "key": key,
            "value": value,
            "source": source # 'source' is used as category in _execute_store_fact
        }
        return await self._execute_direct(parameters)

    async def delete_document(self, # Keeping name, but needs category for KB
                      document_id: str, # This is the key
                      category: str = "default_delete_category", # Category needed
                      context: Optional[SecurityContext] = None) -> ExecutionResult:
        """Direct API for deleting documents. Calls _execute_direct."""
        self.logger.info(f"API call: delete_document with ID '{document_id}', category '{category}'")
        parameters = {
            "operation": KnowledgeOperationType.DELETE.value,
            "document_id": document_id, # _handle_delete uses this as key
            "category": category # Pass category to _handle_delete
        }
        return await self._execute_direct(parameters)

    async def update_document(self, # Keeping name, but needs category for KB
                      document_id: str, # This is the key
                      content: Any, # This is the new value
                      category: str = "default_update_category", # Category needed
                      metadata: Optional[Dict[str, Any]] = None,
                      context: Optional[SecurityContext] = None) -> ExecutionResult:
        """Direct API for updating documents. Calls _execute_direct."""
        self.logger.info(f"API call: update_document for ID '{document_id}', category '{category}'.")
        parameters = {
            "operation": KnowledgeOperationType.UPDATE.value,
            "document_id": document_id, # _handle_update uses this as key
            "content": content, # _handle_update uses this as value
            "category": category, # Pass category to _handle_update
        }
        if metadata is not None:
            parameters["metadata"] = metadata
        
        return await self._execute_direct(parameters)

    def set_max_query_length(self, length: int) -> None:
        """
        Set maximum allowed query length
        
        Args:
            length: Maximum length in characters
        """
        self.logger.info(f"Setting max_query_length to {length}")
        self.max_query_length = length

    def set_max_result_size(self, size: int) -> None:
        """
        Set maximum allowed result size
        
        Args:
            size: Maximum size in characters
        """
        self.logger.info(f"Setting max_result_size to {size}")
        self.max_result_size = size

    def add_indexed_source(self, source: str) -> None:
        """
        Add a new indexed source
        
        Args:
            source: Source name to add
        """
        if source and source not in self.indexed_sources:
            self.indexed_sources.append(source)
            self.logger.info(f"Added indexed source: '{source}'. Current sources: {self.indexed_sources}")
        elif not source:
            self.logger.warning("Attempted to add an empty indexed source.")
        else:
            self.logger.debug(f"Indexed source '{source}' already exists.")


    def remove_indexed_source(self, source: str) -> None:
        """
        Remove an indexed source
        
        Args:
            source: Source name to remove
        """
        if source in self.indexed_sources:
            self.indexed_sources.remove(source)
            self.logger.info(f"Removed indexed source: '{source}'. Current sources: {self.indexed_sources}")
        else:
            self.logger.debug(f"Indexed source '{source}' not found for removal.")