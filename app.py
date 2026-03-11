import streamlit as st
import sqlite3
import time as pytime
from datetime import datetime

from triage_engine import triage_request, extract_name, looks_like_symptom_message
from google_calendar import (
    create_google_event,
    delete_google_event,
    move_google_event,
    build_google_available_slots_week,
    build_available_days
)
import database
from email_service import send_confirmation_email, send_cancellation_email, send_reschedule_email


# -------------------------------------------------
# CONFIG
# -------------------------------------------------
st.set_page_config(
    page_title="AMI",
    page_icon="💬",
    layout="centered",
    initial_sidebar_state="collapsed"
)

database.init_db()


# -------------------------------------------------
# STYLE
# -------------------------------------------------
st.markdown("""
<style>
.stApp {
    background: #1F1F1F;
    color: #F3F4F6;
}

header, #MainMenu, footer {
    visibility: hidden;
}

.block-container {
    max-width: 920px;
    padding-top: 2rem;
    padding-bottom: 2rem;
}

.app-title {
    text-align: center;
    font-size: 3.4rem;
    font-weight: 800;
    color: #4ADE80;
    letter-spacing: 1px;
    margin-bottom: 0.15rem;
}

.app-subtitle {
    text-align: center;
    color: #9CA3AF;
    font-size: 1rem;
    margin-bottom: 2rem;
}

.notice {
    border-radius: 14px;
    padding: 14px 16px;
    margin: 14px 0;
    border: 1px solid #374151;
    background: #262626;
    color: #F3F4F6;
}

.notice-danger {
    background: #3A1F1F;
    border-color: #7F1D1D;
    color: #FECACA;
}

.notice-success {
    background: #1E3A2A;
    border-color: #166534;
    color: #BBF7D0;
}

.notice-info {
    background: #1F2937;
    border-color: #1D4ED8;
    color: #BFDBFE;
}

.section-title {
    text-align: center;
    color: #F3F4F6;
    font-weight: 700;
    font-size: 1.08rem;
    margin-top: 1.2rem;
    margin-bottom: 0.5rem;
}

.section-subtitle {
    text-align: center;
    color: #9CA3AF;
    margin-bottom: 1rem;
}

.period-title {
    color: #D1D5DB;
    font-weight: 700;
    margin-top: 1rem;
    margin-bottom: 0.75rem;
    text-align: center;
}

.day-block {
    margin-bottom: 12px;
}

.day-block div[data-testid="stButton"] {
    width: 100% !important;
}

.day-block div[data-testid="stButton"] > button {
    width: 100% !important;
    min-height: 104px !important;
    height: 104px !important;
    max-height: 104px !important;
    border-radius: 16px !important;
    background: #262626 !important;
    border: 1px solid #3F3F46 !important;
    color: #F3F4F6 !important;
    font-size: 0.95rem !important;
    font-weight: 700 !important;
    line-height: 1.25 !important;
    padding: 10px 12px !important;
    margin: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    text-align: center !important;
    white-space: pre-line !important;
    overflow: hidden !important;
}

.day-block div[data-testid="stButton"] > button:hover {
    background: #2F2F2F !important;
    border-color: #52525B !important;
}

.stButton > button {
    width: 100%;
    background: #2C2C2C;
    border: 1px solid #3F3F46;
    border-radius: 14px;
    color: white;
    padding: 10px;
    font-weight: 600;
}

.stButton > button:hover {
    background: #3F3F46;
    color: white;
}

[data-testid="stChatInput"] {
    position: sticky;
    bottom: 18px;
    background: transparent !important;
    max-width: 760px;
    margin: 0 auto;
    padding: 6px 0;
}

[data-testid="stChatInput"] > div {
    background: #262626 !important;
    border: 1px solid #3F3F46 !important;
    border-radius: 24px !important;
    padding: 8px 12px !important;
    box-shadow: 0 12px 30px rgba(0,0,0,0.25) !important;
}

[data-testid="stChatInput"] textarea,
[data-testid="stChatInput"] input {
    background: transparent !important;
    color: #F5F5F5 !important;
    border: none !important;
    font-size: 16px !important;
    min-height: 30px !important;
    box-shadow: none !important;
}

[data-testid="stChatInput"] textarea::placeholder,
[data-testid="stChatInput"] input::placeholder {
    color: #A3A3A3 !important;
    opacity: 1 !important;
}

[data-testid="stChatInput"] textarea:focus,
[data-testid="stChatInput"] input:focus {
    outline: none !important;
    box-shadow: none !important;
}

[data-testid="stChatInput"] button {
    background: #3A3A3A !important;
    color: white !important;
    border: 1px solid #4B4B4B !important;
    border-radius: 14px !important;
    width: 40px !important;
    height: 40px !important;
    min-width: 40px !important;
}

[data-testid="stChatInput"] button:hover {
    background: #4A4A4A !important;
}
</style>
""", unsafe_allow_html=True)


