import os
import sys

sys.path.append(
    "/tools/packages/python/3.9.6/platform-linux/arch-x86_64/os-rocky-9.2/python/site-packages/"
)
import json
import re
import ssl
import urllib.request
from collections import defaultdict

import fx
from PySide2 import QtWidgets
from PySide2.QtCore import QSize
from PySide2.QtGui import QIcon, QPixmap
from PySide2.QtWidgets import *
from PySide2.QtWidgets import QApplication

try:
    b_show_name = os.environ["B_SHOW"]
    sys.path.insert(0, "/tools/projects/{}/install/core/python".format(b_show_name))
except:
    # sys.path.insert(0, "/tools/projects/config_test_new/install/core/python")
    pass
import glob

import sgtk
import tank
from sgtk.authentication import ShotgunAuthenticator

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import pickle
import shutil
import time

from PySide2.QtCore import *
from PySide2.QtWidgets import QMessageBox

import task_list_ui as _ui
from deadline_submiter import BFSRenderSubmission

if os.getlogin() == "chandru":
    import session_builder

EMPTY_SFX_FILE = "/tools/silhouette_tools/2021.5/modal_sfx_file/empty.sfx"
print("****************************************************")
print("Loading BFS Tools...")


class TaskListCheck(_ui.MainWindow, QtWidgets.QDialog):
    """_summary_

    Args:
        _ui (_type_): _description_
        QtWidgets (_type_): _description_
    """

    def __init__(self):
        """_summary_"""
        super(TaskListCheck, self).__init__()
        self.data = []
        self.working_path = None
        self.latest_version = None
        self.file_path = {}
        self.version_master_data = {}
        self.sg_user = self.set_sgtk_auth()
        self.sg = self.sg_conection()
        # if os.getlogin() != "chandru":
        #     self.get_user_mail()
        self.project = self.set_show()
        self.current_user = os.getlogin().replace(".", "-")

        self.user_name = self.get_username()
        self.get_user_task()
        self.import_button.clicked.connect(self.import_file)
        # self.save_button.clicked.connect(self.save_project)
        self.master_task_button.clicked.connect(self.add_master_plate)
        self.open_button.clicked.connect(self.open_file)
        # self.custom_node_button.clicked.connect(self.custom_node_create)
        self.project_open_path = None
        self.get_user_shots()
        # self.publish_button.clicked.connect(self.call_back)
        self.worker_thread = None
        self.dialog = None
        self.id_item = None
        self.filter_status(self.filter_combo.currentText(), self.task_table, 2)

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
            proxy_ip = self.get_sg_proxy(file_path)
            sa = sgtk.authentication.ShotgunAuthenticator()
            user = sa.create_script_user(
                api_script="silhouette_my_task",
                api_key="cllnjxceqgaa7~pafXthdlaxm",
                host="https://basilic.shotgrid.autodesk.com",
                http_proxy=proxy_ip,
            )
            sgtk.set_authenticated_user(user)

        else:
            authenticator = ShotgunAuthenticator()
            user = authenticator.get_user()
            sgtk.set_authenticated_user(user)

        return user

    def sg_conection(self):
        """
        Creates and returns a connection to the Shotgun server.

        This method utilizes the `create_sg_connection` method from the `sg_user` attribute to establish
        a connection to the Shotgun server.

        Returns:
            Shotgun: An instance of the Shotgun connection.

        Raises:
            ShotgunConnectionError: If the connection to the Shotgun server fails.
        """
        sg = self.sg_user.create_sg_connection()
        return sg

    def show_error_message(self, message):
        # Create an instance of QApplication if it doesn't already exist
        app = QApplication.instance()
        if app is None:
            app = QApplication([])

        # Create a QMessageBox instance
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)  # Sets the icon to indicate an error
        msg_box.setText(message)  # Set the message text
        msg_box.setWindowTitle("Error")  # Set the title of the message box
        msg_box.exec_()  # Show the message box

    def get_user_mail(self):
        try:
            tank_context = os.environ["SHOTGUN_DESKTOP_CURRENT_USER"]
        except KeyError:
            raise RuntimeError(
                "Environment variable 'SHOTGUN_DESKTOP_CURRENT_USER' is not set."
            )

        # Unpickle the context dictionary
        try:
            context_dict = pickle.loads(tank_context.encode("latin1"))
        except (pickle.PickleError, TypeError) as e:
            raise RuntimeError(f"Failed to unpickle context: {e}")

        # Access the email ID directly
        try:
            email_id = context_dict["data"]["login"]
        except KeyError as e:
            raise RuntimeError(f"Key error: {e}")
        if "@bfslabs" in email_id:
            self.show_error_message(
                "Your email id is configured with @bfslabs.com in shotgrid Kindly get it updated by Production Team to @basilicfly.com"
            )
            return
        user_sg = self.sg.find_one(
            "HumanUser",
            [["email", "is", email_id]],
            ["sg_username", "department"],
        )
        if os.getlogin() != str(email_id).split("@")[0]:
            self.show_error_message(
                "Please make sure the system login is matching with the shotgrid login id"
            )
            return
        if user_sg is None:
            self.show_error_message("Please check the email id in Shotgrid")
            return
        if os.getlogin().replace(".", "-") != user_sg["sg_username"]:
            self.sg.update(
                "HumanUser",
                user_sg["id"],
                {"sg_username": os.getlogin().replace(".", "-")},
            )

        return user_sg

    def get_next_version(self, tk, context, template_name, field_name):
        """
        Get the highest version file found on disk for a given template
        :param tk:
        :param template_name:
        :return:
        """
        # print("Template_name",template_name)
        template = tk.templates[template_name]
        fields = context.as_template_fields(template)
        fields["artist_name"] = self.current_user

        # Get a list of existing file paths on disk that match the template and provided fields
        # Skip the version field as we want to find all versions, not a specific version.
        skip_fields = ["version"]
        file_paths = tk.paths_from_template(
            template, fields, skip_fields, skip_missing_optional_keys=True
        )
        latest_file = None
        highest_version = 0
        for a_file in file_paths:
            # extract the values from the path so we can read the version.
            path_fields = template.get_fields(a_file)
            if path_fields["name"] == field_name:
                if path_fields["version"] > highest_version:
                    highest_version = path_fields["version"]
                    latest_file = a_file
        return latest_file, highest_version

    def load_json(self):
        """
        Loads data from a JSON file named 'labels.json' located in the same directory as the script.

        This method determines the current file path, constructs the path to the 'labels.json' file, and
        attempts to load the JSON data. If the file does not exist or cannot be decoded, an empty dictionary
        is returned.

        Returns:
            dict: The data loaded from the JSON file. If the file does not exist or is invalid, an empty
            dictionary is returned.

        Raises:
            json.JSONDecodeError: If the file exists but contains invalid JSON.
        """
        current_file_path = os.path.abspath(__file__)
        current_directory = os.path.dirname(current_file_path)
        json_file = os.path.join(current_directory, "labels.json")
        if os.path.exists(json_file):
            with open(json_file, "r") as file:
                try:
                    data = json.load(file)
                except json.JSONDecodeError:
                    data = {}
        else:
            data = {}
        return data

    def add_label_to_json(self, label=None):
        """
        Adds or updates a label for a selected item in a JSON file named 'labels.json' located in the same directory as the script.

        This method retrieves the selected item's ID from the task table, loads the existing JSON data, adds or updates
        the label for the selected item under the current user's name, and writes the updated data back to the JSON file.

        Args:
            label (str, optional): The label to be added or updated for the selected item. Defaults to None.

        Returns:
            None

        Raises:
            json.JSONDecodeError: If the JSON file contains invalid JSON data.
        """
        current_file_path = os.path.abspath(__file__)
        current_directory = os.path.dirname(current_file_path)
        json_file = os.path.join(current_directory, "labels.json")

        selected_items = self.task_table.selectedItems()
        row = selected_items[0].row()
        # if os.getlogin() == "chandru":
        id_item = self.task_table.item(row, 4).text()
        # else:
        #     id_item = self.task_table.item(row, 5).text()

        if os.path.exists(json_file):
            with open(json_file, "r") as file:
                try:
                    self.json_data = json.load(file)
                except json.JSONDecodeError:
                    self.json_data = {}
        else:
            self.json_data = {}

        # Generate a new unique ID
        new_id = id_item

        # Add or update the new label and user_name in the data dictionary
        if label != None:
            user_name = self.current_user
            self.json_data[new_id] = {user_name: label}

            # Write the updated data back to the JSON file
            try:
                with open(json_file, "w") as file:
                    json.dump(self.json_data, file, indent=4)
            except Exception as e:
                print(e)

    def read_binary_cache_file(self):
        id_item = os.environ["selected_id"]
        return id_item
        # cache_path = os.path.join("/home", str(os.getlogin()), "silhouette_cache")
        # if not os.path.exists(cache_path):
        #     os.makedirs(cache_path)
        # cache_file_path = os.path.join(cache_path, "cache.cache")
        # with open(cache_file_path, "rb") as file:
        #     data = file.read()
        # string_data = data.decode("utf-8")
        # return string_data

    def write_binary_cache_file(self, data):
        cache_path = os.path.join("/home", str(os.getlogin()), "silhouette_cache")
        if not os.path.exists(cache_path):
            os.makedirs(cache_path)
        cache_file_path = os.path.join(cache_path, "cache.cache")
        try:
            with open(cache_file_path, "w") as file:
                file.write(data)
        except Exception as e:
            print(f"An error occurred while writing to the file: {e}")

    def download_image(self, url, version_id):
        """
        Downloads an image from the provided URL and saves it with a filename based on the version ID.

        This method checks if the file already exists. If it does, it returns the file path. If the file does
        not exist, it downloads the image from the URL and saves it as 'thumbnail_<version_id>.jpg'.

        Args:
            url (str): The URL of the image to download.
            version_id (str or int): The version identifier used to name the downloaded file.

        Returns:
            str: The file path of the downloaded image if successful, or None if the URL is None or the download fails.

        Raises:
            requests.exceptions.RequestException: If there is an issue with the HTTP request.
        """
        if url is None:
            return None

        path = f"/home/{str(os.getlogin())}/silhouette_cache/"
        if not os.path.exists(path):
            os.makedirs(path)

        file_path = (
            f"/home/{str(os.getlogin())}/silhouette_cache/thumbnail_{version_id}.jpeg"
        )

        # Check if the file already exists
        if os.path.exists(file_path):
            return file_path
        try:
            context = ssl._create_unverified_context()

            # Create an opener with our SSL context
            opener = urllib.request.build_opener(
                urllib.request.HTTPSHandler(context=context)
            )

            # Install this opener as the default opener
            urllib.request.install_opener(opener)

            # Now use urlretrieve as normal
            urllib.request.urlretrieve(url, file_path)
            return file_path
        except Exception as e:
            print(f"Failed to download image: {e}")
            return None

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
            self.show_error_message("Show is Not configured")
            return

        show_sg = self.sg.find_one("Project", [["name", "is", show_name]])
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
        user_sg = self.sg.find_one(
            "HumanUser",
            [["sg_username", "is", user_name]],
            ["sg_username", "department"],
        )
        if user_sg is None:
            self.show_error_message("Please check the user name in Shotgrid")
            return
        return user_sg

    def multiple_version(self, version_data):
        """
        Processes multiple version entries to find and return the latest published file information.

        This method iterates through version data, retrieves the file path of published files,
        and identifies the latest file based on the largest file ID. It downloads the image
        associated with the latest published file and creates a QListWidgetItem with the file's code.

        Args:
            version_data (list): A list of version dictionaries, each containing information about a published file.

        Returns:
            tuple: A tuple containing the image path (str) and a QListWidgetItem with the file's code.
            Returns None if no valid published files are found.

        Raises:
            KeyError: If expected keys are not present in the version data or published file data.
            AttributeError: If the `self.sg` or `self.download_image` methods are not properly defined.
        """
        latest_file = {}
        file_path = {}

        # Collect all file IDs first to minimize repeated lookups
        file_ids = [
            version["published_files"][0]["id"]
            for version in version_data
            if version["published_files"]
        ]

        # Fetch all published file paths in a single batch call
        published_files_data = self.sg.find(
            "PublishedFile", [["id", "in", file_ids]], ["sg_filepath", "image", "code"]
        )

        for published_file in published_files_data:
            file_id = published_file["id"]
            if published_file["sg_filepath"]:
                file_path[file_id] = published_file["sg_filepath"]
                latest_file[file_id] = published_file

        if not latest_file:
            return None, None

        # Find the published file with the largest ID
        largest_id = max(latest_file.keys())
        published_file = latest_file[largest_id]

        # Download the image and create the list widget item
        image_path = self.download_image(published_file["image"], largest_id)
        item = QtWidgets.QListWidgetItem(published_file["code"])

        # Store the file path using the code as the key
        self.file_path[published_file["code"]] = published_file["sg_filepath"]

        return image_path, item

    def get_user_task(self):
        """
        Retrieves and populates the user's tasks in the task table.

        This method queries Shotgun for tasks assigned to the current user within the current project,
        retrieves relevant fields, and populates a QTableWidget with the task data.

        Fields displayed in the table include:
            - Shot code
            - Step name
            - Project name
            - Task status
            - Due date
            - Task ID

        It also connects the item selection change event to the `get_selected_task_data` method.

        Raises:
            KeyError: If the 'project' or 'user_name' attributes are not set.
            AttributeError: If the 'self.sg' or 'self.task_table' attributes are not properly defined.
        """

        fields = [
            "id",
            "content",
            "entity.Shot.code",
            "due_date",
            "project",
            "sg_status_list",
            "step",
        ]
        # filters = [
        #     ["project", "is", {"type": "Project", "id": self.project["id"]}],
        #     ["task_assignees", "is", {"type": "HumanUser", "id": self.user_name["id"]}],
        # ]
        filters = [
            ["project", "is", {"type": "Project", "id": self.project["id"]}],
            ["task_assignees", "is", {"type": "HumanUser", "id": self.user_name["id"]}],
            # {
            #     "filter_operator": "any",  # This ensures that either "roto" or "paint" will be matched
            #     "filters": [
            #         ["step.Step.code", "is", "roto"],
            #         ["step.Step.code", "is", "paint"]
            #     ]
            # }
        ]

        self.data = self.sg.find("Task", filters, fields)
        print("data ------------------- ", self.data)
        self.task_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        self.task_table.setRowCount(len(self.data))
        for row, data in enumerate(self.data):
            # if os.getlogin() == "chandru":
            # if os.getlogin() == "chandru":
            self.task_table.setItem(
                row, 0, QtWidgets.QTableWidgetItem(data["entity.Shot.code"])
            )
            self.task_table.setItem(row, 1, QtWidgets.QTableWidgetItem(data["content"]))
            self.task_table.setItem(
                row, 2, QtWidgets.QTableWidgetItem(data["sg_status_list"])
            )
            self.task_table.setItem(
                row, 3, QtWidgets.QTableWidgetItem(data["step"]["name"])
            )
            self.task_table.setItem(row, 4, QtWidgets.QTableWidgetItem(str(data["id"])))
            # else:
            #     self.task_table.setItem(
            #         row, 0, QtWidgets.QTableWidgetItem(data["entity.Shot.code"])
            #     )
            #     self.task_table.setItem(
            #         row, 1, QtWidgets.QTableWidgetItem(data["step"]["name"])
            #     )
            #     self.task_table.setItem(
            #         row, 2, QtWidgets.QTableWidgetItem(data["project"]["name"])
            #     )
            #     self.task_table.setItem(
            #         row, 3, QtWidgets.QTableWidgetItem(data["sg_status_list"])
            #     )
            #     self.task_table.setItem(
            #         row, 4, QtWidgets.QTableWidgetItem(data["content"])
            #     )
            #     self.task_table.setItem(row, 5, QtWidgets.QTableWidgetItem(str(data["id"])))

        self.task_table.itemSelectionChanged.connect(self.get_selected_task_data)

    def show_error_pop_up(self, error_message):
        errorDialog = QMessageBox()
        errorDialog.setIcon(QMessageBox.Critical)
        errorDialog.setText("Error")
        errorDialog.setInformativeText(error_message)
        errorDialog.setWindowTitle("Error")
        errorDialog.setStandardButtons(QMessageBox.Ok)
        errorDialog.exec_()

    def get_selected_task_data(self):
        """
        Clears and updates the publish lists and the table widget with data for the selected task.

        This method:
        1. Clears the current contents of the `table_widget`, `publish_list`, and `publish_list_version`.
        2. Retrieves the selected task from the task table.
        3. Fetches version data related to the selected task.
        4. Populates the publish lists with the retrieved version data, setting icon sizes for each item.
        5. Calls the `working_tab` and `publish_tab` methods to update the respective tabs.

        Raises:
            IndexError: If no items are selected in the task table.
            AttributeError: If methods like `get_version_data`, `working_tab`, or `publish_tab` are not properly defined.
        """
        # add cache

        selected_items = self.task_table.selectedItems()
        if selected_items:
            id_row = selected_items[0].row()
            # if os.getlogin() == "chandru":
            id_item = self.task_table.item(id_row, 4).text()
            # else:
            # id_item = self.task_table.item(id_row, 5).text()
            self.write_binary_cache_file(id_item)
            os.environ["selected_id"] = id_item
            self.id_item = id_item
            self.table_widget.clearContents()
            self.publish_list.clear()
            self.publish_list_version.clear()
            row = selected_items[0].row()
            task_name = self.task_table.item(row, 0).text()

            self.get_version_data(task_name)
            self.working_tab()
            self.publish_tab()
        else:
            self.show_error_pop_up("your not selecting the tasks can you pick one task")

        if os.getlogin() == "chandru":
            prerender_path = self.working_file_path("shot_prerender_silhouette")
            if not os.path.exists(prerender_path):
                try:
                    os.makedirs(prerender_path)
                except Exception as e:
                    print(f"Failed to create directory: {e}")
            else:
                print("Path:", prerender_path)
                print("Directory already exists")

    # def get_version_data(self, task_name):
    #     self.file_path = {}
    #     online_version_data = self.sg.find(
    #         "Version",
    #         [
    #             ["project", "is", self.project],
    #             ["entity.Shot.code", "is", task_name],
    #             ["published_files", "is_not", None],
    #         ],
    #         ["id", "published_files","image"],
    #     )
    #     print(task_name)
    #     print(online_version_data)

    #     published_file_ids = set()
    #     for version in online_version_data:
    #         published_files = version.get("published_files", [])
    #         for file in published_files:
    #             published_file_ids.add(file["id"])
    #     if published_file_ids:
    #         published_files_data = self.sg.find(
    #             "PublishedFile",
    #             [["id", "in", list(published_file_ids)]],
    #             ["id", "sg_filepath"]
    #         )

    #         # Create a dictionary to map IDs to file paths
    #         file_paths = {file["id"]: file["sg_filepath"] for file in published_files_data}

    #         # Create QListWidgetItem for each version
    #         for version in online_version_data:

    #             published_files = version.get("published_files", [])
    #             for file in published_files:
    #                 file_name = file["name"]
    #                 file_id = file["id"]
    #                 file_path = file_paths.get(file_id, "No path available")
    #                 print(file_path)
    #                 item = QtWidgets.QListWidgetItem(file_name)
    #                 self.publish_list.addItem(item)
    #                 if file_path:
    #                     self.file_path[file_name] = (
    #                         file_path
    #                     )
    #                     image_path = self.download_image(
    #                         version["image"], version["id"]
    #                     )
    #                 pixmap = QPixmap(image_path)
    #                 scaled_pixmap = pixmap.scaled(300, 200)
    #                 item.setIcon(QIcon(scaled_pixmap))
    #                 self.publish_list.addItem(item)
    #                 if item is not None:
    #                     self.publish_list_version.addItem(item.clone())
    #                     self.publish_list.setIconSize(QSize(100, 100))
    #                     self.publish_list_version.setIconSize(QSize(100, 100))

    def get_proxy_path(self, path):
        match = re.search(r"/v\d{1,4}/", path)
        if match:
            # Extract the directory path up to the version directory
            path = path[: match.end()]

        proxy_path = os.path.join(path, "proxy")
        if not os.path.exists(proxy_path):
            return False
        list_dir = os.listdir(proxy_path)
        if not len(list_dir) > 1:
            return False
        file_name = sorted(os.listdir(proxy_path))[0]
        image_path = os.path.join(proxy_path, file_name)
        return image_path

    def get_version_data(self, task_name):
        start_time = time.time()
        self.file_path = {}
        self.items_data = []

        # Fetch online version data
        self.online_version_data = self.sg.find(
            "Version",
            [
                ["project", "is", self.project],
                ["entity.Shot.code", "is", task_name],
                ["published_files", "is_not", None],
                ["tags", "name_contains", "PLATE"],
            ],
            ["id", "published_files", "image", "sg_first_frame", "sg_last_frame"],
        )
        # Collect all published file IDs
        published_file_ids = set()
        for version in self.online_version_data:
            published_files = version.get("published_files", [])
            for file in published_files:
                published_file_ids.add(file["id"])

        # if published_file_ids:
        #     # Fetch published files data
        #     published_files_data = self.sg.find(
        #         "PublishedFile",
        #         [["id", "in", list(published_file_ids)]],
        #         ["id", "sg_filepath", "published_file_type"],
        #     )

        #     # Map file IDs to their paths
        #     # file_paths = {
        #     #     file["id"]: file["sg_filepath"] for file in published_files_data
        #     # }
        #     file_paths = {}
        #     for file in published_files_data:
        #         # 1. Try sg_filepath
        #         path = file.get("sg_filepath")

        #         # 2. If empty, try path_cache
        #         if not path:
        #             path = file.get("path_cache")

        #         # 3. If still empty, dig into the 'path' dictionary for local storage paths
        #         if not path and file.get("path"):
        #             path_info = file["path"]
        #             # Prioritize the OS you are currently working on (e.g., Linux)
        #             path = path_info.get("local_path_linux") or path_info.get(
        #                 "local_path"
        #             )

        #         file_paths[file["id"]] = path

        #     file_info = {
        #         file["id"]: {"type": file["published_file_type"]}
        #         for file in published_files_data
        #     }
        if published_file_ids:
            # Fetch published files data
            published_files_data = self.sg.find(
                "PublishedFile",
                [["id", "in", list(published_file_ids)]],
                ["id", "sg_filepath", "published_file_type", "path_cache", "path"],
            )

            file_paths = {}
            for file in published_files_data:
                # 1. Try sg_filepath
                path = file.get("sg_filepath")

                # 2. If empty, try path_cache
                if not path:
                    path = file.get("path_cache")

                # 3. If still empty, dig into the 'path' dictionary for local storage paths
                if not path and file.get("path"):
                    path_info = file["path"]
                    # Prioritize the OS you are currently working on (e.g., Linux)
                    path = path_info.get("local_path_linux") or path_info.get(
                        "local_path"
                    )

                file_paths[file["id"]] = path

            print("file_paths : ", file_paths)
            file_info = {
                file["id"]: {"type": file["published_file_type"]}
                for file in published_files_data
            }

            # Process each version
            for version in self.online_version_data:
                published_files = version.get("published_files", [])
                for file in published_files:
                    file_name = file["name"]
                    file_id = file["id"]
                    file_path = file_paths.get(file_id, "No path available")

                    # Create QListWidgetItem
                    item = QtWidgets.QListWidgetItem(file_name)
                    scan_item = QtWidgets.QListWidgetItem(file_name)
                    if file_path:
                        file_name = os.path.basename(file_path)
                        self.version_master_data[file_name] = version["id"]
                        self.file_path[file_name] = file_path

                        # Determine image path based on the file path
                        if "silhouette/render/" not in file_path:
                            image_file_path = self.get_proxy_path(file_path)
                            if image_file_path:
                                image_path = image_file_path
                            else:
                                image_path = self.download_image(
                                    version["image"], version["id"]
                                )
                        else:
                            image_path = self.download_image(
                                version["image"], version["id"]
                            )

                        # Set icon from the image path
                        pixmap = QPixmap(image_path)
                        scaled_pixmap = pixmap.scaled(300, 200)

                        item.setIcon(QIcon(scaled_pixmap))
                        scan_item.setIcon(QIcon(scaled_pixmap))

                        item_data = {
                            "text": "Scan",
                            "file_name": file_name,
                            "icon": scaled_pixmap,
                        }
                        # self.items_data.append(item_data)  # Store item data in the list
                        self.publish_list.addItem(item)
                        # self.add_publish_item(item,"Scan")
                        self.publish_list_version.addItem(scan_item)
                        self.publish_list.setIconSize(QSize(100, 100))
                        self.publish_list_version.setIconSize(QSize(100, 100))
                    else:
                        print("No file path available for", file_name)

            end_time = time.time()

    def get_frame_range(self, path):
        files = sorted(glob.glob(re.sub(r"%0\d+d", "*", path)))
        if not files:
            return None
        start_frame = re.findall(r"\d+", files[0])[-1]
        last_frame = re.findall(r"\d+", files[-1])[-1]
        return re.sub(r"%0\d+d", f"[{start_frame}-{last_frame}]", path)

    def get_user_shots(self):
        """
        Retrieves and populates the user's assigned shots in the shot table.

        This method queries Shotgun for shots assigned to the current user within the current project,
        retrieves relevant fields ('code', 'sg_status_list', 'project'), and populates a QTableWidget
        with the shot data.

        It also connects the item selection change event to the `get_selected_shot_data` method.

        Raises:
            KeyError: If the 'project' or 'user_name' attributes are not set.
            AttributeError: If the 'self.sg' or 'self.shot_table' attributes are not properly defined.
        """
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
        self.shot_table.setRowCount(len(self.shots_data))
        for row, data in enumerate(self.shots_data):
            self.shot_table.setItem(row, 0, QtWidgets.QTableWidgetItem(data["code"]))
            self.shot_table.setItem(
                row, 1, QtWidgets.QTableWidgetItem(data["project"]["name"])
            )
            self.shot_table.setItem(
                row, 2, QtWidgets.QTableWidgetItem(data["sg_status_list"])
            )
        self.shot_table.itemSelectionChanged.connect(self.get_selected_shot_data)

    def get_selected_shot_data(self):
        """
        Clears and updates the all_list_shot and scan_list_shot with version data for the selected shot.

        This method:
        1. Clears the current contents of the `all_list_shot` and `scan_list_shot`.
        2. Retrieves the selected shot from the shot table.
        3. Fetches version data related to the selected shot.
        4. Populates the `all_list_shot` and `scan_list_shot` with QListWidgetItem objects representing the versions,
        setting icons based on associated images.

        Raises:
            IndexError: If no items are selected in the shot table.
            AttributeError: If the `self.shot_table`, `self.all_list_shot`, `self.scan_list_shot`, or `self.get_version_data` methods
                            are not properly defined.
        """
        self.all_list_shot.clear()
        self.scan_list_shot.clear()
        selected_items = self.shot_table.selectedItems()
        row = selected_items[0].row()
        task_name = self.shot_table.item(row, 0).text()
        # items = self.get_version_data(task_name)
        # for item in items:
        #     self.all_list_shot.addItem(item)
        #     self.scan_list_shot.addItem(item.clone())
        #     self.all_list_shot.setIconSize(QSize(100, 100))
        #     self.scan_list_shot.setIconSize(QSize(100, 100))

    def filter_tasks(self):
        """
        Filters and updates the task table based on the selected date filter option.

        This method clears the contents of `publish_list_version` and `publish_list`, retrieves the selected
        date filter option from `date_filter_combo`, applies the date filter to `self.data` using
        `apply_date_filter`, and updates `task_table` with the filtered data.

        The fields displayed in the table include:
            - Shot code
            - Task content
            - Project name
            - Task status
            - Due date
            - Task ID

        Raises:
            AttributeError: If the `self.date_filter_combo`, `self.data`, or `self.task_table` attributes
                            are not properly defined.
        """
        self.publish_list_version.clear()
        self.publish_list.clear()
        filter_option = self.date_filter_combo.currentText()
        filtered_data = self.apply_date_filter(self.data, filter_option)
        self.task_table.clearContents()
        self.task_table.setRowCount(len(filtered_data))
        for row, data in enumerate(filtered_data):
            self.task_table.setItem(row, 0, QTableWidgetItem(data["entity.Shot.code"]))
            self.task_table.setItem(row, 1, QTableWidgetItem(data["content"]))
            self.task_table.setItem(row, 2, QTableWidgetItem(data["project"]["name"]))
            self.task_table.setItem(row, 3, QTableWidgetItem(data["sg_status_list"]))
            self.task_table.setItem(row, 4, QTableWidgetItem(data["due_date"]))
            self.task_table.setItem(row, 5, QTableWidgetItem(data["id"]))

    def get_field_name(self):
        project_path = fx.activeProject().path
        if project_path.split("/")[-1] == "project.sfx":
            project = os.path.dirname(fx.activeProject().path)
        else:
            project = os.path.dirname(fx.activeProject().path)
        try:
            tk = sgtk.sgtk_from_path(project)
        except tank.errors.TankInitError as e:
            print(e)
            self.show_error_message(
                "Please open or create a project first, then use 'Save As Next Version'."
            )

        context = tk.context_from_path(project)
        if not context:
            print(f"Failed to get context from path: {project}")
            return
        template = tk.template_from_path(project)
        fields = template.get_fields(project)

        if not fields:
            print(f"No fields extracted from path: {project}")
            return

        # Retrieve the 'name' field
        name_field = fields.get("name")

        return name_field

    def filter_table(self, text, table_name):
        """
        Filters the specified table (`table_name`) based on the given `text`.

        This method iterates through each row in the table, checking each cell's text content
        against the lowercased `filter_text`. If `filter_text` is found in any cell of a row,
        that row is set to be visible (`setRowHidden(False)`). Otherwise, the row is hidden
        (`setRowHidden(True)`).

        Args:
            text (str): The text to filter the table rows with.
            table_name (QTableWidget): The table widget object to filter.

        Raises:
            AttributeError: If the `table_name` attribute is not a valid QTableWidget object.
        """

        filter_text = text.lower()
        for row in range(table_name.rowCount()):
            item_visible = False
            for column in range(table_name.columnCount()):
                item = table_name.item(row, column)
                if filter_text in item.text().lower():
                    item_visible = True
                    break
            table_name.setRowHidden(row, not item_visible)

    def task_status_filter(self):
        """
        Filters the task table (`task_table`) based on the selected status value (`filter_combo`).

        This method retrieves the selected status value from `filter_combo`, filters `self.data` to
        find tasks that match the selected status value, and updates the visibility of rows in `task_table`
        based on whether each task's shot code (`entity.Shot.code`) matches any cell in the table.

        Raises:
            AttributeError: If the `filter_combo`, `self.data`, or `task_table` attributes
                            are not properly defined.
        """
        status_value = self.filter_combo.currentText()
        filtered_tasks = [
            task for task in self.data if task["sg_status_list"] == status_value
        ]
        for i in filtered_tasks:
            for row in range(self.task_table.rowCount()):
                item_visible = False
                for column in range(self.task_table.columnCount()):
                    item = self.task_table.item(row, column)
                    if i["entity.Shot.code"] in item.text().lower():
                        item_visible = True
                        break
                self.task_table.setRowHidden(row, not item_visible)

    def filter_status(self, text, table_name, status_column):
        """
        Filters the specified `table_name` based on the given `text` and `status_column`.

        This method iterates through each row in `table_name`, retrieves the status text from
        the specified `status_column`, and sets the row visibility based on whether the status
        matches the `text`.

        Args:
            text (str): The status text to filter rows with. If 'All', all rows are shown.
            table_name (QTableWidget): The table widget object to filter.
            status_column (int): The index of the column containing the status information.

        Raises:
            AttributeError: If the `table_name` attribute is not a valid QTableWidget object.
        """
        filter_text = text
        for row in range(table_name.rowCount()):
            status = table_name.item(row, int(status_column)).text()
            table_name.setRowHidden(row, filter_text != "All" and status != filter_text)

    def create_tab_rootnode(self, task_id):
        project = fx.activeProject()
        project_path = project.path
        tk = sgtk.sgtk_from_path(str(project_path))
        context = tk.context_from_path(project_path)
        project_name = context.project["name"]

        shot = context.entity
        shot_name = shot["name"]

        # create your dictionary
        my_dict = {
            "project_name": project_name,
            "shot_name": shot_name,
            "task_id": task_id,
        }

        # convert dict to string
        note_text = json.dumps(my_dict)

        # assign it to project.note
        project.note = note_text

        # verify
        return project.note

    def add_master_plate(self):
        id_item = self.read_binary_cache_file()
        tk = sgtk.sgtk_from_entity("Task", int(id_item))
        context = tk.context_from_entity("Task", int(id_item))
        shot_entity = context.entity

        current_index_value = self.tab_widget.currentIndex()
        if current_index_value == 0:
            if (
                self.publish_list is not None
                or self.scan_table_widget.selectedItems() is not None
            ):
                if self.publish_list.selectedItems():
                    selected_items = self.publish_list.selectedItems()
                else:
                    selected_items = self.scan_table_widget.selectedItems()
                if selected_items:
                    selected_texts = [item.text() for item in selected_items]
                    version_id = self.version_master_data[selected_texts[0]]
                    version = self.sg.find_one("Version", [["id", "is", version_id]])
                    shot_id = shot_entity["id"]  # Replace with your actual Shot ID
                    data_to_update = {
                        "sg_master_plate": version  # Example: Update status to 'In Progress'
                    }

                    # Perform the update
                    updated_shot = self.sg.update("Shot", shot_id, data_to_update)
                    self.show_error_message("Master Plate was Updated in Shotgrid")

    def open_file(self):
        """
        Opens a selected file or project based on the current tab index in `tab_widget_right`.

        This method checks the current tab index (`current_index_value`) of `tab_widget_right`:
        - If index is 0, selects an item from `publish_list` and clears selection afterwards.
        - If index is 1, selects an item from `table_widget`, constructs a project path using `working_file_path`
        for shot work area in Silhouette FX, and clears selection afterwards.
        - If index is 2, selects an item from `published_file_list`, constructs a project path using `working_file_path`
        for shot publish area in Silhouette FX, and clears selection afterwards.
        - If no items are selected in any list, opens a file dialog to choose a Silhouette FX project file (*.sfx).

        After selecting or opening a project file, loads the project using `fx.loadProject(project_path)` and closes
        the current window (`self.close()`).

        Raises:
            IndexError: If no items are selected in the current tab's list (0, 1, or 2) and no file is selected in the dialog.
            AttributeError: If any of the required attributes (`tab_widget_right`, `publish_list`, `table_widget`,
                            `published_file_list`, `fx`) are not properly defined.
        """
        # selected_item = self.publish_list.selectedItems()
        # # selected_item_work = self.published_file_list.selectedItems()
        # if not selected_item:
        #     self.show_error_message("Please select the work file or publish file then click open")
        #     return
        task_selected_items = self.task_table.selectedItems()
        if not task_selected_items:
            self.show_error_message("Please select the task")
        row = task_selected_items[0].row()
        # if os.getlogin() == "chandru":
        task_id = self.task_table.item(row, 4).text()
        # else:
        #     task_id = self.task_table.item(row, 5).text()

        project_path = None
        current_index_value = self.tab_widget_right.currentIndex()
        if (
            self.publish_list.selectedItems()
            or self.table_widget.selectedItems()
            or self.published_file_list.selectedItems()
        ):
            if current_index_value == 0:
                if self.publish_list.selectedItems():
                    selected_item = self.publish_list.selectedItems()
                    if os.path.splitext(selected_item[0].text())[-1] != ".sfx":
                        self.show_error_message(
                            "your selecting the scan file use import button"
                        )
                        return
                    work_file_path = self.working_file_path("shot_work_area_silhouette")
                    project_path = os.path.join(
                        work_file_path, selected_item[0].text(), "project.sfx"
                    )
                    if not os.path.exists(project_path):
                        work_file_path = self.working_file_path(
                            "shot_publish_area_silhouette"
                        )
                        project_path = os.path.join(
                            work_file_path, selected_item[0].text(), "project.sfx"
                        )
                self.publish_list.clearSelection()
            elif current_index_value == 1:
                selected_item = self.table_widget.selectedItems()
                work_file_path = self.working_file_path("shot_work_area_silhouette")
                project_path = os.path.join(
                    work_file_path, selected_item[0].text(), "project.sfx"
                )
                self.working_list.clearSelection()
            elif current_index_value == 2:
                selected_item = self.published_file_list.selectedItems()
                work_file_path = self.working_file_path("shot_publish_area_silhouette")
                project_path = os.path.join(
                    work_file_path, selected_item[0].text(), "project.sfx"
                )
                self.published_file_list.clearSelection()
        else:
            options = QtWidgets.QFileDialog.Options()
            options |= QtWidgets.QFileDialog.ReadOnly
            project_path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "Open File", "", "silhouette FX Files (*.sfx)", options=options
            )

        if project_path is not None:
            sil_version = fx.versionString
            if sil_version == 2021.5:
                project_path = os.path.splitext(os.path.dirname(project_path))[0]
                fx.loadProject(project_path)

            else:
                fx.loadProject(project_path)
        self.create_tab_rootnode(task_id)
        self.close()

    def new_project_creation(self):
        """
        Creates a new Silhouette FX project based on the selected task in `task_table` and user input.

        This method:
        - Retrieves the selected task ID from `task_table`.
        - Checks if `self.json_data` contains information about the task and user labels. If not, prompts the user
        to enter a new label using `show_new_label_dialog()`.
        - If a new label is provided, constructs a project path using `working_file_path` for Silhouette shot work,
        creates a new Silhouette FX project, saves it to the constructed project path, loads the project using `fx.loadProject`,
        and closes the current window (`self.close()`).

        Raises:
            IndexError: If no task is selected in `task_table`.
            AttributeError: If `self.task_table`, `self.json_data`, `self.current_user`, `fx.Project`, `fx.loadProject`,
                            or `self.close()` are not properly defined.
        """
        selected_items = self.task_table.selectedItems()
        row = selected_items[0].row()
        task_id = self.task_table.item(row, 4).text()
        task_selected_items = self.task_table.selectedItems()
        if not task_selected_items:
            self.show_error_message("Please select the task")
        if os.getlogin() == "chandru":
            self.new_label, layer_count = self.show_new_label_dialog_()
        else:
            self.new_label, layer_count = self.show_new_label_dialog()

        if self.new_label != None:
            id_item = self.read_binary_cache_file()
            tk = sgtk.sgtk_from_entity("Task", int(id_item))
            context = tk.context_from_entity("Task", int(id_item))
            template = tk.templates["silhouette_shot_work"]

            fields = context.as_template_fields(template)
            print("INITIAL FIELDS : ", fields)
            fields["artist_name"] = self.current_user
            name = self.json_data[id_item][fields["artist_name"]]
            fields["name"] = name
            fields["version"] = 1
            try:
                self.ensure_step_field(context, fields, id_item, default_step="roto")
            except ValueError as e:
                self.show_error_message(str(e))
                return

            lates_file, latest_version = self.get_next_version(
                tk, context, "silhouette_shot_work", fields["name"]
            )
            fields["version"] = latest_version + 1
            project_path = template.apply_fields(fields)
            # project_path = self.working_file_path("silhouette_shot_work")
            project = fx.Project()
            sil_version = fx.versionString
            if sil_version == "2021.5.0":
                project_path = os.path.splitext(project_path)[0]
                fx.loadProject(EMPTY_SFX_FILE)
                project = fx.activeProject()
                project.save(project_path)
                # fx.loadProject(os.path.join(project_path+".sfx","project.sfx"))
            else:
                if os.getlogin() == "chandru":
                    project_path = os.path.splitext(project_path)[0]
                    fx.loadProject(EMPTY_SFX_FILE)
                    project = fx.activeProject()
                    project.save(project_path)
                else:
                    project.save(project_path)
                    fx.loadProject(project_path)
            current_index_value = self.tab_widget.currentIndex()

            if current_index_value == 0:
                if (
                    self.publish_list is not None
                    or self.publish_list_version is not None
                ):
                    if self.publish_list.selectedItems():
                        selected_items = self.publish_list.selectedItems()
                    else:
                        selected_items = self.publish_list_version.selectedItems()
                    if selected_items:
                        selected_texts = [item.text() for item in selected_items]
                        file_path = self.file_path[selected_texts[0]]
                        print("FILE PATH : ", file_path)
                        file_extension = os.path.splitext(file_path)[-1]
                        username = os.environ.get("USER")
                        if file_extension != ".mov":
                            file_path = self.get_frame_range(file_path)

                        # else:
                        #     if file_extension != ".mov":
                        #         pattern = r"\d+-\d+\."
                        #         frame_range = re.findall(pattern, file_path)
                        #         file_path = file_path.replace(
                        #             frame_range[0].split(".")[0],
                        #             f"[{frame_range[0].split('.')[0]}]",
                        #         )
                        #     else:
                        #         file_path = file_path
                        if file_path:
                            project = fx.activeProject()
                            res = fx.Source(file_path)
                            project.addItem(res)

                if selected_items:
                    if os.getlogin() == "chandru":
                        self.build_session(layer_count)

                    QtWidgets.QMessageBox.information(
                        self, "Imported", "\n".join(selected_texts)
                    )
                    if os.getlogin() == "chandru":
                        self.cleanUpNodes()

                else:
                    QtWidgets.QMessageBox.information(
                        self, "Selected Items", "No items selected."
                    )

            self.create_tab_rootnode(task_id)
            self.close()

    def connect(self, prev_node, new_node):
        output = prev_node.getOutput(0)
        input = new_node.primaryInput
        if output and input:
            output.connect(input)
        return self

    def cleanUpNodes(self):
        session = fx.activeSession()  # Ensure this is returning a valid session object

        nodes = session.nodes
        positions = {}
        for node in nodes:
            positions[node] = node.getState("graph.pos")

        fx.trees.layout()  # Ensure trees.layout() works as expected

        new_positions = {}
        for node in nodes:
            new_positions[node] = node.getState("graph.pos")
            node.setState("graph.pos", positions[node])

        fx.beginUndo("Auto Layout Nodes")

        for node in new_positions:
            pos = new_positions[node]
            node.setState("graph.pos", pos)

        fx.endUndo()
        fx.activeProject().save()
        working_path = fx.activeProject().path
        sil_version = fx.versionString

        if sil_version == 2023.0:
            fx.loadProject(working_path)

        if sil_version == 2021.5:
            working_path = os.path.splitext(os.path.dirname(working_path))[0]
            fx.loadProject(working_path)
        else:
            fx.loadProject(working_path)

    def build_session(self, layer_count):
        session_builder.SessionBuilder(layer=layer_count)
        session = fx.activeSession()
        all_nodes = session.nodes
        roto_nodes = [node for node in all_nodes if node.type == "RotoNode"]
        for roto_node in roto_nodes:
            publish_node = self.custom_node_create(text="publish")
            self.connect(roto_node, publish_node)

    def save_project(self):
        """
        Saves the active Silhouette FX project based on selected task data and current user.

        This method retrieves the selected task ID from `task_table`, initializes Shotgun Toolkit (`sgtk`) using
        the task ID, and retrieves context and template information. It retrieves the artist name from `current_user`
        and constructs a working path using the retrieved information. It calculates the next version number using
        `get_next_version` method, saves the project to the calculated working path, updates the selected task data
        in `task_table`, and closes the current window (`self.close()`).

        Raises:
            IndexError: If no task is selected in `task_table`.
            KeyError: If `self.json_data` does not contain the necessary task or artist name information.
            AttributeError: If any of the required attributes (`task_table`, `current_user`, `sgtk`, `fx.activeProject()`,
                            `self.get_selected_task_data()`, `self.close()`) are not properly defined.
        """
        # selected_items = self.task_table.selectedItems()
        # row = selected_items[0].row()
        # id_item = self.task_table.item(row, 5).text()

        id_item = self.read_binary_cache_file()
        try:
            tk = sgtk.sgtk_from_entity("Task", int(id_item))
        except tank.errors.TankInitError as e:
            print(e)
            self.show_error_message(
                "Please open or create a project first, then use 'Save As Next Version'."
            )
            return

        context = tk.context_from_entity("Task", int(id_item))
        template = tk.templates["silhouette_shot_work"]
        fields = context.as_template_fields(template)
        try:
            self.ensure_step_field(context, fields, id_item)
        except ValueError as e:
            self.show_error_message(str(e))
            return
        fields["name"] = self.get_field_name()
        fields["version"] = 1
        lates_file, latest_version = self.get_next_version(
            tk, context, "silhouette_shot_work", fields["name"]
        )
        fields["version"] = latest_version + 1
        fields["artist_name"] = self.current_user
        working_path = template.apply_fields(fields)
        path = fx.activeProject().path
        project = fx.activeProject()
        sil_version = fx.version
        if sil_version == 2023.0:
            working_path = os.path.join(working_path, "project.sfx")
            project.save(working_path)
            fx.loadProject(working_path)

        if sil_version == 2021.5:
            working_path = os.path.splitext(working_path)[0]
            project.save(working_path)

        else:
            working_path = os.path.join(working_path)
            project.save(working_path)

        self.close()

    def version_change(self):
        """
        Handles the version change action in the application.

        This method retrieves the current text associated with the action that triggered the signal (`self.sender()`),
        determines the current index value of `tab_widget_right`, and updates `table_widget` based on the selected version
        in `self.latest_file`.

        Raises:
            AttributeError: If `tab_widget_right`, `table_widget`, or `self.latest_file` are not properly defined.
        """
        action = self.sender()
        if action:
            for row in range(self.table_widget.rowCount()):
                for col in range(self.table_widget.columnCount()):
                    if self.table_widget.cellWidget(row, col) == action:
                        text = (
                            action.currentText()
                        )  # Retrieve the text associated with the action
                        current_index_value = self.tab_widget_right.currentIndex()
                        if current_index_value == 1:
                            base_name = self.get_base_name(
                                self.table_widget.item(row, 0).text()
                            )
                            self.table_widget.setItem(
                                row,
                                0,
                                QtWidgets.QTableWidgetItem(
                                    self.latest_file[base_name][text]
                                ),
                            )

    def get_base_name(self, filename):
        # if os.getlogin()
        return re.sub(r"_v\d+", "", filename)

    def working_tab(self):
        """
        Sets up the working tab for Silhouette FX.
        This method initializes the working path using `working_file_path` for shot work area in Silhouette FX.
        If the working path does not exist, it creates the necessary directories. It retrieves the list of files in
        the working path, filters out non-version files, extracts version information, and populates `latest_file`
        and `latest_version`. It updates `working_file_data` and populates the table using `populate_table`.
        Finally, it sets the current text in `versionComboBox` to `self.latest_version`.
        """

        working_path = self.working_file_path("shot_work_area_silhouette")
        print(working_path)
        if not os.path.exists(working_path):
            os.makedirs(working_path)
        file_names = os.listdir(working_path)
        grouped_files = defaultdict(list)
        for file in file_names:
            base_name = self.get_base_name(file)
            grouped_files[base_name].append(file)

        self.working_file_data = []
        self.working_list_data = []
        self.latest_file = {}  # Initialize or clear the latest_file dictionary

        for base_name, files in grouped_files.items():
            version_list = []
            self.version_file_map = {}
            for file in files:
                if not file.endswith("~"):  # Ignore temporary files
                    version = file.split(".")[0].split("_")[-1]
                    version_list.append(version)
                    self.version_file_map[version] = file
            if version_list:
                latest_version = max(version_list, default=None)
                self.working_file_data.append(
                    [
                        self.version_file_map[latest_version],  # The latest file path
                        version_list,  # The list of all versions
                    ]
                )
                self.publish_list.addItem(self.version_file_map[latest_version])
                self.working_list_data = [self.version_file_map[latest_version]]
                self.latest_file[base_name] = (
                    self.version_file_map
                )  # Store the latest file for each base name

        self.populate_table()

    def get_base_name(self, file_name):
        """
        Extracts the base name of a file by removing the version number and file extension.
        Example: 'mech_207_043_0600_comp_test001_v001.sfx' -> 'mech_207_043_0600_comp_test001'

        Args:
            file_name (str): The full name of the file.

        Returns:
            str: The base name of the file without the version number and extension.
        """
        parts = file_name.split(".")[0].split("_")
        if parts[-1].startswith("v") and parts[-1][1:].isdigit():
            return "_".join(parts[:-1])
        return file_name

    def publish_tab(self):
        """
        Sets up the publish tab for Silhouette FX.

        This method clears `published_file_list` and retrieves the publish path using `working_file_path`
        for shot publish area in Silhouette FX. If the publish path exists, it retrieves the list of files
        in the publish path, filters out non-publish files, and adds them to both `published_file_list` and `publish_list`.

        Raises:
            AttributeError: If `working_file_path`, `published_file_list`, or `publish_list` are not properly defined.
        """
        self.published_file_list.clear()
        publish_path = self.working_file_path("shot_publish_area_silhouette")
        if os.path.exists(publish_path):
            file_name = os.listdir(publish_path)
            if len(file_name) >= 1:
                for i in file_name:
                    if not i.endswith("~"):
                        self.published_file_list.addItem(i)
                        self.publish_list.addItem(i)

    # def working_file_path(self, template_name=None):
    #     """
    #     Generates the working file path based on the selected task and template name.

    #     Args:
    #         template_name (str): The name of the template to use for generating the path.
    #                             Defaults to None.

    #     Returns:
    #         str: The generated working file path.

    #     Raises:
    #         IndexError: If no task is selected in `task_table`.
    #         KeyError: If `self.json_data` does not contain the necessary task or artist name information.
    #         AttributeError: If any of the required attributes (`task_table`, `current_user`, `sgtk`) are not properly defined.
    #     """
    #     if template_name != None:
    #         publish_path = None
    #         # selected_items = self.task_table.selectedItems()
    #         # row = selected_items[0].row()
    #         id_item = self.read_binary_cache_file()
    #         tk = sgtk.sgtk_from_entity("Task", int(id_item))
    #         context = tk.context_from_entity("Task", int(id_item))
    #         try:
    #             tk.create_filesystem_structure("Task", context.task["id"])

    #         except PermissionError:
    #             self.show_error_message("Your selecting task was you not have a permission")
    #             return
    #         template = tk.templates[template_name]
    #         fields = context.as_template_fields(template)
    #         fields["artist_name"] = self.current_user

    #         fields["version"] = 1
    #         if template_name == "silhouette_shot_work":
    #             name = self.json_data[id_item][fields["artist_name"]]
    #             fields["name"] = name
    #             publish_path = template.apply_fields(fields)
    #         else:
    #             publish_path = os.path.join(template.apply_fields(fields), "scripts")
    #         return publish_path

    # def working_file_path(self, template_name=None):
    #     """
    #     Generates the working file path based on the selected task and template name.

    #     Args:
    #         template_name (str): The name of the template to use for generating the path.

    #     Returns:
    #         str: The generated working file path.

    #     Raises:
    #         IndexError, KeyError, AttributeError: For various errors related to missing data or permissions.
    #     """
    #     if template_name is None:
    #         return None

    #     id_item = self.read_binary_cache_file()

    #     # Cache tk and context if this function is called frequently
    #     tk = sgtk.sgtk_from_entity("Task", int(id_item))
    #     context = tk.context_from_entity("Task", int(id_item))

    #     # Avoid creating the filesystem structure if it's already present
    #     try:
    #         template = tk.templates.get(template_name)
    #         if not template:
    #             raise KeyError(f"Template '{template_name}' not found.")
    #         try:
    #             publish_path = template.apply_fields(context.as_template_fields(template))
    #         except tank.errors.TankError:
    #             tk.create_filesystem_structure("Task", id_item)
    #             publish_path = template.apply_fields(context.as_template_fields(template))

    #         if not os.path.exists(publish_path):
    #             tk.create_filesystem_structure("Task", context.task["id"])
    #     except PermissionError:
    #         self.show_error_message("You do not have permission for the selected task.")
    #         return None

    #     # Efficiently populate fields and construct the path
    #     fields = context.as_template_fields(template)

    #     fields["artist_name"] = self.current_user
    #     fields["version"] = 1

    #     if template_name == "silhouette_shot_work":
    #         try:
    #             fields["name"] = self.json_data[id_item][fields["artist_name"]]
    #         except KeyError:
    #             self.show_error_message("Artist name not found in the JSON data.")
    #             return None
    #         publish_path = template.apply_fields(fields)
    #     else:
    #         publish_path = os.path.join(template.apply_fields(fields), "scripts")

    #     return publish_path

    def working_file_path(self, template_name=None):
        """
        Generates the working file path based on the selected task and template name.

        Args:
            template_name (str): The name of the template to use for generating the path.

        Returns:
            str: The generated working file path.

        Raises:
            IndexError, KeyError, AttributeError: For various errors related to missing data or permissions.
        """
        if template_name is None:
            return None

        # id_item = self.read_binary_cache_file()
        id_item = self.id_item

        # Cache tk and context
        tk = getattr(self, "_tk_cache", None)
        context = getattr(self, "_context_cache", None)

        if tk is None or context is None:
            tk = sgtk.sgtk_from_entity("Task", int(id_item))
            context = tk.context_from_entity("Task", int(id_item))
            # Store them in cache for future calls
            self._tk_cache = tk
            self._context_cache = context

        # Avoid creating the filesystem structure if it's already present
        try:
            # template = tk.templates.get(template_name)
            # if not template:
            #     raise KeyError(f"Template '{template_name}' not found.")
            # try:
            #     # Attempt to extract the fields
            #     fields = context.as_template_fields(template)
            # except tank.errors.TankError:
            #     # If there's an error, attempt to create the filesystem structure
            #     # try:
            #     tk.create_filesystem_structure("Task", int(id_item))
            #     fields = context.as_template_fields(template)
            # except tank.errors.TankError:
            #     # If creation fails, synchronize the filesystem, recreate, and extract fields
            #     tk.synchronize_filesystem_structure(entity_type, entity_id, full_sync=True, delete=True)
            #     tk.create_filesystem_structure("Task", int(id_item))
            #     fields = context.as_template_fields(template)
            # Get the template
            template = tk.templates.get(template_name)
            if not template:
                raise KeyError(f"Template '{template_name}' not found.")

            try:
                # Try to extract the fields
                fields = context.as_template_fields(template)
                selected_items = self.task_table.selectedItems()
                row = selected_items[0].row()
                shot_name = self.task_table.item(row, 0).text()
            except tank.errors.TankError:
                # Folder structure not found, try to create it
                try:
                    tk.create_filesystem_structure("Task", int(id_item))
                    fields = context.as_template_fields(template)
                except tank.errors.TankError:
                    # Folder creation failed, likely due to a registration conflict
                    selected_items = self.task_table.selectedItems()
                    row = selected_items[0].row()
                    shot_name = self.task_table.item(row, 0).text()
                    show_name = self.task_table.item(row, 2).text()
                    unreg_cmd = sgtk.get_command("unregister_folders", tk)
                    parameters = "/projects/{}/{}".format(show_name, shot_name)
                    params = {"path": parameters}
                    unreg_cmd.execute(params)
                    tk.create_filesystem_structure("Task", int(id_item))
                    fields = context.as_template_fields(template)

            fields["artist_name"] = self.current_user

            fields["version"] = 1
            try:
                self.ensure_step_field(context, fields, id_item)
            except ValueError as e:
                self.show_error_message(str(e))
                return
            # Build the path efficiently
            if template_name == "silhouette_shot_work":
                try:
                    fields["name"] = self.json_data[id_item][fields["artist_name"]]
                except KeyError:
                    self.show_error_message("Artist name not found in the JSON data.")
                    return None
                publish_path = template.apply_fields(fields)
            else:
                publish_path = os.path.join(template.apply_fields(fields), "scripts")

            # Check if the path exists before attempting to create filesystem structure
            if not os.path.exists(publish_path):
                # try:
                tk.create_filesystem_structure("Task", int(id_item))
                # except tank.errors.TankError:
                #     new_shot = self.sg.find_one(
                #         "Shot", [["code", "is", shot_name]], ["id", "code"]
                #     )

                #     exe_cmd = "/tools/projects/{}/tank".format(b_show_name)
                #     result = subprocess.run(
                #         [
                #             exe_cmd,
                #             "Shot",
                #             shot_name,
                #             "unregister_folders",
                #         ],
                #         input="Yes",
                #         capture_output=True,
                #         text=True,
                #         check=False,
                #     )
                #     print(result)
                #     fields["Shot"] = shot_name
                #     tk.synchronize_filesystem_structure()
                #     tk.create_filesystem_structure("Shot", int(new_shot["id"]))
                #     new_context = tk.context_from_entity("Shot", int(new_shot["id"]))
                #     print(new_context)

                # engine = sgtk.platform.current_engine()
                # engine.change_context(new_context)
                # tk.create_filesystem_structure("Shot", int(new_shot["id"]))

                # sg = tk.shotgun
                # shot = sg.find_one("Shot", [["code", "is", fields["Shot"]]], ["id"])
                # if shot:
                #     pc = tk.pipeline_configuration
                #     sgtk.util.filesystem.unregister_folders(
                #         tk, entity_type="Shot", entity_id=shot["id"]
                #     )
                #     path_cache = sgtk.util.Shotgunpath
                #     tk.clear_cached_locations(
                #         entity_type="Shot", entity_id=shot["id"]
                #     )

        except (PermissionError, KeyError) as e:
            self.show_error_message(str(e))
            return None

        return publish_path

    def import_file(self):
        """
        Imports selected files based on current tab and sub-tab values.

        Retrieves selected items based on the current tab index (`current_index_value`) and
        sub-tab index (`sub_tab_value`). Depending on the tab:
        - If on the first tab (`current_index_value == 0`), imports from `publish_list`
        or `publish_list_version`.
        - If on the third tab (`current_index_value == 2`), imports from `all_list_shot`
          or `scan_list_shot`.

        After importing:
        - Displays a message box with imported item information if items were selected.
        - Displays a message box indicating no items were selected if no items were selected.

        Note:
        - Assumes `fx` is a module or object that provides methods for working with files in
          Silhouette FX.
        - Assumes `file_path` and `file_path[selected_texts[0]]` are correctly populated with
          file paths.

        Raises:
            KeyError: If `file_path` does not contain the necessary file path information.
        """
        task_selected_items = self.task_table.selectedItems()
        if not task_selected_items:
            self.show_error_message("Please select the task")
        current_index_value = self.tab_widget.currentIndex()
        sub_tab_value = self.tab_widget_right_shot.currentIndex()
        if current_index_value == 0:
            if self.publish_list.selectedItems():
                selected_items = self.publish_list.selectedItems()
            else:
                selected_items = self.publish_list_version.selectedItems()
        if current_index_value == 2:
            if self.all_list_shot.selectedItems():
                selected_items = self.all_list_shot.selectedItems()
            else:
                selected_items = self.scan_list_shot.selectedItems()

        # if os.path.splitext(selected_items[0].text())[-1] == ".sfx":
        #     self.show_error_message("Your selecting workfile so use open button in the UI")
        #     return

        if selected_items:
            selected_texts = [item.text() for item in selected_items]
            file_path = self.file_path[selected_texts[0]]
            file_extension = os.path.splitext(file_path)[-1]
            if file_extension == ".sfx":
                self.show_error_message(
                    "Your selecting a workfile so please use open button in ui"
                )

            if file_extension == ".exr":
                pattern = r"\d+-\d+\."
                frame_range = re.findall(pattern, file_path)
                file_path = file_path.replace(
                    frame_range[0].split(".")[0], f"[{frame_range[0].split('.')[0]}]"
                )
            project = fx.activeProject()
            print("______++++++", project)
            session = fx.activeSession()
            res = fx.Source(file_path)
            res_src = project.addItem(res)
        else:
            print("No items selected.")

        if selected_items:
            QtWidgets.QMessageBox.information(
                self, "Imported", "\n".join(selected_texts)
            )
        else:
            QtWidgets.QMessageBox.information(
                self, "Selected Items", "No items selected."
            )
            return

        self.close()

    def handle_button_click(self):
        self.publish_to_sg()

    def get_latest_node_name(self, output_label):
        output_node = []

        # Collect all output nodes in the active session
        session = fx.activeSession()
        if not session:
            print("No active session found.")
            return None

        for output in session.outputs:
            output_node.append(output)  # Add the whole output node, not just the label

        # Filter for nodes that start with the output label
        matching_nodes = [
            node for node in output_node if node.label.startswith(output_label)
        ]  # Ensure we're checking node labels

        # Now print the actual nodes
        # for node in matching_nodes:
        #     print(f"Node label: {node.label}, Node object: {node}")

        if matching_nodes:
            # Extract numeric suffixes safely
            suffixes = []
            for node in matching_nodes:
                suffix = node.label[
                    len(output_label) :
                ].strip()  # Get the part after the base label
                if suffix.isdigit():  # Check if it's numeric
                    suffixes.append(int(suffix))
                else:
                    suffixes.append(0)  # Treat nodes without a number as 0

            # Determine the next suffix
            next_suffix = max(suffixes) + 1
            node_name = output_label + str(next_suffix)
        else:
            # If no matching nodes, start with "output_label1"
            node_name = output_label + "1"

        return node_name

    def custom_node_create(self, text):
        if text == "publish":
            template_name = "silhouette_shot_render_pub_stereo"
        elif text == "review":
            template_name = "silhouette_shot_render_stereo"
        else:
            return
        id_item = self.read_binary_cache_file()
        project = fx.activeProject().path
        tk = sgtk.sgtk_from_path(str(project))
        context = tk.context_from_entity("Task", int(id_item))

        template = tk.templates[template_name]
        fields = context.as_template_fields(template)

        fields["name"] = self.get_field_name()

        if text == "publish":
            r = self.sg.summarize(
                entity_type="PublishedFile",
                filters=[
                    ["task", "is", {"type": "Task", "id": context.task["id"]}],
                    ["name", "is", fields["name"] + "_pub"],
                    [
                        "published_file_type.PublishedFileType.code",
                        "is",
                        "Rendered Image",
                    ],
                ],
                summary_fields=[{"field": "version_number", "type": "maximum"}],
            )
            fields["version"] = r["summaries"]["version_number"] + 1
            output_node_label = "PublishOutputNode"

        else:
            version_template = context.sgtk.template_from_path(os.path.dirname(project))
            version_fields = version_template.get_fields(os.path.dirname(project))
            fields["version"] = version_fields.get("version")
            output_node_label = "ReviewOutputNode"
        fields["SEQ"] = "%04d"
        fields["artist_name"] = self.current_user
        project_name, shot_name, task, name, id_item = self.get_data()
        try:
            self.ensure_step_field(context, fields, id_item, default_step=task.lower())
        except ValueError as e:
            self.show_error_message(str(e))
            return

        output_path = template.apply_fields(fields)

        render_path = os.path.splitext(os.path.splitext(output_path)[0])[0]
        session = fx.activeSession()
        output_node = fx.Node("OutputNode")
        output_label = self.get_latest_node_name(output_node_label)

        output_node.label = output_label
        output_node.properties["path"].value = render_path
        output_node.properties["channels"].value = 1
        output_node.properties["channels"].value = 2
        channels_prop = output_node.properties.get("channels")
        channels_prop.value = (1 << 0) | (1 << 1)
        # channels_prop.value = 1 << 0
        session.addNode(output_node)
        return output_node
        self.close()

    def get_data(self):
        """
        Retrieves project, shot, sequence, and task details from the active project in Silhouette FX.

        Returns:
            tuple: A tuple containing the following details:
                - project_name (str): Name of the current project.
                - shot_name (str): Name of the current shot.
                - seq (str): Name of the sequence the shot belongs to.
                - task (str): Name of the current task.

        Note:
            Assumes `fx` is a module or object that provides methods for working with projects in Silhouette FX.
            Assumes `sgtk` and `sg` are objects/modules that provide methods for interacting with Shotgun.

        Raises:
            KeyError: If any required data (project name, shot name, sequence name) is not found in Shotgun queries.
        """
        # selected_items = self.task_table.selectedItems()
        # row = selected_items[0].row()
        id_item = self.read_binary_cache_file()
        project = fx.activeProject().path
        tk = sgtk.sgtk_from_path(str(project))
        context = tk.context_from_path(project)
        project_name = context.project["name"]

        shot = context.entity
        shot_name = shot["name"]

        # shot_data = self.sg.find_one(
        #     "Shot", [["id", "is", context.entity["id"]]], ["sg_sequence"]
        # )
        # seq = shot_data["sg_sequence"]["name"]

        try:
            task = context.step["name"]
        except Exception as e:
            print("Error :", e)
            task = "roto"
        name = self.get_field_name()

        # return project_name, shot_name, seq, task, name, id_item
        return project_name, shot_name, task, name, id_item

    def is_valid_string(self, s):
        # Check if the string contains only alphabetic characters and numbers, no spaces or special characters
        if re.match("^[A-Za-z0-9]+$", s):
            return True
        else:
            return False

    def get_version_from_path(self, path):
        # Get the current Toolkit instance (this requires that your context is already set up)
        tk = sgtk.sgtk_from_path(path)

        # Retrieve the template that matches the path
        template = tk.template_from_path(path)

        # Extract the fields from the path using the template
        fields = template.get_fields(path)

        # Retrieve the version number from the fields
        version = fields.get("version")

        return version

    def review_node_version(self, path):
        # Regular expression to match the version pattern (e.g., _v019)
        version_match = re.search(r"_v(\d+)", path)

        if version_match:
            # Extract and return the version number
            return int(version_match.group(1))
        else:
            return None

    def call_back(self):
        """
        Prepares and displays the Deadline script submission UI
        (`BFSRenderSubmission`) with relevant data.

        Retrieves project, shot, sequence, and task details using `get_data()`, then initializes and displays
        the `BFSRenderSubmission` UI for Deadline script submission.

        Connects the button click signal (`button_clicked`) from `BFSRenderSubmission` to `handle_button_click`.

        Sets the Deadline script submission UI to application modal for exclusive interaction.

        Note:
            Assumes `BFSRenderSubmission` is a class or object representing the Deadline script submission UI.
            Assumes `get_data()` method retrieves necessary project, shot, sequence, and task details.

        Raises:
            KeyError: If required data (project name, shot name, sequence name) is not found in Shotgun queries.

        """
        session_name = ""
        for i in fx.activeProject().sessions:
            session_name = str(i.label)

        if not self.is_valid_string(session_name):
            self.show_error_message(
                "Please ensure that any spaces, special characters, or alphanumeric characters are removed in the Session"
            )
            return
        script_version = self.get_version_from_path(
            os.path.dirname(fx.activeProject().path)
        )
        node_version = True
        review_node_name = []
        for session in fx.activeProject().sessions:
            for output in session.outputs:
                if output.label == "ReviewOutputNode":
                    review_node_version = self.review_node_version(
                        output.properties["path"].value
                    )
                    if script_version != review_node_version:
                        node_version = False
        if node_version is False:
            self.show_error_message("Please create a new Review Output Node")
            return

        data = self.get_data()
        self.deadline_script_ui = BFSRenderSubmission(data, self)
        self.deadline_script_ui.button_clicked.connect(self.handle_button_click)
        self.deadline_script_ui.setWindowModality(Qt.ApplicationModal)
        self.deadline_script_ui.raise_()
        self.deadline_script_ui.activateWindow()
        self.deadline_script_ui.show()

    def ensure_step_field(self, context, fields, id_item, default_step=None):
        """
        Centralized Step-field fallback. Call this immediately after
        `fields = context.as_template_fields(template)` at every call site
        that builds template fields for a Task. Guarantees fields["Step"]
        is populated even when context.step fails to resolve (broken/blank
        Step link on the Task in Shotgrid).

        Raises ValueError if Step truly cannot be determined and no
        default_step was given — callers should catch this and show an
        error / return, rather than letting apply_fields() blow up later.
        """
        if "Step" in fields:
            return fields

        if context.step:
            fields["Step"] = context.step["name"].lower()
            return fields

        task_entity = self.sg.find_one("Task", [["id", "is", int(id_item)]], ["step"])
        if task_entity and task_entity.get("step"):
            fields["Step"] = task_entity["step"]["name"].lower()
            return fields

        if default_step:
            fields["Step"] = default_step
            return fields

        raise ValueError(
            "Could not resolve Step for this task in Shotgrid. "
            "Please check the task's Step assignment."
        )

    def publish_to_sg(self):
        """
        Initiates the publishing process to Shotgun (SG) for a selected task.

        Retrieves necessary project and task details, creates filesystem structure,
        prepares template fields, and registers the publish in Shotgun.

        Updates progress bar in `self.deadline_script_ui` during various stages of publishing.

        Assumes `fx` and `sgtk` are properly initialized and connected to the active project and Shotgun instance.

        Note:
            - Requires `self.deadline_script_ui` to be a valid UI component with an `update_progress_bar` method.
            - Assumes `self.task_table` contains task data with the selected task's information.
            - Assumes `self.json_data` contains necessary metadata for publishing.
        """
        # selected_items = self.task_table.selectedItems()
        # row = selected_items[0].row()
        id_item = self.read_binary_cache_file()
        self.deadline_script_ui.update_progress_bar(50)

        project = fx.activeProject().path
        tk = sgtk.sgtk_from_entity("Task", int(id_item))
        context = tk.context_from_entity("Task", int(id_item))
        tk.create_filesystem_structure("Task", context.task["id"])
        self.deadline_script_ui.update_progress_bar(60)
        template_name = "silhouette_shot_publish"
        template = tk.templates[template_name]
        fields = context.as_template_fields(template)
        user_name = self.current_user  # Assuming this is intentional
        fields["name"] = self.get_field_name()
        sg = tk.shotgun
        r = sg.summarize(
            entity_type="PublishedFile",
            filters=[
                ["task", "is", {"type": "Task", "id": context.task["id"]}],
                ["name", "is", fields["name"] + ".sfx"],
            ],
            summary_fields=[{"field": "version_number", "type": "maximum"}],
        )
        self.deadline_script_ui.update_progress_bar(70)
        fields["version"] = r["summaries"]["version_number"] + 1
        try:
            self.ensure_step_field(context, fields, id_item)
        except ValueError as e:
            self.show_error_message(str(e))
            return
        publish_path = template.apply_fields(fields)
        if not os.path.exists(publish_path):
            os.makedirs(publish_path)

        sgtk.util.filesystem.touch_file(publish_path)
        publish_name = fields["name"] + ".sfx"
        self.deadline_script_ui.update_progress_bar(80)
        project = fx.activeProject()
        version_number = fields["version"]
        update_data = {"created_by": self.get_username()}
        publish_data = sgtk.util.register_publish(
            tk,
            context,
            publish_path,
            publish_name,
            version_number,
            published_file_type="Silhouette Script",
            sg_fields=update_data,
        )

        self.deadline_script_ui.update_progress_bar(90)
        shutil.copy(project.path, publish_path)
        # project.save(publish_path)
        self.deadline_script_ui.update_progress_bar(100)
        self.deadline_script_ui.close()
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TaskListCheck()
    window.show()
    sys.exit(app.exec_())
