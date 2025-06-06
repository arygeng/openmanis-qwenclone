# filepath: /workspaces/openmanis-qwenclone/knowledge/knowledge_base.py
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
                for tag_item in item.tags: # iterate over tags if they exist
                    if tag_item.lower() in query_terms: # also check tags
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