"""
event_bus.py
------------
Decoupled pub/sub event bus for SymbiotixEngine.
"""

class EventBus:
    """
    Publish/Subscribe event broker.
    """
    def __init__(self) -> None:
        self._listeners = {}

    def subscribe(self, event_type: str, callback) -> None:
        """
        Register a callback for a specific event type.
        """
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)
        # print(f"[EventBus] Subscribed to '{event_type}': {callback.__name__ if hasattr(callback, '__name__') else callback}")

    def publish(self, event_type: str, *args, **kwargs) -> None:
        """
        Publish an event to all registered listeners.
        """
        if event_type in self._listeners:
            for callback in self._listeners[event_type]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    import traceback
                    print(f"[EventBus] Error in callback for '{event_type}': {e}")
                    traceback.print_exc()

# Global event bus instance
event_bus = EventBus()
