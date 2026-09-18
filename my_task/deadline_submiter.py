"""
Module for submitting Silhouette render jobs to the Deadline render farm.

This module provides a GUI for selecting and submitting render jobs using the
Deadline render farm. It includes functionality for writing job and plugin
information to files, as well as creating and managing the submission dialog.
"""

import json
import os
import re
import shutil
import sys

import fx
from PySide2.QtWidgets import *

deadline_utils = "/tools/packages/deadline_utils/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2/python/deadline_utils"
file_utils = (
    "/tools/packages/fileUtils/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2/python"
)
pyfiles = "/tools/packages/python/3.9.6/platform-linux/arch-x86_64/os-rocky-9.2/python/site-packages"

# sys.path.append(sg_utils)
sys.path.append(deadline_utils)
sys.path.append(file_utils)
sys.path.append(pyfiles)
import sgtk
from PySide2.QtCore import Qt, Signal
from PySide2.QtWidgets import QCheckBox, QGridLayout, QLabel, QLineEdit, QPushButton
from python_job import create_python_job
from sgtk.authentication import ShotgunAuthenticator
from silhouette.deadline_actions import *

sys.path.append("/apps/silhouette/Silhouette-2023.5/resources/scripts/tools/")
import renderer

from mov_render import set_nkt_value

sys.path.append("/apps/silhouette/Silhouette-2023.5/resources/scripts/")
from fx import *
from tools.objectIterator import ObjectFinder

# authenticator = ShotgunAuthenticator()
# user = authenticator.get_user()
# sg = user.create_sg_connection()

if os.getlogin() != "chandru":
    current_user = os.getlogin().replace(".", "-")
else:
    current_user = "manikanda-srinivasulu"


def get_sg_proxy(file_path):
    sg_proxy = None
    with open(file_path, "r") as file:
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
            http_proxy=proxy_ip,
        )
        sgtk.set_authenticated_user(user)

    else:
        authenticator = ShotgunAuthenticator()
        user = authenticator.get_user()
        sgtk.set_authenticated_user(user)
    return user


sg_user = set_sgtk_auth()
sg = sg_user.create_sg_connection()


# def create_sg_entries(project_name="dev_project", sequence="", shot=""):
#     print("_+_+_+_+_+_++_+++++project_name,sequence",project_name,sequence,shot)
#     sg_project = sg.find_one("Project", [["name", "is", project_name]])
#     if sg_project:
#         sg_seq = sg.find_one("Sequence", [["project", "is", sg_project], ['code', 'is', sequence]])
#         if sg_seq:
#             sg_shot = sg.find_one("Shot", [["project", "is", sg_project], ['code', 'is', shot], ['sg_sequence', "is", sg_seq]])
#             print(sg_seq)
#             print("sg_shot",sg_shot)

#             if sg_shot:
#                 return sg_shot, sg_seq, sg_project
#             else:
#                 print("run_______________")
#                 data = {"project": sg_project, "code": shot, "sg_sequence": sg_seq}
#                 filters = [
#                     ["project", "is", data["project"]],
#                     ["code", "is", data["code"]],
#                     ["sg_sequence", "is", data["sg_sequence"]],
#                 ]

#                 fields = ["id", "code", "sg_sequence", "project"]  # or any other fields you need

#                 sg_shot = sg.find_one("Shot", filters, fields)

#                 # sg_shot = sg.create("Shot", data)
#                 return sg_shot, sg_seq, sg_project
#         else:
#             print("Cannot Fetch the sequence contact production")
# data = {"project": sg_project, "code": sequence}
# # sg_seq = sg.create("Sequence", data)
# sg_shot = sg.find_one("Shot", [["project", "is", sg_project], ['code', "is", shot], ['sg_sequence', "is", sg_seq]])
# if sg_shot:
#     return sg_shot, sg_seq, sg_project
# else:
#     print("run_______________test__________")
#     data = {"project": sg_project, "code": shot, "sg_sequence": sg_seq}
#     sg_shot = sg.create("Shot", data)
#     return sg_shot, sg_seq, sg_project


def create_sg_entries(project_name="dev_project", shot=""):
    print("+++ project_name, shot:", project_name, shot)

    # Step 1: Get the project
    sg_project = sg.find_one("Project", [["name", "is", project_name]])

    if not sg_project:
        print("Project not found")
        return

    # Step 2: Get the Shot and also request its Sequence
    sg_shot = sg.find_one(
        "Shot",
        [["project", "is", sg_project], ["code", "is", shot]],
        ["id", "code", "project", "sg_sequence"],
    )

    if sg_shot:
        # sg_seq = sg_shot.get("sg_sequence")
        print("sg_shot:", sg_shot)
        # print("sg_seq:", sg_seq)
        return sg_shot, sg_project
    else:
        print("Shot not found")
        return


