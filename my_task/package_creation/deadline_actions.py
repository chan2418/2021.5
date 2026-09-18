
import os 



import sys
sys.path.append("/tools/packages/nkt_api/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2/python/")
sys.path.append("/tools/packages/deadline_utils/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2/python/deadline_utils")
from nuke_job import *
import subprocess
import logging
import sgtk
from sgtk.authentication import ShotgunAuthenticator
import fx
import socket
import re
from subprocess import PIPE


# authenticator = ShotgunAuthenticator()
# user = authenticator.get_user()
# sg = user.create_sg_connection()


def get_sg_proxy(file_path):
    sg_proxy = None
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            if line.startswith("SG_PROXY:"):
                sg_proxy = line.split(":", 1)[1].strip()
                break
    return sg_proxy

def set_sgtk_auth():
    """
    Authenticates the user with Shotgun and sets the authenticated user in Shotgun Toolkit (sgtk).
    This method uses the ShotgunAuthenticator to prompt the user for authentication credentials,
    retrieves the authenticated user, and then sets this user in the Shotgun Toolkit (sgtk) context.

    Returns:
        ShotgunUser: The authenticated Shotgun user.

    Raises:
        ShotgunAuthenticationError: If the authentication fails for any reason.
    """
    if "B_SHOW" in os.environ:
        sa = sgtk.authentication.ShotgunAuthenticator()
        file_path = "/tools/site_config.yml"
        proxy_ip = get_sg_proxy(file_path)        
        user = sa.create_script_user(
            api_script="sgtk_launcher_test",
            api_key="fc$ul1hexdaqkeipjcwdtOdin",
            host="https://basilic.shotgrid.autodesk.com",
            http_proxy = proxy_ip)
            
        sgtk.set_authenticated_user(user)
        
    else:
        authenticator = ShotgunAuthenticator()
        user = authenticator.get_user()
        sgtk.set_authenticated_user(user)
    return user

sg_user = set_sgtk_auth()
sg = sg_user.create_sg_connection()


def tmp_path_user():
    tmp_path=os.environ['HOME']+"/tmp/"
    if not os.path.exists(tmp_path):
        os.makedirs(tmp_path)
    return tmp_path

tmp_path = tmp_path_user()

def extract_job_id(log_string):
    pattern = r"JobID=([a-f0-9]+)"
    match = re.search(pattern, log_string)
    return match.group(1) if match else None



def write_plugin_info_file(details):
    plugin_info_file = f"{tmp_path}plugin_info.job"
    with open(plugin_info_file, "w+", encoding="utf-8") as file:
        file.write(details)
    return plugin_info_file

def write_job_info_file(details):
    job_info_file = f"{tmp_path}job_info.job"
    with open(job_info_file, "w+", encoding="utf-8") as file:
        file.write(details)
    return job_info_file

def submit_render(session, batch_name="", job_name="", group="", pool="", frames="", output=""):
    chunk_size = 10
    pool="2d_pool"
    group = "2d_group"
    pool2 = "2d_pool"
    version = int(fx.version)
    sec="2d_pool"
    plugin_details = f"""
    Version={version}
    Session={session.label}
    Node={output}
    OutputDirectory=
    OutputFilename=
    OutputFormat=
    AdditionalOptions=
    Resolution=full
    Fields=none
    Dominance=even
    RunScript=False
    DisableRender=False
    ScriptFile=
    """

    job_details = f"""
    BatchName={batch_name}
    Name={job_name}
    Comment=
    Department=
    Pool={pool}
    SecondaryPool={pool}
    Group={group}
    Priority=100
    Plugin=Silhouette
    TaskTimeoutMinutes=0
    EnableAutoTimeout=False
    ConcurrentTasks=1
    LimitConcurrentTasksToNumberOfCpus=True
    MachineLimit=0
    MachineName={socket.gethostname()}
    Whitelist=
    LimitGroups=
    JobDependencies=
    OverrideTaskExtraInfoNames=False
    Frames={frames}
    UserName={os.getlogin()}
    ChunkSize={chunk_size}
    """
    
    deadline_cmd = "/apps/Thinkbox/Deadline10/bin/deadlinecommand"
    sfx_project = str(fx.activeProject().path)
    job_file = write_job_info_file(str(job_details).strip())
    plugin_file = write_plugin_info_file(str(plugin_details).strip())
    command = [deadline_cmd, job_file, plugin_file, sfx_project]
    process = subprocess.Popen(command, stdout=PIPE, stderr=PIPE)
    print(command)
    jobid = extract_job_id(str(process.communicate()[0]))
    print("jobid",jobid)
    return jobid


