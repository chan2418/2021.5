# import subprocess

# # Define the paths to the required files and the Deadline command
# deadline_command = "/apps/Thinkbox/Deadline10/bin/deadlinecommand"
# job_info_path = "/home/chandru/tmp/job_info.job"
# plugin_info_path = "/home/chandru/tmp/plugin_info.job"
# scene_file_path = "/projects/oou_tb/CS1090/dept/roto/rohitk/silhouette/scripts/CS1090_roto_test_nmb_v002.sfx/project.sfx"

# # Create the command as a list
# command = [
#     deadline_command,
#     job_info_path,
#     plugin_info_path,
#     scene_file_path,
# ]

# # Run the command using subprocess
# result = subprocess.run(
#     command,
#     stdout=subprocess.PIPE,
#     stderr=subprocess.PIPE,
#     text=True,  # Ensure output is in string format
#     check=True,  # Raise exception if the command fails
# )

# # Print the output from the command
# print("Command executed successfully!")
# print("Output:", result.stdout)




# /projects/oou_tb/CS1090/dept/roto/rohitk/silhouette/scripts/CS1090_roto_test_nmb_v002.sfx/project.sfx
# /projects/oou_tb/CS1090/dept/roto/rohitk/silhouette/scripts/CS1090_roto_test_nmb_v002.sfx/project.sfx



import os 
import re
def replace_frame_with_padding(path):
    # Split extension
    base, ext = os.path.splitext(path)

    # Find trailing frame number using regex
    match = re.search(r'(\d+)$', base)
    if not match:
        # No frame number found
        return path

    frame_num = match.group(1)

    # Build new path with %0Xd
    padding = len(frame_num)
    new_base = base[:-len(frame_num)]  # Remove the frame number
    new_path = f"{new_base}%0{padding}d{ext}"

    return new_path


print(replace_frame_with_padding("/projects/bfu_sos/JET-013-1130/dept/publish/roto/render/JET-013-1130_roto_test_red_v003/JET-013-1130_roto_test_red_v003.10001.dpx"))