# -------------------------------------------------
# DATABASE
# -------------------------------------------------
def save_appointment(patient_name, start_time, duration, reason, appt_type):
    conn = sqlite3.connect(database.DB_PATH)
    cursor = conn.cursor()

    cursor.execute("INSERT INTO patients (name) VALUES (?)", (patient_name,))
    patient_id = cursor.lastrowid

    cursor.execute(
        """
        INSERT INTO appointments (patient_id, start_time, duration, reason, type)
        VALUES (?, ?, ?, ?, ?)
        """,
        (patient_id, start_time, duration, reason, appt_type)
    )

    conn.commit()
    conn.close()


def delete_local_appointment(start_time):
    conn = sqlite3.connect(database.DB_PATH)
    conn.execute("DELETE FROM appointments WHERE start_time = ?", (start_time,))
    conn.commit()
    conn.close()


def update_local_appointment(old_start_time, new_start_time, duration):
    conn = sqlite3.connect(database.DB_PATH)
    conn.execute(
        "UPDATE appointments SET start_time = ?, duration = ? WHERE start_time = ?",
        (new_start_time, duration, old_start_time)
    )
    conn.commit()
    conn.close()


# -------------------------------------------------
# UTILS
# -------------------------------------------------
def format_slot(slot_iso):
    return datetime.fromisoformat(slot_iso).strftime("%d/%m/%Y à %H:%M")


def slot_still_available(selected_slot, duration):
    latest_slots = build_google_available_slots_week(duration)
    return any(s["iso"] == selected_slot for s in latest_slots)


def split_slots_by_period(slots):
    morning = []
    afternoon = []

    for slot in slots:
        dt = datetime.fromisoformat(slot["iso"])
        if dt.hour < 12:
            morning.append(slot)
        else:
            afternoon.append(slot)

    return morning, afternoon


def render_slot_grid(slots, key_prefix):
    cols_per_row = 4

    for i in range(0, len(slots), cols_per_row):
        row = slots[i:i + cols_per_row]
        cols = st.columns(cols_per_row)

        for j, slot in enumerate(row):
            with cols[j]:
                if st.button(slot["label"], key=f"{key_prefix}_{slot['iso']}"):
                    return slot
    return None


def prepare_slots_for_booking(duration, reason, appt_type):
    all_slots = build_google_available_slots_week(duration)
    available_days = build_available_days(duration)

    st.session_state.all_pending_slots = all_slots
    st.session_state.available_days = available_days
    st.session_state.pending_slots = []
    st.session_state.pending_duration = duration
    st.session_state.pending_type = appt_type
    st.session_state.pending_reason = reason
    st.session_state.selected_day = None
    st.session_state.selected_slot = None
    st.session_state.flow_state = "choose_day"


def run_triage_flow(symptom_message: str):
    category, description, chat_message, score, source = triage_request(symptom_message)

    database.log_triage(symptom_message, category, description, score, source)

    if category == "URGENCY":
        st.session_state.messages.append({
            "role": "assistant",
            "content": chat_message
        })
        st.session_state.banner_message = (
            f"{description}<br>Veuillez appeler le 15 ou vous rendre immédiatement aux urgences."
        )
        st.session_state.banner_type = "danger"
        st.session_state.flow_state = "ready"
        st.session_state.pending_slots = []
        st.session_state.available_days = []
        st.session_state.selected_day = None
        st.session_state.selected_slot = None
        return

    duration = 20 if category == "ANALYSIS_NEEDED" else 15
    appt_type = "Complexe (Analyses)" if category == "ANALYSIS_NEEDED" else "Standard"

    prepare_slots_for_booking(duration, symptom_message, appt_type)

    if st.session_state.available_days:
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"{chat_message} Choisissez d’abord un jour, puis un créneau."
        })
        if category == "ANALYSIS_NEEDED":
            consignes = (
                "\n\n**Consignes de préparation pour vos analyses :**\n"
                "- Présentez-vous **à jeun** depuis au moins 12 heures (eau autorisée).\n"
                "- Évitez l'alcool et le tabac 24h avant le prélèvement.\n"
                "- Apportez votre **carte Vitale** et votre **ordonnance** si vous en avez une.\n"
                "- Si vous prenez un traitement, ne l'arrêtez pas sauf avis médical.\n"
                "\n**Laboratoires à proximité :**\n"
                "- Laboratoire BioMédical Centre — 12 rue de la Santé\n"
                "- Labo Analyse Plus — 45 avenue Pasteur\n"
                "- Centre de Biologie Médicale — 8 place de la République\n"
                "\n_Vous pouvez effectuer vos analyses dans le laboratoire de votre choix._"
            )
            st.session_state.messages.append({
                "role": "assistant",
                "content": consignes
            })
        st.session_state.banner_message = ""
        st.session_state.banner_type = ""
    else:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "Aucun rendez-vous n’est disponible pour le moment."
        })
        st.session_state.banner_message = "Aucun rendez-vous n’est disponible pour le moment."
        st.session_state.banner_type = "danger"
        st.session_state.flow_state = "ready"