def get_fps():
    path = fx.activeProject().path
    tk = sgtk.sgtk_from_path(path)
    context = tk.context_from_path(path)
    projects = sg.find_one("Project", [["name", "is", context.project["name"]]], ["id", "name"])
    filters = [['sg_project', 'is', projects]]
    fields = ['sg_ingestion_fps']

    result = sg.find_one("CustomNonProjectEntity04", filters, fields)
    if result is None:
        print("Please add the fps in sg")
    else:
        return result["sg_ingestion_fps"]
    


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
    proxy_template = f"{tmp_path}{mov_name}.py"
    with open(proxy_template, "w") as cf:
        cf.write(create_proxy_template)

    return proxy_template


#TO DO: Batch name
def create_nuke_job(name, proxy_template, nuke_template, start_frame, end_frame, job_name="_proxy_action", chunk=10, dependent=""):
    print("coming....!")
    log_path = f"{tmp_path}{name}_nuke_job.log"
    logging.basicConfig(filename=log_path, level=logging.DEBUG, format='%(asctime)s %(message)s')

    script = f"""#!/bin/bash
    export PYTHONHOME=/apps/nuke/Nuke14.0v6
    export PYTHONPATH=$PYTHONPATH:'/tools/packages/nkt_api/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2:/tools/packages/nkt_api/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2/python'
    /apps/nuke/Nuke14.0v6/Nuke14.0 -t "{proxy_template}"
    """

    script_path = f"{tmp_path}{name}_run_nuke.sh"
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
        job_id = submit_to_deadline(plugin_details, job_details, f"{tmp_path}{nuke_template}")
        logging.info(f"Template job created with ID: {job_id}")
    except Exception as e:
        logging.error(f"Error submitting job to Deadline: {e}")
        return

    return job_id

def create_proxy_sg_version_file(project_name, dest_file, shot_name, published,exr_path,sg_username,mov_upload):
    create_proxy_action_version_file = f"""
import sys
import os
from glob import glob
sys.path.append("/tools/projects/bfu_stb_sg/install/core/python")
print("run")


def create_sg_version(project_name, dest_file, shot_name, published,exr_path,sg_username,mov_upload):
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context
    import sgtk
    from datetime import datetime
    current_time = datetime.now()
    sa = sgtk.authentication.ShotgunAuthenticator()
    SG_URL = "https://basilic.shotgrid.autodesk.com/"
    SCRIPT_NAME = "pipeline"
    SCRIPT_KEY = "utakzicH#prwwmcd3dmtekumo"
    user = sa.create_script_user(api_script=SCRIPT_NAME,
                             api_key=SCRIPT_KEY,
                             host=SG_URL)
    sg =  user.create_sg_connection()
    print(project_name)
    sg_project = sg.find_one('Project', [['name', 'is', project_name]])
    print(sg_project)
    sg_shot = sg.find_one('Shot', [['project', 'is', sg_project], ['code', 'is', shot_name]])
    print(published)
    published_files = sg.find('PublishedFile', [['id', 'is', int(published)]])
    online = sg.find_one('Step', [['code', 'is', 'Roto']])
    task_data = dict()
    task_data['project'] = sg_project
    task_data["step"] = online
    task_data["entity"] = sg_shot
    task_data["content"] = "Roto"
    task = sg.find_one(
        "Task",
        [
            ["project", "is", sg_project],
            ["entity", "is", sg_shot],
            ["step", "is", online],
            ["content", "is", "Roto"],
        ],
    )
    if not task:
        task = sg.create("Task", task_data)

    sg_existing_versions = sg.find(
        "Version",
        [
            ["project", "is", sg_project],
            ["sg_task", "is", task],
            ["entity", "is", sg_shot],
        ],
    )

    sg_versions_count = len(sg_existing_versions) + 1
    data = dict()
    data['project'] = sg_project
    print(dest_file)
    if  dest_file is True:
        data['code'] = os.path.splitext(os.path.basename(dest_file))[0] + '_v' + str(sg_versions_count).zfill(3)
    else:
        print(os.path.splitext(os.path.basename(exr_path)))
        data['code'] = os.path.splitext(os.path.basename(exr_path))[0] + '_v' + str(sg_versions_count).zfill(3)

    data['description'] = ""
    data['entity'] = sg_shot
    data['published_files'] = published_files
    data['sg_task'] = task
    data["sg_path_to_frames"] = exr_path
    if dest_file is True:
        data["sg_path_to_movie"] = dest_file
    data["user"] = sg.find_one('HumanUser', [['sg_username', 'is', sg_username]])
    data["sg_version_type"] = "Dailies"
    data["sg_dailies_status"] = "penrev"
    data["sg_submission_time"] = current_time
    data["sg_status_list"] = "na"

    version = sg.create('Version', data)
    filters = [["sg_project", "is", sg_project]]
    fields = ["sg_css"]
    get_css = sg.find_one("CustomNonProjectEntity04", filters, fields)
    if not get_css:
        if mov_upload is True:
            sg.upload('Version', version['id'], dest_file, 'sg_uploaded_movie')

if __name__ == "__main__":
    create_sg_version("{project_name}", "{dest_file}", "{shot_name}", "{published}","{exr_path}","{sg_username}","{mov_upload}")
    """
    if dest_file:
        mov_name = os.path.splitext(os.path.basename(dest_file))[0]
    else:
        mov_name = os.path.splitext(os.path.basename(exr_path))[0]

    proxy_action_file = f"{tmp_path}{mov_name}_proxy_action_version_file.py"
    with open(proxy_action_file, "w") as cf:
        cf.write(create_proxy_action_version_file)

    return proxy_action_file



