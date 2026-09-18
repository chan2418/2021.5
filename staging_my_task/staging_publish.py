"""
Staging Publish for Silhouette BFSTOOLS menu.

Uses the bfs_sg_requests Silhouette Publish pipeline from STAGING:
    /tools/bpipe/staging/bfs_sg_requests

Features:
    - Automatically discovers OutputNodes & connected Roto layers in active Silhouette session.
    - Collects output_nodes dictionary: {node_label: matte_name}.
    - Submits via SilhouetteSceneVersion & SilhouetteRenderVersion (EXR render, Review MOV, SG Version).
    - Multi-matte single SG Version grouping with Dailies metadata.
"""

import os
import re
import sys
import time

# ----------------------------------------------------------------------
# 1. Environment & Path Setup
# ----------------------------------------------------------------------
TOOLS_ROOT = "/tools/silhouette_tools/2021.5"
if TOOLS_ROOT not in sys.path:
    sys.path.insert(0, TOOLS_ROOT)

# Priority search for bfs_sg_requests (Staging -> Dev -> Production)
PIPELINE_PATHS = [
    os.environ.get("BFS_SG_REQUESTS_PATH"),
    "/tools/bpipe/staging/bfs_sg_requests",
    "/home/chandru/Documents/development/bfs_sg_requests",
    "/tools/bpipe/bfs_sg_requests",
]
for p in PIPELINE_PATHS:
    if p and os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

try:
    b_show_name = os.environ.get("B_SHOW")
    if b_show_name:
        core_python = f"/tools/projects/{b_show_name}/install/core/python"
        if os.path.exists(core_python) and core_python not in sys.path:
            sys.path.insert(0, core_python)
except Exception:
    pass

import fx
import sgtk

try:
    import sg_requests
except Exception as _err:
    print("[Staging Publish] sg_requests initial import notice:", _err)


def _get_silhouette_publish_classes(sg=None):
    """Safely resolve SilhouetteSceneVersion and SilhouetteRenderVersion."""
    # Ensure all pipeline candidate paths are in sys.path and publish.__path__
    for p in PIPELINE_PATHS:
        if p and os.path.exists(p):
            if p not in sys.path:
                sys.path.insert(0, p)
            pub_dir = os.path.join(p, "publish")
            if os.path.isdir(pub_dir) and "publish" in sys.modules:
                pub_mod = sys.modules["publish"]
                if hasattr(pub_mod, "__path__") and pub_dir not in pub_mod.__path__:
                    pub_mod.__path__.insert(0, pub_dir)

    try:
        from publish.silhouette_publish import (
            SilhouetteRenderVersion,
            SilhouetteSceneVersion,
        )

        return SilhouetteSceneVersion, SilhouetteRenderVersion
    except Exception:
        pass

    try:
        from publish.silhouette_publish.silhouette_versions import (
            SilhouetteRenderVersion,
            SilhouetteSceneVersion,
        )

        return SilhouetteSceneVersion, SilhouetteRenderVersion
    except Exception:
        pass

    try:
        import importlib

        mod = importlib.import_module("publish.silhouette_publish.silhouette_versions")
        return mod.SilhouetteSceneVersion, mod.SilhouetteRenderVersion
    except Exception:
        pass

    import sg_requests

    _sg = sg or sg_requests.ShotgridConnection(project=os.environ.get("B_SHOW"))
    if hasattr(_sg, "publish") and hasattr(_sg.publish, "silhouette_publish"):
        return (
            _sg.publish.silhouette_publish.SilhouetteSceneVersion,
            _sg.publish.silhouette_publish.SilhouetteRenderVersion,
        )

    raise RuntimeError(
        "Could not load Silhouette publish classes. "
        "Please ensure publish/silhouette_publish is deployed to /tools/bpipe/bfs_sg_requests/publish/silhouette_publish"
    )


from PySide2.QtCore import Qt
from PySide2.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

