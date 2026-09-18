""""""

from fx import Action, addAction
from my_task.main import TaskListCheck

from bfstools.core.constants import ROOT_MENU


class SaveNextVersion(Action):
    def __init__(self):
        Action.__init__(self, label="Save As Next Version", root=ROOT_MENU)

    def available(self):
        assert "Create First Project"

    def execute(self):
        TaskListCheck().save_project()


addAction(SaveNextVersion())