def create_proxy_action_file(src_file, dest_file,start_frame, end_frame,scan_path,key,folder_value,job_id):
    render_text = folder_value
    
    input_template_mov = "/tools/roto_proxy_mov_template_v01.nk"
    input_template_exr = "/tools/roto_proxy_exr_template_v01.nk"
    output_template_mov = f"{tmp_path}Silhouette_template.nk"
    mov_name = "Silhouette_template"
    output_template_exr = f"{tmp_path}{os.path.basename(dest_file)}_exr.nk"
    input_path = src_file
    proxy_seq = "206_700"
    dest_mov_file = os.path.join(dest_file,render_text,os.path.basename(str(src_file).split(".")[0])+".mov")
    dest_exr_file = os.path.join(dest_file,render_text,os.path.basename(str(src_file).split(".")[0])+"."+f"%0{len(str(start_frame))}d.exr")
    fps = get_fps()
    mov_name = os.path.basename(dest_file)+"_mov"
    exr_name = os.path.basename(dest_file)+"_exr"
    chunk= end_frame-start_frame+1
    if not os.path.exists(os.path.dirname(dest_exr_file)):
        os.makedirs(os.path.dirname(dest_exr_file))
    proxy_template_exr = create_nkt_template_proxy(input_template_exr,output_template_exr,input_path,proxy_seq,dest_exr_file,int(start_frame),int(end_frame),fps,exr_name,scan_path,key,True)
    submit_exr_template = create_nuke_job(mov_name,proxy_template_exr,os.path.basename(dest_file)+"_exr.nk",start_frame,end_frame,job_name=folder_value+"_exr",chunk=10,dependent=job_id)
    proxy_template_mov = create_nkt_template_proxy(input_template_mov,output_template_mov,dest_exr_file,proxy_seq,dest_mov_file,int(start_frame),int(end_frame),fps,mov_name,scan_path,key,True)
    submit_mov_template = create_nuke_job(mov_name,proxy_template_mov,"Silhouette_template.nk",start_frame,end_frame,job_name=folder_value +"_mov",chunk=chunk,dependent=submit_exr_template)
    return submit_mov_template


