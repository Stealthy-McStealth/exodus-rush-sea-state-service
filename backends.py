"""
State backend implementations for sea-state-service.
Supports both in-memory (per-pod) and distributed (etcd) backends.
"""
import etcd3
from typing import Optional


class InMemoryBackend:
    """
    In-memory state storage.
    WARNING: This is per-pod storage and will cause inconsistency in multi-replica deployments!
    Each pod maintains its own state, leading to different responses depending on which pod handles the request.
    """

    def __init__(self):
        self.data = {"sea_state": "closed"}

    def get(self, key: str) -> Optional[str]:
        """Get value for key from in-memory storage."""
        return self.data.get(key)

    def set(self, key: str, value: str) -> None:
        """Set value for key in in-memory storage."""
        self.data[key] = value

    def close(self):
        """No-op for in-memory backend."""
        pass


class EtcdBackend:
    """
    Distributed state storage using etcd.
    This ensures consistent state across all pods in a deployment.
    """

    def __init__(self, etcd_url: str):
        """
        Initialize etcd client.

        Args:
            etcd_url: URL in format "host:port" (e.g., "etcd:2379")
        """
        host, port = etcd_url.split(":")
        self.client = etcd3.client(host=host, port=int(port))

        # Initialize default state if not exists
        existing_state = self.get("sea_state")
        if existing_state is None:
            self.set("sea_state", "closed")

    def get(self, key: str) -> Optional[str]:
        """Get value for key from etcd."""
        value, _ = self.client.get(key)
        return value.decode('utf-8') if value else None

    def set(self, key: str, value: str) -> None:
        """Set value for key in etcd."""
        self.client.put(key, value)

    def close(self):
        """Close etcd client connection."""
        self.client.close()
