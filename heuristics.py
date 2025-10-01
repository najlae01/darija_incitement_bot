# Lightweight Darija/Arabizi incitement heuristics.
# Returns a small score bonus when explicit violence-encouraging lexemes are present.

import re

# Expand/curate this list with your moderators.
# Include Arabic and Arabizi variants.
LEXEMES = [
    r"\b(dreb|darb|drebhoum|dreb-hom|darbhum|drebkom)\b",
    r"\b(nqtel|n9tel|nqtlo|n9tlo|nqtlhom|n9tlhom|n9telkom)\b",
    r"\b(7rq|hrq|7rqou|7erqou|hreqhom)\b",
    r"\b(ksro|kassrou|ksr|ksrouhum|kassr)\b",
    r"\b(t3awno.*tderbo|taawnou.*tdrbo)\b",
    r"\b(hit|kill|attack|beat|smash)\b",
    r"\b(weapons?|swords?|knives?|molotov)\b",
    r"نقتل|نحرق|إحرق|دير العنف|اضربهم|كسروهم|سلاح|سكين|مطواة|قنبلة",
]

PATTERNS = [re.compile(p, re.IGNORECASE) for p in LEXEMES]

def incitement_bonus(text: str) -> float:
    bonus = 0.0
    for pat in PATTERNS:
        if pat.search(text):
            bonus += 0.07  # tune this weight
    # cap bonus
    return min(bonus, 0.2)
