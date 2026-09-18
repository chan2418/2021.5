# main.py
import sys
from PySide2 import QtWidgets
from core.config_loader import ConfigLoader
from ui.main_window import MainWindow

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    loader = ConfigLoader("configs")
    global_config = loader.load_global()

    shows = ["mxp", "bfu"]
    cases = global_config["cases"]

    window = MainWindow(shows, cases)
    window.show()

    sys.exit(app.exec_())
