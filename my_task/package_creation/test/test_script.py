""""""

import json
import subprocess

# paths
sfx_cmd = "/apps/silhouette/Silhouette-2023.5/sfxcmd"  # your silhouette binary
project_path = "/projects/cfx_snw5/snw5_505_518_280/dept/roto/chandru/silhouette/scripts/snw5_505_518_280_roto_test_v005.sfx/project.sfx"  # existing project with multiple roto nodes
script_path = "/tools/silhouette_tools/2021.5/my_task/package_creation/test/test_sfx_file_edit.py"  # the merge script we wrote
frame_range = "1-10"  # doesn't matter much, no render happening

output_paths_json = json.dumps(
    {
        "output_project_path": "/home/chandru/tmp/roto_packaging/test/merged_project.sfx"  # where the result goes
    }
)

silhouette_cmd = [
    sfx_cmd,
    project_path,
    "-range",
    frame_range,
    "-render",
    "0",
    "-args",
    output_paths_json,
    "-script",
    script_path,
    "-all",
]

print("running:", " ".join(silhouette_cmd))
print("-" * 60)

result = subprocess.run(
    silhouette_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
)

print("STDOUT:")
print(result.stdout)

print("STDERR:")
print(result.stderr)

print("-" * 60)
print("exit code:", result.returncode)
