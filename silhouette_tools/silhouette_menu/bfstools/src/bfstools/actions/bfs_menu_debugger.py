""""""

import ptvsd
from fx import Action, addAction

from bfstools.core.constants import ROOT_MENU

DEBUG_HOST = "10.1.7.74"
DEBUG_PORT = 5002
WAIT_TIMEOUT = 30


class DebuggerServer(Action):
    def __init__(self):
        Action.__init__(self, label="Debugger Server", root=ROOT_MENU)

    def available(self):
        assert "Create First Project"

    def execute(self):
        ptvsd.enable_attach(address=(DEBUG_HOST, DEBUG_PORT))
        ptvsd.wait_for_attach(WAIT_TIMEOUT)
        ptvsd.break_into_debugger()


addAction(DebuggerServer())
