""""""

# Local imports
from bfs_renamer.exceptions import BfsRenamerException


class RenamerException(BfsRenamerException):
    """Base exception for renamer module."""

    pass


class InvalidLabelException(RenamerException):
    """Raised when a layer or shape has no valid label."""

    pass


class NoChildrenException(RenamerException):
    """Raised when selected layer has no children to rename."""

    pass
