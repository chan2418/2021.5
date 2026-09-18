import sys
sys.path.append(
    "/tools/packages/python/3.9.6/platform-linux/arch-x86_64/os-rocky-9.2/python/site-packages"
)
import os
import fileseq
import yaml
from PySide2.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QScrollArea, QWidget, QPushButton, QFileDialog, QMessageBox, QInputDialog
)
from PySide2.QtCore import Qt
import fx
from fx import *


class DynamicDialog(QDialog):
    def __init__(self, yaml_data, initial_inputs=0, parent=None):
        super(DynamicDialog, self).__init__(parent)
        self.setWindowTitle("Template Input Dialog")
        self.setMinimumWidth(800)
        self.main_layout = QVBoxLayout(self)
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)

        self.headers = {}
        self.initial_inputs = initial_inputs
        self.build_ui(yaml_data)

        self.scroll_area.setWidget(self.scroll_widget)
        self.main_layout.addWidget(self.scroll_area)

        self.proceed_button = QPushButton("Proceed")
        self.proceed_button.clicked.connect(self.validate_and_proceed)
        self.main_layout.addWidget(self.proceed_button)

        self.result_data = {}

    def build_ui(self, yaml_data):
        for header, labels in yaml_data.items():
            self.add_header(header, labels)

    def get_outpath(self):
        ouput_path = None
        project = fx.activeProject()
        for session in project.sessions:
            for node in session.nodes:
                if node.type == "OutputNode":
                    ouput_path = node.properties["path"].value
        return ouput_path


    def add_header(self, header_name, labels):
        header_layout = QHBoxLayout()
        header_label = QLabel(header_name)
        header_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(header_label)

        add_button = QPushButton("+")
        add_button.setFixedSize(30, 20)
        add_button.clicked.connect(lambda: self.add_label_dialog(header_name))
        header_layout.addWidget(add_button)

        remove_button = QPushButton("-")
        remove_button.setFixedSize(30, 20)
        remove_button.clicked.connect(lambda: self.remove_label_dialog(header_name))
        header_layout.addWidget(remove_button)

        browse_button = QPushButton("Browse")
        browse_button.setFixedSize(60, 20)
        output_path = self.get_outpath()
        output_path = os.path.dirname(os.path.dirname(output_path))
        browse_button.clicked.connect(lambda: self.browse_files(header_name,output_path))
        header_layout.addWidget(browse_button)

        self.scroll_layout.addLayout(header_layout)

        grid_layout = QGridLayout()
        self.headers[header_name] = {"layout": grid_layout, "labels": {}}

        # Populate with initial inputs or existing labels
       
        for i in range(self.initial_inputs):
            self.add_label_to_grid(header_name)

        self.scroll_layout.addLayout(grid_layout)

    def add_label_to_grid(self, header_name, value=None):
        grid_layout = self.headers[header_name]["layout"]
        labels = self.headers[header_name]["labels"]

        # Automatically generate the label name
        label_name = f"matte{len(labels) + 1}"

        row = len(labels)
        label_widget = QLabel(label_name)
        line_edit = QLineEdit()
        line_edit.setText(value if value else "")

        grid_layout.addWidget(label_widget, row, 0)
        grid_layout.addWidget(line_edit, row, 1)

        labels[label_name] = (label_widget, line_edit)

    # def browse_files(self, header_name):
    #     labels = self.headers[header_name]["labels"]

    #     if not labels:
    #         QMessageBox.warning(self, "No Labels", f"No labels available under '{header_name}' to associate files.")
    #         return

    #     label_names = list(labels.keys())
    #     label_name, ok = QInputDialog.getItem(self, "Select Label", "Choose the label for the file:", label_names, 0, False)

    #     if not ok or not label_name:
    #         return

    #     file_path, _ = QFileDialog.getOpenFileName(self, "Select File")
    #     if not file_path:
    #         return

    #     try:
    #         file_sequences = fileseq.findSequencesOnDisk(file_path)
    #         sequence = file_sequences[0]
    #         start_frame = sequence.start()
    #         end_frame = sequence.end()
    #         if start_frame != end_frame:
    #             padding = sequence.zfill()
    #             padding_format = f"%0{padding}d"
    #             file_extension = sequence.extension()
    #             base_name = sequence.basename()

    #             full_path = os.path.join(os.path.dirname(file_path), base_name + padding_format + file_extension)
    #             self.update_label(header_name, label_name, full_path)
    #         else:
    #             self.update_label(header_name, label_name, file_path)
    #     except Exception as e:
    #         QMessageBox.critical(self, "Error", f"Failed to process the file: {e}")

    def browse_files(self, header_name,render_directory=None):
        labels = self.headers[header_name]["labels"]
        if not labels:
            QMessageBox.warning(self, "No Labels", f"No labels available under '{header_name}' to associate files.")
            return
            
        label_names = list(labels.keys())
        label_name, ok = QInputDialog.getItem(self, "Select Label", "Choose the label for the file:", label_names, 0, False)
        if not ok or not label_name:
            return

        # Specify your default directory path here
        default_directory = render_directory
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File",
            default_directory,  # This sets the initial directory
            "All Files (*.*)"  # Optional: you can specify file filters here
        )
        
        if not file_path:
            return
            
        try:
            file_sequences = fileseq.findSequencesOnDisk(file_path)
            sequence = file_sequences[0]
            start_frame = sequence.start()
            end_frame = sequence.end()
            if start_frame != end_frame:
                padding = sequence.zfill()
                padding_format = f"%0{padding}d"
                file_extension = sequence.extension()
                base_name = sequence.basename()
                full_path = os.path.join(os.path.dirname(file_path), base_name + padding_format + file_extension)
                self.update_label(header_name, label_name, full_path)
            else:
                self.update_label(header_name, label_name, file_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to process the file: {e}")

    def update_label(self, header_name, label_name, value):
        labels = self.headers[header_name]["labels"]
        if label_name in labels:
            _, line_edit = labels[label_name]
            line_edit.setText(value)

    def add_label_dialog(self, header_name):
        self.add_label_to_grid(header_name)

    def remove_label_dialog(self, header_name):
        labels = self.headers[header_name]["labels"]

        if not labels:
            QMessageBox.warning(self, "No Labels", f"No labels available under '{header_name}' to remove.")
            return

        label_name = list(labels.keys())[-1]
        label_widget, line_edit = labels.pop(label_name)
        layout = self.headers[header_name]["layout"]

        layout.removeWidget(label_widget)
        layout.removeWidget(line_edit)

        label_widget.deleteLater()
        line_edit.deleteLater()

    def validate_and_proceed(self):
        self.result_data = {}

        for header, data in self.headers.items():
            labels = data["labels"]
            header_data = {}

            for label_name, (_, line_edit) in labels.items():
                value = line_edit.text().strip()
                if not value:
                    QMessageBox.warning(self, "Validation Error", f"Please fill all fields in '{header}'!")
                    return

                header_data[label_name] = value

            self.result_data[header] = header_data
            print("____+++++++",self.result_data)

        self.accept()
