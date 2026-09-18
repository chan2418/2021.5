import sys

import fx

sys.path.append("/apps/silhouette/Silhouette-2023.5/resources/scripts/")

import os

from fx import *
from tools.objectIterator import ObjectFinder


def disable_motion_blur():
    session = fx.activeSession()
    roto_nodes = session.getNodes("RotoNode")
    for roto_node in roto_nodes:
        roto_node.property("motionBlur.enable").setValue(False)


def disable_blur_recursive(item):
    """
    Recursively traverse roto node children
    and disable blur property if it exists.
    """
    try:
        # Check if this item has blur property
        blur_prop = item.property("blur")
        if blur_prop is not None:
            blur_prop.setValue(0)
    except Exception:
        pass  # Ignore if property doesn't exist

    # Traverse children
    try:
        for child in item.children:
            disable_blur_recursive(child)
    except Exception:
        pass


def nuke_shape_export_nmb(
    shape_export_dir=None,
):
    """Export non-motion blurred Roto shapes from the temporary headless SFX project."""
    shape_export_dir = "/home/" + os.getlogin() + "/tmp/roto_packaging/roto_shapes"

    os.makedirs(shape_export_dir, exist_ok=True)
    session = fx.activeSession()
    roto_nodes = session.getNodes("RotoNode")
    sil_exporter = fx.io_modules.get("Nuke 9+ Shapes")

    for roto_node in roto_nodes:
        layers = roto_node.children
        if not layers:
            continue
        top_layername = layers[0].label
        selected_object = select_all(roto_node)

        nmb_shape_file = os.path.join(
            shape_export_dir, "{0}_nmb.nk".format(top_layername)
        )

        try:
            viewer.node = roto_node
        except Exception:
            pass
        select(selected_object)

        if sil_exporter and sil_exporter.can_export:
            if os.path.exists(nmb_shape_file):
                try:
                    os.remove(nmb_shape_file)
                except Exception:
                    pass
            sil_exporter.export(nmb_shape_file)
            print("[fx_command] Exported NMB shape -> {0}".format(nmb_shape_file))
            select([])


def disable_blur():
    session = fx.activeSession()
    roto_nodes = session.getNodes("RotoNode")

    for roto_node in roto_nodes:
        disable_blur_recursive(roto_node)


def select_all(node):
    node = node
    if node:
        finder = ObjectFinder(hidden=False)
        objects = finder.find(node.children)
        objects.append(node)
        return objects


def nuke_shape_export(nmb_nuke_path):
    session = fx.activeSession()
    roto_nodes = session.getNodes("RotoNode")
    for roto_node in roto_nodes:
        layers = roto_node.children
        top_layername = layers[0].label
        selected_object = select_all(roto_node)
        print(top_layername)
        nuke_path = nmb_nuke_path[str(top_layername)]
        print("nuke_path_", nuke_path)
        select(selected_object)
        sil_exporter = fx.io_modules["Nuke 9+ Shapes"]
        print(sil_exporter.can_export)
        if sil_exporter.can_export:
            sil_exporter.export(nuke_path)
            select([])


def set_output_path(output_paths):
    project = fx.activeProject()
    for session in project.sessions:
        for output in session.outputs:
            print(output_paths[output.label])
            output.properties["path"].value = output_paths[output.label]
            print("Setting the file path of the Publish Output Node...")
            print(output.properties["path"].value)
    disable_motion_blur()
    disable_blur()

    # try:
    #     nuke_shape_export_nmb()
    # except Exception as e:
    #     print("[fx_command] NMB shape export warning: {0}".format(e))

    # nuke_shape_export(output_paths)
    project.save()


if __name__ == "__main__":
    print("FX Command script starting...")
    args = sys.argv
    arg_str = args
    result_dict = {}
    for item in arg_str:
        # Clean up the string to extract key-value pairs
        cleaned = item.replace("{", "").replace("}", "").strip()
        if not cleaned:
            continue

        # Extract key and value
        parts = cleaned.split(":", 1)
        if len(parts) == 2:
            key = parts[0].strip().strip('"')
            value = parts[1].strip().strip('"')
            result_dict[key] = value

    print(result_dict)
    set_output_path(result_dict)
