import json
import os

CHANNEL_MAP = {0: "red", 1: "green", 2: "blue"}


def render_layer_wise(
    layer_dict, first, last, tmp_path, nuke_path, nuke_home, input_path
):
    """
    Submit ONE Deadline job per SHAPE.
    Each job renders its level3 layers, merges them, and writes ONE
    per-channel merged matte exr (e.g. bubbles_red.%04d.exr).
    """
    deadline_scripts = []
    packed_paths = {}  # kept for signature compatibility (unused)
    channel_merge_paths = {}  # nk_path -> per-shape merged matte exr

    for final_path, shape_list in layer_dict.items():
        group_name = os.path.basename(final_path)
        out_folder = os.path.join(tmp_path, "layer_renders", group_name)
        os.makedirs(out_folder, exist_ok=True)

        print(
            "\n[layer_wise_render] Group: {}  shapes: {}".format(
                group_name, len(shape_list)
            )
        )

        # ── ONE JOB PER SHAPE ──────────────────────────────────────────
        for shape in shape_list:
            nk_path = shape["path"]
            nk_name = os.path.splitext(os.path.basename(nk_path))[0]
            ch_name = CHANNEL_MAP.get(shape.get("channel"), "unknown")
            shape_tag = "{}_{}".format(nk_name, ch_name)

            shape_folder = os.path.join(out_folder, shape_tag)
            os.makedirs(shape_folder, exist_ok=True)

            shape_merge_folder = os.path.join(shape_folder, "shape_merge")
            os.makedirs(shape_merge_folder, exist_ok=True)

            merged_path = os.path.join(
                shape_merge_folder, "{}.%04d.exr".format(shape_tag)
            )
            channel_merge_paths[nk_path] = merged_path

            manifest = {
                "shape": nk_name,
                "channel_index": shape.get("channel"),
                "channel_name": ch_name,
                "final_output_group": final_path,
                "merged_path": merged_path,
            }
            manifest_path = os.path.join(shape_folder, "channel_info.json")
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)

            exec_script = _write_nuke_exec_script(
                shape, shape_tag, out_folder, input_path
            )
            sh_path = _write_deadline_sh(shape_tag, exec_script, nuke_path, nuke_home)
            deadline_scripts.append(sh_path)
            print("[layer_wise_render] ready: {}".format(sh_path))

    print("[layer_wise_render] Total: {} scripts".format(len(deadline_scripts)))
    return deadline_scripts, packed_paths, channel_merge_paths


def _write_deadline_sh(tag, nuke_exec_script, nuke_path, nuke_home):
    sh_content = """#!/bin/bash
export PYTHONHOME={nuke_home}
export PYTHONPATH=$PYTHONPATH:'/tools/packages/nkt_api/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2:/tools/packages/nkt_api/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2/python'
export LWR_STARTFRAME=$1
export LWR_ENDFRAME=$2
{nuke_path} -t "{nuke_exec_script}"
""".format(
        nuke_home=nuke_home,
        nuke_path=nuke_path,
        nuke_exec_script=nuke_exec_script,
    )

    sh_path = os.path.join(os.path.dirname(nuke_exec_script), "{}_run.sh".format(tag))
    with open(sh_path, "w") as f:
        f.write(sh_content)
    os.chmod(sh_path, 0o777)
    return sh_path


