import subprocess
import json 
output_paths_json = {"PublishOutputNode1": "/projects/oou_tim/001_mls_0780/dept/upload/roto/PL01V001_v002/001_mls_0780//001_mls_0780_silhouette_basilicflyroto_PL01V001_layer_NMB_v002/001_mls_0780_silhouette_basilicflyroto_PL01V001_layer_NMB_v002", "layer": "/projects/oou_tim/001_mls_0780/dept/upload/roto/PL01V001_v002/001_mls_0780/001_mls_0780_basilicflyroto_layer_NMB_v002.nk"}
script_path = "/tools/silhouette_tools/2021.5/my_task/package_creation/fx_command.py"
sfx_cmd = "/apps/silhouette/Silhouette-2023.5/sfxcmd"
output_paths_str = json.dumps(output_paths_json)
silhouette_cmd = [
        sfx_cmd,
        "/projects/oou_tim/001_mls_0780/dept/roto/rohitk/silhouette/scripts/.tmp/001_mls_0780_roto_test_nmb_v002.sfx/project.sfx/project.sfx",
        "-range", "1000-1010",
        "-args", output_paths_str,
        "-all",
        "-render", "1",
        # "-node", "PublishOutputNode1","PublishOutputNode2"
        ]


#   silhouette_cmd = [
#             sfx_cmd,
#             project_path,
#             "-range", frame_range,
#             "-render", "0",
#             "-args", output_paths_json,
#             "-script", script_path,
#             # "-all",
#         ]
# silhouette_cmd = ['/apps/silhouette/Silhouette-2023.5/sfxcmd', '/projects/oou_tim/001_mls_0780/dept/roto/rohitk/silhouette/scripts/.tmp/001_mls_0780_roto_test_nmb_v002.sfx/project.sfx', '-range', '1001-1010', '-args', '{"PublishOutputNode1": "/projects/oou_tim/001_mls_0780/dept/upload/roto/PL01V001_v002/001_mls_0780//001_mls_0780_silhouette_basilicflyroto_PL01V001_layer_NMB_v002/001_mls_0780_silhouette_basilicflyroto_PL01V001_layer_NMB_v002", "layer": "/projects/oou_tim/001_mls_0780/dept/upload/roto/PL01V001_v002/001_mls_0780/001_mls_0780_basilicflyroto_layer_NMB_v002.nk"}', '-script', '/tools/silhouette_tools/2021.5/my_task/package_creation/fx_command.py', '-all']
print("silhouette_cmd_________",silhouette_cmd)
render_process = subprocess.Popen(
    silhouette_cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)

stdout, stderr = render_process.communicate()
print(stdout)
print(stderr)
# import re

# description_layer = "layer3"  # Only underscore → should fail

# pattern = r'^[A-Za-z0-9]+$'

# print("run")
# if not re.match(pattern, description_layer):
#     print("Invalid!")
#     raise ValueError(
#         f"Invalid layer name '{description_layer}'. "
#         "It must contain at least one letter or digit, and only letters, digits, or underscores."
#     )
# else:
#     print("Valid!")
# filename = "db_205-020_0030_plate_PL01_v001.001_degrain_tha.[0960-1170].exr"
# result = "_".join(filename.split("_")[-3:-1]).split(".")[0]
# print(result)  # PL01_v001

