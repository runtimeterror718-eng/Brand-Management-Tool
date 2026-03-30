"""
Exhaustive Hinglish / Hindi slang lexicon for Indian social media sentiment analysis.

Covers: crisis words, praise, profanity, brand complaints, meme culture, student slang.
Designed for brand monitoring across Instagram, X, Reddit, YouTube, Telegram.

Each category maps term → sentiment weight:
  - Negative terms: -1.0 (strong) to -0.3 (mild)
  - Positive terms:  0.3 (mild)  to  1.0 (strong)
  - Neutral terms:   0.0
"""

from __future__ import annotations

# =============================================================================
# 1. CRISIS / BOYCOTT / OUTRAGE  (severity keywords — negative)
# =============================================================================
CRISIS_HINGLISH = {
    # Boycott & protest
    "boycott karo": -1.0,
    "band karo": -0.9,
    "bahishkaar": -1.0,
    "bahishkar": -1.0,
    "uninstall karo": -0.9,
    "delete karo": -0.7,
    "1-star do": -0.9,
    "1 star karo": -0.9,
    "rating girao": -0.9,
    "sharam karo": -0.8,
    "dhikkar hai": -0.9,
    "lanat hai": -0.9,
    "thoo hai": -0.9,
    "murdabaad": -1.0,
    "murdabad": -1.0,
    "haye haye": -0.6,

    # Anger & frustration
    "bakwaas": -0.7,
    "bakwas": -0.7,
    "bakvas": -0.7,
    "bekar": -0.6,
    "ghatiya": -0.8,
    "ghatia": -0.8,
    "wahiyat": -0.8,
    "wahiyaat": -0.8,
    "tatti": -0.9,
    "tatti hai": -0.9,
    "gandh": -0.7,
    "ganda": -0.7,
    "gandi": -0.7,
    "kachra": -0.8,
    "kachraa": -0.8,
    "raddi": -0.7,
    "faltu": -0.7,
    "faaltu": -0.7,
    "nikammi": -0.7,
    "nikamma": -0.7,
    "jhol": -0.6,
    "jhol hai": -0.7,
    "bhasad": -0.7,
    "bhasaad": -0.7,
    "gadbad": -0.6,
    "gadbadi": -0.6,
    "tang aa gaye": -0.7,
    "thak gaye": -0.5,
    "sar dard": -0.4,
    "sardard": -0.4,
    "paagal kar diya": -0.7,
    "pagal bana diya": -0.7,
    "dimag kharab": -0.7,
    "dimag ka dahi": -0.8,
    "jaan kha li": -0.7,
    "naak mein dum": -0.7,
    "ghanta": -0.6,
    "ghanta kuch hoga": -0.7,
    "fuddu": -0.7,
    "fuddu hai": -0.7,
    "chutiyapa": -0.9,
    "chutiyaap": -0.9,
    "bakchodi": -0.8,
    "harami": -0.8,
    "kamina": -0.8,
    "kameena": -0.8,
    "gadha": -0.5,
    "gadhe": -0.5,
    "ullu": -0.5,
    "ullu bana diya": -0.8,
    "chuna laga diya": -0.8,
    "loot liya": -0.8,
    "loota": -0.8,
    "panga mat le": -0.5,
    "bhand": -0.6,

    # Scam & fraud
    "scam hai": -1.0,
    "scam hai bhai": -1.0,
    "fraad": -0.9,
    "frod": -0.9,
    "dhokha": -0.9,
    "dhoka": -0.9,
    "thuggi": -0.9,
    "thugi": -0.9,
    "lootere": -0.8,
    "lutera": -0.8,
    "chor": -0.7,
    "chor hai": -0.8,
    "paisa barbaad": -0.9,
    "paisa doob gaya": -0.9,
    "paisa vasool nahi": -0.8,
    "katega": -0.7,
    "kat gaya": -0.8,
    "chuna lagaya": -0.8,
    "jhansa": -0.8,
    "jhansa diya": -0.8,
    "chamcha": -0.6,
    "bikau": -0.7,
    "bikau hai": -0.7,
    "paid hai ye": -0.5,

    # Disappointment
    "disappoint kar diya": -0.7,
    "bharosa toot gaya": -0.8,
    "umeed nahi thi": -0.6,
    "expectations se gira": -0.7,
    "bahut bura": -0.7,
    "worst hai": -0.9,
    "flop": -0.7,
    "flop show": -0.7,
    "bekaar experience": -0.7,
    "regret ho raha": -0.6,
    "galti kar di": -0.6,
    "kabhi nahi": -0.7,
}

