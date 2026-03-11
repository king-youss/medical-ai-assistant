# Documentation du code actuel — Medical AI Assistant

_Date : 10 mars 2026_

## 1) Vue d’ensemble

Ce projet est une application **Streamlit** de triage médical local qui :

- récupère une description libre des symptômes d’un patient,
- classe la demande via un moteur de triage (`URGENCY`, `ANALYSIS_NEEDED`, `STANDARD`),
- propose automatiquement un créneau de rendez-vous,
- stocke les données dans une base **SQLite**.

L’objectif est de démontrer une architecture simple combinant :

- interface utilisateur web (`app.py`),
- persistance (`database.py`),
- logique de triage IA/règles (`triage_engine.py`),
- planification de créneaux (`scheduler.py`).

---

## 2) Structure des fichiers

- `app.py` : point d’entrée Streamlit, interface et orchestration globale.
- `database.py` : création/initialisation de la base SQLite et des tables.
- `triage_engine.py` : classification des demandes via Ollama + fallback par règles.
- `scheduler.py` : recherche du prochain créneau disponible.
- `requirements.txt` : dépendances Python.

---

## 3) Détail des modules

## `app.py`

Rôle principal : piloter l’application et relier tous les composants.

Fonctionnalités clés :

1. Configure la page Streamlit (`set_page_config`).
2. Initialise la base au démarrage via `database.init_db()`.
3. Lit les rendez-vous existants (`get_appointments`) avec `pandas.read_sql_query`.
4. Sauvegarde les patients et rendez-vous (`save_appointment`).
5. Affiche :
   - une barre latérale « Agenda du Docteur »,
   - un formulaire patient (nom + description symptômes),
   - une section d’aide technique.
6. Déclenche l’analyse via `triage_request(patient_msg)`.
7. Applique une logique selon la catégorie :
   - `URGENCY` : message d’alerte immédiate (pas de réservation),
   - `ANALYSIS_NEEDED` : réservation de 20 min,
   - `STANDARD` : réservation de 15 min.
8. Utilise `find_available_slot(existing, duration)` pour trouver un créneau.
9. Permet de réinitialiser l’agenda (suppression de `appointments` et `patients`).

Remarques techniques :

- Les dates de rendez-vous sont stockées en texte ISO (`slot.isoformat()`).
- Chaque enregistrement crée un nouveau patient (pas de déduplication par nom/contact).
- La variable `type` est utilisée comme nom de paramètre de fonction, ce qui masque le built-in Python `type` (fonctionnel ici, mais pas idéal).

## `database.py`

Rôle principal : gérer le schéma de données SQLite.

Constante :

- `DB_PATH = "medical_demo.db"`

Fonction :

- `init_db()` crée les tables si elles n’existent pas :
  - `patients` (`id`, `name`, `contact`),
  - `appointments` (`id`, `patient_id`, `start_time`, `duration`, `reason`, `type`),
  - `triage_logs` (`id`, `raw_text`, `extracted_entities`, `category`, `timestamp`).

Remarques techniques :

- La table `triage_logs` est créée mais **non alimentée** dans l’état actuel du code.
- Les clés étrangères existent au niveau schéma mais la logique applicative ne gère pas de contraintes avancées (unicité, cascade, etc.).

## `triage_engine.py`

Rôle principal : classer le texte patient dans une catégorie de triage.

Fonction :

- `triage_request(text)`

Comportement :

1. Construit un prompt demandant une sortie parmi :
   - `URGENCY`
   - `ANALYSIS_NEEDED`
   - `STANDARD`
2. Appelle `ollama.chat` avec le modèle `llama3.1:latest`.
3. Interprète le texte retourné :
   - contient `URGENCY` → catégorie urgence,
   - contient `ANALYSIS_NEEDED` → analyses recommandées,
   - sinon → standard.
4. En cas d’exception (Ollama indisponible, erreur réseau, etc.), applique des règles fallback :
   - si le texte contient `poitrine` → `URGENCY`,
   - si contient `analyse` ou `prise de sang` → `ANALYSIS_NEEDED`,
   - sinon → `STANDARD`.

Valeur retournée : tuple `(category, description, score, source)`.

## `scheduler.py`

Rôle principal : proposer le premier créneau libre dans la journée.

Fonction :

- `find_available_slot(existing, duration)`

Paramètres :

- `existing` : liste de tuples `(start_time_iso, duration_minutes)`.
- `duration` : durée demandée du nouveau rendez-vous en minutes.

