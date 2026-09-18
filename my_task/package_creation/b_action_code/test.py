#!/usr/bin/env python3
"""
Roto Packaging Nuke Wrapper Patcher
=====================================
Pure Nuke API approach.

Usage (from Nuke Script Editor):
    import importlib, roto_wrapper
    importlib.reload(roto_wrapper)

    roto_wrapper.run(
        input_nk   = "/path/to/script.nk",
        output_nk  = "/path/to/patched.nk",
        config     = "/path/to/roto_config.json",
        write_path = "/path/to/output.exr",
        mattes     = [
            {
                "path":        "/shots/sh010/matte1.%04d.exr",
                "shuffle_out": "CSMT_read_1",
                "red":         True,
                "green":       True,
                "blue":        False,
            },
        ]
    )

JSON config holds node names per channel per matte:
    {
      "mattes": [
        {
          "name":  "CSMT_read_1",
          "red":   ["nodeA", "nodeB", "nodeC", "nodeD", "nodeE"],
          "green": ["nodeA", "nodeB", "nodeC", "nodeD", "nodeE"],
          "blue":  ["nodeA", "nodeB", "nodeC", "nodeD", "nodeE"]
        }
      ]
    }

    mattes run() order must match config order.
    red/green/blue = True  -> ENABLE  those nodes
    red/green/blue = False -> DISABLE those nodes
"""

import json

import nuke

# ─────────────────────────────────────────────
# NAME DERIVATION
# ─────────────────────────────────────────────


def _get_names(shuffle_out, channel):
    """
    shuffle_out = "CSMT_read_1", channel = "red"
      alpha_shuffle = "CSMT_read_1_red_alpha"   -> set out1
      copy_node     = "CSMT_read_1_red_alpha_Copy" -> set channels
      out1_value    = "CSMT_read_1_red_alpha"
    """
    return {
        "alpha_shuffle": f"{shuffle_out}_{channel}_alpha",
        "copy_node": f"{shuffle_out}_{channel}_alpha_Copy",
        "out1_value": f"{shuffle_out}_{channel}_alpha",
    }


def _load_config(filepath):
    with open(filepath, "r") as f:
        return json.load(f)


# ─────────────────────────────────────────────
# 1. REPLACE READ NODE PATHS
# ─────────────────────────────────────────────


def _replace_read_paths(cfg_mattes, mattes):
    print("\n[STEP 1] Replacing Read node paths...")
    for cfg_matte, matte in zip(cfg_mattes, mattes):
        node_name = cfg_matte["name"]  # auto from JSON order e.g. CSMT_read_1
        new_path = matte["path"]
        node = nuke.toNode(node_name)
        if node:
            node["file"].setValue(new_path)
            print(f"  [ok] {node_name}  ->  {new_path}")
        else:
            print(f"  [!!] Read node '{node_name}' NOT FOUND")


# ─────────────────────────────────────────────
# 2. DISABLE / ENABLE RGB SECTION NODES
# ─────────────────────────────────────────────


def _process_rgb_sections(cfg_mattes, mattes):
    """
    cfg_mattes  -> from JSON  : holds node name lists per channel
    mattes      -> from run() : holds True/False per channel

    channel True  -> ENABLE  all nodes in that channel list
    channel False -> DISABLE all nodes in that channel list
    """
    print("\n[STEP 2] Processing R/G/B sections...")

    for cfg_matte, matte in zip(cfg_mattes, mattes):
        matte_name = cfg_matte["name"]
        print(f"\n  [Matte] {matte_name}")

        for channel in ["red", "green", "blue"]:
            ch_value = matte.get(channel, False)
            is_used = bool(ch_value)  # False = disabled, string = enabled
            should_disable = not is_used
            node_list = cfg_matte.get(channel, [])
            label = "used   -> ENABLE " if is_used else "unused -> DISABLE"
            print(f"    [{channel.upper()}] {label}  ({len(node_list)} nodes)")

            for node_name in node_list:
                node = nuke.toNode(node_name)
                if node:
                    node["disable"].setValue(should_disable)
                    status = "DISABLED" if should_disable else "ENABLED "
                    print(f"      [{status}] {node_name}")
                else:
                    print(f"      [!!] NOT FOUND: {node_name}")


