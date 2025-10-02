# Lightweight Darija/Arabizi incitement heuristics.
# Returns a small score bonus when explicit violence-encouraging lexemes are present.

import re

# Expand/curate this list with your moderators.
# Include Arabic and Arabizi variants.
LEXEMES = [
    # Arabizi & English stems (violence verbs / weapons)
    r"\b[nty]?(dreb|darb)\w*",                       # dreb, ndrebouhom, tderbo...
    r"\b(n9?tel|nqtel|n9tlo|nqtlo|nqtl)\w*",         # n9tlhom, nqtlkom...
    r"\b(7rq|hrq|7erq|hreq)\w*",                     # 7rqou, hreqhom...
    r"\b(ksr|kassr|ksro|ksrou)\w*",                  # ksrouhum...
    r"\b(t3awno\w*\s+td?erb\w*)",                    # t3awno ... tderbo
    r"\b(hajm|hajmo|hajmou|hajmo(h|)om|hajmou(h|)om)\w*",  # hajmohom, hajmouhom (attack)
    r"\b(syof|syouf|sayf|seif|sif|sword|swords)\b",  # Arabizi/English 'sword(s)'
    r"\b(hit|kill|attack|smash|burn|molotov)\b",
    r"\b(weapon|weapons|knife|knives|gun|guns|bottle)\b",

    # Arabic verbs/nouns (violence/incitement)
    r"نقتل|نحرق|إ?حرق|اضرب(?:و?هم)?|كسرو(?:هم)?|دير(?:\s)?العنف",
    r"هاجم(?:و?هم)?|هجم(?:و?هم)?",                  # attack them
    r"سيف|سيوف|سلِّ?حوا|تسلَّ?حوا",                 # swords / get armed
    r"سكين|سكاكين|مطواة|خنجر|هراوة|عصي|حجر|حجارة|قنبلة|مولوتوف",
]

PATTERNS = [re.compile(p, re.IGNORECASE) for p in LEXEMES]

def incitement_bonus(text: str) -> float:
    bonus = 0.0
    for pat in PATTERNS:
        if pat.search(text):
            bonus += 0.07  # tune this weight
    # cap bonus
    return min(bonus, 0.2)
