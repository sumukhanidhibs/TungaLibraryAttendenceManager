"""Opt-in release smoke test. Never opens or modifies the user's database."""
import json
import os
import sys
import tempfile
import traceback
from contextlib import closing
from datetime import date
from pathlib import Path

from utils.resource_utils import data_path, get_base_path, resource_path


def run_smoke_test(result_path):
    result_path = Path(result_path).resolve()
    result = {"passed": False, "frozen": bool(getattr(sys, "frozen", False)), "checks": []}

    def check(condition, description):
        if not condition:
            raise AssertionError(description)
        result["checks"].append(description)

    old_cwd = Path.cwd()
    try:
        # Exercise real Qt DLLs and plugins, with no scanner or dashboard startup.
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QFontDatabase, QPixmap
        from PySide6.QtCharts import QChart
        from openpyxl import load_workbook
        from reportlab.pdfgen.canvas import Canvas
        from models import database
        from models.student_repo import import_students_from_csv, get_student_basic_info
        from services import daily_report_service, monthly_report_service, student_report_service

        app = QApplication.instance() or QApplication(["TungaLibrary release checks"])
        check(not QPixmap(resource_path("assets/logo.png")).isNull(), "Bundled logo loads")
        check(not QPixmap(resource_path("assets/default_avatar.png")).isNull(), "Default avatar loads")
        check(Path(resource_path("themes/light.qss")).read_text(encoding="utf-8") != "", "Theme loads")
        check(QFontDatabase.addApplicationFont(resource_path("assets/fonts/Inter/Inter.ttf")) >= 0,
              "Inter font loads")
        chart = QChart()
        check(chart is not None, "Qt Charts loads")

        with tempfile.TemporaryDirectory(prefix="tunga-release-") as tmp:
            tmp = Path(tmp)
            os.chdir(tmp)
            check(Path(data_path("data/attendance.db")) == get_base_path() / "data/attendance.db",
                  "User-data path is independent of working directory")
            check(Path(resource_path("assets/logo.ico")).is_file(), "Bundled ICO resolves from another directory")
            if result["frozen"]:
                check(get_base_path() == Path(sys.executable).parent, "Frozen user data is beside executable")
                check(Path(resource_path("assets/logo.ico")).parent.parent == Path(sys._MEIPASS),
                      "Frozen resources resolve inside bundle")

            # All writes are redirected to temporary fixtures, never live attendance.
            original_db = database.DB_PATH
            services = [daily_report_service, monthly_report_service, student_report_service]
            original_reports = [service.REPORT_DIR for service in services]
            try:
                database.DB_PATH = tmp / "data" / "attendance.db"
                for service, name in zip(services, ("daily", "monthly", "student")):
                    service.REPORT_DIR = tmp / "reports" / name
                database.init_db()
                with closing(database.get_connection()) as conn:
                    count = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
                check(count == 0, "Fresh database starts empty")
                csv = tmp / "students.csv"
                csv.write_text("studentid,name,class\nS-TEST,Release Test Student,I BCA\n", encoding="utf-8")
                check(import_students_from_csv(str(csv)) == 1, "CSV import succeeds")
                with closing(database.get_connection()) as conn:
                    conn.execute("INSERT INTO sessions(student_id,start_at,end_at,duration_sec) VALUES(?,?,?,?)",
                                 ("S-TEST", "2026-01-15 12:00:00", "2026-01-15 13:00:00", 3600))
                database.init_db()
                check(get_student_basic_info("S-TEST")["name"] == "Release Test Student",
                      "Reinitialisation preserves existing students")
                paths = [daily_report_service.export_daily_report(date(2026, 1, 15)),
                         monthly_report_service.export_monthly_report(2026, 1),
                         student_report_service.export_student_report("S-TEST")]
                for path in paths:
                    wb = load_workbook(path, read_only=True)
                    values = [value for ws in wb for row in ws.values for value in row]
                    check("S-TEST" in values, Path(path).name + " contains test student")
                    wb.close()
                pdf = tmp / "reports" / "student" / "smoke.pdf"
                canvas = Canvas(str(pdf))
                canvas.drawString(72, 720, "TungaLibrary release smoke test")
                canvas.save()
                check(pdf.read_bytes().startswith(b"%PDF-"), "ReportLab generates a PDF")
            finally:
                database.DB_PATH = original_db
                for service, report_dir in zip(services, original_reports):
                    service.REPORT_DIR = report_dir
        result["passed"] = True
    except Exception:
        result["error"] = traceback.format_exc()
    finally:
        os.chdir(old_cwd)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0 if result["passed"] else 1
