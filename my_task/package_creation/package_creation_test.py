import datetime
import datetime as _dt
import inspect
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

if os.getlogin() == "chandru":
    pass


import fx

sys.path.append(
    "/tools/packages/python/3.9.6/platform-linux/arch-x86_64/os-rocky-9.2/python/site-packages"
)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import yaml

try:
    b_show_name = os.environ["B_SHOW"]
    sys.path.insert(0, "/tools/projects/{}/install/core/python".format(b_show_name))
except:
    pass
import sgtk
from PySide2 import QtCore, QtWidgets
from PySide2.QtCore import Qt
from sgtk.authentication import ShotgunAuthenticator

sys.path.append(
    "/tools/packages/deadline_utils/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2/python/deadline_utils"
)
from nuke_job import *

deadline_utils = "/tools/packages/deadline_utils/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2/python/deadline_utils"
file_utils = (
    "/tools/packages/fileUtils/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2/python"
)
pyfiles = "/tools/packages/python/3.9.6/platform-linux/arch-x86_64/os-rocky-9.2/python/site-packages"
sys.path.append(deadline_utils)
sys.path.append(file_utils)
sys.path.append(pyfiles)
from fx import *
from python_job import create_python_job
from silhouette.deadline_actions import *
from silhouette.deadline_actions import create_packager_SG_version

from deadline_actions import *
from deadline_submiter_packager import show_render_settings_ui
from user_input_dialog import *

sys.path.append("/apps/silhouette/Silhouette-2023.5/resources/scripts/")
from tools.objectIterator import ObjectFinder

sys.path.insert(0, "/tools/bpipe/staging/bfs_sg_requests")
import sg_requests

sys.path.append(
    "/tools/packages/sgUtils/1.0.2/platform-linux/arch-x86_64/os-rocky-9.2/python/"
)
from site_config_py2 import SiteConfig

sys.path.append("/tools/bpipe/config/")
from coloroverlay_ui import mxp_ui

SG = sg_requests.ShotgridConnection(project=os.environ["B_SHOW"])