# =============================================================================
# 2. POSITIVE / PRAISE / HYPE
# =============================================================================
POSITIVE_HINGLISH = {
    # Praise
    "mast": 0.7,
    "maast": 0.7,
    "zabardast": 0.9,
    "zabardast hai": 0.9,
    "kadak": 0.8,
    "kadak hai": 0.8,
    "dhansu": 0.8,
    "shandaar": 0.9,
    "shandar": 0.9,
    "kamaal": 0.8,
    "kamaal hai": 0.8,
    "lajawab": 0.9,
    "lajawaab": 0.9,
    "bemisaal": 0.9,
    "badhiya": 0.7,
    "badhia": 0.7,
    "badiya": 0.7,
    "maza aa gaya": 0.8,
    "mazaa": 0.6,
    "jhakkas": 0.8,
    "jhakaas": 0.8,
    "jhakas": 0.8,
    "solid hai": 0.7,
    "tagda": 0.7,
    "tagdi": 0.7,
    "ekdum": 0.5,
    "ekdam": 0.5,
    "bindaas": 0.6,
    "bindass": 0.6,
    "bawal": 0.7,
    "bawaal": 0.7,
    "toofani": 0.7,
    "first class": 0.8,
    "asli": 0.5,
    "kamaal ka": 0.8,
    "dimaag hila diya": 0.9,
    "paisa vasool": 0.8,
    "gazab": 0.8,
    "gajab": 0.8,
    "killer hai": 0.8,
    "fire hai": 0.8,
    "lit hai": 0.7,
    "OP hai": 0.8,
    "beast hai": 0.8,

    # Hype & support
    "support karo": 0.5,
    "jai ho": 0.6,
    "aag laga di": 0.8,
    "dil jeet liya": 0.9,
    "fan ho gaya": 0.8,
    "respect badh gayi": 0.7,
    "legend hai": 0.9,
    "sher": 0.7,
    "sherni": 0.7,
    "bada W": 0.8,
    "jabarjast": 0.8,
    "on fire": 0.7,

    # Approval
    "sahi hai": 0.5,
    "sahi baat": 0.5,
    "bilkul sahi": 0.6,
    "ekdum sahi": 0.6,
    "baat rakh di": 0.7,
    "faxxx": 0.5,
    "true hai": 0.4,
    "based": 0.5,
}

# =============================================================================
# 3. PROFANITY / ABUSE (for detection & filtering — all negative)
# =============================================================================
PROFANITY_HINGLISH = {
    # Full forms
    "bhenchod": -1.0,
    "benchod": -1.0,
    "madarchod": -1.0,
    "chutiya": -0.9,
    "gandu": -0.9,
    "lodu": -0.8,
    "laude": -0.8,
    "lavde": -0.8,
    "randi": -0.9,
    "randi rona": -0.7,
    "saala": -0.4,
    "saale": -0.4,
    "sale": -0.4,
    "kutte": -0.7,
    "kutta": -0.7,
    "suar": -0.7,
    "suwar": -0.7,
    "haramkhor": -0.8,
    "chodu": -0.9,
    "jhaat": -0.8,
    "jhaatu": -0.8,
    "tharki": -0.7,
    "chapri": -0.6,
    "chapri hai": -0.6,
    "chhapri": -0.6,

    # Abbreviations & censored forms
    "bc": -0.8,
    "mc": -0.8,
    "bsdk": -0.9,
    "bsdke": -0.9,
    "bsdka": -0.9,
    "bkl": -0.8,
    "tmkc": -0.9,
    "teri maa ki": -0.9,
    "laudu": -0.8,
    "lawde": -0.8,

    # Leetspeak / symbol variants (common on Instagram)
    "bh3nchod": -1.0,
    "b€nch0d": -1.0,
    "ch00tiya": -0.9,
    "g@ndu": -0.9,
    "m@darchod": -1.0,
}

