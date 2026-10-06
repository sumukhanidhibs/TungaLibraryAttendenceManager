"""Automated candidate checks on Windows; uses an isolated install directory."""
import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import tempfile
from contextlib import closing
from pathlib import Path


def run(args, cwd=None):
    try:
        subprocess.run([str(arg) for arg in args], cwd=cwd, check=True, timeout=180)
    except subprocess.CalledProcessError:
        # Windowed executables have no stdout; expose their JSON diagnostics in
        # the host test runner's log before propagating the failure.
        if "--smoke-test" in args:
            result_path = Path(args[args.index("--smoke-test") + 1])
            if result_path.is_file():
                print(result_path.read_text(encoding="utf-8"), flush=True)
        raise


def verify(installer, results_dir):
    if os.name != "nt":
        raise RuntimeError("Installer verification requires Windows")
    # Installation registers this AppId even with /DIR. Never replace a real
    # user's registered installation; run the check on a clean CI runner or VM.
    import winreg
    key = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{A3F2C1D4-5E6B-7F8A-9B0C-1D2E3F4A5B6C}_is1"
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(hive, key):
                raise RuntimeError("An installation already exists. Verify in a clean Windows VM.")
        except FileNotFoundError:
            pass
    installer = Path(installer).resolve()
    results_dir = Path(results_dir).resolve()
    results_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="tunga-install-") as tmp:
        tmp = Path(tmp)
        app = tmp / "TungaLibrary Attendance Manager"

        def registered_uninstaller():
            # Inno can allocate unins001.exe after a reinstall. Use the current
            # registration, rather than assuming a fixed uninstaller number.
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as handle:
                command = winreg.QueryValueEx(handle, "UninstallString")[0]
            path = Path(command.strip().strip('"'))
            assert path.parent.resolve() == app.resolve() and path.is_file(), command
            return path

        switches = ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/TASKS=", f"/DIR={app}"]
        run([installer, *switches, f"/LOG={results_dir / 'install.log'}"])
        exe = app / "TungaLibrary.exe"
        assert exe.is_file(), "Installed executable missing"
        assert not (app / "data" / "attendance.db").exists(), "Installer shipped a database"
        assert not list((app / "photos").iterdir()), "Installer shipped photos"
        smoke = results_dir / "installed-smoke.json"
        run([exe, "--smoke-test", smoke], cwd=tmp)
        result = json.loads(smoke.read_text(encoding="utf-8"))
        assert result["passed"] and result["frozen"], result
        print("PASS: installed frozen runtime smoke", flush=True)

        # Seed a user-created fixture, then demand byte-for-byte persistence.
        db = app / "data" / "attendance.db"
        with closing(sqlite3.connect(db)) as conn:
            conn.execute("CREATE TABLE release_sentinel(value TEXT)")
            conn.execute("INSERT INTO release_sentinel VALUES ('keep attendance')")
            conn.commit()
        photo = app / "photos" / "S-TEST.png"
        photo.write_bytes(b"user-managed photo sentinel")
        report = app / "reports" / "daily" / "keep.txt"
        report.write_text("user-managed export", encoding="utf-8")
        fixtures = [db, photo, report]
        original = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in fixtures}

        def assert_preserved():
            for path in fixtures:
                assert path.is_file(), f"User data lost: {path}"
                assert hashlib.sha256(path.read_bytes()).hexdigest() == original[str(path)], f"User data replaced: {path}"

        run([installer, *switches, f"/LOG={results_dir / 'upgrade.log'}"])
        assert_preserved()
        print("PASS: upgrade preserves database, photo and report", flush=True)
        run([registered_uninstaller(), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
             f"/LOG={results_dir / 'uninstall.log'}"])
        assert_preserved()
        assert not exe.exists(), "Uninstaller left executable behind"
        print("PASS: uninstall removes app and preserves user data", flush=True)
        run([installer, *switches, f"/LOG={results_dir / 'reinstall.log'}"])
        assert_preserved()
        run([exe, "--smoke-test", results_dir / "reinstalled-smoke.json"], cwd=tmp)
        print("PASS: reinstall preserves user data and frozen runtime works", flush=True)
        run([registered_uninstaller(), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"])
    (results_dir / "installer-verification.json").write_text(
        json.dumps({"passed": True, "checks": ["install", "frozen smoke", "upgrade preserves user data",
                                               "uninstall preserves user data", "reinstall preserves user data"]}, indent=2),
        encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("installer")
    parser.add_argument("results_dir")
    args = parser.parse_args()
    verify(args.installer, args.results_dir)