def show_loader(text: str, seconds: float = 1.2):
    with st.spinner(text):
        pytime.sleep(seconds)


# -------------------------------------------------
# STATE
# -------------------------------------------------
defaults = {
    "messages": [],
    "patient_name": "",
    "pending_slots": [],
    "all_pending_slots": [],
    "available_days": [],
    "pending_duration": None,
    "pending_type": None,
    "pending_reason": "",
    "selected_day": None,
    "selected_slot": None,
    "flow_state": "ask_name",
    "banner_message": "",
    "banner_type": "",
    "waiting_name_for_symptoms": False,
    "buffered_symptom_message": "",
    "confirmed_event_id": None,
    "confirmed_start_time": None,
    "pending_user_message": None,
    "pending_processing": False,
    "patient_email": ""
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = [] if isinstance(value, list) else value

if not st.session_state.messages:
    st.session_state.messages.append({
        "role": "assistant",
        "content": "Bonjour. Je suis AMI, votre assistant médical. Quel est votre nom ?"
    })


# -------------------------------------------------
# HEADER
# -------------------------------------------------
st.markdown('<div class="app-title">AMI</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="app-subtitle">Votre assistant médical</div>',
    unsafe_allow_html=True
)


# -------------------------------------------------
# CHAT DISPLAY
# -------------------------------------------------
for msg in st.session_state.messages:
    with st.chat_message("user" if msg["role"] == "user" else "assistant"):
        st.write(msg["content"])


# -------------------------------------------------
# BANNER
# -------------------------------------------------
if st.session_state.banner_message:
    extra = ""
    if st.session_state.banner_type == "danger":
        extra = " notice-danger"
    elif st.session_state.banner_type == "success":
        extra = " notice-success"
    elif st.session_state.banner_type == "info":
        extra = " notice-info"

    st.markdown(
        f'<div class="notice{extra}">{st.session_state.banner_message}</div>',
        unsafe_allow_html=True
    )


# -------------------------------------------------
# CHOOSE DAY
# -------------------------------------------------
if st.session_state.flow_state == "choose_day" and st.session_state.available_days:
    st.markdown('<div class="section-title">Choisissez un jour</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Du lundi au vendredi</div>', unsafe_allow_html=True)

    cols_per_row = 3
    days = st.session_state.available_days[:10]

    for i in range(0, len(days), cols_per_row):
        row = days[i:i + cols_per_row]
        cols = st.columns(cols_per_row)

        for j, day in enumerate(row):
            with cols[j]:
                st.markdown('<div class="day-block">', unsafe_allow_html=True)
                label = f"{day['label']}\n{day['count']} dispos"
                if st.button(label, key=f"day_{day['date_iso']}"):
                    st.session_state.selected_day = day["date_iso"]
                    st.session_state.pending_slots = [
                        s for s in st.session_state.all_pending_slots
                        if s["date_iso"] == day["date_iso"]
                    ]
                    st.session_state.messages.append({
                        "role": "user",
                        "content": f"Je choisis le jour {day['label']}"
                    })
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"Très bien. Voici les créneaux disponibles pour {day['label']}."
                    })
                    st.session_state.flow_state = "waiting_slot"
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)


