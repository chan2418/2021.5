import os
try: 
    import fx
except:
    pass    
import subprocess
import logging
import sys
sys.path.append("/tools/packages/deadline_utils/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2/python/deadline_utils")
from nuke_job import *
import time
from datetime import datetime


def tmp_path_user():
    tmp_path=os.environ['HOME']+"/tmp/"
    if not os.path.exists(tmp_path):
        os.makedirs(tmp_path)
    return tmp_path



def create_nuke_job(name, proxy_template, nuke_template, start_frame, end_frame, job_name="_proxy_action", chunk="", dependent=""):
    tmp_path = tmp_path_user()
    if not os.path.exists(tmp_path):
        os.makedirs(tmp_path)
    
    log_path = "{}/{}_nuke_job.log".format(tmp_path, name)
    logging.basicConfig(filename=log_path, level=logging.DEBUG, format='%(asctime)s %(message)s')

    script = """#!/bin/bash
    export PYTHONHOME=/apps/nuke/Nuke12.2v7
    export PYTHONPATH=$PYTHONPATH:'/tools/packages/nkt_api/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2:/tools/packages/nkt_api/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2/python'
    /apps/nuke/Nuke12.2v7/Nuke12.2 -t "{}"
    """.format(proxy_template)

    script_path = "{}/{}_run_nuke.sh".format(tmp_path, name)
    with open(script_path, 'w') as file:
        file.write(script)

    subprocess.call(['chmod', '+x', script_path])

    logging.debug("Running script: {}".format(script))

    try:
        result = subprocess.Popen([script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout_data, stderr_data = result.communicate()
        logging.info("Output: {}".format(result.stdout))
        logging.error("Error: {}".format(result.stderr))
    except subprocess.CalledProcessError as e:
        logging.error("Error running Nuke script: {}".format(e))
        logging.error("Output: {}".format(e.stdout))
        logging.error("Error: {}".format(e.stderr))
        return

    logging.debug("Nuke script ran successfully.")

    try:
        plugin_details, job_details = get_info_txt(
            "{}_{}".format(name, job_name),
            name,
            "2d_pool", 
            "2d_group", 
            start_frame, 
            end_frame, 
            12.2, 
            chunk, 
            dependent,
            "Roto"
            
        )
        logging.debug("Plugin details: {}".format(plugin_details))
        logging.debug("Job details: {}".format(job_details))
    except Exception as e:
        logging.error("Error getting job details: {}".format(e))
        return

    time.sleep(4)

    try:
        job_id = submit_to_deadline(plugin_details, job_details, "{}/{}".format(tmp_path, nuke_template))
        logging.info("Template job created with ID: {}".format(job_id))
    except Exception as e:
        logging.error("Error submitting job to Deadline: {}".format(e))
        return

    return job_id


def set_nkt_value(read_paths,start_frame,end_frame,dependent=None):
    for i in read_paths:
        write_mov_file = os.path.basename(i)

    input_template = "/tools/bpipe/config/roto_mov_template/roto_mov_template.nk"
    tmp_path = tmp_path_user()
    output_template = os.path.join(tmp_path,os.path.basename(write_mov_file)+".nk")

    project = os.path.dirname(fx.activeProject().path)
    file_name = os.path.basename(project).split(".")[0] + ".mov"
    write_mov = read_paths[0].split("/render/")[0] + "/review/qt/"+ file_name
    name = os.path.basename(write_mov)
    bake = True
    
    chunk = end_frame - start_frame + 1
    proxy_template = create_roto_nkt_file(input_template, output_template, write_mov,start_frame,end_frame ,read_paths, name, bake)
    job_id = create_nuke_job(name, proxy_template, os.path.basename(write_mov_file)+".nk", start_frame, end_frame, job_name="_proxy_action", chunk=chunk, dependent=dependent)
    return job_id


def create_roto_nkt_file(input_template_path, output_template_path, write_path, startframe, endframe, mate_list_path, name, bake):
    print("create_roto_nkt_file called!")
    create_proxy_template = """
import sys
sys.path.append("/tools/packages/nkt_api/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2/python")
from processors import roto_mov_render
input_template_path="{input_template_path}"
output_template_path="{output_template_path}"
startframe={startframe}
endframe={endframe}
mate_list_path = "{mate_list_path}"
write_path="{write_path}"
roto_mov_render(input_template_path,output_template_path,write_path,startframe,endframe,mate_list_path,bake={bake})
    """.format(
    input_template_path=input_template_path,
    output_template_path=output_template_path,
    write_path=write_path,
    startframe=startframe,
    endframe=endframe,
    mate_list_path = mate_list_path,
    bake=bake
    )        
    mov_name = name.rsplit('.', 1)[0]
    tmp_path = tmp_path_user()

    if not os.path.exists(tmp_path):
        os.makedirs(tmp_path)

    proxy_template = "{}/{}.py".format(tmp_path, mov_name)
    print(proxy_template)

    with open(proxy_template, "w") as cf:
        cf.write(create_proxy_template)

    return proxy_template


