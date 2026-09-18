""""""

from fx import Action, addAction
from my_task.main import TaskListCheck

from bfstools.core.constants import ROOT_MENU


class ReviewOutputNode(Action):
    def __init__(self):
        Action.__init__(self, label="Review Output Node", root=ROOT_MENU)

    def available(self):
        assert "Create First Project"

    def execute(self):
        TaskListCheck().custom_node_create("review")


addAction(ReviewOutputNode())
