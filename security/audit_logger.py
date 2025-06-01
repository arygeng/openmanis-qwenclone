"""
Audit logging system for Manus AI Clone
Implements comprehensive security event logging
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Callable

from security.permission_validator import PermissionValidator, SecurityContext, PermissionLevel
from security.access_rule_manager import AccessRuleManager

class AuditEvent:
    """Types of audit events"""
    SYSTEM = "system"
    SECURITY = "security"
    USER = "user"
    ACCESS = "access"
    ERROR = "error"
    PERFORMANCE = "performance"


class AuditLogEntry:
    """
    Represents a single audit log entry
    """
    def __init__(self, 
                 event_type: str,
                 message: str,
                 context: SecurityContext,
                 operation: Dict[str, Any],
                 severity: int = 3,
                 category: str = "general"):
        self.entry_id = str(uuid.uuid4())
        self.event_type = event_type
        self.message = message
        self.context = context
        self.operation = operation
        self.severity = severity
        self.category = category
        self.timestamp = datetime.now().isoformat()
        self.duration = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary"""
        return {
            "id": self.entry_id,
            "event_type": self.event_type,
            "message": self.message,
            "context": self.context.to_dict(),
            "operation": self.operation,
            "severity": self.severity,
            "category": self.category,
            "timestamp": self.timestamp,
            "duration": self.duration
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuditLogEntry':
        """Create log entry from dictionary"""
        context = SecurityContext(
            user_id=data["context"]["user_id"],
            roles=data["context"]["roles"],
            ip_address=data["context"]["ip_address"],
            session_id=data["context"]["session_id"]
        )
        
        return cls(
            event_type=data["event_type"],
            message=data["message"],
            context=context,
            operation=data["operation"],
            severity=data.get("severity", 3),
            category=data.get("category", "general")
        )


class AuditFilter:
    """
    Filter for selecting specific audit records
    """
    def __init__(self, 
                 start_time: Optional[datetime] = None,
                 end_time: Optional[datetime] = None,
                 severity_min: int = 1,
                 severity_max: int = 5,
                 categories: Optional[List[str]] = None,
                 users: Optional[List[str]] = None):
        self.start_time = start_time
        self.end_time = end_time
        self.severity_min = severity_min
        self.severity_max = severity_max
        self.categories = categories or []
        self.users = users or []

    def matches(self, entry: AuditLogEntry) -> bool:
        """
        Check if an audit entry matches this filter
        
        Args:
            entry: Audit log entry to check
            
        Returns:
            True if matches filter
        """
        # Convert entry timestamp to datetime
        try:
            entry_time = datetime.fromisoformat(entry.timestamp)
        except ValueError:
            return False
            
        # Time range check
        if self.start_time and entry_time < self.start_time:
            return False
            
        if self.end_time and entry_time > self.end_time:
            return False
            
        # Severity level check
        if not (self.severity_min <= entry.severity <= self.severity_max):
            return False
            
        # Category check
        if self.categories and entry.category not in self.categories:
            return False
            
        # User check
        if self.users and entry.details.get("user_id") not in self.users:
            return False
            
        return True


class AuditLogger:
    """
    Central audit logging system with filtering capabilities
    """
    def __init__(self):
        # Audit log storage
        self.audit_log = []  # type: List[AuditLogEntry]
        
        # Log retention settings
        self.max_entries = 10000  # Maximum number of entries to retain
        self.retention_period = 30  # Days to keep logs
        
        # Security settings
        self.log_level = 3  # Default minimum severity level to log
        self.log_all_operations = False  # Whether to log all operations
        
        # Event handlers
        self.handlers = []  # type: List[Callable[[AuditLogEntry], None]]

    def log_event(self, 
                 event_type: str,
                 message: str,
                 context: SecurityContext,
                 operation: Dict[str, Any],
                 severity: int = 3,
                 category: str = "security") -> str:
        """
        Log a security event
        
        Args:
            event_type: Type of event
            message: Description of event
            context: Security context
            operation: Operation details
            severity: Severity level (1-5)
            category: Event category
            
        Returns:
            ID of created log entry
        """
        # Skip if below log level
        if severity < self.log_level:
            return "none"
            
        # Create entry ID
        entry_id = str(uuid.uuid4())
        
        # Build context dictionary
        context_dict = context.to_dict() if hasattr(context, "to_dict") else {**context}
        
        # Build operation details
        operation_details = {
            "type": event_type,
            "parameters": operation,
            "context": context_dict
        }
        
        # Create log entry
        entry = AuditLogEntry(
            entry_id=entry_id,
            severity=severity,
            category=category,
            description=message,
            details={
                "event_type": event_type,
                "context": context_dict,
                "operation": operation,
                "user_id": context.user_id if isinstance(context, SecurityContext) else "unknown"
            }
        )
        
        # Store entry
        self.audit_log.append(entry)
        
        # Enforce size limit
        if len(self.audit_log) > self.max_entries:
            # Remove oldest entries first
            self.audit_log = self.audit_log[-self.max_entries:]
            
        # Notify handlers
        self._notify_handlers(entry)
        
        return entry_id

    def _notify_handlers(self, entry: AuditLogEntry) -> None:
        """
        Notify registered handlers about new log entries
        
        Args:
            entry: New audit log entry
        """
        for handler in self.handlers:
            try:
                handler(entry)
            except Exception:
                # Don't let handler errors affect main flow
                pass

    def add_handler(self, handler: Callable[[AuditLogEntry], None]) -> None:
        """
        Add a new event handler
        
        Args:
            handler: Function to call for each new entry
        """
        self.handlers.append(handler)

    def remove_handler(self, handler: Callable[[AuditLogEntry], None]) -> None:
        """
        Remove an event handler
        
        Args:
            handler: Handler function to remove
        """
        if handler in self.handlers:
            self.handlers.remove(handler)

    def get_audit_log(self, 
                     filter_criteria: Optional[AuditFilter] = None) -> List[AuditLogEntry]:
        """
        Get audit log entries matching criteria
        
        Args:
            filter_criteria: Criteria to filter by
            
        Returns:
            List of matching audit entries
        """
        # Start with all entries
        result = list(self.audit_log)
        
        # Apply filter if provided
        if filter_criteria:
            result = [e for e in result if filter_criteria.matches(e)]
            
        return result

    def clear_audit_log(self) -> None:
        """Clear the audit log"""
        self.audit_log = []

    def set_retention_policy(self, 
                           max_entries: int = 10000,
                           retention_period: int = 30) -> None:
        """
        Set log retention policy
        
        Args:
            max_entries: Maximum number of entries to keep
            retention_period: Number of days to keep entries
        """
        self.max_entries = max_entries
        self.retention_period = retention_period

    def set_log_level(self, level: int) -> None:
        """
        Set minimum severity level to log
        
        Args:
            level: Minimum severity level (1-5)
        """
        self.log_level = max(1, min(5, level))  # Ensure valid range

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about logged events"""
        # Calculate statistics
        total_events = len(self.audit_log)
        
        # Count by category
        category_counts = {}
        for entry in self.audit_log:
            if entry.category not in category_counts:
                category_counts[entry.category] = 0
            category_counts[entry.category] += 1
            
        # Count by severity
        severity_counts = {i: sum(1 for e in self.audit_log if e.severity == i) for i in range(1, 6)}
        
        # Get recent events
        recent_events = [e.to_dict() for e in self.audit_log[-10:]]
        
        return {
            "total_events": total_events,
            "category_counts": category_counts,
            "severity_counts": severity_counts,
            "recent_events": recent_events,
            "log_level": self.log_level,
            "retention_period": self.retention_period,
            "max_entries": self.max_entries
        }

    def export_log(self, 
                  filter_criteria: Optional[AuditFilter] = None) -> Dict[str, Any]:
        """
        Export audit log data
        
        Args:
            filter_criteria: Criteria to filter exported data
            
        Returns:
            Dictionary containing log data
        """
        # Get filtered log
        log_data = [e.to_dict() for e in self.get_audit_log(filter_criteria)]
        
        # Return structured export
        return {
            "metadata": {
                "export_time": datetime.now().isoformat(),
                "total_entries": len(log_data),
                "filter_criteria": filter_criteria.__dict__ if filter_criteria else {},
                "system_info": "Manus AI Clone Security Module"
            },
            "entries": log_data
        }

    def cleanup_old_entries(self) -> int:
        """
        Clean up old audit entries based on retention period
        
        Returns:
            Number of entries removed
        """
        if self.retention_period <= 0:
            return 0
            
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=self.retention_period)
        
        # Filter entries that are too old
        old_count = 0
        while old_count < len(self.audit_log):
            try:
                entry_time = datetime.fromisoformat(self.audit_log[old_count].timestamp)
                if entry_time >= cutoff_date:
                    break
                old_count += 1
            except Exception:
                break
                
        # Remove old entries
        if old_count > 0:
            self.audit_log = self.audit_log[old_count:]
        
        return old_count

    def log_security_event(self, 
                         event_type: str,
                         message: str,
                         context: SecurityContext,
                         operation: Dict[str, Any],
                         severity: int = 3,
                         category: str = "security") -> str:
        """
        Log a security-related event
        
        Args:
            event_type: Type of event
            message: Description of event
            context: Security context
            operation: Operation details
            severity: Severity level (1-5)
            category: Event category
            
        Returns:
            ID of created log entry
        """
        return self.log_event(event_type, message, context, operation, severity, category)

    def log_access_denied(self, 
                        message: str,
                        context: SecurityContext,
                        operation: Dict[str, Any]) -> str:
        """
        Log access denied event
        
        Args:
            message: Description of event
            context: Security context
            operation: Operation details
            
        Returns:
            ID of created log entry
        """
        return self.log_event(
            event_type="ACCESS_DENIED",
            message=message,
            context=context,
            operation=operation,
            severity=3,
            category="access_control"
        )

    def log_access_granted(self, 
                         message: str,
                         context: SecurityContext,
                         operation: Dict[str, Any]) -> str:
        """
        Log access granted event
        
        Args:
            message: Description of event
            context: Security context
            operation: Operation details
            
        Returns:
            ID of created log entry
        """
        return self.log_event(
            event_type="ACCESS_GRANTED",
            message=message,
            context=context,
            operation=operation,
            severity=2,
            category="access_control"
        )

    def log_authentication_failure(self, 
                                 message: str,
                                 context: SecurityContext,
                                 operation: Dict[str, Any]) -> str:
        """
        Log authentication failure event
        
        Args:
            message: Description of event
            context: Security context
            operation: Operation details
            
        Returns:
            ID of created log entry
        """
        return self.log_event(
            event_type="AUTH_FAILURE",
            message=message,
            context=context,
            operation=operation,
            severity=4,
            category="authentication"
        )

    def log_critical_event(self, 
                         message: str,
                         context: SecurityContext,
                         operation: Dict[str, Any]) -> str:
        """
        Log critical security event
        
        Args:
            message: Description of event
            context: Security context
            operation: Operation details
            
        Returns:
            ID of created log entry
        """
        return self.log_event(
            event_type="CRITICAL",
            message=message,
            context=context,
            operation=operation,
            severity=5,
            category="critical"
        )

    def log_configuration_change(self, 
                               message: str,
                               context: SecurityContext,
                               operation: Dict[str, Any]) -> str:
        """
        Log configuration change event
        
        Args:
            message: Description of event
            context: Security context
            operation: Operation details
            
        Returns:
            ID of created log entry
        """
        return self.log_event(
            event_type="CONFIG_CHANGE",
            message=message,
            context=context,
            operation=operation,
            severity=3,
            category="configuration"
        )

    def apply_to_validator(self, validator: PermissionValidator) -> None:
        """
        Integrate with permission validator for security event logging
        
        Args:
            validator: PermissionValidator to integrate with
        """
        # Register as logger for validator
        if hasattr(validator, "set_logger"):
            validator.set_logger(self.log_security_event)
            
        # Register for audit events
        validator.add_handler(self._handle_validator_event)

    def _handle_validator_event(self, event: Dict[str, Any]) -> None:
        """
        Handle events from permission validator
        
        Args:
            event: Event data
        """
        # Convert validator event to audit log format
        if event.get("event_type") == "ACCESS_DENIED":
            self.log_access_denied(
                message=event.get("message", "Access denied"),
                context=event.get("context", {}),
                operation=event.get("operation", {})
            )
        elif event.get("event_type") == "ACCESS_GRANTED":
            self.log_access_granted(
                message=event.get("message", "Access granted"),
                context=event.get("context", {}),
                operation=event.get("operation", {})
            )
        # Add more event type mappings as needed