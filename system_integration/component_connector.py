"""
System integration module for Manus AI Clone
Implements component connection and data flow
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Callable

from core.types import SecurityException
from planner.task_prioritization import TaskPrioritizer
from planner.task_planner import TaskPlanner
from tools.tool_interface import ToolAdapter
from security.permission_validator import PermissionValidator, SecurityContext
from security.audit_logger import AuditLogger, AuditEvent
from security.access_rule_manager import AccessRuleManager
from .data_flow import MessageRouter
from .monitoring import SystemMonitor

class ComponentConnection:
    """
    Represents a connection between system components
    """
    def __init__(self, 
                 connection_id: str,
                 source: str,
                 target: str,
                 protocol: str = "internal",
                 secure: bool = True):
        self.connection_id = connection_id
        self.source = source
        self.target = target
        self.protocol = protocol
        self.secure = secure
        self.created_at = datetime.now().isoformat()
        self.status = "active"

    def to_dict(self) -> Dict[str, Any]:
        """Convert connection to dictionary representation"""
        return {
            "connection_id": self.connection_id,
            "source": self.source,
            "target": self.target,
            "protocol": self.protocol,
            "secure": self.secure,
            "created_at": self.created_at,
            "status": self.status
        }


class DataFlow:
    """
    Represents data flow between components
    """
    def __init__(self, 
                 flow_id: str,
                 source_component: str,
                 target_component: str,
                 data_type: str,
                 direction: str = "unidirectional"):
        self.flow_id = flow_id
        self.source_component = source_component
        self.target_component = target_component
        self.data_type = data_type
        self.direction = direction
        self.max_data_size = 10 * 1024 * 1024  # bytes (10MB)
        self.encryption_required = True
        self.last_checked = datetime.now().isoformat()

    def validate_data(self, data: Any) -> bool:
        """
        Validate data against flow requirements
        
        Args:
            data: Data to validate
            
        Returns:
            True if valid
        """
        # Check data type
        if not isinstance(data, type(self.data_type)):
            return False
            
        # Check size limits
        try:
            data_size = len(str(data))
            if data_size > self.max_data_size:
                return False
        except Exception:
            return False
            
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert flow to dictionary representation"""
        return {
            "flow_id": self.flow_id,
            "source_component": self.source_component,
            "target_component": self.target_component,
            "data_type": self.data_type,
            "direction": self.direction,
            "max_data_size": self.max_data_size,
            "encryption_required": self.encryption_required,
            "last_checked": self.last_checked
        }


