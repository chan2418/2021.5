# roto_packaging_tool/ui/main_ui.py
import sys, os
sys.path.append("/tools/packages/python/3.9.6/platform-linux/arch-x86_64/os-rocky-9.2/python/site-packages")
from PySide2 import QtWidgets
from PySide2 import QtWidgets, QtGui


# Local imports
from roto_packaging_tool.core.structure_builder import StructureBuilder
from roto_packaging_tool.core.package_manager import PackageManager
from roto_packaging_tool.context import CONTEXT


class RotoPackagingUI(QtWidgets.QWidget):
    def __init__(self, config_dir="../configs"):
        super().__init__()
        self.setWindowTitle("Roto Packaging Tool")
        self.setGeometry(200, 100, 900, 700)
        self.config_dir = os.path.abspath(config_dir)

        # === Layout ===
        main_layout = QtWidgets.QVBoxLayout(self)

        # ---------------- Project Info ----------------
        project_group = QtWidgets.QGroupBox("Project Info")
        form_layout = QtWidgets.QFormLayout()

        # Show (from context, locked)
        self.show_dropdown = QtWidgets.QComboBox()
        self.show_dropdown.addItems(["mxp", "bfu"])
        self.show_dropdown.setCurrentText(CONTEXT["show"])
        self.show_dropdown.setEnabled(False)

        # Subgroup (artist can pick)
        self.subgroup_dropdown = QtWidgets.QComboBox()
        self.subgroup_dropdown.addItems(["clh", "dm2", "wam", "sos", "mro"])

        # Shot (from context, locked)
        self.shot_input = QtWidgets.QLineEdit(CONTEXT["shot"])
        self.shot_input.setReadOnly(True)

        # Out Version (from context, locked)
        self.version_input = QtWidgets.QLineEdit(CONTEXT["out_version"])
        self.version_input.setReadOnly(True)

        # Plate Name (editable)
        self.plate_input = QtWidgets.QLineEdit(CONTEXT.get("plate_name", ""))

        # Plate Version (editable)
        self.plate_version_input = QtWidgets.QLineEdit(CONTEXT.get("plate_version", ""))
        # Frame range inputs
        self.start_frame_input = QtWidgets.QLineEdit("1001")
        self.start_frame_input.setValidator(QtGui.QIntValidator())



        self.end_frame_input = QtWidgets.QLineEdit("1100")
        self.end_frame_input.setValidator(QtGui.QIntValidator())

        # Reviewer (editable dropdown)
        self.reviewer_dropdown = QtWidgets.QComboBox()
        self.reviewer_dropdown.setEditable(True)
        self.reviewer_dropdown.addItems(["", "lead.roto", "sup.roto", "prod.roto"])

        # Notes (multiline)
        self.notes_edit = QtWidgets.QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Submission notes (optional)…")

        # Assemble form
        form_layout.addRow("Show:", self.show_dropdown)
        form_layout.addRow("Subgroup:", self.subgroup_dropdown)
        form_layout.addRow("Shot:", self.shot_input)
        form_layout.addRow("Out Version:", self.version_input)
        form_layout.addRow("Plate Name:", self.plate_input)
        form_layout.addRow("Plate Version:", self.plate_version_input)
        form_layout.addRow("Start Frame:", self.start_frame_input)
        form_layout.addRow("End Frame:", self.end_frame_input)
        form_layout.addRow("Reviewer:", self.reviewer_dropdown)
        form_layout.addRow("Submission Notes:", self.notes_edit)
        project_group.setLayout(form_layout)

        # ---------------- Output Preview ----------------
        output_group = QtWidgets.QGroupBox("Output Structure Preview")
        vlayout = QtWidgets.QVBoxLayout()
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderHidden(True)
        vlayout.addWidget(self.tree)
        output_group.setLayout(vlayout)

        # ---------------- Buttons ----------------
        button_layout = QtWidgets.QHBoxLayout()
        self.build_btn = QtWidgets.QPushButton("Build Structure")
        self.render_btn = QtWidgets.QPushButton("Render & Package")
        button_layout.addWidget(self.build_btn)
        button_layout.addWidget(self.render_btn)

        # ---------------- Layout Assembly ----------------
        main_layout.addWidget(project_group)
        main_layout.addWidget(output_group)
        main_layout.addLayout(button_layout)

        # ---------------- Signals ----------------
        self.build_btn.clicked.connect(self.on_build_structure)
        self.render_btn.clicked.connect(self.on_render_package)

    # ---------------------------------------------------
    def build_tree(self, parent, structure):
        """Recursive dict/list/str → QTreeWidget"""
        if isinstance(structure, dict):
            for k, v in structure.items():
                node = QtWidgets.QTreeWidgetItem([k])
                parent.addChild(node)
                self.build_tree(node, v)
        elif isinstance(structure, list):
            for item in structure:
                self.build_tree(parent, item)
        elif isinstance(structure, str):
            QtWidgets.QTreeWidgetItem(parent, [structure])

    # ---------------------------------------------------
    def _collect_tokens(self):
        """Collect tokens from UI + context."""
        sf = self.start_frame_input.text().strip() or "1001"
        ef = self.end_frame_input.text().strip() or "1001"
        frame_range = f"{sf}-{ef}"

        tokens = {
            "show": CONTEXT["show"],
            "shot": CONTEXT["shot"],
            "sg_plate_name": self.plate_input.text().strip(),
            "plate_name": self.plate_input.text().strip(),
            "out_version": CONTEXT["out_version"],
            "plate_version": self.plate_version_input.text().strip(),
            "frame_range": frame_range,
            "reviewer": self.reviewer_dropdown.currentText().strip(),
            "notes": self.notes_edit.toPlainText().strip(),
        }
        return tokens

    # ---------------------------------------------------
    def on_build_structure(self):
        show = self.show_dropdown.currentText()
        subgroup = self.subgroup_dropdown.currentText()
        tokens = self._collect_tokens()

        config_file = os.path.join(self.config_dir, f"{show}.yaml")
        try:
            builder = StructureBuilder(config_file, tokens)
            structure = builder.expand_structure(subgroup)

            self.tree.clear()
            root = QtWidgets.QTreeWidgetItem([f"{show} - {subgroup}"])
            self.tree.addTopLevelItem(root)

            self.build_tree(root, structure)
            self.tree.expandAll()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))

    # ---------------------------------------------------
    def on_render_package(self):
        show = self.show_dropdown.currentText()
        subgroup = self.subgroup_dropdown.currentText()
        tokens = self._collect_tokens()

        if not tokens["reviewer"]:
            QtWidgets.QMessageBox.warning(self, "Missing Reviewer", "Please select or type a reviewer.")
            return

        pm = PackageManager(
            config_dir=self.config_dir,
            tools_paths={"nuke": "/apps/nuke/Nuke12.2v7/Nuke12.2"},
            out_path="/projects/out/roto"
        )

        try:
            results = pm.run_packaging(show, subgroup, tokens)
            QtWidgets.QMessageBox.information(
                self, "Nuke Packaging",
                f"Nuke job launched ✅\nJob ID: {results.get('nuke_job','(local)')}"
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))


# ---------------- Run standalone ----------------
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    here = os.path.dirname(__file__)
    window = RotoPackagingUI(config_dir=os.path.abspath(os.path.join(here, "../configs")))
    window.show()
    sys.exit(app.exec_())