Algorithme :

1. Définit une plage de travail **09:00 → 18:00** pour la date courante.
2. Balaye les créneaux toutes les **15 minutes**.
3. Vérifie les chevauchements avec les rendez-vous existants.
4. Retourne le premier créneau valide en ISO (`.isoformat()`), sinon `None`.

---

## 4) Flux d’exécution global

1. L’utilisateur saisit nom + symptômes.
2. Le triage classe la demande (`triage_engine`).
3. L’interface affiche le niveau de réponse.
4. Si non urgent, le scheduler cherche un slot.
5. Le rendez-vous est enregistré en base SQLite.
6. L’agenda affiché dans la sidebar est rafraîchi.

---

## 5) Dépendances (`requirements.txt`)

- `streamlit` : interface web interactive.
- `spacy` : présent dans les dépendances, non utilisé directement dans le code actuel.
- `ortools` : présent dans les dépendances, non utilisé directement dans le code actuel.
- `pandas` : lecture tabulaire des rendez-vous depuis SQLite.
- `pydantic` : présent dans les dépendances, non utilisé directement dans le code actuel.
- `ollama` : appel au modèle local pour le triage.

---

## 6) Limites actuelles et points d’amélioration

- Pas de validation métier avancée des entrées patient.
- Déduplication patient absente (insert systématique).
- `triage_logs` non exploité pour historiser les analyses.
- Dépendances potentiellement inutilisées (`spacy`, `ortools`, `pydantic`) dans la version actuelle.
- Gestion des horaires sur la journée courante uniquement.
- Pas de tests automatisés fournis dans le dépôt actuel.

---

## 7) Résumé

Le code actuel fournit une base fonctionnelle de démonstration :

- triage IA avec fallback,
- prise de rendez-vous automatique simple,
- persistance locale SQLite,
- interface Streamlit claire.

L’architecture est lisible et modulaire, avec une bonne séparation entre UI, triage, planification et base de données, ce qui facilite les évolutions futures.

---

## 8) Mise a jour du 11 mars 2026

Cette section complete la documentation precedente avec l'etat actuel observe dans le code.

### Evolutions majeures

- L'interface dans `app.py` est devenue une experience conversationnelle (chat) avec un parcours guide.
- Un nouveau module `google_calendar.py` est ajoute pour gerer les disponibilites et les rendez-vous via Google Calendar.
- Le triage (`triage_engine.py`) est enrichi avec :
   - extraction du prenom (`extract_name`),
   - detection d'un message de symptomes (`looks_like_symptom_message`),
   - reponse structuree avec categorie, description, message patient et score.

### Nouveau flux applicatif

1. L'assistant demande d'abord le nom du patient.
2. Le patient decrit ses symptomes dans le chat.
3. Le moteur de triage retourne : categorie, description, message patient, score, source.
4. Si urgence : message d'alerte, sans reservation.
5. Sinon : chargement des creneaux disponibles sur plusieurs jours ouvrables via Google Calendar.
6. Le patient choisit un jour puis un creneau.
7. La validation cree :
    - un rendez-vous local SQLite,
    - un evenement Google Calendar.
8. Le patient peut ensuite annuler ou deplacer le rendez-vous.

### Gestion d'etat dans l'interface

`app.py` utilise `st.session_state` avec des etats de parcours, notamment :

- `ask_name`
- `ready`
- `choose_day`
- `waiting_slot`
- `selected`
- `confirmed`
- `move_choose_day`
- `move_waiting_slot`
- `move_selected`

Cette machine d'etats permet un enchainement stable des actions utilisateur dans Streamlit.

### Module `google_calendar.py`

Fonctions principales :

- authentification OAuth (`get_calendar_service`),
- creation d'evenement (`create_google_event`),
- suppression (`delete_google_event`),
- deplacement (`move_google_event`),
- lecture des plages occupees d'une journee,
- generation des creneaux libres (pas de 15 min) sur plusieurs jours,
- agregation des jours disponibles avec compteur de slots.

Constantes importantes dans le code actuel :

- `CALENDAR_ID`
- `DOCTOR_EMAIL`
- `TIMEZONE = "Europe/Paris"`

### Impact sur l'ancienne documentation

