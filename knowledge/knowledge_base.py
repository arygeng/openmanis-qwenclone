# Knowledge Base Implementation for Manus AI Clone
"""
Knowledge base for storing and retrieving structured information
"""

from typing import Dict, Any, List, Optional
import json


class KnowledgeBase:
    """
    Knowledge base for storing and retrieving structured information
    """
    
    def __init__(self):
        self.knowledge_store = {}
        self.categories = set()
        self.initialized = True
    
    async def store_knowledge(self, category: str, key: str, data: Dict[str, Any]) -> None:
        """Store knowledge in the knowledge base"""
        if category not in self.knowledge_store:
            self.knowledge_store[category] = {}
        
        self.knowledge_store[category][key] = {
            "data": data,
            "created_at": "2024-01-01T00:00:00",  # Placeholder for Phase 1
            "updated_at": "2024-01-01T00:00:00"
        }
        
        self.categories.add(category)
    
    async def retrieve_knowledge(self, category: str, key: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve knowledge from the knowledge base"""
        if category not in self.knowledge_store:
            return {}
        
        if key:
            return self.knowledge_store[category].get(key, {})
        else:
            return self.knowledge_store[category]
    
    async def search_knowledge(self, query: str) -> List[Dict[str, Any]]:
        """Search knowledge base for relevant information"""
        results = []
        query_lower = query.lower()
        
        for category, items in self.knowledge_store.items():
            for key, entry in items.items():
                # Simple text search - will be enhanced in Phase 2
                entry_text = json.dumps(entry["data"]).lower()
                if query_lower in entry_text:
                    results.append({
                        "category": category,
                        "key": key,
                        "data": entry["data"],
                        "relevance": self._calculate_relevance(query_lower, entry_text)
                    })
        
        # Sort by relevance
        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results
    
    def _calculate_relevance(self, query: str, text: str) -> float:
        """Calculate relevance score"""
        # Simple keyword matching for Phase 1
        query_words = set(query.split())
        text_words = set(text.split())
        
        if not query_words:
            return 0.0
        
        intersection = len(query_words.intersection(text_words))
        return intersection / len(query_words)
    
    def get_categories(self) -> List[str]:
        """Get all knowledge categories"""
        return list(self.categories)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        total_entries = sum(len(items) for items in self.knowledge_store.values())
        return {
            "total_categories": len(self.categories),
            "total_entries": total_entries,
            "categories": list(self.categories),
            "initialized": self.initialized
        }