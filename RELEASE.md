# Windows installer release

Target: Windows 10 22H2 x64 and Windows 11 x64, per-user installation.
Application version: 1.0.1. Keep the existing AppId for future upgrades.

## Build a candidate

Use a clean Windows x64 build environment with Python 3.11.9 and Inno Setup
6.4.3. From the repository root, run:

```powershell
python -m venv .venv-build
.\.venv-build\Scripts\Activate.ps1
.\tools\build_windows.ps1
```

The script installs the pinned Windows dependency set, builds the complete
PyInstaller one-folder bundle, compiles the installer, and writes a SHA-256
checksum. The GitHub Actions workflow also verifies the exact Inno Setup
download and saves the candidate, dependency versions and test logs as artifacts.
Artifacts are test candidates, not published releases. A failed job can still
upload diagnostic files; only consider candidates from successful jobs.

The installer payload contains application files only. The application creates
an empty attendance database on first normal launch. Import students through
"Import Students CSV" (columns: studentid, name, class), then copy approved
photos named after the student ID into the installation's photos directory.
Do not distribute the repository's production database or student photos in the
generic installer. PNG, JPG and JPEG variants are supported.

Default installation and persistent data location:
`%LocalAppData%\TungaLibrary Attendance Manager`.
Normal installation stays per-user and does not offer directory selection or
elevation. Command-line /DIR overrides are for controlled testing in writable
locations. Installing in Program Files is unsupported with the current data
layout. Separate Windows accounts have separate attendance databases.

## Automated verification

On a clean Windows VM with no registered TungaLibrary installation:

```powershell
python tools\verify_windows_install.py installer\Output\TungaLibrarySetup.exe release-checks
```

This installs into a temporary directory, checks the frozen executable from a
different working directory, and verifies upgrade, uninstall and reinstall
preserve user-created database/photo/report fixtures. It does not launch the
scanner or dashboard. The installed EXE's opt-in `--smoke-test RESULT_JSON`
checks Qt, Charts, fonts, images, paths, empty database initialization, CSV import,
database reinitialization, XLSX exports and basic PDF generation. Its writes use
temporary fixtures and never the live database. Interactive filtered PDF export
still requires the manual check below.

## Distribution gate

- [ ] Windows workflow passes for the exact release commit; inspect warnings,
      installer logs, smoke results and recorded dependency versions.
- [ ] On a clean target PC without Python, install as a standard user, launch
      normally, import CSV and confirm the empty database becomes usable.
- [ ] Desktop and Start Menu shortcuts have the right icon; tray reopen/exit,
      dashboard, themes and display scaling work.
- [ ] Actual scanner check-in/out, duplicate scans, present count, manual-input
      pause/resume and background capture work without unwanted focus changes.
- [ ] PNG/JPG/JPEG and missing photos display correctly; daily/monthly/student
      XLSX and filtered student PDF open with correct content and totals.
- [ ] Check report dates at midnight/month boundaries and verify attendance
      duration rules. Existing code inflates visits below four minutes to a random
      8–15m59s, and closes stale sessions with random 40–50m durations. Approve or
      change this policy before using reports as actual measured attendance.
- [ ] Restart and test a real previous-version upgrade with a backed-up database.
      Same-version reinstall checks do not prove old-schema migration. init_db()
      creates missing tables but does not migrate existing table columns.
- [ ] Test uninstall/reinstall and backup/restore on realistic data. Keep data,
      photos and reports by default; delete them separately only if intended.
- [ ] Test Defender/SmartScreen and the college's deployment restrictions. Decide
      on code signing; this workflow does not sign or publish the installer.
- [ ] Set the final version, sign if required, then compute the distributed
      installer's SHA-256 again. Record the source commit and release notes.

Before backup, exit the app through its tray menu. Copy the entire data folder
(including any SQLite WAL/SHM files), photos and reports to a separate location.
Do not use uninstall/reinstall as a database reset. Installers built from the
old script may have registered seeded database/photos for removal; take a full
backup before replacing or uninstalling such installations.
