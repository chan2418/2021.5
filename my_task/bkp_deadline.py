"""
Module for submitting Silhouette render jobs to the Deadline render farm.

This module provides a GUI for selecting and submitting render jobs using the
Deadline render farm. It includes functionality for writing job and plugin
information to files, as well as creating and managing the submission dialog.
"""

import socket
import os
import subprocess
import sys
from subprocess import PIPE
from glob import glob
import re
import fx
import json
import shutil

from PySide2.QtWidgets import *
from PySide2 import QtCore
deadline_utils = "/tools/packages/deadline_utils/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2/python/deadline_utils"
file_utils="/tools/packages/fileUtils/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2/python"
pyfiles="/tools/packages/python/3.9.6/platform-linux/arch-x86_64/os-rocky-9.2/python/site-packages"

# sys.path.append(sg_utils)
sys.path.append(deadline_utils)
sys.path.append(file_utils)
sys.path.append(pyfiles)
from python_job import create_python_job
from PySide2.QtWidgets import (QCheckBox, QLabel, QLineEdit, QPushButton, 
                               QGridLayout, QWidget)
from PySide2.QtCore import Qt
from PySide2.QtCore import Signal
import sgtk
from sgtk.authentication import ShotgunAuthenticator
from sgtk.authentication.user import serialize_user
from silhouette.deadline_actions import *
sys.path.append("/apps/silhouette/Silhouette-2023.5/resources/scripts/tools/")
import renderer


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
        file_path = "/tools/site_config.yml"
        proxy_ip = get_sg_proxy(file_path)
        sa = sgtk.authentication.ShotgunAuthenticator()
        user = sa.create_script_user(
            api_script="sgtk_launcher_test",
            api_key="fc$ul1hexdaqkeipjcwdtOdin",
            host="https://basilic.shotgrid.autodesk.com",
            http_proxy = proxy_ip
            )
        sgtk.set_authenticated_user(user)
        
    else:
        authenticator = ShotgunAuthenticator()
        user = authenticator.get_user()
        sgtk.set_authenticated_user(user)
    return user


sg_user = set_sgtk_auth()
sg = sg_user.create_sg_connection()


def create_sg_entries(project_name="dev_project", sequence="", shot=""):
    sg_project = sg.find_one("Project", [["name", "is", project_name]])
    if sg_project:
        sg_seq = sg.find_one("Sequence", [["project", "is", sg_project], ['code', 'is', sequence]])
        if sg_seq:
            sg_shot = sg.find_one("Shot", [["project", "is", sg_project], ['code', 'is', shot], ['sg_sequence', "is", sg_seq]])
            if sg_shot:
                return sg_shot, sg_seq, sg_project
            else:
                data = {"project": sg_project, "code": shot, "sg_sequence": sg_seq}
                sg_shot = sg.create("Shot", data)
                return sg_shot, sg_seq, sg_project
        else:
            data = {"project": sg_project, "code": sequence}
            sg_seq = sg.create("Sequence", data)
            sg_shot = sg.find_one("Shot", [["project", "is", sg_project], ['code', "is", shot], ['sg_sequence', "is", sg_seq]])
            if sg_shot:
                return sg_shot, sg_seq, sg_project
            else:
                data = {"project": sg_project, "code": shot, "sg_sequence": sg_seq}
                sg_shot = sg.create("Shot", data)
                return sg_shot, sg_seq, sg_project


def get_sessional_token():
    sa = sgtk.authentication.ShotgunAuthenticator()
    sa_manager = sgtk.authentication.DefaultsManager()
    token = sa_manager.get_user_credentials()
    return token