# =============================================================================
# 4. BRAND / PRODUCT COMPLAINTS — negative sentiment
# =============================================================================
BRAND_COMPLAINTS_HINGLISH = {
    # Product quality
    "maal kharab hai": -0.8,
    "quality ghatiya hai": -0.8,
    "sasta maal": -0.5,
    "nakli": -0.8,
    "nakli hai": -0.8,
    "first copy": -0.6,
    "cheez toot gayi": -0.7,
    "do din mein kharab": -0.8,
    "waste hai": -0.7,
    "waste of money": -0.8,
    "overpriced hai": -0.6,
    "mehnga": -0.3,
    "bahut mehnga": -0.5,
    "loot machi hai": -0.8,
    "chor bazaar": -0.7,
    "nalla product": -0.8,

    # Customer service
    "response nahi de rahe": -0.7,
    "call nahi utha rahe": -0.7,
    "ignore kar rahe": -0.7,
    "ghoom rahe hain": -0.6,
    "taka rahe hain": -0.6,
    "jhoota promise": -0.8,
    "jhooth bol rahe": -0.8,
    "refund nahi diya": -0.8,
    "refund kab milega": -0.6,
    "replacement do": -0.5,
    "koi sunne wala nahi": -0.7,
    "customer care bakwaas": -0.8,
    "robot se baat kar raha hoon": -0.6,
    "copy paste reply": -0.6,
    "escalate karo": -0.5,
    "consumer court": -0.9,
    "consumer forum": -0.9,
    "legal action": -0.9,
    "legal notice": -0.9,
    "twitter pe aao tab sunte ho": -0.7,

    # Delivery / e-commerce
    "late delivery": -0.5,
    "delivery nahi aayi": -0.7,
    "wrong product": -0.7,
    "galat product": -0.7,
    "damaged aaya": -0.7,
    "seal tuta hua": -0.7,
    "used product bheja": -0.8,
    "khali dabba": -0.9,
    "empty box": -0.9,
    "tracking update nahi": -0.5,
    "return nahi ho raha": -0.6,
    "refund pending": -0.5,
}

# =============================================================================
# 5. BRAND / PRODUCT PRAISE — positive sentiment
# =============================================================================
BRAND_PRAISE_HINGLISH = {
    "solid build": 0.7,
    "premium feel": 0.7,
    "asli maal": 0.7,
    "achha maal hai": 0.7,
    "tagda product": 0.7,
    "tikau": 0.6,
    "tikaau": 0.6,
    "lambi race ka ghoda": 0.8,
    "value for money": 0.8,
    "VFM": 0.7,
    "worth hai": 0.7,
    "worth it hai": 0.7,
    "sasta aur accha": 0.7,
}

# =============================================================================
# 6. MEME CULTURE / VIRAL PHRASES
# =============================================================================
MEME_HINGLISH = {
    # Sarcasm markers (appear positive but often negative — flag for manual review)
    "waah": 0.0,         # highly context-dependent / sarcastic
    "wah wah": 0.0,
    "bahut accha": 0.0,  # sarcastic when isolated
    "slow clap": -0.5,
    "slow claps": -0.5,
    "ye toh hona hi tha": -0.4,
    "expected tha": -0.3,
    "pata tha": -0.3,
    "pta tha": -0.3,
    "aur kya chahiye": -0.4,

    # Sadness / pain memes
    "sed lyf": -0.3,
    "sed life": -0.3,
    "dard": -0.4,
    "dukh dard peeda": -0.5,
    "rula diya": -0.4,
    "pain": -0.3,

    # Hype memes
    "pawri ho rahi hai": 0.5,
    "aag laga di": 0.7,
    "viral ho gaya": 0.3,
    "trending": 0.2,

    # Reaction memes
    "bruh": -0.2,
    "bruh moment": -0.3,
    "ded": 0.0,
    "sus": -0.3,
    "sussy": -0.3,
    "cope": -0.4,
    "copium": -0.4,
    "ratio": -0.5,
    "ratioed": -0.5,
    "bada L": -0.6,
    "skill issue": -0.5,
    "touch grass": -0.4,
    "ok boomer": -0.3,
    "ok uncle": -0.3,
    "ok aunty": -0.3,

    # Indian meme phrases
    "rasode mein kaun tha": 0.0,
    "mera desh badal raha hai": -0.3,
    "acche din": -0.3,   # almost always sarcastic
    "janta maaf nahi karegi": -0.7,
    "sharma ji ka beta": 0.0,
    "log kya kahenge": -0.2,
    "papa ki pari": -0.2,
    "engineers of india": -0.2,
    "IT coolie": -0.4,
    "sab moh maya hai": -0.3,

    # Win/loss
    "W": 0.6,
    "bada W": 0.7,
    "L": -0.5,
    "bada L": -0.6,
    "F in chat": -0.4,

    # Meme quality
    "normie": -0.2,
    "normie hai": -0.3,
    "dank": 0.3,
    "denk": 0.2,
    "komedy": -0.3,  # ironic
}

