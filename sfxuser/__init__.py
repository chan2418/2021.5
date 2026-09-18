import os
import sys

# import sfx_mount_remapper

if os.environ["SILHOUETTE_VER"] == "2021.5":
    import glob
    from os.path import basename, dirname, isfile, join

    modules = glob.glob(join(dirname(__file__), "*.py"))
    __all__ = [
        basename(f)[:-3] for f in modules if isfile(f) and not f.endswith("__init__.py")
    ]
    print("***************** Inside main init file ******************** ")

    import getpass

    lst_of_users = [
        "ilambharathi",
    ]

    current_user = getpass.getuser()
    if current_user != "chandru":
        print("Silhouette script called user ___________^^^^^^^^^^______________")
        import silhouette_idle_monitor

        print("current_user:", current_user)
        silhouette_idle_monitor.start_idle_monitor()

if os.environ["SILHOUETTE_VER"] == "7" or os.environ["SILHOUETTE_VER"] == "5":
    import os
    import os.path
    import sys

    sys.path.insert(0, r"D:\pipelineCodes\global_silhouette_menu\sfxsite")
    scripts = []
    possible = []
    contents = os.listdir(__path__[0])

    for content in contents:
        if (
            content in ["__init__.py", "__init__.pyc", "__pycache__"]
            or ".pyc" in content
        ):
            continue

        s = "import " + content.split(".")[0]
        exec(s)
