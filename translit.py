# Simple Arabizi → Arabic normalization for Moroccan Darija.
# This is heuristic (rule-based). Improve with a learned transliterator for better accuracy.

import re

ARABIZI_MAP = [
    ('ch', 'ش'),
    ('gh', 'غ'),
    ('kh', 'خ'),
    ('sh', 'ش'),  # fallback
    ('3', 'ع'),
    ('7', 'ح'),
    ('9', 'ق'),
    ('2', 'ء'),
    ('5', 'خ'),
    ('6', 'ط'),
    ('9a', 'قا'),
    ('9i', 'قي'),
    ('9u', 'قو'),
]

PUNCT_SPACES = r"[،؛,!?:;]+"

def arabizi_to_arabic(text: str) -> str:
    t = text
    # common digraphs first (order matters)
    for src, dst in ARABIZI_MAP:
        t = re.sub(src, dst, t, flags=re.IGNORECASE)
    # collapse repeated punctuation
    t = re.sub(PUNCT_SPACES, lambda m: m.group(0)[0], t)
    # normalize spaces
    t = re.sub(r"\s+", " ", t).strip()
    return t

def normalize(text: str) -> str:
    # lower, unify quotes, keep emojis/hashtags/mentions
    t = text.replace("’", "'").replace("“", '"').replace("”", '"')
    t = re.sub(r"[‘`´]", "'", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t