def get_sessional_token():
    sa = sgtk.authentication.ShotgunAuthenticator()
    sa_manager = sgtk.authentication.DefaultsManager()
    token = sa_manager.get_user_credentials()
    return token


def remove_version(publish_type, path):
    field_name = get_field_name()
    data = json.load(
        open("/tools/common/cfg/silhouette_sg_integration/version_delete.json")
    )
    review_scripts_value = data[publish_type]["render"]
    target_dir = "silhouette"
    base_path = path[: path.find(target_dir) + len(target_dir) + 1]
    print(base_path)
    list_dir_path = os.listdir(base_path)
    for i in list_dir_path:
        print(i)
        list_path = None
        version_limit = None
        all_files = []
        if i == "review":
            list_path = os.path.join(base_path, i, "qt")
            version_limit = data[publish_type]["render"] - 1
        else:
            if i == "scripts":
                version_limit = data[publish_type]["scripts"]
            else:
                version_limit = data[publish_type]["render"] - 1
            list_path = os.path.join(base_path, i)
        print(list_path)
        for a_file in os.listdir(list_path):
            if field_name in a_file:
                all_files.append(a_file)
        allfiles = sorted(all_files)
        if len(allfiles) > version_limit:
            remove_path = os.path.join(list_path, allfiles[0])
            shutil.rmtree(remove_path)


def output_type_padding():
    project_name = os.environ["B_SHOW"]

    # project = self.sg.find_one("Project", [["name", "is", project_name]], ["sg_output_type"])

    # # Check and print the sg_output_type value
    # if project:
    #     try:
    #         sg_output_type = project.get("sg_output_type")
    #         if sg_output_type is None:
    #             return "exr"
    #         else:
    #             return sg_output_type.lower()
    #     except:
    #         return "exr"
    project = sg.find_one("Project", [["name", "is", project_name]])
    show_config = sg.find_one(
        "CustomNonProjectEntity04",
        [["sg_project", "is", project]],
        ["sg_frame_padding", "sg_extension"],
    )
    return show_config["sg_frame_padding"]


