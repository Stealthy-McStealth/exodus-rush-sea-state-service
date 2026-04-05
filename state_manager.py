"""
State manager for sea-state-service.
Manages sea state transitions and backend selection.
"""
import os
import logging
from backends import InMemoryBackend, EtcdBackend

logger = logging.getLogger(__name__)


class StateManager:
    """
    Manages the state of the Red Sea.

    THE BUG: Backend selection based on STATE_CACHE_URL environment variable.
    If STATE_CACHE_URL is not set, falls back to InMemoryBackend which causes
    inconsistent state across multiple pods in a Kubernetes deployment.
    """

    VALID_STATES = ["closed", "splitting", "split"]

    def __init__(self):
        """Initialize state manager with appropriate backend."""
        cache_url = os.getenv("STATE_CACHE_URL")

        if cache_url:
            logger.info(f"Initializing with distributed etcd backend: {cache_url}")
            self.backend = EtcdBackend(cache_url)
        else:
            logger.warning("STATE_CACHE_URL not set - using in-memory backend (per-pod storage)")
            logger.warning("This will cause inconsistent state in multi-replica deployments!")
            self.backend = InMemoryBackend()

    def get_state(self) -> str:
        """Get current sea state."""
        state = self.backend.get("sea_state")
        return state if state else "closed"

    def set_state(self, new_state: str) -> bool:
        """
        Set sea state.

        Args:
            new_state: New state to set

        Returns:
            True if state was set successfully, False otherwise
        """
        if new_state not in self.VALID_STATES:
            logger.error(f"Invalid state: {new_state}")
            return False

        current_state = self.get_state()
        logger.info(f"State transition: {current_state} -> {new_state}")
        self.backend.set("sea_state", new_state)
        return True

    def can_split(self) -> bool:
        """Check if sea can be split (must be in 'closed' state)."""
        return self.get_state() == "closed"

    def split(self) -> tuple[bool, str]:
        """
        Initiate sea splitting sequence.

        Returns:
            Tuple of (success, message)
        """
        if not self.can_split():
            current = self.get_state()
            return False, f"Cannot split sea - current state: {current}"

        # Simulate splitting sequence
        self.set_state("splitting")
        # In real implementation, this might trigger async process
        self.set_state("split")

        return True, "Sea has been split! Path is clear for crossing."

    def close(self) -> tuple[bool, str]:
        """
        Close the sea (admin operation).

        Returns:
            Tuple of (success, message)
        """
        current = self.get_state()
        if current == "closed":
            return False, "Sea is already closed"

        self.set_state("closed")
        return True, "Sea has been closed"

    def cleanup(self):
        """Clean up backend resources."""
        self.backend.close()