# -------------------------------------------------
# CHOOSE SLOT
# -------------------------------------------------
if st.session_state.flow_state == "waiting_slot" and st.session_state.pending_slots:
    st.markdown('<div class="section-title">Choisissez un créneau</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Sélectionnez l’horaire qui vous convient</div>', unsafe_allow_html=True)

    if st.button("← Changer de jour"):
        st.session_state.selected_day = None
        st.session_state.selected_slot = None
        st.session_state.pending_slots = []
        st.session_state.flow_state = "choose_day"
        st.session_state.messages.append({
            "role": "user",
            "content": "Je veux choisir un autre jour"
        })
        st.session_state.messages.append({
            "role": "assistant",
            "content": "Très bien. Choisissez un autre jour."
        })
        st.rerun()

    morning_slots, afternoon_slots = split_slots_by_period(st.session_state.pending_slots)

    if morning_slots:
        st.markdown('<div class="period-title">Matin</div>', unsafe_allow_html=True)
        chosen = render_slot_grid(morning_slots, "slot_morning")
        if chosen:
            st.session_state.selected_slot = chosen["iso"]
            st.session_state.messages.append({
                "role": "user",
                "content": f"Je choisis le créneau du {format_slot(chosen['iso'])}"
            })
            st.session_state.messages.append({
                "role": "assistant",
                "content": (
                    f"Très bien. Vous avez choisi le créneau du "
                    f"{format_slot(chosen['iso'])}. "
                    f"Vous pouvez maintenant valider le rendez-vous."
                )
            })
            st.session_state.flow_state = "selected"
            st.session_state.banner_message = ""
            st.session_state.banner_type = ""
            st.rerun()

    if afternoon_slots:
        st.markdown('<div class="period-title">Après-midi</div>', unsafe_allow_html=True)
        chosen = render_slot_grid(afternoon_slots, "slot_afternoon")
        if chosen:
            st.session_state.selected_slot = chosen["iso"]
            st.session_state.messages.append({
                "role": "user",
                "content": f"Je choisis le créneau du {format_slot(chosen['iso'])}"
            })
            st.session_state.messages.append({
                "role": "assistant",
                "content": (
                    f"Très bien. Vous avez choisi le créneau du "
                    f"{format_slot(chosen['iso'])}. "
                    f"Vous pouvez maintenant valider le rendez-vous."
                )
            })
            st.session_state.flow_state = "selected"
            st.session_state.banner_message = ""
            st.session_state.banner_type = ""
            st.rerun()


# -------------------------------------------------
# SELECTED SLOT
# -------------------------------------------------
if st.session_state.flow_state == "selected" and st.session_state.selected_slot:
    if st.button("Modifier le rendez-vous"):
        st.session_state.selected_day = None
        st.session_state.selected_slot = None
        st.session_state.pending_slots = []
        st.session_state.flow_state = "choose_day"
        st.session_state.messages.append({
            "role": "user",
            "content": "Je veux modifier mon choix"
        })
        st.session_state.messages.append({
            "role": "assistant",
            "content": "Très bien. Choisissez d’abord un nouveau jour."
        })
        st.rerun()

    if st.button("Valider le rendez-vous"):
        show_loader("Confirmation du rendez-vous...")

        if not slot_still_available(st.session_state.selected_slot, st.session_state.pending_duration):
            st.session_state.banner_message = "Ce créneau n’est plus disponible. Merci d’en choisir un autre."
            st.session_state.banner_type = "danger"
            st.session_state.selected_slot = None
            st.session_state.flow_state = "choose_day"
            st.rerun()

        save_appointment(
            st.session_state.patient_name,
            st.session_state.selected_slot,
            st.session_state.pending_duration,
            st.session_state.pending_reason,
            st.session_state.pending_type
        )

        google_result = create_google_event(
            patient_name=st.session_state.patient_name,
            start_time=st.session_state.selected_slot,
            duration=st.session_state.pending_duration,
            reason=st.session_state.pending_reason,
            event_type=st.session_state.pending_type
        )

        st.session_state.confirmed_event_id = google_result["event_id"]
        st.session_state.confirmed_start_time = st.session_state.selected_slot
        st.session_state.flow_state = "confirmed"
        st.session_state.banner_message = (
            f"Rendez-vous confirmé pour le {format_slot(st.session_state.selected_slot)}."
        )
        st.session_state.banner_type = "success"

        email_sent = False
        if st.session_state.patient_email:
            try:
                email_sent = send_confirmation_email(
                    to_email=st.session_state.patient_email,
                    patient_name=st.session_state.patient_name,
                    start_time=st.session_state.selected_slot,
                    duration=st.session_state.pending_duration,
                    appt_type=st.session_state.pending_type,
                    reason=st.session_state.pending_reason
                )
            except Exception:
                email_sent = False

        confirm_msg = "Votre rendez-vous est confirmé."
        if email_sent:
            confirm_msg += f" Un e-mail de confirmation a été envoyé à {st.session_state.patient_email}."

        st.session_state.messages.append({
            "role": "assistant",
            "content": confirm_msg
        })

        st.rerun()


