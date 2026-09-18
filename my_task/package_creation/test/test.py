import glob
import os
import re
import shutil
from concurrent.futures import ThreadPoolExecutor


def parse_pattern(pattern):
    directory = os.path.dirname(pattern)
    filename = os.path.basename(pattern)
    match = re.match(r"(.*)%(\d+)d(.*)$", filename)
    if match:
        prefix, padding, suffix = match.groups()
        padding = int(padding)
    else:
        raise ValueError("Invalid pattern: frame number placeholder (%Nd) not found")
    return directory, prefix, padding, suffix


def copy_file(src_file, src_info, dest_info):
    src_dir, src_prefix, src_padding, src_suffix = src_info
    dest_dir, dest_prefix, dest_padding, dest_suffix = dest_info
    frame_number_match = re.search(r"(\d+)", src_file[len(src_dir) + len(src_prefix) :])
    if frame_number_match:
        frame_number = int(frame_number_match.group(1))
    else:
        raise ValueError(f"Unable to extract frame number from {src_file}")
    dest_file = os.path.join(
        dest_dir, f"{dest_prefix}{frame_number:0{dest_padding}d}{dest_suffix}"
    )

    os.makedirs(os.path.dirname(dest_file), exist_ok=True)
    shutil.copy2(src_file, dest_file)
    print(f"Copied: {src_file} -> {dest_file}")


def main(source_pattern, dest_pattern):
    src_info = parse_pattern(source_pattern)
    dest_info = parse_pattern(dest_pattern)
    src_dir, src_prefix, src_padding, src_suffix = src_info
    source_files = glob.glob(os.path.join(src_dir, f"{src_prefix}*{src_suffix}"))

    with ThreadPoolExecutor() as executor:
        executor.map(lambda f: copy_file(f, src_info, dest_info), source_files)


if __name__ == "__main__":
    main(
        "/projects/ie_flx/FLX_1003_0220/dept/publish/roto/render/FLX_1003_0220_roto_test_matteA_v001/FLX_1003_0220_roto_test_matteA_v001.%04d.exr",
        "/projects/ie_flx/FLX_1003_0220/dept/upload/roto/test/v001/flx_1003_0220/flx_1003_0220_test_v001_matteA_mattes_v001/flx_1003_0220_test_v001_matteA_mattes_v001.%04d.exr",
    )
