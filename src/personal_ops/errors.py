from __future__ import annotations


class ConfigError(ValueError):
    pass


class DomainError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