# -------------------------------------------------
# CONFIRMED ACTIONS
# -------------------------------------------------
if st.session_state.flow_state == "confirmed" and st.session_state.confirmed_event_id:
    action1, action2 = st.columns(2)

    with action1:
        if st.button("Annuler le rendez-vous"):
            show_loader("Annulation du rendez-vous...")
            delete_google_event(st.session_state.confirmed_event_id)

            if st.session_state.confirmed_start_time:
                delete_local_appointment(st.session_state.confirmed_start_time)

            if st.session_state.patient_email and st.session_state.confirmed_start_time:
                try:
                    send_cancellation_email(
                        to_email=st.session_state.patient_email,
                        patient_name=st.session_state.patient_name,
                        start_time=st.session_state.confirmed_start_time
                    )
                except Exception:
                    pass

            st.session_state.messages.append({
                "role": "assistant",
                "content": "Votre rendez-vous a été annulé."
            })
            st.session_state.banner_message = "Rendez-vous annulé."
            st.session_state.banner_type = "info"
            st.session_state.confirmed_event_id = None
            st.session_state.confirmed_start_time = None
            st.session_state.flow_state = "ready"
            st.rerun()

    with action2:
        if st.button("Déplacer le rendez-vous"):
            show_loader("Recherche de nouvelles disponibilités...")
            prepare_slots_for_booking(
                st.session_state.pending_duration,
                st.session_state.pending_reason,
                st.session_state.pending_type
            )
            st.session_state.flow_state = "move_choose_day"
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Très bien. Choisissez un nouveau jour pour déplacer votre rendez-vous."
            })
            st.rerun()


# -------------------------------------------------
# MOVE - CHOOSE DAY
# -------------------------------------------------
if st.session_state.flow_state == "move_choose_day" and st.session_state.available_days:
    st.markdown('<div class="section-title">Choisissez un nouveau jour</div>', unsafe_allow_html=True)

    cols_per_row = 3
    days = st.session_state.available_days[:10]

    for i in range(0, len(days), cols_per_row):
        row = days[i:i + cols_per_row]
        cols = st.columns(cols_per_row)

        for j, day in enumerate(row):
            with cols[j]:
                st.markdown('<div class="day-block">', unsafe_allow_html=True)
                label = f"{day['label']}\n{day['count']} dispos"
                if st.button(label, key=f"move_day_{day['date_iso']}"):
                    st.session_state.selected_day = day["date_iso"]
                    st.session_state.pending_slots = [
                        s for s in st.session_state.all_pending_slots
                        if s["date_iso"] == day["date_iso"]
                    ]
                    st.session_state.flow_state = "move_waiting_slot"
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)


# -------------------------------------------------
# MOVE - CHOOSE SLOT
# -------------------------------------------------
if st.session_state.flow_state == "move_waiting_slot" and st.session_state.pending_slots:
    st.markdown('<div class="section-title">Choisissez un nouveau créneau</div>', unsafe_allow_html=True)

    if st.button("← Changer de jour", key="move_back_to_days"):
        st.session_state.flow_state = "move_choose_day"
        st.session_state.pending_slots = []
        st.rerun()

    move_morning, move_afternoon = split_slots_by_period(st.session_state.pending_slots)

    if move_morning:
        st.markdown('<div class="period-title">Matin</div>', unsafe_allow_html=True)
        chosen = render_slot_grid(move_morning, "move_slot_morning")
        if chosen:
            st.session_state.selected_slot = chosen["iso"]
            st.session_state.flow_state = "move_selected"
            st.rerun()

    if move_afternoon:
        st.markdown('<div class="period-title">Après-midi</div>', unsafe_allow_html=True)
        chosen = render_slot_grid(move_afternoon, "move_slot_afternoon")
        if chosen:
            st.session_state.selected_slot = chosen["iso"]
            st.session_state.flow_state = "move_selected"
            st.rerun()