def _write_nuke_exec_script(shape, shape_tag, out_folder, input_path):
    nuke_exec_content = """import os
import time
import nuke
import nuke.rotopaint as rp

VIS = rp.AnimAttributes.kVisibleAttribute

shape_tag  = {shape_tag!r}
out_folder = {out_folder!r}
input_path = {input_path!r}
nk_path    = {nk_path!r}

first = int(os.environ["LWR_STARTFRAME"])
last  = int(os.environ["LWR_ENDFRAME"])

print("[execute] shape: {{}}  frames: {{}}-{{}}".format(shape_tag, first, last))
nuke.scriptClear()
res_read = nuke.nodes.Read(file=input_path)
res_read["first"].setValue(first)
res_read["last"].setValue(first)
width = res_read.width()
height = res_read.height()
pixel_aspect = res_read.format().pixelAspect()
fmt_name = "{{}}_fmt".format(shape_tag)
try:
    new_format = nuke.addFormat("{{}} {{}} {{}} {{}}".format(width, height, pixel_aspect, fmt_name))
except Exception as e:
    print("[execute] addFormat failed, using existing: {{}}".format(e))
    new_format = None
if new_format:
    nuke.root()["format"].setValue(fmt_name)
nuke.delete(res_read)
print("[execute] format set: {{}}".format(nuke.root()["format"].value()))
nuke.nodePaste(nk_path)
if new_format:
    nuke.root()["format"].setValue(fmt_name)
print("[execute] format after paste: {{}}".format(nuke.root()["format"].value()))

roto_nodes = nuke.allNodes("Roto")
if not roto_nodes:
    print("[execute] No Roto nodes found - aborting")
    raise SystemExit(1)

roto = roto_nodes[0]

mb_mode_knob = roto.knob("motionblur_mode")
if mb_mode_knob is not None:
    mb_mode_knob.setValue("shape")
curves = roto["curves"]
top_layers = [l for l in curves.rootLayer]
if top_layers:
    attrs = top_layers[0].getAttributes()
    attrs.set("mb", float(8))
    curves.changed()
    print("[execute] motionblur set: mode=shape  mb={{}}".format(attrs.getValue(0, "mb")))

root = roto["curves"].rootLayer
level3 = []
for l1 in root:
    if not isinstance(l1, rp.Layer): continue
    for l2 in l1:
        if not isinstance(l2, rp.Layer): continue
        for l3 in l2:
            if isinstance(l3, rp.Layer):
                level3.append(l3)

if not level3:
    print("[execute] No level3 layers - aborting")
    raise SystemExit(1)

print("[execute] {{}} level3 layers: {{}}".format(len(level3), [l.name for l in level3]))

reformat = nuke.nodes.Reformat(name="reformat_{{}}".format(shape_tag))
reformat.setInput(0, roto)
reformat["format"].setValue(fmt_name)
reformat["resize"].setValue("none")
reformat["black_outside"].setValue(True)

write = nuke.nodes.Write()
write.setInput(0, reformat)
write["channels"].setValue("rgba")
write["file_type"].setValue("exr")

for l in level3:
    l.getAttributes().set(VIS, 0)
roto["curves"].changed()

renders = []
for l in level3:
    lname = l.name.replace(" ", "_")
    l.getAttributes().set(VIS, 1)
    roto["curves"].changed()

    folder = os.path.join(out_folder, shape_tag, lname)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "{{}}.%04d.exr".format(lname))
    write["file"].setValue(path)

    t = time.time()
    nuke.execute(write, first, last)
    print("[execute] layer '{{}}' done: {{:.1f}}s".format(lname, time.time() - t))

    renders.append((lname, path))
    l.getAttributes().set(VIS, 0)
    roto["curves"].changed()

for l in level3:
    l.getAttributes().set(VIS, 1)
roto["curves"].changed()
nuke.delete(write)

reads = []
for lname, path in renders:
    r = nuke.nodes.Read(name="read_lyr_{{}}".format(lname))
    r["file"].setValue(path)
    r["first"].setValue(first)
    r["last"].setValue(last)
    r["origfirst"].setValue(first)
    r["origlast"].setValue(last)
    reads.append(r)

top = reads[0]
for r in reads[1:]:
    m = nuke.nodes.Merge2(name="merge_lyr_{{}}".format(r.name()))
    m["operation"].setValue("over")
    m.setInput(0, top)
    m.setInput(1, r)
    top = m

shape_merged_folder = os.path.join(out_folder, shape_tag, "shape_merge")
os.makedirs(shape_merged_folder, exist_ok=True)
shape_merged_path = os.path.join(shape_merged_folder, "{{}}.%04d.exr".format(shape_tag))

mw = nuke.nodes.Write(name="write_shape_merged_{{}}".format(shape_tag))
mw.setInput(0, top)
mw["file"].setValue(shape_merged_path)
mw["channels"].setValue("rgba")
mw["file_type"].setValue("exr")


# --- save the built graph as .nk for debugging ---
debug_nk_folder = os.path.join(out_folder, shape_tag, "debug_nk")
os.makedirs(debug_nk_folder, exist_ok=True)
debug_nk_path = os.path.join(debug_nk_folder, "{{}}.nk".format(shape_tag))
try:
    nuke.scriptSaveAs(debug_nk_path, overwrite=1)
    print("[execute] DEBUG nk saved -> {{}}".format(debug_nk_path))
except Exception as e:
    print("[execute] DEBUG nk save failed: {{}}".format(e))
# --- end debug save ---

t = time.time()
nuke.execute(mw, first, last)
print("[execute] MERGED: {{:.1f}}s -> {{}}".format(time.time() - t, shape_merged_path))
""".format(
        shape_tag=shape_tag,
        out_folder=out_folder,
        input_path=input_path,
        nk_path=shape["path"],
    )

    exec_path = os.path.join(out_folder, shape_tag, "{}_execute.py".format(shape_tag))
    os.makedirs(os.path.dirname(exec_path), exist_ok=True)
    with open(exec_path, "w") as f:
        f.write(nuke_exec_content)
    return exec_path
