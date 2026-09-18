import sys
sys.path.append("/tools/packages/nkt_api/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2/python/")
sys.path.append("/tools/packages/deadline_utils/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2/python/deadline_utils")
from nuke_job import *
import subprocess
import logging




def create_nkt_template_proxy(input_template_path,output_template_path,input_path,proxy_seq,proxy_mov,startframe,endframe,fps,name,plate_path,render_type,bake):
    create_proxy_template= f"""
import sys
sys.path.append("/tools/packages/nkt_api/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2/python")
from processors import roto_proxy_processor
input_template_path="{input_template_path}"
output_template_path="{output_template_path}"
startframe={startframe}
endframe={endframe}
fps={fps}
proxy_seq="{proxy_seq}"
proxy_mov="{proxy_mov}"
input_path= "{input_path}"
plate_path = "{plate_path}"
rendertype = "{render_type}"


roto_proxy_processor(input_template_path,output_template_path,input_path,proxy_seq,proxy_mov,startframe,endframe,fps,plate_path,rendertype,bake={bake})

"""
    print("input_path",input_path)
    print("proxy_seq",proxy_seq)
    mov_name = name.rsplit('.', 1)[0]
    proxy_template = f"/usr/tmp/{mov_name}.py"
    with open(proxy_template, "w") as cf:
        cf.write(create_proxy_template)

    return proxy_template



def create_nuke_job(name, proxy_template, nuke_template, start_frame, end_frame, job_name="_proxy_action", chunk=10, dependent=""):
    log_path = f"/usr/tmp/{name}_nuke_job.log"
    logging.basicConfig(filename=log_path, level=logging.DEBUG, format='%(asctime)s %(message)s')

    script = f"""#!/bin/bash
    export PYTHONHOME=/samrat/projects/apps/nuke/Nuke12.2v7
    export PYTHONPATH=$PYTHONPATH:'/tools/packages/nkt_api/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2:/tools/packages/nkt_api/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2/python'
    /samrat/projects/apps/nuke/Nuke12.2v7/Nuke12.2 -t "{proxy_template}"
    """

    script_path = f"/usr/tmp/{name}_run_nuke.sh"
    with open(script_path, 'w') as file:
        file.write(script)

    subprocess.run(['chmod', '+x', script_path])

    logging.debug(f"Running script: {script}")

    try:
        result = subprocess.run([script_path], check=True, text=True, capture_output=True)
        logging.info(f"Output: {result.stdout}")
        logging.error(f"Error: {result.stderr}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error running Nuke script: {e}")
        logging.error(f"Output: {e.stdout}")
        logging.error(f"Error: {e.stderr}")
        return

    logging.debug("Nuke script ran successfully.")

    try:
        plugin_details, job_details = get_info_txt(f"{name}_{job_name}", name,"2d_pool", "2d_group", start_frame, end_frame, 12.2, chunk, dependent)
        logging.debug(f"Plugin details: {plugin_details}")
        logging.debug(f"Job details: {job_details}")
    except Exception as e:
        logging.error(f"Error getting job details: {e}")
        return

    try:
        job_id = submit_to_deadline(plugin_details, job_details, f"/usr/tmp/{nuke_template}")
        logging.info(f"Template job created with ID: {job_id}")
    except Exception as e:
        logging.error(f"Error submitting job to Deadline: {e}")
        return

    return job_id




