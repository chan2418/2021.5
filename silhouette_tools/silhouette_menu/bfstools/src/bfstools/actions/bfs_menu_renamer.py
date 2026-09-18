""""""

from bfs_renamer.actions.rename_layers import RenameLayersAction
from fx import Action, addAction

from bfstools.core.constants import ROOT_MENU


class LayerRenamer(Action):
    def __init__(self):
        Action.__init__(self, label="Layer Renamer", root=ROOT_MENU)

    def available(self):
        assert "Create First Project"

    def execute(self):
        RenameLayersAction().execute()


addAction(LayerRenamer())
