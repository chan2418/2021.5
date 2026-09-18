import sys
sys.path.append("/tools/common/scripts/render_sg_utils/")
import sg_connect
import os 


sg = sg_connect.sg_connect()

filters = [['sg_username', 'is', "rohitk"]]

# Define the fields you want to retrieve
fields = ['id', 'type', 'name']

# Find the person(s) matching the username
persons = sg.find_one('HumanUser', filters, fields)

project_name = "bfu_stb_sg"
project = sg.find_one("Project", [["name", "is", project_name]])
if project:
    versions_prenrev = sg.find(
        "Version",
        [
            ["project", "is", project],
            ["sg_status_list", "is", "penrev"],
            ["user", "is", {"type": "HumanUser", "id": int(persons['id'])}],
            # ["user", "is", {"type": "HumanUser", "id": 2266}],                    
        ],
        [
            "code",
            "sg_task",
            "sg_task.Task.task_assignees",
            "sg_task.Task.task_reviewers",
            "sg_task.Task.sg_supervisor",
            "sg_task.Task.sg_supervisor.HumanUser.email",
            # "sg_uploaded_movie",
            "image",
            "sg_task.Task.sg_reviewer",
            "sg_reviewer",
        ],
    )
print(versions_prenrev)