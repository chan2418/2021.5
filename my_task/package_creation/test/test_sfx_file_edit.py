import os
import sys
import uuid
import xml.etree.ElementTree as ET

import fx

sys.path.append("/apps/silhouette/Silhouette-2023.5/resources/scripts/")
from fx import *


def print_tree(session, label="current tree"):
    roto_nodes = session.getNodes("RotoNode")
    print(f"\n=== {label} ({len(roto_nodes)} roto nodes) ===")
    for node in roto_nodes:
        print(f"  node: '{node.label}'")
        for child in node.children:
            print(f"    └── '{child.label}'")
            for sub in child.children:
                print(f"          └── '{sub.label}'")
    print("=" * 50 + "\n")


def collect_connections(roto_nodes, session):
    connections = {"inputs": []}

    for roto_node in roto_nodes:
        for port in roto_node.connectedInputs:
            for pipe in port.pipes:
                source_port = pipe.source
                source_node = source_port.node
                connections["inputs"].append(
                    {
                        "source_node_id": source_node.id,
                        "source_port_name": source_port.name,
                        "target_port_name": port.name,
                    }
                )
                print(
                    f"  saved input connection: '{source_node.label}'.{source_port.name} -> roto.{port.name}"
                )

    return connections


def rewire_connections(new_roto_node, connections, session):
    print("\n  rewiring connections...")

    for conn in connections["inputs"]:
        source_node = fx.findObject(conn["source_node_id"])
        if not source_node:
            print(f"  could not find source node {conn['source_node_id']}, skipping")
            continue
        try:
            source_port = source_node.port(conn["source_port_name"])
            target_port = new_roto_node.port(conn["target_port_name"])
            source_port.connect(target_port)
            print(
                f"  connected '{source_node.label}'.{conn['source_port_name']} -> roto.{conn['target_port_name']}"
            )
        except Exception as e:
            print(f"  input connection failed: {e}")


def build_layer_properties_elem(props_parent):
    standard_props = [
        ("note", "True", None, ""),
        ("color", "True", None, "(1.000000,1.000000,1.000000)"),
        ("transform", "True", None, ""),
        ("transform.anchor", "True", None, "(0.000000000,0.000000000,0.000000000)"),
        ("transform.position", "True", None, "(0.000000000,0.000000000,0.000000000)"),
        ("transform.scale", "True", "True", "(1.000000000,1.000000000,1.000000000)"),
        ("transform.rotate", "True", None, "0"),
        ("transform.pin", "True", None, ""),
        ("transform.pin_ul", "True", None, "(0.000000000,0.000000000,0.000000000)"),
        ("transform.pin_ur", "True", None, "(1.000000000,0.000000000,0.000000000)"),
        ("transform.pin_lr", "True", None, "(1.000000000,1.000000000,0.000000000)"),
        ("transform.pin_ll", "True", None, "(0.000000000,1.000000000,0.000000000)"),
        ("transform.surface", "True", None, ""),
        ("transform.surface_ul", "True", None, "(0.000000000,0.000000000,0.000000000)"),
        ("transform.surface_ur", "True", None, "(1.000000000,0.000000000,0.000000000)"),
        ("transform.surface_lr", "True", None, "(1.000000000,1.000000000,0.000000000)"),
        ("transform.surface_ll", "True", None, "(0.000000000,1.000000000,0.000000000)"),
        ("transform.matrix", "True", None, ""),
        ("stereoOffset", None, None, "(0.000000000,0.000000000,0.000000000)"),
        ("trackSource", None, None, "0"),
    ]
    for prop_id, constant, gang, value in standard_props:
        prop = ET.SubElement(props_parent, "Property")
        prop.set("id", prop_id)
        if constant:
            prop.set("constant", constant)
        if gang:
            prop.set("gang", gang)
        ET.SubElement(prop, "Value").text = value


