# sg_manager.py
import sgtk
from sgtk.authentication import ShotgunAuthenticator

class SGManager:
    def __init__(self):
        self.user = self.authenticate()
        self.sg = self.user.create_sg_connection()

    def authenticate(self):
        sa = ShotgunAuthenticator()
        return sa.get_user()

    def find_versions(self, project_name, shot_id):
        filters = [["project.Project.name", "is", project_name],
                   ["entity.Shot.id", "is", shot_id]]
        fields = ["code", "sg_path_to_frames", "sg_status_list"]
        return self.sg.find("Version", filters, fields)

    def register_publish(self, context, path, name, version):
        return sgtk.util.register_publish(
            context.tk, context, path, name, version,
            published_file_type="Rendered Image"
        )
