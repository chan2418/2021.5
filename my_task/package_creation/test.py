import os

path = "/projects/bb_nciss4/401_036_0035/dept/roto/chandru/.nmb"


def _chmod_recursive(self, path, mode):
    try:
        os.chmod(path, mode)
        for root, dirs, files in os.walk(path):
            for d in dirs:
                os.chmod(os.path.join(root, d), mode)
            for f in files:
                os.chmod(os.path.join(root, f), mode)
    except PermissionError as e:
        print(f"Permission denied {path} please check {e}")
