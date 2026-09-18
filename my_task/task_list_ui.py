from PySide2 import QtWidgets
from PySide2.QtCore import QDate, Qt
from PySide2.QtGui import QColor, QPalette
from PySide2.QtWidgets import *


class TwoFieldDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(TwoFieldDialog, self).__init__(parent)

        self.setWindowTitle("New Task Label")

        # Layout and widgets
        layout = QtWidgets.QVBoxLayout(self)

        self.label_input = QtWidgets.QLineEdit(self)
        self.label_input.setPlaceholderText("Enter Task Label")
        layout.addWidget(QtWidgets.QLabel("Task Label:"))
        layout.addWidget(self.label_input)

        self.layer_input = QtWidgets.QLineEdit(self)
        self.layer_input.setPlaceholderText("Enter Layer Count")
        layout.addWidget(QtWidgets.QLabel("Layer Count:"))
        layout.addWidget(self.layer_input)

        # OK and Cancel buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, self
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_inputs(self):
        return self.label_input.text(), self.layer_input.text()


class MainWindow(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("B Prod")
        self.setGeometry(80, 80, 1200, 600)
        self.json_data = self.load_json()
        # Set dark theme
        self.set_dark_theme()
        self.new_label = None
        self.layer_count = None
        self.working_file_data = []
        self.table_widget = QTableWidget()
        self.setup_table_widget(self.table_widget)
        self.working_combo_box = QtWidgets.QMenuBar(self)
        central_widget = QWidget()
        self.button_layout = QHBoxLayout()
        # self.custom_node_button = QPushButton("Output Node")
        self.master_task_button = QPushButton("Master Task")
        self.open_button = QPushButton("Open")
        self.new_button = QPushButton("New File")
        self.import_button = QPushButton("Import")
        # self.save_button = QPushButton("Save As Next Version")
        # self.publish_button = QPushButton("Publish")
        self.button_layout.addStretch()
        # self.button_layout.addWidget(self.custom_node_button)
        self.button_layout.addWidget(self.master_task_button)
        self.button_layout.addWidget(self.open_button)
        self.button_layout.addWidget(self.new_button)
        self.button_layout.addWidget(self.import_button)
        # self.button_layout.addWidget(self.save_button)
        # self.button_layout.addWidget(self.publish_button)

        main_layout = QVBoxLayout(central_widget)
        self.setLayout(main_layout)

        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        self.my_tasks_tab = QWidget()
        self.assets_tab = QWidget()
        self.shots_tab = QWidget()

        self.tab_widget.addTab(self.my_tasks_tab, "My Tasks")
        self.tab_widget.addTab(self.assets_tab, "Assets")
        self.tab_widget.addTab(self.shots_tab, "Shots")
        main_layout.addLayout(self.button_layout)
        self.new_button.clicked.connect(self.new_project_creation)

        self.create_my_tasks_tab()
        self.create_assets_tab()
        self.create_shots_tab()

    def set_dark_theme(self):
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(56, 56, 56))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(56, 56, 56))
        dark_palette.setColor(QPalette.AlternateBase, QColor(56, 56, 56))
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(56, 56, 56))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        self.setPalette(dark_palette)
        self.setStyleSheet("""
        QWidget {
            background-color: #383838;
            color: white;
        }
        QLineEdit, QComboBox, QCheckBox, QPushButton {
            background-color: #383838;
            color: white;
            border: 1px solid #555555;
            padding: 5px;
        }
        QTabWidget::pane {
            border: 1px solid #555555;
        }
        QTabBar::tab {
            background: #383838;
            color: white;
            padding: 10px;
            border: 1px solid #555555;
        }
        QTabBar::tab:selected {
            background: #555555;
        }
        QSplitter::handle {
            background: #555555;
        }
        QPushButton {
            background-color: #383838;
            color: white;
            border: 1px solid #555555;
            padding: 8px;
            font-size: 11px;
            font-weight: bold;
        }
        QPushButton:pressed {
            background-color: #555555;
        }
    """)

    def setup_table_widget(self, table_widget):
        table_widget.setMouseTracking(True)  # Enable mouse tracking
        table_widget.cellEntered.connect(
            lambda row, col: self.handle_mouse_move_event(table_widget, row, col)
        )

    def handle_mouse_move_event(self, table_widget, row, col):
        item = table_widget.item(row, col)
        if item:
            tooltip_text = f"""
            <b>{item.text()}</b><br>
            Path: {self.working_file_path()}<br>
            """
            table_widget.setToolTip(tooltip_text)

            # Show the tooltip at the center of the viewport of the QTableWidget
            viewport_center = table_widget.viewport().rect().center()
            global_position = table_widget.viewport().mapToGlobal(viewport_center)
            QToolTip.showText(global_position, tooltip_text)
        else:
            QToolTip.hideText()

    def show_new_label_dialog_(self):
        dialog = TwoFieldDialog(self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            task_label, layer_count = dialog.get_inputs()
            print("_+_+_+_+_+++", task_label, layer_count)
            if task_label and layer_count:
                self.new_label = task_label
                self.add_label_to_json(
                    task_label
                )  # Modify as needed ilam commanded for error
                return task_label, layer_count
        return None, None

    def show_new_label_dialog(self):
        text, ok = QtWidgets.QInputDialog.getText(self, "New Task Label", "Task Label:")

        if ok:
            self.new_label = text
            self.add_label_to_json(text)  # ilam commanded for error
            return text, "text"
        else:
            return None, None

    def create_layer_dialog(self):
        text, ok = QtWidgets.QInputDialog.getText(
            self, "New Layer Count", "Layer Count:"
        )
        if ok:
            self.layer_count = text
            return text
        else:
            return None

    def calculate_table_width(self, table_name):
        total_width = 0

        # Sum up the widths of all columns
        for column in range(table_name.columnCount()):
            total_width += table_name.columnWidth(column)

        # Add the width of the vertical header
        total_width += table_name.verticalHeader().width()

        # Add the width of the scroll bar, if it's visible
        if table_name.verticalScrollBar().isVisible():
            total_width += table_name.verticalScrollBar().width()

        # Add the table's margins (if any)
        total_width += (
            table_name.contentsMargins().left() + table_name.contentsMargins().right()
        )

        return total_width

    def create_my_tasks_tab(self):
        layout = QVBoxLayout(self.my_tasks_tab)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)  # Set handle width to make it more visible

        left_frame = QFrame()
        left_layout = QVBoxLayout(left_frame)

        # Create a horizontal layout for the filters and search box
        search_filter_layout = QHBoxLayout()

        self.filter_combo = QComboBox()
        # if os.getlogin() == "chandru":
        self.filter_combo.addItems(["ip", "pentec"])
        # else:
        #     self.filter_combo.addItems(["All", 'opn', 'bidreq', 'pbdep', 'penawd', 'awd', 'notawd', 'schled', 'pendep', 'pidep', 'ip', 'paused', 'penrev', 'pensup', 'pentec', 'kbk', 'bnk', 'delmas', 'deldep', 'pentfr', 'pcr', 'clikbk', 'apr', 'dlvr', 'hld', 'omt', 'omtctd', 'act', 'nr'])

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search My Tasks")

        self.date_filter_combo = QComboBox()
        self.date_filter_combo.addItems(
            [
                "All",
                "Today",
                "This Week",
                "Next Week",
                "Next Month",
                "Future",
                "Last Week",
                "Last Month",
                "Past",
            ]
        )

        search_filter_layout.addWidget(self.filter_combo)
        self.filter_combo.currentIndexChanged.connect(
            lambda index: self.filter_status(
                self.filter_combo.currentText(), self.task_table, 3
            )
        )
        search_filter_layout.addWidget(self.search_box)
        search_filter_layout.addWidget(self.date_filter_combo)
        self.search_box.textChanged.connect(
            lambda text: self.filter_table(text, self.task_table)
        )

        # if os.getlogin() == "chandru":
        self.task_table = QTableWidget(0, 5)  # 0 rows, 5 columns
        self.task_table.setHorizontalHeaderLabels(
            ["Shot", "Tasks", "Status", "Department", "id"]
        )
        # else:
        #     self.task_table = QTableWidget(0, 6)  # 0 rows, 5 columns
        #     self.task_table.setHorizontalHeaderLabels(["Shot", "Task Name", "Show Name", "Status", "Due Date","id"])

        self.task_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # if os.getlogin() == "chandru":
        self.task_table.setColumnHidden(4, True)
        # else:
        # self.task_table.setColumnHidden(5, True)

        # Enable word wrap
        self.task_table.setWordWrap(True)

        # Set the row height and column width policies
        self.task_table.verticalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeToContents
        )
        self.task_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeToContents
        )

        # Optionally, set a maximum row height to ensure readability
        self.task_table.verticalHeader().setDefaultSectionSize(
            50
        )  # Set a default row height
        self.task_table.verticalHeader().setMaximumSectionSize(
            100
        )  # Set a maximum row height

        left_layout.addLayout(search_filter_layout)
        left_layout.addWidget(self.task_table)
        self.task_table.setStyleSheet("""
        QTableWidget {
            background-color: #383838;
            color: white;
        }
        QTableWidget QHeaderView::section {
            background-color: #555555;
            color: white;
        }
        """)

        right_frame = QFrame()
        right_layout = QVBoxLayout(right_frame)
        filter_layout = QHBoxLayout()

        self.tab_widget_right = QTabWidget()
        self.tab_all = QWidget()
        self.tab_working = QListWidget()
        self.tab_publish = QWidget()
        self.tab_scan = QWidget()

        self.tab_widget_right.addTab(self.tab_all, "All")
        self.tab_widget_right.addTab(self.tab_working, "Working")
        self.tab_widget_right.addTab(self.tab_publish, "Publish")
        self.tab_widget_right.addTab(self.tab_scan, "Scan")

        self.publish_list = QListWidget()
        self.file_filter_combo = QComboBox()
        self.file_filter_combo.addItems(["All", "Working", "publish", "Scan"])
        filter_layout.addWidget(self.file_filter_combo)
        self.all_versions_checkbox = QCheckBox("All Versions")
        filter_layout.addWidget(self.all_versions_checkbox)
        filter_layout.addStretch()
        refresh_button = QPushButton("↺")
        refresh_button.setToolTip("Refresh")
        refresh_button.setFixedSize(30, 30)  # Slightly increase the size of the button
        font = refresh_button.font()
        font.setPointSize(20)  #
        filter_layout.addWidget(refresh_button)

        right_layout.addLayout(filter_layout)
        refresh_button.clicked.connect(self.get_selected_task_data)
        # right_layout.addWidget(self.all_versions_checkbox)
        right_layout.addWidget(self.tab_widget_right)

        # Add the publish list to the "All" tab
        tab_all_layout = QVBoxLayout(self.tab_all)
        tab_all_layout.addWidget(self.publish_list)
        self.publish_list_version = QListWidget()
        tab_version_layout = QVBoxLayout(self.tab_scan)
        tab_version_layout.addWidget(self.publish_list_version)
        self.working_list = QListWidget()
        tab_working_layout = QVBoxLayout(self.tab_working)
        self.table_widget.setColumnCount(2)  # Adjust column count as needed
        self.table_widget.setColumnWidth(0, 300)
        self.table_widget.setColumnWidth(1, 80)
        self.table_widget.horizontalHeader().setVisible(False)  # Hide horizontal header
        self.table_widget.setEditTriggers(
            QTableWidget.NoEditTriggers
        )  # Disable editing
        self.table_widget.setEditTriggers(
            QTableWidget.NoEditTriggers
        )  # Disable editing
        self.table_widget.setStyleSheet(
            "QTableWidget::item { border-right: 0px; }"
        )  # Remove vertical borders
        tab_working_layout.addWidget(self.table_widget)
        self.published_file_list = QListWidget()
        tab_publish_layout = QVBoxLayout(self.tab_publish)
        tab_publish_layout.addWidget(self.published_file_list)
        self.setStyleSheet("""

        """)
        self.publish_list.setStyleSheet("""
            QListWidget::item {
                border: 2px solid #383838;
                padding: 10px;
                margin: 5px;
            }
            QListWidget::item:selected {
                background-color: #2F8BC4;
            }
        """)
        self.published_file_list.setStyleSheet("""
            QListWidget::item {
                border: 2px solid #383838;
                padding: 10px;
                margin: 5px;
            }
            QListWidget::item:selected {
                background-color: #2F8BC4;
            }
        """)
        self.working_list.setStyleSheet("""
            QListWidget::item {
                border: 2px solid #555555;
                padding: 10px;
                margin: 5px;
            }
            QListWidget::item:selected {
                background-color: #2F8BC4;
            }
        """)
        splitter.addWidget(left_frame)
        splitter.addWidget(right_frame)
        layout.addWidget(splitter)

        self.date_filter_combo.currentIndexChanged.connect(self.filter_tasks)

        left_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        table_width = self.calculate_table_width(self.task_table) + 270

        # Set initial sizes for the splitter
        splitter.setSizes([table_width, 800])  # Adjust as needed

    def populate_table(self):
        """
        Populates the table with the working file data.
        This method updates the table in the UI with the data from `self.working_file_data`.
        Each row in the table will display the latest file and a combo box with the list of all versions.
        """
        self.table_widget.setRowCount(len(self.working_file_data))

        for row, rowData in enumerate(self.working_file_data):
            # Ensure the first item in rowData is a string
            if isinstance(rowData[0], str):
                text_item = QTableWidgetItem(rowData[0])
                self.table_widget.setItem(row, 0, text_item)
            else:
                continue

            # Create a new QComboBox for each row
            versionComboBox = QtWidgets.QComboBox(self)

            # Clear the existing items in the combo box before adding new ones
            versionComboBox.clear()
            versions = rowData[1]
            versions.sort(key=lambda x: x[1:])
            for version in versions:
                versionComboBox.addItem(version)

            if versions:  # Ensure there are versions to choose from
                latest_version = max(versions)
                versionComboBox.setCurrentText(latest_version)

            self.table_widget.setCellWidget(row, 1, versionComboBox)
            versionComboBox.currentIndexChanged.connect(self.version_change)

        self.setStyleSheet("""
            QWidget {
                background-color: #383838;
                color: white;
            }
            QLineEdit, QComboBox, QCheckBox, QPushButton {
                background-color: #383838;
                color: white;
                border: 1px solid #555555;
                padding: 5px;
            }""")

    def filter_tasks(self):
        filter_option = self.date_filter_combo.currentText()
        filtered_data = self.apply_date_filter(self.data, filter_option)

        self.publish_list.clear()  # Clear the list widget

        for task in filtered_data:
            row_position = self.publish_list.count()
            self.publish_list.addItem(task["content"])

    def apply_date_filter(self, data, filter_option):
        today = QDate.currentDate()
        filtered_data = []

        for task in data:
            due_date = QDate.fromString(task["due_date"], "yyyy-MM-dd")
            if filter_option == "All":
                filtered_data.append(task)
            elif filter_option == "Today" and due_date == today:
                filtered_data.append(task)
            elif filter_option == "This Week" and self.is_in_week(due_date, today):
                filtered_data.append(task)
            elif filter_option == "Next Week" and self.is_in_next_week(due_date, today):
                filtered_data.append(task)
            elif filter_option == "Next Month" and self.is_in_next_month(
                due_date, today
            ):
                filtered_data.append(task)
            elif filter_option == "Future" and due_date > today:
                filtered_data.append(task)
            elif filter_option == "Last Week" and self.is_in_last_week(due_date, today):
                filtered_data.append(task)
            elif filter_option == "Last Month" and self.is_in_last_month(
                due_date, today
            ):
                filtered_data.append(task)
            elif filter_option == "Past" and due_date < today:
                filtered_data.append(task)

        return filtered_data

    def is_in_week(self, due_date, today):
        start_of_week = today.addDays(-(today.dayOfWeek() - 1))

    def is_in_week(self, due_date, today):
        start_of_week = today.addDays(-(today.dayOfWeek() - 1))
        end_of_week = start_of_week.addDays(6)
        return start_of_week <= due_date <= end_of_week

    def is_in_next_week(self, due_date, today):
        start_of_next_week = today.addDays(7 - (today.dayOfWeek() - 1))
        end_of_next_week = start_of_next_week.addDays(6)
        return start_of_next_week <= due_date <= end_of_next_week

    def is_in_next_month(self, due_date, today):
        next_month = today.addMonths(1)
        return (
            next_month.year() == due_date.year()
            and next_month.month() == due_date.month()
        )

    def is_in_last_week(self, due_date, today):
        end_of_last_week = today.addDays(-(today.dayOfWeek()))
        start_of_last_week = end_of_last_week.addDays(-6)
        return start_of_last_week <= due_date <= end_of_last_week

    def is_in_last_month(self, due_date, today):
        last_month = today.addMonths(-1)
        return (
            last_month.year() == due_date.year()
            and last_month.month() == due_date.month()
        )

    def create_assets_tab(self):
        layout = QVBoxLayout(self.assets_tab)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)  # Set handle width to make it more visible

        # Left frame for search, asset list, and pipeline steps
        left_frame = QFrame()
        left_layout = QVBoxLayout(left_frame)
        search_filter_layout = QHBoxLayout()

        self.asset_filter_combo = QComboBox()
        self.asset_filter_combo.addItems(["All", "Working", "Publishes"])

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search Assets")

        self.asset_date_filter_combo = QComboBox()
        self.asset_date_filter_combo.addItems(
            [
                "All",
                "Today",
                "This Week",
                "Next Week",
                "Next Month",
                "Future",
                "Last Week",
                "Last Month",
                "Past",
            ]
        )

        search_filter_layout.addWidget(self.asset_filter_combo)
        search_filter_layout.addWidget(self.search_box)
        search_filter_layout.addWidget(self.asset_date_filter_combo)
        left_layout.addLayout(search_filter_layout)

        left_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        left_splitter = QSplitter(Qt.Vertical)
        left_splitter.setHandleWidth(1)  # Set handle width to make it more visible

        # Asset List Widget
        self.asset_list_widget = QListWidget()

        asset_list_layout = QVBoxLayout()
        asset_list_layout.addWidget(self.asset_list_widget)

        asset_list_frame = QFrame()
        asset_list_frame.setLayout(asset_list_layout)

        # Filter by Pipeline Step Widget
        filter_layout = QVBoxLayout()
        filter_label = QLabel("Filter by Pipeline Step")

        self.pipeline_step_list = QListWidget()
        pipeline_steps = [
            "Art",
            "Art_OS",
            "Cloth",
            "Cloth_OS",
            "Concept",
            "Concept Art_OS",
            "Design",
            "Design_OS",
            "Environment",
            "Environment_OS",
            "Groom",
            "Groom_OS",
        ]

        for step in pipeline_steps:
            item = QListWidgetItem(step)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.pipeline_step_list.addItem(item)

        select_buttons_layout = QHBoxLayout()
        self.select_all_button = QPushButton("Select All")
        self.select_none_button = QPushButton("Select None")

        select_buttons_layout.addWidget(self.select_all_button)
        select_buttons_layout.addWidget(self.select_none_button)

        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.pipeline_step_list)
        filter_layout.addLayout(select_buttons_layout)

        filter_frame = QFrame()
        filter_frame.setLayout(filter_layout)

        # Add both frames to the vertical splitter
        left_splitter.addWidget(asset_list_frame)
        left_splitter.addWidget(filter_frame)
        left_splitter.setSizes(
            [200, 200]
        )  # Initial sizes for asset list and filter list (50% each)

        # Add the search box and the left splitter to the left layout
        left_layout.addWidget(left_splitter)

        # Right frame for asset details
        right_frame = QFrame()
        right_layout = QVBoxLayout(right_frame)

        top_filter_layout = QHBoxLayout()
        search_work_files = QLineEdit()
        search_work_files.setPlaceholderText("Search Work Files")
        top_filter_layout.addWidget(search_work_files)
        refresh_button = QPushButton("↺")
        refresh_button.setToolTip("Refresh")
        top_filter_layout.addWidget(refresh_button)
        self.assets_list = QListWidget()
        self.all_versions_checkbox = QCheckBox("All Versions")

        right_layout.addLayout(top_filter_layout)
        right_layout.addWidget(self.all_versions_checkbox)
        right_layout.addWidget(self.assets_list)

        # Adding frames to splitter
        splitter.addWidget(left_frame)
        splitter.addWidget(right_frame)

        layout.addWidget(splitter)

        # Connect signals
        self.select_all_button.clicked.connect(self.select_all_pipeline_steps)
        self.select_none_button.clicked.connect(self.select_none_pipeline_steps)

        # Set initial sizes for splitter
        splitter.setSizes([200, 800])  # Adjust as needed

    def select_all_pipeline_steps(self):
        for index in range(self.pipeline_step_list.count()):
            item = self.pipeline_step_list.item(index)
            item.setCheckState(Qt.Checked)

    def on_publish_item_clicked(self, item):
        """Show file details when publish list item is clicked"""
        print("run_____________________")
        if item:
            file_name = item.text()
            # Update the details table with file info
            details = [
                ["File Name", file_name],
                ["Size", "125 MB"],
                ["Date", "2024-01-15"],
                ["Version", "v003"],
                ["Status", "Published"],
            ]

            self.details_table.setRowCount(len(details))
            for row, (prop, value) in enumerate(details):
                self.details_table.setItem(row, 0, QTableWidgetItem(prop))
                self.details_table.setItem(row, 1, QTableWidgetItem(value))

    def select_none_pipeline_steps(self):
        for index in range(self.pipeline_step_list.count()):
            item = self.pipeline_step_list.item(index)
            item.setCheckState(Qt.Unchecked)

    def create_shots_tab(self):
        layout = QVBoxLayout(self.shots_tab)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)  # Set handle width to make it more visible

        left_frame = QFrame()
        left_layout = QVBoxLayout(left_frame)

        # Create a horizontal layout for the filters and search box
        search_filter_layout = QHBoxLayout()

        self.shot_filter_combo = QComboBox()
        self.shot_filter_combo.addItems(
            [
                "All",
                "opn",
                "bidreq",
                "pbdep",
                "penawd",
                "awd",
                "notawd",
                "schled",
                "pendep",
                "pidep",
                "ip",
                "paused",
                "penrev",
                "pensup",
                "pentec",
                "kbk",
                "bnk",
                "delmas",
                "deldep",
                "pentfr",
                "pcr",
                "clikbk",
                "apr",
                "dlvr",
                "hld",
                "omt",
                "omtctd",
                "act",
                "nr",
            ]
        )

        self.shot_search_box = QLineEdit()
        self.shot_search_box.setPlaceholderText("Search Shots")

        # self.shot_date_filter_combo = QComboBox()
        # self.shot_date_filter_combo.addItems([
        #     "All", "Today", "This Week", "Next Week",
        #     "Next Month", "Future", "Last Week",
        #     "Last Month", "Past"
        # ])

        search_filter_layout.addWidget(self.shot_filter_combo)
        self.shot_filter_combo.currentIndexChanged.connect(
            lambda index: self.filter_status(
                self.shot_filter_combo.currentText(), self.shot_table, 2
            )
        )
        search_filter_layout.addWidget(self.shot_search_box)
        self.shot_search_box.textChanged.connect(
            lambda text: self.filter_table(text, self.shot_table)
        )
        # self.shot_search_box.textChanged.connect(self.filter_shots_table)
        self.shot_table = QTableWidget(0, 3)  # 0 rows, 5 columns
        self.shot_table.setHorizontalHeaderLabels(
            ["Shot Name", "Project Name", "Status"]
        )

        left_layout.addLayout(search_filter_layout)
        left_layout.addWidget(self.shot_table)
        self.shot_table.setStyleSheet("""
        QTableWidget {
            background-color: #383838;
            color: white;
        }
        QTableWidget QHeaderView::section {
            background-col
            or: #555555;
            color: white;
        }
        """)
        self.shot_table.setWordWrap(True)

        # Set the row height and column width policies
        self.shot_table.verticalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeToContents
        )
        self.shot_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeToContents
        )

        # Optionally, set a maximum row height to ensure readability
        self.shot_table.verticalHeader().setDefaultSectionSize(
            50
        )  # Set a default row height
        self.shot_table.verticalHeader().setMaximumSectionSize(
            100
        )  # Set a maximum row height

        right_frame = QFrame()
        right_layout = QVBoxLayout(right_frame)
        filter_layout = QHBoxLayout()

        self.tab_widget_right_shot = QTabWidget()
        self.tab_all_shot = QWidget()
        self.tab_scan_shot = QWidget()

        self.tab_widget_right_shot.addTab(self.tab_all_shot, "All")
        self.tab_widget_right_shot.addTab(self.tab_scan_shot, "Scan")

        self.all_list_shot = QListWidget()
        self.scan_list_shot = QListWidget()
        self.all_versions_checkbox_shot = QCheckBox("All Versions")

        right_layout.addLayout(filter_layout)
        right_layout.addWidget(self.all_versions_checkbox_shot)
        right_layout.addWidget(self.tab_widget_right_shot)

        # Add the publish list to the "All" tab
        tab_all_shot_layout = QVBoxLayout(self.tab_all_shot)
        tab_all_shot_layout.addWidget(self.all_list_shot)
        tab_scan_shot_layout = QVBoxLayout(self.tab_scan_shot)
        tab_scan_shot_layout.addWidget(self.scan_list_shot)
        self.publish_list_version_shot = QListWidget()

        splitter.addWidget(left_frame)
        splitter.addWidget(right_frame)
        layout.addWidget(splitter)

        # self.shot_date_filter_combo.currentIndexChanged.connect(self.filter_shots)

        # Set size policies for left and right frames
        left_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Set initial sizes for the splitter
        table_width = self.calculate_table_width(self.shot_table) + 100

        # Set initial sizes for the splitter
        splitter.setSizes([table_width, 800])  # Adjust as needed


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()
