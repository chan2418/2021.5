""""""

import fx
from fx import Layer

from .exceptions import InvalidLabelException, NoChildrenException


def validate_active_node():
    """"""
    node = fx.activeNode()
    if node is None:
        raise Exception("No active node found. Please select a Roto node.")
    return node


def validate_selection():
    """"""
    selection = fx.selection()
    if not selection:
        raise Exception("Nothing selected. Please select a layer first.")
    return selection


def validate_layer(selection):
    """"""
    selected_layer = selection[0]

    if not isinstance(selected_layer, Layer):
        raise Exception("Selected object is not a Layer. Please select a valid layer.")
    if not selected_layer.label:
        raise InvalidLabelException("Selected layer has no name.")
    if not selected_layer.children:
        raise NoChildrenException(
            "Selected layer '" + selected_layer.label + "' has no children to rename."
        )
    return selected_layer