def remove_version(publish_type,path):
    field_name = get_field_name()
    data = json.load(open('/tools/common/cfg/silhouette_sg_integration/version_delete.json'))
    review_scripts_value = data[publish_type]['render']
    target_dir = 'silhouette'
    base_path = path[:path.find(target_dir) + len(target_dir) + 1]
    print(base_path)
    list_dir_path = os.listdir(base_path)
    for i in list_dir_path:
        print(i)
        list_path = None
        version_limit = None
        all_files = []
        if i == "review":
            list_path = os.path.join(base_path,i,"qt")
            version_limit = data[publish_type]['render'] - 1
        else:
            if i == "scripts":
                version_limit = data[publish_type]['scripts']
            else:
                version_limit = data[publish_type]['render'] - 1
            list_path = os.path.join(base_path,i)
        print(list_path)
        for a_file in os.listdir(list_path):
            if field_name in a_file:
                all_files.append(a_file)
        allfiles = sorted(all_files)
        print("______________________+++++++++++++++++++++++++++++++++",len(all_files))
        print(version_limit)
        print(all_files)
        if len(allfiles) > version_limit:
            remove_path = os.path.join(list_path,allfiles[0])
            shutil.rmtree(remove_path)

def sg_proxy(
    channel, output, start_frame, end_frame, job_id, 
    project, shot, sg_project, sg_shot, session,selected_id ,label_name,publish_type,check_box_value,shotgrid_submit
):
    
    project = fx.activeProject()
    for i in project.sources:
        source_file_name = i.properties["path"].getValue()
    print(source_file_name)
    file_ext = source_file_name.split(".")[-1]
    render_value = None
    if publish_type == "final_publish":
        template_name = "silhouette_pub_render_movie"
        if file_ext == "exr" or file_ext == "mov":
            exr_template_name = "silhouette_shot_render_pub_stereo"
        else:
            exr_template_name = "silhouette_shot_render_pub_mono_dpx"
    else:
        template_name = "silhouette_shot_render_movie"
        if file_ext == "exr" or file_ext == "mov":
            exr_template_name = "silhouette_shot_render_stereo"
        else:
            exr_template_name = "silhouette_shot_render_mono_dpx"
    if channel == 2:
        render_value = "_alpha"

    
    project = fx.activeProject().path
    tk = sgtk.sgtk_from_path(str(project))
    context = tk.context_from_entity("Task", int(selected_id))
    template = tk.templates[template_name]
    fields = context.as_template_fields(template)
    description_value = os.environ["name_description"]
    fields["name"] = description_value
    fields["artist_name"] = os.getlogin().replace(".","-")
    if publish_type == "final_publish":
        r = sg.summarize(entity_type="PublishedFile",
                        filters=[["task", "is", {"type": "Task", "id": context.task["id"]}],
                                  ["name", "is", fields["name"]+"_pub"],
                                  ["published_file_type.PublishedFileType.code","is","Rendered Image"],
                                  ],
                        summary_fields=[{"field": "version_number", "type": "maximum"}])
        fields["version"] = r["summaries"]["version_number"] +1
        version_number = fields["version"]
        publish_name = fields["name"] + "_pub"

    else:
        version_template = context.sgtk.template_from_path(os.path.dirname(project))
        # version_template.get("")
        version_fields = version_template.get_fields(os.path.dirname(project))
        fields["version"] = version_fields.get('version')
        publish_name = fields["name"]
        version_number = fields["version"]
    fields["SEQ"] = "%04d"
    if "Step" not in fields:
        task_name  = context.step["name"]
        fields["Step"] = task_name
    mov_path = template.apply_fields(fields)
    
    exr_template = tk.templates[exr_template_name]
    exr_path = exr_template.apply_fields(fields)
    print("_+_+_++____++___________",exr_path)
   
    
    project = fx.activeProject()
    mov_review_path = mov_path.split(".")[0]


    if render_value is not None:
        exr_path = exr_path.split(".")[0]+render_value+"."+exr_path.split(".")[1]+"."+exr_path.split(".")[-1]
        
    exr_path = str(exr_path).replace(f".{fields['SEQ']}.",f".%0{len(str(start_frame))}d.")
    folder = {0:"roto_id",1:"roto_pre",2:"roto_overlay",3:"gray_overlay"}
    print("_+_+_+_+++++++",source_file_name)
    match = re.search(r'\.\[(\d+)-\d+\]\.', source_file_name)
    padding_length = len(match.group(1))
    output_path = re.sub(r'\.\[\d+-\d+\]\.', f'.%0{padding_length}d.', source_file_name)
    
    increment_value = 0
    result = any(check_box_value.values())
    if result:
        for key , value in check_box_value.items():
            print("exr_path______",exr_path)
            print(mov_review_path)
            if value == True:
                proxy_action_file = create_proxy_action_file(
                    exr_path,
                    mov_review_path,
                    start_frame,
                    end_frame,
                    output_path,
                    key,
                    folder[key],
                    job_id
                )
                job_id = proxy_action_file
        
                additional_fields = {
                "upstream_published_files": project.path,
                "sg_filepath":exr_path,
                }
                
                publish_data = sgtk.util.register_publish(
                    tk,
                    context,
                    exr_path,
                    publish_name,
                    version_number + increment_value,
                    published_file_type="Rendered Image",
                    sg_data=additional_fields,
                )

                dest_mov_file = os.path.join(mov_review_path,folder[key],os.path.basename(str(exr_path).split(".")[0])+".mov")
                if shotgrid_submit:
                    upload_action = create_proxy_sg_version_file(context.project["name"], dest_mov_file, context.entity["name"], publish_data["id"],exr_path,os.getlogin().replace(".","-"),mov_upload = True)                    
                    version_create = create_python_job(
                        job_name=f"{fx.activeProject().name}_{session.label}_{output.label}",
                        python_job_command=upload_action,
                        dependent=job_id,
                        pool="ingestion_pool",
                        Secondary_pool="2d_pool"
                    )
                    job_id = version_create
                increment_value += 1
    else:
        additional_fields = {
                "upstream_published_files": project.path,
                "sg_filepath":exr_path,
                }

        publish_data = sgtk.util.register_publish(
            tk,
            context,
            exr_path,
            publish_name,
            version_number,
            published_file_type="Rendered Image",
            sg_data=additional_fields,
                )
        dest_mov_file = False
        upload_action = create_proxy_sg_version_file(context.project["name"], dest_mov_file, context.entity["name"], publish_data["id"],exr_path,os.getlogin().replace(".","-"),mov_upload = False)                    
        version_create = create_python_job(
            job_name=f"{fx.activeProject().name}_{session.label}_{output.label}",
            python_job_command=upload_action,
            dependent=job_id,
            pool="ingestion_pool",
            Secondary_pool="2d_pool"
        )

    return publish_type , exr_path