def sg_proxy(
    channel,
    output,
    start_frame,
    end_frame,
    job_id,
    project,
    shot,
    sg_project,
    sg_shot,
    session,
    selected_id,
    label_name,
    publish_type,
    check_box_value,
    shotgrid_submit,
):
    project = fx.activeProject()
    for i in project.sources:
        source_file_name = i.properties["path"].getValue()
    file_ext = source_file_name.split(".")[-1]
    render_value = None
    if publish_type == "final_publish":
        template_name = "silhouette_pub_render_movie"
        if file_ext == "exr" or file_ext == "mov":
            exr_template_name = "silhouette_shot_render_pub_stereo"
        elif file_ext == "dpx":
            exr_template_name = "silhouette_shot_render_pub_mono_dpx"
        else:
            exr_template_name = "silhouette_shot_render_pub_stereo"

    else:
        template_name = "silhouette_shot_render_movie"
        if file_ext == "exr" or file_ext == "mov":
            exr_template_name = "silhouette_shot_render_stereo"
        elif file_ext == "dpx":
            exr_template_name = "silhouette_shot_render_pub_mono_dpx"
        else:
            exr_template_name = "silhouette_shot_render_pub_stereo"
    if channel == 2:
        render_value = "_alpha"

    project = fx.activeProject().path
    tk = sgtk.sgtk_from_path(str(project))
    context = tk.context_from_entity("Task", int(selected_id))
    template = tk.templates[template_name]
    fields = context.as_template_fields(template)
    description_value = os.environ["name_description"]
    fields["name"] = description_value
    fields["artist_name"] = os.getlogin().replace(".", "-")
    if publish_type == "final_publish":
        r = sg.summarize(
            entity_type="PublishedFile",
            filters=[
                ["task", "is", {"type": "Task", "id": context.task["id"]}],
                ["name", "is", fields["name"] + "_pub"],
                ["published_file_type.PublishedFileType.code", "is", "Rendered Image"],
            ],
            summary_fields=[{"field": "version_number", "type": "maximum"}],
        )
        fields["version"] = int(os.environ["render_file_version"])
        version_number = int(os.environ["render_file_version"])
        publish_name = fields["name"] + "_pub"

    else:
        version_template = context.sgtk.template_from_path(os.path.dirname(project))
        # version_template.get("")
        version_fields = version_template.get_fields(os.path.dirname(project))
        fields["version"] = version_fields.get("version")
        publish_name = fields["name"]
        version_number = fields["version"]
    fields["SEQ"] = "%04d"
    if "Step" not in fields:
        task_name = context.step["name"]
        fields["Step"] = task_name.lower()
    mov_path = template.apply_fields(fields)

    exr_template = tk.templates[exr_template_name]
    exr_path = exr_template.apply_fields(fields)

    project = fx.activeProject()
    mov_review_path = mov_path.split(".")[0]

    if render_value is not None:
        exr_path = (
            exr_path.split(".")[0]
            + "."
            + exr_path.split(".")[1]
            + "."
            + exr_path.split(".")[-1]
        )

    exr_path = str(exr_path).replace(
        f".{fields['SEQ']}.", f".%0{len(str(start_frame))}d."
    )
    if len(str(start_frame)) == 3:
        padding = 4
    else:
        padding = len(str(start_frame))

    sg_exr_path_padding = str(exr_path).replace(
        f".%0{len(str(start_frame))}d.", f".%0{str(padding)}d."
    )

    folder = {0: "roto_id", 1: "roto_pre", 2: "roto_overlay", 3: "gray_overlay"}
    match = re.search(r"\.\[(\d+)-\d+\]\.", source_file_name)
    if match:
        padding_length = len(match.group(1))
        output_path = re.sub(
            r"\.\[\d+-\d+\]\.", f".%0{padding_length}d.", source_file_name
        )
    else:
        # mov or single file - no frame range pattern, use as is
        padding_length = len(str(start_frame))
        output_path = source_file_name

    increment_value = 0

    # if os.getlogin() == "chandru":
    #     print(output_path_list)
    #     set_nkt_value(output_path_list,)

    result = any(check_box_value.values())
    if result:
        for key, value in check_box_value.items():
            if value == True:
                proxy_action_file = create_proxy_action_file(
                    sg_exr_path_padding,
                    mov_review_path,
                    start_frame,
                    end_frame,
                    output_path,
                    key,
                    folder[key],
                    job_id,
                )
                job_id = proxy_action_file

                additional_fields = {
                    "upstream_published_files": project.path,
                    "sg_filepath": sg_exr_path_padding,
                }

                publish_data = sgtk.util.register_publish(
                    tk,
                    context,
                    sg_exr_path_padding,
                    publish_name,
                    version_number + increment_value,
                    published_file_type="Rendered Image",
                    sg_data=additional_fields,
                )

                dest_mov_file = os.path.join(
                    mov_review_path,
                    folder[key],
                    os.path.basename(str(exr_path).split(".")[0]) + ".mov",
                )
                id_item = os.environ["selected_id"]
                task_filters = [["id", "is", int(id_item)]]
                task_data = self.sg.find_one("Task", task_filters)
                mov_upload = True
                # padding = output_type_padding()
                if len(str(start_frame)) == 3:
                    padding = 4
                else:
                    padding = len(str(start_frame))
                sg_exr_path = str(exr_path).replace(
                    f".%0{len(str(start_frame))}d.", f".%0{str(padding)}d."
                )
                if shotgrid_submit:
                    upload_action = create_proxy_sg_version_file(
                        context.project["name"],
                        dest_mov_file,
                        context.entity["name"],
                        publish_data["id"],
                        sg_exr_path,
                        os.getlogin().replace(".", "-"),
                        mov_upload,
                        task_data,
                    )
                    version_create = create_python_job(
                        job_name=f"{fx.activeProject().name}_{session.label}_{output.label}",
                        python_job_command=upload_action,
                        dependent=job_id,
                        pool="ingestion_pool",
                        Secondary_pool="2d_pool",
                    )
                    job_id = version_create
                increment_value += 1
    else:
        if len(str(start_frame)) == 3:
            padding = 4
        else:
            padding = len(str(start_frame))
        sg_exr_path_padding = str(exr_path).replace(
            f".%0{len(str(start_frame))}d.", f".%0{str(padding)}d."
        )
        additional_fields = {
            "upstream_published_files": project.path,
            "sg_filepath": sg_exr_path_padding,
        }

        publish_data = sgtk.util.register_publish(
            tk,
            context,
            sg_exr_path_padding,
            publish_name,
            version_number,
            published_file_type="Rendered Image",
            sg_data=additional_fields,
        )
        dest_mov_file = False

    # padding = output_type_padding()
    # if len(start_frame)
    if len(str(start_frame)) == 3:
        padding = 4
    else:
        padding = len(str(start_frame))

    sg_exr_path = str(exr_path).replace(
        f".%0{len(str(start_frame))}d.", f".%0{str(padding)}d."
    )

    return publish_type, exr_path, context, publish_data, sg_exr_path