# =============================================================================
# 7. COLLEGE / STUDENT SLANG
# =============================================================================
STUDENT_HINGLISH = {
    # Academic frustration
    "KT": -0.5,
    "backlog": -0.5,
    "mass bunk": 0.0,
    "proxy laga": 0.0,
    "attendance shortage": -0.4,
    "debarred": -0.8,
    "ratta": -0.2,
    "ratta maar": -0.3,
    "ghissu": -0.2,
    "padh le bsdk": -0.4,
    "padhai kar le": -0.2,

    # Student life
    "mess ka khana": -0.4,
    "broke hu": -0.4,
    "month end": -0.3,
    "ghar se paisa maang": -0.3,
    "LinkedIn cringe": -0.5,
    "humble brag": -0.4,

    # Service complaints (student context)
    "wifi nahi chal raha": -0.6,
    "data khatam": -0.5,
    "plan bekar hai": -0.6,
    "speed nahi aa rahi": -0.6,
    "buffering": -0.4,
    "student discount": 0.0,

    # Student positive
    "placement": 0.3,
    "dream company": 0.6,
    "package": 0.3,
}

# =============================================================================
# 8. NEUTRAL / COMMON SLANG  (for Hinglish language detection, not sentiment)
# =============================================================================
NEUTRAL_HINGLISH = {
    "yaar": 0.0,
    "yar": 0.0,
    "bhai": 0.0,
    "bro": 0.0,
    "behen": 0.0,
    "behn": 0.0,
    "didi": 0.0,
    "bhaiya": 0.0,
    "bhaiyya": 0.0,
    "arre": 0.0,
    "arey": 0.0,
    "accha": 0.0,
    "haan": 0.0,
    "nahi": 0.0,
    "nai": 0.0,
    "theek hai": 0.0,
    "thik hai": 0.0,
    "chal": 0.0,
    "chalo": 0.0,
    "kya baat hai": 0.0,
    "kya scene hai": 0.0,
    "matlab": 0.0,
    "waise": 0.0,
    "vaise": 0.0,
    "bas": 0.0,
    "bohot": 0.0,
    "bahut": 0.0,
    "bhot": 0.0,
    "boht": 0.0,
    "thoda": 0.0,
    "jugaad": 0.0,
    "jugad": 0.0,
    "fundaa": 0.0,
    "funda": 0.0,
    "panga": -0.2,
    "lafda": -0.3,
    "lafda ho gaya": -0.4,
    "chill hai": 0.2,
    "chill maar": 0.2,
    "tension mat le": 0.2,
    "rehne de": -0.1,
    "koi na": 0.1,
    "koi nai": 0.1,
    "vella": -0.1,
    "velli": -0.1,
    "timepass": 0.0,
}

# =============================================================================
# 9. POLITICAL / COMMUNITY FLAGS  (for crisis detection, not sentiment bias)
# =============================================================================
POLITICAL_FLAGS_HINGLISH = {
    "sanghi": -0.5,
    "librandu": -0.5,
    "liberandu": -0.5,
    "bhakt": -0.4,
    "anti-national": -0.7,
    "urban naxal": -0.6,
    "IT cell": -0.5,
    "paid troll": -0.6,
    "godi media": -0.6,
    "presstitute": -0.7,
    "troll hai": -0.3,
    "bot hai": -0.3,
    "fake account": -0.5,
}

# =============================================================================
# 10. INSTAGRAM-SPECIFIC SPAM (Hinglish)
# =============================================================================
INSTAGRAM_SPAM_HINGLISH = [
    "follow back karo",
    "follow for follow",
    "f4f",
    "like for like",
    "l4l",
    "dm for collab",
    "paid promo",
    "meri profile dekho",
    "check my profile",
    "bio mein link",
    "link in bio",
    "free mein",
    "paise kamao",
    "ghar baithe kamao",
    "whatsapp karo",
    "telegram join karo",
]


# =============================================================================
# COMBINED ACCESSORS
# =============================================================================