class PackagingUI:
    """
    A class to handle the packaging UI for rendering in Nuke.

    This class initializes the user interface for rendering settings, manages
    project data, interacts with Shotgun for version control, and sets up the
    necessary nodes in Nuke. It handles user inputs and provides methods for
    updating the UI based on selected versions.
    """

    def __init__(self):
        """
        Initializes the PackagingUI instance.

        This method sets up the user interface, initializes project-related data,
        authenticates with Shotgun, reads configuration from a YAML file, and
        creates the necessary nodes in Nuke. It also connects UI signals to
        relevant slot methods for interactivity.

        Returns:
            None
        """
        super(PackagingUI, self).__init__()
        self.render_ui, self.app = show_render_settings_ui()
        self.input_path = None
        self.base_path = None
        self.project_name = None
        self.client_name = None
        self.show_name = None
        self.shot_name = None
        self.department_name = None
        self.task_id = None
        self.seq = None
        self.slate_note = None
        self.nmb_actual_path = {}
        self.versions = "v001"
        self.approved_version = []
        self.render_path_dict = {}
        self.layer_dict = {}
        self.layer_job_ids = []
        self.packed_layer_dict = {}
        self.job_id = None
        self.out_version = "v001"
        self.out_path = ""
        self.job_id = ""
        self.submit_deadline = False
        self.template_input_data = {}
        self.render_folder_dict = {}
        self.mb_nuke_path = {}
        self.matte_shape_bkp = {}

        self.nmb_nuke_path = {}
        self.b_package_data = {}
        self.nmb_folder_value = {}
        self.mb_folder_path = []
        # self.start_frame = self.render_ui.startFrameInput.text()
        # self.end_frame = self.render_ui.endFrameInput.text()
        self.placeholders = {}
        self.nmb_shape = None
        self.applied_folder_structure = None

        self.sg_user = self.set_sgtk_auth()
        self.source_path = None
        self.full_source_path = None
        self.sg_plate_name = ""

        self.sg = self.sg_connection()
        self.current_user = os.getlogin().replace(".", "-")
        self.user_name = self.get_username()
        pentec_version = self.check_version_pentec()
        if pentec_version is False:
            return
        self.yaml_data = self.read_yaml()
        self.initialize_data()
        # self.create_bfs_nodes()
        # self.render_ui.approvedVersionInput.currentTextChanged.connect(self.update_version_from_approved)
        # self.render_ui.approvedVersionList.itemClicked.connect(self.update_version_from_approved)
        # self.render_ui.version_update_signal.connect(self.fetch_structure)
        self.call_back()
        self.render_ui.templateButton.clicked.connect(self.open_input_template_dialog)
        self.render_ui.plate_name.currentIndexChanged.connect(self.on_plate_changed)
        # if os.getlogin() == "manikanda.srinivasulu":
        self.render_ui.user_plate_name.editingFinished.connect(self.on_knob_change)

    def manifest_copy(self, **args):
        manifest_src = self.placeholders.get("manifest_json")
        if not manifest_src:
            print("[manifest_copy] no 'manifest_json' token set — skipping")
            return

        if not os.path.exists(manifest_src):
            print(f"[manifest_copy] source manifest not found: {manifest_src}")
            return

        base_path = self.out_path + self.placeholders.get("project_base_path", "")
        actual_base = self.apply_placeholders(base_path, self.placeholders)
        dst_manifest = os.path.join(actual_base, "manifest.json")

        try:
            with open(manifest_src, "r") as f:
                manifest_data = json.load(f)
        except Exception as e:
            print(f"[manifest_copy] failed reading source manifest: {e}")
            return

        # only fills keys that already exist in the template — won't add new ones
        for key in (
            "shot",
            "sg_plate_name",
            "out_version",
            "plate_version",
            "date_folder",
        ):
            if key in manifest_data and key in self.placeholders:
                manifest_data[key] = self.placeholders[key]

        os.makedirs(os.path.dirname(dst_manifest), exist_ok=True)
        try:
            with open(dst_manifest, "w") as f:
                json.dump(manifest_data, f, indent=4)
            print(f"[manifest_copy] ✅ wrote manifest → {dst_manifest}")
        except Exception as e:
            print(f"[manifest_copy] failed writing manifest: {e}")

    def notes_create(self, **args):
        artist_notes = (getattr(self, "version_data", "") or "").strip()
        shot = self.placeholders.get("shot", "")
        base_path = self.out_path + self.placeholders.get("project_base_path", "")
        actual_base = self.apply_placeholders(base_path, self.placeholders)
        dst_notes = os.path.join(actual_base, "notes.txt")
        lines = [
            f"{shot}_roto01",
            "",
            artist_notes,
        ]
        content = "\n".join(lines).rstrip() + "\n"
        os.makedirs(os.path.dirname(dst_notes), exist_ok=True)
        try:
            with open(dst_notes, "w") as f:
                f.write(content)
            print(f"[notes_create] ✅ wrote notes → {dst_notes}")
        except Exception as e:
            print(f"[notes_create] failed writing notes: {e}")

    def on_plate_changed(self):
        plate_ = self.render_ui.plate_name.currentText()
        plate_name_value_ = self.render_ui.user_plate_name.text()
        self.source_path = plate_
        self.apply_placeholders(self.placeholders["source_path"], self.placeholders)
        self.placeholders["plate_name"] = plate_name_value_
        self.placeholders["sg_plate_name"] = plate_name_value_
        if self.placeholders.get("user_input_plate"):
            self.placeholders["user_input_plate"] = plate_name_value_
        if self.placeholders.get("sg_register_plate_name"):
            self.placeholders["sg_plate_name"] = self.apply_placeholders(
                self.placeholders.get("sg_register_plate_name", {}),
                self.placeholders,  # noqa
            )
            self.placeholders["plate_name"] = self.apply_placeholders(
                self.placeholders.get("sg_register_plate_name", {}),
                self.placeholders,  # noqa
            )

        self.get_department_structure()
        print("mb_nuke_path_______", self.mb_nuke_path)
        print("source_path__________________", self.source_path)

    def set_current_date(self):
        today = _dt.datetime.now().strftime("%Y%m%d")
        self.placeholders["date_folder"] = "BFS_{}_01".format(today)
        self.placeholders["date_folder_client"] = _dt.datetime.now().strftime("%d%m%y")

    def on_knob_change(self):
        # Get values from UI
        source_label_name = self.render_ui.plate_name.currentText()
        plate_name_value = self.render_ui.user_plate_name.text()

        # Update placeholders with user input
        # self.placeholders["source_path"] = source_label_name
        self.placeholders["sg_plate_name"] = plate_name_value
        self.placeholders["plate_name"] = plate_name_value
        if self.placeholders.get("user_input_plate"):
            self.placeholders["user_input_plate"] = plate_name_value

        if self.placeholders.get("sg_register_plate_name"):
            self.placeholders["sg_plate_name"] = self.apply_placeholders(
                self.placeholders.get("sg_register_plate_name", {}),
                self.placeholders,  # noqa
            )
            self.placeholders["plate_name"] = self.apply_placeholders(
                self.placeholders.get("sg_register_plate_name", {}),
                self.placeholders,  # noqa
            )

        # self.set_current_date()
        variables = {
            "shot": self.shot_name.lower(),
            "client": self.client_name.lower(),
            "show": self.show_name.lower(),
            "department": self.department_name.lower(),
            "input_path": self.input_path,
        }
        main_out_path = eval(self.yaml_data.get("roto_main_out"), {"os": os}, variables)
        self.out_version = self.get_latest_version(
            os.path.join(main_out_path, self.placeholders["sg_plate_name"])
        )
        self.placeholders["out_version"] = self.out_version

        if (
            self.placeholders.get("default_out_verison")
            and self.yaml_data.get("default_version_padding") is not None
        ):
            self.out_version
            # default_version_padding
            self.default_out_version = "v" + str(int(self.out_version[1:])).zfill(
                int(self.yaml_data.get("default_version_padding"))
            )
            self.placeholders["default_out_verison"] = self.default_out_version

        print("dndfdf", self.out_version)
        self.render_ui.versionDropdown.setText(self.out_version)

        # Process the change
        self.get_department_structure()
        print("mb_nuke_path_______", self.mb_nuke_path)

        print(os.path.join(main_out_path, self.placeholders["sg_plate_name"]))

    def on_enter_pressed(self):
        # Get values from UI
        source_label_name = self.render_ui.plate_name.currentText()
        plate_name_value = self.render_ui.user_plate_name.text()

        # Update placeholders with user input
        # self.placeholders["source_path"] = source_label_name
        self.placeholders["sg_plate_name"] = plate_name_value
        self.placeholders["plate_name"] = plate_name_value
        if self.placeholders.get("user_input_plate"):
            self.placeholders["user_input_plate"] = plate_name_value

        if self.placeholders.get("sg_register_plate_name"):
            self.placeholders["sg_plate_name"] = self.apply_placeholders(
                self.placeholders.get("sg_register_plate_name", {}),
                self.placeholders,  # noqa
            )
            self.placeholders["plate_name"] = self.apply_placeholders(
                self.placeholders.get("sg_register_plate_name", {}),
                self.placeholders,  # noqa
            )

        variables = {
            "shot": self.shot_name.lower(),
            "client": self.client_name.lower(),
            "show": self.show_name.lower(),
            "department": self.department_name.lower(),
            "input_path": self.input_path,
        }
        main_out_path = eval(self.yaml_data.get("roto_main_out"), {"os": os}, variables)
        self.out_version = self.get_latest_version(
            os.path.join(main_out_path, self.placeholders["sg_plate_name"])
        )
        self.placeholders["out_version"] = self.out_version
        print("dndfdf", self.out_version)
        self.render_ui.versionDropdown.setText(self.out_version)

        # Process the change
        self.get_department_structure()
        print("mb_nuke_path_______", self.mb_nuke_path)

        print(os.path.join(main_out_path, self.placeholders["sg_plate_name"]))

    # def on_plate_changed(self):
    #     if self.render_ui.plate_name.currentText() == "None":
    #         self.placeholders["sg_plate_name"] = ""

    #         self.get_department_structure()
    #         # self.update_placeholders()

    #     else:
    #         source_label_name = self.render_ui.plate_name.currentText()
    #         self.placeholders["source_path"] = source_label_name
    #         plate_name_value = self.placeholders["plate_name"]
    #         self.placeholders["sg_plate_name"] = plate_name_value + "_"
    #         self.get_department_structure()
    #         # self.process_paths()
    #         # self.update_placeholders()

    def show_dialog(self, message):
        """
        Displays a warning dialog with a specified message.

        This method creates and shows a modal warning dialog to the user, displaying
        the provided message. The dialog will have an "Ok" button to close it.

        Args:
            message (str): The message to display in the dialog.

        Returns:
            None
        """
        msg_box = QtWidgets.QMessageBox()
        msg_box.setIcon(QtWidgets.QMessageBox.Warning)
        msg_box.setText(message)
        msg_box.setWindowTitle("Warning")
        msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msg_box.exec_()

    def get_tmp_path(self):
        tmp_path = os.environ["HOME"] + "/tmp/roto_packaging/"

        if not os.path.exists(tmp_path):
            os.makedirs(tmp_path)
        return tmp_path

    def read_yaml(self):
        """
        Reads the YAML configuration file for the current project.

        This method constructs the path to the YAML configuration file based on the
        project name. It attempts to read the file and load its content using the
        YAML library. If successful, it returns the parsed YAML data. If the file
        is not found or if any error occurs during reading, it logs the error
        and returns an empty dictionary.

        Returns:
            dict: The parsed YAML data or an empty dictionary if an error occurs.
        """
        project = fx.activeProject().path
        p = os.path.dirname(project)
        tk = sgtk.sgtk_from_path(p)
        context = tk.context_from_path(p)
        print("context : ", context)
        self.project_name = context.project["name"]
        self.client_name = (self.project_name.split("_")[0]).lower()
        project_config = self.client_name + "_config"
        if os.getlogin() == "chandru":
            yaml_path = "/home/chandru/Documents/development/roto_packager_config/config/{}.yaml".format(
                project_config
            )
        else:
            yaml_path = "/tools/silhouette_tools/2021.5/my_task/package_creation/packaging_config/{}.yaml".format(
                project_config
            )
        try:
            with open(yaml_path, "r") as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            print(f"YAML file not found: {yaml_path}")
        except Exception as e:
            print(f"Error reading YAML file: {e}")
        return {}

    def get_context(self):
        project = fx.activeProject().path
        tk = sgtk.sgtk_from_path(str(project))
        context = tk.context_from_path(project)
        project_name = context.project["name"]
        shot_id = context.entity["id"]
        return project_name, shot_id

    def get_all_plate_versions(self, project_name, shot_id):
        filters = [
            ["project.Project.name", "is", project_name],
            ["entity", "is", {"type": "Shot", "id": int(shot_id)}],
            ["sg_task.Task.content", "is", "Plate_Proxy"],
            ["sg_path_to_frames", "is_not", None],
        ]
        fields = ["sg_path_to_frames"]
        sgVersions = SG.find(
            "Version",
            filters,
            fields,
        )

        return sorted(sgVersions, key=lambda k: k["id"]) or []

    def _get_show_structure(self, client_structure):
        """
        Look up show_name in client_structure.
        Falls back to the 'default' entry if show_name is not present.
        Returns None if neither exists.
        """
        show_structure = next(
            (
                item[self.show_name]
                for item in client_structure
                if self.show_name in item
            ),
            None,
        )
        if show_structure is None:
            show_structure = next(
                (item["default"] for item in client_structure if "default" in item),
                None,
            )
            if show_structure is not None:
                print(
                    f"[_get_show_structure] show '{self.show_name}' not found — "
                    f"using 'default' structure"
                )
            else:
                print(
                    f"[_get_show_structure] show '{self.show_name}' not found and "
                    f"no 'default' entry exists in client structure"
                )
        return show_structure

    def check_version_pentec(self):
        project = fx.activeProject().path
        data = fx.activeProject()
        p = os.path.dirname(project)
        tk = sgtk.sgtk_from_path(p)
        context = tk.context_from_path(p)
        version_fields = ["code", "image", "sg_task.Task.sg_plate_path", "id"]
        filters = [
            ["entity.Shot.id", "is", int(context.entity["id"])],
            ["sg_status_list", "is", "pentec"],
        ]

        versions = self.sg.find("Version", filters, version_fields)
        if not versions:
            print("Versions Filters: ", filters)
            # Show error message box in Foundry
            self.show_dialog("Version Error: Your version is not approved")
            return False
        return True

    def get_reviewers_list(self):
        task_filters = [["id", "is", int(self.task_id)]]
        self.task = self.sg.find_one("Task", task_filters, ["step", "sg_plate_path"])
        dept = (self.task["step"]["name"]).lower() if self.task["step"] else None
        dept = dept.lower()

        filters = [
            {
                "filter_operator": "any",
                "filters": [
                    ["permission_rule_set", "name_is", "Lead"],
                    ["permission_rule_set", "name_is", "Lead - Artist"],
                    ["permission_rule_set", "name_is", "Supervisor"],
                    ["permission_rule_set", "name_is", "Supervisor - Production"],
                ],
            },
            ["sg_status_list", "is", "act"],
        ]
        fields = ["name", "lastname", "groups", "email"]
        people = self.sg.find("HumanUser", filters, fields)
        reviewers = []
        reviewers.insert(0, "")
        for person in people:
            name = person.get("name", "Unnamed")
            lastname = person.get("lastname", "Unnamed")
            email = person.get("email", "No Email")
            if len(person.get("groups")) != 0:
                groups = person.get("groups")[0]["name"]
            else:
                groups = None
            if dept in lastname.lower():
                reviewers.append(name)

        print("reviewers", reviewers)
        return reviewers

    def sg_connection(self):
        """
        Establishes a connection to the Shotgun API.

        This method creates and returns a connection to the Shotgun server using
        the user's credentials.

        Returns:
            Shotgun: An instance of the Shotgun connection.
        """
        return self.sg_user.create_sg_connection()

    def get_sg_proxy(self, file_path):
        sg_proxy = None
        with open(file_path, "r") as file:
            for line in file:
                line = line.strip()
                if line.startswith("SG_PROXY:"):
                    sg_proxy = line.split(":", 1)[1].strip()
                    break
        return sg_proxy

    def set_sgtk_auth(self):
        """
        Authenticates the user for Shotgun Toolkit.

        This method retrieves the current user through the ShotgunAuthenticator
        and sets the authenticated user in the Shotgun Toolkit context.

        Returns:
            dict: The authenticated user information.
        """
        if "B_SHOW" in os.environ:
            file_path = "/tools/site_config.yml"
            proxy_ip = self.get_sg_proxy(file_path)
            sa = sgtk.authentication.ShotgunAuthenticator()
            user = sa.create_script_user(
                api_script="silhouette_my_task",
                api_key="cllnjxceqgaa7~pafXthdlaxm",
                host="https://basilic.shotgrid.autodesk.com",
                http_proxy=proxy_ip,
            )
            print("_________________", user)
            sgtk.set_authenticated_user(user)

        else:
            authenticator = ShotgunAuthenticator()
            user = authenticator.get_user()
            sgtk.set_authenticated_user(user)

        return user

    def set_show(self):
        """
        Retrieves the current project from the Shotgun server based on the environment variable 'TANK_CURRENT_PC'.

        This method extracts the show name from the 'TANK_CURRENT_PC' environment variable, searches for the
        corresponding project in Shotgun, and returns the project's Shotgun data.

        Returns:
            dict: The Shotgun data for the project if found, otherwise None.

        Raises:
            KeyError: If the 'TANK_CURRENT_PC' environment variable is not set.
            AttributeError: If the environment variable does not match the expected pattern.
        """

        get_env = os.getenv("TANK_CURRENT_PC")
        show_name = re.search(r"[^/]+$", get_env)[0]
        if show_name is None:
            # self.show_error_message("Show is Not configured")
            return

        show_sg = self.sg.find_one("Project", [["name", "is", show_name]], ["name"])
        return show_sg

    def get_username(self):
        """
        Retrieves the Shotgun user data for the current user.

        This method uses the current user's name to search for the corresponding user in Shotgun
        and returns the user's Shotgun data, including the username and department.

        Returns:
            dict: The Shotgun data for the user if found, otherwise None.

        Raises:
            KeyError: If the 'current_user' attribute is not set.
        """
        user_name = self.current_user
        print(user_name)
        user_sg = self.sg.find_one(
            "HumanUser",
            [["sg_username", "is", user_name]],
            ["sg_username", "department"],
        )
        if user_sg is None:
            self.show_error_message("Please check the user name in Shotgrid")
            return
        return user_sg

    def get_project_notes(self):
        project = fx.activeProject()
        note_str = project.note  # this is a string
        note_dict = json.loads(note_str)  # now it's a dictionary

        return note_dict["task_id"]

    def initialize_data(self):
        """
        Initializes project-related data for the current context.

        This method retrieves information about the project, shot, and versions
        associated with the current context in Nuke. It updates various class
        attributes such as project name, shot name, approved versions, sequence name,
        department name, client name, and show name. It also calls the method to
        update placeholders based on this data.

        Returns:
            None
        """

        self.project = self.set_show()
        project = fx.activeProject().path
        for i in fx.activeProject().sources:
            source_file_name = i.properties["path"].getValue()
            frame_range_match = re.search(r"\[(\d+)-(\d+)\]", source_file_name)
            if frame_range_match:
                digit_count = len(frame_range_match.group(2))
                formatted_path = re.sub(
                    r"\[\d+-\d+\]", f"%0{digit_count}d", source_file_name
                )
                self.full_source_path = formatted_path
                self.source_path = os.path.basename(formatted_path)

        data = fx.activeProject()
        p = os.path.dirname(project)
        self.input_path = p
        tk = sgtk.sgtk_from_path(p)
        context = tk.context_from_path(p)
        # self.department_name = "roto"
        print("context : ", dir(context))
        print(context.to_dict)
        sg_task = SG.find_one(
            "Task",
            [
                ["entity.Shot.id", "is", context.entity["id"]],
                ["step.Step.id", "is", context.step["id"]],
                [
                    "task_assignees",
                    "is",
                    {"type": "HumanUser", "id": self.user_name["id"]},
                ],
            ],
            [],
        )
        try:
            self.task_id = int(self.get_project_notes())
        except json.decoder.JSONDecodeError:
            self.task_id = int(sg_task["id"])

        print("+++____________EEEEEEEEERTASk", self.task_id)
        SG.change_context("Task", self.task_id)

        filters = [
            ["project", "is", {"type": "Project", "id": self.project["id"]}],
            [
                "tasks.Task.task_assignees",
                "is",
                {"type": "HumanUser", "id": self.user_name["id"]},
            ],
        ]

        fields = ["code", "sg_status_list", "project"]
        self.shots_data = self.sg.find("Shot", filters, fields)

        self.project_name = context.project["name"]
        self.client_name = self.project_name.split("_")[0]
        self.show_name = "_".join(self.project_name.split("_")[1:])

        shot = context.entity
        self.shot_name = shot["name"]

        shot_data = self.sg.find_one(
            "Shot", [["id", "is", context.entity["id"]]], ["sg_sequence"]
        )
        # seq = shot_data["sg_sequence"]["name"]

        self.department_name = (context.step["name"]).lower()
        print(self.department_name)
        self.department_name = "roto"

        # print("task",task)
        versions = None

        if self.project_name and self.shot_name:
            versions = self.sg.find(
                "Version",
                [
                    ["project.Project.name", "is", self.project_name],
                    ["entity.Shot.code", "is", self.shot_name],
                    ["sg_status_list", "is", "pentec"],
                    #  ["sg_task.Task.step.Step.code", "is", "Roto"]
                ],
                [
                    "code",
                    "image",
                    "created_by",
                    "description",
                    "sg_version_type",
                    "sg_status_list",
                    "sg_path_to_frames",
                    "sg_task.Task.sg_plate_path",
                    "sg_task.Task.content",
                    "entity.Shot.code",
                    "project.Project.name",
                ],
            )

        if not versions:
            return
        self.overlay_render_files = []
        self.update_placeholders()
        print(self.fetch_structure())

    def get_jpeg_files_from_proxy_folder(self, base_directory):
        for root, dirs, files in os.walk(base_directory):
            if os.path.basename(root) == "proxy":
                for file in files:
                    if file.lower().endswith((".jpg", ".jpeg")):
                        return os.path.join(root, file)
        return None

    def download_image(self, url, version_id):
        if url is None:
            return None

        path = f"/home/{str(os.getlogin())}/nuke_cache/"
        if not os.path.exists(path):
            os.makedirs(path)

        file_path = f"/home/{str(os.getlogin())}/nuke_cache/thumbnail_{version_id}.jpeg"

        if os.path.exists(file_path):
            return file_path
        try:
            urllib.request.urlretrieve(url, file_path)
            print(f"Image successfully downloaded to {file_path}")
            return file_path
        except Exception as e:
            print(f"Failed to download image: {e}")
            return None

    def update_placeholders(self):
        self.placeholders = {
            "shot": self.shot_name.lower(),
            "client": self.client_name.lower(),
            "show": self.show_name.lower(),
            "department": self.department_name.lower(),
            "input_path": self.input_path,
            "source_path": self.source_path,
            "sg_plate_name": self.sg_plate_name,
            "user_name": os.getlogin().replace(".", "-"),
        }
        self.set_current_date()  # <-- seed date_folder so the token can split it

    def _build_nmb_additional_paths(self):
        """
        Build NMB write paths keyed by description, for merging into additional_value
        sent to roto_coloroverlay_processor. Token-driven (nmb_project_base_path or
        fallback to out_path+project_base_path), same resolution logic as
        render_nmb_token_driven. Returns {} if nmb descriptions haven't been resolved
        yet — safe no-op.
        """
        descriptions = getattr(self, "nmb_descriptions", None) or []
        if not descriptions:
            return {}

        if "nmb_project_base_path" in self.placeholders:
            base_path = self.placeholders["nmb_project_base_path"]
        else:
            base_path = self.out_path + self.placeholders.get("project_base_path", "")
        actual_base = self.apply_placeholders(base_path, self.placeholders)

        matte_extend = self.placeholders.get(
            "nmb_extend_path",
            self.placeholders.get("matte_extend_path", ["matte_renders_exr"]),
        )
        matte_naming_convention = self.placeholders.get(
            "nmb_naming_convention", self.placeholders.get("matte_naming_convention")
        )

        nmb_paths = {}
        for description in descriptions:
            local_ph = dict(self.placeholders)
            local_ph["description"] = description
            expanded_segments = [
                self.apply_placeholders(seg, local_ph) for seg in matte_extend
            ]
            dst_folder = os.path.join(actual_base, *expanded_segments)

            if matte_naming_convention:
                file_name = (
                    self.apply_placeholders(matte_naming_convention, local_ph)
                    + ".%04d.exr"
                )
            else:
                file_name = f"{description}.%04d.exr"

            nmb_paths[description] = os.path.join(dst_folder, file_name)

        return nmb_paths

    def call_back(self):
        self.render_ui.setWindowModality(Qt.ApplicationModal)
        self.render_ui.raise_()
        self.render_ui.activateWindow()
        self.render_ui.show()
        self.render_ui.showNameInput.setText(self.project_name)
        self.render_ui.directoryPathInput.setText(self.out_path)
        self.render_ui.shotNameInput.setText(self.shot_name)
        self.render_ui.versionDropdown.setText(self.out_version)

    def get_latest_version(self, out_path):
        if not out_path:
            return None

        padding = self.yaml_data.get("version_padding", 3)

        if not os.path.exists(out_path):
            return f"v{'1':0>{padding}}"  # v001 or v0001

        version_pattern = re.compile(r"v(\d+)")
        max_version_number = None
        max_length = 0

        for folder_name in os.listdir(out_path):
            folder_path = os.path.join(out_path, folder_name)
            if os.path.isdir(folder_path):
                versions = version_pattern.findall(folder_name)
                if versions:
                    last_version = versions[-1]
                    version_number = int(last_version)
                    if (
                        max_version_number is None
                        or version_number > max_version_number
                    ):
                        max_version_number = version_number
                        max_length = len(last_version)

        if max_version_number is None:
            return f"v{'1':0>{padding}}"  # ✅ use yaml padding

        next_version = f"v{max_version_number + 1:0{max_length}}"
        return next_version

    def create_zip(self, **args):
        """
        Zips the shot delivery folder after all render tasks complete.
        Reads zip_source_folder and zip_full_path from self.placeholders.
        """
        import zipfile

        # ── Resolve template strings ──────────────────────────────────────────
        zip_src_tpl = self.placeholders.get("zip_source_folder", "")
        zip_dst_tpl = self.placeholders.get("zip_full_path", "")

        if not zip_src_tpl or not zip_dst_tpl:
            print("[create_zip] zip_source_folder or zip_full_path not set in token")
            return

        zip_src = self.out_path + self.replace_placeholders(
            zip_src_tpl, self.placeholders
        )
        zip_dst = self.out_path + self.replace_placeholders(
            zip_dst_tpl, self.placeholders
        )

        if not os.path.isdir(zip_src):
            print(f"[create_zip] source folder does not exist: {zip_src}")
            return

        # ── Remove stale archive ──────────────────────────────────────────────
        if os.path.exists(zip_dst):
            os.remove(zip_dst)
            print(f"[create_zip] removed old zip: {zip_dst}")

        os.makedirs(os.path.dirname(zip_dst), exist_ok=True)

        # ── Build archive ─────────────────────────────────────────────────────
        file_count = 0
        with zipfile.ZipFile(zip_dst, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(zip_src):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for fname in files:
                    full_path = os.path.join(root, fname)
                    archive_name = os.path.relpath(full_path, os.path.dirname(zip_src))
                    zf.write(full_path, archive_name)
                    file_count += 1

        size_mb = os.path.getsize(zip_dst) / (1024 * 1024)
        print(f"[create_zip] ✓ {file_count} files, {size_mb:.1f} MB → {zip_dst}")
        return zip_dst

    def get_transform_data(self):
        variables = {
            "shot": self.shot_name.lower(),
            "client": self.client_name.lower(),
            "show": self.show_name.lower(),
            "department": self.department_name.lower(),
            "input_path": self.input_path,
        }

        try:
            self.out_path = eval(
                self.yaml_data.get("roto_out_path"), {"os": os}, variables
            )

            main_out_path = eval(
                self.yaml_data.get("roto_main_out"), {"os": os}, variables
            )
            print("test", self.out_path)
            self.out_version = self.get_latest_version(
                os.path.join(main_out_path, self.placeholders["sg_plate_name"])
            )
            self.placeholders["out_version"] = self.out_version
            self.render_ui.versionDropdown.setText(self.out_version)
            print("################", self.out_version)
        except Exception as e:
            print("errrrrrrrrrrrorrrr", e)

        print("self.out_path", self.out_path)
        print("self.out_version", self.out_version)

        transforms = self.yaml_data.get("tokens", {})
        show_department = f"{self.show_name}_{self.department_name}"
        transform_data = transforms.get(show_department, {})
        if not transform_data:
            default_key = f"default_{self.department_name}"
            transform_data = transforms.get(default_key, {})
            if transform_data:
                print(
                    f"[get_transform_data] No tokens for '{show_department}' — "
                    f"using '{default_key}'"
                )
            else:
                print(
                    f"[get_transform_data] No tokens for '{show_department}' "
                    f"and no '{default_key}' fallback found"
                )

        controlled_env = {
            "os": os,
            "out_path": self.out_path,
            "out_version": self.out_version,
            "input_path": self.input_path,
            "replace_placeholders": self.replace_placeholders,
        }

        for key, expression in transform_data.items():
            try:
                if isinstance(expression, str) and expression.startswith("$d("):
                    date_format = re.search(r"\$d\((.*?)\)", expression).group(1)
                    computed_value = datetime.datetime.now().strftime(date_format)
                else:
                    computed_value = self.execute_code(
                        expression, {**controlled_env, **self.placeholders}
                    )
                self.placeholders[key] = computed_value
                controlled_env[key] = computed_value
            except Exception as e:
                print(f"Error computing value for {key}: {e}")

        self.placeholders["render"] = self.apply_placeholders(
            self.placeholders.get("render", {}), self.placeholders
        )
        return self.placeholders

    def execute_code(self, expression, env):
        local_env = {}
        try:
            exec(f"result = {expression}", env, local_env)
            return local_env.get("result", expression)
        except Exception:
            return expression

    def get_active_session_work_range(self):
        """
        getting strat and end frame
        """
        project_object = fx.activeProject()
        session_obj = project_object.activeSession
        return map(int, session_obj.workRange)

    def extract_specific_structure(self, data):
        result = {}
        for outer_dict in data:
            for out_version, shots_list in outer_dict.items():
                result[out_version] = {}
                for shot_item in shots_list:
                    if isinstance(shot_item, dict):
                        for shot, contents in shot_item.items():
                            # Find difference overlay entries
                            difference_overlays = [
                                key for key in contents if "differenceoverlay" in key
                            ]
                            if difference_overlays:
                                result[out_version][shot] = difference_overlays
        return result

    def get_naming_convention(self):
        show_name = os.environ["B_SHOW"]
        if os.getlogin() == "chandru":
            template_path = (
                "/home/chandru/Documents/development/roto_packager_config/config/"
                + show_name.split("_")[0]
                + "_config.yaml"
            )
        else:
            template_path = (
                "/tools/silhouette_tools/2021.5/my_task/package_creation/packaging_config/"
                + show_name.split("_")[0]
                + "_config.yaml"
            )
        with open(template_path, "r") as file:
            data = yaml.safe_load(file)
        coloroverlay_value = data["naming_convention"][show_name][self.department_name][
            "coloroverlay"
        ]
        return coloroverlay_value

    def fetch_data_structure(self):
        print(self.placeholders)
        self.placeholders["extension"] = "exr"
        start_frame, end_frame = self.get_active_session_work_range()
        full_frame = str(start_frame) + "-" + str(end_frame)
        self.placeholders["frame_range"] = full_frame
        # color_overlay_path = self.placeholders["exr_path"]
        # self.apply_placeholders(color_overlay_path,self.placeholders)
        color_overlay_path = self.out_path + self.apply_placeholders(
            self.placeholders["exr_path"], self.placeholders
        )
        # dst_path = os.path.dirname(os.path.dirname(color_overlay_path))
        # dst_path = project_base_path
        base_path = self.out_path + self.placeholders["project_base_path"]
        actual_path = self.apply_placeholders(base_path, self.placeholders)
        dst_path = os.path.dirname(actual_path)
        show_name = os.environ["B_SHOW"]
        sg_user_name = self.get_username()["sg_username"]
        reviewer_name = self.render_ui.reviewerinput.currentText()
        version_data = self.render_ui.version_description_error()
        print(
            "cg creation data : ",
            show_name,
            self.task_id,
            self.out_version[1:],
            color_overlay_path,
            dst_path,
            sg_user_name,
            "Package",
            reviewer_name,
            version_data,
        )
        command_file = create_packager_SG_version(
            show_name,
            self.task_id,
            self.out_version[1:],
            color_overlay_path,
            dst_path,
            sg_user_name,
            "Package",
            reviewer_name,
            version_data,
        )
        self.submit_py_deadline(command_file, self.job_id)

    def replace_frame_range_with_padding(self, filename):
        # Pattern to match [start-end]
        pattern = r"\[(\d+)-(\d+)\]"

        def replacer(match):
            end_frame = match.group(2)
            num_digits = len(end_frame)
            return f"%0{num_digits}d"

        return re.sub(pattern, replacer, filename)

    def select_plate_package(self, scene_list):
        project = fx.activeProject()
        print("Project:", project)
        for session in project.sessions:
            for node in session.nodes:
                if node.type == "SourceNode":
                    scene_file_name = self.replace_frame_range_with_padding(node.label)
                    if scene_file_name in scene_list:
                        return scene_file_name
                    else:
                        return None
        return None

    # def get_department_structure(self):
    #     self.render_ui.tree.clear()

    #     # ✅ Reset all render dicts so re-run starts clean
    #     self.render_folder_dict = {}
    #     self.render_path_dict = {}
    #     self.mb_folder_path = []
    #     self.mb_nuke_path = {}
    #     self.nmb_nuke_path = {}
    #     self.nmb_actual_path = {}
    #     self.matte_shape_bkp = {}

    #     # ✅ Always pull fresh from YAML - never from already processed structure
    #     project_structure = self.yaml_data.get("project_structure", [])
    #     client_structure = next(
    #         (
    #             item[self.client_name]
    #             for item in project_structure
    #             if self.client_name in item
    #         ),
    #         None,
    #     )
    #     show_structure = next(
    #         (
    #             item[self.show_name]
    #             for item in client_structure
    #             if self.show_name in item
    #         ),
    #         None,
    #     )
    #     department_structure = next(
    #         (
    #             item[self.department_name]
    #             for item in show_structure
    #             if self.department_name in item
    #         ),
    #         None,
    #     )

    #     self.applied_folder_structure = self.apply_placeholders(
    #         department_structure, self.placeholders
    #     )
    #     department_structure = self.get_description(self.applied_folder_structure)
    #     self.applied_folder_structure = self.apply_placeholders(
    #         department_structure, self.placeholders
    #     )
    #     self.populate_tree_widget(self.applied_folder_structure)

    def get_department_structure(self):
        self.render_ui.tree.clear()

        # ✅ Reset all render dicts
        self.render_folder_dict = {}
        self.render_path_dict = {}
        self.mb_folder_path = []
        self.mb_nuke_path = {}
        self.nmb_nuke_path = {}
        self.nmb_actual_path = {}
        self.matte_shape_bkp = {}

        project_structure = self.yaml_data.get("project_structure", [])
        client_structure = next(
            (
                item[self.client_name]
                for item in project_structure
                if self.client_name in item
            ),
            None,
        )
        # show_structure = next(
        #     (
        #         item[self.show_name]
        #         for item in client_structure
        #         if self.show_name in item
        #     ),
        #     None,
        # )

        show_structure = self._get_show_structure(client_structure)
        department_structure = next(
            (
                item[self.department_name]
                for item in show_structure
                if self.department_name in item
            ),
            None,
        )

        # needs_description_expand = not self.placeholders.get(
        #     "mb_folder_template", ""
        # ).strip()
        needs_description_expand = "{description}" in str(department_structure)

        if needs_description_expand:
            # ✅ get_description on RAW yaml structure BEFORE apply_placeholders
            department_structure = self.get_description(department_structure)
            self.applied_folder_structure = self.apply_placeholders(
                department_structure, self.placeholders
            )
        else:
            department_structure = self.get_description(
                department_structure
            )  # expand FIRST on raw
            self.applied_folder_structure = self.apply_placeholders(
                department_structure, self.placeholders
            )

        self.populate_tree_widget(self.applied_folder_structure)

    def fetch_structure(self):
        self.get_transform_data()
        project_structure = self.yaml_data.get("project_structure", [])
        client_structure = next(
            (
                item[self.client_name]
                for item in project_structure
                if self.client_name in item
            ),
            None,
        )
        print(client_structure)
        if client_structure:
            show_structure = self._get_show_structure(client_structure)
            print(show_structure)
            if show_structure:
                department_structure = next(
                    (
                        item[self.department_name]
                        for item in show_structure
                        if self.department_name in item
                    ),
                    None,
                )
                print(department_structure)
                if department_structure:
                    self.render_ui.versionDropdown.setText(self.out_version)
                    self.render_ui.directoryPathInput.setText(self.out_path)
                    start_frame, end_frame = self.get_active_session_work_range()
                    self.render_ui.startFrameInput.setText(str(start_frame))
                    self.render_ui.endFrameInput.setText(str(end_frame))
                    reviewer_list = self.get_reviewers_list()
                    self.render_ui.reviewerinput.addItems(reviewer_list)
                    project_name, shot_id = self.get_context()
                    sg_version = self.get_all_plate_versions(project_name, shot_id)
                    print("_____sg_version", sg_version)
                    sg_master_plate = []
                    self.render_ui.plate_name.addItem("None", None)
                    for i in sg_version:
                        sg_master_plate.append(
                            os.path.basename(str(i["sg_path_to_frames"]))
                        )
                        self.render_ui.plate_name.addItem(
                            os.path.basename(str(i["sg_path_to_frames"])),
                            i["sg_path_to_frames"],
                        )

                    source_label_name = self.select_plate_package(sg_master_plate)
                    if source_label_name == None:
                        print("plate_name is None")
                    else:
                        self.render_ui.plate_name.setCurrentText(source_label_name)
                        self.placeholders["source_path"] = source_label_name
                        if os.getlogin() == "chandru":
                            self.placeholders["plate_name"] = "test"
                        plate_name_value = self.placeholders.get("plate_name")
                        self.placeholders["sg_plate_name"] = plate_name_value
                        if self.placeholders.get("user_input_plate"):
                            self.placeholders["user_input_plate"] = plate_name_value

                        if self.placeholders.get("sg_register_plate_name"):
                            self.placeholders["sg_plate_name"] = (
                                self.apply_placeholders(
                                    self.placeholders.get("sg_register_plate_name", {}),
                                    self.placeholders,  # noqa
                                )
                            )
                            self.placeholders["plate_name"] = self.apply_placeholders(
                                self.placeholders.get("sg_register_plate_name", {}),
                                self.placeholders,  # noqa
                            )
                        if plate_name_value is not None:
                            plate_name_value = "mp01"

                        self.render_ui.user_plate_name.setText(plate_name_value)

                    self.render_ui.tree.clear()
                    yaml_data = self.placeholders.get("nuke_template_context_data", {})
                    print(yaml_data)
                    self.get_roto_node_count()
                    invalid_layers = self.validate_layer_names()
                    if invalid_layers:
                        self.show_dialog(
                            "Layer name(s) contain spaces — rename before packaging:\n\n"
                            + "\n".join(f"  • {name}" for name in invalid_layers)
                        )
                        return

                    self.input_dialog = DynamicDialog(yaml_data, self.roto_node_count)
                    if self.input_dialog.exec_():
                        self.template_input_data = self.input_dialog.result_data
                        print(
                            "###########  test ###############",
                            self.template_input_data,
                        )
                        self.template_input_data["NMB_matte_path"] = (
                            self.template_input_data["MB_matte_path"]
                        )
                        print(self.placeholders)

                    # ✅ Reset all render dicts before rebuilding structure
                    self.render_folder_dict = {}
                    self.render_path_dict = {}
                    self.mb_folder_path = []
                    self.mb_nuke_path = {}
                    self.nmb_nuke_path = {}
                    self.nmb_actual_path = {}
                    self.matte_shape_bkp = {}

                    # ✅ Always use fresh department_structure from YAML (already fetched above)
                    print(department_structure)
                    self.applied_folder_structure = self.apply_placeholders(
                        department_structure, self.placeholders
                    )
                    department_structure = self.get_description(
                        self.applied_folder_structure
                    )
                    self.applied_folder_structure = self.apply_placeholders(
                        department_structure, self.placeholders
                    )
                    self.populate_tree_widget(self.applied_folder_structure)

                    try:
                        self.render_ui.publishButton.clicked.disconnect()
                    except RuntimeError:
                        pass  # no existing connection, ignore

                    self.render_ui.publishButton.clicked.connect(
                        lambda: self.create_folder_structure(
                            self.applied_folder_structure, self.placeholders
                        )
                    )

    def validate_layer_names(self):
        session = fx.activeSession()
        roto_nodes = session.getNodes("RotoNode")
        invalid_layers = []
        for roto_node in roto_nodes:
            for layer_main in roto_node.children:
                if " " in layer_main.label:
                    invalid_layers.append(layer_main.label)
        return invalid_layers

    def get_roto_node_count(self):
        project = fx.activeProject()
        print("Project:", project)
        self.roto_node_count = 0
        for session in project.sessions:
            for node in session.nodes:
                if node.type == "RotoNode":
                    print("Found a RotoNode:", node)
                    self.roto_node_count += 1

    def open_input_template_dialog(self):
        print("run__________________")
        print("_____+++++++_+++", self.template_input_data)
        if not self.template_input_data:
            yaml_data = self.placeholders.get("nuke_template_context_data", {})
            self.input_dialog = DynamicDialog(yaml_data, self.roto_node_count)
        else:
            self.input_dialog = DynamicDialog(self.template_input_data)

        if self.input_dialog.exec_():
            self.template_input_data = self.input_dialog.result_data

    def apply_placeholders(self, structure, placeholders):
        """
        Recursively applies placeholders to a given structure.

        This method processes a structure (which can be a list, dictionary, or string)
        and replaces any placeholders with their corresponding values from the provided
        dictionary. It returns the modified structure.

        Args:
            structure (list | dict | str): The structure containing placeholders.
            placeholders (dict): A dictionary mapping placeholder names to their values.

        Returns:
            The structure with placeholders replaced by their corresponding values.
        """
        print("structure__________________________", structure)
        if isinstance(structure, list):
            return [self.apply_placeholders(item, placeholders) for item in structure]
        elif isinstance(structure, dict):
            return {
                self.apply_placeholders(key, placeholders): self.apply_placeholders(
                    value, placeholders
                )
                for key, value in structure.items()
            }
        elif isinstance(structure, str):
            try:
                return structure.format(**placeholders)
            except KeyError as e:
                print("Missing placeholder:", e, "in string:", structure)
                return structure

    def shape_layer_wise_render(self, **args):
        if self.render_ui.shape_checkbox.isChecked():
            first = int(self.render_ui.startFrameInput.text())
            last = int(self.render_ui.endFrameInput.text())

            user_name = os.getlogin()

            # Get everything up to /dept/ from self.out_path
            base_dept_path = self.out_path.split("/dept/")[0] + "/dept/"

            # Final temp base path
            user_tmp_base = os.path.join(base_dept_path, "roto", user_name)

            tmp_path = os.path.join(user_tmp_base, ".tmp_layer_render")
            os.makedirs(tmp_path, exist_ok=True)
            try:
                os.chmod(tmp_path, 0o777)
            except:
                pass

            if not self.layer_dict:
                print("[shape_layer_wise_render] No layer_dict, skipping")
                return

            # Copy shape nk files to shared path for farm access
            shared_shapes_dir = os.path.join(tmp_path, "roto_shapes")
            os.makedirs(shared_shapes_dir, exist_ok=True)

            shared_layer_dict = {}
            for final_path, shape_list in self.layer_dict.items():
                shared_shapes = []
                for shape in shape_list:
                    local_nk = shape["path"]
                    nk_name = os.path.basename(local_nk)
                    shared_nk = os.path.join(shared_shapes_dir, nk_name)
                    shutil.copy2(local_nk, shared_nk)
                    os.chmod(shared_nk, 0o777)
                    print(
                        "[shape_layer_wise_render] copied {} -> {}".format(
                            local_nk, shared_nk
                        )
                    )
                    shared_shapes.append(
                        {
                            "path": shared_nk,
                            "channel": shape["channel"],
                        }
                    )
                shared_layer_dict[final_path] = shared_shapes

            nuke_path = self.yaml_data.get(
                "nuke_version_path", "/apps/nuke/Nuke15.0v4/Nuke15.0"
            )
            nuke_home = os.path.dirname(nuke_path)

            # import here — no nuke dependency at module level
            sys.path.append("/tools/silhouette_tools/2021.5/my_task/package_creation/")
            from layer_wise_render.main import render_layer_wise

            # this just writes .sh and .py scripts — no nuke needed
            deadline_sh_scripts, packed_paths, channel_merge_paths = render_layer_wise(
                shared_layer_dict,
                first,
                last,
                tmp_path,
                nuke_path,
                nuke_home,
                self.full_source_path,
            )

            if not deadline_sh_scripts:
                print("[shape_layer_wise_render] No scripts generated")
                return
            matte_layer_dict = {}

            self.packed_layer_dict = {}
            for final_path, shape_list in shared_layer_dict.items():
                matte_shapes = []
                for shape in shape_list:
                    nk_path = shape["path"]
                    channel = shape["channel"]
                    merged_exr = channel_merge_paths.get(nk_path)
                    if merged_exr:
                        matte_shapes.append({"path": merged_exr, "channel": channel})
                    else:
                        print(
                            "[shape_layer_wise_render] WARNING no merged exr for {}".format(
                                nk_path
                            )
                        )
                self.packed_layer_dict[final_path] = matte_shapes
                print(
                    "[shape_layer_wise_render] packed_layer_dict[{}] = {}".format(
                        final_path, matte_shapes
                    )
                )

            print(
                "[shape_layer_wise_render] {} scripts ready".format(
                    len(deadline_sh_scripts)
                )
            )

            # submit each as CommandLine job
            submitted_job_ids = []
            for sh_path in deadline_sh_scripts:
                nk_name = os.path.basename(sh_path).replace("_run.sh", "")
                print("[shape_layer_wise_render] Submitting: {}".format(nk_name))
                try:
                    plugin_info = (
                        "Executable={sh_path}\n"
                        "Arguments=<STARTFRAME> <ENDFRAME>\n"
                        "Shell=default\n"
                        "ShellExecute=False\n"
                        "SingleFramesOnly=False\n"
                    ).format(sh_path=sh_path)

                    job_info = (
                        "BatchName={batch_name}\n"
                        "Name={nk_name}_layer_render\n"
                        "Plugin=CommandLine\n"
                        "Frames={first}-{last}\n"
                        "ChunkSize=10\n"
                        "Pool=2d_pool\n"
                        "Group=2d_group\n"
                        "Priority=50\n"
                        "Department=Roto\n"
                        "UserName={user}\n"
                        "JobDependencies=\n"
                        "ConcurrentTasks=1\n"
                        "TaskTimeoutMinutes=0\n"
                        "MachineName=\n"
                    ).format(
                        batch_name=os.getlogin() + "_layer_render",
                        nk_name=nk_name,
                        first=first,
                        last=last,
                        user=os.getlogin(),
                    )

                    tmp = self.get_tmp_path()
                    job_file = os.path.join(tmp, "cmdline_job_info.job")
                    plugin_file = os.path.join(tmp, "cmdline_plugin_info.job")

                    with open(job_file, "w") as f:
                        f.write(job_info)
                    with open(plugin_file, "w") as f:
                        f.write(plugin_info)

                    deadline_cmd = "/apps/Thinkbox/Deadline10/bin/deadlinecommand"
                    command = [deadline_cmd, job_file, plugin_file]

                    process = subprocess.Popen(
                        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                    )
                    stdout, stderr = process.communicate()
                    result = stdout.decode("utf-8")
                    print(
                        "[shape_layer_wise_render] deadline result: {}".format(result)
                    )

                    job_id = None
                    for line in result.split("\n"):
                        if "JobID=" in line:
                            job_id = line.split("JobID=")[1].strip()
                            break

                    if job_id:
                        print(
                            "[shape_layer_wise_render] submitted '{}' job_id={}".format(
                                nk_name, job_id
                            )
                        )
                        submitted_job_ids.append(job_id)
                except Exception as e:
                    print("[shape_layer_wise_render] ERROR '{}': {}".format(nk_name, e))

            if submitted_job_ids:
                self.job_id = submitted_job_ids[-1]
                self.layer_job_ids = submitted_job_ids
                print("[shape_layer_wise_render] self.job_id={}".format(self.job_id))
            else:
                self.layer_job_ids = []
                print("[shape_layer_wise_render] No jobs submitted")

    def populate_tree_widget(self, structure, parent_item=None):
        """
        Populates a tree widget with a given structure.

        This method recursively creates tree items in the UI's tree widget based on
        the provided structure. It supports both nested dictionaries and strings,
        replacing placeholders in the names of the items.

        Args:
            structure (list | dict): The structure to populate in the tree widget.
            parent_item (QtWidgets.QTreeWidgetItem, optional): The parent item to which
                                                                new items will be added.
                                                                Defaults to None.

        Returns:
            None
        """
        if parent_item is None:
            path_parts = self.out_path.split("/")
            root_item = QtWidgets.QTreeWidgetItem(self.render_ui.tree, [path_parts[0]])
            current_item = root_item

            for part in path_parts[1:]:
                current_item = QtWidgets.QTreeWidgetItem(current_item, [part])
            parent_item = current_item

        for item in structure:
            if isinstance(item, dict):
                for key, value in item.items():
                    key = self.replace_placeholders(key, self.placeholders)
                    tree_item = QtWidgets.QTreeWidgetItem(parent_item, [key])
                    self.populate_tree_widget(value, tree_item)
            elif isinstance(item, str):
                item = self.replace_placeholders(item, self.placeholders)
                QtWidgets.QTreeWidgetItem(parent_item, [item])

        self.render_ui.tree.expandAll()

    # def layer_count(self):
    # session = fx.activeSession()
    # roto_nodes = session.getNodes("RotoNode")
    # for roto_node in roto_nodes:
    #     layers = roto_node.children
    #     top_layername = layers
    # return roto_node , len(top_layername)

    def render_nmb(self, **args):
        for key, value in args.items():
            print(value)
            if "NMB" in value:
                nuke_file_path = self.nmb_nuke_path
            else:
                nuke_file_path = ""
        project = fx.activeProject().path
        # self.disable_blur()

        base_dir = os.path.join(project.split("/scripts/")[0], "scripts")
        end_dir = project.split("/scripts/")[1]
        hidden_folder_path = os.path.join(base_dir, ".tmp")
        os.makedirs(hidden_folder_path, exist_ok=True)
        fields = self.get_fields_from_path(
            os.path.dirname(project), "silhouette_shot_work"
        )
        field_name = fields["name"]
        nmb_script_path = os.path.join(hidden_folder_path, end_dir).replace(
            "_" + field_name + "_", "_" + field_name + "_nmb_"
        )
        nmb_script_path = os.path.dirname(nmb_script_path)
        if os.path.exists(nmb_script_path):
            shutil.rmtree(nmb_script_path)
        source_folder = os.path.dirname(fx.activeProject().path)
        shutil.copytree(source_folder, nmb_script_path)
        project_name_fields = self.get_fields_from_path(
            os.path.dirname(project), "silhouette_shot_work"
        )
        project_field_name = project_name_fields["name"]
        fields = self.get_fields_from_path(
            os.path.dirname(project), "silhouette_shot_work"
        )
        field_name = fields["name"]
        session = fx.activeSession()
        output_nodes = session.getNodes("OutputNode")
        output_paths = {}
        print("*" * 20)
        print("self.template_input_data: ", self.template_input_data)
        print("*" * 20)
        import getpass

        if (
            self.template_input_data.get("MB_matte_path")
            and getpass.getuser() == "ilambharathi"
        ):
            for matte_name, matte_path in self.template_input_data.get(
                "MB_matte_path"
            ).items():
                description = self.get_fields_from_path(
                    matte_path, "silhouette_shot_render_pub_stereo"
                )
                nmb_render_path = self.nmb_actual_path[
                    description["name"].replace(project_field_name + "_", "")
                ]
                output_paths[matte_name] = nmb_render_path
        else:
            for publish_node in output_nodes:
                description = self.get_fields_from_path(
                    publish_node.properties["path"].value + ".%04d" + ".exr",
                    "silhouette_shot_render_pub_stereo",
                )
                nmb_render_path = self.nmb_actual_path[
                    description["name"].replace(project_field_name + "_", "")
                ]
                output_paths[publish_node.label] = nmb_render_path
        start_frame = self.render_ui.startFrameInput.text()
        end_frame = self.render_ui.endFrameInput.text()
        project_path = nmb_script_path
        script_path = (
            "/tools/silhouette_tools/2021.5/my_task/package_creation/fx_command.py"
        )
        location = SiteConfig().get_location()
        if location == "chennai":
            sfx_cmd = "/apps/silhouette/Silhouette-2023.5/sfxcmd"
        else:
            sfx_cmd = "/cold/pipeline/apps/silhouette/Silhouette-2023.5/sfxcmd"
        merged_args = output_paths.copy()
        merged_args.update(nuke_file_path)
        output_paths_json = json.dumps(merged_args)
        frame_range = str(start_frame) + "-" + str(end_frame)
        os.chmod(project_path, 0o777)
        silhouette_cmd = [
            sfx_cmd,
            project_path,
            "-range",
            frame_range,
            "-render",
            "0",
            "-args",
            output_paths_json,
            "-script",
            script_path,
            "-all",
        ]

        render_process = subprocess.Popen(
            silhouette_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = render_process.communicate()
        if render_process.returncode == 0:
            print("Render command executed successfully")
            print("Output: {stdout}")
        else:
            print("Command failed with return code {render_process.returncode}")
            print("Error output: {stderr}")

        try:
            from silhouette_package import feather_removal

            feather_removal.remove_all_feathers_from_path(nmb_script_path)
        except Exception as e:
            print(f"❌ Feather removal failed: {e}")

        batch_name = os.path.basename(fx.activeProject().path).split(".")[0]
        job_name = fx.activeProject().path + "_nmb_render"
        pool = ("ingestion_pool",)
        frames = f"{start_frame}-{end_frame}"
        job_id = self.submit_render(
            batch_name=batch_name,
            job_name=job_name,
            pool=pool,
            frames=frames,
            output="-all",
            department="Roto",
            scene_file=project_path,
        )
        self.job_id = job_id

        # else:

        #     nmb_render_script = create_nmb.create_silhouette_script_file(
        #         output_paths=output_paths,
        #         start_frame=start_frame,
        #         end_frame=end_frame,
        #         project_path=project_path,
        #         script_path=script_path,
        #         nuke_file_paths = nuke_file_path
        #     )
        #     nmb_render_id = create_python_job(
        #         job_name=fx.activeProject().path+ "_nmb_render",
        #         python_job_command=nmb_render_script,
        #         dependent=self.job_id,
        #         pool="ingestion_pool"
        #     )
        # self.set_value_nkt()

        # self.nmb_render_deadline()vbn

    def nuke_multiple_shape_export(self, layer_dict=None, export_mode="layer", **args):
        print("layer_dict______", layer_dict)
        session = fx.activeSession()
        roto_nodes = session.getNodes("RotoNode")
        count = 0

        try:
            project_field_name = self.get_fields_from_path(
                os.path.dirname(fx.activeProject().path), "silhouette_shot_work"
            )["name"]
        except Exception:
            project_field_name = ""

        dst_tpl = self.placeholders.get("layer_shape_dst_path")

        for roto_node in roto_nodes:
            values = []
            layers = roto_node.children

            # ── resolve description for this roto_node, only if a show opts in ──
            description = None
            if dst_tpl:
                try:
                    out_node = self.get_connected_output_nodes(roto_node)
                    node_path = out_node.properties["path"].value + ".%04d.exr"
                    fields = self.get_fields_from_path(
                        node_path, "silhouette_shot_render_pub_stereo"
                    )
                    description = fields["name"].replace(project_field_name + "_", "")
                except Exception as e:
                    print(
                        f"[nuke_multiple_shape_export] could not resolve description: {e}"
                    )
                    top_layername = str(layers[0].label) if layers else ""
                    description = self.matte_shape_bkp.get(
                        top_layername, top_layername
                    ).split(".")[0]

            if export_mode == "layer":
                for layer_main in layers:
                    for layer_children in layer_main.children:
                        print("layer_children", layer_children)
                        parent_name = layer_main.label.replace(" ", "_")
                        child_name = layer_children.label.replace(" ", "_")

                        if layer_dict is not None:
                            key = f"{child_name}"
                            layer_name_for_file = layer_dict[key]
                        else:
                            layer_name_for_file = child_name

                        if dst_tpl:
                            local_ph = dict(self.placeholders)
                            local_ph["description"] = description
                            local_ph["layer"] = layer_name_for_file
                            resolved = self.apply_placeholders(dst_tpl, local_ph)
                            nuke_path = (
                                self.out_path + resolved
                                if not os.path.isabs(resolved)
                                else resolved
                            )
                            os.makedirs(os.path.dirname(nuke_path), exist_ok=True)
                        else:
                            nuke_file_name = f"{layer_name_for_file}.nk"
                            nuke_bkp_path = os.path.join(
                                self.get_tmp_path(), "roto_shapes"
                            )
                            if not os.path.exists(nuke_bkp_path):
                                os.makedirs(nuke_bkp_path)
                            nuke_path = os.path.join(nuke_bkp_path, nuke_file_name)

                        print("nuke_path_____", nuke_path)

                        selected = self.children_select_all(layer_children.children)
                        if not selected:
                            print(
                                f"[nuke_multiple_shape_export] No children found for {layer_children.label}, skipping"
                            )
                            continue

                        viewer.node = roto_node
                        select(selected)
                        sil_exporter = fx.io_modules["Nuke 9+ Shapes"]
                        if sil_exporter.can_export:
                            if os.path.exists(nuke_path):
                                os.remove(nuke_path)
                            sil_exporter.export(nuke_path)
                            select([])
                            values.append(
                                {
                                    "path": nuke_path,
                                    "channel": layer_children.properties[
                                        "channel"
                                    ].value,
                                }
                            )
                            count += 1

            elif export_mode == "node":
                all_selected = []
                for layer_main in layers:
                    children = self.children_select_all(layer_main.children)
                    if children:
                        all_selected.extend(children)

                if not all_selected:
                    print(
                        "[nuke_multiple_shape_export] No children found in roto_node, skipping"
                    )
                    continue  # or appropriate handling for your loop structure

                if dst_tpl:
                    local_ph = dict(self.placeholders)
                    local_ph["description"] = description
                    resolved = self.apply_placeholders(dst_tpl, local_ph)
                    nuke_path = (
                        self.out_path + resolved
                    )  # ✅ always prepend, no isabs check
                    os.makedirs(os.path.dirname(nuke_path), exist_ok=True)
                else:
                    nuke_file_name = f"{self.placeholders.get('shot', 'shape')}.nk"
                    export_dir = os.path.join(self.get_tmp_path(), "roto_shapes")
                    if not os.path.exists(export_dir):
                        os.makedirs(export_dir)
                    nuke_path = os.path.join(export_dir, nuke_file_name)

                viewer.node = roto_node
                select(all_selected)
                sil_exporter = fx.io_modules["Nuke 9+ Shapes"]
                if sil_exporter.can_export:
                    if os.path.exists(nuke_path):
                        os.remove(nuke_path)
                    sil_exporter.export(nuke_path)
                    select([])
                    values.append({"path": nuke_path, "layer": "all"})
                    count += 1

            self.layer_dict[
                self.get_connected_output_nodes(roto_node).properties["path"].value
            ] = values

    def create_folder_structure(self, structure, placeholders):
        """
        Creates a folder structure based on a defined template and placeholders.

        This method checks for valid inputs in the rendering UI, retrieves version data,
        and initiates the process of creating the specified folder structure. It updates
        the write node and saves the current Nuke script before creating folders and files
        as defined in the structure.

        Args:
            structure (list): A list defining the folder and file structure to create.
            placeholders (dict): A dictionary of placeholders for dynamic content in folder/file names.

        Returns:
            None

        Raises:
            ValueError: If the version data is invalid or missing.
        """
        if self.placeholders.get("ui"):
            # roto_node,count = self.layer_count()
            window = mxp_ui.PXORotoLayerMaker()
            result = window.exec_()
            print(result)
            if result:
                self.nuke_multiple_shape_export(window.get_values())

        print("*" * 50)
        print(placeholders["sg_plate_name"])
        print(self.placeholders["sg_plate_name"])
        print(self.sg_plate_name)
        print("*" * 50)
        # if self.sg_plate_name == "":
        #     self.app
        if self.render_ui.reviewerinput.currentText() == "":
            self.show_dialog("Please select the reviewer")
            return
        print("______________________")
        if self.render_ui.versionDropdown.text() == "":
            self.show_dialog("Please select the valid version")
            return
        self.version_data = self.render_ui.version_description_error()
        if self.version_data is None:
            return

        if self.render_ui.check_reviwer() == None:
            self.show_dialog("Please select the reviwer")
            return

        self.create_structure(self.out_path, structure, placeholders)
        self.render()

    # def create_structure(self, base_path, structure, placeholders):
    #     """
    #     Recursively creates directories and files based on a specified structure.

    #     This method traverses a given structure definition, creating directories and files
    #     as specified. Directories are created if they don't already exist, and placeholder
    #     values are replaced in both folder and file names.

    #     Args:
    #         base_path (str): The base path where the structure will be created.
    #         structure (list): A list of directories and files to create.
    #         placeholders (dict): A dictionary for replacing placeholders in names.

    #     Returns:
    #         None
    #     """

    #     for item in structure:
    #         if isinstance(item, dict):
    #             for folder, contents in item.items():
    #                 folder = self.replace_placeholders(folder, placeholders)
    #                 folder_path = os.path.join(base_path, folder)
    #                 os.makedirs(folder_path, exist_ok=True)
    #                 key_value = os.path.basename(folder_path)
    #                 print("_+_+_++++++++++++jeyey", key_value)
    #                 print(self.render_folder_dict)
    #                 if key_value in self.render_folder_dict:
    #                     self.render_path_dict[folder_path] = self.render_folder_dict[
    #                         key_value
    #                     ]
    #                 if self.placeholders.get("matte_folder"):
    #                     if key_value == "matte":
    #                         for (
    #                             matte_name,
    #                             matte_path,
    #                         ) in self.render_folder_dict.items():
    #                             target = os.path.join(folder_path, matte_name)
    #                             self.render_path_dict[target] = matte_path

    #                 print(f"Created folder: {folder_path}")

    #                 self.create_structure(folder_path, contents, placeholders)
    #         elif isinstance(item, str):
    #             file_name = self.replace_placeholders(item, placeholders)
    #             file_path = os.path.join(base_path, file_name)
    #             with open(file_path, "w") as f:
    #                 f.write("")
    #                 f.close()
    #             print(f"Created file: {file_path}")

    def create_structure(self, base_path, structure, placeholders):
        """
        Recursively creates directories and files based on a specified structure.

        Args:
            base_path (str): The base path where the structure will be created.
            structure (list): A list of directories and files to create.
            placeholders (dict): A dictionary for replacing placeholders in names.

        Returns:
            None
        """
        for item in structure:
            if isinstance(item, dict):
                for folder, contents in item.items():
                    folder = self.replace_placeholders(folder, placeholders)
                    folder_path = os.path.join(base_path, folder)
                    os.makedirs(folder_path, exist_ok=True)
                    key_value = os.path.basename(folder_path)
                    parent_folder = os.path.basename(base_path)

                    print(
                        f"[create_structure] checking parent={parent_folder} vs matte_parent, key={key_value}"
                    )

                    # e.g. other shows where mb_folder_template = "some_folder_name"
                    # if key_value in self.render_folder_dict:
                    #     self.render_path_dict[folder_path] = self.render_folder_dict[
                    #         key_value
                    #     ]
                    #     print(
                    #         f"[create_structure] Mapped: {folder_path} → {self.render_folder_dict[key_value]}"
                    #     )
                    if key_value in self.render_folder_dict:
                        self.render_path_dict[folder_path] = self.render_folder_dict[
                            key_value
                        ]
                        print(
                            f"[create_structure] Mapped: {folder_path} → {self.render_folder_dict[key_value]}"
                        )

                    # handles tfs2 where leaf is "main" but description is in parent e.g. "matte01"
                    else:
                        parent_desc = next(
                            (
                                k
                                for k in self.render_folder_dict
                                if parent_folder.endswith(k)
                            ),
                            None,
                        )
                        if parent_desc:
                            self.render_path_dict[folder_path] = (
                                self.render_folder_dict[parent_desc]
                            )
                            print(
                                f"[create_structure] PARENT Mapped: {folder_path} → {self.render_folder_dict[parent_desc]}"
                            )

                    # Only triggers when mb_folder_template is empty string
                    # Only maps when parent folder is matte_renders_exr (or configured matte parent)
                    # This ensures matte01 folder → matte01 src, matte02 folder → matte02 src
                    if not self.placeholders.get("mb_folder_template", "").strip():
                        matte_parent = self.placeholders.get(
                            "matte_extend_path", ["matte_renders_exr"]
                        )[0]

                        if parent_folder == matte_parent:
                            if key_value in self.render_folder_dict:
                                self.render_path_dict[folder_path] = (
                                    self.render_folder_dict[key_value]
                                )
                                print(
                                    f"[create_structure] DESC Mapped: {folder_path} → {self.render_folder_dict[key_value]}"
                                )
                            else:
                                print(
                                    f"[create_structure] ⚠️ key '{key_value}' NOT in render_folder_dict keys: {list(self.render_folder_dict.keys())}"
                                )

                    # ✅ CASE 3: matte_folder style (older shows that use a single "matte" folder)
                    if self.placeholders.get("matte_folder"):
                        if key_value == "matte":
                            for (
                                matte_name,
                                matte_path,
                            ) in self.render_folder_dict.items():
                                target = os.path.join(folder_path, matte_name)
                                self.render_path_dict[target] = matte_path
                                print(
                                    f"[create_structure] MATTE_FOLDER Mapped: {target} → {matte_path}"
                                )

                    print(f"Created folder: {folder_path}")
                    self.create_structure(folder_path, contents, placeholders)

            elif isinstance(item, str):
                file_name = self.replace_placeholders(item, placeholders)
                file_path = os.path.join(base_path, file_name)
                with open(file_path, "w") as f:
                    f.write("")
                print(f"Created file: {file_path}")

    def select_all(self, node):
        node = node
        if node:
            finder = ObjectFinder(hidden=False)
            objects = finder.find(node.children)
            objects.append(node)
            return objects

    def children_select_all(self, children):
        node = children
        if node:
            finder = ObjectFinder(hidden=False)
            objects = finder.find(children)
            return objects
        return []  # ✅ return empty list instead of None

    def submit_py_deadline(self, command, job_id):
        session = fx.activeSession()
        version_create = create_python_job(
            job_name=f"{fx.activeProject().name}_{session.label}",
            python_job_command=command,
            dependent=job_id,
            pool="ingestion_pool",
            Secondary_pool="2d_pool",
            department="Roto",
        )

    # def mate_copy(self, **args):
    #     mb_folder_template = self.placeholders["mb_folder_template"]
    #     mb_actual_path = self.apply_placeholders(mb_folder_template, self.placeholders)
    #     print("gdjdhd", self.render_path_dict.items())

    #     for dst_path, src_path in self.render_path_dict.items():
    #         print("run____________2")
    #         file_name = os.path.basename(src_path)
    #         frame_ext = file_name.split(".")
    #         frame = frame_ext[-2]
    #         ext = frame_ext[-1]
    #         if self.placeholders.get("matte_folder"):
    #             matte_folder = os.path.basename(dst_path)
    #             shot = self.placeholders.get("shot", "unknown")
    #             out_version = self.placeholders.get("out_version", "v001")
    #             frame_digits = (
    #                 len(re.search(r"(\d+)", src_path).group(1))
    #                 if re.search(r"(\d+)", src_path)
    #                 else 4
    #             )
    #             frame_pattern = f"%0{frame_digits}d"
    #             file_name = (
    #                 f"{shot}_roto_BFS_{matte_folder}_{out_version}.{frame_pattern}.exr"
    #             )

    #         else:
    #             file_name = os.path.basename(dst_path) + "." + frame + "." + ext

    #         dst_path = os.path.join(dst_path, file_name)
    #         self.job_id = self.copying_render_files(src_path, dst_path)
    #         directory = os.path.dirname(src_path)
    #         base_name, ext = os.path.splitext(file_name)
    #         file_pattern = os.path.join(directory, f"{base_name.split('.')[0]}.*{ext}")
    #         matching_files = sorted(glob.glob(file_pattern))
    #         print("run____________4")
    #         if matching_files:
    #             print("run____________3")
    #             frames = [
    #                 int(os.path.splitext(f)[0].split(".")[-1]) for f in matching_files
    #             ]
    #             first_frame = min(frames)
    #             last_frame = max(frames)
    #             print(f"Frame range for {dst_path}: {first_frame} to {last_frame}")
    #             self.mb_folder_path.append(
    #                 dst_path + "[" + str(first_frame) + "-" + str(last_frame) + "]"
    #             )
    #             deadline_version_mate_path = dst_path
    #         else:
    #             print(f"No matching files found for {dst_path}.")

    def mate_copy(self, **args):
        print(f"[mate_copy] render_folder_dict: {self.render_folder_dict}")
        print(f"[mate_copy] render_path_dict has {len(self.render_path_dict)} entries:")
        for k, v in self.render_path_dict.items():
            print(f"  DST: {k}  SRC: {v}")

        matte_naming_convention = self.placeholders.get("matte_naming_convention")
        print(f"[mate_copy] matte_naming_convention: {matte_naming_convention}")

        desc_lookup = {}  # dst_folder -> description (for fallback naming)

        if not self.render_path_dict:
            print(
                "[mate_copy] render_path_dict is EMPTY — falling back to render_folder_dict"
            )

            base_path = self.out_path + self.placeholders.get("project_base_path", "")
            actual_base = self.apply_placeholders(base_path, self.placeholders)
            matte_extend = self.placeholders.get(
                "matte_extend_path", ["matte_renders_exr"]
            )

            for desc, src_path in self.render_folder_dict.items():
                local_ph = dict(self.placeholders)
                local_ph["description"] = desc
                expanded_segments = [
                    self.apply_placeholders(seg, local_ph) for seg in matte_extend
                ]
                dst_folder = os.path.join(actual_base, *expanded_segments)
                os.makedirs(dst_folder, exist_ok=True)
                self.render_path_dict[dst_folder] = src_path
                desc_lookup[dst_folder] = desc  # leaf is "main", remember real desc
                print(f"[mate_copy] Fallback mapped: {dst_folder} → {src_path}")

        submitted_job_ids = []
        project = fx.activeProject().path
        project_name_fields = self.get_fields_from_path(
            os.path.dirname(project), "silhouette_shot_work"
        )
        project_field_name = project_name_fields["name"]

        for dst_folder_path, src_path in self.render_path_dict.items():
            print(f"[mate_copy] Processing: {dst_folder_path} ← {src_path}")

            file_name = os.path.basename(src_path)
            frame_ext = file_name.split(".")
            # handle %04d in filename: split gives ['name', '%04d', 'exr']
            if len(frame_ext) >= 3:
                frame = frame_ext[-2]  # %04d
                ext = frame_ext[-1]  # exr
            else:
                frame = "%04d"
                ext = "exr"
            # description = os.path.basename(dst_folder_path)
            # try:
            #     description = self.get_fields_from_path(
            #         src_path,
            #         "silhouette_shot_render_pub_stereo",
            #     )
            #     description = description["name"].replace(project_field_name + "_", "")
            # except Exception:
            description = os.path.basename(dst_folder_path)

            print(f"[mate_copy] description from dst folder: {description}")

            if matte_naming_convention:
                local_ph = dict(self.placeholders)
                local_ph["description"] = description
                resolved_name = self.apply_placeholders(
                    matte_naming_convention, local_ph
                )
                file_name = f"{resolved_name}.{frame}.{ext}"
                print(f"[mate_copy] naming_convention → {file_name}")

            elif self.placeholders.get("matte_folder"):
                shot = self.placeholders.get("shot", "unknown")
                out_version = self.placeholders.get("out_version", "v001")
                frame_digits = (
                    len(re.search(r"(\d+)", src_path).group(1))
                    if re.search(r"(\d+)", src_path)
                    else 4
                )
                frame_pattern = f"%0{frame_digits}d"
                file_name = (
                    f"{shot}_roto_BFS_{description}_{out_version}.{frame_pattern}.exr"
                )

            else:
                # fallback — should not reach here if matte_naming_convention is set
                file_name = f"{description}.{frame}.{ext}"
                print(f"[mate_copy] using fallback filename: {file_name}")

            final_dst_path = os.path.join(dst_folder_path, file_name)
            print(f"[mate_copy] Copying {src_path} → {final_dst_path}")

            job_id = self.copying_render_files(src_path, final_dst_path)
            if job_id:
                submitted_job_ids.append(job_id)
                print(f"[mate_copy]  job_id={job_id} for {description}")

        if submitted_job_ids:
            self.job_id = submitted_job_ids[-1]
            print(f"[mate_copy] All job IDs: {submitted_job_ids}")
        else:
            print("[mate_copy]  No jobs submitted")

    # def matte_template_render(self, matte_template_path):
    #     input_template_path = matte_template_path
    #     output_template_path = os.path.join(
    #         self.get_tmp_path(),
    #         os.path.basename(input_template_path) + ".nk",
    #     )
    #     TEMPLATE_COUNT = 1

    #     for dst_path, src_path in self.render_path_dict.items():
    #         py_template = self.create_roto_nkt_file(
    #             input_template_path,
    #             output_template_path,
    #             input_path,
    #             write_path,
    #             startframe,
    #             endframe,
    #             mate_list_path,
    #             name,
    #             self.layer_dict,
    #             additional_value,
    #             resolution,
    #             layer_path,
    #             bake,
    #         )

    #     pass

    def mate_nuke_set(self, **args):
        nuke_template_paths = args.get("key", [])
        if not nuke_template_paths:
            print("[mate_nuke_set] No nuke template path found")
            return

        nuke_template_path = nuke_template_paths[0]

        print(
            f"[mate_nuke_set] render_path_dict has {len(self.render_path_dict)} entries:"
        )
        for k, v in self.render_path_dict.items():
            print(f"  DST: {k}  SRC: {v}")

        for k, v in self.render_folder_dict.items():
            print(f"  KEY: {k}  PATH: {v}")

        start_frame = self.render_ui.startFrameInput.text()
        end_frame = self.render_ui.endFrameInput.text()
        chunk = int(int(end_frame) - int(start_frame) + 1)
        tmp_path = self.get_tmp_path()

        initial_dependent_job_id = self.job_id
        submitted_job_ids = []

        # This has ALL descriptions, not just the ones that matched folder structure
        source_dict = (
            self.render_folder_dict
            if self.render_folder_dict
            else self.render_path_dict
        )

        print(
            f"[mate_nuke_set] Will process {len(source_dict)} descriptions: {list(source_dict.keys())}"
        )

        for description, src_path in source_dict.items():
            print(f"\n[mate_nuke_set] ---- Processing: {description} ----")
            print(f"[mate_nuke_set] src_path: {src_path}")

            local_placeholders = dict(self.placeholders)
            local_placeholders["description"] = description

            file_name = os.path.basename(src_path)
            frame_ext = file_name.split(".")
            ext = local_placeholders.get("matte_extension", frame_ext[-1])

            # Build frame pattern
            # frame_digits = (
            #     len(re.search(r"(\d+)", src_path).group(1))
            #     if re.search(r"(\d+)", src_path)
            #     else 4
            # )
            frame_digits_match = re.search(r"%0(\d+)d", src_path)
            frame_digits: int = (
                int(frame_digits_match.group(1)) if frame_digits_match else 4
            )
            frame_pattern = f"%0{frame_digits}d"

            # Build input_path
            input_path = re.sub(
                r"\d{" + str(frame_digits) + r"}\." + frame_ext[-1],
                f"{frame_pattern}.{frame_ext[-1]}",
                src_path,
            )

            # Match by folder name == description
            dst_path = None
            for dp in self.render_path_dict.keys():
                if os.path.basename(dp) == description:
                    dst_path = dp
                    break

            # Fallback: build dst_path from out_path + project_base_path + description
            if dst_path is None:
                base_path = self.out_path + local_placeholders.get(
                    "project_base_path", ""
                )
                actual_base = self.apply_placeholders(base_path, local_placeholders)
                dst_path = os.path.join(actual_base, description)

            os.makedirs(dst_path, exist_ok=True)

            # Build write_path
            matte_naming_convention = local_placeholders.get("matte_naming_convention")
            if matte_naming_convention:
                write_file_name = (
                    self.apply_placeholders(matte_naming_convention, local_placeholders)
                    + f".{frame_pattern}.{ext}"
                )
            elif local_placeholders.get("matte_folder"):
                shot = local_placeholders.get("shot", "unknown")
                out_version = local_placeholders.get("out_version", "v001")
                write_file_name = (
                    f"{shot}_roto_BFS_{description}_{out_version}.{frame_pattern}.{ext}"
                )
            else:
                write_file_name = f"{description}.{frame_pattern}.{ext}"

            write_path = os.path.join(dst_path, write_file_name)

            nk_base_name = f"{os.path.splitext(os.path.basename(nuke_template_path))[0]}_{description}"
            script_name = f"mate_nuke_set_{description}"
            output_template_path = os.path.join(tmp_path, f"{nk_base_name}.nk")

            print(f"[mate_nuke_set] input_path:           {input_path}")
            print(f"[mate_nuke_set] write_path:           {write_path}")
            print(f"[mate_nuke_set] output_template_path: {output_template_path}")
            print(f"[mate_nuke_set] script_name:          {script_name}")

            # STEP 1 - create the py script
            py_template = self.create_roto_nkt_file(
                nuke_template_path,
                output_template_path,
                input_path,
                write_path,
                start_frame,
                end_frame,
                None,
                script_name,
                self.layer_dict,
                None,
                None,
                None,
                False,
            )
            print(f"[mate_nuke_set] py_template created: {py_template}")

            # STEP 2 - run nuke locally
            bash_script = """#!/bin/bash
    export PYTHONHOME=/apps/nuke/Nuke12.2v7
    export PYTHONPATH=$PYTHONPATH:'/tools/packages/nkt_api/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2:/tools/packages/nkt_api/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2/python'
    /apps/nuke/Nuke12.2v7/Nuke12.2 -t "{}"
    """.format(py_template)

            sh_path = os.path.join(tmp_path, f"{script_name}_run_nuke.sh")
            with open(sh_path, "w") as f:
                f.write(bash_script)
            subprocess.call(["chmod", "+x", sh_path])

            print(f"[mate_nuke_set] Running nuke locally for {description}...")
            result = subprocess.Popen(
                [sh_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = result.communicate()
            print(f"[mate_nuke_set] Nuke STDOUT: {stdout.decode()}")
            print(f"[mate_nuke_set] Nuke STDERR: {stderr.decode()}")
            print(f"[mate_nuke_set] Nuke return code: {result.returncode}")

            # STEP 3 - verify .nk was created
            if not os.path.exists(output_template_path):
                print(
                    f"[mate_nuke_set] ❌ NK FILE NOT CREATED for {description}: {output_template_path}"
                )
                continue

            print(f"[mate_nuke_set] ✅ NK file exists: {output_template_path}")

            # STEP 4 - submit to deadline
            try:
                plugin_details, job_details = get_info_txt(
                    f"{script_name}_proxy_action",
                    script_name,
                    "2d_pool",
                    "2d_group",
                    start_frame,
                    end_frame,
                    12.2,
                    chunk,
                    initial_dependent_job_id,
                    department="Roto",
                )
            except Exception as e:
                print(f"[mate_nuke_set] ❌ get_info_txt failed for {description}: {e}")
                continue

            try:
                job_id = submit_to_deadline(
                    plugin_details,
                    job_details,
                    output_template_path,
                )
                print(f"[mate_nuke_set] ✅ Submitted {description} → job_id: {job_id}")
                submitted_job_ids.append(job_id)
            except Exception as e:
                print(
                    f"[mate_nuke_set] ❌ submit_to_deadline failed for {description}: {e}"
                )
                continue

        if submitted_job_ids:
            self.job_id = submitted_job_ids[-1]
            print(f"[mate_nuke_set] All submitted job IDs: {submitted_job_ids}")
            print(f"[mate_nuke_set] self.job_id set to last: {self.job_id}")
        else:
            print("[mate_nuke_set] ⚠️ No jobs were successfully submitted.")

    def disable_motion_blur(self, check):
        session = fx.activeSession()
        roto_nodes = session.getNodes("RotoNode")
        for roto_node in roto_nodes:
            roto_node.property("motionBlur.enable").setValue(check)

    def disable_blur_recursive(self, item):
        """
        Recursively traverse roto node children
        and disable blur property if it exists.
        """
        try:
            # Check if this item has blur property
            blur_prop = item.property("blur")
            if blur_prop is not None:
                blur_prop.setValue(0)
        except Exception:
            pass  # Ignore if property doesn't exist

        # Traverse children
        try:
            for child in item.children:
                disable_blur_recursive(child)
        except Exception:
            pass

    def disable_blur(self):
        if self.placeholders.get("nmb_blur_remove"):
            print("motion_blur" * 25)

            session = fx.activeSession()
            roto_nodes = session.getNodes("RotoNode")

            for roto_node in roto_nodes:
                self.disable_blur_recursive(roto_node)

    def nuke_children_shpae_export(self, **args):
        session = fx.activeSession()
        roto_nodes = session.getNodes("RotoNode")
        for key, value_list in args.items():
            if not isinstance(value_list, list):
                value_list = [value_list]
        for value in value_list:
            for roto_node in roto_nodes:
                layers = roto_node.children
                top_layername = layers[0].label
                for layer_children in layers:
                    for k in layer_children.children:
                        shape_name = k.properties["channel"].value
                        nuke_file_name = (
                            self.matte_shape_bkp[str(top_layername)] + shape_name
                        )
                        nuke_bkp_path = os.path.join(self.get_tmp_path(), "roto_shapes")
                        if not os.path.exists(nuke_bkp_path):
                            os.makedirs(nuke_bkp_path)
                        nuke_bkp_path = os.path.join(nuke_bkp_path, nuke_file_name)
                        nuke_path = nuke_bkp_path
                        viewer.node = roto_node
                        select(selected_object)
                        sil_exporter = fx.io_modules["Nuke 9+ Shapes"]
                        if sil_exporter.can_export:
                            if os.path.exists(nuke_path):
                                os.remove(nuke_path)
                            print("_+++++++++++++++++++++++nuke_path", nuke_path)
                            check = sil_exporter.export(nuke_path)
                            select([])
                            if value == "NMB":
                                self.disable_motion_blur(True)

    def run_subprocess(self, script):
        # Copy current environment but remove Python contamination
        env = os.environ.copy()
        env.pop("PYTHONHOME", None)
        env.pop("PYTHONPATH", None)

        # result = subprocess.Popen([script], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        result = subprocess.run(
            script, shell=True, capture_output=True, text=True, env=env
        )
        print("STDOUT:\n", result.stdout)
        print("STDERR:\n", result.stderr)

        if result.returncode != 0:
            raise RuntimeError(f"Subprocess failed with code {result.returncode}")

    def export_all_shape_one(self, **args):
        nuke_file_path = self.placeholders["nuke_color_overlay_file"]
        nuke_file_path = self.out_path + self.apply_placeholders(
            nuke_file_path, self.placeholders
        )
        nuke_bkp_path = []
        session = fx.activeSession()
        roto_nodes = session.getNodes("RotoNode")
        for roto_node in roto_nodes:
            layers = roto_node.children
            top_layername = layers[0].label
            nuke_file_name = self.matte_shape_bkp[str(top_layername)]
            nuke_shape_path = os.path.join(self.get_tmp_path(), "roto_shapes")
            nuke_shape_path = os.path.join(nuke_shape_path, nuke_file_name)
            nuke_bkp_path.append(nuke_shape_path)
        print("nuke_bkp_path" * 100, nuke_bkp_path)
        if os.path.exists(nuke_file_path):
            os.remove(nuke_file_path)

        script = """
        /apps/nuke/Nuke12.2v7/Nuke12.2 -t "{}" --input {} --output {}
        """.format(
            "/tools/bpipe/roto_packaging_resolver/shape_add.py",
            " ".join(nuke_bkp_path),
            nuke_file_path,
        )
        self.run_subprocess(script)

    def export_fusion_shape(self, **args):
        session = fx.activeSession()
        fusion_setting_path = self.placeholders["fusion_shape"]
        fusion_setting_path = self.out_path + self.apply_placeholders(
            fusion_setting_path, self.placeholders
        )
        roto_nodes = session.getNodes("RotoNode")
        for roto_node in roto_nodes:
            selected_object = self.select_all(roto_node)
            viewer.node = roto_node
            select(selected_object)
            sil_exporter = fx.io_modules["Fusion Shapes"]
            sil_exporter.export(fusion_setting_path)

    def nuke_shape_export(self, **args):
        session = fx.activeSession()
        roto_nodes = session.getNodes("RotoNode")
        for key, value_list in args.items():
            if not isinstance(value_list, list):
                value_list = [value_list]
        for value in value_list:
            for roto_node in roto_nodes:
                layers = roto_node.children
                top_layername = layers[0].label
                selected_object = self.select_all(roto_node)

                if str(top_layername) in self.matte_shape_bkp:
                    nuke_file_name = self.matte_shape_bkp[str(top_layername)]
                elif self.matte_shape_bkp:
                    nuke_file_name = next(iter(self.matte_shape_bkp.values()))
                    print(
                        f"[nuke_shape_export] WARNING: layer '{top_layername}' not in "
                        f"matte_shape_bkp keys {list(self.matte_shape_bkp.keys())} — "
                        f"using fallback: {nuke_file_name}"
                    )
                else:
                    print(
                        f"[nuke_shape_export] ERROR: matte_shape_bkp is empty — "
                        f"skipping layer '{top_layername}'"
                    )
                    continue
                # ─────────────────────────────────────────────────────────────────

                nuke_bkp_path = os.path.join(self.get_tmp_path(), "roto_shapes")
                if not os.path.exists(nuke_bkp_path):
                    os.makedirs(nuke_bkp_path)
                nuke_bkp_path = os.path.join(nuke_bkp_path, nuke_file_name)
                if value == "MB":
                    nuke_path = self.mb_nuke_path[str(top_layername)]
                elif value == "NMB":
                    nuke_path = self.nmb_nuke_path[str(top_layername)]
                    self.disable_motion_blur(False)
                else:
                    nuke_path = nuke_bkp_path
                viewer.node = roto_node
                select(selected_object)
                sil_exporter = fx.io_modules["Nuke 9+ Shapes"]
                if sil_exporter.can_export:
                    if os.path.exists(nuke_path):
                        os.remove(nuke_path)
                    print("_+++++++++++++++++++++++nuke_path", nuke_path)
                    check = sil_exporter.export(nuke_path)
                    select([])
                    if value == "NMB":
                        self.disable_motion_blur(True)

    def sfx_file_copy(self, **args):
        # self.placeholders["sg_plate_name"] =
        dst_sfx_path = self.apply_placeholders(
            self.placeholders["dst_path_sx"], self.placeholders
        )
        sfx_file_path = self.out_path + dst_sfx_path
        project = fx.activeProject().path
        if os.path.exists(sfx_file_path):
            os.remove(sfx_file_path)
        shutil.copy(project, sfx_file_path)
        sfx_delivery_version = SG.publish.delivery_publish.DeliveryVersion(
            SG,
            "_",
            SG.context,
            comment="",
            sg_version_fields={"sg_client_deliverable": True},
        )
        sfx_delivery_version.version_type = "SFX Scene"
        sfx_delivery_version._version_number = int(self.out_version[1:])
        sfx_delivery_version.properties.source_path = project

        sfx_delivery_exporter = SG.publish.delivery_publish.DeliveryExporter(
            sfx_delivery_version, pf_type="SFX Scene", file_ext="sfx"
        )
        sfx_delivery_version.add_exporter(sfx_delivery_exporter)
        sfx_delivery_exporter.publish_path = sfx_file_path
        if os.getlogin() != "chandru":
            sfx_delivery_version.create_sg_entities()  # need to un command

    def sfx_roto_merge(self, **args):
        sfx_cmd = "/apps/silhouette/Silhouette-2023.5/sfxcmd"
        project_path = (
            fx.activeProject().path
        )  # existing project with multiple roto nodes
        script_path = "/tools/silhouette_tools/2021.5/my_task/package_creation/package_dependency/merge_roto_node.py"  # the merge script we wrote
        frame_range = "1-10"  # doesn't matter much, no render happening
        dst_sfx_path = self.apply_placeholders(
            self.placeholders["dst_path_sx"], self.placeholders
        )
        sfx_out_path = self.out_path + dst_sfx_path
        tmp_path = os.path.join(os.environ["HOME"], "tmp") + "/silhouette_copy_script"
        sfx_file_path = tmp_path + dst_sfx_path
        if os.path.exists(sfx_file_path):
            if os.path.isdir(sfx_file_path):
                shutil.rmtree(sfx_file_path)
            else:
                os.remove(sfx_file_path)

        output_paths_json = json.dumps(
            {
                "output_project_path": sfx_file_path  # where the result goes
            }
        )

        silhouette_cmd = [
            sfx_cmd,
            project_path,
            "-range",
            frame_range,
            "-render",
            "0",
            "-args",
            output_paths_json,
            "-script",
            script_path,
            "-all",
        ]

        print("running:", " ".join(silhouette_cmd))
        result = subprocess.run(
            silhouette_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        src_path = Path(sfx_file_path)
        file_name = "project.sfx"
        src_path = src_path / file_name
        shutil.copy(src_path, sfx_out_path)
        print("STDOUT:")
        print(result.stdout)

        print("STDERR:")
        print(result.stderr)
        print("exit code:", result.returncode)

    # def sfx_roto_merge(self, **args):
    #     sfx_cmd = "/apps/silhouette/Silhouette-2023.5/sfxcmd"
    #     project_path = fx.activeProject().path
    #     script_path = "/tools/silhouette_tools/2021.5/my_task/package_creation/package_dependency/merge_roto_node.py"
    #     frame_range = "1-10"

    #     dst_sfx_path = self.apply_placeholders(
    #         self.placeholders["dst_path_sx"], self.placeholders
    #     )

    #     # Final destination file path (with .sfx extension)
    #     sfx_out_path = self.out_path + dst_sfx_path

    #     # Temporary folder for Silhouette output (remove the .sfx filename part)
    #     tmp_path = os.path.dirname(sfx_out_path)

    #     # Ensure temp directory exists
    #     os.makedirs(tmp_path, exist_ok=True)

    #     # Remove final file if it already exists
    #     if os.path.exists(sfx_out_path):
    #         os.remove(sfx_out_path)

    #     # Pass only the FOLDER to Silhouette (not the filename)
    #     output_paths_json = json.dumps({"output_project_path": tmp_path})

    #     silhouette_cmd = [
    #         sfx_cmd,
    #         project_path,
    #         "-range",
    #         frame_range,
    #         "-render",
    #         "0",
    #         "-args",
    #         output_paths_json,
    #         "-script",
    #         script_path,
    #         "-all",
    #     ]

    #     print("running:", " ".join(silhouette_cmd))
    #     result = subprocess.run(
    #         silhouette_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    #     )

    #     print("STDOUT:", result.stdout)
    #     print("STDERR:", result.stderr)
    #     print("exit code:", result.returncode)

    #     # After Silhouette finishes, rename project.sfx to the desired filename
    #     if result.returncode == 0:
    #         project_sfx_src = os.path.join(tmp_path, "project.sfx")

    #         if os.path.exists(project_sfx_src):
    #             # Rename project.sfx to the final filename
    #             shutil.move(project_sfx_src, sfx_out_path)
    #             print(
    #                 f"✓ Success! Renamed: project.sfx -> {os.path.basename(sfx_out_path)}"
    #             )
    #             print(f"✓ Location: {sfx_out_path}")
    #         else:
    #             print(f"✗ Error: project.sfx not found at {project_sfx_src}")
    #     else:
    #         print(f"✗ Silhouette failed with exit code {result.returncode}")

    def submit_render(
        self,
        batch_name="",
        job_name="",
        group="",
        pool="",
        frames="",
        output="",
        department="",
        scene_file="",
    ):
        current_process = psutil.Process()
        current_process_name = current_process.name()
        chunk_size = 10
        pool = "2d_pool"
        group = "2d_group"
        pool2 = "2d_pool"
        version = int(fx.version)
        sec = "2d_pool"
        plugin_details = """
        Version={}
        Node={}
        OutputDirectory=
        OutputFilename=
        OutputFormat=
        AdditionalOptions=
        Resolution=full
        Fields=none
        Dominance=even
        RunScript=False
        DisableRender=False
        SubmitScene=True
        """.format(version, output)

        job_details = """
        BatchName={}
        Name={}
        Comment=
        Pool={}
        SecondaryPool={}
        Group={}
        Priority=100
        Plugin=Silhouette
        TaskTimeoutMinutes=0
        EnableAutoTimeout=False
        ConcurrentTasks=1
        LimitConcurrentTasksToNumberOfCpus=True
        MachineLimit=0
        MachineName={}
        Whitelist=
        LimitGroups=
        JobDependencies=
        OverrideTaskExtraInfoNames=False
        Frames={}
        UserName={}
        Department={}
        ChunkSize={}
        """.format(
            batch_name,
            job_name,
            pool,
            pool2,
            group,
            socket.gethostname(),
            frames,
            os.getlogin(),
            department,
            chunk_size,
        )

        deadline_cmd = parse_simple_yaml("/tools/site_config.yml")["deadline_cmd"]
        if scene_file == "":
            sfx_project = str(fx.activeProject().path)
        else:
            sfx_project = str(os.path.join(scene_file, "project.sfx"))

        tmp_path = os.path.join(os.environ["HOME"], "tmp") + "/silhouette_copy_script"

        if not os.path.exists(tmp_path):
            os.makedirs(tmp_path)

        shutil.copy(sfx_project, tmp_path + "/" + os.path.basename(sfx_project))
        copy_script = tmp_path + "/" + os.path.basename(sfx_project)

        job_file = write_job_info_file(str(job_details).strip())
        plugin_file = write_plugin_info_file(str(plugin_details).strip())
        command = [deadline_cmd, job_file, plugin_file, copy_script]
        process = subprocess.Popen(command, stdout=PIPE, stderr=PIPE)
        print(command)
        jobid = extract_job_id(str(process.communicate()[0]))
        return jobid

    def set_value_nkt_layer_wise(self, **args):
        self.placeholders["extension"] = "exr"
        start_frame, end_frame = self.get_active_session_work_range()
        self.placeholders["frame_range"] = str(start_frame) + "-" + str(end_frame)

        write_path = self.placeholders["write_node_path"]
        write_path = self.out_path + self.apply_placeholders(
            write_path, self.placeholders
        )

        input_template_path = self.placeholders["nuke_coloroverlay_template"]
        tmp_path = self.get_tmp_path()

        project = fx.activeProject()
        formatted_path = None
        for i in project.sources:
            source_file_name = i.properties["path"].getValue()
            frame_range_match = re.search(r"\[(\d+)-(\d+)\]", source_file_name)
            if frame_range_match:
                digit_count = len(frame_range_match.group(2))
                formatted_path = re.sub(
                    r"\[\d+-\d+\]", f"%0{digit_count}d", source_file_name
                )
                break

        if not formatted_path:
            print("[set_value_nkt_layer_wise] No source path found")
            return

        start_frame = self.render_ui.startFrameInput.text()
        end_frame = self.render_ui.endFrameInput.text()
        chunk = int(int(end_frame) - int(start_frame) + 1)
        if self.packed_layer_dict:
            mate_list_path = ",".join(self.packed_layer_dict.keys())
        else:
            mate_list_path = self.mb_path_list()
        layer_path = self.get_layer_dict()
        resolution = (
            None
            if "dst" in self.project_name
            else os.path.basename(os.path.dirname(self.full_source_path))
        )

        session = fx.activeSession()
        roto_nodes = session.getNodes("RotoNode")
        submitted_job_ids = []

        for roto_node in roto_nodes:
            for layer_main in roto_node.children:
                for layer_children in layer_main.children:
                    child_name = layer_children.label.replace(" ", "_")

                    selected = self.children_select_all(layer_children.children)
                    if not selected:
                        print(
                            f"[set_value_nkt_layer_wise] No children in {child_name}, skipping"
                        )
                        continue

                    # export shapes for this layer to tmp
                    nuke_shape_dir = os.path.join(tmp_path, "roto_shapes")
                    os.makedirs(nuke_shape_dir, exist_ok=True)
                    layer_shape_path = os.path.join(nuke_shape_dir, f"{child_name}.nk")

                    viewer.node = roto_node
                    select(selected)
                    sil_exporter = fx.io_modules["Nuke 9+ Shapes"]
                    if not sil_exporter.can_export:
                        select([])
                        continue
                    if os.path.exists(layer_shape_path):
                        os.remove(layer_shape_path)
                    sil_exporter.export(layer_shape_path)
                    select([])

                    # ---- KEY CHANGE ----
                    # build per-layer tmp folder instead of using write_node_path
                    layer_tmp_dir = os.path.join(tmp_path, "layer_renders", child_name)
                    os.makedirs(layer_tmp_dir, exist_ok=True)

                    # get frame padding and ext from original write_path
                    frame_ext = os.path.basename(write_path).split(".")
                    frame_token = frame_ext[-2]  # %04d
                    ext = frame_ext[-1]  # exr

                    # write path goes to tmp/layer_renders/{child_name}/{child_name}.%04d.exr
                    layer_write_path = os.path.join(
                        layer_tmp_dir, "{}.{}.{}".format(child_name, frame_token, ext)
                    )
                    # ---- END KEY CHANGE ----

                    # build layer-specific nuke script name
                    nk_base = re.sub(r"\.%0\d+d", "", child_name)
                    nuke_template_name = "{}.nk".format(nk_base)
                    output_template_path = os.path.join(tmp_path, nuke_template_name)

                    # inject layer shape export into layer_dict for this submission
                    layer_write_dict = {
                        layer_shape_path: [
                            {
                                "path": layer_shape_path,
                                "channel": layer_children.properties["channel"].value,
                            }
                        ]
                    }

                    py_template = self.create_roto_nkt_file(
                        input_template_path,
                        output_template_path,
                        formatted_path,
                        layer_write_path,  # <-- now points to tmp
                        start_frame,
                        end_frame,
                        mate_list_path,
                        child_name,
                        layer_write_dict,
                        None,
                        resolution,
                        layer_path,
                        True,
                    )

                    print(
                        "[set_value_nkt_layer_wise] layer='{}' write='{}'".format(
                            child_name, layer_write_path
                        )
                    )

                    job_id = self.create_nuke_job(
                        child_name,
                        py_template,
                        nuke_template_name,
                        start_frame,
                        end_frame,
                        "",
                        chunk,
                        "",
                        True,
                    )

                    if job_id:
                        submitted_job_ids.append(job_id)
                        print(
                            f"[set_value_nkt_layer_wise] submitted {child_name} -> job_id={job_id}"
                        )
                    else:
                        print(
                            f"[set_value_nkt_layer_wise] ⚠️ No job_id for {child_name}"
                        )

        print(f"[set_value_nkt_layer_wise] All layer job IDs: {submitted_job_ids}")

    def render_nmb_token_driven(self, **args):
        """
        Token-driven NMB render. Builds nmb_render_path directly from YAML tokens
        (out_path + nmb_project_base_path/project_base_path + nmb_extend_path/matte_extend_path
        + description) instead of resolving it via sgtk template field matching
        (self.nmb_actual_path). Falls back to the shared MB tokens if no NMB-specific
        override is defined in the show's yaml, so it stays backward compatible.
        """
        for key, value in args.items():
            print(value)
            if "NMB" in value:
                nuke_file_path = self.nmb_nuke_path
            else:
                nuke_file_path = ""

        project = fx.activeProject().path
        base_dir = os.path.join(project.split("/scripts/")[0], "scripts")
        end_dir = project.split("/scripts/")[1]
        hidden_folder_path = os.path.join(base_dir, ".tmp")
        os.makedirs(hidden_folder_path, exist_ok=True)
        fields = self.get_fields_from_path(
            os.path.dirname(project), "silhouette_shot_work"
        )
        field_name = fields["name"]
        nmb_script_path = os.path.join(hidden_folder_path, end_dir).replace(
            "_" + field_name + "_", "_" + field_name + "_nmb_"
        )
        nmb_script_path = os.path.dirname(nmb_script_path)
        if os.path.exists(nmb_script_path):
            shutil.rmtree(nmb_script_path)
        source_folder = os.path.dirname(fx.activeProject().path)
        shutil.copytree(source_folder, nmb_script_path)

        if "nmb_project_base_path" in self.placeholders:
            base_path = self.placeholders["nmb_project_base_path"]
        else:
            base_path = self.out_path + self.placeholders.get("project_base_path", "")
        actual_base = self.apply_placeholders(base_path, self.placeholders)

        matte_extend = self.placeholders.get(
            "nmb_extend_path",
            self.placeholders.get("matte_extend_path", ["matte_renders_exr"]),
        )
        matte_naming_convention = self.placeholders.get(
            "nmb_naming_convention", self.placeholders.get("matte_naming_convention")
        )

        descriptions = getattr(self, "nmb_descriptions", None) or []
        if not descriptions:
            print(
                "[render_nmb_token_driven] no nmb descriptions found, nothing to render"
            )
            return

        session = fx.activeSession()
        output_nodes = session.getNodes("OutputNode")

        output_paths = {}
        for output_node, description in zip(output_nodes, descriptions):
            local_ph = dict(self.placeholders)
            local_ph["description"] = description
            expanded_segments = [
                self.apply_placeholders(seg, local_ph) for seg in matte_extend
            ]
            dst_folder = os.path.join(actual_base, *expanded_segments)
            os.makedirs(dst_folder, exist_ok=True)

            if matte_naming_convention:
                file_name = self.apply_placeholders(matte_naming_convention, local_ph)
            else:
                file_name = description

            nmb_render_path = os.path.join(dst_folder, file_name)

            nmb_render_path = os.path.join(dst_folder, file_name)
            output_paths[output_node.label] = nmb_render_path
            print(f"[render_nmb_token_driven] {output_node.label} -> {nmb_render_path}")

        start_frame = self.render_ui.startFrameInput.text()
        end_frame = self.render_ui.endFrameInput.text()
        project_path = nmb_script_path
        script_path = (
            "/tools/silhouette_tools/2021.5/my_task/package_creation/fx_command.py"
        )
        location = SiteConfig().get_location()
        sfx_cmd = (
            "/apps/silhouette/Silhouette-2023.5/sfxcmd"
            if location == "chennai"
            else "/cold/pipeline/apps/silhouette/Silhouette-2023.5/sfxcmd"
        )
        merged_args = output_paths.copy()
        merged_args.update(nuke_file_path)
        output_paths_json = json.dumps(merged_args)
        frame_range = f"{start_frame}-{end_frame}"
        os.chmod(project_path, 0o777)
        silhouette_cmd = [
            sfx_cmd,
            project_path,
            "-range",
            frame_range,
            "-render",
            "0",
            "-args",
            output_paths_json,
            "-script",
            script_path,
            "-all",
        ]

        render_process = subprocess.Popen(
            silhouette_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        stdout, stderr = render_process.communicate()
        if render_process.returncode == 0:
            print("Render command executed successfully")
        else:
            print(f"Command failed with return code {render_process.returncode}")
            print(f"Error output: {stderr}")

        try:
            from silhouette_package import feather_removal

            feather_removal.remove_all_feathers_from_path(nmb_script_path)
        except Exception as e:
            print(f"❌ Feather removal failed: {e}")

        batch_name = os.path.basename(fx.activeProject().path).split(".")[0]
        job_name = fx.activeProject().path + "_nmb_render"
        job_id = self.submit_render(
            batch_name=batch_name,
            job_name=job_name,
            pool="ingestion_pool",
            frames=f"{start_frame}-{end_frame}",
            output="-all",
            department="Roto",
            scene_file=project_path,
        )
        self.job_id = job_id

    def nmb_render_deadline(self):
        for session in fx.activeProject().sessions:
            for output in session.outputs:
                start_frame = session.outputRange[0]
                end_frame = session.outputRange[1]
                frames = f"{int(start_frame)}-{int(end_frame)}"
                self.project = self.set_show()
                project = fx.activeProject().path
                p = os.path.dirname(project)
                self.input_path = p
                tk = sgtk.sgtk_from_path(p)
                context = tk.context_from_path(p)
                batch_name_mani = (
                    str(self.current_user) + "_" + str(fx.activeProject().name)
                )

                print("batch_name_mani@@@@@@@@ :", batch_name_mani)
                job_id = submit_render(
                    session,
                    batch_name=batch_name_mani,
                    job_name=f"{fx.activeProject().name}_{session.label}_{output.label}",
                    group="",
                    pool="ingestion_pool",
                    frames=frames,
                    output=output.label,
                    # department="Roto",
                )
                print(job_id)
        self.set_value_nkt()

    def check_matte_count(self, **args):
        if os.getlogin() == "chandru":
            data = self.template_input_data
            mate_list = list(data.get("MB_matte_path", {}).values())
            print("_mb_folder_path", mate_list)

            mate_list = [str(value) for value in mate_list]
            print("testing_________", len(mate_list))
            print("testing_____________________", mate_list)
            if len(mate_list) > 1:
                self.placeholders["mb_folder_template"] = ""

    def create_version_data(self, **args):
        self.fetch_data_structure()

    def mb_path_list(self):
        # print(self.mb_folder_path)

        # if self.mb_folder_path == []:
        data = self.template_input_data
        self.mb_folder_path = list(data.get("MB_matte_path", {}).values())
        print("_mb_folder_path", self.mb_folder_path)

        mate_list = [str(value) for value in self.mb_folder_path]
        print("mate_list", mate_list)
        print("______++++++", ", ".join(mate_list))
        return ",".join(mate_list)

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

    def get_connected_output_nodes(self, node, visited=None):
        if visited is None:
            visited = set()

        if node in visited:
            return []

        visited.add(node)
        output_nodes = []

        for output_port in node.outputs:
            targets = output_port.targets  # List of ports it's connected to

            for target in targets:
                dest_node = target.node
                output_nodes.append(dest_node)
                return dest_node

    def get_layer_dict(self):
        mate_layer = {}
        for session in fx.activeProject().sessions:
            output_label = []
            for output in session.outputs:
                roto_node = self.get_connected_roto_node(output)
                layers = roto_node.children
                top_layername = layers[0].label
                mate_layer[output.properties["path"].value] = top_layername
        return mate_layer

    def _inject_root_format(self, nk_path):
        """Prepend a root format line to a Silhouette-exported shape .nk"""
        # resolution string like "4312x1806" from source plate folder
        try:
            resolution = os.path.basename(os.path.dirname(self.full_source_path))
            w, h = resolution.split("x")
            w, h = int(w), int(h)
        except Exception as e:
            print("[_inject_root_format] could not parse resolution: {}".format(e))
            return

        fmt_line = 'root {{\n format "{w} {h} 0 0 {w} {h} 1 roto_fmt"\n}}\n'.format(
            w=w, h=h
        )

        try:
            with open(nk_path, "r") as f:
                content = f.read()
            with open(nk_path, "w") as f:
                f.write(fmt_line + content)
            print("[_inject_root_format] set {}x{} in {}".format(w, h, nk_path))
        except Exception as e:
            print("[_inject_root_format] write failed: {}".format(e))

    def set_value_nkt(
        self,
        input_template_path=None,
        name=None,
        use_packed=False,
        force_shape=False,
        **args,
    ):
        deadline_render = True
        layer_path = None
        additional_value = None
        self.placeholders["extension"] = "exr"
        start_frame, end_frame = self.get_active_session_work_range()
        full_frame = str(start_frame) + "-" + str(end_frame)
        self.placeholders["frame_range"] = full_frame
        print(self.placeholders)
        exr_path_color_overlay = self.apply_placeholders(
            self.placeholders["exr_path"], self.placeholders
        )
        color_overlay_path = os.path.splitext(
            os.path.splitext(exr_path_color_overlay)[0]
        )[0]
        write_path = self.placeholders["write_node_path"]
        write_path = self.out_path + self.apply_placeholders(
            write_path, self.placeholders
        )
        project = fx.activeProject()
        for i in project.sources:
            source_file_name = i.properties["path"].getValue()
            frame_range_match = re.search(r"\[(\d+)-(\d+)\]", source_file_name)

            if frame_range_match:
                start_frame = int(frame_range_match.group(1))
                end_frame = int(frame_range_match.group(2))
                digit_count = len(frame_range_match.group(2))
                formatted_path = re.sub(
                    r"\[\d+-\d+\]", f"%0{digit_count}d", source_file_name
                )
                if input_template_path is None:
                    input_template_path = self.placeholders[
                        "nuke_coloroverlay_template"
                    ]
                    output_template_path = os.path.join(
                        self.get_tmp_path(), os.path.basename(write_path) + ".nk"
                    )
                else:
                    deadline_render = False
                    input_template_path = input_template_path
                    output_template_path = os.path.join(
                        self.get_tmp_path(),
                        os.path.basename(input_template_path) + ".nk",
                    )

                input_path = formatted_path
                start_frame = self.render_ui.startFrameInput.text()
                end_frame = self.render_ui.endFrameInput.text()
                print("color_overlay", color_overlay_path)
                yaml_data = self.template_input_data
                startframe = start_frame
                endframe = end_frame
                # if self.packed_layer_dict:
                #     mate_list_path = ",".join(self.packed_layer_dict.keys())
                # else:
                #     mate_list_path = self.mb_path_list()
                if name is None:
                    name = "roto_package"
                else:
                    name = name

                bake = True
                if self.placeholders.get("chunk"):
                    chunk = int(self.placeholders.get("chunk"))
                else:
                    if str(write_path).endswith(".mov"):
                        chunk = int(int(end_frame) + int(start_frame) + 1)
                    else:
                        chunk = int(int(end_frame) / int(start_frame) + 1)

                try:
                    if "mate_snippet" in self.placeholders:
                        additional_value = self.placeholders["mate_snippet"]

                except:
                    pass
                if "additional_write_path" in self.placeholders:
                    additional_value = {}
                    for i in self.placeholders.get("additional_write_path"):
                        additional_value[i] = self.out_path + self.apply_placeholders(
                            self.placeholders[i], self.placeholders
                        )
                        print("additional_value", additional_value)
                if "NMB" in self.placeholders.get("mb_nmb", []):
                    nmb_paths = self._build_nmb_additional_paths()
                    if nmb_paths:
                        if additional_value is None:
                            additional_value = {}
                        elif not isinstance(additional_value, dict):
                            # mate_snippet might be a raw string — don't clobber it
                            additional_value = {"mate_snippet": additional_value}
                        additional_value["nmb_path"] = nmb_paths
                        print(
                            "[set_value_nkt] added nmb_path to additional_value:",
                            nmb_paths,
                        )

                layer_path = self.get_layer_dict()

                addition_value = self.mb_folder_path
                if "dst" in self.project_name:
                    resolution = None
                else:
                    resolution = os.path.basename(
                        os.path.dirname(self.full_source_path)
                    )

                if self.placeholders.get("nuke_global_coloroverlay_template"):
                    if self.render_ui.global_checkbox.isChecked():
                        chosen = "global"
                    elif self.render_ui.shape_checkbox.isChecked():
                        chosen = "shape"
                    else:
                        chosen = None

                print("_+__+_+_++++chosen______________", chosen)

                # decide which dict to send
                if chosen == "shape" and self.packed_layer_dict and not force_shape:
                    layer_dict_to_use = self.packed_layer_dict
                    mate_list_path = ",".join(self.packed_layer_dict.keys())
                else:
                    if self.placeholders.get("nuke_global_coloroverlay_template"):
                        caller_name = inspect.stack()[1].function
                        if caller_name != "save_tmp_coloroverlay":
                            input_template_path = self.placeholders[
                                "nuke_global_coloroverlay_template"
                            ]
                    layer_dict_to_use = self.layer_dict
                    mate_list_path = self.mb_path_list()

                    # Only use layer_dict.keys() when we are forcing shape mode
                    if force_shape:
                        mate_list_path = ",".join(self.layer_dict.keys())
                    else:
                        mate_list_path = (
                            self.mb_path_list()
                        )  # ← Original behavior restored

                py_template = self.create_roto_nkt_file(
                    input_template_path,
                    output_template_path,
                    input_path,
                    write_path,
                    startframe,
                    endframe,
                    mate_list_path,
                    name,
                    layer_dict_to_use,
                    additional_value,
                    resolution,
                    layer_path,
                    bake,
                )
                if self.job_id is None:
                    self.job_id = ""

                if getattr(self, "layer_job_ids", None):
                    dependency = ",".join(self.layer_job_ids)
                else:
                    dependency = self.job_id if self.job_id else ""
                print("[set_value_nkt] dependency = {}".format(dependency))

                if deadline_render:
                    job_id = self.create_nuke_job(
                        name,
                        py_template,
                        os.path.basename(write_path) + ".nk",
                        startframe,
                        endframe,
                        "",
                        chunk,
                        dependency,
                        deadline_render,
                    )
                    if job_id:
                        self.job_id = job_id  # ✅ next task depends on this
                        print(f"[set_value_nkt] ✅ submitted job_id={self.job_id}")
                else:
                    self.create_nuke_job(
                        name,
                        py_template,
                        os.path.basename(input_template_path) + ".nk",
                        startframe,
                        endframe,
                        "",
                        chunk,
                        self.job_id,
                        deadline_render,
                    )
                    return os.path.basename(input_template_path) + ".nk"

    def create_nuke_job(
        self,
        name,
        proxy_template,
        nuke_template,
        start_frame,
        end_frame,
        job_name="_proxy_action",
        chunk=None,
        dependent="",
        deadline_render=True,
    ):
        if chunk is None:
            chunk = int(end_frame) / int(start_frame) + 1
            chunk = int(chunk)

        tmp_path = self.get_tmp_path()
        if not os.path.exists(tmp_path):
            os.makedirs(tmp_path)

        log_path = "{}/{}_nuke_job.log".format(tmp_path, name)
        logging.basicConfig(
            filename=log_path, level=logging.DEBUG, format="%(asctime)s %(message)s"
        )

        nuke_path = self.yaml_data.get(
            "nuke_version_path", "/apps/nuke/Nuke12.2v7/Nuke12.2"
        )
        nuke_home = os.path.dirname(nuke_path)

        script = """#!/bin/bash
                export PYTHONHOME={}
                export PYTHONPATH=$PYTHONPATH:'/tools/packages/nkt_api/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2:/tools/packages/nkt_api/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2/python'
                {} -t "{}"
                """.format(nuke_home, nuke_path, proxy_template)
        # script = """#!/bin/bash
        # export PYTHONHOME=/apps/nuke/Nuke12.2v7
        # export PYTHONPATH=$PYTHONPATH:'/tools/packages/nkt_api/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2:/tools/packages/nkt_api/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2/python'
        # /apps/nuke/Nuke12.2v7/Nuke12.2 -t "{}"
        # """.format(proxy_template)

        script_path = "{}/{}_run_nuke.sh".format(tmp_path, name)
        with open(script_path, "w") as file:
            file.write(script)

        subprocess.call(["chmod", "+x", script_path])
        logging.debug("Running script: {}".format(script))

        try:
            result = subprocess.Popen(
                [script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = result.communicate()
            logging.info("Output: {}".format(result.stdout))
            logging.error("Error: {}".format(result.stderr))
        except subprocess.CalledProcessError as e:
            logging.error("Error running Nuke script: {}".format(e))
            logging.error("Output: {}".format(e.stdout))
            logging.error("Error: {}".format(e.stderr))
            return

        logging.debug("Nuke script ran successfully.")
        print(deadline_render)
        if deadline_render is True:
            print("run_deadline_render" * 100)
            try:
                # if os.getlogin() == "chandru":
                #         plugin_details, job_details = get_info_txt(
                #             "{}_{}".format(name, job_name),
                #             name,
                #             "2d_pool",
                #             "2d_group",
                #             start_frame,
                #             end_frame,
                #             12.2,
                #             chunk,
                #             dependent,
                #             department="Roto",
                #             plugin="CommandLine"
                #         )
                # else:

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
                    department="Roto",
                )
                logging.debug("Plugin details: {}".format(plugin_details))
                logging.debug("Job details: {}".format(job_details))
            except Exception as e:
                logging.error("Error getting job details: {}".format(e))
                return

            time.sleep(4)

            try:
                job_id = submit_to_deadline(
                    plugin_details, job_details, "{}/{}".format(tmp_path, nuke_template)
                )
                logging.info("Template job created with ID: {}".format(job_id))
            except Exception as e:
                logging.error("Error submitting job to Deadline: {}".format(e))
                return

            return job_id

    def create_roto_nkt_file(
        self,
        input_template_path,
        output_template_path,
        input_path,
        write_path,
        startframe,
        endframe,
        mate_list_path,
        name,
        layer_dict,
        additional_value,
        resolution,
        layer_path,
        bake,
    ):
        create_proxy_template = """
import sys
sys.path.append("/tools/packages/nkt_api/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2/python")
from processors import roto_coloroverlay_processor
input_template_path="{input_template_path}"
output_template_path="{output_template_path}"
startframe={startframe}
endframe={endframe}
mate_list_path = "{mate_list_path}"
write_path="{write_path}"
input_path="{input_path}"
layer_path="{layer_path}"
addition_value="{additional_value}"
resolution="{resolution}"
layer_dict="{layer_dict}"
roto_coloroverlay_processor(input_template_path,output_template_path,input_path,write_path,startframe,endframe,mate_list_path,layer_dict,addition_value,resolution,layer_path,bake={bake})
        """.format(
            input_template_path=input_template_path,
            output_template_path=output_template_path,
            input_path=input_path,
            write_path=write_path,
            startframe=startframe,
            endframe=endframe,
            mate_list_path=mate_list_path,
            layer_dict=layer_dict,
            additional_value=additional_value,
            resolution=resolution,
            layer_path=layer_path,
            bake=bake,
        )
        mov_name = name.rsplit(".", 1)[0]
        tmp_path = self.get_tmp_path()

        if not os.path.exists(tmp_path):
            os.makedirs(tmp_path)

        proxy_template = "{}/{}.py".format(tmp_path, mov_name)
        print(proxy_template)

        with open(proxy_template, "w") as cf:
            cf.write(create_proxy_template)

        return proxy_template

    def copying_render_files(self, src_path, dst_path):
        """
        Copies render files from a source pattern to a destination pattern by generating
        a temporary Python script that handles the file copying process.

        This method creates a temporary script that uses multithreading to copy files
        matching the source pattern to the destination pattern, preserving the frame
        numbering and directory structure. It submits the script as a job to the
        ingestion pool.

        Args:
            src_path (str): The source file pattern, including the frame number placeholder.
            dst_path (str): The destination file pattern, including the frame number placeholder.

        Returns:
            None

        Raises:
            ValueError: If the source or destination pattern is invalid.
        """
        # tmp_path=os.environ['HOME']+"/tmp/roto_packaging/"
        tmp_path = self.get_tmp_path()
        file_path = os.path.join(tmp_path, "file_copy_script.py")
        content = """import os
import shutil
import glob
from concurrent.futures import ThreadPoolExecutor
import argparse
import re

def parse_pattern(pattern):
    directory = os.path.dirname(pattern)
    filename = os.path.basename(pattern)
    match = re.match(r'(.*)%(\d+)d(.*)$', filename)
    if match:
        prefix, padding, suffix = match.groups()
        padding = int(padding)
    else:
        raise ValueError("Invalid pattern: frame number placeholder (%Nd) not found")
    return directory, prefix, padding, suffix

def copy_file(src_file, src_info, dest_info):
    src_dir, src_prefix, src_padding, src_suffix = src_info
    dest_dir, dest_prefix, dest_padding, dest_suffix = dest_info
    frame_number_match = re.search(r'(\d+)', src_file[len(src_dir) + len(src_prefix):])
    if frame_number_match:
        frame_number = int(frame_number_match.group(1))
    else:
        raise ValueError(f"Unable to extract frame number from {{src_file}}")
    dest_file = os.path.join(dest_dir, f"{{dest_prefix}}{{frame_number:0{{dest_padding}}d}}{{dest_suffix}}")

    os.makedirs(os.path.dirname(dest_file), exist_ok=True)
    shutil.copy2(src_file, dest_file)
    print(f"Copied: {{src_file}} -> {{dest_file}}")

def main(source_pattern, dest_pattern):
    src_info = parse_pattern(source_pattern)
    dest_info = parse_pattern(dest_pattern)
    src_dir, src_prefix, src_padding, src_suffix = src_info
    source_files = glob.glob(os.path.join(src_dir, f"{{src_prefix}}*{{src_suffix}}"))

    with ThreadPoolExecutor() as executor:
        executor.map(lambda f: copy_file(f, src_info, dest_info), source_files)

if __name__ == "__main__":
    main({0!r}, {1!r})
    """
        formatted_content = content.format(src_path, dst_path)
        base_name_dst = os.path.basename(dst_path)

        with open(file_path, "w") as file:
            file.write(formatted_content)

        frame_len = len(os.listdir(os.path.dirname(src_path)))
        Frames = "1-{}".format(frame_len)
        job_id = create_python_job(
            job_name=base_name_dst + "copy_render_frames",
            python_job_command=file_path,
            pool="2d_pool",
            # Frames=Frames,
            department="Roto",
        )
        return job_id

    def rendering_proxy_mov(self, **args):
        """
        Creates a proxy MOV file based on the rendering job.

        This method adds the job ID and slate note to the provided arguments and then
        invokes a function to create a proxy MOV file. The job ID for this action
        is stored for further reference.

        Args:
            **args: Keyword arguments containing additional parameters for the proxy creation.

        Returns:
            None
        """
        project = fx.activeProject()
        for i in project.sources:
            source_file_name = i.properties["path"].getValue()
            frame_range_match = re.search(r"\[(\d+)-(\d+)\]", source_file_name)

            if frame_range_match:
                start_frame = int(frame_range_match.group(1))
                end_frame = int(frame_range_match.group(2))
                digit_count = len(frame_range_match.group(2))
                formatted_path = re.sub(
                    r"\[\d+-\d+\]", f"%0{digit_count}d", source_file_name
                )

        print(start_frame, end_frame)
        args["startframe"] = start_frame
        args["endframe"] = end_frame
        args["job_id"] = self.job_id
        args["input_path"] = formatted_path
        args["overlay_render_files"] = self.template_input_data
        # args['overlay_render_files'] = self.overlay_render_files

        mov_job_id = create_roto_proxy_action_file(**args)
        if mov_job_id:
            self.job_id = mov_job_id
        else:
            self.job_id = ""

    def creating_sg_version(self, **args):
        """
        Creates a version entry in Shotgun for the rendered output.

        This method retrieves project and context information, registers the rendered
        EXR file with Shotgun, and submits a job to create a version file. It captures
        metadata such as project name, shot name, and user information for the version entry.

        Args:
            **args: Keyword arguments containing necessary parameters for version creation,
                    including 'exr_path'.

        Returns:
            None

        Raises:
            KeyError: If required keys are missing in the 'args' dictionary.
            sgtk.exceptions.SgtkError: If there are issues registering the publish in Shotgun.
        """
        project = nuke.root().name()
        tk = sgtk.sgtk_from_path(str(project))
        context = tk.context_from_path(project)
        template = tk.template_from_path(project)
        fields = template.get_fields(project)
        publish_name = fields["name"]
        version_number = fields.get("version")
        exr_path = args["exr_path"]
        update_data = {"sg_filepath": exr_path}
        publish_data = sgtk.util.register_publish(
            tk,
            context,
            exr_path,
            publish_name,
            version_number,
            published_file_type="Rendered Image",
            sg_fields=update_data,
        )

        args["project_name"] = context.project["name"]
        args["shot_name"] = context.entity["name"]
        args["published"] = publish_data["id"]
        args["description"] = self.version_data
        args["sg_username"] = str(os.getlogin().replace(".", "-"))
        args["task_name"] = context.step["name"]
        upload_action = create_proxy_sg_version_file(**args)
        version_job_id = create_python_job(
            job_name=os.path.basename(nuke.root().name()) + "version_sg",
            python_job_command=upload_action,
            dependent=self.job_id,
            pool="ingestion_pool",
        )
        if version_job_id:
            self.job_id = version_job_id
        else:
            self.job_id = ""

    def save_nuke_file(self, nuke_file_path):
        current_script_path = nuke.root().name()
        shutil.copy(current_script_path, nuke_file_path)

    #     def expand_matte_node(self, placeholders):
    #     mattes_value = placeholders.get("mattes")
    #     if mattes_value is None:
    #         return []
    #     if isinstance(mattes_value, str):
    #         matte_names = [mattes_value]
    #     else:
    #         matte_names = list(mattes_value)

    #     shot = placeholders.get("shot", "shot")
    #     plate = placeholders.get("sg_plate_name", "plate")
    #     version = placeholders.get("out_version", "v001")

    #     result = []
    #     if len(matte_names) == 1 and matte_names[0] == "matte":
    #         # single matte
    #         file_pattern = f"{shot}_roto_{plate}_{matte_names[0]}_{version}.%04d.exr"
    #         result.append(file_pattern)
    #     else:
    #         # multiple mattes
    #         for m in matte_names:
    #             result.append({m: [f"{shot}_roto_{plate}_{m}_{version}.%04d.exr"]})
    #     return result

    # def preprocess_structure(self, struct, placeholders):
    #     if isinstance(struct, list):
    #         new_list = []
    #         for item in struct:
    #             if isinstance(item, dict):
    #                 for k, v in item.items():
    #                     if isinstance(v, dict) and v.get("__expand_mattes__"):
    #                         expanded = self.expand_matte_node(placeholders)
    #                         new_list.append({k: expanded})
    #                     else:
    #                         new_list.append({k: self.preprocess_structure(v, placeholders)})
    #             else:
    #                 new_list.append(self.preprocess_structure(item, placeholders))
    #         return new_list
    #     elif isinstance(struct, dict):
    #         return {k: self.preprocess_structure(v, placeholders) for k, v in struct.items()}
    #     else:
    #         return struct

    def save_tmp_coloroverlay(self, **args):
        print("run__________________ [client shape script]")

        nuke_file_path = self.placeholders["nuke_color_overlay_file"]
        nuke_file_path = self.out_path + self.apply_placeholders(
            nuke_file_path, self.placeholders
        )
        print("nuke_file_path_+_+++++", nuke_file_path)

        # ✅ bake a SHAPE-based client script (no deadline submit)
        client_template = self.placeholders["nuke_coloroverlay_template"]
        client_nk_name = self.set_value_nkt(
            input_template_path=client_template,
            name="client_shape",
            force_shape=True,  # ← force shapes, not matte
        )

        if not client_nk_name:
            print("[save_tmp_coloroverlay] client script not generated")
            return

        current_script_path = os.path.join(self.get_tmp_path(), client_nk_name)

        if not os.path.exists(current_script_path):
            print(
                "[save_tmp_coloroverlay]  baked client nk missing: {}".format(
                    current_script_path
                )
            )
            return

        shutil.copy(current_script_path, nuke_file_path)
        print(
            "[save_tmp_coloroverlay] shape client script -> {}".format(nuke_file_path)
        )

    def set_value_nkt_sequence(self, templates=None, **args):
        """
        Loops through templates list and submits each as a chained deadline job.
        Each job depends on the previous one finishing first.
        """
        if not templates:
            print("[set_value_nkt_sequence] No templates provided")
            return

        previous_job_id = self.job_id if self.job_id else ""

        for entry in templates:
            input_template_path = entry.get("input_template_path", None)
            name = entry.get("name", None)
            print(
                f"[set_value_nkt_sequence] Submitting: {name}  dependent on: '{previous_job_id}'"
            )

            job_id = self.create_nuke_job_sequence(
                input_template_path=input_template_path,
                name=name,
                dependent_job_id=previous_job_id,  # ✅ pass explicitly
                **args,
            )

            if job_id:
                previous_job_id = job_id
                self.job_id = job_id
                print(
                    f"[set_value_nkt_sequence] ✅ job_id={job_id}, next job will depend on this"
                )
            else:
                print(
                    f"[set_value_nkt_sequence] ⚠️ No job_id returned for '{name}' — dependent chain may be broken"
                )

    def create_nuke_job_sequence(
        self, input_template_path=None, name=None, dependent_job_id="", **args
    ):
        """
        Builds and submits a single nuke job to deadline.
        Uses dependent_job_id (passed explicitly) as dependency.
        Returns new job_id for chaining.
        """
        self.placeholders["extension"] = "exr"
        start_frame, end_frame = self.get_active_session_work_range()
        self.placeholders["frame_range"] = str(start_frame) + "-" + str(end_frame)

        write_path = self.placeholders["write_node_path"]
        write_path = self.out_path + self.apply_placeholders(
            write_path, self.placeholders
        )

        project = fx.activeProject()
        for i in project.sources:
            source_file_name = i.properties["path"].getValue()
            frame_range_match = re.search(r"\[(\d+)-(\d+)\]", source_file_name)

            if frame_range_match:
                digit_count = len(frame_range_match.group(2))
                formatted_path = re.sub(
                    r"\[\d+-\d+\]", f"%0{digit_count}d", source_file_name
                )

                tmp_path = self.get_tmp_path()

                if input_template_path is None:
                    input_template_path = self.placeholders[
                        "nuke_coloroverlay_template"
                    ]
                    nuke_template_name = os.path.basename(write_path) + ".nk"
                else:
                    # ✅ strip existing .nk to avoid double extension
                    base_name = os.path.splitext(os.path.basename(input_template_path))[
                        0
                    ]
                    nuke_template_name = base_name + ".nk"

                output_template_path = os.path.join(tmp_path, nuke_template_name)

                start_frame = self.render_ui.startFrameInput.text()
                end_frame = self.render_ui.endFrameInput.text()
                chunk = int(int(end_frame) - int(start_frame) + 1)
                if self.packed_layer_dict:
                    mate_list_path = ",".join(self.packed_layer_dict.keys())
                else:
                    mate_list_path = self.mb_path_list()

                if name is None:
                    name = "roto_package_seq"

                # additional_value = None
                # if "additional_write_path" in self.placeholders:
                #     additional_value = {}
                #     for k in self.placeholders.get("additional_write_path"):
                #         additional_value[k] = self.out_path + self.apply_placeholders(
                #             self.placeholders[k], self.placeholders
                #         )

                additional_value = None
                if "additional_write_path" in self.placeholders:
                    additional_value = {}
                    for k in self.placeholders.get("additional_write_path"):
                        additional_value[k] = self.out_path + self.apply_placeholders(
                            self.placeholders[k], self.placeholders
                        )

                # Add notes from UI to additional_value safely
                try:
                    if hasattr(self, "version_data") and self.version_data:
                        if additional_value is None:
                            additional_value = {}
                        additional_value["notes"] = self.version_data
                        print(
                            "[create_nuke_job_sequence] INFO: notes added to additional_value: {}".format(
                                self.version_data
                            )
                        )
                except Exception as e:
                    print(
                        "[create_nuke_job_sequence] INFO: Could not add notes - {}".format(
                            e
                        )
                    )

                layer_path = self.get_layer_dict()
                resolution = (
                    None
                    if "dst" in self.project_name
                    else os.path.basename(os.path.dirname(self.full_source_path))
                )
                slate_frame = int(start_frame) - 1

                py_template = self.create_roto_nkt_file(
                    input_template_path,
                    output_template_path,
                    formatted_path,
                    write_path,
                    start_frame,
                    end_frame,
                    mate_list_path,
                    name,
                    self.layer_dict,
                    additional_value,
                    resolution,
                    layer_path,
                    True,
                )

                print(
                    f"[create_nuke_job_sequence] submitting '{name}' → nuke_template: {nuke_template_name}"
                )
                print(
                    f"[create_nuke_job_sequence] dependent on job_id: '{dependent_job_id}'"
                )

                # ✅ create_nuke_job runs nuke locally first, THEN submits to deadline
                # ✅ NO pre-check here — nuke hasn't run yet at this point
                job_id = self.create_nuke_job(
                    name,
                    py_template,
                    nuke_template_name,
                    slate_frame,
                    slate_frame,
                    "",
                    1,
                    dependent_job_id,  # ✅ explicit dependency passed in
                    True,
                )

                print(
                    f"[create_nuke_job_sequence] create_nuke_job returned job_id='{job_id}'"
                )
                return job_id

        return None

    def render(self):
        """
        Renders the current Nuke script and uploads the necessary tasks.

        This method initializes a progress task to track the upload process, copies the
        current Nuke script to a designated path, and processes a series of render tasks.
        Each task is executed based on its associated function name and arguments, with
        progress updates communicated through the progress task.

        Raises:
            FileNotFoundError: If the current script path is invalid or the copy fails.
            AttributeError: If a function specified in the render tasks does not exist.
        """
        render_tasks = self.placeholders.get("render", [])
        total_tasks = len(render_tasks)

        progress_dialog = QtWidgets.QProgressDialog(
            "Rendering...", "Cancel", 0, total_tasks, None
        )
        progress_dialog.setWindowTitle("Render Progress")
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setAutoClose(True)
        progress_dialog.setValue(0)

        for index, (func_name, args) in enumerate(render_tasks.items()):
            if progress_dialog.wasCanceled():
                break

            func = getattr(self, func_name, None)
            print("____________________________func__", func)
            if func:
                func(**args)

            progress_dialog.setValue(index + 1)
            QtWidgets.QApplication.processEvents()

        self.render_ui.close()

    def change_nuke_file(self, **args):
        nuke_file_path = self.placeholders["nuke_color_overlay_file"]
        nuke_file_path = self.out_path + self.apply_placeholders(
            nuke_file_path, self.placeholders
        )
        print(nuke_file_path)
        input_template = self.placeholders["nuke_client_file"]
        name = "client_file"
        client_file_path = self.set_value_nkt(input_template, name)
        current_script_path = os.path.join(self.get_tmp_path(), client_file_path)
        nuke_file_path = self.placeholders["nuke_color_overlay_file"]
        nuke_file_path = self.out_path + self.apply_placeholders(
            nuke_file_path, self.placeholders
        )
        print("nuke_file_path_+_+++++", nuke_file_path)
        shutil.copy(current_script_path, nuke_file_path)

    def replace_placeholders(self, text, placeholders):
        """
        Replaces placeholders in a given text with corresponding values from a dictionary.

        Args:
            text (str): The input string containing placeholders in the format {key}.
            placeholders (dict): A dictionary mapping keys to their replacement values.

        Returns:
            str: The input text with all placeholders replaced by their corresponding values.

        Example:
            >>> replace_placeholders("Hello, {name}!", {"name": "Alice"})
            "Hello, Alice!"
        """
        for key, value in placeholders.items():
            text = text.replace(f"{{{key}}}", str(value))
        return text

    def find_upstream_read_node(self, node):
        """
        Finds the first upstream 'Read' node for a given node in the Nuke node graph.

        This method performs a breadth-first search starting from the specified node,
        traversing its inputs to locate the nearest 'Read' node.

        Args:
            node (nuke.Node): The starting node from which to search upstream.

        Returns:
            nuke.Node: The first encountered 'Read' node, or None if no such node exists.

        Example:
            >>> read_node = find_upstream_read_node(some_node)
            >>> if read_node:
            ...     print(f"Found Read node: {read_node.name()}")
        """
        queue, visited = [node], set()

        while queue:
            current_node = queue.pop(0)
            if current_node in visited:
                continue
            visited.add(current_node)
            if current_node.Class() == "Read":
                return current_node
            queue.extend(
                current_node.input(i)
                for i in range(current_node.inputs())
                if current_node.input(i)
            )

    def get_fields_from_path(self, project, template_name=None, seq=None):
        project = project.replace("/brahmos", "")
        tk = sgtk.sgtk_from_path(project)
        if seq is not None:
            project = project.replace(seq, "%04d")

        context = tk.context_from_path(project)

        if not context:
            return

        template = tk.templates[template_name]
        fields = template.get_fields(project)

        return fields

    # def add_values_to_shot(self, data, new_values):
    #     """
    #     Update the shot data within the department structure by adding new values to existing lists.

    #     Args:
    #         data (list): The department structure data.
    #         new_values (list): New values to add to each shot's data.

    #     Returns:
    #         list: Updated department structure.
    #     """
    #     print("Initial data structure:", data)  # Debugging print statement

    #     for item in data:
    #         for out_version, shot_data in item.items():
    #             print("Out Version: {0}, Shot Data: {1}".format(out_version, shot_data))

    #             for shot in shot_data:
    #                 print("Shot data before update: {0}".format(shot))
    #                 if isinstance(shot, dict):  # If the shot is a dictionary
    #                     for key, value in shot.items():
    #                         if isinstance(value, list):  # If value is a list, extend it
    #                             value.extend(new_values)
    #                             print("Updated shot data (dict): {0}".format(shot))
    #                         else:
    #                             print("Skipping non-list value in dict: {0}".format(value))
    #                 elif isinstance(shot, list):  # If the shot is a list itself, extend it
    #                     shot.extend(new_values)
    #                     print("Updated shot data (list): {0}".format(shot))
    #                 else:
    #                     print("Skipping non-list shot data: {0}".format(shot))

    #     return data

    # def _add_to_specific_folder(self, shot_contents, new_value, folder_path):
    #     """
    #     Add value to a specific folder path within the shot structure.

    #     Args:
    #         shot_contents (list): The current shot contents (nested list/dict structure).
    #         new_value (str|dict): The new item (file/folder) to insert.
    #         folder_path (list): Path of folders where the item should be placed.
    #                             Example: ["script", "Nuke"]
    #     """

    #     if not folder_path:
    #         # No path given → append to main
    #         shot_contents.append(new_value)
    #         return

    #     current_level = folder_path[0]

    #     # Look for dict with this level (e.g. {"script": [...]})
    #     target_dict = None
    #     for item in shot_contents:
    #         if isinstance(item, dict) and current_level in item:
    #             target_dict = item
    #             break

    #     # If not found, create it
    #     if target_dict is None:
    #         target_dict = {current_level: []}
    #         shot_contents.append(target_dict)

    #     # Recurse into the next level
    #     if len(folder_path) > 1:
    #         next_contents = target_dict[current_level]
    #         if not isinstance(next_contents, list):
    #             target_dict[current_level] = []
    #             next_contents = target_dict[current_level]
    #         self._add_to_specific_folder(next_contents, new_value, folder_path[1:])
    #     else:
    #         # Last level → just append here
    #         if isinstance(target_dict[current_level], list):
    #             target_dict[current_level].append(new_value)
    #         else:
    #             target_dict[current_level] = [new_value]

    def _add_to_specific_folder(self, shot_contents, new_value, folder_path):
        if not folder_path:
            shot_contents.append(new_value)
            return

        current_level = folder_path[0]

        target_dict = None
        matched_key = current_level

        for item in shot_contents:
            if isinstance(item, dict):
                for k in item:
                    if k == current_level:
                        target_dict = item
                        matched_key = k
                        break
                    # match unresolved template key by prefix before first {
                    if "{" in k:
                        k_prefix = k.split("{")[0]
                        cl_prefix = current_level.split("{")[0]
                        if k_prefix and k_prefix == cl_prefix:
                            target_dict = item
                            matched_key = k
                            break
                if target_dict is not None:
                    break

        if target_dict is None:
            target_dict = {current_level: []}
            shot_contents.append(target_dict)
            matched_key = current_level

        if len(folder_path) > 1:
            next_contents = target_dict[matched_key]
            if not isinstance(next_contents, list):
                target_dict[matched_key] = []
                next_contents = target_dict[matched_key]
            self._add_to_specific_folder(next_contents, new_value, folder_path[1:])
        else:
            if isinstance(target_dict[matched_key], list):
                target_dict[matched_key].append(new_value)
            else:
                target_dict[matched_key] = [new_value]

    def _determine_placement(self, value):
        """
        Analyze the value content to determine where it should be placed
        Based on your templates and YAML structure
        """
        matte_naming_convention = self.placeholders.get("matte_naming_convention")
        value_str = str(value)
        print("*" * 10, matte_naming_convention)

        # Check for nuke files (.nk extension)
        if value_str.endswith(".nk"):
            return "nuke"

        # Check for silhouette files (.sfx extension)
        if value_str.endswith(".sfx"):
            return "silhouette"

        # # Check for nuke-related patterns in filename
        # if '_roto*' in value_str and '.nk' in value_str:
        #     return "nuke"

        # Check for folder patterns (matteimage_ prefix indicates folder)
        if matte_naming_convention is not None:
            if value_str.startswith(matte_naming_convention):
                return "main"

        # Check if it's a dictionary (likely a folder structure)
        if isinstance(value, dict):
            return "main"

        # Default to main shot contents
        return "main"

    def _distribute_values(self, shot_contents, new_values, description=None):
        for new_value in new_values:
            placement_location = self._determine_placement(new_value)

            if placement_location == "main":
                matte_extend_path = self.placeholders.get("matte_extend_path")
                if matte_extend_path:
                    if isinstance(matte_extend_path, str):
                        matte_extend_path = [matte_extend_path]
                    elif isinstance(matte_extend_path, list):
                        matte_extend_path = list(matte_extend_path)  # shallow copy

                    # ✅ Build a local placeholder dict with THIS iteration's description
                    local_ph = dict(self.placeholders)
                    if description is not None:
                        local_ph["description"] = description

                    matte_extend_path = [
                        self.apply_placeholders(p, local_ph) for p in matte_extend_path
                    ]

                    navigate_path = (
                        matte_extend_path
                        if self.yaml_data.get("matte_path_changes")
                        else matte_extend_path[:1]
                    )

                    self._add_to_specific_folder(
                        shot_contents, new_value, navigate_path
                    )
                else:
                    shot_contents.append(new_value)

    def add_values_to_shot(self, data, new_values, descriptions=None):
        for item in data:
            for pkg_key, version_list in item.items():
                for version_dict in version_list:
                    for version, shot_list in version_dict.items():
                        for shot in shot_list:
                            if isinstance(shot, dict):
                                for shot_key, shot_contents in shot.items():
                                    if self.yaml_data.get("new_update"):
                                        # ✅ zip each value with its description
                                        if descriptions and len(descriptions) == len(
                                            new_values
                                        ):
                                            for value, desc in zip(
                                                new_values, descriptions
                                            ):
                                                self._distribute_values(
                                                    shot_contents, [value], desc
                                                )
                                        else:
                                            # fallback: no per-value description available
                                            self._distribute_values(
                                                shot_contents, new_values
                                            )
                                    else:
                                        if isinstance(shot_contents, list):
                                            shot_contents.extend(new_values)
        return data

    def run_mb_copy(self, **args):
        from handler.mb_nmb_handler import MbNmbHandler

        MbNmbHandler(self).run_mb_copy(**args)

    def run_nmb_render(self, **args):
        from handler.mb_nmb_handler import MbNmbHandler

        MbNmbHandler(self).run_nmb_render(**args)

    def process_paths(self, paths, placeholders, description_key):
        project_path = fx.activeProject().path
        project_name_fields = self.get_fields_from_path(
            os.path.dirname(project_path), "silhouette_shot_work"
        )
        project_field_name = project_name_fields["name"]
        print(project_field_name)
        s, e = self.get_active_session_work_range()
        frame_range = "%0" + str(len(str(e))) + "d"
        extension = "exr"
        roto_values = []
        descriptions = []
        base_path = self.out_path + self.placeholders["project_base_path"]
        actual_path = self.apply_placeholders(base_path, self.placeholders)

        for path in paths:
            print("_++++path_check", path)
            if "alpha" in os.path.basename(path):
                fields = self.get_fields_from_path(
                    path, "silhouette_shot_render_pub_stereo_alpha"
                )
            else:
                seq = path.split(".")[-2]
                fields = self.get_fields_from_path(
                    path, "silhouette_shot_render_pub_stereo", seq
                )

            self.placeholders["description"] = fields["name"].replace(
                project_field_name + "_", ""
            )
            self.matte_shape_bkp[self.placeholders["description"]] = (
                os.path.basename(path).split(".")[0] + ".nk"
            )

            # ✅ NEW - track every description
            description = self.placeholders["description"]
            if description not in descriptions:
                descriptions.append(description)
                self.placeholders["descriptions"] = description

            if "MB" in self.placeholders["mb_nmb"]:
                if description_key == "MB":
                    if "mb_folder_template" in self.placeholders:
                        mb_folder_path = self.placeholders["mb_folder_template"]

                        if mb_folder_path:
                            folder_template = {mb_folder_path: []}
                            folder_value = self.apply_placeholders(
                                folder_template, self.placeholders
                            )
                            # self.render_folder_dict[next(iter(folder_value))] = path
                            dict_key = (
                                description
                                if "{description}" not in mb_folder_path
                                else next(iter(folder_value))
                            )
                            self.render_folder_dict[dict_key] = path

                            # for multi-level paths (like tfs2), the folder already exists in YAML structure
                            matte_extend_path = self.placeholders.get(
                                "matte_extend_path", []
                            )
                            if len(matte_extend_path) <= 1:
                                if folder_value not in roto_values:
                                    roto_values.append(folder_value)
                            mb_actual_path = self.apply_placeholders(
                                base_path
                                + "/"
                                + mb_folder_path
                                + "/"
                                + mb_folder_path
                                + "."
                                + frame_range
                                + "."
                                + extension,
                                self.placeholders,
                            )
                            self.mb_folder_path.append(mb_actual_path)
                        else:
                            # mb_folder_template is "" so map description → path directly
                            self.render_folder_dict[description] = path
                            print(f"render_folder_dict[{description}] = {path}")

                    if "mb_nuke_file_template" in self.placeholders:
                        nuke_file_template = self.placeholders["mb_nuke_file_template"]
                        if self.yaml_data.get("new_update"):
                            mb_nuke_base_path = (
                                self.out_path
                                + self.placeholders["nuke_full_shpae_path"]
                            )
                            mb_nuke_actual_path = self.apply_placeholders(
                                mb_nuke_base_path, self.placeholders
                            )
                            file_value = self.apply_placeholders(
                                nuke_file_template, self.placeholders
                            )
                            self.mb_nuke_path[
                                fields["name"].replace(project_field_name + "_", "")
                            ] = os.path.join(mb_nuke_actual_path, file_value)
                        else:
                            file_value = self.apply_placeholders(
                                nuke_file_template, self.placeholders
                            )
                            self.mb_nuke_path[
                                fields["name"].replace(project_field_name + "_", "")
                            ] = os.path.join(actual_path, file_value)

                        if file_value not in roto_values:
                            roto_values.append(file_value)

            if "NMB" in self.placeholders["mb_nmb"]:
                file_value = ""
                if description_key == "NMB":
                    folder_template = {self.placeholders["nmb_folder_template"]: []}
                    folder_path = self.placeholders["nmb_folder_template"]
                    nuke_file_template = self.placeholders.get("nmb_nuke_file_template")
                    if nuke_file_template is not None:
                        file_value = self.apply_placeholders(
                            nuke_file_template, self.placeholders
                        )
                    base_path = self.out_path + self.placeholders["project_base_path"]
                    actual_path = self.apply_placeholders(
                        base_path + "/" + folder_path + "/" + folder_path,
                        self.placeholders,
                    )
                    self.nmb_actual_path[
                        fields["name"].replace(project_field_name + "_", "")
                    ] = actual_path
                    folder_value = self.apply_placeholders(
                        folder_template, self.placeholders
                    )
                    if file_value != "":
                        if file_value not in roto_values:
                            roto_values.append(file_value)
                    if folder_value not in roto_values:
                        roto_values.append(folder_value)
                    mb_file_actual_path = self.apply_placeholders(
                        base_path, self.placeholders
                    )
                    if file_value != "":
                        self.nmb_nuke_path[
                            fields["name"].replace(project_field_name + "_", "")
                        ] = os.path.join(mb_file_actual_path, file_value)

        # self.placeholders["descriptions"] = descriptions

        return roto_values, descriptions

    # def expand_description_folders(self, structure, descriptions):
    #     """
    #     Recursively replace any dict key '{description}' with one
    #     entry per actual description name.

    #     Before:  [{'{description}': []}]
    #     After:   [{'mate1': []}, {'mate2': []}, ..., {'mate7': []}]
    #     """
    #     if isinstance(structure, list):
    #         expanded = []
    #         for item in structure:
    #             if isinstance(item, dict):
    #                 new_dict = {}
    #                 for k, v in item.items():
    #                     if k == "{description}":
    #                         # ✅ one folder per description instead of one overwritten folder
    #                         for desc in descriptions:
    #                             expanded.append(
    #                                 {
    #                                     desc: self.expand_description_folders(
    #                                         v, descriptions
    #                                     )
    #                                 }
    #                             )
    #                     else:
    #                         new_dict[k] = self.expand_description_folders(
    #                             v, descriptions
    #                         )
    #                 if new_dict:
    #                     expanded.append(new_dict)
    #             else:
    #                 expanded.append(item)
    #         return expanded
    #     if isinstance(structure, dict):
    #         return {
    #             k: self.expand_description_folders(v, descriptions)
    #             for k, v in structure.items()
    #         }
    #     return structure

    def expand_description_folders(self, structure, descriptions):
        if isinstance(structure, list):
            expanded = []
            for item in structure:
                if isinstance(item, dict):
                    new_dict = {}
                    for k, v in item.items():
                        if "{description}" in k:  # ← was: k == "{description}"
                            for desc in descriptions:
                                # resolve only {description} in the key, leave others for apply_placeholders
                                expanded_key = k.replace("{description}", desc)
                                expanded.append(
                                    {
                                        expanded_key: self.expand_description_folders(
                                            v, descriptions
                                        )
                                    }
                                )
                        else:
                            new_dict[k] = self.expand_description_folders(
                                v, descriptions
                            )
                    if new_dict:
                        expanded.append(new_dict)
                else:
                    expanded.append(item)
            return expanded
        if isinstance(structure, dict):
            return {
                k: self.expand_description_folders(v, descriptions)
                for k, v in structure.items()
            }
        return structure

    def get_description(self, department_structure):
        mb_paths = list(self.template_input_data.get("MB_matte_path", {}).values())
        nmb_paths = list(self.template_input_data.get("NMB_matte_path", {}).values())

        mb_roto_values, mb_descriptions = self.process_paths(
            mb_paths, self.placeholders, "MB"
        )

        dept_strcture = department_structure
        if mb_descriptions:
            dept_strcture = self.expand_description_folders(
                dept_strcture, mb_descriptions
            )

        department_structure = self.add_values_to_shot(
            dept_strcture, mb_roto_values, mb_descriptions
        )

        nmb_roto_values, nmb_descriptions = self.process_paths(
            nmb_paths, self.placeholders, "NMB"
        )
        self.nmb_descriptions = nmb_descriptions

        if nmb_descriptions:
            department_structure = self.expand_description_folders(
                department_structure, nmb_descriptions
            )

        department_structure = self.add_values_to_shot(
            department_structure, nmb_roto_values, nmb_descriptions
        )

        return department_structure
