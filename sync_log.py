"""Weekly local sync: pull log.csv from the ESP8684 device (COM3) and push it to GitHub.

Runs unattended via Windows Task Scheduler. Requires physical USB access to the
device, so this step cannot run in the cloud — the weekly Notion update (separate
cloud routine) reads the log.csv this script pushes.
"""
import subprocess
import sys
import time
import csv
import io
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_DIR = Path(r"c:\dev\rpr0521_test")
LOG_FILE = REPO_DIR / "log.csv"
COM_PORT = "COM3"
LOGGER_SCRIPT = "overnight_logger.py"
# mpremote is only installed under this interpreter, not the `py -3.14` default
PYTHON_MPREMOTE = r"C:\Users\highm\AppData\Local\Programs\Python\Python312\python.exe"


def run(cmd, **kw):
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", **kw)


def stop_logger_process():
    ps = (
        "Get-CimInstance Win32_Process | "
        f"Where-Object {{$_.CommandLine -like '*mpremote*{LOGGER_SCRIPT}*'}} | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Output \"stopped $($_.ProcessId)\" }"
    )
    r = run(["powershell", "-NoProfile", "-Command", ps])
    print(r.stdout.strip() or "(no running logger process found)")
    time.sleep(2)


def start_logger_process():
    ps = (
        f"Start-Process -FilePath '{PYTHON_MPREMOTE}' -ArgumentList "
        f"'-m mpremote connect {COM_PORT} run {LOGGER_SCRIPT}' "
        f"-WorkingDirectory '{REPO_DIR}' -WindowStyle Hidden"
    )
    r = run(["powershell", "-NoProfile", "-Command", ps])
    if r.returncode != 0:
        print("WARNING: failed to restart logger:", r.stderr)


def fetch_device_log(tmp_path: Path) -> bool:
    r = run([PYTHON_MPREMOTE, "-m", "mpremote", "connect", COM_PORT, "fs", "cp", ":log.csv", str(tmp_path)])
    if r.returncode != 0:
        print("ERROR: could not read log.csv from device:", r.stderr)
        return False
    return True


def merge_logs(device_csv: Path, repo_csv: Path):
    rows = list(csv.reader(io.open(device_csv, encoding="utf-8")))
    if not rows:
        return False
    header, data = rows[0], rows[1:]
    clean = []
    prev_ts = None
    for r in data:
        if not r:
            continue
        ts = r[0]
        if prev_ts and ts < prev_ts:
            continue  # drop any RTC-reset anomaly rows
        clean.append(r)
        prev_ts = ts
    with open(repo_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(clean)
    print(f"merged {len(clean)} rows into {repo_csv}")
    return True


def git_push():
    run(["git", "add", "log.csv"], cwd=REPO_DIR)
    diff = run(["git", "diff", "--cached", "--quiet"], cwd=REPO_DIR)
    if diff.returncode == 0:
        print("no changes to log.csv, skipping commit/push")
        return
    commit = run(
        ["git", "commit", "-m", f"Weekly log sync ({time.strftime('%Y-%m-%d')})"],
        cwd=REPO_DIR,
    )
    print(commit.stdout, commit.stderr)
    push = run(["git", "push"], cwd=REPO_DIR)
    print(push.stdout, push.stderr)
    if push.returncode != 0:
        print("ERROR: git push failed")


def main():
    stop_logger_process()
    tmp_path = REPO_DIR / "_device_log_tmp.csv"
    ok = fetch_device_log(tmp_path)
    start_logger_process()  # restart logging ASAP regardless of merge outcome
    if not ok:
        sys.exit(1)
    merge_logs(tmp_path, LOG_FILE)
    tmp_path.unlink(missing_ok=True)
    git_push()


if __name__ == "__main__":
    main()
