import sys

from fx import *

# import silhouette
# if fx.gui:
# 	import keybinds
# 	from gui import *
# 	from templates import *


class BFS_Menu_4(Action):
    def __init__(self):
        Action.__init__(
            self,
            label="Review Output Node         ",
            root="BFSTOOLS",
        )

    def available(self):
        assert "Create First Project"

    def execute(self):
        from my_task.main import TaskListCheck

        task_list_check = TaskListCheck()
        task_list_check.custom_node_create("review")


addAction(BFS_Menu_4())


class BFS_Menu_5(Action):
    def __init__(self):
        Action.__init__(self, label="Publish Output Node         ", root="BFSTOOLS")

    def available(self):
        assert "Create First Project"

    def execute(self):
        from my_task.main import TaskListCheck

        task_list_check = TaskListCheck()
        task_list_check.custom_node_create("publish")


addAction(BFS_Menu_5())


class BFS_Menu_6(Action):
    def __init__(self):
        Action.__init__(self, label="Save AS Next Version       ", root="BFSTOOLS")

    def available(self):
        assert "Create First Project"

    def execute(self):
        from my_task.main import TaskListCheck

        task_list_check = TaskListCheck()
        task_list_check.save_project()


addAction(BFS_Menu_6())


class BFS_Menu_7(Action):
    def __init__(self):
        Action.__init__(
            self, label="Publish                               ", root="BFSTOOLS"
        )

    def available(self):
        assert "Create First Project"

    def execute(self):
        from my_task.main import TaskListCheck

        task_list_check = TaskListCheck()
        task_list_check.call_back()


addAction(BFS_Menu_7())


class BFS_Menu_3(Action):
    def __init__(self):
        Action.__init__(
            self, label="My Task                              ", root="BFSTOOLS"
        )

    def available(self):
        assert "Create First Project"

    def execute(self):
        from PySide2.QtWidgets import QApplication

        from my_task.main import TaskListCheck

        app = QApplication.instance()
        bfsren = TaskListCheck()
        bfsren.exec_()


addAction(BFS_Menu_3())


class BFS_Menu_8(Action):
    def __init__(self):
        Action.__init__(
            self, label="BPackage                           ", root="BFSTOOLS"
        )

    def available(self):
        assert "Create First Project"

    def execute(self):
        from my_task.package_creation import package_creation

        global widget
        widget = package_creation.PackagingUI()


# B=BFS_Menu_8()
# addAction(B)
addAction(BFS_Menu_8())
# fx.bind("Alt+e", B)
# silhouette.ui.addAction(BFS_Menu_8(),shortcut="Ctrl+Shift+P")


class BFS_Menu_9(Action):
    def __init__(self):
        Action.__init__(
            self, label="Sync Task Frame                              ", root="BFSTOOLS"
        )

    def available(self):
        assert "Create First Project"

    def execute(self):
        sys.path.append("/tools/bpipe/")
        from sync_task_frame import main

        main.sg_task_frame()

        # from PySide2.QtWidgets import QApplication
        # from menu_script import menu_script
        # menu_script.sg_task_frame()


addAction(BFS_Menu_9())


class BFS_Menu_13(Action):
    def __init__(self):
        Action.__init__(
            self, label="My Task_sync                             ", root="BFSTOOLS"
        )

    def available(self):
        assert "Create First Project"

    def execute(self):
        from PySide2.QtWidgets import QApplication

        from my_task.main import TaskListCheck

        app = QApplication.instance()
        bfsren = TaskListCheck()
        bfsren.exec_()


addAction(BFS_Menu_13())


# class BFS_Menu_StagingBPackage(Action):
#     def __init__(self):
#         Action.__init__(self, label="Staging BPackage", root="BFSTOOLS")

#     def available(self):
#         assert "Create First Project"

#     def execute(self):
#         from my_task.package_creation import package_creation_test

#         global widget
#         widget = package_creation_test.PackagingUI()


# addAction(BFS_Menu_StagingBPackage())


class BFS_Menu_33(Action):
    def __init__(self):
        Action.__init__(
            self,
            label="debugger Server                           ",
            root="BFSTOOLS",
        )

    def available(self):
        assert "Create First Project"

    def execute(self):
        """"""
        sys.path.insert(
            1,
            r"/tools/dev_team/portable_application/rocky/python/Python-3.9.11/lib/python3.9/site-packages",
        )
        import ptvsd

        ptvsd.enable_attach(address=("0.0.0.0", 5002))
        ptvsd.wait_for_attach(30)
        ptvsd.break_into_debugger()


addAction(BFS_Menu_33())


class BFS_Menu_Renamer(Action):
    def __init__(self):
        Action.__init__(
            self,
            label="Layer Renamer                        ",
            root="BFSTOOLS",
        )

    def available(self):
        assert "Create First Project"

    def execute(self):
        sys.path.insert(
            1,
            r"/tools/silhouette_tools/2021.5/silhouette_tools/batch_renamer/src",
        )
        from bfs_renamer.actions.rename_layers import RenameLayersAction

        renamer_action = RenameLayersAction()
        renamer_action.execute()


addAction(BFS_Menu_Renamer())


class BFS_Menu_PathReplace(Action):
    def __init__(self):
        Action.__init__(
            self,
            label="Path Find & Replace                  ",
            root="BFSTOOLS",
        )

    def available(self):
        assert "Create First Project"

    def execute(self):
        import os

        # Ensure the path_replace package is importable (dev tree next to sfxuser)
        tools_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if tools_root not in sys.path:
            sys.path.insert(0, tools_root)
        from path_replace.main import show

        show()


addAction(BFS_Menu_PathReplace())

# add_option_to_menu(debug_menu, "Start Debug Server", enable_debugger_server, "")


# add_option_to_menu(debug_menu, "Start Debug Server", enable_debugger_server, "")
