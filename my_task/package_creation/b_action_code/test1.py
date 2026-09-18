import sys

sys.path.insert(
    0, "/tools/silhouette_tools/2021.5/my_task/package_creation/b_action_code"
)
import json

import test as roto_wrapper

nk_file = "/home/chandru/Documents/nuke/004_ARR__0010__004_ARR_0010_BG01_V01_denoise__roto__v001.nk"
config = "/tools/silhouette_tools/2021.5/my_task/package_creation/b_action_code/test_config.json"

f = open(nk_file, "r")
original = f.read()
f.close()

f = open(config, "r")
cfg = json.load(f)
f.close()

mattes = cfg["mattes"]
read_paths = [
    "/shots/sh010/matte1.%04d.exr",
    "/shots/sh010/matte2.%04d.exr",
    "/shots/sh010/matte3.%04d.exr",
]

# Run step 1
content = roto_wrapper._replace_read_paths(original, mattes, read_paths)

# Run step 2
matte_input = [
    {
        "path": "/shots/sh010/matte1.%04d.exr",
        "shuffle_out": "CSMT_read_1",
        "red": True,
        "green": True,
        "blue": False,
    },
    {
        "path": "/shots/sh010/matte2.%04d.exr",
        "shuffle_out": "CSMT_read_2",
        "red": False,
        "green": True,
        "blue": True,
    },
    {
        "path": "/shots/sh010/matte3.%04d.exr",
        "shuffle_out": "CSMT_read_3",
        "red": True,
        "green": False,
        "blue": True,
    },
]
content = roto_wrapper._process_rgb_sections(content, mattes, matte_input)

# Now test step 3 directly
result = roto_wrapper._extract_node_block(content, "Shuffle2", "CSMT_read_1_red_alpha")
if result:
    print("FOUND after step 2!")
    print(repr(result[2]))
else:
    print("NOT FOUND after step 2 - step 2 is corrupting content!")
    # Check original
    result2 = roto_wrapper._extract_node_block(
        original, "Shuffle2", "CSMT_read_1_red_alpha"
    )
    print("Found in original:", result2 is not None)