# ----------------------------------------------------------------------
# 2. Modern Dark UI Stylesheet
# ----------------------------------------------------------------------
_DIALOG_STYLE = """
QDialog#StagingPublishDialog {
    background-color: #14181f;
    color: #e8eaed;
    font-family: "Segoe UI", "Ubuntu", "Noto Sans", sans-serif;
    font-size: 12px;
}
QLabel {
    color: #c8cdd5;
    background: transparent;
}
QLabel#HeaderTitle {
    color: #ffffff;
    font-size: 16px;
    font-weight: 700;
}
QLabel#HeaderSub {
    color: #8b93a7;
    font-size: 11px;
}
QLabel#SectionTitle {
    color: #7eb6ff;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
}
QLabel#ColHeader {
    color: #9aa3b5;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
}
QLabel#NodeName {
    color: #f0f3f8;
    font-weight: 600;
    font-size: 12px;
}
QFrame#HeaderBar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a2332, stop:0.5 #1e3a5f, stop:1 #1a2332);
    border: 1px solid #2a3a52;
    border-radius: 8px;
}
QFrame#TableCard, QFrame#FooterCard {
    background-color: #1a1f2a;
    border: 1px solid #2a3142;
    border-radius: 8px;
}
QLineEdit, QComboBox {
    background-color: #0f131a;
    color: #e8eaed;
    border: 1px solid #2e3648;
    border-radius: 5px;
    padding: 4px 8px;
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #3d8bfd;
}
QLineEdit:read-only {
    background-color: #151a24;
    color: #8b93a7;
}
QPushButton#BtnPrimary {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2575fc, stop:1 #1a56c4);
    color: #ffffff;
    border: none;
    border-radius: 6px;
    font-weight: 600;
    font-size: 12px;
    padding: 8px 18px;
}
QPushButton#BtnPrimary:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3a85ff, stop:1 #2575fc);
}
QPushButton#BtnSecondary {
    background-color: #242c3d;
    color: #d0d5e0;
    border: 1px solid #364156;
    border-radius: 6px;
    font-weight: 500;
    padding: 8px 16px;
}
QPushButton#BtnSecondary:hover {
    background-color: #2d374d;
    border-color: #485672;
}
QProgressBar {
    border: 1px solid #2a3142;
    border-radius: 4px;
    background-color: #0f131a;
    text-align: center;
    color: #e8eaed;
}
QProgressBar::chunk {
    background-color: #2575fc;
    border-radius: 3px;
}
"""


