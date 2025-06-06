Okay, here is a detailed plan of action for **Day 1: Afternoon (4 hours): Fix Critical Imports**, incorporating a smarter approach to implement basic versions of the `KnowledgeSystem` and `MemorySystem` from Day 3 and Day 4 plans, rather than just stubs. This will make the system more functional earlier.

This plan assumes the AI agent has access to the project codebase and the deliverables from the "Day 1 Morning Analysis" (specifically `import_dependencies_map.json`, `circular_imports_and_conflicts.md`, `module_structure_comparison.md`) and the `phase1_detailed_implementation.md` document.

---

## Detailed Plan of Action: Day 1 Afternoon - Fix Critical Imports & Basic Knowledge Module Implementation

**Objective:** Resolve critical import errors identified in the morning analysis, update **init**.py files, implement basic (in-memory) versions of the `MemorySystem` and `KnowledgeBase` classes, and validate these changes.

---

### Task 1: Fix [engine.py](http://engine.py/) Imports

**Goal:** Correct the import statements in [engine.py](http://engine.py/) based on the morning analysis and `phase1_detailed_implementation.md`.

**Detailed Steps for AI Agent:**

1. **Reference Analysis:**
    - Open module_structure_comparison.md.
    - Open phase1_detailed_implementation.md (Day 1, Afternoon, "Implementation Details" and Day 1, Morning, "Expected Issues").
2. **Modify [engine.py](http://engine.py/):**
    - Apply the following changes as specified:
    
    ```python
    // filepath: /workspaces/openmanis-qwenclone/core/engine.py
    // ...existing code...
    # Current broken imports (example, actual lines might vary):
    # from planner.planner import Planner
    # from knowledge.memory_system import MemorySystem
    # from tools.tool_interface import ToolInterface
    # from security.permission_validator import PermissionValidator # May or may not be broken
    
    # Fixed imports:
    from planner.task_planner import TaskPlanner
    from knowledge.memory_system import MemorySystem # This will point to the new basic implementation
    from tools.tool_interface import ToolAdapter # Assuming tool_interface.py contains ToolAdapter
    from security.permission_validator import PermissionValidator # Ensure this is correct
    from system_integration.component_connector import ComponentConnector
    from config.settings import settings
    # ... other existing correct imports ...
    
    class AgenticLoop:
    // ...existing code...
    
    ```
    
    - **Note:** Carefully check `module_structure_comparison.md` for the exact problematic lines in your current [engine.py](http://engine.py/) and replace them. The `phase1_detailed_implementation.md` provides the target corrected imports. Ensure `ToolAdapter` is the correct class name if `tools.tool_interface` is the module. The `PermissionValidator` import should also be verified against existing files or created if part of the plan.

---

### Task 2: Implement Basic `knowledge.memory_system.MemorySystem`

**Goal:** Create a functional, albeit basic, in-memory version of the `MemorySystem` class, drawing from Day 3 plans.

**Detailed Steps for AI Agent:**

1. **Reference Design:**
    - Open phase1_detailed_implementation.md (Day 3, Morning, "MemorySystem Class Design" and Day 3, Afternoon, "Implementation Focus").
2. **Create/Update memory_system.py:**
    - If the file exists as a stub, replace its content. If not, create it.
    
    ```python
    // filepath: /workspaces/openmanis-qwenclone/knowledge/memory_system.py
    import uuid
    from datetime import datetime
    from typing import List, Dict, Any, Optional
    
    class Message:
        def __init__(self, role: str, content: str, timestamp: Optional[datetime] = None, message_id: Optional[str] = None):
            self.message_id = message_id or str(uuid.uuid4())
            self.role = role  # "user", "assistant", "system", "tool"
            self.content = content
            self.timestamp = timestamp or datetime.utcnow()
    
        def to_dict(self) -> Dict[str, Any]:
            return {
                "message_id": self.message_id,
                "role": self.role,
                "content": self.content,
                "timestamp": self.timestamp.isoformat()
            }
    
    class MemorySystem:
        """
        Basic in-memory implementation of the MemorySystem.
        Manages conversation history and provides context.
        """
        def __init__(self):
            self.conversations: Dict[str, List[Message]] = {} # Stores conversation history per conversation_id
            self.short_term_memory: Dict[str, Any] = {} # For general short-term data
            print("INFO: Basic MemorySystem initialized (in-memory).")
    
        def start_conversation(self, conversation_id: Optional[str] = None) -> str:
            """Starts a new conversation or uses an existing ID."""
            conv_id = conversation_id or str(uuid.uuid4())
            if conv_id not in self.conversations:
                self.conversations[conv_id] = []
            return conv_id
    
        def add_message(self, conversation_id: str, role: str, content: str) -> Message:
            """Adds a message to the conversation history."""
            if conversation_id not in self.conversations:
                # Or raise an error, or auto-start. For now, auto-start.
                self.start_conversation(conversation_id)
    
            message = Message(role=role, content=content)
            self.conversations[conversation_id].append(message)
            return message
    
        def get_conversation_history(self, conversation_id: str, limit: Optional[int] = None) -> List[Message]:
            """Retrieves the conversation history for a given ID."""
            history = self.conversations.get(conversation_id, [])
            if limit:
                return history[-limit:]
            return history
    
        def get_formatted_history(self, conversation_id: str, limit: Optional[int] = None) -> List[Dict[str, str]]:
            """Retrieves conversation history in a simple list of dicts format."""
            messages = self.get_conversation_history(conversation_id, limit)
            return [{"role": msg.role, "content": msg.content} for msg in messages]
    
        def get_context(self, conversation_id: str, max_tokens: Optional[int] = None) -> str:
            """
            Generates a simple context string from the conversation history.
            Rudimentary implementation for now.
            """
            history = self.get_conversation_history(conversation_id)
            context_str = "\\n".join([f"{msg.role}: {msg.content}" for msg in history])
    
            if max_tokens: # Very basic token management by character length
                # This is not a proper tokenizer, just a rough estimate
                if len(context_str) > max_tokens * 4: # Assuming avg 4 chars per token
                     context_str = context_str[-(max_tokens*4):]
            return context_str
    
        def store_short_term(self, key: str, value: Any):
            """Stores a value in short-term memory."""
            self.short_term_memory[key] = value
    
        def retrieve_short_term(self, key: str) -> Optional[Any]:
            """Retrieves a value from short-term memory."""
            return self.short_term_memory.get(key)
    
        def clear_conversation(self, conversation_id: str):
            """Clears the history for a specific conversation."""
            if conversation_id in self.conversations:
                del self.conversations[conversation_id]
    
        def clear_all_memory(self):
            """Clears all conversations and short-term memory."""
            self.conversations.clear()
            self.short_term_memory.clear()
            print("INFO: All memory cleared in MemorySystem.")
    
    ```
    

---

### Task 3: Implement Basic `knowledge.knowledge_base.KnowledgeBase`

**Goal:** Create a functional, albeit basic, in-memory version of the `KnowledgeBase` class, drawing from Day 4 Morning plans.

**Detailed Steps for AI Agent:**

1. **Reference Design:**
    - Open phase1_detailed_implementation.md (Day 4, Morning, "KnowledgeBase Class").
2. **Create/Update knowledge_base.py:**
    
    ```python
    // filepath: /workspaces/openmanis-qwenclone/knowledge/knowledge_base.py
    from typing import List, Dict, Any, Optional
    import uuid
    from datetime import datetime
    
    class KnowledgeItem:
        def __init__(self, content: str, source: Optional[str] = None, item_id: Optional[str] = None, tags: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None):
            self.item_id = item_id or str(uuid.uuid4())
            self.content = content
            self.source = source
            self.tags = tags or []
            self.metadata = metadata or {}
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()
    
        def to_dict(self) -> Dict[str, Any]:
            return {
                "item_id": self.item_id,
                "content": self.content,
                "source": self.source,
                "tags": self.tags,
                "metadata": self.metadata,
                "created_at": self.created_at.isoformat(),
                "updated_at": self.updated_at.isoformat()
            }
    
    class KnowledgeBase:
        """
        Basic in-memory implementation of the KnowledgeBase.
        Stores and retrieves general information.
        """
        def __init__(self):
            self.storage: Dict[str, KnowledgeItem] = {} # item_id -> KnowledgeItem
            print("INFO: Basic KnowledgeBase initialized (in-memory).")
    
        def store_information(self, content: str, source: Optional[str] = None, tags: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None) -> KnowledgeItem:
            """Stores a piece of information."""
            item = KnowledgeItem(content=content, source=source, tags=tags, metadata=metadata)
            self.storage[item.item_id] = item
            return item
    
        def retrieve_information(self, item_id: str) -> Optional[KnowledgeItem]:
            """Retrieves a specific piece of information by its ID."""
            return self.storage.get(item_id)
    
        def search_knowledge(self, query: str, top_k: int = 5) -> List[KnowledgeItem]:
            """
            Performs a very basic keyword search on the content of stored items.
            Rudimentary implementation.
            """
            query_terms = query.lower().split()
            results = []
            for item in self.storage.values():
                match_score = 0
                item_content_lower = item.content.lower()
                for term in query_terms:
                    if term in item_content_lower:
                        match_score += 1
                if item.tags:
                    for tag in item.tags:
                        if tag.lower() in query_terms: # also check tags
                            match_score +=1
    
                if match_score > 0:
                    results.append({"item": item, "score": match_score})
    
            # Sort by score descending
            results.sort(key=lambda x: x["score"], reverse=True)
            return [res["item"] for res in results[:top_k]]
    
        def update_information(self, item_id: str, content: Optional[str] = None, source: Optional[str] = None, tags: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None) -> Optional[KnowledgeItem]:
            """Updates an existing knowledge item."""
            item = self.storage.get(item_id)
            if not item:
                return None
    
            if content is not None:
                item.content = content
            if source is not None:
                item.source = source
            if tags is not None:
                item.tags = tags
            if metadata is not None:
                item.metadata.update(metadata) # Merge metadata
            item.updated_at = datetime.utcnow()
            return item
    
        def delete_information(self, item_id: str) -> bool:
            """Deletes a piece of information."""
            if item_id in self.storage:
                del self.storage[item_id]
                return True
            return False
    
        def list_all_items(self) -> List[KnowledgeItem]:
            """Lists all items in the knowledge base."""
            return list(self.storage.values())
    
    ```
    
3. **Create placeholder files for other knowledge module components (Day 4):**
    - To prevent import errors if these are referenced in **init**.py or elsewhere soon.
    
    ```python
    // filepath: /workspaces/openmanis-qwenclone/knowledge/prompt_engineering.py
    # Placeholder for prompt engineering utilities
    # This module will contain functions and classes for constructing and managing prompts.
    
    def format_prompt(template: str, **kwargs) -> str:
        """Basic prompt formatting."""
        print("Warning: Using stub for prompt_engineering.format_prompt.")
        try:
            return template.format(**kwargs)
        except KeyError as e:
            print(f"Error formatting prompt: Missing key {e}")
            return template # return template as is if formatting fails
    
    class PromptTemplate:
        def __init__(self, template_string: str):
            self.template_string = template_string
            print("Warning: Using stub for prompt_engineering.PromptTemplate.")
    
        def render(self, **kwargs) -> str:
            return format_prompt(self.template_string, **kwargs)
    
    ```
    
    ```python
    // filepath: /workspaces/openmanis-qwenclone/knowledge/context_manager.py
    # Placeholder for context management system
    # This module will be responsible for managing and assembling context for the AI.
    
    class ContextManager:
        def __init__(self, memory_system, knowledge_base):
            self.memory_system = memory_system
            self.knowledge_base = knowledge_base
            print("Warning: Using stub for knowledge.ContextManager.")
    
        def build_context_for_prompt(self, conversation_id: str, user_query: str, max_tokens: int = 2000) -> str:
            """Builds a context string for the AI prompt."""
            print(f"Warning: Stub ContextManager.build_context_for_prompt called for conv_id {conversation_id}")
            # Basic stub: just get conversation history
            history_context = self.memory_system.get_context(conversation_id, max_tokens=max_tokens // 2)
            # In a real system, you might search knowledge_base based on user_query
            # relevant_knowledge = self.knowledge_base.search_knowledge(user_query, top_k=2)
            # knowledge_str = "\\n".join([item.content for item in relevant_knowledge])
            # return f"{history_context}\\n\\nRelevant Info:\\n{knowledge_str}\\n\\nUser Query: {user_query}"
            return f"{history_context}\\n\\nUser Query: {user_query}"
    
    ```
    

---

### Task 4: Update **init**.py Files

**Goal:** Ensure all relevant **init**.py files correctly export classes and functions to make them available for import by other modules.

**Detailed Steps for AI Agent:**

1. **Review `import_dependencies_map.json`:**
    - Identify which modules are importing from others and what specific symbols they are trying to import. This helps determine what needs to be exposed in **init**.py files.
2. **Update init.py:**
    
    ```python
    // filepath: /workspaces/openmanis-qwenclone/knowledge/__init__.py
    from .memory_system import MemorySystem, Message
    from .knowledge_base import KnowledgeBase, KnowledgeItem
    from .prompt_engineering import format_prompt, PromptTemplate
    from .context_manager import ContextManager
    
    __all__ = [
        "MemorySystem",
        "Message",
        "KnowledgeBase",
        "KnowledgeItem",
        "format_prompt",
        "PromptTemplate",
        "ContextManager"
    ]
    
    ```
    
3. **Update init.py:**
    - Assuming task_planner.py contains `TaskPlanner`.
    
    ```python
    // filepath: /workspaces/openmanis-qwenclone/planner/__init__.py
    # Assuming task_planner.py exists and contains TaskPlanner
    # If planner.py was renamed to task_planner.py and class Planner to TaskPlanner
    from .task_planner import TaskPlanner
    # Add other necessary exports from the planner module
    
    __all__ = [
        "TaskPlanner"
        # Add other exported class/function names here
    ]
    
    ```
    
    - **Action:** Verify the actual filename and class name within the planner directory. If `planner.py` was the old file and `task_planner.py` is the new one, ensure `task_planner.py` exists and contains `TaskPlanner`.
4. **Update init.py:**
    - Assuming tool_interface.py contains `ToolAdapter`.
    
    ```python
    // filepath: /workspaces/openmanis-qwenclone/tools/__init__.py
    # Assuming tool_interface.py exists and contains ToolAdapter
    from .tool_interface import ToolAdapter
    # from .file_tool import FileTool # Example if you have other tools
    # from .message_tool import MessageTool # Example
    
    __all__ = [
        "ToolAdapter"
        # "FileTool",
        # "MessageTool"
        # Add other exported tool classes here
    ]
    
    ```
    
    - **Action:** Verify `tool_interface.py` exists and contains the class `ToolAdapter`. Add other tools if they are meant to be exported.
5. **Update init.py:**
    - Assuming permission_validator.py contains `PermissionValidator`.
    
    ```python
    // filepath: /workspaces/openmanis-qwenclone/security/__init__.py
    from .permission_validator import PermissionValidator
    # Add other necessary exports from the security module
    
    __all__ = [
        "PermissionValidator"
    ]
    
    ```
    
    - **Action:** Verify `permission_validator.py` exists and contains `PermissionValidator`.
6. **Update init.py:**
    
    ```python
    // filepath: /workspaces/openmanis-qwenclone/core/__init__.py
    from .engine import AgenticLoop
    # from .event_processor import EventProcessor # If it exists and needs to be exported
    
    __all__ = [
        "AgenticLoop"
        # "EventProcessor"
    ]
    
    ```
    
7. **Update Project Root init.py (Optional but good practice for discoverability):**
    - This makes it easier to import top-level components if desired.
    
    ```python
    // filepath: /workspaces/openmanis-qwenclone/__init__.py
    # This file can be used to make parts of your package easily accessible
    # or to perform package-level initialization.
    
    # Example:
    # from .core.engine import AgenticLoop
    # from .config.settings import settings
    
    # print("Manus AI Clone package initialized.")
    
    ```
    
    - For now, keeping it minimal or empty is fine unless specific top-level exports are immediately needed.

---

### Task 5: Test Basic Module Imports

**Goal:** Validate that the critical import errors are resolved and basic modules can be imported.

**Detailed Steps for AI Agent:**

1. **Execute Validation Commands:**
    - Run these commands in the integrated terminal from the openmanis-qwenclone directory.
    
    ```bash
    python -c "from core.engine import AgenticLoop; print('SUCCESS: core.engine.AgenticLoop imported')"
    python -c "from planner.task_planner import TaskPlanner; print('SUCCESS: planner.task_planner.TaskPlanner imported')"
    python -c "from tools.tool_interface import ToolAdapter; print('SUCCESS: tools.tool_interface.ToolAdapter imported')"
    python -c "from security.permission_validator import PermissionValidator; print('SUCCESS: security.permission_validator.PermissionValidator imported')"
    python -c "from knowledge.memory_system import MemorySystem; ms = MemorySystem(); print('SUCCESS: knowledge.memory_system.MemorySystem imported and instantiated')"
    python -c "from knowledge.knowledge_base import KnowledgeBase; kb = KnowledgeBase(); print('SUCCESS: knowledge.knowledge_base.KnowledgeBase imported and instantiated')"
    python -c "from knowledge import ContextManager, format_prompt; print('SUCCESS: knowledge.ContextManager and format_prompt imported')"
    
    ```
    
2. **Review Output:**
    - Check for any `ImportError` or `AttributeError` messages. All commands should print "SUCCESS..." if the fixes and **init**.py updates are correct.
    - The instantiation tests for `MemorySystem` and `KnowledgeBase` will also print their "INFO: Basic ... initialized" messages.

---

This detailed plan should guide the AI agent to effectively complete the Day 1 Afternoon tasks, including the proactive basic implementation of key knowledge module components.