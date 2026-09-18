from PySide2.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QSpacerItem,
    QSizePolicy,
    QListWidgetItem,
)
from PySide2.QtCore import Qt, QSize
import sys


class CustomListWidget(QListWidget):
    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        if item is None:
            self.clearSelection()
        super().mousePressEvent(event)


class MainWindow(QDialog):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

        # Set up the main layout
        main_layout = QVBoxLayout()

        # Set the main widget's background color and text color
        self.setStyleSheet("background-color: #282828; color: white;")

        # Create a horizontal layout for the first row of labels and line edits
        hbox1 = QHBoxLayout()

        # Define the label style
        label_style = """
        font: bold 15pt 'Helvetica';
        padding: 15px;
        border-radius: 4px;
        border: 1px solid #C0C0C0;
        color:white;
        """

        list_widget_style = """
        QListWidget {
            font: bold 12pt 'Helvetica';
            padding: 15px;
            border-radius: 4px;
            border: 1px solid #C0C0C0;
            color:white;
        }
        QListWidget::item {
            background-color: #383838;
            border-radius: 4px;
            padding: 10px;
            margin: 5px;
        }
        QListWidget::item:selected {
            background-color: #5686CE;
            color: white;
        }
        """

        # Add spacer to center the label horizontally
        hbox1.addSpacerItem(
            QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        )

        # Add label for "Show" as a heading
        self.show_heading = QLabel("show")
        self.show_heading.setStyleSheet(label_style)
        self.show_heading.adjustSize()
        # Add the label to the horizontal layout
        hbox1.addWidget(self.show_heading)

        # Add spacer to center the label horizontally
        hbox1.addSpacerItem(
            QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        )

        # Add the first horizontal layout to the main vertical layout
        main_layout.addLayout(hbox1)

        # Create a horizontal layout for the second row of labels and list widgets
        hbox2 = QHBoxLayout()

        # Create label and list widget for "Tasks"
        self.list_tasks = CustomListWidget()
        self.list_tasks.setStyleSheet(list_widget_style)
        self.list_tasks.addItems(["Task 1", "Task 2", "Task 3"])  # Add your tasks here

        # Add label and list widget to the second horizontal layout
        temp_layout_tasks = QVBoxLayout()
        temp_layout_tasks.addWidget(self.list_tasks)
        hbox2.addLayout(temp_layout_tasks)

        # Add stretching item to push the list widget to the start
        hbox2.addSpacerItem(
            QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        )

        # Add the second horizontal layout to the main vertical layout
        main_layout.addLayout(hbox2)
        import_button_style = """
            QPushButton, QLabel, QCheckBox, QRadioButton, QLineEdit, QSlider, QComboBox, QDateEdit, QTextEdit {
                color: rgb(255, 255, 255);
                font: bold 12pt 'Helvetica'; /* Adjust font size to 12pt */
                padding: 8px; /* Increase padding */
                border-radius: 8px; /* Increase border radius */
                border: 2px solid #333; /* Increase border width */
                background-color: rgb(54, 106, 206);
                
                min-height: 25px; /* Adjust minimum height */
            }
            QPushButton:hover {
                background-color: rgb(34, 86, 176); /* Lighter shade for hover */
            }
            QPushButton:pressed {
                background-color: rgb(14, 66, 156); /* Slightly darker shade for pressed */
            }
        """
        # Create the import button
        self.import_button = QPushButton("Import")
        self.import_button.setStyleSheet(import_button_style)
        main_layout.addWidget(self.import_button)

        # Set the layout for the dialog
        self.setLayout(main_layout)

        # Set window title
        self.setWindowTitle("Scan Import")

        # Set minimum width and height to 70% of the screen size
        screen = QApplication.primaryScreen()
        screen_size = screen.size()
        self.setMinimumWidth(screen_size.width() * 0.7)
        self.setMinimumHeight(screen_size.height() * 0.7)

        # Set initial size to 80% of the screen size
        self.resize(screen_size.width() * 0.8, screen_size.height() * 0.8)

    def resizeEvent(self, event):
        # Set the list widget width to 50% of the window width
        new_width = self.width() * 0.5
        self.list_tasks.setFixedWidth(new_width)
        super().resizeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