def get_all_negative_terms() -> dict[str, float]:
    """All negative-sentiment Hinglish terms with weights."""
    combined = {}
    combined.update(CRISIS_HINGLISH)
    combined.update(PROFANITY_HINGLISH)
    combined.update(BRAND_COMPLAINTS_HINGLISH)
    combined.update(POLITICAL_FLAGS_HINGLISH)
    # Only include negative meme/student terms
    for k, v in {**MEME_HINGLISH, **STUDENT_HINGLISH}.items():
        if v < 0:
            combined[k] = v
    return combined


def get_all_positive_terms() -> dict[str, float]:
    """All positive-sentiment Hinglish terms with weights."""
    combined = {}
    combined.update(POSITIVE_HINGLISH)
    combined.update(BRAND_PRAISE_HINGLISH)
    for k, v in {**MEME_HINGLISH, **STUDENT_HINGLISH}.items():
        if v > 0:
            combined[k] = v
    return combined


def get_all_terms() -> dict[str, float]:
    """Complete lexicon — every term with its sentiment weight."""
    combined = {}
    combined.update(CRISIS_HINGLISH)
    combined.update(POSITIVE_HINGLISH)
    combined.update(PROFANITY_HINGLISH)
    combined.update(BRAND_COMPLAINTS_HINGLISH)
    combined.update(BRAND_PRAISE_HINGLISH)
    combined.update(MEME_HINGLISH)
    combined.update(STUDENT_HINGLISH)
    combined.update(NEUTRAL_HINGLISH)
    combined.update(POLITICAL_FLAGS_HINGLISH)
    return combined


def get_crisis_terms() -> list[str]:
    """All terms that should trigger severity keyword scoring."""
    crisis = {}
    crisis.update(CRISIS_HINGLISH)
    crisis.update(PROFANITY_HINGLISH)
    crisis.update(BRAND_COMPLAINTS_HINGLISH)
    crisis.update(POLITICAL_FLAGS_HINGLISH)
    return [k for k, v in crisis.items() if v <= -0.6]


def get_spam_phrases() -> list[str]:
    """Instagram/social media spam phrases in Hinglish."""
    return list(INSTAGRAM_SPAM_HINGLISH)


def get_sarcasm_markers() -> list[str]:
    """Terms that frequently indicate sarcasm — flag for manual review."""
    return [
        "waah", "wah wah", "bahut accha", "slow clap", "slow claps",
        "ye toh hona hi tha", "expected tha", "pata tha", "pta tha",
        "aur kya chahiye", "acche din", "mera desh badal raha hai",
        "komedy", "ok boomer", "ok uncle", "ok aunty",
    ]


def is_hinglish(text: str) -> bool:
    """Quick check if text contains Hinglish terms (useful when fastText says 'en')."""
    text_lower = text.lower()
    hinglish_markers = [
        "yaar", "bhai", "behen", "arre", "accha", "haan", "nahi", "kya",
        "hai", "mein", "ka", "ki", "ke", "se", "ko", "par", "aur",
        "bohot", "bahut", "karo", "karna", "dekho", "suno", "chalo",
        "matlab", "waise", "theek", "bilkul", "ekdum",
    ]
    words = text_lower.split()
    hits = sum(1 for w in words if w in hinglish_markers)
    return hits >= 2 or (len(words) > 0 and hits / len(words) > 0.15)


def compute_hinglish_sentiment(text: str) -> tuple[float, list[str]]:
    """
    Score text sentiment using the Hinglish lexicon.

    Returns (score, matched_terms) where score is in [-1, 1].
    Use this to augment XLM-RoBERTa when Hinglish is detected.
    """
    text_lower = text.lower()
    all_terms = get_all_terms()

    matched = []
    total_weight = 0.0

    # Match longer phrases first to avoid partial matches
    sorted_terms = sorted(all_terms.keys(), key=len, reverse=True)
    remaining = text_lower

    for term in sorted_terms:
        if term in remaining:
            weight = all_terms[term]
            matched.append(term)
            total_weight += weight
            # Remove matched term to avoid double-counting
            remaining = remaining.replace(term, "", 1)

    if not matched:
        return 0.0, []

    # Normalize to [-1, 1]
    avg_score = total_weight / len(matched)
    clamped = max(min(avg_score, 1.0), -1.0)

    return round(clamped, 4), matched