def get_field_name():
    project_path = fx.activeProject().path
    if project_path.split("/")[-1] == "project.sfx":
        project = os.path.dirname(fx.activeProject().path)
    else:
        project = os.path.dirname(fx.activeProject().path)
    tk = sgtk.sgtk_from_path(project)
    context = tk.context_from_path(project)
    if not context:
        return
    template = tk.template_from_path(project)
    fields = template.get_fields(project)
    if not fields:
        print(f"No fields extracted from path: {project}")
        return

    # Retrieve the 'name' field
    name_field = fields.get("name")

    return name_field


# def get_version():


class BFSRenderSubmission(QDialog):
    button_clicked = Signal()  # Define button_clicked as a class attribute

    def __init__(self, project_data, parent=None):
        super(BFSRenderSubmission, self).__init__(parent)
        if not self._validate_layer_names_pre_ui():
            return
        self.node_checkboxes = []  # List to store node checkboxes
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        self.grid_layout = QGridLayout()
        self.setWindowTitle("BFS Deadline Submission")
        self.main_layout.addLayout(self.grid_layout)
        self.session = fx.activeSession()
        self.setFixedWidth(800)
        self.all_outputs = {}
        # if os.getlogin() == "chandru":
        self.create_ui_test()
        # else:
        #     self.create_ui()
        project, shot, task_name, label_name, selected_id = project_data
        (
            self.project_name,
            self.shot_name,
            self.task_name,
            self.label_name,
            self.selected_id,
        ) = project_data
        sg_shot, sg_project = create_sg_entries(project_name=project, shot=shot)
        self.sg_project = sg_project  # Save these as instance variables for later use
        self.sg_shot = sg_shot
        # self.final_publish.clicked.connect(self.publish_to_sg)
        roto_step = sg.find_one("Step", [["code", "is", task_name]])
        task_data = dict()
        task_data["project"] = sg_project
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

    def _validate_layer_names_pre_ui(self):
        session = fx.activeSession()
        roto_nodes = session.getNodes("RotoNode")
        space_layer_name = []
        for roto_node in roto_nodes:
            layers = roto_node.children
            if not layers:
                continue
            top_label = layers[0].label
            if re.search(r"\s", top_label):
                space_layer_name.append(repr(top_label))

        if space_layer_name:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Invalid Layer Name")
            msg.setText(
                "Top layer name(s) contain spaces — rename before rendering:\n\n"
                + "\n".join(f"  • {name}" for name in space_layer_name)
            )
            msg.exec_()
            return False
        return True

    def get_connected_roto_node(self, output_node, visited=None):
        if visited is None:
            visited = set()

        # Avoid infinite loops by tracking visited nodes
        if output_node in visited:
            return None
        visited.add(output_node)

        # Get all input connections
        input_connection = output_node.getInput(0)
        if not input_connection:
            return None

        source_node = input_connection.source.node
        print(source_node)
        if source_node.type == "RotoNode":
            return source_node

    def show_error_message(self, message):
        errormessage = message
        errorDialog = QMessageBox()
        errorDialog.setIcon(QMessageBox.Critical)
        errorDialog.setText("Error")
        errorDialog.setInformativeText(errormessage)
        errorDialog.setWindowTitle("Error")
        errorDialog.setStandardButtons(QMessageBox.Ok)
        errorDialog.exec_()

    def create_ui_test(self):
        # Add header labels to the grid layout
        self.grid_layout.addWidget(QLabel("Check"), 1, 0)  # 'Check' label on left
        self.grid_layout.addWidget(
            QLabel("Name"), 1, 1
        )  # 'Name' label in the second column
        self.grid_layout.addWidget(QLabel("Description"), 1, 2)
        self.grid_layout.addWidget(QLabel("Output Path"), 1, 3)
        self.grid_layout.addWidget(QLabel("Start Frame"), 1, 4)
        self.grid_layout.addWidget(QLabel("End Frame"), 1, 5)
        index = 2
        # session_outputs = [
        #     {"label": "Output 1", "path": "/path/to/output1", "start_frame": 1, "end_frame": 100, "description": "Desc 1"},
        #     {"label": "Output 2", "path": "/path/to/output2", "start_frame": 101, "end_frame": 200, "description": "Desc 2"},
        # ]
        for session in fx.activeProject().sessions:
            index += 1
            output_label = []
            for output in session.outputs:
                # Create 'Check' checkbox
                if " " in output.label:
                    self.show_error_message(
                        f"OutputNode label '{output.label}' is invalid: contains spaces."
                    )
                    self.close()
                    return

                check_widget = QCheckBox()
                self.node_checkboxes.append(
                    check_widget
                )  # Store the checkbox for later use
                label_name_widget = QLabel(
                    output.label
                )  # Use QLabel to display node name as text
                description_widget = QLineEdit()
                description_widget.setReadOnly(True)  # Make description read-only

                path_widget = QLineEdit(output.properties["path"].value)
                path_widget.setReadOnly(True)  # Make path read-only

                sf_widget = QLineEdit()
                sf_widget.setReadOnly(False)
                sf_widget.setFixedWidth(100)
                sf_widget.setText(str(int(session.outputRange[0])))

                ef_widget = QLineEdit()
                ef_widget.setReadOnly(False)
                ef_widget.setFixedWidth(100)
                ef_widget.setText(str(int(session.outputRange[1])))

                roto_node = self.get_connected_roto_node(output)
                layers = roto_node.children
                top_layername = layers[0].label
                description_layer = str(top_layername)
                pattern = r"^[A-Za-z0-9]+$"

                # if not re.match(pattern, description_layer):
                #     self.show_error_message(f"Invalid layer name on '{output.label}' '{description_layer}'. "
                #                     "It must contain only letters, numbers no underscores,no spaces and no special character.")
                #     self.close()
                #     return

                description_widget.setText(description_layer)
                description_widget.setFixedWidth(60)

                # Store outputs for later use
                if output not in self.all_outputs:
                    self.all_outputs[output] = []

                self.all_outputs[output].append(
                    (
                        check_widget,
                        description_widget,
                        path_widget,
                        sf_widget,
                        ef_widget,
                    )
                )

                # Add widgets to layout
                self.grid_layout.addWidget(check_widget, index, 0)  # 'Check' checkbox
                self.grid_layout.addWidget(
                    label_name_widget, index, 1
                )  # 'Name' node name (as label)
                self.grid_layout.addWidget(
                    description_widget, index, 2
                )  # 'Description' field
                self.grid_layout.addWidget(path_widget, index, 3)  # 'Output Path'
                self.grid_layout.addWidget(sf_widget, index, 4)  # 'Start Frame'
                self.grid_layout.addWidget(ef_widget, index, 5)  # 'End Frame'

                index += 1

                # Create a horizontal layout for additional checkboxes (if any)
                checkbox_layout = QHBoxLayout()
                self.roto_id_checkbox = QCheckBox("alpha")
                self.roto_pre_multi_checkbox = QCheckBox("Roto pre multiply")
                self.roto_overlay_checkbox = QCheckBox("color overlay")
                self.gray_overlay_checkbox = QCheckBox("Grey overlay")

                # Align the checkboxes in the center
                checkbox_layout.addWidget(self.roto_id_checkbox)
                checkbox_layout.addWidget(self.roto_pre_multi_checkbox)
                checkbox_layout.addWidget(self.roto_overlay_checkbox)
                checkbox_layout.addWidget(self.gray_overlay_checkbox)
                for i in range(checkbox_layout.count()):
                    widget = checkbox_layout.itemAt(i).widget()
                    if widget:
                        widget.hide()

                # Center the checkbox layout in the grid layout
                self.grid_layout.addLayout(
                    checkbox_layout, index, 0, 1, 6, alignment=Qt.AlignCenter
                )
                index += 1
                output_label.append(output.label)

        # Add 'Check All' checkbox to left corner
        self.check_all_widget = QCheckBox("Check All")
        self.grid_layout.addWidget(
            self.check_all_widget, index, 0, 1, 2, alignment=Qt.AlignLeft
        )

        # Create a horizontal layout for the bottom-left checkboxes
        checkbox_layout_bottom_left = QHBoxLayout()
        self.submit_deadline_checkbox = QCheckBox("Submit to Deadline")
        self.submit_shotgrid_checkbox = QCheckBox("Submit to ShotGrid")
        checkbox_layout_bottom_left.addWidget(self.submit_deadline_checkbox)
        checkbox_layout_bottom_left.addWidget(self.submit_shotgrid_checkbox)

        # Add the checkbox layout to the grid at the bottom left
        self.grid_layout.addLayout(checkbox_layout_bottom_left, index + 1, 0, 1, 3)

        # Add Submit button (Final Publish) at the bottom-right
        self.review_publish = QPushButton("Review Publish")

        self.review_publish.setMinimumWidth(150)
        button_layout = QHBoxLayout()
        self.final_publish = QPushButton("Final Publish")
        button_layout.addSpacerItem(
            QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        )
        button_layout.addWidget(self.final_publish)
        button_layout.addWidget(self.review_publish)
        self.grid_layout.addLayout(
            button_layout, index + 1, 3, 1, 2, alignment=Qt.AlignRight
        )

        # Add Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setVisible(False)
        self.grid_layout.addWidget(self.progress_bar, index + 2, 0, 1, 10)

        # Adjust grid layout spacing
        self.grid_layout.setHorizontalSpacing(10)
        self.grid_layout.setVerticalSpacing(10)

        # Connect the "Check All" checkbox to toggle all node checkboxes
        self.check_all_widget.stateChanged.connect(self.toggle_all_checkboxes)
        if any("PublishOutputNode" in label for label in output_label):
            self.review_publish.hide()
        else:
            self.final_publish.hide()

    def toggle_all_checkboxes(self, state):
        # Toggle all node checkboxes based on the "Check All" checkbox state
        for checkbox in self.node_checkboxes:
            checkbox.setChecked(state == Qt.Checked)

    def create_ui(self):
        self.check_all_widget = QCheckBox("Check All")
        self.grid_layout.addWidget(
            self.check_all_widget, 0, 1, 1, 5, alignment=Qt.AlignCenter
        )
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
                try:
                    roto_node = self.get_connected_roto_node(output)
                    layers = roto_node.children
                    top_layername = layers[0].label
                    description_layer = str(top_layername)
                    label_name_widget.setText(description_layer)

                except:
                    pass

                label_name_widget.setFixedWidth(60)

                # Store outputs for later use
                if output not in self.all_outputs:
                    self.all_outputs[output] = []

                self.all_outputs[output].append(
                    (check_widget, label_name_widget, path_widget, sf_widget, ef_widget)
                )

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
                for i in range(checkbox_layout.count()):
                    widget = checkbox_layout.itemAt(i).widget()
                    if widget:
                        widget.hide()

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
            button_layout.addSpacerItem(
                QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
            )
            button_layout.addWidget(self.review_publish)
            button_layout.addSpacerItem(QSpacerItem(20, 20))  # Space between buttons
            button_layout.addWidget(self.final_publish)
            self.grid_layout.addLayout(
                button_layout, index, 3, 1, 2, alignment=Qt.AlignRight
            )

            self.grid_layout.addWidget(self.review_publish, index, 3)
            self.grid_layout.addWidget(self.final_publish, index, 4)

            index += 1

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setVisible(False)
        self.grid_layout.addWidget(self.progress_bar, index, 0, 1, 10)
        self.grid_layout.setHorizontalSpacing(10)
        self.grid_layout.setVerticalSpacing(10)
        print("_____________", output_label)
        if any("PublishOutputNode" in label for label in output_label):
            self.review_publish.hide()
        else:
            self.final_publish.hide()

    def update_progress_bar(self, value):
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(value)

    def toggle_check_all(self, checked):
        for output_widgets in self.all_outputs.values():
            for widgets in output_widgets:
                widgets[0].setChecked(checked)

    def select_all(self, node):
        node = node
        if node:
            finder = ObjectFinder(hidden=False)
            objects = finder.find(node.children)
            objects.append(node)
            return objects

    def layer_name_validation(self):
        session = fx.activeSession()
        roto_nodes = session.getNodes("RotoNode")
        space_layer_name = []
        for roto_node in roto_nodes:
            layers = roto_node.children
            if not layers:
                continue
            top_layer_label = layers[0].label  # only first child — same as render uses
            if re.search(r"\s", top_layer_label):
                space_layer_name.append(
                    repr(top_layer_label)
                )  # repr shows hidden spaces

        if space_layer_name:
            self.show_error_message(
                "Top layer name(s) contain spaces — rename before rendering:\n\n"
                + "\n".join(f"  • {name}" for name in space_layer_name)
            )
            return False

    def silhouette_shape_export(self):
        session = fx.activeSession()
        project_path = fx.activeProject().path
        sil_shape_path = os.path.dirname(project_path)
        roto_nodes = session.getNodes("RotoNode")
        for roto_node in roto_nodes:
            layers = roto_node.children
            top_layername = layers[0].label
            selected_object = self.select_all(roto_node)
            shape_export_path = os.path.join(
                sil_shape_path, os.path.basename(sil_shape_path) + ".fsx"
            )
            viewer.node = roto_node
            select(selected_object)
            sil_exporter = fx.io_modules["Silhouette Shapes"]
            print(sil_exporter.can_export)
            if sil_exporter.can_export:
                sil_exporter.export(shape_export_path)
                select([])

    def get_next_version(self, tk, context, template_name, field_name, current_user):
        """
        Get the highest version file found on disk for a given template
        :param tk:
        :param template_name:
        :return:
        """

        template = tk.templates[template_name]
        fields = context.as_template_fields(template)
        fields["artist_name"] = current_user
        skip_fields = ["version"]
        file_paths = tk.paths_from_template(
            template, fields, skip_fields, skip_missing_optional_keys=True
        )
        latest_file = None
        highest_version = 0
        for a_file in file_paths:
            path_fields = template.get_fields(a_file)
            if path_fields["description"] == field_name:
                if path_fields["version"] > highest_version:
                    highest_version = path_fields["version"]
                    latest_file = a_file
        return latest_file, highest_version

    def append_project_note(self, new_data):
        project = fx.activeProject()

        note_text = project.note

        if note_text:
            try:
                data = json.loads(note_text)
            except ValueError:
                data = {}
        else:
            data = {}

        data.update(new_data)  # merges keys

        project.note = json.dumps(data)

        project.save()

    def layer_name_validation(self):
        session = fx.activeSession()
        roto_nodes = session.getNodes("RotoNode")
        space_layer_name = []
        for roto_node in roto_nodes:
            for layer_main in roto_node.children:
                if " " in layer_main.label:
                    space_layer_name.append(layer_main.label)

        if space_layer_name:
            self.show_error_message(
                "Layer name(s) contain spaces — rename before rendering:\n\n"
                + "\n".join(f"  • {name}" for name in space_layer_name)
            )
            return False

    def all_sessions_outputs_render(self, publish_type):
        if self.layer_name_validation() is False:
            return
        self.update_progress_bar(10)
        if os.getlogin() == "chandru":
            self.silhouette_shape_export()
        output_path_list = []
        publish_data_list = []
        for session in fx.activeProject().sessions:
            self.update_progress_bar(20)
            for output in session.outputs:
                if self.all_outputs[output][0][0].isChecked():
                    description = self.all_outputs[output][0][1].text()
                    already_existing_file = self.all_outputs[output][0][2].text()
                    print("________________________", description)
                    if description:
                        project = fx.activeProject()
                        for i in project.sources:
                            source_file_name = i.properties["path"].getValue()
                        file_ext = source_file_name.split(".")[-1]
                        print(file_ext)
                        if publish_type == "review_publish":
                            if file_ext == "dpx":
                                template_name = "silhouette_shot_render_description_dpx"
                            else:
                                template_name = "silhouette_shot_render_description"
                        else:
                            if file_ext == "dpx":
                                print("file_ext___________", file_ext)
                                template_name = (
                                    "silhouette_shot_render_pub_description_dpx"
                                )
                                output.properties["format"].value = "DPX"
                            else:
                                output.properties["format"].value = "OpenEXR"
                                template_name = "silhouette_shot_render_pub_description"
                        project = fx.activeProject().path
                        tk = sgtk.sgtk_from_path(str(project))
                        context = tk.context_from_entity("Task", int(self.selected_id))
                        template = tk.templates[template_name]
                        fields = context.as_template_fields(template)
                        name = get_field_name()
                        fields["name"] = name
                        fields["artist_name"] = current_user
                        fields["description"] = name + "_" + description
                        file_path, version = self.get_next_version(
                            tk,
                            context,
                            template_name,
                            fields["description"],
                            current_user,
                        )
                        fields["version"] = int(version) + 1
                        os.environ["name_description"] = fields["description"]
                        os.environ["render_file_version"] = str(fields["version"])

                        fields["SEQ"] = "%04d"
                        if "Step" not in fields:
                            task_name = context.step["name"]
                            fields["Step"] = task_name.lower()
                        output_path = template.apply_fields(fields)
                        render_path = os.path.splitext(
                            os.path.splitext(output_path)[0]
                        )[0]
                        print("render_path____________________", render_path)
                        output_path_list.append(output_path)
                        output.properties["path"].value = render_path
                        project = fx.activeProject()
                        project.save()
                    sf_widget = self.all_outputs[output][0][3]
                    ef_widget = self.all_outputs[output][0][4]
                    # return
                    start_frame = int(sf_widget.text())
                    end_frame = int(ef_widget.text())
                    frames = f"{start_frame}-{end_frame}"

                    if self.submit_deadline_checkbox.isChecked():
                        batch_name = str(fx.activeProject().name)
                        job_id = submit_render_commandline(
                            session,
                            batch_name=batch_name,
                            job_name=f"{fx.activeProject().name}_{session.label}_{output.label}",
                            group="",
                            pool="ingestion_pool",
                            frames=frames,
                            output=output.label,
                            department="Roto",
                            scene_file=fx.activeProject().path,
                        )
                        # else:
                        #     job_id = submit_render(
                        #         session,
                        #         batch_name=batch_name,
                        #         job_name=f"{fx.activeProject().name}_{session.label}_{output.label}",
                        #         group="",
                        #         pool="ingestion_pool",
                        #         frames=frames,
                        #         output=output.label,
                        #         department="Roto",
                        #         # scene_file=fx.activeProject().path,
                        #     )
                        print("job_id silhoutte:", job_id)
                    else:
                        session = fx.activeSession()
                        new_work_range = (
                            int(start_frame),
                            int(end_frame),
                        )  # Example: Start at frame 1001, end at frame 1160
                        session.workRange = new_work_range
                        r = renderer.Renderer()
                        nodes = session.outputs
                        options = {"session": session, "nodes": nodes}
                        progress = fx.PreviewProgressHandler()
                        progress.preview = True
                        progress.pixelAspect = session.pixelAspect
                        r.render(options, progress=progress)
                        job_id = ""

                    for node in session.nodes:
                        if node.type == "OutputNode":
                            channel_value = node.properties["channels"].getValue()

                    roto_id_checked = self.roto_id_checkbox.isChecked()
                    roto_pre_multi_checked = self.roto_pre_multi_checkbox.isChecked()
                    roto_overlay_checked = self.roto_overlay_checkbox.isChecked()
                    gray_overlay_checked = self.gray_overlay_checkbox.isChecked()
                    render_check_data = {
                        0: roto_id_checked,
                        1: roto_pre_multi_checked,
                        2: roto_overlay_checked,
                        3: gray_overlay_checked,
                    }
                    if self.submit_shotgrid_checkbox.isChecked():
                        shotgrid_submit = True
                    else:
                        shotgrid_submit = False

                    value = sg_proxy(
                        channel=channel_value,
                        output=output,
                        start_frame=start_frame,
                        end_frame=end_frame,
                        job_id=job_id,
                        project=self.project_name,
                        shot=self.shot_name,
                        sg_project=self.sg_project,
                        sg_shot=self.sg_shot,
                        session=session,
                        selected_id=self.selected_id,
                        label_name=self.label_name,
                        publish_type=publish_type,
                        check_box_value=render_check_data,
                        shotgrid_submit=shotgrid_submit,
                    )

                    publish_type_value, exr_path, context, publish_data, sg_exr_path = (
                        value
                    )
                    publish_data_list.append(publish_data["id"])

        if publish_type == "review_publish":
            self.update_progress_bar(100)
            self.close()
            self.parent().close()

        else:
            print("job_id_________-", job_id)
            job_id = set_nkt_value(
                output_path_list, start_frame, end_frame, job_id
            )  # for mov
            print(job_id)
            project = os.path.dirname(fx.activeProject().path)
            file_name = os.path.basename(project).split(".")[0] + ".mov"
            dest_mov_file = (
                output_path_list[0].split("/render/")[0] + "/review/qt/" + file_name
            )
            id_item = os.environ["selected_id"]
            task_filters = [["id", "is", int(id_item)]]
            task_data = sg.find_one("Task", task_filters)
            mov_upload = True
            upload_action = create_proxy_sg_version_file(
                context.project["name"],
                dest_mov_file,
                context.entity["name"],
                publish_data_list,
                sg_exr_path,
                os.getlogin().replace(".", "-"),
                mov_upload,
                task_data,
            )
            version_create = create_python_job(
                job_name=f"{fx.activeProject().name}_{session.label}_{output.label}",
                python_job_command=upload_action,
                dependent=job_id,
                pool="ingestion_pool",
                Secondary_pool="2d_pool",
                department="Roto",
            )
            self.update_progress_bar(40)
        return value

    def create_signals(self):
        self.check_all_widget.stateChanged.connect(self.toggle_check_all)
        self.final_publish.clicked.connect(
            lambda: self.on_button_clicked("final_publish")
        )
        self.review_publish.clicked.connect(
            lambda: self.on_button_clicked("review_publish")
        )

    def on_button_clicked(self, publish_type):
        value = self.all_sessions_outputs_render(publish_type)
        if publish_type != "review_publish":
            self.button_clicked.emit()
        # publish_type , exr_path = value
        # remove_version(publish_type,exr_path)
