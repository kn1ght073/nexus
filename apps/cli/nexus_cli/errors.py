"""Typed error definitions and exit codes for NEXUS CLI."""

from enum import IntEnum
from typing import Optional


class ExitCode(IntEnum):
    SUCCESS = 0
    FAILURE = 1
    USAGE_ERROR = 2
    AUTH_ERROR = 3
    FORBIDDEN = 4
    NOT_FOUND = 5
    NETWORK_ERROR = 6
    TIMEOUT = 7


class NexusError(Exception):
    """Base exception for all NEXUS CLI runtime errors."""

    def __init__(
        self,
        message: str,
        hint: Optional[str] = None,
        exit_code: ExitCode = ExitCode.FAILURE,
        details: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.hint = hint
        self.exit_code = exit_code
        self.details = details


class AuthenticationError(NexusError):
    def __init__(
        self,
        message: str = "Authentication required or session expired.",
        hint: Optional[str] = "Run 'nexus auth login' to authenticate.",
        details: Optional[str] = None,
    ):
        super().__init__(message=message, hint=hint, exit_code=ExitCode.AUTH_ERROR, details=details)


class ForbiddenError(NexusError):
    def __init__(
        self,
        message: str = "Access denied: elevated privileges or specific scope required.",
        hint: Optional[str] = None,
        details: Optional[str] = None,
    ):
        super().__init__(message=message, hint=hint, exit_code=ExitCode.FORBIDDEN, details=details)


class NotFoundError(NexusError):
    def __init__(
        self,
        message: str = "Requested resource not found.",
        hint: Optional[str] = None,
        details: Optional[str] = None,
    ):
        super().__init__(message=message, hint=hint, exit_code=ExitCode.NOT_FOUND, details=details)


class NetworkError(NexusError):
    def __init__(
        self,
        message: str,
        hint: Optional[str] = "Verify the NEXUS Core server is online using 'nexus status' or 'nexus doctor'.",
        details: Optional[str] = None,
    ):
        super().__init__(message=message, hint=hint, exit_code=ExitCode.NETWORK_ERROR, details=details)


class TimeoutError(NexusError):
    def __init__(
        self,
        message: str = "API request timed out.",
        hint: Optional[str] = "Check connection latency or increase NEXUS_TIMEOUT.",
        details: Optional[str] = None,
    ):
        super().__init__(message=message, hint=hint, exit_code=ExitCode.TIMEOUT, details=details)


class ConfigurationError(NexusError):
    def __init__(
        self,
        message: str,
        hint: Optional[str] = None,
        details: Optional[str] = None,
    ):
        super().__init__(message=message, hint=hint, exit_code=ExitCode.USAGE_ERROR, details=details)