def build_combined_node_xml(exported_layer_files, base_node_uuid):
    objects_root = ET.Element("Objects")

    roto_obj = ET.SubElement(objects_root, "Object")
    roto_obj.set("type", "RotoNode")
    roto_obj.set("id", "0")
    roto_obj.set("label", "Roto1")
    roto_obj.set("expanded", "True")
    roto_obj.set("uuid", base_node_uuid)
    roto_obj.set("active", "True")

    node_props = ET.SubElement(roto_obj, "Properties")

    for prop_id, constant, value in [
        ("note", "True", ""),
        ("obey_matte.obey", "True", "false"),
        ("obey_matte.invert", "True", "false"),
        ("obey_matte.channel", "True", "Alpha"),
        ("node.format", "True", "Session"),
        ("node.dod", "True", ""),
    ]:
        prop = ET.SubElement(node_props, "Property")
        prop.set("id", prop_id)
        if constant:
            prop.set("constant", constant)
        ET.SubElement(prop, "Value").text = value

    prop = ET.SubElement(node_props, "Property")
    prop.set("id", "obey_matte.opacity")
    ET.SubElement(prop, "Value").text = "100"

    prop = ET.SubElement(node_props, "Property")
    prop.set("id", "markers")
    ET.SubElement(prop, "Value").text = ""

    node_objects_prop = ET.SubElement(node_props, "Property")
    node_objects_prop.set("id", "objects")
    node_objects_prop.set("expanded", "True")
    node_objects_prop.set("constant", "True")

    main_layer_obj = ET.SubElement(node_objects_prop, "Object")
    main_layer_obj.set("type", "Layer")
    main_layer_obj.set("id", "1")
    main_layer_obj.set("label", "main_layer")
    main_layer_obj.set("expanded", "True")
    main_layer_obj.set("uuid", str(uuid.uuid4()))

    main_layer_props = ET.SubElement(main_layer_obj, "Properties")
    build_layer_properties_elem(main_layer_props)

    main_objects_prop = ET.SubElement(main_layer_props, "Property")
    main_objects_prop.set("id", "objects")
    main_objects_prop.set("expanded", "True")
    main_objects_prop.set("constant", "True")

    for i, xml_file in enumerate(exported_layer_files):
        tree = ET.parse(xml_file)
        root = tree.getroot()
        for obj in root.findall("Object"):
            obj.set("id", str(i + 2))
            print(f"    nesting '{obj.get('label')}' inside main_layer")
            main_objects_prop.append(obj)

    for prop_id, value in [
        ("mode", "Add"),
        ("blur", "0"),
        ("blurType", "Centered"),
        ("opacity", "100"),
        ("invert", "false"),
        ("channel", "Alpha"),
    ]:
        prop = ET.SubElement(main_layer_props, "Property")
        prop.set("id", prop_id)
        prop.set("constant", "True")
        ET.SubElement(prop, "Value").text = value

    for prop_id, constant, value in [
        ("alpha", "True", ""),
        ("alpha.preserve", "True", "false"),
        ("alpha.invert", "True", "false"),
        ("color", "True", ""),
        ("color.enable", "True", "false"),
        ("motionBlur", "True", ""),
        ("motionBlur.enable", "True", "false"),
        ("motionBlur.shutterAngle", "True", "180"),
        ("motionBlur.shutterPhase", "True", "-90"),
        ("motionBlur.samples", "True", "16"),
        ("antialias", "True", "true"),
    ]:
        prop = ET.SubElement(node_props, "Property")
        prop.set("id", prop_id)
        if constant:
            prop.set("constant", constant)
        ET.SubElement(prop, "Value").text = value

    prop = ET.SubElement(node_props, "Property")
    prop.set("id", "alpha.blur")
    ET.SubElement(prop, "Value").text = "0"

    prop = ET.SubElement(node_props, "Property")
    prop.set("id", "color.outline")
    ET.SubElement(prop, "Value").text = "0"

    prop = ET.SubElement(node_props, "Property")
    prop.set("id", "color.opacity")
    ET.SubElement(prop, "Value").text = "0"

    ports = ET.SubElement(roto_obj, "Ports")
    for port_id, flags in [
        ("obey_matte", "32777"),
        ("foreground", "1"),
        ("background", "1"),
        ("output", "2"),
        ("colorComp", "6"),
        ("composite", "6"),
        ("channels", "6"),
        ("objects", "18"),
    ]:
        port = ET.SubElement(ports, "Port")
        port.set("id", port_id)
        port.set("flags", flags)

    return objects_root


