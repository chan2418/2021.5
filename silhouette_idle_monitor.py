import datetime
import getpass
import logging
import os
import pathlib
import socket
import sys
import threading
import time
from logging.handlers import RotatingFileHandler

import fx
import hook
from PySide2.QtCore import QTimer
from PySide2.QtWidgets import QMessageBox, QPushButton, QSizePolicy, QSpacerItem

import silhouette_auto_mail

# Setup usage logger (unchanged)
user_name = getpass.getuser()
log_dir = "/tools/DCC_idle_monitor/logs/{}".format(user_name)
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
    os.chmod(log_dir, 0o777)

usage_log_path = os.path.join(log_dir, "usage.log")
if not os.path.exists(usage_log_path):
    open(usage_log_path, "a").close()
    os.chmod(usage_log_path, 0o666)

usage_logger = logging.getLogger("SilhouetteIdleMonitor")
usage_logger.setLevel(logging.INFO)
# Guard against duplicate handlers if this module gets re-executed in the
# same session (e.g. re-run from the script editor without restarting the app).
if not usage_logger.handlers:
    handler = RotatingFileHandler(
        usage_log_path, maxBytes=5 * 1024 * 1024, backupCount=5
    )
    formatter = logging.Formatter(
        "%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    usage_logger.addHandler(handler)

print("Inside SilhouetteIdleMonitor!")


def rotate_autosaves(directory, keep_count=5, prefix="autosave_"):
    """Keep only the most recent `keep_count` autosave files in `directory`,
    deleting older ones. Only touches files starting with `prefix` so it
    never removes unrelated files. A `keep_count` of 0 or less means
    "keep everything" (no deletion), to avoid accidental wipes from a bad
    config value."""
    if not directory or not os.path.isdir(directory) or keep_count <= 0:
        return

    try:
        autosave_files = [
            os.path.join(directory, f)
            for f in os.listdir(directory)
            if f.startswith(prefix) and os.path.isfile(os.path.join(directory, f))
        ]
        # Oldest first, so we know which ones to drop from the front.
        autosave_files.sort(key=os.path.getmtime)

        files_to_delete = (
            autosave_files[:-keep_count] if len(autosave_files) > keep_count else []
        )
        for old_file in files_to_delete:
            try:
                os.remove(old_file)
                print("Removed old autosave: {0}".format(old_file))
            except Exception as e:
                print(
                    "Warning: failed to remove old autosave {0}: {1}".format(
                        old_file, e
                    )
                )
    except Exception as e:
        print("Warning: failed to rotate autosaves in {0}: {1}".format(directory, e))


class SilhouetteIdleMonitor:  # 1800
    def __init__(
        self,
        check_idle_time=1800,
        popup_timeout=45,
        ignore_threshold=300,
        autosave_keep_count=5,
    ):
        print("[Init] Initializing Silhouette Idle Monitor...")
        self.check_idle_time = check_idle_time
        self.popup_timeout = popup_timeout
        self.ignore_threshold = ignore_threshold
        self.autosave_keep_count = (
            autosave_keep_count  # how many local autosaves to retain
        )

        self.last_activity_time = time.time()
        self.is_rendering = False
        self.ignore_mode = False
        self.ignore_start_time = None
        self.auto_close_count = 0
        self.cumulative_idle_time = 0
        self.popup_suppressed_until = 0

        self.current_usr = getpass.getuser()

        self.autosave_local_dir = os.path.expanduser("~/Documents/SilhouetteAutoSave")
        if not pathlib.Path(self.autosave_local_dir).exists():
            pathlib.Path(self.autosave_local_dir).mkdir(parents=True)
            print(f"[Init] Created autosave directory: {self.autosave_local_dir}")

        self.silhouette_version = fx.version
        self.silhouette_open_time: datetime.datetime = datetime.datetime.now()
        self.silhouette_open_time_formatted = self.silhouette_open_time.strftime(
            "%I:%M %p"
        )
        print(f"[Info] Silhouette version: {self.silhouette_version}")
        print(f"[Info] Open time: {self.silhouette_open_time_formatted}")

        # Kept as an instance attribute so teardown() can unregister the same list.
        self.activity_callbacks = [
            "frameChanged",
            "selectionChanged",
            "object_created",
            "node_selected",
            "post_load",
            "object_added",
            "object_removed",
        ]
        for cb in self.activity_callbacks:
            hook.add(cb, self.update_last_activity)
        hook.add("pre_render", self.render_started)
        hook.add("post_render", self.render_finished)

        self.idle_check_timer = QTimer()
        self.idle_check_timer.timeout.connect(self.idle_status)
        self.idle_check_timer.start(5000)
        print("[Init] Idle checker running (interval: 5s) ...")

    def restart_idle_timer(self, interval=5000):
        """Small helper to avoid repeating the same start(...) call everywhere,
        and to keep the interval choice in one place."""
        self.idle_check_timer.start(interval)

    def teardown(self):
        """Stop the timer and unregister all hooks. Call this before discarding
        a monitor instance (e.g. when replacing it)."""
        print("[Teardown] Tearing down Silhouette Idle Monitor...")
        self.idle_check_timer.stop()
        for cb in self.activity_callbacks:
            try:
                hook.remove(cb, self.update_last_activity)
            except Exception as e:
                print(f"Warning: failed to remove '{cb}' hook: {e}")
        try:
            hook.remove("pre_render", self.render_started)
        except Exception as e:
            print(f"Warning: failed to remove 'pre_render' hook: {e}")
        try:
            hook.remove("post_render", self.render_finished)
        except Exception as e:
            print(f"Warning: failed to remove 'post_render' hook: {e}")

    def update_last_activity(self, event=None):
        print("[Hook] Activity detected!")
        current_time = time.time()
        idle_duration = current_time - self.last_activity_time
        self.cumulative_idle_time += idle_duration
        self.last_activity_time = current_time
        if self.ignore_mode:
            print("[Hook] Exiting ignore mode.")
            self.ignore_mode = False
            self.ignore_start_time = None
        print(
            f"[Hook] Last activity updated at {datetime.datetime.fromtimestamp(self.last_activity_time)}"
        )

    def render_started(self):
        self.is_rendering = True
        print("[Hook] Render started!")

    def render_finished(self):
        self.is_rendering = False
        self.last_activity_time = time.time()
        print("[Hook] Render finished!")

    def idle_status(self):
        if self.is_rendering:
            return
        current_time = time.time()
        idle_time = current_time - self.last_activity_time

        if self.ignore_mode:
            ignore_elapsed = current_time - self.ignore_start_time
            if (
                idle_time > self.ignore_threshold
                and ignore_elapsed > self.ignore_threshold
            ):
                self.ignore_mode = False
                self.ignore_start_time = None
                self.popup_message()
            else:
                print(
                    f"[Idle] In ignore mode. Idle: {idle_time:.1f}s, Elapsed: {ignore_elapsed:.1f}s"
                )
            return

        if idle_time > self.check_idle_time:
            if time.time() < self.popup_suppressed_until:
                self.restart_idle_timer(10000)
            else:
                self.idle_check_timer.stop()
                self.popup_message()

    def popup_message(self):
        timeout = [self.popup_timeout]
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Idle Alert")
        msg_box.setFixedSize(600, 200)
        msg_box.setText(
            f"Silhouette has been idle.\nThis window will close in {timeout[0]} seconds."
        )

        save_close_button = QPushButton("Save and Close")
        ignore_button = QPushButton("Ignore")
        msg_box.addButton(save_close_button, QMessageBox.AcceptRole)
        msg_box.addButton(ignore_button, QMessageBox.DestructiveRole)
        layout = msg_box.layout()
        spacer = QSpacerItem(700, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
        layout.addItem(spacer, layout.rowCount(), 0, 1, layout.columnCount())

        def update_countdown():
            timeout[0] -= 1
            if timeout[0] <= 0:
                countdown_timer.stop()
                msg_box.done(0)
            else:
                msg_box.setText(
                    f"Silhouette has been idle.\nThis window will close in {timeout[0]} seconds."
                )

        countdown_timer = QTimer()
        countdown_timer.timeout.connect(update_countdown)
        countdown_timer.start(1000)
        msg_box.exec_()
        countdown_timer.stop()

        clicked_button = msg_box.clickedButton()
        if clicked_button == save_close_button:
            print("[Popup] User clicked Save and Close.")
            self.on_save_and_close()
        elif clicked_button == ignore_button:
            print("[Popup] User clicked Ignore.")
            self.ignore_mode = True
            self.ignore_start_time = time.time()
            self.last_activity_time = time.time()
            self.restart_idle_timer(5000)
        else:
            self.auto_close_count += 1
            print(f"[Popup] Auto-close count: {self.auto_close_count}")
            if self.auto_close_count > 2:
                print("[Popup] Auto-close count > 2, saving and closing.")
                self.on_save_and_close()
            else:
                self.popup_suppressed_until = time.time() + 300  # 5 minutes
                print(
                    f"Popup auto-closed, suppressing next popup for 5 minutes.{self.popup_suppressed_until}"
                )
                self.restart_idle_timer(10000)

    def make_formailized_usr_name(self):
        user_name = self.current_usr
        split_usr_name = user_name.split(".")
        make_capitalize = [name.capitalize() for name in split_usr_name]
        formalized_name = " ".join(make_capitalize)
        return formalized_name

    def auto_close_mail(self, file_name, scene_path_server, scene_path_local):
        try:
            in_mail = silhouette_auto_mail.CreateMail()
            mail_domain = "@basilicfly.co"
            form_to_address = self.current_usr + mail_domain
            in_mail.to_address = [form_to_address]
            in_mail.cc_address = [""]
            in_mail.subject = f"Silhouette Auto-Closed - scene saved: {file_name}"
            email_body = (
                "Hi {},\n\n"
                "Silhouette on {} was auto-closed at {}.\n"
                "Scene saved at:\nFrom Input Location: {}\n\n"
                "Local Location: {}\n\n"
                "Have a great day!\n\nRegards,\nAuto Close System"
            ).format(
                self.make_formailized_usr_name(),
                socket.gethostname(),
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                scene_path_server,
                scene_path_local,
            )
            in_mail.append_body(email_body)
            in_mail.send_mail()
            print("[Mail] Auto-close mail sent successfully.")
        except Exception as e:
            # Don't let a mail failure block or crash the shutdown flow.
            print(f"Warning: failed to send auto-close mail: {e}")

    def send_mail_async(self, file_name, scene_path_server, scene_path_local):
        """Fire-and-forget the mail send so it never blocks sys.exit()."""
        mail_thread = threading.Thread(
            target=self.auto_close_mail,
            args=(file_name, scene_path_server, scene_path_local),
            daemon=True,
        )
        mail_thread.start()

    def on_save_and_close(self):
        print("[SaveClose] Attempting to auto-save and close...")
        project = fx.activeProject()
        current_script_path = project.path if hasattr(project, "path") else None
        file_name = (
            pathlib.Path(current_script_path).name
            if current_script_path
            else "untitled.sfx"
        )
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        autosave_server_file = None
        autosave_local_file = None

        print("Current script path:", current_script_path)
        if self.autosave_local_dir:
            try:
                autosave_local_file = os.path.join(
                    self.autosave_local_dir, f"autosave_{timestamp}_{file_name}"
                )
                print(f"[SaveClose] Local autosave: {autosave_local_file}")
                project.save(autosave_local_file)
                rotate_autosaves(self.autosave_local_dir, self.autosave_keep_count)
            except Exception as e:
                print(f"Warning: failed to save local autosave: {e}")
                autosave_local_file = None

        # Server-side behavior kept as original: overwrite the live project
        # file in place (no timestamped copy, no rotation on this side).
        if current_script_path and current_script_path.lower().endswith(".sfx"):
            print(f"[SaveClose] Server autosave: {current_script_path}")
            try:
                p = project.save()
                autosave_server_file = current_script_path
                print("P:", p)
            except Exception as e:
                print(f"Failed to save project: {e}")

        auto_close_timestamp = int(time.time())
        formatted_auto_close_time = datetime.datetime.fromtimestamp(
            auto_close_timestamp
        ).strftime("%I:%M %p")
        self.setup_logging(
            software_auto_close_time=formatted_auto_close_time,
            autosave_server_file=autosave_server_file,
            autosave_local_file=autosave_local_file,
        )

        # Mail sending is fixed (async + error-handled) but left disabled here,
        # matching current behavior. Uncomment to re-enable:
        # self.send_mail_async(file_name=file_name, scene_path_server=autosave_server_file, scene_path_local=autosave_local_file)
        print("[SaveClose] Closing Silhouette... (sys.exit called)")
        sys.exit()

    def setup_logging(
        self, software_auto_close_time, autosave_server_file, autosave_local_file
    ):
        user = self.make_formailized_usr_name()
        date = datetime.date.today().isoformat()
        dcc_name = "Silhouette"
        dcc_version = self.silhouette_version
        open_time = self.silhouette_open_time_formatted
        idle_time = float(f"{self.cumulative_idle_time / 60.0:.2f}")
        auto_close_time = software_auto_close_time

        log_message = "{} | {} | {} | {} | {} | {} | {} | {} | {}".format(
            user,
            date,
            dcc_name,
            dcc_version,
            idle_time,
            open_time,
            auto_close_time,
            autosave_server_file,
            autosave_local_file,
        )
        usage_logger.info(log_message)
        print(f"Logged usage data for {user} on {date} with idle_time={idle_time}")


# Module-level singleton guard: prevents duplicate hooks/timers if this
# script is re-run without restarting Silhouette.
_monitor_instance = None


def start_idle_monitor(
    check_idle_time=1800,
    popup_timeout=45,
    ignore_threshold=300,
    autosave_keep_count=5,
):
    global _monitor_instance
    if _monitor_instance is not None:
        print("[Debug] Idle monitor already running — tearing down old instance first.")
        _monitor_instance.teardown()
        _monitor_instance = None

    _monitor_instance = SilhouetteIdleMonitor(
        check_idle_time=check_idle_time,
        popup_timeout=popup_timeout,
        ignore_threshold=ignore_threshold,
        autosave_keep_count=autosave_keep_count,
    )
    print("[Debug] Silhouette idle monitoring script setup complete.")
    return _monitor_instance


def stop_idle_monitor():
    global _monitor_instance
    if _monitor_instance is not None:
        _monitor_instance.teardown()
        _monitor_instance = None
    else:
        print("[Debug] No idle monitor is currently running.")
