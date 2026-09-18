

import fx
import sys 
sys.path.append("/tools/common/scripts/render_sg_utils")
from  sg_connect import sg_connect
import sgtk
sg = sg_connect()

def sg_task_frame():
    project = fx.activeProject().path
    tk = sgtk.sgtk_from_path(str(project))
    context = tk.context_from_path(project)
    project_entity = context.project
    step_data = context.step

    task_filters = [["entity", "is", context.entity],["step","is",step_data]]
    task_fields = ["sg_task_cut_in","sg_task_cut_out"]

    tasks = sg.find("Task", task_filters,task_fields)
    valid_task = next(
    (task for task in tasks if task['sg_task_cut_in'] is not None and task['sg_task_cut_out'] is not None),
    None
    )
    if valid_task:
        start_frame = int(valid_task['sg_task_cut_in'])
        end_frame = int(valid_task['sg_task_cut_out'])
        session = fx.activeSession()
        new_work_range = (int(start_frame), int(end_frame))  # Example: Start at frame 1001, end at frame 1160
        session.workRange = new_work_range
