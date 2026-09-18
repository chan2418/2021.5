# # from PySide2.QtWidgets import (
# #     QApplication, QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
# #     QTableWidget, QTableWidgetItem, QLabel
# # )
# # from PySide2.QtCore import Qt
# # import sys

# # class MainWindow(QWidget):
# #     def __init__(self):
# #         super().__init__()
# #         self.setWindowTitle("QListWidget Item -> Show Table")
# #         self.resize(500, 400)

# #         self.layout = QVBoxLayout(self)

# #         self.list_widget = QListWidget()
# #         self.layout.addWidget(self.list_widget)

# #         self.table = QTableWidget(3, 2)  # 3 rows, 2 columns
# #         self.table.setHorizontalHeaderLabels(["Key", "Value"])
# #         self.table.setVisible(False)  # Initially hidden
# #         self.layout.addWidget(self.table)

# #         self.populate_list()
# #         self.list_widget.itemClicked.connect(self.show_table_for_item)

# #     def populate_list(self):
# #         for i in range(5):
# #             item = QListWidgetItem(f"Item {i}")
# #             self.list_widget.addItem(item)

# #     def show_table_for_item(self, item):
# #         # Populate the table with dummy info for the selected item
# #         self.table.clearContents()
# #         self.table.setItem(0, 0, QTableWidgetItem("Name"))
# #         self.table.setItem(0, 1, QTableWidgetItem(item.text()))
# #         self.table.setItem(1, 0, QTableWidgetItem("Type"))
# #         self.table.setItem(1, 1, QTableWidgetItem("Example Type"))
# #         self.table.setItem(2, 0, QTableWidgetItem("Status"))
# #         self.table.setItem(2, 1, QTableWidgetItem("Active"))

# #         self.table.setVisible(True)

# # if __name__ == "__main__":
# #     app = QApplication(sys.argv)
# #     window = MainWindow()
# #     window.show()
# #     sys.exit(app.exec_())


# # import string

# # layer = "matteF"  # example input

# # if layer.startswith("matte") and layer[-1] in string.ascii_uppercase:
# #     current_letter = layer[-1]
# #     next_letter = chr(ord(current_letter) + 1)
# #     mattelayer_name = layer[:-1] + next_letter

# #     # Letter index: A=0, B=1, C=2, ...
# #     index = ord(current_letter) - ord('A')

# #     # Compute start and end
# #     count_per_group = 4
# #     start = index * count_per_group + 1
# #     end = start + count_per_group

# #     # Build child list dynamically
# #     mattechild_layer = [f"m{i}" for i in range(start, end)]

# #     print(f"Current: {layer}")
# #     print(f"Next Matte: {mattelayer_name}")
# #     print(f"Child Layers: {mattechild_layer}")


# import os

# path = "ICE101_FBP_0440_v001_MP01_.0977.exr"
# version = next((s[i:i+4] for s in reversed(path.split('_')) for i in reversed(range(len(s)-3)) if s[i:i+2].isalpha() and s[i+2:i+4].isdigit()), None)
# print(version)


# dict_items = ('/projects/stm_mkg2/201_017_0034/dept/upload/roto/201_017_0034_roto_BFS_v001/matte/matte01', '/projects/stm_mkg2/201_017_0034/dept/publish/roto/render/201_017_0034_roto_test_matte01_v001/201_017_0034_roto_test_matte01_v001.%04d.exr'), ('/projects/stm_mkg2/201_017_0034/dept/upload/roto/201_017_0034_roto_BFS_v001/matte/matte02', '/projects/stm_mkg2/201_017_0034/dept/publish/roto/render/201_017_0034_roto_test_matte02_v001/201_017_0034_roto_test_matte02_v001.%04d.exr')
# for dst_path, src_path in dict_items.items():
#     print(dst_path)
#     print(src_path)

import glob
import re

path = "/projects/ie_flx/FLX-1001-0100/in/plates/v001/bgRt_plate_workingMask/4608x3164/FLX_1001_0100_bgRt_plate_workingMask_v0003.%06d.exr"


def frame_range(pattern):
    """"""
    files = sorted(glob.glob(re.sub(r"%0\d+d", "*", pattern)))
    if not files:
        return None
    start_frame = re.findall(r"\d+", files[0])[-1]
    last_frame = re.findall(r"\d+", files[-1])[-1]
    return re.sub(r"%0\d+d", f"[{start_frame}-{last_frame}]", pattern)


file_path = frame_range(path)
file_path
