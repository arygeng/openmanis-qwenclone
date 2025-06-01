# Memory System Implementation for Manus AI Clone
"""
Memory management system for conversation and task history
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json


class MemorySystem:
    """
    Memory management system for conversation and task history
    """
    
    def __init__(self):
        self.conversation_history = []
        self.task_history = []
        self.context_cache = {}
        self.max_history_size = 1000
        self.initialized = True
    
    async def store_conversation(self, user_id: str, message: Dict[str, Any]) -> None:
        """Store conversation message in memory"""
        conversation_entry = {
            "user_id": user_id,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "type": message.get("type", "user")
        }
        
        self.conversation_history.append(conversation_entry)
        
        # Maintain max history size
        if len(self.conversation_history) > self.max_history_size:
            self.conversation_history = self.conversation_history[-self.max_history_size:]
    
    async def get_context(self, user_id: str) -> Dict[str, Any]:
        """Retrieve conversation context for user"""
        user_conversations = [
            conv for conv in self.conversation_history 
            if conv["user_id"] == user_id
        ]
        
        return {
            "user_id": user_id,
            "conversation_count": len(user_conversations),
            "recent_messages": user_conversations[-10:],  # Last 10 messages
            "context_summary": self._generate_context_summary(user_conversations)
        }
    
    async def store_task_result(self, task_id: str, result: Dict[str, Any]) -> None:
        """Store task execution result"""
        task_entry = {
            "task_id": task_id,
            "result": result,
            "timestamp": datetime.now().isoformat(),
            "status": result.get("status", "completed")
        }
        
        self.task_history.append(task_entry)
        
        # Maintain max history size
        if len(self.task_history) > self.max_history_size:
            self.task_history = self.task_history[-self.max_history_size:]
    
    async def get_relevant_history(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get relevant historical context for query"""
        # Simple keyword-based relevance for Phase 1
        # Will be enhanced with semantic search in Phase 2
        query_lower = query.lower()
        relevant_items = []
        
        # Search conversation history
        for conv in self.conversation_history:
            message_text = str(conv.get("message", "")).lower()
            if any(word in message_text for word in query_lower.split()):
                relevant_items.append({
                    "type": "conversation",
                    "relevance_score": self._calculate_relevance(query_lower, message_text),
                    "data": conv
                })
        
        # Search task history
        for task in self.task_history:
            task_text = str(task.get("result", "")).lower()
            if any(word in task_text for word in query_lower.split()):
                relevant_items.append({
                    "type": "task",
                    "relevance_score": self._calculate_relevance(query_lower, task_text),
                    "data": task
                })
        
        # Sort by relevance and return top results
        relevant_items.sort(key=lambda x: x["relevance_score"], reverse=True)
        return relevant_items[:limit]
    
    def _generate_context_summary(self, conversations: List[Dict[str, Any]]) -> str:
        """Generate a summary of conversation context"""
        if not conversations:
            return "No conversation history"
        
        total_messages = len(conversations)
        recent_topics = []
        
        # Extract topics from recent messages (simple keyword extraction)
        for conv in conversations[-5:]:
            message = conv.get("message", {})
            if isinstance(message, dict) and "content" in message:
                content = str(message["content"]).lower()
                # Simple topic extraction - will be enhanced in Phase 2
                words = content.split()
                topics = [word for word in words if len(word) > 4]
                recent_topics.extend(topics[:3])  # Top 3 words per message
        
        unique_topics = list(set(recent_topics))[:5]  # Top 5 unique topics
        
        return f"Total messages: {total_messages}, Recent topics: {', '.join(unique_topics)}"
    
    def _calculate_relevance(self, query: str, text: str) -> float:
        """Calculate relevance score between query and text"""
        query_words = set(query.split())
        text_words = set(text.split())
        
        if not query_words:
            return 0.0
        
        # Simple Jaccard similarity
        intersection = len(query_words.intersection(text_words))
        union = len(query_words.union(text_words))
        
        return intersection / union if union > 0 else 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        return {
            "conversation_entries": len(self.conversation_history),
            "task_entries": len(self.task_history),
            "cache_entries": len(self.context_cache),
            "max_history_size": self.max_history_size,
            "initialized": self.initialized
        }