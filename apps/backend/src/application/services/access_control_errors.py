"""Stable application errors for user and role administration."""


class AccessControlNotFoundError(ValueError):
    """Raised when a managed user or role does not exist."""


class AccessControlConflictError(ValueError):
    """Raised when a unique or assignment invariant would be violated."""


class AccessControlValidationError(ValueError):
    """Raised when input violates the access-control policy."""