- La planification n'est plus uniquement locale (`scheduler.py`) : la disponibilite est desormais calculee depuis Google Calendar.
- `scheduler.py` est encore present dans le depot mais n'est plus au coeur du flux principal observe.
- Le tuple de sortie de `triage_request` n'a plus la meme forme qu'avant (ajout d'un message de chat patient).

### Point de vigilance dependances

Le module `google_calendar.py` utilise des bibliotheques Google qui ne figurent pas dans `requirements.txt` actuel. Pour executer ce flux, il faut prevoir au minimum :

- `google-api-python-client`
- `google-auth`
- `google-auth-oauthlib`
- `google-auth-httplib2`

Sans ces paquets (et sans `credentials.json`), les fonctions Google Calendar ne pourront pas fonctionner.

---

## 9) État d'avancement du projet — 11 mars 2026

Bilan fonctionnel comparé au schéma cible (tableau blanc).

### ✅ Ce qui est FAIT (opérationnel)

| Fonctionnalité | Détail | Fichier(s) |
|---|---|---|
| Interface conversationnelle | Passage du formulaire classique à un chat Streamlit guidé | `app.py` |
| Moteur de triage (IA) | Ollama (`mistral-nemo`) avec fallback par mots-clés si indisponible | `triage_engine.py` |
| Détection d'urgence | Branche « Urgence → Hôpital » : alerte affichée, aucun RDV réservé | `app.py`, `triage_engine.py` |
| Connexion Google Calendar | Lecture des disponibilités réelles du médecin + création d'événements | `google_calendar.py` |
| Persistance locale | Patients et rendez-vous sauvegardés dans `medical_demo.db` (SQLite) | `database.py`, `app.py` |
| Logique de durée | RDV standard = 15 min, RDV analyse = 20 min | `app.py` |

### ⏳ Ce qui est EN COURS / PARTIEL

| Élément | État actuel | Ce qui manque |
|---|---|---|
| Extraction d'entités | Le prénom est extrait via `extract_name` | Le contact (mail/téléphone) n'est pas récupéré de façon structurée |
| Séparation des agendas | Seul le calendrier du médecin est géré | L'invitation automatique du patient (en tant qu'`attendee`) n'est pas active |
| Gestion des jours | Créneaux proposés sur ~14 jours ouvrables | Pas de vue calendrier mensuel (Jan/Fév/Mars tel que prévu sur le tableau) |

### ❌ Ce qui MANQUE (à faire pour correspondre au schéma cible)

#### 1. Communication & Notifications

- [x] **Envoi de mail** : Implémenté le 11/03/2026. Module `email_service.py` ajouté (SMTP/TLS via variables d'environnement). Trois types d'e-mails envoyés automatiquement : confirmation, annulation, déplacement. L'adresse du patient est collectée dans le chat (état `ask_email`).
- [ ] **Invitations Calendar au patient** : Le patient devrait être ajouté en tant qu'`attendee` dans l'événement Google pour que le RDV apparaisse dans son agenda.

#### 2. Branche « Analyse / Laboratoire »

- [x] **Instructions patient** : Implémenté le 11/03/2026. Lorsque le triage détecte `ANALYSIS_NEEDED`, le chat affiche automatiquement les consignes de préparation (à jeun, carte Vitale, traitement en cours). Ces consignes sont également incluses dans l'e-mail de confirmation.
- [x] **Orientation labo** : Implémenté le 11/03/2026. Trois laboratoires à proximité sont proposés dans le chat et dans l'e-mail de confirmation pour les rendez-vous de type analyse.

#### 3. Data & Analytics

- [x] **Historisation (`triage_logs`)** : Implémenté le 11/03/2026. La fonction `database.log_triage()` enregistre chaque analyse (texte brut, catégorie, description, score, source) dans la table `triage_logs`. Appelée automatiquement dans `run_triage_flow()` après chaque appel au moteur de triage.
- [ ] **Export de prescription** : Le schéma mentionne « Prescription Analyse ». Il manque la génération d'un document récapitulatif (même un simple texte) à remettre au patient.

### 🛠️ Prochaines étapes suggérées

Ordre recommandé pour suivre la logique du tableau blanc :

| Priorité | Action | Justification |
|---|---|---|
| **P1 — Fiabilité** | Remplir la table `triage_logs` à chaque analyse | Ne rien perdre des décisions de l'IA ; traçabilité médicale |
| **P2 — Communication** | Configurer l'envoi de mail de confirmation (SMTP ou API) | Fermer la boucle patient après la prise de RDV |
| **P3 — Métier** | Enrichir la branche « Analyse » (consignes + orientation labo) | Compléter le parcours patient tel que prévu sur le schéma |