# ─────────────────────────────────────────────
# 3. SET ALPHA SHUFFLE out1 + COPY channels
# ─────────────────────────────────────────────


def _sync_shuffle_copy(cfg_mattes, mattes):
    """
    For each matte x channel:
      node to FIND  -> cfg_matte["name"] from JSON  e.g. CSMT_read_1_red_alpha
      value to SET  -> matte[channel] you pass       e.g. test1_red

      1. Register the passed value as a Nuke layer first
      2. Find alpha Shuffle2 by config name, set out1 to passed value
      3. Find Copy by config name, set channels to passed value
    """
    print("\n[STEP 3] Setting alpha Shuffle2 out1 + Copy channels...")

    for cfg_matte, matte in zip(cfg_mattes, mattes):
        cfg_name = cfg_matte["name"]
        print(f"\n  [Matte] {cfg_name}")

        for channel in ["red", "green", "blue"]:
            ch_value = matte.get(channel, False)
            if not ch_value:
                print(f"    [{channel.upper()}] skipping - disabled")
                continue

            # Node names to find (from JSON config)
            alpha_node_name = f"{cfg_name}_{channel}_alpha"
            copy_node_name = f"{cfg_name}_{channel}_alpha_Copy"

            # out1 value = exactly what user passed
            out1_value = ch_value

            # MUST register layer first or setValue falls back to none
            nuke.Layer(
                out1_value,
                [
                    out1_value + ".red",
                    out1_value + ".green",
                    out1_value + ".blue",
                    out1_value + ".alpha",
                ],
            )
            print(f"    [ok] Layer registered: {out1_value}")

            # Set alpha Shuffle2 out1
            alpha_node = nuke.toNode(alpha_node_name)
            if alpha_node:
                alpha_node["out1"].setValue(out1_value)
                print(
                    f"    [ok] Shuffle '{alpha_node_name}'  out1     -> {alpha_node['out1'].value()}"
                )
            else:
                print(f"    [!!] Shuffle '{alpha_node_name}' NOT FOUND")

            # Set Copy node channels dropdown
            copy_node = nuke.toNode(copy_node_name)
            if copy_node:
                copy_node["channels"].setValue(out1_value)
                print(
                    f"    [ok] Copy   '{copy_node_name}'  channels -> {copy_node['channels'].value()}"
                )
            else:
                print(f"    [!!] Copy   '{copy_node_name}' NOT FOUND")


# ─────────────────────────────────────────────
# 4. SET WRITE NODE PATH
# ─────────────────────────────────────────────


def _set_write_path(write_path):
    print("\n[STEP 4] Setting Write node path...")
    write_nodes = nuke.allNodes("Write")
    if write_nodes:
        write_nodes[0]["file"].setValue(write_path)
        print(f"  [ok] Write '{write_nodes[0].name()}'  ->  {write_path}")
    else:
        print("  [!!] Write node NOT FOUND")


# ─────────────────────────────────────────────
# 5. PATCH ADD_LAYER LINES IN SAVED FILE
# ─────────────────────────────────────────────


