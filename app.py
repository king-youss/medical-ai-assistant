import streamlit as st
import sqlite3
import time
from datetime import datetime

import database

from triage_engine import (
    triage_request,
    extract_name,
    looks_like_symptom_message
)

from google_calendar import (
    create_google_event,
    delete_google_event,
    move_google_event,
    build_google_available_slots_week,
    build_available_days
)

from email_service import (
    send_confirmation_email,
    send_cancellation_email,
    send_reschedule_email
)

# ------------------------------------------------
# CONFIG
# ------------------------------------------------

st.set_page_config(
    page_title="AMI",
    page_icon="🩺",
    layout="centered"
)

database.init_db()

# ------------------------------------------------
# STYLE UI
# ------------------------------------------------

st.markdown("""
<style>

.block-container{
max-width:800px;
margin:auto;
}

.stApp{
background:#0f1117;
color:white;
}

header, footer, #MainMenu{
visibility:hidden;
}

.title{
text-align:center;
color:#4ADE80;
font-size:50px;
font-weight:700;
margin-bottom:5px;
}

.subtitle{
text-align:center;
color:#9CA3AF;
margin-bottom:30px;
}

.chat-card{
background:#161b22;
padding:20px;
border-radius:10px;
border:1px solid #2d333b;
}

.day-btn button{
width:100%;
height:70px;
border-radius:12px;
background:#1c2128;
border:1px solid #30363d;
}

.day-btn button:hover{
border:1px solid #4ADE80;
}

.slot-btn button{
width:100%;
height:45px;
border-radius:10px;
background:#1c2128;
border:1px solid #30363d;
}

.slot-btn button:hover{
border:1px solid #60A5FA;
}

.confirm-box{
background:#161b22;
padding:15px;
border-radius:10px;
border:1px solid #30363d;
margin-top:10px;
}

.success-box{
background:#052e16;
padding:15px;
border-radius:10px;
border:1px solid #065f46;
margin-top:10px;
}

</style>
""", unsafe_allow_html=True)

# ------------------------------------------------
# HEADER
# ------------------------------------------------

st.markdown('<div class="title">AMI</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Assistant Médical Intelligent</div>', unsafe_allow_html=True)

# ------------------------------------------------
# SESSION STATE
# ------------------------------------------------

defaults = {

    "messages": [],
    "patient_name": "",
    "patient_email": "",

    "flow_state": "ask_name",

    "available_days": [],
    "all_pending_slots": [],
    "pending_slots": [],

    "selected_day": None,
    "selected_slot": None,

    "pending_duration": None,
    "pending_reason": "",
    "pending_type": "",

    "confirmed_event_id": None,
    "confirmed_start_time": None,

    "pending_user_message": None,
    "pending_processing": False

}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ------------------------------------------------
# MESSAGE INITIAL
# ------------------------------------------------

if not st.session_state.messages:
    st.session_state.messages.append({
        "role": "assistant",
        "content": "Bonjour. Je suis AMI. Quel est votre nom ?"
    })

# ------------------------------------------------
# CHAT DISPLAY
# ------------------------------------------------

for msg in st.session_state.messages:

    avatar = "🧑" if msg["role"] == "user" else "🩺"

    with st.chat_message(msg["role"], avatar=avatar):
        st.write(msg["content"])

# ------------------------------------------------
# UTILITIES
# ------------------------------------------------

def format_slot(iso):
    return datetime.fromisoformat(iso).strftime("%d/%m/%Y à %H:%M")

def ai_thinking():
    with st.spinner("Analyse en cours..."):
        time.sleep(1.2)

def split_slots(slots):

    morning = []
    afternoon = []

    for s in slots:

        hour = datetime.fromisoformat(s["iso"]).hour

        if hour < 12:
            morning.append(s)
        else:
            afternoon.append(s)

    return morning, afternoon

def prepare_slots(duration, reason, type_):

    slots = build_google_available_slots_week(duration)
    days = build_available_days(duration)

    st.session_state.all_pending_slots = slots
    st.session_state.available_days = days
    st.session_state.pending_duration = duration
    st.session_state.pending_reason = reason
    st.session_state.pending_type = type_

    st.session_state.flow_state = "choose_day"

# ------------------------------------------------
# TRIAGE
# ------------------------------------------------

def run_triage(text):

    category, desc, message, score, source = triage_request(text)

    if category == "URGENCY":

        st.session_state.messages.append({
            "role": "assistant",
            "content": "⚠️ Situation urgente. Appelez le 15 immédiatement."
        })

        return

    duration = 20 if category == "ANALYSIS_NEEDED" else 15
    appt_type = "Analyse" if category == "ANALYSIS_NEEDED" else "Consultation"

    prepare_slots(duration, text, appt_type)

    st.session_state.messages.append({
        "role": "assistant",
        "content": message + " Choisissez un jour."
    })

# ------------------------------------------------
# CHOIX JOUR
# ------------------------------------------------

