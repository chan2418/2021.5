import subprocess, logging, time


def create_roto_nkt_script(input_template_path, output_template_path,
                           input_path, write_path, startframe, endframe,
                           mate_list_path, name, layer_dict, additional_value,
                           resolution, layer_path, bake):
    return f"""
import sys
sys.path.append("/tools/packages/nkt_api/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2/python")
from processors import roto_coloroverlay_processor
input_template_path="{input_template_path}"
output_template_path="{output_template_path}"
startframe={startframe}
endframe={endframe}
mate_list_path="{mate_list_path}"
write_path="{write_path}"
input_path="{input_path}"
layer_path="{layer_path}"
addition_value="{additional_value}"
resolution="{resolution}"
layer_dict="{layer_dict}"
roto_coloroverlay_processor(
    input_template_path, output_template_path, input_path, write_path,
    startframe, endframe, mate_list_path, layer_dict,
    addition_value, resolution, layer_path, bake={bake}
)
"""

def create_nuke_job(name, script_content, nuke_template,
                    start_frame, end_frame, job_name="_proxy_action",
                    chunk=10, dependent="", deadline_render=True):
    chunk = int(end_frame) - int(start_frame) + 1

    tmp_path = get_tmp_path()
    if not os.path.exists(tmp_path):
        os.makedirs(tmp_path)

    log_path = f"{tmp_path}/{name}_nuke_job.log"
    logging.basicConfig(filename=log_path, level=logging.DEBUG,
                        format='%(asctime)s %(message)s')

    # Run Nuke with script via stdin
    try:
        process = subprocess.Popen(
            ["/apps/nuke/Nuke12.2v7/Nuke12.2", "-t", "-"],  # "-" means read script from stdin
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(script_content)
        logging.info("Output: %s", stdout)
        logging.error("Error: %s", stderr)
    except Exception as e:
        logging.error("Error running Nuke script: %s", e)
        return

    logging.debug("Nuke script ran successfully.")
    if deadline_render:
        try:
            plugin_details, job_details = get_info_txt(
                f"{name}_{job_name}", name, "2d_pool", "2d_group",
                start_frame, end_frame, 12.2, chunk, dependent,
                department="Roto"
            )
            logging.debug("Plugin details: %s", plugin_details)
            logging.debug("Job details: %s", job_details)
        except Exception as e:
            logging.error("Error getting job details: %s", e)
            return

        time.sleep(4)

        try:
            job_id = submit_to_deadline(
                plugin_details, job_details, f"{tmp_path}/{nuke_template}"
            )
            logging.info("Template job created with ID: %s", job_id)
            return job_id
        except Exception as e:
            logging.error("Error submitting job to Deadline: %s", e)
            return



script_content = create_roto_nkt_script(
    input_template_path, output_template_path,
    input_path, write_path,
    startframe, endframe,
    mate_list_path, name,
    layer_dict, additional_value,
    resolution, layer_path, bake
)

if self.job_id is None:
    self.job_id = ""

if deadline_render:
    self.create_nuke_job(name, script_content,
                         os.path.basename(write_path)+".nk",
                         startframe, endframe, "", chunk, self.job_id, deadline_render)
else:
    self.create_nuke_job(name, script_content,
                         os.path.basename(input_template_path)+".nk",
                         startframe, endframe, "", chunk, self.job_id, deadline_render)