# -------------------------------------------------
# MOVE - CONFIRM
# -------------------------------------------------
if st.session_state.flow_state == "move_selected" and st.session_state.selected_slot:
    if st.button("Valider le nouveau créneau"):
        show_loader("Déplacement du rendez-vous...")

        if not slot_still_available(st.session_state.selected_slot, st.session_state.pending_duration):
            st.session_state.banner_message = "Ce créneau n’est plus disponible."
            st.session_state.banner_type = "danger"
            st.session_state.flow_state = "move_choose_day"
            st.rerun()

        old_start = st.session_state.confirmed_start_time

        move_google_event(
            event_id=st.session_state.confirmed_event_id,
            new_start_time=st.session_state.selected_slot,
            duration=st.session_state.pending_duration,
            patient_name=st.session_state.patient_name,
            reason=st.session_state.pending_reason,
            event_type=st.session_state.pending_type
        )

        if old_start:
            update_local_appointment(
                old_start_time=old_start,
                new_start_time=st.session_state.selected_slot,
                duration=st.session_state.pending_duration
            )

        if st.session_state.patient_email and old_start:
            try:
                send_reschedule_email(
                    to_email=st.session_state.patient_email,
                    patient_name=st.session_state.patient_name,
                    old_start_time=old_start,
                    new_start_time=st.session_state.selected_slot,
                    duration=st.session_state.pending_duration
                )
            except Exception:
                pass

        st.session_state.confirmed_start_time = st.session_state.selected_slot
        st.session_state.flow_state = "confirmed"
        st.session_state.banner_message = (
            f"Rendez-vous déplacé au {format_slot(st.session_state.selected_slot)}."
        )
        st.session_state.banner_type = "success"
        st.session_state.messages.append({
            "role": "assistant",
            "content": "Votre rendez-vous a été déplacé."
        })
        st.rerun()


# -------------------------------------------------
# CHAT INPUT
# -------------------------------------------------
st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

user_message = st.chat_input("Décrivez vos symptômes ou votre demande")

if user_message:
    st.session_state.messages.append({
        "role": "user",
        "content": user_message
    })
    st.session_state.pending_user_message = user_message
    st.session_state.pending_processing = True
    st.rerun()


# -------------------------------------------------
# HANDLE USER MESSAGE AFTER DISPLAY
# -------------------------------------------------
if st.session_state.pending_processing and st.session_state.pending_user_message:
    user_message = st.session_state.pending_user_message

    show_loader("Traitement de votre demande...")

    st.session_state.pending_processing = False
    st.session_state.pending_user_message = None

    if st.session_state.flow_state == "ask_name":
        if looks_like_symptom_message(user_message):
            st.session_state.buffered_symptom_message = user_message
            st.session_state.waiting_name_for_symptoms = True
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Je n’ai pas encore votre prénom. Pouvez-vous d’abord me dire votre nom ?"
            })
            st.rerun()

        extracted_name = extract_name(user_message)
        st.session_state.patient_name = extracted_name
        st.session_state.flow_state = "ask_email"
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"Bonjour {st.session_state.patient_name}. Quelle est votre adresse e-mail pour recevoir les confirmations ?"
        })
        st.rerun()

    if st.session_state.flow_state == "ask_email":
        email = user_message.strip()
        if "@" in email and "." in email:
            st.session_state.patient_email = email
            st.session_state.flow_state = "ready"
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"Merci. Décrivez-moi maintenant votre demande."
            })
        else:
            st.session_state.messages.append({
                "role": "assistant",
                "content": "L'adresse saisie ne semble pas valide. Pouvez-vous réessayer ?"
            })
        st.rerun()

    if st.session_state.waiting_name_for_symptoms:
        extracted_name = extract_name(user_message)
        st.session_state.patient_name = extracted_name
        st.session_state.waiting_name_for_symptoms = False
        st.session_state.flow_state = "ask_email"
        st.session_state.buffered_symptom_message = st.session_state.buffered_symptom_message  # keep it

        st.session_state.messages.append({
            "role": "assistant",
            "content": f"Bonjour {st.session_state.patient_name}. Quelle est votre adresse e-mail pour recevoir les confirmations ?"
        })
        st.rerun()

        buffered_message = st.session_state.buffered_symptom_message
        st.session_state.buffered_symptom_message = ""

        run_triage_flow(buffered_message)
        st.rerun()

    run_triage_flow(user_message)
    st.rerun()


# -------------------------------------------------
# RESET
# -------------------------------------------------
if st.button("Réinitialiser"):
    conn = sqlite3.connect(database.DB_PATH)
    conn.execute("DELETE FROM appointments")
    conn.execute("DELETE FROM patients")
    conn.commit()
    conn.close()

    for key, value in defaults.items():
        st.session_state[key] = [] if isinstance(value, list) else value

    st.rerun()