class ComponentConnector:
    """
    Connects system components and manages data flow
    """
    def __init__(self):
        # Component registry
        self.components = {}  # type: Dict[str, Any]
        
        # Connection registry
        self.connections = {}  # type: Dict[str, ComponentConnection]
        
        # Data flow registry
        self.data_flows = {}  # type: Dict[str, DataFlow]
        
        # Message routing
        self.message_router = MessageRouter()
        
        # Default settings
        self.default_protocol = "internal"
        self.default_secure = True
        
        # Integration status
        self.integrated_components = set()
        
        # System monitoring
        self.system_monitor = SystemMonitor()

    def register_component(self, name: str, component: Any) -> None:
        """
        Register a system component
        
        Args:
            name: Name of component
            component: Component instance
        """
        self.components[name] = component
        
        # If this is a core component, mark as integrated
        if name in ["engine", "planner", "validator", "tool_manager"]:
            self.integrated_components.add(name)

    def connect_components(self, 
                         source: str,
                         target: str,
                         protocol: str = "internal",
                         secure: bool = True) -> str:
        """
        Create a connection between components
        
        Args:
            source: Source component name
            target: Target component name
            protocol: Communication protocol
            secure: Whether the connection is secure
            
        Returns:
            ID of created connection
        """
        # Check if components exist
        if source not in self.components or target not in self.components:
            raise ValueError("Source or target component not found")
            
        # Generate connection ID
        connection_id = str(uuid.uuid4())
        
        # Create connection
        connection = ComponentConnection(
            connection_id=connection_id,
            source=source,
            target=target,
            protocol=protocol,
            secure=secure
        )
        
        # Store connection
        self.connections[connection_id] = connection
        
        # Return connection ID
        return connection_id

    def create_data_flow(self, 
                       source: str,
                       target: str,
                       data_type: str,
                       direction: str = "unidirectional") -> str:
        """
        Define data flow between components
        
        Args:
            source: Source component
            target: Target component
            data_type: Type of data being transferred
            direction: Direction of data flow
            
        Returns:
            ID of created data flow
        """
        # Generate flow ID
        flow_id = str(uuid.uuid4())
        
        # Create data flow definition
        flow = DataFlow(
            flow_id=flow_id,
            source_component=source,
            target_component=target,
            data_type=data_type,
            direction=direction
        )
        
        # Store data flow
        self.data_flows[flow_id] = flow
        
        return flow_id

    def setup_core_connections(self) -> List[str]:
        """
        Setup connections for core components
        
        Returns:
            List of created connection IDs
        """
        connection_ids = []
        
        # Engine <-> Planner
        if "engine" in self.components and "planner" in self.components:
            conn_id = self.connect_components("engine", "planner")
            connection_ids.append(conn_id)
            
            # Setup data flows
            self.create_data_flow("engine", "planner", "execution_plan")
            self.create_data_flow("planner", "engine", "execution_result")
            
        # Engine <-> Validator
        if "engine" in self.components and "validator" in self.components:
            conn_id = self.connect_components("engine", "validator")
            connection_ids.append(conn_id)
            
            # Setup data flows
            self.create_data_flow("engine", "validator", "security_check")
            self.create_data_flow("validator", "engine", "security_response")
            
        # Engine <-> Tool Manager
        if "engine" in self.components and "tool_manager" in self.components:
            conn_id = self.connect_components("engine", "tool_manager")
            connection_ids.append(conn_id)
            
            # Setup data flows
            self.create_data_flow("engine", "tool_manager", "tool_request")
            self.create_data_flow("tool_manager", "engine", "tool_response")
            
        # Planner <-> Validator
        if "planner" in self.components and "validator" in self.components:
            conn_id = self.connect_components("planner", "validator")
            connection_ids.append(conn_id)
            
            # Setup data flows
            self.create_data_flow("planner", "validator", "plan_validation")
            self.create_data_flow("validator", "planner", "validation_result")
            
        return connection_ids

    def get_connection_status(self) -> Dict[str, Any]:
        """Get current status of all connections"""
        return {
            "total_connections": len(self.connections),
            "connections_by_component": self._count_connections_by_component(),
            "active_flows": len(self.data_flows),
            "integrated_components": list(self.integrated_components),
            "last_checked": datetime.now().isoformat()
        }

    def _count_connections_by_component(self) -> Dict[str, int]:
        """Count connections per component"""
        result = {}
        
        # Count connections for each component
        for connection in self.connections.values():
            # Source side
            if connection.source not in result:
                result[connection.source] = 0
            result[connection.source] += 1
            
            # Target side
            if connection.target not in result:
                result[connection.target] = 0
            result[connection.target] += 1
            
        return result

    def send_message(self, 
                    source: str,
                    target: str,
                    message: Dict[str, Any],
                    context: Optional[SecurityContext] = None) -> Dict[str, Any]:
        """
        Send a message between components
        
        Args:
            source: Source component
            target: Target component
            message: Message to send
            context: Security context for operation validation
            
        Returns:
            Response from target
        """
        # Check if components exist
        if source not in self.components or target not in self.components:
            raise ValueError("Source or target component not found")
            
        # Find connection
        connection = self._find_connection(source, target)
        if not connection:
            raise ValueError(f"No connection from {source} to {target}")
            
        # Validate security context
        if context and hasattr(context, "validator"):
            # Create permission check
            operation = {
                "type": "message",
                "parameters": {
                    "source": source,
                    "target": target,
                    "size": len(str(message))
                }
            }
            
            if not context.validator.validate_operation(operation, context):
                raise SecurityException(f"Access denied for {source} to {target}")
                
        # Route message
        return self._route_message(source, target, message)

    def _find_connection(self, source: str, target: str) -> Optional[ComponentConnection]:
        """
        Find connection between components
        
        Args:
            source: Source component
            target: Target component
            
        Returns:
            Matching connection or None
        """
        # Find direct connection
        for connection in self.connections.values():
            if connection.source == source and connection.target == target:
                return connection
                
        # No connection found
        return None

    def _route_message(self, 
                     source: str,
                     target: str,
                     message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route message between components
        
        Args:
            source: Source component
            target: Target component
            message: Message to route
            
        Returns:
            Response from target
        """
        # Get components
        source_component = self.components[source]
        target_component = self.components[target]
        
        # Handle different component types
        if hasattr(target_component, "process_message"):
            # Use process_message interface
            return target_component.process_message(source, message)
        elif hasattr(target_component, "execute"):
            # Use execute interface with empty parameters
            return target_component.execute({}, None)
        else:
            # Fallback - just echo back
            return {
                "error": "Target component has no message handling capability",
                "message_received": message
            }

    def integrate_all_components(self, 
                              engine: ManusAIEngine,
                              planner: TaskPlanner,
                              validator: PermissionValidator,
                              tool_manager: ToolAdapter,
                              audit_logger: AuditLogger,
                              access_rules: AccessRuleManager) -> None:
        """
        Integrate all core components into the system
        
        Args:
            engine: Core engine
            planner: Task planner
            validator: Permission validator
            tool_manager: Tool manager
            audit_logger: System audit logger
            access_rules: Access rule manager
        """
        # Register core components
        self.register_component("engine", engine)
        self.register_component("planner", planner)
        self.register_component("validator", validator)
        self.register_component("tool_manager", tool_manager)
        self.register_component("audit_logger", audit_logger)
        self.register_component("access_rules", access_rules)
        
        # Setup core connections
        self.setup_core_connections()
        
        # Configure security integrations
        self._configure_security_integrations(validator, tool_manager, access_rules)
        
        # Configure monitoring
        self._setup_monitoring(engine, validator, audit_logger)

    def _configure_security_integrations(self, 
                                     validator: PermissionValidator,
                                     tool_manager: ToolAdapter,
                                     access_rules: AccessRuleManager) -> None:
        """
        Configure security integrations between components
        
        Args:
            validator: Permission validator
            tool_manager: Tool manager
            access_rules: Access rule manager
        """
        # Set validator on engine
        if "engine" in self.components:
            self.components["engine"].set_validator(validator)
            
        # Apply access rules to validator
        if "access_rules" in self.components:
            access_rules.apply_to_validator(validator)
            
        # Apply role permissions to validator
        tool_manager.apply_to_validator(validator)
        
        # Set up audit logging
        if "audit_logger" in self.components:
            audit_logger = self.components["audit_logger"]
            audit_logger.apply_to_validator(validator)

    def _setup_monitoring(self, engine: ManusAIEngine, validator: PermissionValidator, audit_logger: AuditLogger) -> None:
        """
        Setup monitoring for system components
        
        Args:
            engine: Core engine
            validator: Permission validator
            audit_logger: Audit logger
        """
        # Register core components
        self.system_monitor.register_component("engine")
        self.system_monitor.register_component("planner")
        self.system_monitor.register_component("validator")
        self.system_monitor.register_component("tool_manager")
        
        # Setup monitoring for engine
        if "engine" in self.components:
            engine.set_monitor_callback(self._handle_engine_event)
            
        # Setup monitoring for validator
        if "validator" in self.components:
            validator.set_audit_handler(self._handle_security_event)
            
        # Set audit logger if available
        if "audit_logger" in self.components:
            self.system_monitor.set_audit_logger(audit_logger)

    def _handle_engine_event(self, event: Dict[str, Any]) -> None:
        """
        Handle engine events
        
        Args:
            event: Event data
        """
        # Forward event to appropriate components
        if "type" in event:
            if event["type"] == "plan_created":
                # Notify planner
                if "planner" in self.components:
                    self.components["planner"].on_plan_created(event.get("plan"))
            elif event["type"] == "tool_executed":
                # Notify validator
                if "validator" in self.components:
                    self.components["validator"].on_tool_executed(event.get("tool_name"))
                    
        # Log event if logger exists
        if "audit_logger" in self.components:
            self.components["audit_logger"].log_event(
                event_type=event.get("type", "unknown"),
                message=event.get("message", "Engine event"),
                context=event.get("context", {}),
                operation=event,
                severity=event.get("severity", 3),
                category=event.get("category", "engine")
            )

    def _handle_security_event(self, event: Dict[str, Any]) -> None:
        """
        Handle security events
        
        Args:
            event: Event data
        """
        # Forward event to engine
        if "engine" in self.components:
            self.components["engine"].handle_security_event(event)
            
        # Forward event to planner
        if "planner" in self.components:
            self.components["planner"].handle_security_event(event)
            
        # Log event if logger exists
        if "audit_logger" in self.components:
            self.components["audit_logger"].log_event(
                event_type=event.get("event_type", "security"),
                message=event.get("message", "Security event"),
                context=event.get("context", {}),
                operation=event,
                severity=event.get("severity", 3),
                category="security"
            )

    def get_component_interfaces(self) -> Dict[str, Dict[str, Any]]:
        """Get interfaces of all registered components"""
        result = {}
        
        for name, component in self.components.items():
            result[name] = {
                "methods": [m for m in dir(component) if callable(getattr(component, m)) and not m.startswith("_")],
                "properties": [p for p in dir(component) if not callable(getattr(component, p)) and not p.startswith("_")],
                "type": type(component).__name__
            }
            
        return result

    def get_diagnostic_report(self) -> Dict[str, Any]:
        """Generate diagnostic report for system health"""
        return self.system_monitor.get_diagnostic_report()

    def get_component_diagnostics(self, component: str) -> Dict[str, Any]:
        """
        Get diagnostic information for a component
        
        Args:
            component: Component name
            
        Returns:
            Diagnostic report
        """
        return self.system_monitor.get_component_diagnostics(component)

    def log_event(self, 
                 event_type: str,
                 message: str,
                 component: str,
                 duration: Optional[float] = None) -> None:
        """
        Log an event with optional performance metric
        
        Args:
            event_type: Type of event
            message: Event description
            component: Component involved
            duration: Optional duration metric
        """
        # Log event if logger exists
        if "audit_logger" in self.components:
            self.components["audit_logger"].log_event(
                event_type=event_type,
                message=message,
                component=component,
                duration=duration
            )
        
        # Record event in monitoring
        self.system_monitor.log_event(event_type, message, component, duration)

    def verify_integrity(self) -> Dict[str, Any]:
        """Verify system integrity by checking connections"""
        # Initialize results
        results = {
            "components": {},
            "connections": {},
            "flows": {},
            "overall_status": "healthy"
        }
        
        # Check components
        for name, component in self.components.items():
            status = self._check_component_health(component)
            results["components"][name] = status
            
            if status != "healthy":
                results["overall_status"] = "degraded"
        
        # Check connections
        for conn_id, connection in self.connections.items():
            status = self._check_connection_health(connection)
            results["connections"][conn_id] = status
            
            if status != "healthy":
                results["overall_status"] = "degraded"
                
        # Check data flows
        for flow_id, flow in self.data_flows.items():
            status = self._check_flow_health(flow)
            results["flows"][flow_id] = status
            
            if status != "healthy":
                results["overall_status"] = "degraded"
                
        # Add timestamp
        results["checked_at"] = datetime.now().isoformat()
        
        # Add monitoring statistics
        if hasattr(self.system_monitor, "get_health_statistics"):
            results["health_stats"] = self.system_monitor.get_health_statistics()
        if hasattr(self.system_monitor, "get_performance_statistics"):
            results["performance_stats"] = self.system_monitor.get_performance_statistics()
        
        return results

    def _check_component_health(self, component: Any) -> str:
        """
        Check health of a component
        
        Args:
            component: Component to check
            
        Returns:
            Health status string
        """
        # In real implementation would do actual checks
        return "healthy"

    def _check_connection_health(self, connection: ComponentConnection) -> str:
        """
        Check health of a connection
        
        Args:
            connection: Connection to check
            
        Returns:
            Health status string
        """
        # In real implementation would do actual checks
        return "healthy"

    def _check_flow_health(self, flow: DataFlow) -> str:
        """
        Check health of a data flow
        
        Args:
            flow: Flow to check
            
        Returns:
            Health status string
        """
        # In real implementation would do actual checks
        return "healthy"

    def set_message_router(self, router: Any) -> None:
        """
        Set message router for system
        
        Args:
            router: Message router component
        """
        self.message_router = router

    def route_message(self, 
                     source: str,
                     target: str,
                     message: Dict[str, Any],
                     context: Optional[SecurityContext] = None) -> Dict[str, Any]:
        """
        Route message through the system
        
        Args:
            source: Source component
            target: Target component
            message: Message to send
            context: Security context
            
        Returns:
            Response from target
        """
        # If we have a message router, use it
        if self.message_router:
            return self.message_router.route_message(source, target, message, context)
            
        # Otherwise use default routing
        return self.send_message(source, target, message, context)

    def configure_message_routing(self, 
                               router: Any,
                               routing_rules: List[Dict[str, Any]]) -> bool:
        """
        Configure message routing rules
        
        Args:
            router: Message router component
            routing_rules: List of routing rules
            
        Returns:
            True if successful
        """
        # Set message router
        self.set_message_router(router)
        
        # Configure routing rules
        if hasattr(router, "configure_routes"):
            try:
                router.configure_routes(routing_rules)
                return True
            except Exception as e:
                # Log error
                if "audit_logger" in self.components:
                    self.components["audit_logger"].log_critical_event(
                        message=f"Routing configuration failed: {str(e)}",
                        context=SecurityContext(
                            user_id="system",
                            roles=["admin"],
                            session_id="system",
                            ip_address="127.0.0.1"
                        ),
                        operation={
                            "type": "routing_config",
                            "error": str(e)
                        }
                    )
                return False
        
        return False

    def get_routing_table(self) -> Dict[str, Any]:
        """Get current routing table"""
        routing_table = {
            "default_routes": {
                "engine": "planner",
                "planner": "tool_manager",
                "tool_manager": "validator"
            },
            "last_updated": datetime.now().isoformat()
        }
            
        # Add custom routes from message router
        custom_routes = self._get_custom_routes()
        if custom_routes:
            routing_table["custom_routes"] = custom_routes
                
        return routing_table
    
    def _get_custom_routes(self) -> Dict[str, Dict[str, str]]:
        """Get custom routes from message router"""
        if self.message_router and hasattr(self.message_router, "routes"):
            return self.message_router.routes
        return {}