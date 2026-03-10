import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from triage_engine import triage_request
from scheduler import find_available_slot
import database

# Page Config
st.set_page_config(page_title="Medical Triage AI", page_icon="💊", layout="wide")

# Init Database
database.init_db()

def get_appointments():
    conn = sqlite3.connect(database.DB_PATH)
    df = pd.read_sql_query("SELECT * FROM appointments", conn)
    conn.close()
    return df

def save_appointment(patient_name, start_time, duration, reason, type):
    conn = sqlite3.connect(database.DB_PATH)
    cursor = conn.cursor()
    # Create patient if not exists (simplified)
    cursor.execute("INSERT INTO patients (name) VALUES (?)", (patient_name,))
    patient_id = cursor.lastrowid
    cursor.execute("INSERT INTO appointments (patient_id, start_time, duration, reason, type) VALUES (?, ?, ?, ?, ?)",
                   (patient_id, start_time, duration, reason, type))
    conn.commit()
    conn.close()

# Sidebar - Doctor's Calendar View
st.sidebar.title("📅 Agenda du Docteur")
appointments_df = get_appointments()
if not appointments_df.empty:
    st.sidebar.table(appointments_df[['start_time', 'duration', 'type']])
else:
    st.sidebar.info("Aucun rendez-vous aujourd'hui.")

# Main UI
st.title("🏥 Assistant Médical Intelligent")
st.markdown("---")

col1, col2 = st.columns([2, 1])

with col1:
    st.header("Saisie du Patient")
    patient_name = st.text_input("Nom du Patient")
    patient_msg = st.text_area("Expliquez votre situation / symptômes", height=150)
    
    if st.button("Analyser ma demande", type="primary"):
        if not patient_name or not patient_msg:
            st.error("Veuillez remplir tous les champs.")
        else:
            with st.spinner("Analyse en cours..."):
                category, description, score, source = triage_request(patient_msg)
                st.info(f"Analyse réalisée par : {source}")
                
                # Show results
                if category == "URGENCY":
                    st.error(f"🚨 **URGENCE DÉTECTÉE : {description}**")
                    st.warning("Veuillez contacter immédiatement le 15 ou vous rendre aux urgences les plus proches.")
                elif category == "ANALYSIS_NEEDED":
                    st.success(f"✅ **Analyse IA : {description}**")
                    st.info("Un créneau de 20 minutes a été réservé. Une prescription pour analyses vous sera envoyée.")
                    
                    # Schedule
                    existing = [(row['start_time'], row['duration']) for _, row in appointments_df.iterrows()]
                    slot = find_available_slot(existing, 20)
                    if slot:
                        save_appointment(patient_name, slot, 20, patient_msg, "Complexe (Analyses)")
                        st.balloons()
                        st.success(f"Rendez-vous confirmé à **{slot}**.")
                        st.rerun()
                    else:
                        st.error("Désolé, plus aucun créneau disponible pour aujourd'hui.")
                else:
                    st.success(f"✅ **Analyse IA : {description}**")
                    # Schedule
                    existing = [(row['start_time'], row['duration']) for _, row in appointments_df.iterrows()]
                    slot = find_available_slot(existing, 15)
                    if slot:
                        save_appointment(patient_name, slot, 15, patient_msg, "Standard")
                        st.balloons()
                        st.success(f"Rendez-vous confirmé à **{slot}**.")
                        st.rerun()
                    else:
                        st.error("Désolé, plus aucun créneau disponible pour aujourd'hui.")

with col2:
    st.header("Aide Technique")
    st.info("""
    **Comment ça marche ?**
    1. **NLP** : Analyse du texte libre pour détecter l'urgence.
    2. **Système Expert** : Décision de la durée du RDV (15 vs 20 min).
    3. **OR-Tools** : Optimisation du calendrier en temps réel.
    """)
    
    if st.button("Réinitialiser l'agenda"):
        conn = sqlite3.connect(database.DB_PATH)
        conn.execute("DELETE FROM appointments")
        conn.execute("DELETE FROM patients")
        conn.commit()
        conn.close()
        st.rerun()

st.markdown("---")
st.caption("Démo réalisée pour une présentation technique - Architecture Full Python / Local")