def _patch_add_layers(nk_file, cfg_mattes, mattes):
    """
    After scriptSaveAs, patch the .nk file to insert add_layer lines
    before each alpha Shuffle2 node block. This ensures the layer is
    registered when the file is reopened and out1 resolves correctly.
    """
    with open(nk_file, "r") as f:
        content = f.read()

    for cfg_matte, matte in zip(cfg_mattes, mattes):
        cfg_name = cfg_matte["name"]
        shuffle_out = matte["shuffle_out"]
        for channel in ["red", "green", "blue"]:
            ch_value = matte.get(channel, False)
            if not ch_value:
                continue
            layer_name = ch_value
            node_name = f"{cfg_name}_{channel}_alpha"  # find by config name

            add_layer_line = (
                f"add_layer {{{layer_name} "
                f"{layer_name}.red {layer_name}.green "
                f"{layer_name}.blue {layer_name}.alpha}}"
            )

            # Find exact name line in file
            exact_name = f"name {node_name}"
            idx = 0
            while True:
                name_pos = content.find(exact_name, idx)
                if name_pos == -1:
                    break

                after = name_pos + len(exact_name)
                if after < len(content) and content[after] not in (
                    " ",
                    "\n",
                    "\r",
                    "\t",
                ):
                    idx = name_pos + 1
                    continue

                # Walk backward to find start of Shuffle2 block
                block_start = content.rfind("Shuffle2 {", 0, name_pos)
                if block_start == -1:
                    break

                # Check add_layer not already there
                preceding = content[max(0, block_start - 200) : block_start]
                if layer_name in preceding:
                    break

                # Insert add_layer before the Shuffle2 block
                content = (
                    content[:block_start]
                    + add_layer_line
                    + "\n"
                    + content[block_start:]
                )
                print(f"  [ok] add_layer inserted: {layer_name}")
                break

    with open(nk_file, "w") as f:
        f.write(content)


# ─────────────────────────────────────────────
# PUBLIC RUN FUNCTION
# ─────────────────────────────────────────────


def run(input_nk, output_nk, config, write_path, mattes):
    """
    Parameters
    ----------
    input_nk   : str  - Input .nk file to open
    output_nk  : str  - Output .nk file to save
    config     : str  - roto_config.json path
    write_path : str  - Write node output path
    mattes     : list - One dict per matte in config order:
        [
            {
                "path":  "/shots/matte1.%04d.exr",
                "red":   True,   # True  = ENABLE  red nodes
                "green": False,  # False = DISABLE green nodes
                "blue":  False,
            },
            ...
        ]
        # shuffle_out and read node name are auto-taken from JSON config order
        # 1st dict -> cfg_mattes[0]["name"] = "CSMT_read_1"
        # 2nd dict -> cfg_mattes[1]["name"] = "CSMT_read_2"  etc.
    """
    cfg = _load_config(config)
    cfg_mattes = cfg["mattes"]

    print(f"\n{'=' * 60}")
    print("  Roto Wrapper Patcher")
    print(f"{'=' * 60}")
    print(f"  Input  : {input_nk}")
    print(f"  Output : {output_nk}")
    print(f"  Config : {config}")
    print(f"  Mattes : {len(mattes)}")
    print(f"{'=' * 60}")

    nuke.scriptOpen(input_nk)
    _replace_read_paths(cfg_mattes, mattes)
    _process_rgb_sections(cfg_mattes, mattes)
    _sync_shuffle_copy(cfg_mattes, mattes)
    _set_write_path(write_path)

    nuke.scriptSaveAs(output_nk, overwrite=1)
    print(f"\n[ok] Saved: {output_nk}")

    # Patch saved file - add add_layer lines before each alpha shuffle
    # so layers are registered when file is reopened
    _patch_add_layers(output_nk, cfg_mattes, mattes)
    print(f"\n[ok] Patched add_layer lines: {output_nk}")
    print(f"\n{'=' * 60}")
    print("  All done!")
    print(f"{'=' * 60}\n")


run(
    input_nk="/home/chandru/Documents/nuke/004_ARR__0010__004_ARR_0010_BG01_V01_denoise__roto__v001.nk",
    output_nk="/home/chandru/Documents/nuke/004_ARR__0010__004_ARR_0010_BG01_V01_denoise__roto__v001_test.nk",
    config="/tools/silhouette_tools/2021.5/my_task/package_creation/b_action_code/test_config.json",
    write_path="/path/to/output.exr",
    mattes=[
        {
            "path": "/shots/matte1.%04d.exr",
            "red": "test1_red",  # → sets out1 = test1_red_red_alpha
            "green": "test1_green",  # → sets out1 = test1_green_green_alpha
            "blue": False,  # → disabled
        },
        {
            "path": "/shots/matte2.%04d.exr",
            "red": False,
            "green": "test2_green",
            "blue": "test2_blue",
        },
    ],
)
