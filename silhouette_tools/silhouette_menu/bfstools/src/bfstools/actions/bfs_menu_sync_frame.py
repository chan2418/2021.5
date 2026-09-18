""""""

from fx import Action, addAction
from sync_task_frame.main import sg_task_frame

from bfstools.core.constants import ROOT_MENU


class SyncTaskFrame(Action):
    def __init__(self):
        Action.__init__(self, label="Sync Task Frame", root=ROOT_MENU)

    def available(self):
        assert "Create First Project"

    def execute(self):
        sg_task_frame()


addAction(SyncTaskFrame())