if st.session_state.flow_state == "choose_day":

    st.markdown("### Choisissez un jour")

    cols = st.columns(3)

    for i, day in enumerate(st.session_state.available_days):

        with cols[i % 3]:

            st.markdown('<div class="day-btn">', unsafe_allow_html=True)

            label = f"{day['label']}\n{day['count']} disponibles"

            if st.button(label):

                st.session_state.selected_day = day["date_iso"]

                st.session_state.pending_slots = [
                    s for s in st.session_state.all_pending_slots
                    if s["date_iso"] == day["date_iso"]
                ]

                st.session_state.flow_state = "choose_slot"
                st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------------
# CHOIX CRENEAU
# ------------------------------------------------

if st.session_state.flow_state == "choose_slot":

    st.markdown("### Choisissez un créneau")

    morning, afternoon = split_slots(st.session_state.pending_slots)

    st.markdown("#### Matin")

    cols = st.columns(4)

    for i, slot in enumerate(morning):

        with cols[i % 4]:

            st.markdown('<div class="slot-btn">', unsafe_allow_html=True)

            if st.button(slot["label"]):

                st.session_state.selected_slot = slot["iso"]
                st.session_state.flow_state = "selected"
                st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("#### Après-midi")

    cols = st.columns(4)

    for i, slot in enumerate(afternoon):

        with cols[i % 4]:

            st.markdown('<div class="slot-btn">', unsafe_allow_html=True)

            if st.button(slot["label"]):

                st.session_state.selected_slot = slot["iso"]
                st.session_state.flow_state = "selected"
                st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------------
# VALIDATION RDV
# ------------------------------------------------

if st.session_state.flow_state == "selected":

    st.markdown(
        f'<div class="confirm-box">Créneau choisi : <b>{format_slot(st.session_state.selected_slot)}</b></div>',
        unsafe_allow_html=True
    )

    if st.button("Confirmer le rendez-vous"):

        ai_thinking()

        google = create_google_event(
            st.session_state.patient_name,
            st.session_state.selected_slot,
            st.session_state.pending_duration,
            st.session_state.pending_reason,
            st.session_state.pending_type
        )

        st.session_state.confirmed_event_id = google["event_id"]
        st.session_state.confirmed_start_time = st.session_state.selected_slot

        try:
            send_confirmation_email(
                st.session_state.patient_email,
                st.session_state.patient_name,
                st.session_state.selected_slot,
                st.session_state.pending_duration,
                st.session_state.pending_type,
                st.session_state.pending_reason
            )
        except Exception:
            pass

        st.session_state.messages.append({
            "role": "assistant",
            "content": f"Rendez-vous confirmé pour le {format_slot(st.session_state.selected_slot)}"
        })

        st.session_state.flow_state = "confirmed"
        st.rerun()

# ------------------------------------------------
# ACTIONS
# ------------------------------------------------

if st.session_state.flow_state == "confirmed":

    st.markdown(
        f'<div class="success-box">Rendez-vous confirmé<br>{format_slot(st.session_state.confirmed_start_time)}</div>',
        unsafe_allow_html=True
    )

    c1, c2 = st.columns(2)

    with c1:

        if st.button("Annuler"):

            try:
                delete_google_event(st.session_state.confirmed_event_id)
            except Exception:
                pass

            try:
                send_cancellation_email(
                    st.session_state.patient_email,
                    st.session_state.patient_name,
                    st.session_state.confirmed_start_time
                )
            except Exception:
                pass

            st.success("Rendez-vous annulé")

    with c2:

        if st.button("Déplacer"):

            prepare_slots(
                st.session_state.pending_duration,
                st.session_state.pending_reason,
                st.session_state.pending_type
            )

            st.session_state.flow_state = "choose_day"
            st.rerun()

# ------------------------------------------------
# CHAT INPUT
# ------------------------------------------------

user = st.chat_input("Décrivez votre problème")

if user:

    st.session_state.messages.append({
        "role": "user",
        "content": user
    })

    st.session_state.pending_user_message = user
    st.session_state.pending_processing = True
    st.rerun()

# ------------------------------------------------
# PROCESS MESSAGE
# ------------------------------------------------

if st.session_state.pending_processing:

    user_message = st.session_state.pending_user_message

    ai_thinking()

    st.session_state.pending_processing = False
    st.session_state.pending_user_message = None

    if st.session_state.flow_state == "ask_name":

        st.session_state.patient_name = extract_name(user_message)
        st.session_state.flow_state = "ask_email"

        st.session_state.messages.append({
            "role": "assistant",
            "content": f"Bonjour {st.session_state.patient_name}. Quelle est votre adresse email ?"
        })

        st.rerun()

    elif st.session_state.flow_state == "ask_email":

        st.session_state.patient_email = user_message
        st.session_state.flow_state = "ready"

        st.session_state.messages.append({
            "role": "assistant",
            "content": "Merci. Décrivez vos symptômes."
        })

        st.rerun()

    else:

        run_triage(user_message)
        st.rerun()