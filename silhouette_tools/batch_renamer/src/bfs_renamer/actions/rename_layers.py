""""""

# 3rd party imports
import fx

# Local imports
from bfs_renamer.actions.constants import ACTION_NAME
from bfs_renamer.actions.exceptions import ActionException
from bfs_renamer.renamer.renamer import LayerRenamer
from bfs_renamer.renamer.validators import (
    validate_active_node,
    validate_layer,
    validate_selection,
)


class RenameLayersAction(fx.Action):
    def __init__(self):
        fx.Action.__init__(
            self,
            label="Layer Renamer                        ",
            root="BFSTOOLS",
        )

    def available(self):
        assert "Create First Project"

    def execute(self):
        try:
            validate_active_node()
            selection = validate_selection()
            selected_layer = validate_layer(selection)

            renamer = LayerRenamer(base_label=selected_layer.label)

            fx.beginUndo(ACTION_NAME)
            renamer.rename(selected_layer)
            fx.endUndo()

        except Exception as e:
            fx.endUndo()
            raise ActionException("RenameLayersAction failed: " + str(e))
