import sys
import requests
from PySide2.QtWidgets import *
from PySide2.QtCore import Qt, Signal, QSize, QObject, QThreadPool, QRunnable
from PySide2.QtGui import QPixmap, QIcon

class WorkerSignals(QObject):
    result = Signal(str, bytes)  # version_code, image_data

class ThumbnailWorker(QRunnable):
    def __init__(self, url, version_code):
        super(ThumbnailWorker, self).__init__()
        self.url = url
        self.version_code = version_code
        self.signals = WorkerSignals()

    def run(self):
        if not self.url or self.url in ['', 'None']:
            return
            
        try:
            response = requests.get(self.url, timeout=10)
            if response.status_code == 200:
                self.signals.result.emit(self.version_code, response.content)
        except Exception as e:
            print(f"DEBUG: Failed to download thumbnail for {self.version_code}: {e}")

class ThumbnailWidget(QWidget):
    thumbnail_clicked = Signal(str, str) # version_name, path

    def __init__(self, parent=None):
        super(ThumbnailWidget, self).__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.thread_pool = QThreadPool()
        self.items_map = {} # version_code -> QListWidgetItem
        
        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.IconMode)
        
        # Square thumbnails - make them visible boxes
        self.list_widget.setIconSize(QSize(100, 100))
        # Increase grid height to allocate more space for text below icon
        self.list_widget.setGridSize(QSize(120, 150))
        
        # CRITICAL: Disable wrapping for true horizontal scrolling
        self.list_widget.setWrapping(False)
        
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setFlow(QListWidget.LeftToRight)
        
        # Enable horizontal scrolling
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.list_widget.setSpacing(10)
        # Increase widget height to accommodate larger grid items + scrollbar
        self.list_widget.setFixedHeight(175)
        
        # Style for visible boxes
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #2b2b2b;
                border: 1px solid #444;
            }
            QListWidget::item {
                background-color: #3c3c3c;
                border: 2px solid #555;
                border-radius: 5px;
                padding: 5px;
                margin: 2px;
                color: #e0e0e0; /* Explicit text color */
            }
            QListWidget::item:hover {
                background-color: #4a4a4a;
                border-color: #888;
            }
            QListWidget::item:selected {
                background-color: #5a5a5a;
                border-color: #aaa;
                color: #ffffff;
            }
        """)
        
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        self.layout.addWidget(self.list_widget)

    def populate(self, items):
        """
        items: list of dicts (Versions) from SG
        """
        self.list_widget.clear()
        self.items_map.clear()
        
        if not items:
            return

        for item_data in items:
            version_code = item_data.get('code', 'Unknown')
            
            # Tooltip Data
            # Try 'user' field first (Artist), then fallback to 'created_by' (Creator)
            user_field = item_data.get('user') or item_data.get('created_by')
            created_by = user_field.get('name', 'Unknown') if user_field else 'Unknown'
            pub_files_links = item_data.get('sg_published_files', [])
            pub_files_names = ", ".join([pf.get('name', '') for pf in pub_files_links if pf.get('name')])
            
            tooltip_text = f"Version: {version_code}\nUser: {created_by}\nPublished Files: {pub_files_names or 'None'}"

            # Set text on item to show below the icon
            item = QListWidgetItem(version_code)
            item.setToolTip(tooltip_text)
            item.setTextAlignment(Qt.AlignCenter)
            
            # Store version code
            item.setData(Qt.UserRole, {'code': version_code, 'path': ''})
            
            # Initial placeholder
            self._create_placeholder_icon(item, version_code)
            
            self.list_widget.addItem(item)
            self.items_map[version_code] = item
            
            # Initiate background download
            thumb_url = item_data.get('image')
            if thumb_url and thumb_url not in ['', 'None']:
                worker = ThumbnailWorker(thumb_url, version_code)
                worker.signals.result.connect(self.handle_thumbnail_downloaded)
                self.thread_pool.start(worker)
                
    def handle_thumbnail_downloaded(self, version_code, image_data):
        """Slot to handle downloaded image data"""
        if version_code in self.items_map:
            item = self.items_map[version_code]
            pixmap = QPixmap()
            if pixmap.loadFromData(image_data):
                scaled_pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                item.setIcon(QIcon(scaled_pixmap))
    
    def _create_placeholder_icon(self, item, text):
        """Create a placeholder icon with version text drawn on it"""
        from PySide2.QtGui import QPainter, QFont, QColor, QPen
        
        pixmap = QPixmap(100, 100)
        pixmap.fill(QColor(60, 60, 60))  # Dark gray background
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw border
        pen = QPen(QColor(100, 100, 100))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawRect(1, 1, 97, 97)
        
        # Draw version text in center with readable font size (User requested smaller)
        font = QFont("Arial", 9, QFont.Bold) # Reduced from 12
        painter.setFont(font)
        painter.setPen(QColor(240, 240, 240))
        
        # Enable text wrapping for long version names
        painter.drawText(5, 5, 90, 90, Qt.AlignCenter | Qt.TextWordWrap, text)
        
        painter.end()
        item.setIcon(QIcon(pixmap))

    def on_item_clicked(self, item):
        data = item.data(Qt.UserRole)
        self.thumbnail_clicked.emit(data['code'], data['path'])


class RenderSettingsUI(QWidget):
    publish_signal = Signal()
    version_update_signal = Signal()
    # New signal to communicate selection back to controller
    thumbnail_selected_signal = Signal(str, str) 

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
        
        # [NEW] Add Thumbnail Widget
        self.thumbnail_widget = ThumbnailWidget()
        self.thumbnail_widget.thumbnail_clicked.connect(self.on_thumbnail_selected)
        form_layout.addRow("Matte Versions:", self.thumbnail_widget)


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

    def on_thumbnail_selected(self, code, path):
        self.thumbnail_selected_signal.emit(code, path)

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
            QMessageBox.warning(self, "Incomplete Description", "Please fill the Description")

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