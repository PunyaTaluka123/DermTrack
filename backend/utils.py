"""Utility functions for DermaTrack API"""
from typing import Optional, List
import bleach


def sanitize_html(text: str) -> str:
    """Sanitize user input to prevent XSS attacks"""
    if not text:
        return text
    # Allow basic formatting but strip dangerous tags
    allowed_tags = ['b', 'i', 'u', 'em', 'strong', 'p', 'br', 'ul', 'ol', 'li']
    return bleach.clean(text, tags=allowed_tags, strip=True)


def as_int_or_none(value) -> Optional[int]:
    """Convert a value to int or return None if it can't be converted"""
    try:
        if value is None:
            return None
        s = str(value).strip()
        if s == "":
            return None
        return int(s)
    except Exception:
        return None


def suggest_questions_from_text(text: str, n: int = 5) -> List[str]:
    """Generate suggestion questions based on text content"""
    t = (text or "").lower()
    base: List[str] = []

    # General dermatology prompts
    base.extend([
        "When did these symptoms first start, and have they changed over time?",
        "On a scale of 1–10, how severe are the symptoms right now?",
        "Have you noticed any triggers (e.g., new products, heat, stress, foods)?",
        "What treatments or home remedies have you tried, and did they help?",
        "Do you have any photos showing how it looked at its worst?",
    ])

    # Condition-specific questions
    if any(k in t for k in ["itch", "itchy", "pruritus"]):
        base.append("Is the area itchy throughout the day or worse at night?")
        base.append("Does antihistamine or cold compress reduce the itch?")

    if any(k in t for k in ["pain", "tender", "sore"]):
        base.append("Is the area painful to touch or only with movement?")
        base.append("Have you noticed swelling, warmth, or fever with the pain?")

    if any(k in t for k in ["rash", "red", "patch", "lesion", "spots"]):
        base.append("Where on the body did the rash start, and did it spread?")
        base.append("Do the lesions blanch (turn white) when pressed?")

    if any(k in t for k in ["acne", "pimple", "blackhead", "whitehead"]):
        base.append("Do breakouts correlate with menstrual cycle, stress, or diet?")
        base.append("What is your current skincare routine (cleanser, actives, SPF)?")

    if any(k in t for k in ["eczema", "dermatitis", "atopic"]):
        base.append("Any family history of eczema, asthma, or allergies?")
        base.append("How often do you moisturize and what products do you use?")

    if any(k in t for k in ["psoriasis", "plaque", "silvery scale"]):
        base.append("Any joint pain or stiffness suggestive of psoriatic arthritis?")
        base.append("Have you tried topical steroids or vitamin D analogues?")

    if any(k in t for k in ["infection", "pus", "ooze", "crust"]):
        base.append("Have you had recent antibiotic use or noticed spreading redness?")

    if any(k in t for k in ["allergy", "allergic", "contact"]):
        base.append("Any new detergents, fragrances, jewelry, or cosmetics recently?")

    # De-duplicate and return top n
    seen = set()
    dedup = []
    for q in base:
        if q not in seen:
            seen.add(q)
            dedup.append(q)

    return dedup[: max(3, min(5, n or 5))]
