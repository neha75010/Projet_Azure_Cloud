import json
import logging
import os
import re
from typing import List

logger = logging.getLogger(__name__)

RULE_KEYWORDS = {
    "cv": "cv",
    "resume": "cv",
    "rh": "rh",
    "azure": "azure",
    "cloud": "cloud",
    "document": "document",
    "pdf": "pdf",
    "doc": "document",
    "docx": "document",
    "rapport": "rapport",
    "report": "rapport",
    "stage": "stage",
    "intern": "stage",
}


def tags_from_rules(file_name: str) -> List[str]:
    base = file_name.lower().rsplit(".", 1)[0]
    tokens = re.split(r"[_\-\s.]+", base)
    tags: List[str] = []
    for token in tokens:
        if not token:
            continue
        mapped = RULE_KEYWORDS.get(token, token)
        if mapped not in tags:
            tags.append(mapped)
    if "document" not in tags:
        tags.append("document")
    return tags[:8]


def generate_tags(file_name: str) -> List[str]:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        logger.warning("OPENAI_API_KEY manquante — fallback règles")
        return tags_from_rules(file_name)

    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    prompt = (
        "Analyse le nom de fichier suivant et génère entre 3 et 8 tags courts en français.\n"
        f"Nom du fichier : {file_name}\n\n"
        "Retourne uniquement un tableau JSON de chaînes."
    )

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        content = (response.choices[0].message.content or "").strip()
        tags = _parse_tags_json(content)
        if 3 <= len(tags) <= 8:
            return tags
        logger.warning("Réponse OpenAI invalide (%s tags) — fallback règles", len(tags))
    except Exception as exc:
        logger.warning("Échec OpenAI — fallback règles: %s", exc)

    return tags_from_rules(file_name)


def _parse_tags_json(content: str) -> List[str]:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("La réponse n'est pas un tableau JSON")
    return [str(t).strip().lower() for t in data if str(t).strip()]
