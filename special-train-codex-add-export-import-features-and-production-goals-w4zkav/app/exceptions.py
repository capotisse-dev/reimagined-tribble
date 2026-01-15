class PermissionDenied(Exception):
    """Raised when a user lacks permission for an action."""


class ValidationError(Exception):
    """Raised when incoming data fails validation."""


class NotFoundError(Exception):
    """Raised when a requested entity cannot be found."""
