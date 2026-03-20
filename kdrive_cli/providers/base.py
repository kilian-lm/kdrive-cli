"""Base token provider interface."""

from abc import ABC, abstractmethod


class TokenProvider(ABC):
    """Abstract base class for API token providers."""

    @abstractmethod
    def get_token(self) -> str | None:
        """Return the API token or None if unavailable."""
        ...

    @property
    def name(self) -> str:
        return self.__class__.__name__
