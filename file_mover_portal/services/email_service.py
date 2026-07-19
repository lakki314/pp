from __future__ import annotations

import smtplib
from email.message import EmailMessage
from io import BytesIO


class EmailDeliveryError(Exception):
    pass


class EmailService:
    def __init__(self, config) -> None:
        self.enabled = config["MAIL_ENABLED"]
        self.app_name = config["APP_NAME"]
        self.host = config["SMTP_HOST"]
        self.port = config["SMTP_PORT"]
        self.from_address = config["MAIL_FROM_ADDRESS"]
        self.from_name = config["MAIL_FROM_NAME"]
        self.timeout = config["SMTP_TIMEOUT_SECONDS"]

        if self.enabled:
            if not self.host or not self.from_address:
                raise RuntimeError("SMTP_HOST and MAIL_FROM_ADDRESS are required when MAIL_ENABLED=true")
            if not self._valid_recipient(self.from_address):
                raise RuntimeError("MAIL_FROM_ADDRESS must be a valid email address")

    @staticmethod
    def _valid_recipient(address: str) -> bool:
        if not address or len(address) > 254 or "\r" in address or "\n" in address:
            return False
        local, separator, domain = address.rpartition("@")
        return bool(separator and local and domain and "." in domain)

    def send_move_report(
        self,
        *,
        recipient: str,
        username: str,
        batch_id: str,
        moved_count: int,
        failed_count: int,
        workbook: BytesIO,
    ) -> None:
        if not self.enabled:
            return
        if not self._valid_recipient(recipient):
            raise EmailDeliveryError("A valid recipient email address is unavailable")

        status = "Completed" if failed_count == 0 else "Completed with failures"
        message = EmailMessage()
        message["Subject"] = f"{self.app_name} - File move report - {batch_id} - {status}"
        message["From"] = f"{self.from_name} <{self.from_address}>" if self.from_name else self.from_address
        message["To"] = recipient
        message.set_content(
            f"Your {self.app_name} file move request has completed.\n\n"
            f"Batch ID: {batch_id}\n"
            f"User: {username}\n"
            f"Moved successfully: {moved_count}\n"
            f"Failed: {failed_count}\n\n"
            "The attached Excel workbook contains the file-level results."
        )

        workbook.seek(0)
        message.add_attachment(
            workbook.read(),
            maintype="application",
            subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"file_move_report_{batch_id}.xlsx",
        )

        try:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as smtp:
                smtp.ehlo()
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            raise EmailDeliveryError("SMTP delivery failed") from exc
