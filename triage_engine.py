import ollama

def triage_request(text):

    prompt = f"""
Tu es un assistant de triage médical.

Classe les symptômes du patient dans UNE seule catégorie :

URGENCY
ANALYSIS_NEEDED
STANDARD

Texte patient :
{text}
"""

    try:
        response = ollama.chat(
            model="llama3.1:latest",
            messages=[{"role": "user", "content": prompt}]
        )

        result = response["message"]["content"].strip()

        if "URGENCY" in result:
            return "URGENCY", "Urgence détectée", 3, "LLM Ollama"

        elif "ANALYSIS_NEEDED" in result:
            return "ANALYSIS_NEEDED", "Analyses recommandées", 2, "LLM Ollama"

        else:
            return "STANDARD", "Consultation standard (15 min)", 1, "LLM Ollama"

    except Exception:
        # fallback si le LLM ne répond pas
        text_lower = text.lower()

        if "poitrine" in text_lower:
            return "URGENCY", "Urgence détectée", 3, "Fallback rules"

        if "analyse" in text_lower or "prise de sang" in text_lower:
            return "ANALYSIS_NEEDED", "Analyses recommandées", 2, "Fallback rules"

        return "STANDARD", "Consultation standard (15 min)", 1, "Fallback rules"