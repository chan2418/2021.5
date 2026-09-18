import os
import sys

from PySide2.QtCore import Qt, Signal
from PySide2.QtWidgets import *


class RenderSettingsUI(QWidget):
    publish_signal = Signal()
    version_update_signal = Signal()

    def __init__(self):
        super(RenderSettingsUI, self).__init__()
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout(self)

        self.directoryPathInput = QLineEdit(self)
        self.directoryPathInput.setReadOnly(True)
        self.showNameInput = QLineEdit(self)
        self.showNameInput.setReadOnly(True)
        self.shotNameInput = QLineEdit(self)
        self.shotNameInput.setReadOnly(True)
        self.versionDropdown = QLineEdit(self)
        self.versionDropdown.setReadOnly(True)
        self.startFrameInput = QLineEdit(self)
        self.endFrameInput = QLineEdit(self)
        self.reviewerinput = QComboBox(self)
        self.plate_name = QComboBox(self)
        self.user_plate_name = QLineEdit(self)

        # self.plate_name = QComboBox(self)

        form_layout = QFormLayout()
        # form_layout.addRow("Approved Versions:", self.approvedVersionList)
        form_layout.addRow("Directory Path:", self.directoryPathInput)
        form_layout.addRow("Show Name:", self.showNameInput)
        form_layout.addRow("Shot Name:", self.shotNameInput)
        form_layout.addRow("Version:", self.versionDropdown)
        form_layout.addRow("Plate:", self.plate_name)
        form_layout.addRow("Plate Name:", self.user_plate_name)
        form_layout.addRow("Stat Frame:", self.startFrameInput)
        form_layout.addRow("End Frame:", self.endFrameInput)
        form_layout.addRow("Reviewer:", self.reviewerinput)

        self.global_checkbox = QCheckBox("Global (Normal Matte Render)", self)
        self.shape_checkbox = QCheckBox("Shape (Layer-wise Render)", self)

        form_layout.addRow(self.global_checkbox)
        form_layout.addRow(self.shape_checkbox)

        # Make checkboxes mutually exclusive
        self.global_checkbox.toggled.connect(
            lambda checked: self.shape_checkbox.setChecked(False) if checked else None
        )
        self.shape_checkbox.toggled.connect(
            lambda checked: self.global_checkbox.setChecked(False) if checked else None
        )

        self.endFrameInput.setStyleSheet("""
    QComboBox {
        background-color: #2b2b2b;
        color: #f0f0f0;
        border: 1px solid #444;
        padding: 4px;
    }
    QComboBox::drop-down {
        border-left: 1px solid #444;
        background-color: #3c3c3c;
    }
    QComboBox QAbstractItemView {
        background-color: #2b2b2b;
        color: #f0f0f0;
        selection-background-color: #444444;
        selection-color: white;
    }
        """)

        version_description_widget = QWidget(self)
        version_description_layout = QVBoxLayout(version_description_widget)
        self.doneInput = QLineEdit(self)
        self.doneInput.setPlaceholderText("Submission NOtes")
        version_description_layout.addWidget(self.doneInput)
        # self.toDoInput = QLineEdit(self)
        # self.toDoInput.setPlaceholderText("To do")
        # version_description_layout.addWidget(self.toDoInput)
        # self.queryInput = QLineEdit(self)
        # self.queryInput.setPlaceholderText("Query")
        # version_description_layout.addWidget(self.queryInput)

        form_layout.addRow("Submission Notes:", version_description_widget)

        # Create a horizontal layout for template button and tree
        tree_container = QWidget()
        tree_layout = QHBoxLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)

        # Add template input button
        self.templateButton = QPushButton("Template Input", self)
        self.templateButton.setFixedWidth(100)  # Set a fixed width for the button
        tree_layout.addWidget(self.templateButton, alignment=Qt.AlignTop)

        # Add tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setColumnCount(1)
        self.tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        tree_layout.addWidget(self.tree)

        main_layout.addLayout(form_layout)
        main_layout.addWidget(tree_container)

        button_layout = QHBoxLayout()

        self.publishButton = QPushButton("Create Package", self)
        button_layout.addWidget(self.publishButton)

        self.progressBar = QProgressBar(self)
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(0)
        self.progressBar.setVisible(False)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.progressBar)

    def check_reviwer(self):
        if not self.reviewerinput.currentText().strip():
            print("Reviewer field is empty")
            return None
        else:
            return self.reviewerinput.currentText().strip()

    def populate_table_widget(self, render_list):
        self.table.setRowCount(len(render_list))
        self.table.setHorizontalHeaderLabels(["Upload File Path"])
        for row_index, (_, file_path) in enumerate(render_list.items()):
            file_path_item = QTableWidgetItem(file_path)
            self.table.setItem(row_index, 0, file_path_item)
        self.table.resizeColumnsToContents()

    def version_description_error(self):
        done_filled = bool(self.doneInput.text().strip())
        # to_do_filled = bool(self.toDoInput.text().strip())
        # query_filled = bool(self.queryInput.text().strip())
        # filled_count = sum([done_filled, to_do_filled, query_filled])

        # if filled_count < 2:
        #     empty_fields = []
        #     if not done_filled:
        #         empty_fields.append("Done")
        #     if not to_do_filled:
        #         empty_fields.append("To do")
        #     if not query_filled:
        #         empty_fields.append("Query")

        #     QMessageBox.warning(self, "Incomplete Description", "Please fill at least two of the following fields: {}".format(", ".join(empty_fields)))
        #     return None
        if not done_filled:
            QMessageBox.warning(
                self, "Incomplete Description", "Please fill the Description"
            )

        else:
            version_description_parts = []
            if done_filled:
                version_description_parts.append({self.doneInput.text().strip()})
            # if to_do_filled:
            #     version_description_parts.append(f"To do: {self.toDoInput.text().strip()}")
            # if query_filled:
            #     version_description_parts.append(f"Query: {self.queryInput.text().strip()}")
            return self.doneInput.text().strip()

    def update_progress_bar(self, value):
        self.progressBar.setValue(value)


def show_render_settings_ui():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    render_ui = RenderSettingsUI()
    render_ui.setWindowTitle("B Package")
    render_ui.resize(1200, 800)
    render_ui.show()

    return render_ui, app
