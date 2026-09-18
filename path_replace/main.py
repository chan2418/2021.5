"""
sfx_path_replace.py  –  Find & Replace source paths in Boris FX Silhouette
===========================================================================

Targets the Source items that live in the Project panel (the footage nodes
that sessions pull their frames from).  In Silhouette the path property is
accessed via:

    source.properties["path"].getValue()          # read
    source.properties["path"].setValue("...")     # write

OBJECT MODEL TRAVERSAL
----------------------
    fx.activeProject()
        └── project.sources          ← all Source footage items
            └── source.properties["path"]

HOW TO INSTALL
--------------
Copy this file to Silhouette's actions directory, e.g.:

    Linux / Windows
        $SFX_SCRIPT_PATH/actions/sfx_path_replace.py
    macOS
        ~/Library/Application Support/BorisFX/Silhouette/scripts/actions/sfx_path_replace.py

Restart Silhouette.  The tool appears under  Actions › Pipeline › Path Find & Replace.

Alternatively, paste this whole file into the Silhouette Script Console to
run it immediately without restarting.

USAGE
-----
Actions › Pipeline › Path Find & Replace
"""

import re

import fx

try:
    from PySide2 import QtCore, QtWidgets
except ImportError:
    from PySide6 import QtCore, QtWidgets  # Silhouette 2023+ ships PySide6


# ---------------------------------------------------------------------------
# Core helpers  (can be used headlessly from the Script Console)
# ---------------------------------------------------------------------------


def _source_label(src):
    """Best-effort label for a Source item."""
    label = getattr(src, "label", None)
    if label:
        return label
    name_prop = src.properties.get("name") if hasattr(src, "properties") else None
    if name_prop is not None:
        return getattr(name_prop, "label", None) or getattr(name_prop, "value", None) or repr(name_prop)
    return repr(src)


def _get_path_property(src):
    """Return the path property object for a Source, or None."""
    try:
        props = getattr(src, "properties", None)
        if props is None:
            return None
        if hasattr(props, "get"):
            return props.get("path")
        return props["path"]
    except Exception:
        return None


def _read_path(path_prop):
    """Read a path property value (supports getValue() and .value)."""
    if path_prop is None:
        return ""
    try:
        if hasattr(path_prop, "getValue"):
            return path_prop.getValue() or ""
        return path_prop.value or ""
    except Exception:
        return ""


def _write_path(path_prop, new_path):
    """Write a path property value (prefer setValue, fall back to .value)."""
    if hasattr(path_prop, "setValue"):
        path_prop.setValue(new_path)
    else:
        path_prop.value = new_path


def _all_sources(project=None):
    """Return every Source object in the active (or given) project."""
    project = project or fx.activeProject()
    if project is None:
        return []

    # Preferred API used across this codebase (deadline submitter, remapper, etc.)
    sources = getattr(project, "sources", None)
    if sources is not None:
        return list(sources)

    # Fallback: walk top-level project items
    sources = []
    for item in getattr(project, "items", []) or []:
        if isinstance(item, fx.Source):
            sources.append(item)
    return sources


def find_sources(search, use_regex=False, project=None):
    """
    Return list of (source, current_path) for every Source whose path matches.
    """
    results = []
    pattern = re.compile(search) if use_regex else None

    for src in _all_sources(project):
        path_prop = _get_path_property(src)
        path = _read_path(path_prop)
        if not path and path_prop is None:
            continue

        hit = (pattern.search(path) is not None) if use_regex else (search in path)
        if hit:
            results.append((src, path))

    return results


def replace_source_paths(search, replace, use_regex=False, project=None):
    """
    Replace paths on all matching Source items with proper undo support.

    Returns list of dicts: {label, old_path, new_path}
    """
    project = project or fx.activeProject()
    if project is None:
        return []

    hits = find_sources(search, use_regex, project)
    if not hits:
        return []

    changed = []
    fx.beginUndo("Path Find & Replace")
    try:
        for src, old_path in hits:
            if use_regex:
                new_path = re.sub(search, replace, old_path)
            else:
                new_path = old_path.replace(search, replace)

            if new_path != old_path:
                path_prop = _get_path_property(src)
                if path_prop is None:
                    continue
                _write_path(path_prop, new_path)
                changed.append(
                    {
                        "label": _source_label(src),
                        "old_path": old_path,
                        "new_path": new_path,
                    }
                )
    finally:
        fx.endUndo()

    return changed


# ---------------------------------------------------------------------------
# PySide dialog
# ---------------------------------------------------------------------------


