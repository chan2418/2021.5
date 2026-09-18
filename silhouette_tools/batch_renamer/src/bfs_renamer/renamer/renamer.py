""""""

from fx import Layer, Shape

# Local imports
from .exceptions import InvalidLabelException
from .utils import format_label


class LayerRenamer:
    """"""

    def __init__(self, base_label):
        self.base_label = base_label
        self.layer_counter = [1]
        self.shape_counter = [1]

    def rename(self, parent):
        """"""
        for child in parent.children:
            if isinstance(child, Layer):
                if not hasattr(child, "label"):
                    raise InvalidLabelException(
                        "Layer object has no label attribute: " + str(child)
                    )
                child.label = format_label(self.base_label, self.layer_counter[0])
                self.layer_counter[0] += 1
                self.rename(child)

            elif isinstance(child, Shape):
                if not hasattr(child, "label"):
                    raise InvalidLabelException(
                        "Shape object has no label attribute: " + str(child)
                    )
                child.label = format_label(self.base_label, self.shape_counter[0])
                self.shape_counter[0] += 1

    @property
    def total_layers_renamed(self):
        """"""
        return self.layer_counter[0] - 1

    @property
    def total_shapes_renamed(self):
        """"""
        return self.shape_counter[0] - 1
