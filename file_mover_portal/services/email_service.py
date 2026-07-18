from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from io import BytesIO
from pathlib import Path


class EmailDeliveryError(Exception):
    pass


class EmailService:
    def __init__(self, config) -> None:
        self.enabled = config["MAIL_ENABLED"]
        self.app_name = config["APP_NAME"]
        self.host = config["SMTP_HOST"]
        self.port = config["SMTP_PORT"]
        self.username = config["SMTP_USERNAME"]
        self.password = config["SMTP_PASSWORD"]
        self.from_address = config["MAIL_FROM_ADDRESS"]
        self.from_name = config["MAIL_FROM_NAME"]
        self.use_starttls = config["SMTP_USE_STARTTLS"]
        self.use_ssl = config["SMTP_USE_SSL"]
        self.timeout = config["SMTP_TIMEOUT_SECONDS"]
        self.ca_cert_file = config["SMTP_CA_CERT_FILE"] or None

        if self.enabled:
            if not self.host or not self.from_address:
                raise RuntimeError("SMTP_HOST and MAIL_FROM_ADDRESS are required when MAIL_ENABLED=true")
            if self.use_ssl and self.use_starttls:
                raise RuntimeError("Use either SMTP SSL or STARTTLS, not both")
            if not self.use_ssl and not self.use_starttls:
                raise RuntimeError("SMTP transport encryption is required")
            if self.username and not self.password:
                raise RuntimeError("SMTP_PASSWORD is required when SMTP_USERNAME is set")
            if not self._valid_recipient(self.from_address):
                raise RuntimeError("MAIL_FROM_ADDRESS must be a valid email address")

    def _ssl_context(self) -> ssl.SSLContext:
        context = ssl.create_default_context(cafile=self.ca_cert_file)
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        return context

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
            if self.use_ssl:
                with smtplib.SMTP_SSL(
                    self.host,
                    self.port,
                    timeout=self.timeout,
                    context=self._ssl_context(),
                ) as smtp:
                    if self.username:
                        smtp.login(self.username, self.password)
                    smtp.send_message(message)
            else:
                with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as smtp:
                    smtp.ehlo()
                    if self.use_starttls:
                        smtp.starttls(context=self._ssl_context())
                        smtp.ehlo()
                    if self.username:
                        smtp.login(self.username, self.password)
                    smtp.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            raise EmailDeliveryError("SMTP delivery failed") from exc
