""""""

from fx import Action, addAction
from my_task.main import TaskListCheck

from bfstools.core.constants import ROOT_MENU


class PublishOutputNode(Action):
    def __init__(self):
        Action.__init__(self, label="Publish Output Node", root=ROOT_MENU)

    def available(self):
        assert "Create First Project"

    def execute(self):
        TaskListCheck().custom_node_create("publish")


addAction(PublishOutputNode())
