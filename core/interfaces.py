# In core/interfaces.py
from abc import ABC, abstractmethod
from typing import Any, Dict

class IEngine(ABC):
    @abstractmethod
    def set_validator(self, validator: Any) -> None:
        pass

    @abstractmethod
    def set_monitor_callback(self, callback: Any) -> None:
        pass

    @abstractmethod
    def handle_security_event(self, event: Dict[str, Any]) -> None:
        pass

    # Add other methods ComponentConnector might call on the "engine"
    # based on your inspection of system_integration/component_connector.py
    # For now, the architect identified these three.