# ----------------------------------------------------------------------
# 3. Staging Publish Dialog UI
# ----------------------------------------------------------------------
class StagingPublishDialog(QDialog):
    """
    GUI Dialog for Silhouette Multi-Matte Publish & Deadline Submission
    using the staging bfs_sg_requests pipeline.
    """

    def __init__(self, context_data, parent=None):
        super(StagingPublishDialog, self).__init__(parent)
        self.setObjectName("StagingPublishDialog")
        self.setStyleSheet(_DIALOG_STYLE)
        self.setWindowTitle("BFS Silhouette Staging Publish")
        self.resize(780, 520)

        self.project_name = context_data.get("project_name", "")
        self.shot_name = context_data.get("shot_name", "")
        self.task_name = context_data.get("task", "")
        self.publish_name = context_data.get("name", "test")
        self.task_id = context_data.get("task_id", "")
        self.SG = context_data.get("sg")

        self.node_rows = []
        self._build_ui()
        self._populate_nodes()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(12)

        # ── Header ──────────────────────────────────────────
        header = QFrame()
        header.setObjectName("HeaderBar")
        header_lay = QVBoxLayout(header)
        header_lay.setContentsMargins(14, 10, 14, 10)
        header_lay.setSpacing(3)

        title = QLabel("Silhouette Staging Publish")
        title.setObjectName("HeaderTitle")
        sub_text = f"Project: {self.project_name}  ·  Shot: {self.shot_name}  ·  Task: {self.task_name} (ID: {self.task_id})"
        sub = QLabel(sub_text)
        sub.setObjectName("HeaderSub")

        header_lay.addWidget(title)
        header_lay.addWidget(sub)
        main_layout.addWidget(header)

        # ── Matte / Output Nodes Card ────────────────────────
        table_card = QFrame()
        table_card.setObjectName("TableCard")
        table_lay = QVBoxLayout(table_card)
        table_lay.setContentsMargins(12, 10, 12, 10)
        table_lay.setSpacing(8)

        sec_title = QLabel("Output Nodes & Matte Layers")
        sec_title.setObjectName("SectionTitle")
        table_lay.addWidget(sec_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(180)
        scroll.setMaximumHeight(260)

        scroll_body = QWidget()
        self.grid_layout = QGridLayout(scroll_body)
        self.grid_layout.setContentsMargins(6, 6, 6, 6)
        self.grid_layout.setHorizontalSpacing(10)
        self.grid_layout.setVerticalSpacing(6)
        self.grid_layout.setColumnStretch(2, 1)

        # Column headers
        headers = ["", "Node Label", "Matte / Layer Name", "Start Frame", "End Frame"]
        for col, text in enumerate(headers):
            h = QLabel(text)
            h.setObjectName("ColHeader")
            self.grid_layout.addWidget(h, 0, col)

        scroll.setWidget(scroll_body)
        table_lay.addWidget(scroll)
        main_layout.addWidget(table_card)

        # ── Publish Settings Card ────────────────────────────
        settings_card = QFrame()
        settings_card.setObjectName("FooterCard")
        settings_lay = QGridLayout(settings_card)
        settings_lay.setContentsMargins(14, 10, 14, 10)
        settings_lay.setHorizontalSpacing(12)
        settings_lay.setVerticalSpacing(8)

        # Publish Name
        settings_lay.addWidget(QLabel("Publish Name:"), 0, 0)
        self.pub_name_edit = QLineEdit(self.publish_name)
        settings_lay.addWidget(self.pub_name_edit, 0, 1)

        # Version Type (Dailies vs Package)
        settings_lay.addWidget(QLabel("Version Type:"), 0, 2)
        self.version_type_combo = QComboBox()
        self.version_type_combo.addItems(["Dailies", "Package"])
        settings_lay.addWidget(self.version_type_combo, 0, 3)

        # Submission Mode (Farm vs Local)
        settings_lay.addWidget(QLabel("Render Mode:"), 1, 0)
        self.render_mode_combo = QComboBox()
        self.render_mode_combo.addItems(["Deadline Farm Render", "Local Render"])
        settings_lay.addWidget(self.render_mode_combo, 1, 1)

        # Skip Movie Export
        self.skip_movie_check = QCheckBox("Skip Movie Export (EXR Only)")
        self.skip_movie_check.setChecked(False)
        settings_lay.addWidget(self.skip_movie_check, 1, 2, 1, 2)

        main_layout.addWidget(settings_card)

        # ── Progress Bar ─────────────────────────────────────
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(18)
        main_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setObjectName("HeaderSub")
        self.status_label.setVisible(False)
        main_layout.addWidget(self.status_label)

        # ── Buttons ──────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch(1)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("BtnSecondary")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.submit_btn = QPushButton("Submit Publish")
        self.submit_btn.setObjectName("BtnPrimary")
        self.submit_btn.clicked.connect(self._on_submit)
        btn_layout.addWidget(self.submit_btn)

        main_layout.addLayout(btn_layout)

    def _get_connected_roto_name(self, output_node):
        """Find the top layer name of the connected RotoNode."""
        try:
            input_conn = output_node.getInput(0)
            if input_conn and input_conn.source and input_conn.source.node:
                src = input_conn.source.node
                if (
                    getattr(src, "type", "") == "RotoNode"
                    and hasattr(src, "children")
                    and src.children
                ):
                    top_layer = src.children[0].label
                    clean_name = re.sub(r"[^A-Za-z0-9_]+", "_", top_layer).strip("_")
                    if clean_name:
                        return clean_name
        except Exception:
            pass
        return ""

    def _populate_nodes(self):
        """Discover OutputNodes in active session and populate table."""
        session = fx.activeSession()
        if not session:
            return

        out_range = getattr(session, "outputRange", [1001, 1050])
        start_f = int(out_range[0])
        end_f = int(out_range[1])

        outputs = getattr(session, "outputs", [])
        if not outputs:
            # Fallback: inspect getNodes("OutputNode")
            outputs = (
                session.getNodes("OutputNode") if hasattr(session, "getNodes") else []
            )

        for idx, out in enumerate(outputs, start=1):
            chk = QCheckBox()
            chk.setChecked(True)

            node_label = getattr(out, "label", f"OutputNode{idx}")
            lbl = QLabel(node_label)
            lbl.setObjectName("NodeName")

            # Auto-detect layer name from connected RotoNode, or fallback to matte01, matte02
            matte_default = self._get_connected_roto_name(out) or f"matte{idx:02d}"
            matte_edit = QLineEdit(matte_default)

            start_edit = QLineEdit(str(start_f))
            start_edit.setFixedWidth(65)
            start_edit.setAlignment(Qt.AlignCenter)

            end_edit = QLineEdit(str(end_f))
            end_edit.setFixedWidth(65)
            end_edit.setAlignment(Qt.AlignCenter)

            self.grid_layout.addWidget(chk, idx, 0)
            self.grid_layout.addWidget(lbl, idx, 1)
            self.grid_layout.addWidget(matte_edit, idx, 2)
            self.grid_layout.addWidget(start_edit, idx, 3)
            self.grid_layout.addWidget(end_edit, idx, 4)

            self.node_rows.append(
                {
                    "checkbox": chk,
                    "node_label": node_label,
                    "matte_edit": matte_edit,
                    "start_edit": start_edit,
                    "end_edit": end_edit,
                    "output_node": out,
                }
            )

    def update_progress(self, percent, message):
        """Update progress bar and status label."""
        self.progress_bar.setVisible(True)
        self.status_label.setVisible(True)
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)
        QApplication.processEvents()

    def _on_submit(self):
        """Perform the publish using staging bfs_sg_requests."""
        # Collect selected nodes
        selected_nodes = {}
        frame_range = None

        for row in self.node_rows:
            if row["checkbox"].isChecked():
                node_label = row["node_label"]
                matte_name = row["matte_edit"].text().strip()
                if not matte_name:
                    matte_name = node_label

                selected_nodes[node_label] = matte_name

                # Frame range from first checked node
                if frame_range is None:
                    try:
                        sf = int(row["start_edit"].text().strip())
                        ef = int(row["end_edit"].text().strip())
                        frame_range = (sf, ef)
                    except ValueError:
                        frame_range = (1001, 1050)

        if not selected_nodes:
            QMessageBox.warning(
                self,
                "No Nodes Selected",
                "Please select at least one output node to publish.",
            )
            return

        publish_name = self.pub_name_edit.text().strip() or "test"
        version_type = self.version_type_combo.currentText()
        is_local = self.render_mode_combo.currentText() == "Local Render"
        skip_movie = self.skip_movie_check.isChecked()

        # Disable buttons during publish
        self.submit_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)

        try:
            # 1. Connect to ShotGrid & set context
            self.update_progress(15, "Connecting to ShotGrid (Staging)…")
            SG = self.SG
            if not SG:
                SG = sg_requests.ShotgridConnection(project=self.project_name)

            if self.task_id:
                SG.change_context("Task", int(self.task_id))

            session = fx.activeSession()
            session_name = (
                getattr(session, "label", "NewSession1") if session else "NewSession1"
            )

            # 2. Configure multi-matte render version and preprocess node paths (single project save)
            SilhouetteSceneVersion, SilhouetteRenderVersion = (
                _get_silhouette_publish_classes(SG)
            )

            self.update_progress(25, "Configuring render nodes & paths…")
            render_version = SilhouetteRenderVersion(
                SG,
                publish_name,
                SG.context,
                output_nodes=selected_nodes,
                skip_movie_export=skip_movie,
                is_local_publish=is_local,
            )

            # Dailies / Package metadata
            render_version.additional_sg_version_fields["sg_version_type"] = (
                version_type
            )
            render_version.properties.session_name = session_name
            render_version.properties.frame_range = frame_range

            # Preprocess updates all output node paths in memory and saves project ONCE
            render_version.preprocess()

            # 3. Publish Silhouette Scene (.sfx) with updated output paths
            self.update_progress(45, "Publishing Silhouette Scene (.sfx)…")
            scene_version = SilhouetteSceneVersion(
                SG,
                publish_name,
                SG.context,
            )
            scene_version.publish()
            print(
                "[Staging Publish] Scene Published:",
                scene_version.exporters[0].publish_path,
            )

            # 4. Link scene exporter and create ShotGrid entities
            self.update_progress(60, "Registering ShotGrid Version & PublishedFiles…")
            render_version.properties.scene_exporter = scene_version.exporters[0]
            render_version._scene_bundle_synced = (
                True  # Already published with correct node paths
            )

            render_version.create_sg_version = True
            render_version.create_sg_entities([scene_version])

            # 5. Submit Deadline jobs with concurrent submission
            total_exps = len(render_version.exporters)
            if not is_local and total_exps > 1:
                import concurrent.futures

                # Primary matte and review movie submitted first
                exp0 = render_version.exporters[0]
                if exp0.enabled:
                    self.update_progress(
                        65,
                        f"Submitting primary render job (1/{total_exps}): {exp0.name}…",
                    )
                    exp0.export()
                    if getattr(exp0, "_child_exporters", []):
                        self.update_progress(
                            70,
                            f"Submitting Review Movie job for {exp0.name} to Deadline…",
                        )
                        exp0.export_children()

                # Remaining mattes submitted concurrently
                remaining_exps = [e for e in render_version.exporters[1:] if e.enabled]
                if remaining_exps:
                    self.update_progress(
                        75,
                        f"Submitting remaining {len(remaining_exps)} mattes to Deadline in parallel…",
                    )

                    def _submit_exp(exp):
                        exp.export()
                        return exp.name

                    max_workers = min(len(remaining_exps), 6)
                    with concurrent.futures.ThreadPoolExecutor(
                        max_workers=max_workers
                    ) as executor:
                        futures = {
                            executor.submit(_submit_exp, exp): exp
                            for exp in remaining_exps
                        }
                        done_count = 0
                        for future in concurrent.futures.as_completed(futures):
                            done_count += 1
                            pct = int(
                                75 + (done_count / float(len(remaining_exps))) * 23
                            )
                            name = futures[future].name
                            self.update_progress(
                                pct,
                                f"Submitted matte ({done_count + 1}/{total_exps}): {name}…",
                            )
            else:
                for idx, exporter in enumerate(render_version.exporters, start=1):
                    pct = int(65 + ((idx - 0.5) / float(total_exps)) * 30)
                    matte_name = exporter.name
                    self.update_progress(
                        pct,
                        f"Submitting render job ({idx}/{total_exps}): {matte_name} to Deadline…"
                        if not is_local
                        else f"Rendering locally ({idx}/{total_exps}): {matte_name}…",
                    )
                    if exporter.enabled:
                        exporter.export()

                    if getattr(exporter, "_child_exporters", []):
                        movie_pct = int(65 + (idx / float(total_exps)) * 30)
                        self.update_progress(
                            movie_pct,
                            f"Submitting Review Movie job for {matte_name} to Deadline…",
                        )
                        exporter.export_children()

            self.update_progress(100, "Publish submitted successfully!")
            time.sleep(0.2)

            msg = (
                f"Publish successfully submitted!\n\n"
                f"  • Base Name: {publish_name}\n"
                f"  • Version Type: {version_type}\n"
                f"  • Mattes: {', '.join(selected_nodes.values())}\n"
                f"  • Frame Range: {frame_range[0]}-{frame_range[1]}\n"
                f"  • Destination: {'Local' if is_local else 'Deadline Farm'}"
            )
            QMessageBox.information(self, "Staging Publish Complete", msg)
            self.accept()

        except Exception as err:
            self.progress_bar.setVisible(False)
            self.status_label.setText(f"Error: {err}")
            self.submit_btn.setEnabled(True)
            self.cancel_btn.setEnabled(True)
            QMessageBox.critical(
                self, "Publish Error", f"Failed to complete staging publish:\n\n{err}"
            )
            raise