def get_field_name():
        project_path = fx.activeProject().path
        if project_path.split('/')[-1] == "project.sfx":
            project = os.path.dirname(fx.activeProject().path)
        else:
            project = os.path.dirname(fx.activeProject().path)
        tk = sgtk.sgtk_from_path(project)
        context = tk.context_from_path(project)
        if not context:
            print(f"Failed to get context from path: {project}")
            return
        template = tk.template_from_path(project)
        fields = template.get_fields(project)
        print(fields)
        if not fields:
            print(f"No fields extracted from path: {project}")
            return

        # Retrieve the 'name' field
        name_field = fields.get("name")

        return name_field

# def get_version():




class BFSRenderSubmission(QDialog):
    button_clicked = Signal()  # Define button_clicked as a class attribute
    def __init__(self,project_data ,parent=None):
        super(BFSRenderSubmission,self).__init__(parent)
        
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        self.grid_layout = QGridLayout()
        self.setWindowTitle("BFS Deadline Submission")
        self.main_layout.addLayout(self.grid_layout)
        self.session = fx.activeSession()
        self.setFixedWidth(800)
        self.all_outputs = {}
       
        self.create_ui()
        project , shot , seq, task_name,label_name , selected_id = project_data
        self.project_name ,self.shot_name , self.seq_name , self.task_name , self.label_name , self.selected_id= project_data
        
        sg_shot, sg_seq, sg_project = create_sg_entries(project_name=project,sequence=seq, shot=shot)
        print(sg_shot)
        self.sg_project = sg_project  # Save these as instance variables for later use
        self.sg_shot = sg_shot
        # self.final_publish.clicked.connect(self.publish_to_sg)
        roto_step = sg.find_one('Step', [['code', 'is', task_name]])
        task_data = dict()
        task_data['project'] = sg_project
        task_data["step"] = roto_step
        task_data["entity"] = sg_shot
        task_data["content"] = task_name  # Corrected variable name here
        task = sg.find_one(
            "Task",
            [
                ["project", "is", sg_project],
                [
                    "entity",
                    "is",
                    sg_shot,
                ],
                ["step", "is", roto_step],
            ],
        )
        if not task:
            errormessage = "Task is not found please contact production"
            errorDialog = QMessageBox()
            errorDialog.setIcon(QMessageBox.Critical)
            errorDialog.setText("Error")
            errorDialog.setInformativeText(errormessage)
            errorDialog.setWindowTitle("Error")
            errorDialog.setStandardButtons(QMessageBox.Ok)
            errorDialog.exec_()
            return
        
        self.create_signals()

    


    def create_ui(self):
        self.check_all_widget = QCheckBox("Check All")
        self.grid_layout.addWidget(self.check_all_widget, 0, 1, 1, 5, alignment=Qt.AlignCenter)
        style_sheet = """
        /* General Style for Widgets */
        QWidget {
            font-family: Arial, sans-serif;
            font-size: 12px;
        }

        /* Label Style */
        QLabel {
            padding: 5px;
        }

        /* Header Label Style */
        QLabel.header {
            color: #4D4D4D; /* Dark grey text color for headers */
            font-weight: bold;
            background-color: #D0D0D0; /* Light gray background for headers */
            padding: 5px;
            border: 1px solid #B0B0B0; /* Slightly darker gray border for headers */
        }

        /* LineEdit Style */
        QLineEdit {
            border: 1px solid #CCCCCC; /* Light gray border color */
            border-radius: 4px;
            padding: 5px;
            color:white;
        }

        /* QCheckBox Style */
        QCheckBox {
            spacing: 5px;
        }

        /* QPushButton Style */
        QPushButton {
            color: white;
            padding: 10px 20px;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 14px;
            margin: 4px 2px;
            cursor: pointer;
            border-radius: 4px;
        }

    
        QPushButton:disabled {
            background-color: #d0d0d0;
            color: #a0a0a0; /* Light gray text color */
            cursor: not-allowed;
        }

        /* QHBoxLayout */
        QHBoxLayout {
            margin: 0;
            padding: 0;
        }

        /* Grid Layout Spacing */
        QGridLayout {
            margin: 10px;
            spacing: 10px;
        }
        """

    # Apply the style sheet to the widget
        self.setStyleSheet(style_sheet)


        self.grid_layout.addWidget(QLabel("Name"), 1, 0)
        self.grid_layout.addWidget(QLabel("Check"), 1, 1)
        self.grid_layout.addWidget(QLabel("Description"), 1, 2)
        self.grid_layout.addWidget(QLabel("Output Path"), 1, 3)
        self.grid_layout.addWidget(QLabel("Start Frame"), 1, 4)
        self.grid_layout.addWidget(QLabel("End Frame"), 1, 5)

        index = 2
        for session in fx.activeProject().sessions:
            index += 1
            output_label = []
            for output in session.outputs:
                self.grid_layout.addWidget(QLabel(output.label), index, 0)

                # Widgets for each output
                check_widget = QCheckBox()
                label_name_widget = QLineEdit()
                path_widget = QLineEdit()
                path_widget.setReadOnly(True)
                path_widget.setText(output.properties["path"].value)

                sf_widget = QLineEdit()
                sf_widget.setReadOnly(False)
                sf_widget.setFixedWidth(100)
                sf_widget.setText(str(int(session.outputRange[0])))

                ef_widget = QLineEdit()
                ef_widget.setReadOnly(False)
                ef_widget.setFixedWidth(100)
                ef_widget.setText(str(int(session.outputRange[1])))
                label_name_widget.setFixedWidth(60)

                # Store outputs for later use
                if output not in self.all_outputs:
                    self.all_outputs[output] = []

                self.all_outputs[output].append((check_widget, label_name_widget, path_widget, sf_widget, ef_widget))

                # Add widgets to layout
                self.grid_layout.addWidget(check_widget, index, 1)
                self.grid_layout.addWidget(label_name_widget, index, 2)
                self.grid_layout.addWidget(path_widget, index, 3)
                self.grid_layout.addWidget(sf_widget, index, 4)
                self.grid_layout.addWidget(ef_widget, index, 5)

                index += 1

                # Create a horizontal layout for the checkboxes
                checkbox_layout = QHBoxLayout()
                self.roto_id_checkbox = QCheckBox("alpha")
                self.roto_pre_multi_checkbox = QCheckBox("Roto pre multiply")
                self.roto_overlay_checkbox = QCheckBox("color overlay")
                self.gray_overlay_checkbox = QCheckBox("Grey overlay")
                checkbox_layout.addWidget(self.roto_id_checkbox)
                checkbox_layout.addWidget(self.roto_pre_multi_checkbox)
                checkbox_layout.addWidget(self.roto_overlay_checkbox)
                checkbox_layout.addWidget(self.gray_overlay_checkbox)

                # Add the horizontal layout to the grid layout
                self.grid_layout.addLayout(checkbox_layout, index, 0, 1, 6)

                index += 1
                output_label.append(output.label)

            self.submit_deadline_checkbox = QCheckBox("Submit to Deadline")
            self.submit_deadline_checkbox.setChecked(True)
            self.submit_deadline_checkbox.setMinimumWidth(150)  # Adjust the width
            # self.grid_layout.addWidget(self.submit_deadline_checkbox, index, 1)
            self.submit_shotgrid_checkbox = QCheckBox("Submit to Shotgrid")
            self.submit_shotgrid_checkbox.setChecked(True)
            self.grid_layout.addWidget(self.submit_deadline_checkbox, index, 1)
            self.grid_layout.addWidget(self.submit_shotgrid_checkbox, index, 2)
            self.submit_shotgrid_checkbox.setMinimumWidth(150)  # Adjust the width
            # self.grid_layout.addWidget(self.submit_shotgrid_checkbox, index, 2)
            self.review_publish = QPushButton("Review Publish")
            
            self.review_publish.setMinimumWidth(150)
            
            self.final_publish = QPushButton("Final Publish")
            self.final_publish.setMinimumHeight(50)
            self.final_publish.setMinimumWidth(150)  # Adjust the 
            button_layout = QHBoxLayout()
            button_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
            button_layout.addWidget(self.review_publish)
            button_layout.addSpacerItem(QSpacerItem(20, 20))  # Space between buttons
            button_layout.addWidget(self.final_publish)
            self.grid_layout.addLayout(button_layout, index, 3, 1, 2, alignment=Qt.AlignRight)

            self.grid_layout.addWidget(self.review_publish, index, 3)
            self.grid_layout.addWidget(self.final_publish, index, 4)

            index += 1

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setVisible(False)
        self.grid_layout.addWidget(self.progress_bar, index, 0, 1, 10)
        self.grid_layout.setHorizontalSpacing(10)
        self.grid_layout.setVerticalSpacing(10)
        print("_____________",output_label)
        if any("PublishOutputNode" in label for label in output_label):
            self.review_publish.hide()
        else:
            self.final_publish.hide()

    def update_progress_bar(self,value):
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(value)
   
    def toggle_check_all(self, checked):
        for output_widgets in self.all_outputs.values():
            for widgets in output_widgets:
                widgets[0].setChecked(checked)

    def all_sessions_outputs_render(self,publish_type):
        self.update_progress_bar(10)
        for session in fx.activeProject().sessions:
            self.update_progress_bar(20)
            for output in session.outputs:
                if self.all_outputs[output][0][0].isChecked():
                    description = self.all_outputs[output][0][1].text()
                    already_existing_file = self.all_outputs[output][0][2].text()
                    print("________________________",description)
                    if description:
                        print(description)
                        if publish_type == "review_publish":
                            template_name = "silhouette_shot_render_description"
                        else:
                            template_name = "silhouette_shot_render_pub_description"
                        project = fx.activeProject().path
                        tk = sgtk.sgtk_from_path(str(project))
                        context = tk.context_from_entity("Task", int(self.selected_id))
                        template = tk.templates[template_name]
                        fields = context.as_template_fields(template)
                        version = re.search(r'_v(\d+)', already_existing_file).group(1).lstrip('0')
                        formatted_version = version.zfill(3)
                        fields["version"] = int(formatted_version)
                        name = get_field_name()
                        fields["name"] = name
                        fields["description"] = name+"_"+description
                        os.environ["name_description"] = fields["description"]
                        fields["SEQ"] = "%04d"
                        if 'Step' not in fields:
                            task_name  = context.step["name"]
                            fields["Step"] = task_name
                        output_path = template.apply_fields(fields)
                        print(output_path)
                        render_path = os.path.splitext(os.path.splitext(output_path)[0])[0]
                        output.properties["path"].value = render_path
                        project = fx.activeProject()
                        project.save()
                    sf_widget = self.all_outputs[output][0][3]
                    ef_widget = self.all_outputs[output][0][4]
                    print(sf_widget.text())
                    print(ef_widget.text())
                    # return
                    start_frame = int(sf_widget.text())
                    end_frame = int(ef_widget.text())
                    frames = f"{start_frame}-{end_frame}"
                    if self.submit_deadline_checkbox.isChecked():
                        job_id = submit_render(
                            session,
                            job_name=f"{fx.activeProject().name}_{session.label}_{output.label}",
                            group="",
                            pool="ingestion_pool",
                            frames=frames,
                            output=output.label,
                        )
                    else:
                        session = fx.activeSession()
                        new_work_range = (int(start_frame), int(end_frame))  # Example: Start at frame 1001, end at frame 1160
                        session.workRange = new_work_range
                        r = renderer.Renderer()
                        nodes = session.outputs
                        options = { "session":session, "nodes":nodes }
                        progress = fx.PreviewProgressHandler()
                        progress.preview = True
                        progress.pixelAspect = session.pixelAspect
                        r.render(options, progress=progress)
                        job_id =""

                    for node in session.nodes:
                        if node.type == "OutputNode":
                            channel_value = node.properties["channels"].getValue()

                    roto_id_checked = self.roto_id_checkbox.isChecked()
                    roto_pre_multi_checked = self.roto_pre_multi_checkbox.isChecked()
                    roto_overlay_checked = self.roto_overlay_checkbox.isChecked()
                    gray_overlay_checked = self.gray_overlay_checkbox.isChecked()
                    render_check_data = {0:roto_id_checked,1:roto_pre_multi_checked,2:roto_overlay_checked,3:gray_overlay_checked}
                    if self.submit_shotgrid_checkbox.isChecked():
                        shotgrid_submit = True 
                    else:
                        shotgrid_submit = False

                    value = sg_proxy(
                        channel = channel_value, output=output, start_frame=start_frame, end_frame=end_frame, 
                        job_id=job_id, project=self.project_name, shot=self.shot_name, sg_project=self.sg_project, 
                        sg_shot=self.sg_shot, session=session , selected_id=self.selected_id , label_name = self.label_name,publish_type = publish_type,check_box_value = render_check_data,shotgrid_submit=shotgrid_submit)
        if publish_type == "review_publish":
            self.update_progress_bar(100)
            self.close()
            self.parent().close()


        else:
            self.update_progress_bar(40)   
        return value        

    def create_signals(self):
        self.check_all_widget.stateChanged.connect(self.toggle_check_all)
        self.final_publish.clicked.connect(lambda: self.on_button_clicked('final_publish'))
        self.review_publish.clicked.connect(lambda: self.on_button_clicked('review_publish'))

    def on_button_clicked(self,publish_type):
        value = self.all_sessions_outputs_render(publish_type)
        if publish_type != "review_publish":
            self.button_clicked.emit()
        # publish_type , exr_path = value 
        # remove_version(publish_type,exr_path)
        
        