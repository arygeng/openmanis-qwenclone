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