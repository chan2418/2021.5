# import importlib.util
# import os
# from contextlib import contextmanager

# import fx


# @contextmanager
# def add_to_path(p):
#     import sys

#     old_path = sys.path
#     sys.path = sys.path[:]
#     sys.path.insert(0, p)
#     try:
#         yield
#     finally:
#         sys.path = old_path


# import pathlib

# from actions import *
# from extensions import *
# from hooks import *
# from resolvers import *

# if fx.gui:
#     from gui import *
#     from templates import *

# try:
#     from sfxsite import *
# except:
#     pass

# try:
#     from sfxuser import *
# except:
#     pass

# # import external script paths - they should contain their own '__init__.py'
# if fx.prefs["scripting.enableExternal"]:
#     external_paths = fx.prefs["scripting.scriptPaths"]
#     for path in external_paths:
#         if len(path) != 0 and pathlib.Path(path).exists():
#             print("Loading external scripts from path:", path)
#             with add_to_path(path):
#                 path = os.path.join(path, "__init__.py")
#                 spec = importlib.util.spec_from_file_location(path, path)
#                 module = importlib.util.module_from_spec(spec)
#                 spec.loader.exec_module(module)

# # load user keybinds at the end, in case some of them bind to actions
# if fx.gui:
#     try:
#         pass
#     except:
#         pass

# """

# 	Calling Autosave save script to save the workfile for every 5 mins in local dir
# 	~/SilhouetteAutosaves/
#     MyProject/
#         20231010_123045/
#             MyProject.silhouette
#         20231010_124050/
#             MyProject.silhouette
#         20231010_125055/
#             MyProject.silhouette
#         ...

# """
# script_path = "/tools/common/scripts/silhouette_autosave_script.py"

# try:
#     with pathlib.Path(script_path).open("r") as file:
#         script_code = file.read()

#     exec(script_code)
#     print(f"Script '{script_path}' executed successfully.")
# except Exception as e:
#     print(f"An error occurred while executing the script: {e}")


print(
    "******************************* Running in server  *****************************"
)
import getpass

lst_of_users = [
    "prasad.jairam",
    # "ilambharathi",
    # "manikanda.srinivasulu",
    # "kalaiselvan.j",
    # "arunkumar.p",
    # "shybin.benny",
    # "suriya.prakash",
    # "mugesh.jothikrishnan",
    # "vignesh.elumalai",
    # "anandhakumar.vijayakumar",
    # "vignesh.suresh",
    # "prasanth.p",
    # "kunal.lahiri",
    # "ranjithkumar.m",
]

current_user = getpass.getuser()
print("current_user:", current_user)
# Create and keep a persistent global reference
if current_user in lst_of_users:
    import silhouette_idle_monitor

    print(
        "--------------------------- Start Silhouette Idle Monitor ---------------------------"
    )
    silhouette_idle_monitor.start_idle_monitor()
