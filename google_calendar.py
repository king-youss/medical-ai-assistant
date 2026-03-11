from datetime import datetime, timedelta, time
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]

CALENDAR_ID = "fedbd0eb47f0a048eded0c31e41dcb5ff56533d844a542c6abe3ec26057994ae@group.calendar.google.com"
DOCTOR_EMAIL = "ami.cabinet.medical.demo@gmail.com"
TIMEZONE = "Europe/Paris"

DAY_NAMES_FR = {
    0: "Lundi",
    1: "Mardi",
    2: "Mercredi",
    3: "Jeudi",
    4: "Vendredi",
    5: "Samedi",
    6: "Dimanche",
}


def get_calendar_service():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def create_google_event(patient_name, start_time, duration, reason, event_type):
    service = get_calendar_service()

    start_dt = datetime.fromisoformat(start_time)
    end_dt = start_dt + timedelta(minutes=duration)

    event = {
        "summary": f"Consultation - {patient_name}",
        "description": f"Type: {event_type}\nMotif: {reason}",
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": TIMEZONE,
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": TIMEZONE,
        },
        "attendees": [
            {"email": DOCTOR_EMAIL}
        ],
    }

    created_event = service.events().insert(
        calendarId=CALENDAR_ID,
        body=event,
        sendUpdates="all"
    ).execute()

    return {
        "event_id": created_event.get("id"),
        "calendar_id": CALENDAR_ID,
        "summary": created_event.get("summary"),
    }


def delete_google_event(event_id):
    service = get_calendar_service()
    service.events().delete(
        calendarId=CALENDAR_ID,
        eventId=event_id,
        sendUpdates="all"
    ).execute()


def move_google_event(event_id, new_start_time, duration, patient_name, reason, event_type):
    service = get_calendar_service()

    start_dt = datetime.fromisoformat(new_start_time)
    end_dt = start_dt + timedelta(minutes=duration)

    event = service.events().get(
        calendarId=CALENDAR_ID,
        eventId=event_id
    ).execute()

    event["summary"] = f"Consultation - {patient_name}"
    event["description"] = f"Type: {event_type}\nMotif: {reason}"
    event["start"] = {
        "dateTime": start_dt.isoformat(),
        "timeZone": TIMEZONE,
    }
    event["end"] = {
        "dateTime": end_dt.isoformat(),
        "timeZone": TIMEZONE,
    }

    updated_event = service.events().update(
        calendarId=CALENDAR_ID,
        eventId=event_id,
        body=event,
        sendUpdates="all"
    ).execute()

    return {
        "event_id": updated_event.get("id"),
        "calendar_id": CALENDAR_ID,
        "summary": updated_event.get("summary"),
    }


def get_doctor_busy_slots_for_day(target_date):
    service = get_calendar_service()

    day_start = datetime.combine(target_date, time(9, 0))
    day_end = datetime.combine(target_date, time(17, 0))

    result = service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=day_start.isoformat() + "+01:00",
        timeMax=day_end.isoformat() + "+01:00",
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    items = result.get("items", [])
    busy_slots = []

    for item in items:
        start_raw = item.get("start", {}).get("dateTime")
        end_raw = item.get("end", {}).get("dateTime")

        if start_raw and end_raw:
            start_dt = datetime.fromisoformat(
                start_raw.replace("Z", "+00:00")
            ).replace(tzinfo=None)
            end_dt = datetime.fromisoformat(
                end_raw.replace("Z", "+00:00")
            ).replace(tzinfo=None)
            busy_slots.append((start_dt, end_dt))

    return busy_slots


def build_google_available_slots_for_day(duration, target_date):
    work_start = datetime.combine(target_date, time(9, 0))
    work_end = datetime.combine(target_date, time(17, 0))

    busy_slots = get_doctor_busy_slots_for_day(target_date)

    slots = []
    current = work_start

    while current + timedelta(minutes=duration) <= work_end:
        slot_end = current + timedelta(minutes=duration)
        is_free = True

        for busy_start, busy_end in busy_slots:
            if current < busy_end and busy_start < slot_end:
                is_free = False
                break

        if is_free:
            slots.append({
                "iso": current.isoformat(),
                "label": current.strftime("%H:%M"),
                "date_label": f"{DAY_NAMES_FR[target_date.weekday()]} {current.strftime('%d/%m')}",
                "date_iso": target_date.isoformat(),
            })

        current += timedelta(minutes=15)

    return slots


def build_google_available_slots_week(duration, days_ahead=14):
    today = datetime.now().date()
    all_slots = []

    for offset in range(days_ahead):
        current_date = today + timedelta(days=offset)

        if current_date.weekday() <= 4:
            day_slots = build_google_available_slots_for_day(duration, current_date)
            all_slots.extend(day_slots)

    return all_slots


def build_available_days(duration, days_ahead=14):
    slots = build_google_available_slots_week(duration, days_ahead)
    days = {}

    for slot in slots:
        key = slot["date_iso"]
        if key not in days:
            days[key] = {
                "date_iso": key,
                "label": slot["date_label"],
                "count": 0
            }
        days[key]["count"] += 1

    return list(days.values())