def clean_up_node():
    session = fx.activeSession()
    nodes = session.nodes
    positions = {}
    for node in nodes:
        positions[node] = node.getState("graph.pos")

    new_positions = {}
    for node in nodes:
        new_positions[node] = node.getState("graph.pos")
        node.setState("graph.pos", positions[node])

    fx.beginUndo("Auto Layout Nodes")

    for node in new_positions:
        pos = new_positions[node]
        node.setState("graph.pos", pos)

    fx.endUndo()
    fx.activeProject().save()


def remove_output_node():
    project = fx.activeProject()
    session = fx.activeSession()
    roto_nodes = session.getNodes("OutputNode")

    for i in roto_nodes:
        session.removeNode(i)


def merge_roto_nodes_into_one(output_project_path):
    project = fx.activeProject()
    session = fx.activeSession()
    roto_nodes = session.getNodes("RotoNode")

    print_tree(session, label="BEFORE MERGE")

    if not roto_nodes:
        print("no roto nodes found, nothing to do")
        return

    if len(roto_nodes) == 1:
        print("only one roto node — still connecting to all output nodes")
        rewire_connections(
            roto_nodes[0], collect_connections(roto_nodes, session), session
        )
        project.save(output_project_path)
        return

    print(f"found {len(roto_nodes)} roto nodes — starting merge...")

    # save all connections before removing anything
    print("\n  collecting connections...")
    connections = collect_connections(roto_nodes, session)

    tmp_dir = "/tmp/sfx_merge"
    os.makedirs(tmp_dir, exist_ok=True)

    base_node_uuid = roto_nodes[0].id

    # export all top layers
    exported_layer_files = []
    for i, node in enumerate(roto_nodes):
        if not node.children:
            print(f"  skipping '{node.label}' — no children")
            continue
        top_layer = node.children[0]
        tmp_path = os.path.join(tmp_dir, f"layer_{i}.xml")
        fx.exportObjects(tmp_path, [top_layer])
        print(f"  exported '{top_layer.label}' from '{node.label}'")
        exported_layer_files.append(tmp_path)

    if not exported_layer_files:
        print("nothing to export, aborting")
        return

    # build combined node xml
    print("\n  building combined node xml...")
    combined_xml = build_combined_node_xml(exported_layer_files, base_node_uuid)
    combined_path = os.path.join(tmp_dir, "combined_node.xml")

    with open(combined_path, "w") as f:
        f.write("<!-- Silhouette Objects -->\n")
        f.write(ET.tostring(combined_xml, encoding="unicode"))

    print(f"  xml written — {os.path.getsize(combined_path)} bytes")

    # remove all roto nodes
    print("\n  removing all existing roto nodes...")
    for node in roto_nodes:
        session.removeNode(node)
        print(f"  removed '{node.label}'")

    # import fresh merged node and add to session

    result = fx.importObjects(combined_path)

    if not result:
        print("  import returned nothing, aborting")
        return

    new_roto_node = result[0]
    session.addNode(new_roto_node)
    print(f"  added '{new_roto_node.label}' to session")
    print(f"  children: {[c.label for c in new_roto_node.children]}")

    if new_roto_node.children:
        main = new_roto_node.children[0]
        print(f"  main_layer children: {[c.label for c in main.children]}")

    # rewire all connections to the merged node
    rewire_connections(new_roto_node, connections, session)
    remove_output_node()
    clean_up_node()

    print_tree(session, label="AFTER MERGE — before save")

    project.save(output_project_path)
    print(f"\ndone — saved to: {output_project_path}")


if __name__ == "__main__":
    print("FX Command script starting...")

    args = sys.argv
    result_dict = {}

    for item in args:
        cleaned = item.replace("{", "").replace("}", "").strip()
        if not cleaned:
            continue
        parts = cleaned.split(":", 1)
        if len(parts) == 2:
            key = parts[0].strip().strip('"')
            value = parts[1].strip().strip('"')
            result_dict[key] = value

    print(f"parsed args: {result_dict}")

    output_project_path = result_dict.get("output_project_path")
    if not output_project_path:
        print("no output_project_path found in args, exiting")
        sys.exit(1)

    merge_roto_nodes_into_one(output_project_path)
