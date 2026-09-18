import sys
import os
from glob import glob
import urllib.error
import ssl
def create_sg_version(project_name, dest_file, shot_name):
    import logging
    import sys
    sys.path.insert(0, "/tools/bpipe/staging/bfs_sg_requests")
    # import sg_requests
    # os.environ["B_SHOW"] = "dev_project"
    # SG = sg_requests.ShotgridConnection(project="dev_project")
    sys.path.append('/tools/common/scripts/render_sg_utils')
    import sg_connect_bkp as sg_connect
    SG = sg_connect.sg_connect()
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    sg_logger = logging.getLogger('shotgun_api3')
    sg_logger.setLevel(logging.DEBUG)
    sg = SG
    sg_project = sg.find_one('Project', [['name', 'is', project_name]])
    print(sg_project)
    sg_shot = sg.find_one('Shot', [['project', 'is', sg_project], ['code', 'is', shot_name]])
    print(sg_shot)
    user_sg = sg.find_one(
            "HumanUser",
            [["sg_username", "is", "manikanda.srinivasulu"]],
            ["sg_username", "department"],
    )
    task_id = 338517
    task = sg.find_one("Task", [["id", "is", task_id]], ["content", "entity", "step", "project", "sg_status_list"])
    data = dict()
    data['project'] = sg_project
    data['description'] = ""
    data['entity'] = sg_shot
    data['created_by'] = user_sg
    data['sg_task'] = task
    data["user"] = sg.find_one('HumanUser', [['sg_username', 'is', "manikanda.srinivasulu"]])
    data["sg_version_type"] = "Dailies"
    data["sg_status_list"] = "na"
    logger.debug('Creating a Version...')

    version = sg.create('Version', data)
    print(version)
    upload_version = sg.upload('Version', version['id'], dest_file, 'sg_uploaded_movie')
    print(version["id"])
    delete_version = sg.delete('Version', version['id'])

    # logger.debug('API call version:',version)
    # logger.debug('API call upload_version:',upload_version)
    # logger.debug('API call delete_version:',delete_version)
# count = 0
# for i in range(1,51):
#     try:
#         version = create_sg_version("dev_project", "/projects/oou_tim/004_bfb_0400/dept/publish/prep/review/qt/004_bfb_0400_prep_test_v002.mov", "001_0470")
#         print(f"-----------------> {i}")
#     except urllib.error.URLError as e:
#         count += 1
#         print("failed_count_live",count)
#     except ssl.SSLEOFError as e:
#         count += 1
#         print("failed_count_live",count)

#         print(count)
#     except Exception as e:
#         print(e)

# print("Failed count",count)

version = create_sg_version("dev_project", "/projects/oou_tim/004_bfb_0400/dept/publish/prep/review/qt/004_bfb_0400_prep_test_v002.mov", "001_0470")


    
