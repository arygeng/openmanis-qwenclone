# Core Types and Enums for Manus AI Clone
"""
Shared types and enums to avoid circular imports
"""

from enum import Enum


class AgentState(Enum):
    """Agent lifecycle states"""
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING = "waiting"
    ERROR = "error"
    COMPLETED = "completed"


class SecurityException(Exception):
    """Security-related exceptions"""
    pass


class PermissionLevel(Enum):
    """Permission levels for security validation"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"