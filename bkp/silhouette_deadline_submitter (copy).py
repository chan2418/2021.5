from fx import *
from PySide2.QtWidgets import *
from PySide2 import QtCore
import socket
import os
import fx
import subprocess
from subprocess import PIPE


def write_plugin_info_file(details):
    plugin_info_file = "/usr/tmp/plugin_info.job"
    with open(plugin_info_file, "w+") as file:
        file.write(details)
    return plugin_info_file


def write_job_info_file(details):
    job_info_file = "/usr/tmp/job_info.job"
    with open(job_info_file, "w+") as file:
        file.write(details)
    return job_info_file


def submit_render(session, job_name="", group="", pool="", frames="", output=""):
    chunk_size = 10
    pool = "2d_pool"
    version = int(fx.version)
    group="2d_group"
    # PostJobScript=/bolt/projects/dev_project/common/himanshutest/pythontest.py    
    plugin_details = f"""
    Version={version}
	Session={session.label}
	Node={output}
    OutputDirectory=
    OutputFilename=
    OutputFormat=
    AdditionalOptions=
    Resolution=full
    Fields=none
    Dominance=even
    RunScript=False
    DisableRender=False
    ScriptFile=
    """

    job_details = f"""
    Plugin=Silhouette
    Name={job_name}
    Comment=
    Department=
    Pool={pool}
    SecondaryPool=
    Group={group}
    Priority=100
    TaskTimeoutMinutes=0
    EnableAutoTimeout=False
    ConcurrentTasks=1
    LimitConcurrentTasksToNumberOfCpus=True
    MachineLimit=0
    MachineName={socket.gethostname()}
    Whitelist=
    LimitGroups=
    JobDependencies=
    OnJobComplete=Nothing
    Frames={frames}
    UserName={os.getlogin()}
    ChunkSize={chunk_size}
    """

    deadline_cmd = "/opt/Thinkbox/Deadline10/bin/deadlinecommand"
    sfx_project = str(fx.activeProject().path)
    job_file = write_job_info_file(str(job_details).strip())
    plugin_file = write_plugin_info_file(str(plugin_details).strip())
    command = [deadline_cmd, job_file, plugin_file, sfx_project]
    process = subprocess.Popen(command, stdout=PIPE, stderr=PIPE)
    print(command)
    stdout, stderr = process.communicate()
    # process.wait()


class BFSRenderSubmission(QWidget):

    def __init__(self, parent=None):
        QWidget.__init__(self, parent=parent)
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        self.grid_layout = QGridLayout()
        self.setWindowTitle("BFS Deadline Submission")
        self.main_layout.addLayout(self.grid_layout)
        self.session = activeSession()
        self.setFixedWidth(800)

        self.all_outputs = {}
        self.create_ui()
        self.create_signals()

    def create_ui(self):
        # Add "Check All" checkbox in a new row
        self.check_all_widget = QCheckBox("Check All")
        self.grid_layout.addWidget(self.check_all_widget, 1, 1, QtCore.Qt.AlignCenter)

        # Column headers
        self.grid_layout.addWidget(QLabel("Name"), 0, 0)
        self.grid_layout.addWidget(QLabel("Check"), 0, 1)
        self.grid_layout.addWidget(QLabel("Output Path"), 0, 2)
        self.grid_layout.addWidget(QLabel("Start Frame"), 0, 3)
        self.grid_layout.addWidget(QLabel("End Frame"), 0, 4)

        index = 2
        for session in fx.activeProject().sessions:
            session_label = QLabel(session.label)
            self.grid_layout.addWidget(QLabel("Session>"), index, 0, QtCore.Qt.AlignRight)
            self.grid_layout.addWidget(session_label, index, 1, QtCore.Qt.AlignRight)
            index += 1

            for output in session.outputs:
                self.grid_layout.addWidget(QLabel(output.label), index, 0)
                check_widget = QCheckBox()
                path_widget = QLineEdit()
                path_widget.setReadOnly(True)
                path_widget.setText(output.properties["path"].value)
                sf_widget = QLineEdit()
                sf_widget.setReadOnly(False)
                sf_widget.setFixedWidth(100)
                sf_widget.setText(str(int(self.session.outputRange[0])))
                ef_widget = QLineEdit()
                ef_widget.setReadOnly(False)
                ef_widget.setFixedWidth(100)
                ef_widget.setText(str(int(self.session.outputRange[1])))

                if output not in self.all_outputs:
                    self.all_outputs[output] = []

                self.all_outputs[output].append((check_widget, path_widget, sf_widget, ef_widget))

                self.grid_layout.addWidget(check_widget, index, 1)
                self.grid_layout.addWidget(path_widget, index, 2)
                self.grid_layout.addWidget(sf_widget, index, 3)
                self.grid_layout.addWidget(ef_widget, index, 4)
                index += 1

        self.submit_button = QPushButton("Submit Selected")
        self.submit_button.setMinimumHeight(50)
        self.grid_layout.addWidget(self.submit_button, index + 1, 3)

    def toggle_check_all(self, checked):
        for output_widgets in self.all_outputs.values():
            for widgets in output_widgets:
                widgets[0].setChecked(checked)

    def all_sessions_outputs_render(self):
        for session in fx.activeProject().sessions:
            for output in session.outputs:
                if self.all_outputs[output][0][0].isChecked():
                    sf_widget = self.all_outputs[output][0][2]
                    ef_widget = self.all_outputs[output][0][3]
                    start_frame = int(sf_widget.text())
                    end_frame = int(ef_widget.text())
                    frames = f"{start_frame}-{end_frame}"
                    submit_render(
                        session,
                        job_name=f"{fx.activeProject().name}_{session.label}_{output.label}",
                        group="",
                        pool="2d_pool",
                        frames=frames,
                        output=output.label,
                    )

    def create_signals(self):
        self.submit_button.clicked.connect(self.all_sessions_outputs_render)
        self.check_all_widget.stateChanged.connect(self.toggle_check_all)


def run_deadline_submission(*args):
    app = QApplication.instance() or QApplication([])
    wdg = BFSRenderSubmission()
    wdg.show()

if __name__ == "__main__":
    run_deadline_submission()
