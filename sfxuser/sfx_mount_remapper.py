""""""

# DCC Imports
import fx

_PATH_REMAPS = [
    ("/brahmos/projects", "/projects"),
    # ("/old/root", "/new/root"),
]


def remap_path(path):
    """Return path with the first matching prefix swapped out, or path unchanged."""
    if not path:
        return path
    for old, new in _PATH_REMAPS:
        if path.startswith(old):
            return new + path[len(old) :]
    return path


def log_remap(dcc, node_name, knob_or_attr, old, new):
    print(
        "[PathRemap:{dcc}] {node_name}.{knob_or_attr}  {old} {new}".format(
            dcc=dcc, node_name=node_name, knob_or_attr=knob_or_attr, old=old, new=new
        )
    )


"""
silhouette/path_remap.py

Remaps file paths in the active Silhouette project.

This file serves two purposes:

  1. STARTUP SCRIPT (automatic, runs on every project load)
     Deploy: copy to the Silhouette startup-scripts folder.
       Windows : %APPDATA%\\Boris FX\\Silhouette\\startup\\
       macOS   : ~/Library/Application Support/Boris FX/Silhouette/startup/
     The fx.events.connect() call at the bottom registers the callback so
     it fires automatically whenever a project is opened.

  2. ACTION (manual trigger from the Scripts menu)
     Deploy: copy to the Silhouette user-scripts folder.
       Windows : %APPDATA%\\Boris FX\\Silhouette\\scripts\\
       macOS   : ~/Library/Application Support/Boris FX/Silhouette/scripts/
     The file name becomes the menu entry. Running it calls _remap_project()
     immediately on the currently open project.
"""


def update_source_mount():
    """"""
    project = fx.activeProject()
    print("Current_project : ", project)
    sources = [] if project is None else project.sources
    for each_source in sources:
        node_name = each_source.properties.get("name")
        path_property = each_source.properties.get("path")
        current_src_path = path_property.value
        updated_mount_path = remap_path(current_src_path)
        if updated_mount_path != current_src_path:
            log_remap(
                "Silhouette",
                getattr(node_name, "label", repr(node_name)),
                "path",
                current_src_path,
                updated_mount_path,
            )
        if current_src_path != updated_mount_path:
            path_property.setValue(updated_mount_path)
            print("Sources path updated..!!")


def remap_project():

    update_source_mount()


# --- Startup-script usage: register callback so it fires on every project load.
fx.hooks["project_selected"] = remap_project
print("[PathRemap:Silhouette] project_selected callback registered.")
