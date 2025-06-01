# Access Rule Implementation for Manus AI Clone
"""
Access rule definitions for security validation
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Union

from core.types import PermissionLevel


class RuleType(Enum):
    """Types of access rules"""
    ALLOW = "allow"
    DENY = "deny"
    CONDITIONAL = "conditional"


class AccessRule:
    """
    Access rule for security validation
    """
    
    def __init__(self, 
                 rule_type: RuleType,
                 resource_type: str,
                 permission_level: PermissionLevel,
                 conditions: Optional[Dict[str, Any]] = None):
        self.rule_id = str(uuid.uuid4())
        self.rule_type = rule_type
        self.resource_type = resource_type
        self.permission_level = permission_level
        self.conditions = conditions or {}
        self.created_at = datetime.now()
        self.active = True
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Evaluate if this rule applies to the given context
        
        Args:
            context: Security context to evaluate
            
        Returns:
            True if rule applies, False otherwise
        """
        if not self.active:
            return False
        
        # Check basic conditions
        if self.conditions:
            for key, expected_value in self.conditions.items():
                if context.get(key) != expected_value:
                    return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary representation"""
        return {
            "rule_id": self.rule_id,
            "rule_type": self.rule_type.value,
            "resource_type": self.resource_type,
            "permission_level": self.permission_level.value,
            "conditions": self.conditions,
            "created_at": self.created_at.isoformat(),
            "active": self.active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AccessRule':
        """Create rule from dictionary representation"""
        rule = cls(
            rule_type=RuleType(data["rule_type"]),
            resource_type=data["resource_type"],
            permission_level=PermissionLevel(data["permission_level"]),
            conditions=data.get("conditions", {})
        )
        rule.rule_id = data["rule_id"]
        rule.active = data.get("active", True)
        return rule