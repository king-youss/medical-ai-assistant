import resend
import os
from datetime import datetime

resend.api_key = os.environ.get("RESEND_API_KEY")

FROM = "AMI <onboarding@resend.dev>"


def format_date(iso):

    return datetime.fromisoformat(iso).strftime("%d/%m/%Y à %H:%M")


def send_confirmation_email(email, name, start, duration, type_, reason):

    resend.Emails.send({

        "from": FROM,

        "to": [email],

        "subject": "Confirmation rendez-vous",

        "html": f"""
        <h2>Rendez-vous confirmé</h2>

        Bonjour <b>{name}</b><br><br>

        Votre rendez-vous est confirmé :

        <ul>
        <li>Date : {format_date(start)}</li>
        <li>Durée : {duration} min</li>
        <li>Type : {type_}</li>
        <li>Motif : {reason}</li>
        </ul>

        AMI — Assistant Médical
        """

    })


def send_cancellation_email(email, name, start):

    resend.Emails.send({

        "from": FROM,

        "to": [email],

        "subject": "Annulation rendez-vous",

        "html": f"""

        Bonjour {name}<br><br>

        Votre rendez-vous du {format_date(start)} a été annulé.

        """

    })


def send_reschedule_email(email, name, old, new, duration):

    resend.Emails.send({

        "from": FROM,

        "to": [email],

        "subject": "Rendez-vous déplacé",

        "html": f"""

        Bonjour {name}<br><br>

        Ancien rendez-vous : {format_date(old)}<br>

        Nouveau rendez-vous : {format_date(new)}

        """

    })