""""""

from fx import Action, addAction
from my_task.main import TaskListCheck
from PySide2.QtWidgets import QApplication

from bfstools.core.constants import ROOT_MENU


class MyTask(Action):
    def __init__(self):
        Action.__init__(self, label="My Task", root=ROOT_MENU)

    def available(self):
        assert "Create First Project"

    def execute(self):
        QApplication.instance()
        task = TaskListCheck()
        task.exec_()


addAction(MyTask())
