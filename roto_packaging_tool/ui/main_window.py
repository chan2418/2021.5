# main_window.py
from PySide2 import QtWidgets

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, shows, cases):
        super().__init__()
        self.setWindowTitle("Roto Packaging Tool")

        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        self.show_combo = QtWidgets.QComboBox()
        self.show_combo.addItems(shows)

        self.case_combo = QtWidgets.QComboBox()
        self.case_combo.addItems([f"{k}: {v['name']}" for k, v in cases.items()])

        self.publish_btn = QtWidgets.QPushButton("Publish")

        layout.addWidget(QtWidgets.QLabel("Select Show:"))
        layout.addWidget(self.show_combo)
        layout.addWidget(QtWidgets.QLabel("Select Case:"))
        layout.addWidget(self.case_combo)
        layout.addWidget(self.publish_btn)

        self.setCentralWidget(widget)
