import ollama

MODEL_NAME = "mistral-nemo"


def extract_name(text: str) -> str:
    prompt = f"""
Tu dois extraire uniquement le prénom d'une personne à partir de son message.

Règles :
- Réponds uniquement par le prénom
- Pas de phrase complète
- Pas d'explication
- Une seule réponse
- Mets une majuscule au prénom

Exemples :
Message: je m'appelle youssouf
Réponse: Youssouf

Message: moi c'est amina
Réponse: Amina

Message: mon nom est paul durand
Réponse: Paul

Message: fatou
Réponse: Fatou

Message utilisateur :
{text}
"""

    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}]
        )

        name = response["message"]["content"].strip()

        if not name:
            return "Patient"

        name = name.replace("\n", " ").strip().split()[0]
        return name.capitalize()

    except Exception:
        raw = text.lower().strip()

        patterns = [
            "je m'appelle",
            "je suis",
            "moi c'est",
            "mon nom est",
            "c'est",
        ]

        for p in patterns:
            if raw.startswith(p):
                raw = raw.replace(p, "", 1).strip()
                break

        if not raw:
            return "Patient"

        return raw.split()[0].capitalize()


def looks_like_symptom_message(text: str) -> bool:
    text_lower = text.lower()

    symptom_keywords = [
        "j'ai", "jai", "mal", "douleur", "fièvre", "fievre", "tête",
        "gorge", "poitrine", "thorax", "respire", "respiration",
        "fatigue", "nausée", "vomir", "migraine", "sang",
        "analyse", "prise de sang", "bilan", "urine",
        "vertige", "malaise", "toux", "grippe", "rhume",
        "allergie", "brûlure", "froid", "chaud", "température",
        "diarrhée", "constipation", "vomissement"
    ]

    return any(keyword in text_lower for keyword in symptom_keywords)


def triage_request(text: str):
    prompt = f"""
Tu es un assistant de triage médical.

Tu dois classer le message du patient dans UNE SEULE catégorie parmi :
- URGENCY
- ANALYSIS_NEEDED
- STANDARD

Réponds EXACTEMENT au format suivant :

CATEGORY: <URGENCY ou ANALYSIS_NEEDED ou STANDARD>
DESCRIPTION: <courte phrase en français>
CHAT: <courte phrase adressée au patient en français>
SCORE: <3 pour URGENCY, 2 pour ANALYSIS_NEEDED, 1 pour STANDARD>

Règles :
- URGENCY : douleur thoracique, détresse respiratoire, perte de connaissance, saignement important, accident grave, symptôme neurologique grave, symptômes sévères
- ANALYSIS_NEEDED : prise de sang, bilan, analyse d’urine, laboratoire, cholestérol, glycémie, examen nécessitant des analyses
- STANDARD : symptômes légers ou modérés, consultation classique, problème non grave

Exemples :

Message : j'ai très mal à la poitrine et je respire mal
Réponse :
CATEGORY: URGENCY
DESCRIPTION: Symptômes potentiellement graves nécessitant une prise en charge urgente.
CHAT: Vos symptômes semblent préoccupants. Appelez le 15 immédiatement.
SCORE: 3

Message : je voudrais faire un bilan sanguin
Réponse :
CATEGORY: ANALYSIS_NEEDED
DESCRIPTION: La demande semble nécessiter des analyses médicales.
CHAT: Votre situation ne semble pas urgente. Choisissez un rendez-vous ci-dessous.
SCORE: 2

Message : j'ai mal à la gorge depuis hier
Réponse :
CATEGORY: STANDARD
DESCRIPTION: Les symptômes semblent compatibles avec une consultation standard.
CHAT: Votre situation ne semble pas urgente. Choisissez un rendez-vous ci-dessous.
SCORE: 1

Message du patient :
{text}
"""

    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response["message"]["content"].strip()

        category = "STANDARD"
        description = "Les symptômes semblent compatibles avec une consultation standard."
        chat_message = "Votre situation ne semble pas urgente. Choisissez un rendez-vous ci-dessous."
        score = 1

        for line in content.splitlines():
            line = line.strip()

            if line.startswith("CATEGORY:"):
                value = line.replace("CATEGORY:", "").strip()
                if value in ["URGENCY", "ANALYSIS_NEEDED", "STANDARD"]:
                    category = value

            elif line.startswith("DESCRIPTION:"):
                description = line.replace("DESCRIPTION:", "").strip()

            elif line.startswith("CHAT:"):
                chat_message = line.replace("CHAT:", "").strip()

            elif line.startswith("SCORE:"):
                try:
                    score = int(line.replace("SCORE:", "").strip())
                except ValueError:
                    score = 1

        if category == "URGENCY":
            score = 3
            if not chat_message:
                chat_message = "Vos symptômes semblent préoccupants. Appelez le 15 immédiatement."
        elif category == "ANALYSIS_NEEDED":
            score = 2
            if not chat_message:
                chat_message = "Votre situation ne semble pas urgente. Choisissez un rendez-vous ci-dessous."
        else:
            category = "STANDARD"
            score = 1
            if not chat_message:
                chat_message = "Votre situation ne semble pas urgente. Choisissez un rendez-vous ci-dessous."

        return category, description, chat_message, score, f"LLM Ollama ({MODEL_NAME})"

    except Exception:
        text_lower = text.lower()

        urgency_keywords = [
            "poitrine", "thorax", "respire mal", "respiration", "étouffe",
            "sang", "perte de connaissance", "inconscient", "malaise",
            "accident", "grave", "urgent", "avc", "paralysie",
            "douleur intense", "douleur forte"
        ]

        analysis_keywords = [
            "analyse", "prise de sang", "bilan", "laboratoire",
            "urine", "glucose", "glycémie", "cholestérol"
        ]

        if any(k in text_lower for k in urgency_keywords):
            return (
                "URGENCY",
                "Symptômes potentiellement graves détectés.",
                "Vos symptômes semblent préoccupants. Appelez le 15 immédiatement.",
                3,
                "Fallback rules"
            )

        if any(k in text_lower for k in analysis_keywords):
            return (
                "ANALYSIS_NEEDED",
                "La demande semble nécessiter des analyses médicales.",
                "Votre situation ne semble pas urgente. Choisissez un rendez-vous ci-dessous.",
                2,
                "Fallback rules"
            )

        return (
            "STANDARD",
            "Les symptômes semblent compatibles avec une consultation standard.",
            "Votre situation ne semble pas urgente. Choisissez un rendez-vous ci-dessous.",
            1,
            "Fallback rules"
        )