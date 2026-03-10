import sqlite3
import os

DB_PATH = "medical_demo.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Patients table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact TEXT
    )
    ''')
    
    # Appointments table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        start_time TEXT NOT NULL,
        duration INTEGER NOT NULL,
        reason TEXT,
        type TEXT,
        FOREIGN KEY (patient_id) REFERENCES patients (id)
    )
    ''')
    
    # Triage Logs
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS triage_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        raw_text TEXT,
        extracted_entities TEXT,
        category TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
