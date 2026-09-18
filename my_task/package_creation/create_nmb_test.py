import subprocess
import json
import os
import sys

def create_silhouette_script_file(output_paths, start_frame, end_frame, project_path, script_path, tmp_path="/tmp/"):
    """
    Create a Python script file for Silhouette rendering operations.
    
    Args:
        output_paths (dict): Dictionary of output node names and their paths
        start_frame (int): Starting frame number
        end_frame (int): Ending frame number
        project_path (str): Path to the Silhouette project file (.sfx)
        script_path (str): Path to the fx_command.py script
        tmp_path (str): Temporary directory path for storing the generated script
    
    Returns:
        str: Path to the generated Python script file
    """
    
    silhouette_script_content = f"""
import subprocess
import json
import os
import sys

def create_nmb_script(output_paths, start_frame, end_frame):
    try:
        # Convert output_paths dict to JSON string
        output_paths_json = json.dumps(output_paths)
        frame_range = str(start_frame) + "-" + str(end_frame)

        silhouette_cmd = [
            "/apps/silhouette/Silhouette-2023.5/sfxcmd",
            "{project_path}",
            "-range", frame_range,
            "-render", "1",
            "-args", output_paths_json,
            "-script", "{script_path}"
        ]

        print("Executing Silhouette command:", " ".join(silhouette_cmd))

        render_process = subprocess.Popen(
            silhouette_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        stdout, stderr = render_process.communicate()

        if render_process.returncode == 0:
            print("Render command executed successfully")
            print(f"Output: {{stdout}}")
        else:
            print(f"Command failed with return code {{render_process.returncode}}")
            print(f"Error output: {{stderr}}")

    except Exception as e:
        print(f"An error occurred: {{str(e)}}")

if __name__ == "__main__":
    output_paths = {json.dumps(output_paths, indent=8)}
    start_frame = {start_frame}
    end_frame = {end_frame}
    create_nmb_script(output_paths, start_frame, end_frame)
    """
    
    # Generate a unique filename based on the project
    if project_path:
        project_name = project_path
    else:
        project_name = "silhouette_render"
    
    script_filename = f"{tmp_path}{project_name}_silhouette_script.py"
    
    # Write the script content to file
    with open(script_filename, "w") as script_file:
        script_file.write(silhouette_script_content)
    
    return script_filename
