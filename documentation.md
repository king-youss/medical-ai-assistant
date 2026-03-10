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