def create_roto_proxy_action_file(**args):
    
    tmp_path=os.environ['HOME']+"/tmp"
    name=os.path.basename(args['input_path']).split('.')[0]
    if not os.path.exists(tmp_path):
        os.makedirs(tmp_path)
    input_template_exr = "/projects/dev_project/ilam_dev/FP0120_nuke_template_pipeline_v001.nk"
    output_template_mov = f"{tmp_path}/nuke_comp_template.nk"
    
    mov_name = "nuke_roto_template"
    # proxy_seq = "206_700"
   
    # start_frame = int(start_frame)
    # chunk= int(end_frame)-int(start_frame)+1
    # chunk=20
    # fps = 23.975
       
    # mov_folder_path = os.path.dirname(dest_file)
    # if not os.path.exists(mov_folder_path):
    #     os.makedirs(mov_folder_path)

    # dest_file = os.path.join(mov_folder_path,os.path.basename(dest_file))
    args['bake'] = True
    proxy_template_mov = create_roto_nkt_template_proxy(input_template_exr,output_template_mov,args["input_path"],args["dest_path"],args['overlay_render_files'],True,args['startframe'],args['endframe'])
    submit_mov_template = create_nuke_job(mov_name,proxy_template_mov,"nuke_comp_template.nk",args['startframe'],args['endframe'],job_name="test_mov" +"_mov",chunk=20,dependent=args['job_id'])
    return submit_mov_template


def create_roto_nkt_template_proxy(input_template_path,output_template_path,input_path,dest_path,overlay_render_files,bake,startframe="1001",endframe="1010"):
    create_proxy_template= f"""
import sys
sys.path.append("/tools/nuke_tools/ilam/scripts/nkt_api/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2/python")
from processors import roto_proxy_processor_mov
input_template_path="{input_template_path}"
output_template_path="{output_template_path}"
startframe={startframe}
endframe={endframe}
input_path= "{input_path}"
dest_path="{dest_path}"
overlay_render_files = "{overlay_render_files}"
      
roto_proxy_processor_mov(
    input_template_path=input_template_path,
    output_template_path=output_template_path,
    input_path=input_path,
    dest_path=dest_path,
    overlay_render_files=overlay_render_files,
    startframe=startframe,
    endframe=endframe,
    bake=True
)
print("over")
"""
    # print("input_path",input_path)
    # print("proxy_seq",proxy_seq)
    # mov_name = name.rsplit('.', 1)[0]
    tmp_path=os.environ['HOME']+"/tmp"
    if not os.path.exists(tmp_path):
        os.makedirs(tmp_path)
    proxy_template = f"{tmp_path}/roto_template.py"
    with open(proxy_template, "w") as cf:
        cf.write(create_proxy_template)
    print("pt",proxy_template)
    return proxy_template









def _create_SG_version(project_name,task_id, version_num ,source_path, dest_file):
    create_proxy_action_version_file = f"""
import sys
import os
from glob import glob

def _create_sg_version(project_name,task_id, version_num ,source_path, dest_file):
    sys.path.insert(0, "/tools/bpipe/staging/bfs_sg_requests")
    import sg_requests
    SG = sg_requests.ShotgridConnection(project=project_name)
    SG.change_context("Task", task_id)
    sfx_delivery_version = SG.publish.delivery_publish.DeliveryVersion(
        SG, 
        "delivery_sfx", 
        SG.context,
        comment="",
        sg_version_fields={
            "sg_client_deliverable": True
        }
    )
    sfx_delivery_version.version_type = "SFX Scene"
    sfx_delivery_version._version_number = int(version_num)
    sfx_delivery_version.properties.source_path = source_path

    sfx_delivery_exporter = SG.publish.delivery_publish.DeliveryExporter(
        sfx_delivery_version,
        pf_type="SFX Scene",
        file_ext="exr"
    )
    sfx_delivery_version.add_exporter(sfx_delivery_exporter)
    sfx_delivery_exporter.publish_path = dest_file
    sfx_delivery_version.create_sg_version = True
    sfx_delivery_version.create_sg_entities()


    
if __name__ == "__main__":
    _create_sg_version("{project_name}", "{task_id}", "{version_num}", "{source_path}","{dest_file}")
    """
    if dest_file:
        file_name = os.path.splitext(os.path.basename(dest_file))[0]
    else:
        file_name = os.path.splitext(os.path.basename(exr_path))[0]

    proxy_action_file = f"{tmp_path}{file_name}_version_create.py"
    with open(proxy_action_file, "w") as cf:
        cf.write(create_proxy_action_version_file)

    return proxy_action_file

