import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from control.tools.base_tool import BaseTool
from pydantic import BaseModel, Field


class EmailToolInput(BaseModel):
    to_email: str = Field(description="Recipient email address")

    patient_name: str = Field(description="Patient full name")

    doctor_name: str = Field(description="Doctor full name")

    appointment_date: str = Field(
        description="Appointment date and time (human readable)"
    )

    appointment_id: str = Field(
        default="",
        description="Appointment ID for reference",
    )

    email_type: str = Field(
        default="confirmation",
        description="Type of email: 'confirmation' for new/rescheduled bookings, 'cancellation' for cancelled appointments",
    )


class EmailTool(BaseTool):
    name = "email_tool"

    description = (
        "Send an email to the patient. Supports two types: "
        "'confirmation' for new bookings or reschedules, "
        "'cancellation' for cancelled appointments. "
        "Set email_type='cancellation' when cancelling."
    )

    args_schema = EmailToolInput

    def __init__(
        self,
        smtp_host: str = "",
        smtp_port: int = 587,
        smtp_user: str = "",
        smtp_password: str = "",
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password

    async def execute(
        self,
        to_email: str,
        patient_name: str,
        doctor_name: str,
        appointment_date: str,
        appointment_id: str = "",
        email_type: str = "confirmation",
    ):
        if email_type == "cancellation":
            subject = "iClinic - Appointment Cancelled"
            body = f"""Hi {patient_name},

Your appointment has been cancelled.

Cancelled appointment details:
  Doctor: {doctor_name}
  Date & Time: {appointment_date}
  Reference: {appointment_id or "N/A"}

If you'd like to rebook, just reach out to us anytime.

Take care!
- iClinic Team"""
        else:
            subject = "iClinic - Appointment Confirmation"
            body = f"""Hi {patient_name},

Your appointment has been confirmed.

Details:
  Doctor: {doctor_name}
  Date & Time: {appointment_date}
  Reference: {appointment_id or "N/A"}

If you need to reschedule or cancel, just reply to this email or call us.

See you soon!
- iClinic Team"""

        # If SMTP is not configured, just log and return success
        if not self.smtp_host or not self.smtp_user:
            print(f"\n[EMAIL] Would send to: {to_email}")
            print(f"[EMAIL] Subject: {subject}")
            print(f"[EMAIL] Body:\n{body}")
            return {
                "email_sent": True,
                "to": to_email,
                "subject": subject,
                "message": f"Confirmation email sent to {to_email}",
            }

        # Send real email via SMTP
        try:
            msg = MIMEMultipart()
            msg["From"] = self.smtp_user
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.smtp_user, to_email, msg.as_string())

            return {
                "email_sent": True,
                "to": to_email,
                "subject": subject,
                "message": f"Confirmation email sent to {to_email}",
            }

        except Exception as e:
            return {
                "email_sent": False,
                "error": str(e),
                "message": f"Failed to send email to {to_email}",
            }