class PathReplaceDialog(QtWidgets.QDialog):
    """Modal Find & Replace dialog with preview and undo-safe replace."""

    def __init__(self, parent=None):
        super(PathReplaceDialog, self).__init__(parent)
        self.setWindowTitle("Path Find & Replace  –  Silhouette")
        self.setMinimumWidth(620)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(12, 12, 12, 12)

        # ── Find / Replace fields ──────────────────────────────────────
        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignRight)

        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("e.g.  /project_01")
        form.addRow("Find:", self.search_edit)

        self.replace_edit = QtWidgets.QLineEdit()
        self.replace_edit.setPlaceholderText("e.g.  /project_02")
        form.addRow("Replace with:", self.replace_edit)

        root.addLayout(form)

        # ── Options ───────────────────────────────────────────────────
        opt_row = QtWidgets.QHBoxLayout()
        self.regex_chk = QtWidgets.QCheckBox("Use regex")
        self.regex_chk.setToolTip(
            "Treat 'Find' as a Python regular expression.\n"
            "Back-references (\\1, \\2 …) work in 'Replace with'."
        )
        opt_row.addWidget(self.regex_chk)
        opt_row.addStretch()
        root.addLayout(opt_row)

        # ── Buttons ───────────────────────────────────────────────────
        btn_row = QtWidgets.QHBoxLayout()
        self.preview_btn = QtWidgets.QPushButton("Preview Matches")
        self.replace_btn = QtWidgets.QPushButton("Replace All")
        self.close_btn = QtWidgets.QPushButton("Close")

        self.replace_btn.setDefault(True)

        btn_row.addWidget(self.preview_btn)
        btn_row.addWidget(self.replace_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.close_btn)
        root.addLayout(btn_row)

        # ── Result log ────────────────────────────────────────────────
        root.addWidget(QtWidgets.QLabel("Results:"))
        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(200)
        self.log.setStyleSheet(
            "QPlainTextEdit { font-family: monospace; font-size: 11px; }"
        )
        self.log.setPlaceholderText("Results will appear here…")
        root.addWidget(self.log)

        # ── Connections ───────────────────────────────────────────────
        self.preview_btn.clicked.connect(self._do_preview)
        self.replace_btn.clicked.connect(self._do_replace)
        self.close_btn.clicked.connect(self.close)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _search(self):
        return self.search_edit.text().strip()

    def _replace(self):
        return self.replace_edit.text()  # allow empty (deletion)

    def _use_regex(self):
        return self.regex_chk.isChecked()

    def _log(self, text):
        self.log.setPlainText(text)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _do_preview(self):
        search = self._search()
        if not search:
            self._log("⚠  Please enter a search string.")
            return

        try:
            hits = find_sources(search, self._use_regex())
        except re.error as exc:
            self._log("⚠  Regex error: {}".format(exc))
            return

        if not hits:
            self._log("No matching Source items found.")
            return

        lines = ["Found {} matching Source(s):\n".format(len(hits))]
        for src, path in hits:
            lines.append("  [{label}]".format(label=_source_label(src)))
            lines.append("  {path}\n".format(path=path))

        self._log("\n".join(lines))

    def _do_replace(self):
        search = self._search()
        replace = self._replace()

        if not search:
            self._log("⚠  Please enter a search string.")
            return

        try:
            changed = replace_source_paths(search, replace, self._use_regex())
        except re.error as exc:
            self._log("⚠  Regex error: {}".format(exc))
            return

        if not changed:
            self._log("No Source paths were changed.")
            return

        lines = ["✓  Replaced {} Source path(s):\n".format(len(changed))]
        for entry in changed:
            lines.append("  Source : {}".format(entry["label"]))
            lines.append("  From   : {}".format(entry["old_path"]))
            lines.append("  To     : {}".format(entry["new_path"]))
            lines.append("")

        self._log("\n".join(lines))
        fx.status("Path Replace: {} source(s) updated.".format(len(changed)))


# ---------------------------------------------------------------------------
# Silhouette Action class  (shows up in Actions menu)
# ---------------------------------------------------------------------------


class PathReplaceAction(fx.Action):
    """
    Silhouette Action: BFSTOOLS | Path Find & Replace

    Walks every Source item in the active project and lets the user
    find/replace parts of the file path with undo support.
    """

    def __init__(self):
        fx.Action.__init__(
            self,
            label="Path Find & Replace                  ",
            root="BFSTOOLS",
        )

    def available(self):
        assert "Create First Project"

    def execute(self):
        show()


# ---------------------------------------------------------------------------
# Quick-launch from the Script Console
# ---------------------------------------------------------------------------


def show():
    """Open the dialog directly from the Script Console."""
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    dlg = PathReplaceDialog()
    dlg.exec_()
