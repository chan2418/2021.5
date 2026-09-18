from silhoutee_tool import scan_import_ui as _ui
from PySide2.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QListWidget,
    QPushButton,
    QListWidgetItem,
)
import os
from PySide2.QtGui import QPixmap, QIcon
from PySide2.QtCore import QSize
from PySide2.QtWidgets import QMessageBox
from PySide2 import QtWidgets
import ssl
import sys

sg_utils = "/tools/common/scripts"

sys.path.append(sg_utils)
from render_sg_utils import read
import requests
import re


import fx


class silhoutee_import(_ui.MainWindow, QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(silhoutee_import, self).__init__(parent)
        self.sg = read.SG
        self.show_name = self.set_show()

        self.user_name = self.get_username()
        self.my_task = self.task_list()

        self.set_list_widget()
        self.import_button.clicked.connect(self.import_button_clicked)

    def download_image(self, url, version_id):
        if not url is None:
            response = requests.get(url)
            if response.status_code == 200:
                file_path = f"/tools/silhouette_tools/2021.5/silhoutee_tool/download_image/thumbnail_{version_id}.jpg"
                with open(file_path, "wb") as file:
                    file.write(response.content)
                return file_path
            return None
        else:
            return None

    def set_show(self):
        get_env = os.getenv("TANK_CURRENT_PC")
        show_name = re.search(r"[^/]+$", get_env)[0]
        self.show_heading.setText(show_name)
        show_sg = self.sg.find_one("Project", [["name", "is", show_name]])
        return show_sg

    def get_username(self):
        data = os.getenv("SHOTGUN_DESKTOP_CURRENT_USER")
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        match = re.search(email_pattern, data)
        if match:
            email = match.group(0)
            user_email = email.replace("V", "", 1)
        user_sg = self.sg.find_one("HumanUser", [["login", "is", user_email]])
        return user_sg

    def task_list(self):
        my_tasks = self.sg.find(
            "Task",
            [
                ["project", "is", self.show_name],
                ["task_assignees", "is", [self.user_name]],
            ],
            ["entity.Shot.code", "entity.Asset.code"],
        )
        return my_tasks

    def multiple_version(self, version_data):
        largest_id = None
        latest_file = {}
        image_file = {}
        for version in version_data:
            if version["published_files"]:
                file_id = version["published_files"][0]["id"]
                published_file_path = self.sg.find_one(
                    "PublishedFile",
                    [["id", "is", file_id]],
                    ["sg_filepath", "image", "code"],
                )
                if published_file_path["sg_filepath"]:
                    self.file_path[published_file_path["id"]] = published_file_path[
                        "sg_filepath"
                    ]
                if published_file_path["image"]:
                    image_file[published_file_path["id"]] = published_file_path["image"]
                if published_file_path["code"]:
                    latest_file[published_file_path["id"]] = published_file_path["code"]
        # Get the largest id
        largest_id = max(latest_file.keys())

        if image_file is not None:
            image = image_file[largest_id]
            image_path = self.download_image(image, largest_id)
        if latest_file is not None:
            code_name = latest_file[largest_id]
            item = QListWidgetItem(code_name)
        return image_path, item

    def set_list_widget(self):
        items = []
        self.file_path = {}
        for task in self.my_task:
            online_vesion_data = self.sg.find(
                "Version",
                [
                    ["project", "is", self.show_name],
                    ["entity.Shot.code", "is", task["entity.Shot.code"]],
                    ["sg_task.Task.content", "is", "Plate_Proxy"],
                    ["published_files", "is_not", None],
                ],
                ["id", "published_files", "image"],
            )
            if len(online_vesion_data) > 1:
                image_path, item = self.multiple_version(online_vesion_data)
            else:
                online_vesion = online_vesion_data[0]
                if online_vesion:
                    image_path = self.download_image(
                        online_vesion["image"], online_vesion["id"]
                    )

                    item = QListWidgetItem(online_vesion["published_files"][0]["name"])
                    if online_vesion.get("published_files"):
                        published_file_path = self.sg.find_one(
                            "PublishedFile",
                            [["id", "is", online_vesion["published_files"][0]["id"]]],
                            ["sg_filepath"],
                        )
                        self.file_path[online_vesion["published_files"][0]["name"]] = (
                            published_file_path["sg_filepath"]
                        )
            pixmap = QPixmap(image_path)
            scaled_pixmap = pixmap.scaled(300, 200)
            item.setIcon(QIcon(scaled_pixmap))
            items.append(item)

        self.list_tasks.clear()
        self.list_tasks.setIconSize(QSize(100, 100))
        for item in items:
            self.list_tasks.addItem(item)

    def on_task_changed(self):
        current_task = self.combo_task.currentText()
        found_items = [item for item in self.my_task if item["name"] == current_task]
        self.set_list_widget(found_items[0])

    def import_button_clicked(self):
        selected_items = self.list_tasks.selectedItems()

        if selected_items:
            selected_texts = [item.text() for item in selected_items]
            file_path = self.file_path[selected_texts[0]]
            project = fx.activeProject()
            session = fx.activeSession()
            res = fx.Source(file_path)
            res_src = project.addItem(res)
        else:
            print("No items selected.")

        if selected_items:
            QMessageBox.information(self, "Imported", "\n".join(selected_texts))
        else:
            QMessageBox.information(self, "Selected Items", "No items selected.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = silhoutee_import()
    window.show()
    sys.exit(app.exec_())
