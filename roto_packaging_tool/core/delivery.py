# delivery.py
import shutil
import os

class Delivery:
    def copy_file(self, src, dst):
        shutil.copy2(src, dst)

    def compress_exr(self, path, compression="zip"):
        print(f"Compressing {path} with {compression}")
        # TODO: call OpenImageIO or Nuke write node settings

    def make_mov(self, exr_sequence, mov_path, codec="prores"):
        cmd = f"ffmpeg -i {exr_sequence} -c:v {codec} {mov_path}"
        os.system(cmd)
