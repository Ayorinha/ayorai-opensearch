"""Minimal stand-in for ``nltk.tokenize.api.TokenizerI`` (only ``tokenize`` is used)."""

from abc import ABC, abstractmethod


class TokenizerI(ABC):
    @abstractmethod
    def tokenize(self, s: str) -> list[str]:
        """Return a tokenized copy of *s*."""
