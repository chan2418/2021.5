#!/usr/bin/env python3

import os
import subprocess
import argparse
import sys


def find_deadline_cmd():
    paths = [
        "/opt/Thinkbox/Deadline10/bin/deadlinecommand",
        "/apps/Thinkbox/Deadline10/bin/deadlinecommand",
    ]
    for path in paths:
        if os.path.exists(path):
            return path
    return None


def submit_to_deadline(job_file, plugin_file, nuke_file):
    deadline_cmd = find_deadline_cmd()
    if not deadline_cmd:
        sys.exit("❌ Deadline command not found.")

    for f in (job_file, plugin_file, nuke_file):
        if not os.path.exists(f):
            sys.exit(f"❌ File not found: {f}")

    command = [
        deadline_cmd,
        job_file,
        plugin_file,
        nuke_file,
    ]

    print("🚀 Deadline Submit Command:")
    print(" ".join(command))

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    stdout, stderr = process.communicate()

    if stderr:
        print("⚠️ Deadline STDERR:")
        print(stderr)

    print("📄 Deadline STDOUT:")
    print(stdout)

    job_id = None
    for line in stdout.splitlines():
        if line.startswith("JobID="):
            job_id = line.split("=", 1)[1].strip()
            break

    if job_id:
        print(f"✅ Job submitted successfully | JobID: {job_id}")
    else:
        print("❌ Job submission failed (no JobID).")

    return job_id


def main():
    parser = argparse.ArgumentParser(
        description="Submit a Nuke job to Deadline (.job files)"
    )

    parser.add_argument(
        "--job",
        required=True,
        help="Path to Job Info (.job)",
    )

    parser.add_argument(
        "--plugin",
        required=True,
        help="Path to Plugin Info (.job)",
    )

    parser.add_argument(
        "--nuke",
        required=True,
        help="Path to Nuke script (.nk)",
    )

    args = parser.parse_args()

    submit_to_deadline(
        job_file=args.job,
        plugin_file=args.plugin,
        nuke_file=args.nuke,
    )


if __name__ == "__main__":
    main()
