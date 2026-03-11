import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SENDER_NAME = "AMI — Assistant Médical"


def _analysis_instructions_html(appt_type: str) -> str:
    if "Analyse" not in appt_type:
        return ""
    return """
        <div style="margin-top: 16px; padding: 12px; background: #FEF3C7; border: 1px solid #F59E0B; border-radius: 8px;">
            <strong>Consignes de préparation pour vos analyses :</strong>
            <ul style="margin: 8px 0;">
                <li>Présentez-vous <strong>à jeun</strong> depuis au moins 12 heures (eau autorisée).</li>
                <li>Évitez l'alcool et le tabac 24h avant le prélèvement.</li>
                <li>Apportez votre <strong>carte Vitale</strong> et votre <strong>ordonnance</strong>.</li>
                <li>Si vous prenez un traitement, ne l'arrêtez pas sauf avis médical.</li>
            </ul>
            <strong>Laboratoires à proximité :</strong>
            <ul style="margin: 8px 0;">
                <li>Laboratoire BioMédical Centre — 12 rue de la Santé</li>
                <li>Labo Analyse Plus — 45 avenue Pasteur</li>
                <li>Centre de Biologie Médicale — 8 place de la République</li>
            </ul>
            <em>Vous pouvez effectuer vos analyses dans le laboratoire de votre choix.</em>
        </div>
    """


def _format_datetime(iso_str: str) -> str:
    dt = datetime.fromisoformat(iso_str)
    return dt.strftime("%d/%m/%Y à %H:%M")


def _send_email(to_email: str, subject: str, html_body: str):
    if not SMTP_USER or not SMTP_PASSWORD:
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{SENDER_NAME} <{SMTP_USER}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, to_email, msg.as_string())

    return True


def send_confirmation_email(to_email: str, patient_name: str, start_time: str,
                            duration: int, appt_type: str, reason: str) -> bool:
    date_str = _format_datetime(start_time)
    subject = f"Confirmation de votre rendez-vous — {date_str}"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;">
        <h2 style="color: #166534;">Rendez-vous confirmé</h2>
        <p>Bonjour <strong>{patient_name}</strong>,</p>
        <p>Votre rendez-vous a bien été enregistré :</p>
        <table style="border-collapse: collapse; width: 100%;">
            <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Date</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{date_str}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Durée</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{duration} minutes</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Type</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{appt_type}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Motif</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{reason}</td></tr>
        </table>
        {_analysis_instructions_html(appt_type)}
        <p style="margin-top: 16px;">À bientôt,<br><em>AMI — Assistant Médical</em></p>
    </div>
    """
    return _send_email(to_email, subject, html)


def send_cancellation_email(to_email: str, patient_name: str, start_time: str) -> bool:
    date_str = _format_datetime(start_time)
    subject = f"Annulation de votre rendez-vous — {date_str}"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;">
        <h2 style="color: #7F1D1D;">Rendez-vous annulé</h2>
        <p>Bonjour <strong>{patient_name}</strong>,</p>
        <p>Votre rendez-vous prévu le <strong>{date_str}</strong> a été annulé.</p>
        <p>Si vous souhaitez reprendre un rendez-vous, n'hésitez pas à revenir sur AMI.</p>
        <p>Cordialement,<br><em>AMI — Assistant Médical</em></p>
    </div>
    """
    return _send_email(to_email, subject, html)


def send_reschedule_email(to_email: str, patient_name: str,
                          old_start_time: str, new_start_time: str,
                          duration: int) -> bool:
    old_date = _format_datetime(old_start_time)
    new_date = _format_datetime(new_start_time)
    subject = f"Déplacement de votre rendez-vous — {new_date}"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;">
        <h2 style="color: #1D4ED8;">Rendez-vous déplacé</h2>
        <p>Bonjour <strong>{patient_name}</strong>,</p>
        <p>Votre rendez-vous initialement prévu le <strong>{old_date}</strong>
           a été déplacé.</p>
        <p><strong>Nouveau créneau :</strong> {new_date} ({duration} minutes)</p>
        <p>À bientôt,<br><em>AMI — Assistant Médical</em></p>
    </div>
    """
    return _send_email(to_email, subject, html)