# ----------------------------------------------------------------------
# 4. Entrypoint
# ----------------------------------------------------------------------
def launch_staging_publish():
    """
    Main entrypoint called from Silhouette BFSTOOLS 'Staging Publish' menu item.
    """
    active_proj = fx.activeProject()
    if not active_proj or not active_proj.path:
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setText(
            "No active Silhouette project found. Please open or save a project first."
        )
        msg_box.setWindowTitle("Staging Publish - Warning")
        msg_box.exec_()
        return

    # Extract context data from ShotGrid Toolkit
    project_path = str(active_proj.path)
    try:
        tk = sgtk.sgtk_from_path(project_path)
        ctx = tk.context_from_path(project_path)

        project_name = ctx.project.get("name", os.environ.get("B_SHOW", ""))
        shot_name = ctx.entity.get("name", "") if ctx.entity else ""
        task_name = ctx.step.get("name", "") if ctx.step else ""
        task_id = (
            ctx.task.get("id", os.environ.get("selected_id", ""))
            if ctx.task
            else os.environ.get("selected_id", "")
        )

        fields = ctx.as_template_fields(tk.templates.get("silhouette_shot_work"))
        publish_name = fields.get("name", "test")
    except Exception as err:
        print("[Staging Publish] Warning reading context from path:", err)
        project_name = os.environ.get("B_SHOW", "")
        shot_name = ""
        task_name = "Roto"
        task_id = os.environ.get("selected_id", "")
        publish_name = "test"

    # Connect to ShotGrid (Staging) with in-memory SGTK caching
    SG = sg_requests.ShotgridConnection(project=project_name)
    if task_id:
        try:
            _tk_c = getattr(SG, "_tk_cache", {})
            _ctx_c = getattr(SG, "_ctx_cache", {})
            if "tk" in locals() and tk:
                _tk_c[("Task", int(task_id))] = tk

            _orig_sgtk_from_entity = SG.sgtk_from_entity
            _orig_context_from_entity = SG.context_from_entity

            def _cached_sgtk(entity_type, entity_id):
                key = (str(entity_type), int(entity_id))
                if key not in _tk_c:
                    _tk_c[key] = _orig_sgtk_from_entity(entity_type, entity_id)
                return _tk_c[key]

            def _cached_ctx(entity_type, entity_id):
                key = (str(entity_type), int(entity_id))
                if key not in _ctx_c:
                    _ctx_c[key] = _orig_context_from_entity(entity_type, entity_id)
                return _ctx_c[key]

            SG.sgtk_from_entity = _cached_sgtk
            SG.context_from_entity = _cached_ctx
            SG._tk_cache = _tk_c
            SG._ctx_cache = _ctx_c
            SG._sgtk_cache_enabled = True

            SG.change_context("Task", int(task_id))
        except Exception as err:
            print("[Staging Publish] Warning setting task context:", err)

    context_data = {
        "project_name": project_name,
        "shot_name": shot_name,
        "task": task_name,
        "task_id": task_id,
        "name": publish_name,
        "sg": SG,
    }

    # Open dialog
    dlg = StagingPublishDialog(context_data)
    dlg.exec_()


if __name__ == "__main__":
    launch_staging_publish()
