# Documentation Technique — Medical AI Assistant

Date de mise à jour: 13 mars 2026

## 1) Vue d'ensemble actuelle

Le projet est une application Streamlit de triage médical conversationnel.

Objectifs actuels du code:
- analyser un message patient en texte libre,
- classer la demande en `URGENCY`, `ANALYSIS_NEEDED` ou `STANDARD`,
- proposer des créneaux de consultation en se basant sur Google Calendar,
- confirmer, annuler ou déplacer des rendez-vous,
- conserver une trace minimale des rendez-vous dans SQLite.

Le flux principal est aujourd'hui centré sur:
- UI chat dans `app.py`,
- triage LLM + fallback dans `triage_engine.py`,
- disponibilité/booking Google dans `google_calendar.py`,
- persistance locale dans `database.py`.

## 2) État des fichiers du dépôt

- `app.py`: application Streamlit principale (chat, machine d'états, réservation Google).
- `triage_engine.py`: extraction prénom, détection message symptômes, triage IA/fallback.
- `google_calendar.py`: OAuth Google, lecture disponibilités, create/delete/move événements.
- `database.py`: création du schéma SQLite (`patients`, `appointments`, `triage_logs`).
- `email_service.py`: service SMTP HTML prêt, mais non branché dans `app.py` sur cette branche.
- `scheduler.py`: scheduler local historique, non utilisé par `app.py` actuel.
- `requirements.txt`: dépendances Python partielles.
- `.env`: variables SMTP présentes localement.
- `.gitignore`: ignore `credentials.json`, `token.json`, `medical_demo.db`, environnements Python.

## 3) Analyse détaillée par module

### 3.1 `app.py`

Rôle:
- orchestrer le parcours utilisateur conversationnel,
- piloter la logique métier de réservation,
- appeler triage, calendrier Google et base locale.

Points techniques majeurs:
- Configuration Streamlit en layout centré.
- CSS custom important (thème sombre + composants de sélection de jours/créneaux).
- Fonctions DB locales:
   - `save_appointment(...)`
   - `delete_local_appointment(...)`
   - `update_local_appointment(...)`
- Utilitaires:
   - `format_slot(...)`
   - `slot_still_available(...)`
   - `split_slots_by_period(...)`
   - `render_slot_grid(...)`
   - `prepare_slots_for_booking(...)`
   - `run_triage_flow(...)`

Machine d'états gérée via `st.session_state`:
- `ask_name`
- `ready`
- `choose_day`
- `waiting_slot`
- `selected`
- `confirmed`
- `move_choose_day`
- `move_waiting_slot`
- `move_selected`

Parcours utilisateur réel:
1. AMI demande le prénom.
2. Le patient décrit sa demande/ses symptômes.
3. Le triage retourne la catégorie.
4. Si `URGENCY`: message d'alerte, arrêt du flux de réservation.
5. Sinon: récupération de créneaux Google (`build_google_available_slots_week`).
6. Choix jour -> choix créneau -> confirmation.
7. Création d'un événement Google + insertion locale SQLite.
8. Actions post-confirmation: annuler ou déplacer.

Durées de rendez-vous:
- `STANDARD`: 15 minutes
- `ANALYSIS_NEEDED`: 20 minutes

Observations importantes:
- Pas d'import `email_service` dans cette version d'`app.py`.
- Pas de collecte e-mail patient dans le chat.
- Pas d'insert dans `triage_logs`.
- Si `credentials.json` est absent, un `FileNotFoundError` peut remonter via `google_calendar.py`.

### 3.2 `triage_engine.py`

Rôle:
- traitement NLP/LLM du message patient.

Fonctions:
- `extract_name(text)`: extraction du prénom (LLM puis fallback règles).
- `looks_like_symptom_message(text)`: heuristique mots-clés symptômes.
- `triage_request(text)`: classification + message utilisateur.

Détails du triage:
- Modèle utilisé: `mistral-nemo` (`MODEL_NAME`).
- Format de réponse demandé au LLM:
   - `CATEGORY`
   - `DESCRIPTION`
   - `CHAT`
   - `SCORE`
- Valeur de retour:
   - `(category, description, chat_message, score, source)`
- Fallback robuste si l'appel Ollama échoue (listes de mots-clés urgence/analyses).

### 3.3 `google_calendar.py`

Rôle:
- couche d'intégration Google Calendar.

Fonctions clés:
- `get_calendar_service()` (OAuth via `credentials.json`/`token.json`)
- `create_google_event(...)`
- `delete_google_event(...)`
- `move_google_event(...)`
- `get_doctor_busy_slots_for_day(...)`
- `build_google_available_slots_for_day(...)`
- `build_google_available_slots_week(...)`
- `build_available_days(...)`

Caractéristiques:
- plage de travail: 09:00 -> 17:00,
- pas d'incrément: 15 min,
- jours ouvrables uniquement (lundi-vendredi),
- horizon par défaut: 14 jours.

Limitation actuelle:
- l'événement est créé avec le médecin uniquement dans `attendees`.
- le patient n'est pas ajouté comme participant calendrier.

### 3.4 `database.py`

Rôle:
- initialiser le schéma SQLite `medical_demo.db`.

Tables:
- `patients(id, name, contact)`
- `appointments(id, patient_id, start_time, duration, reason, type)`
- `triage_logs(id, raw_text, extracted_entities, category, timestamp)`

Limitation actuelle:
- `triage_logs` n'est pas alimentée par `app.py`.

### 3.5 `email_service.py`

Rôle:
- fournir des fonctions d'envoi SMTP HTML.

Fonctions:
- `send_confirmation_email(...)`
- `send_cancellation_email(...)`
- `send_reschedule_email(...)`

Configuration:
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` via variables d'environnement.

État actuel:
- module techniquement prêt,
- non utilisé par `app.py` dans cette branche.

### 3.6 `scheduler.py`

Rôle:
- ancien scheduler local de créneaux sur la journée.

État actuel:
- présent dans le dépôt,
- non utilisé par `app.py` (remplacé par la logique Google Calendar).

## 4) Flux d'exécution global (branche actuelle)

1. Démarrage Streamlit et init DB.
2. Conversation patient (nom, puis description).
3. Triage IA/fallback.
4. Si urgence -> message d'alerte.
5. Sinon -> calcul des disponibilités Google.
6. Sélection jour/créneau.
7. Confirmation:
    - création événement Google,
    - sauvegarde locale dans SQLite.
8. Option d'annulation ou de déplacement.

## 5) Dépendances et exécution

Contenu actuel de `requirements.txt`:
- `streamlit`
- `spacy`
- `ortools`
- `pandas`
- `pydantic`
- `ollama`

Écart technique important:
- `google_calendar.py` utilise des paquets Google non déclarés dans `requirements.txt`:
   - `google-api-python-client`
   - `google-auth`
   - `google-auth-oauthlib`
   - `google-auth-httplib2`

Prérequis runtime:
- fichier `credentials.json` requis pour OAuth Google,
- `token.json` généré après autorisation,
- instance Ollama disponible localement avec le modèle `mistral-nemo`.

## 6) Écarts avec la roadmap discutée précédemment

### Implémenté et opérationnel
- Interface conversationnelle Streamlit.
- Triage IA + fallback règles.
- Branche urgence avec arrêt du booking.
- Réservation/annulation/déplacement via Google Calendar.
- Persistance locale des rendez-vous.
- Distinction 15 min / 20 min.

### Implémenté dans le dépôt mais non branché
- Service e-mail complet (`email_service.py`).
- Variables SMTP locales (`.env`).

### Non implémenté sur cette branche
- Historisation active dans `triage_logs`.
- Collecte structurée de l'e-mail patient dans le chat.
- Envoi automatique des e-mails (confirmation/annulation/déplacement) depuis `app.py`.
- Consignes patient et orientation labo affichées dans `app.py` pour `ANALYSIS_NEEDED`.
- Ajout du patient dans `attendees` Google Calendar.
- Gestion propre de l'absence de `credentials.json` (actuellement crash possible).

## 7) Risques techniques actuels

- Risque d'échec au runtime si `credentials.json` absent.
- Risque d'échec environnement si dépendances Google non installées.
- Risque de dette de maintenance car `documentation.md` précédente ne décrivait pas l'état réel.
- Risque sécurité: secrets SMTP potentiellement exposés si `.env` est partagé.
- Risque qualité données: patients dupliqués (pas de déduplication ni contact obligatoire).

## 8) Recommandations prioritaires

1. Ajouter la gestion d'erreur explicite pour Google Calendar (`credentials.json` manquant).
2. Brancher `email_service.py` dans `app.py` + collecte e-mail patient.
3. Alimenter `triage_logs` à chaque analyse.
4. Compléter `requirements.txt` avec les paquets Google.
5. Ajouter le patient dans `attendees` pour synchronisation agenda.
6. Mettre en place des tests de non-régression sur le flux principal (triage -> slot -> confirmation).

## 9) Résumé exécutif

Le code de la branche actuelle fournit une base fonctionnelle solide pour un assistant médical conversationnel avec Google Calendar.

Le coeur produit fonctionne, mais la documentation précédente était en décalage et plusieurs briques utiles existent sans être reliées au flux principal (notamment e-mail et logging triage).

La priorité immédiate est de sécuriser l'exécution (gestion erreurs Google + dépendances) puis de reconnecter les fonctionnalités déjà codées mais inactives.
