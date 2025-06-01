"""
Permission validation system for Manus AI Clone
Implements access control and security validation
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Union

from core.types import PermissionLevel
from security.access_rule import AccessRule


class RolePermissions:
    """
    Role-based permission definitions
    """
    def __init__(self, 
                 role_name: str,
                 permissions: Dict[str, PermissionLevel],
                 description: str = ""):
        self.role_name = role_name
        self.permissions = permissions
        self.description = description
        self.created_at = datetime.now().isoformat()

    def has_permission(self, resource: str, level: PermissionLevel) -> bool:
        """
        Check if role has required permission
        
        Args:
            resource: Resource to check
            level: Required permission level
            
        Returns:
            True if permitted, False otherwise
        """
        if resource not in self.permissions:
            return False
            
        return self.permissions[resource].value >= level.value

    def to_dict(self) -> Dict[str, Any]:
        """Convert role permissions to dictionary"""
        return {
            "role_name": self.role_name,
            "description": self.description,
            "permissions": {k: v.value for k, v in self.permissions.items()},
            "created_at": self.created_at
        }


class SecurityContext:
    """
    Security context for operation validation
    """
    def __init__(self, 
                 user_id: str,
                 roles: List[str],
                 session_id: str,
                 ip_address: str,
                 timestamp: Optional[str] = None):
        self.user_id = user_id
        self.roles = roles
        self.session_id = session_id
        self.ip_address = ip_address
        self.timestamp = timestamp or datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert security context to dictionary"""
        return {
            "user_id": self.user_id,
            "roles": self.roles,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
            "timestamp": self.timestamp
        }


class PermissionValidator:
    """
    Validates permissions and access controls
    """
    def __init__(self):
        # Access control rules by resource type
        self.access_rules = {}
        
        # Role permissions
        self.role_permissions = {}
        
        # Operation audit log
        self.audit_log = []

    def validate_operation(self, 
                         operation: Dict[str, Any],
                         context: SecurityContext) -> bool:
        """
        Validate if an operation should be allowed
        
        Args:
            operation: Operation details including type and parameters
            context: Security context for the operation
            
        Returns:
            True if operation is allowed, False otherwise
        """
        # Extract operation details
        resource_type = operation.get("type", "unknown")
        required_permission = PermissionLevel.EXECUTE
        
        # Get required permission from operation
        if "permission" in operation:
            try:
                required_permission = PermissionLevel(operation["permission"])
            except ValueError:
                required_permission = PermissionLevel.EXECUTE
        
        # Check access rules
        if not self._check_access_rules(resource_type, required_permission, context):
            self._log_audit_event(
                "ACCESS_DENIED",
                f"User {context.user_id} denied access to {resource_type}",
                context.to_dict(),
                operation
            )
            return False
            
        # Log successful access
        self._log_audit_event(
            "ACCESS_GRANTED",
            f"User {context.user_id} granted access to {resource_type}",
            context.to_dict(),
            operation
        )
        
        return True

    def _check_access_rules(self, 
                          resource_type: str,
                          required_permission: PermissionLevel,
                          context: SecurityContext) -> bool:
        """
        Check access rules for a resource type
        
        Args:
            resource_type: Type of resource to access
            required_permission: Required permission level
            context: Security context
            
        Returns:
            True if access is allowed, False otherwise
        """
        # If no rules exist, allow access (open system)
        if not self.access_rules:
            return True
            
        # If no rule for this resource type, deny access
        if resource_type not in self.access_rules:
            return False
            
        # Check each rule for this resource type
        for rule_id in self.access_rules[resource_type]:
            rule = self.access_rules[resource_type][rule_id]
            
            # Skip if rule doesn't match conditions
            if not self._check_conditions(rule, context):
                continue
                
            # Return based on permission level
            if rule.required_permission.value <= required_permission.value:
                return True
            
        return False

    def _check_conditions(self, 
                        rule: AccessRule,
                        context: SecurityContext) -> bool:
        """
        Check additional conditions for a rule
        
        Args:
            rule: Access rule to validate against
            context: Security context
            
        Returns:
            True if conditions are satisfied
        """
        # No conditions means unconditional access
        if not rule.conditions:
            return True
            
        # Example IP address condition
        if "ip_whitelist" in rule.conditions:
            if context.ip_address not in rule.conditions["ip_whitelist"]:
                return False
                
        # Time-based restrictions
        if "time_restriction" in rule.conditions:
            current_hour = datetime.now().hour
            allowed_hours = rule.conditions["time_restriction"].split("-")
            if len(allowed_hours) == 2:
                start_hour, end_hour = map(int, allowed_hours)
                if not (start_hour <= current_hour < end_hour):
                    return False
            
        # Add more condition checks here as needed
        return True

    def _log_audit_event(self, 
                       event_type: str,
                       message: str,
                       context: Dict[str, Any],
                       operation: Dict[str, Any]) -> None:
        """
        Log security events for auditing
        
        Args:
            event_type: Type of event
            message: Description of event
            context: Security context
            operation: Operation details
        """
        audit_record = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "message": message,
            "context": context,
            "operation": operation,
            "timestamp": datetime.now().isoformat()
        }
        
        self.audit_log.append(audit_record)
        # In production, would also send to centralized logging

    def add_access_rule(self, 
                      resource_type: str, 
                      rule: AccessRule) -> None:
        """
        Add a new access control rule
        
        Args:
            resource_type: Type of resource to apply rule to
            rule: Rule definition
        """
        if resource_type not in self.access_rules:
            self.access_rules[resource_type] = {}
            
        self.access_rules[resource_type][rule.rule_id] = rule

    def add_role_permissions(self, 
                           role_name: str, 
                           permissions: Dict[str, PermissionLevel]) -> None:
        """
        Add permissions for a role
        
        Args:
            role_name: Role to add permissions for
            permissions: Dictionary of resource-type to permission mappings
        """
        self.role_permissions[role_name] = RolePermissions(
            role_name=role_name,
            permissions=permissions
        )

    def check_user_permission(self, 
                            user_roles: List[str],
                            resource_type: str,
                            required_permission: PermissionLevel) -> bool:
        """
        Check if user has required permission through any role
        
        Args:
            user_roles: User's roles
            resource_type: Resource type to access
            required_permission: Required permission level
            
        Returns:
            True if permitted, False otherwise
        """
        # Check each user role
        for role_name in user_roles:
            if role_name not in self.role_permissions:
                continue
                
            role = self.role_permissions[role_name]
            if role.has_permission(resource_type, required_permission):
                return True
                
        return False

    def get_audit_log(self) -> List[Dict[str, Any]]:
        """
        Get complete audit log
        
        Returns:
            List of audit records
        """
        return self.audit_log

    def clear_audit_log(self) -> None:
        """
        Clear the audit log
        """
        self.audit_log = []