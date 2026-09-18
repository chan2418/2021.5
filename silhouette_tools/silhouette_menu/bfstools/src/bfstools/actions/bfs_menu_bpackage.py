""""""

from fx import Action, addAction
from my_task.package_creation.package_creation import PackagingUI

from bfstools.core.constants import ROOT_MENU

_widget = None


class BPackage(Action):
    def __init__(self):
        Action.__init__(self, label="BPackage", root=ROOT_MENU)

    def available(self):
        assert "Create First Project"

    def execute(self):
        global _widget
        _widget = PackagingUI()


addAction(BPackage())
