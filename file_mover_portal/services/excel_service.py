from __future__ import annotations

from io import BytesIO
from typing import Iterable, Mapping

import xlsxwriter


class ExcelExportService:
    """Create safe, in-memory XLSX exports of audit history."""

    def __init__(self, app_name: str = "File Mover Portal") -> None:
        self.app_name = str(app_name).strip() or "File Mover Portal"

    HEADERS = ("Timestamp (UTC)", "User", "Action", "Details", "Client IP")
    KEYS = ("timestamp", "username", "action", "details", "remote_addr")

    @staticmethod
    def _safe_excel_text(value: object, maximum: int = 32767) -> str:
        """Prevent spreadsheet-formula injection and Excel cell overflows."""
        text = str(value or "").replace("\x00", "").replace("\r", " ").replace("\n", " ")
        text = text[:maximum]
        if text.lstrip().startswith(("=", "+", "-", "@")):
            text = "'" + text
        return text

    def build_audit_workbook(self, entries: Iterable[Mapping[str, object]]) -> BytesIO:
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True, "strings_to_formulas": False, "strings_to_urls": False})
        worksheet = workbook.add_worksheet("Audit History")

        title_format = workbook.add_format({
            "bold": True,
            "font_size": 16,
            "font_color": "#FFFFFF",
            "bg_color": "#17365D",
            "align": "left",
            "valign": "vcenter",
        })
        header_format = workbook.add_format({
            "bold": True,
            "font_color": "#FFFFFF",
            "bg_color": "#1769AA",
            "border": 1,
            "align": "left",
            "valign": "vcenter",
        })
        cell_format = workbook.add_format({"border": 1, "valign": "top"})
        wrapped_format = workbook.add_format({"border": 1, "valign": "top", "text_wrap": True})

        worksheet.merge_range("A1:E1", f"{self.app_name} - Audit History", title_format)
        worksheet.set_row(0, 26)
        worksheet.write_row(2, 0, self.HEADERS, header_format)

        row_index = 3
        for entry in entries:
            values = [self._safe_excel_text(entry.get(key, "")) for key in self.KEYS]
            for column_index, value in enumerate(values):
                fmt = wrapped_format if column_index == 3 else cell_format
                worksheet.write_string(row_index, column_index, value, fmt)
            row_index += 1

        last_row = max(row_index - 1, 3)
        worksheet.autofilter(2, 0, last_row, len(self.HEADERS) - 1)
        worksheet.freeze_panes(3, 0)
        worksheet.set_column("A:A", 29)
        worksheet.set_column("B:B", 22)
        worksheet.set_column("C:C", 20)
        worksheet.set_column("D:D", 65)
        worksheet.set_column("E:E", 18)
        worksheet.set_landscape()
        worksheet.fit_to_pages(1, 0)
        worksheet.repeat_rows(0, 2)

        workbook.close()
        output.seek(0)
        return output

    def build_move_report_workbook(
        self,
        *,
        batch_id: str,
        username: str,
        recipient: str,
        started_at: str,
        completed_at: str,
        source_directory: str,
        destination_directory: str,
        results: Iterable[Mapping[str, object]],
    ) -> BytesIO:
        """Create a safe file-level report for one move request."""
        result_rows = list(results)
        output = BytesIO()
        workbook = xlsxwriter.Workbook(
            output,
            {"in_memory": True, "strings_to_formulas": False, "strings_to_urls": False},
        )
        summary = workbook.add_worksheet("Summary")
        details = workbook.add_worksheet("File Results")

        title = workbook.add_format({
            "bold": True, "font_size": 16, "font_color": "#FFFFFF",
            "bg_color": "#17365D", "valign": "vcenter",
        })
        label = workbook.add_format({"bold": True, "bg_color": "#DCE6F1", "border": 1})
        value = workbook.add_format({"border": 1, "text_wrap": True})
        header = workbook.add_format({
            "bold": True, "font_color": "#FFFFFF", "bg_color": "#1769AA", "border": 1,
        })
        cell = workbook.add_format({"border": 1, "valign": "top"})
        wrapped = workbook.add_format({"border": 1, "valign": "top", "text_wrap": True})

        moved_count = sum(1 for row in result_rows if row.get("status") == "MOVED")
        failed_count = len(result_rows) - moved_count
        overall_status = "SUCCESS" if failed_count == 0 else ("FAILED" if moved_count == 0 else "PARTIAL_SUCCESS")

        summary.merge_range("A1:D1", f"{self.app_name} - Move Report", title)
        summary.set_row(0, 26)
        summary_rows = [
            ("Batch ID", batch_id),
            ("User", username),
            ("Email recipient", recipient),
            ("Started (UTC)", started_at),
            ("Completed (UTC)", completed_at),
            ("Overall status", overall_status),
            ("Requested", len(result_rows)),
            ("Moved", moved_count),
            ("Failed", failed_count),
            ("Source directory", source_directory),
            ("Destination directory", destination_directory),
        ]
        for row_index, (name, data) in enumerate(summary_rows, start=2):
            summary.write_string(row_index, 0, name, label)
            summary.write_string(row_index, 1, self._safe_excel_text(data), value)
        summary.set_column("A:A", 24)
        summary.set_column("B:B", 75)

        detail_headers = ("File name", "Status", "Message")
        details.write_row(0, 0, detail_headers, header)
        for row_index, row in enumerate(result_rows, start=1):
            details.write_string(row_index, 0, self._safe_excel_text(row.get("filename", "")), cell)
            details.write_string(row_index, 1, self._safe_excel_text(row.get("status", "")), cell)
            details.write_string(row_index, 2, self._safe_excel_text(row.get("message", "")), wrapped)
        last_row = max(len(result_rows), 1)
        details.autofilter(0, 0, last_row, 2)
        details.freeze_panes(1, 0)
        details.set_column("A:A", 55)
        details.set_column("B:B", 20)
        details.set_column("C:C", 70)

        workbook.close()
        output.seek(0)
        return output
