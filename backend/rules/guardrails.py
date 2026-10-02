"""Empowerment guardrails (rules layer).

The plan's §6 rules, written as code so nothing depends on the LLM behaving:

* **Intent whitelist** -- user text is never handed to the model as an
  instruction. It is first classified into one of the whitelisted intents
  (:data:`ALLOWED_INTENTS`); anything else becomes ``unknown`` and is answered
  with a template. A prompt-injection attempt ("ignore your instructions...")
  lands in ``unknown`` too, so it can never become a prompt.
* **Banned-output filter** -- :func:`screen` scans *every* generated or
  templated answer and blocks loan offers, urgency language, guaranteed-return
  claims, product promotion, and approve/deny or numeric-score language.
  A blocked answer is replaced by the safe template (:func:`safe_refusal`),
  never patched word by word.
* **Number grounding** -- :func:`ungrounded_numbers` proves the answer invents
  no figure absent from the structured context, the mechanical version of
  "the LLM never invents numbers".

Pure text processing here: no network, no model, no database.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, List, Literal, Sequence, Tuple

Intent = Literal[
    "explain_transactions",
    "forecast",
    "savings_plan",
    "fees",
    "consistency",
    "tips",
    "health_coach",
    "anomalies",
    "tradeoffs",
    "unknown",
]

#: The only intents the assistant may answer. ``unknown`` is in the list
#: precisely because it is the safe sink: it needs no user data.
ALLOWED_INTENTS: Tuple[str, ...] = (
    "explain_transactions",
    "forecast",
    "savings_plan",
    "fees",
    "consistency",
    "tips",
    "health_coach",
    "anomalies",
    "tradeoffs",
    "unknown",
)

#: Tie-break order when two intents score equally (specific before general).
_INTENT_PRIORITY: Tuple[str, ...] = (
    "savings_plan",
    "tradeoffs",
    "fees",
    "anomalies",
    "health_coach",
    "forecast",
    "consistency",
    "tips",
    "explain_transactions",
)

#: Bangla and English surface forms per intent, including the Bangla-English
#: code-mixed way the demo user actually types ("fees", "savings plan").
INTENT_KEYWORDS: dict[str, Tuple[str, ...]] = {
    "savings_plan": (
        "জমাতে", "জমানো", "জমা", "সঞ্চয়", "সঞ্চয়পরিক্লপনা", "পরিকল্পনা", "সাপ্লিমেন্ট",
        "খরচ কমালে", "goal", "save", "saving", "savings", "plan",
    ),
    "fees": (
        "ফি", "ফী", "ফিস", "ক্যাশ আউট", "ক্যাশআউট", "কমিশন", "charge", "charges",
        "fee", "fees", "cash out", "cash-out", "cashout", "extra cost",
    ),
    "forecast": (
        "প্রবাহ", "ভবিষ্যদ্বারা", "ভবিষ্যৎ", "আসতে", "আসবে", "কমবে", "কমে যাবে",
        "প্রেশার", "টাকা আসবে", "কবে", "forecast", "predict", "prediction",
        "upcoming", "next week", "next month", "run out",
    ),
    "consistency": (
        "সিগন্যাল", "সঙ্গতি", "বিশ্বাসযোগ্যতা", "স্কোর", "ক্রেডিট", "ধার নেওয়ার যোগ্যতা",
        "consistency", "signal", "credit", "creditworthiness", "trustworthiness",
        "financial standing",
    ),
    "tips": (
        "টিপস", "টিপ", "পরামর্শ", "পরামর্শ দিন", "কী করব", "কি করব", "সহায়তা",
        "tip", "tips", "advice", "suggest", "suggestion", "help me", "what should i do",
    ),
    "explain_transactions": (
        "লেনদেন", "ট্রানজেকশন", "কী হয়েছে", "কি হয়েছে", "কেন হয়েছে", "খরচের",
        "হিসাব", "ব্যাখ্যা", "transaction", "transactions", "history", "what is this",
        "what happened", "why did", "explain",
    ),
    "health_coach": (
        "অভ্যাস", "আর্থিক স্বাস্থ্য", "স্বাস্থ্য", "কোয়ালিটি", "অবস্থা কেমন",
        "কেমন আছি", "মান আমার", "habit", "habits", "health", "health score",
        "financial health", "how am i doing", "my habits", "coach me",
    ),
    "anomalies": (
        "অস্বাভাবিক", "অদ্ভুত", "আপাত আপাত", "এই লেনদেনটা", "এত বেশি কেন",
        "unusual", "odd", "weird", "strange", "why so much", "big transaction",
        "suspicious", "anomaly", "anomalies",
    ),
    "tradeoffs": (
        "বিকল্প", "কোনটা ভালো", "সুবিধা", "তুলনা", "কমবে না", "কী করলে",
        "option", "options", "alternative", "trade off", "tradeoff", "compare",
        "instead", "which is better",
    ),
}

# ---------------------------------------------------------------------------
# banned-output filter
# ---------------------------------------------------------------------------
#: Phrases that must *survive* the filter because they are the refusal or the
#: banner itself. Masked first, so "we do not offer loans" is not blocked for
#: containing the word "loans".
ALLOWED_PHRASES: Tuple[str, ...] = (
    "not a loan eligibility decision",
    "not a lending decision",
    "not a credit score",
    "this is not a decision",
    "we do not offer loans",
    "we never offer loans",
    "we do not push loans",
    "no loan offers",
    "we never sell your data",
    "no upsell",
    "do nothing",
    "এটি ঋণ পাওয়ার সিদ্ধান্ত নয়",
    "এটি লেন্ডিং সিদ্ধান্ত নয়",
    "এটি ক্রেডিট স্কোর নয়",
    "আমরা ধার প্রস্তাব দিই না",
    "আমরা কোনো ধার চাই না",
    "কোনো ঋণ প্রস্তাব নয়",
    "কোনো আপসেল নয়",
)

#: ``(category, pattern)``. Categories mirror the plan's §6 list.
BANNED_PATTERNS: Tuple[Tuple[str, str], ...] = (
    # --- loan offers -------------------------------------------------------
    ("loan_offer", r"\b(apply for|apply now|take|get|avail|grab|secure)\b[^.\n]{0,40}\bloan\b"),
    ("loan_offer", r"\bloan\s+(offer|offers|application|applications|approval|approved)\b"),
    ("loan_offer", r"\b(offer|provide|arrange|give)\s+(you\s+)?(a\s+|an\s+)?(loan|credit)\b"),
    ("loan_offer", r"\b(borrow|take)\s+money\s+(from|with)\s+(us|our|me)\b"),
    ("loan_offer", r"\bwe\s+(offer|provide|arrange)\s+(loans?|credit|credit\s+limit)\b"),
    ("loan_offer", r"\b(pre-?approved|prequalified)\s+(loan|credit)\b"),
    ("loan_offer", r"(ধার|ঋণ)\s*(নেওয়ার\s*)?(অফার|আবেদন|অনুমোদন|পাওয়া)"),
    ("loan_offer", r"(এখনই|আজই)\s*(ধার|ঋণ)\s*(নিন|নেওয়ার|চাই)"),
    ("loan_offer", r"ধার\s+(নিয়ে|নিতে)\s+(পারবেন|পারো|চাই)"),
    # --- urgency -----------------------------------------------------------
    ("urgency", r"\b(hurry|urgent|urgently|act now|apply today|limited time|last chance|don'?t miss|don'?t wait)\b"),
    ("urgency", r"\b(offer|discount|price|slot|window)\s+ends?\s+(today|tonight|now|soon)\b"),
    ("urgency", r"(জরুরি|জরুরী|দ্রুত করুন|সাথে সাথে|এখনই করুন|সীমিত সময়|শেষ সুযোগ|আজই থাকবে)"),
    # --- guaranteed returns ------------------------------------------------
    ("guaranteed_return", r"\bguarantee[ds]?\b[^.\n]{0,40}\b(return|returns|profit|profits|gain|gains|interest|income)\b"),
    ("guaranteed_return", r"\b(risk[- ]free|zero\s+risk|no\s+risk|100%\s+(safe|profit|guaranteed))\b"),
    ("guaranteed_return", r"\bdouble\s+your\s+money\b"),
    ("guaranteed_return", r"(নিশ্চিত|নিশ্চিতভাবে)\s*(লাভ|মুনাফা|ফেরত|আয়)"),
    ("guaranteed_return", r"ঝুঁ?কিমুক্ত"),
    # --- product promotion / upsell ---------------------------------------
    ("promotion", r"\b(buy|purchase|order|subscribe|upgrade|download)\s+(now|today|the|our)\b"),
    ("promotion", r"\b(buy|purchase|order|book)\s+now\b"),
    ("promotion", r"\b(limited\s+time\s+)?(offer|discount|promo|coupon|voucher|cashback|deal)\b"),
    ("promotion", r"\b(click|tap)\s+(here|the\s+link)\b"),
    ("promotion", r"(এখনই|আজই)\s*(কিনুন|কিনতে|নিন|অর্ডার|সাবস্ক্রাইব)"),
    ("promotion", r"(ছাড়|অফার|প্রচার|বিজ্ঞাপন)"),
    # --- lending / approval language --------------------------------------
    ("lending_decision", r"\byou\s+(are|'re)\s+(approved|rejected|eligible|pre-?approved)\b"),
    ("lending_decision", r"\b(approve|approved)\s+(your|the)\s+(loan|application|credit)\b"),
    ("lending_decision", r"\b(deny|denied|decline|declined)\s+(your|the)\s+(loan|application|credit)\b"),
    ("lending_decision", r"(ঋণ|ধার)\s*(আবেদন)?\s*(অনুমোদিত|মঞ্জুর|বাতিল|অগ্রাহ্য)"),
    ("lending_decision", r"(ঋণ|ধার)\s*পাওয়ার\s*(যোগ্যতা|অনুমোদন)"),
    # --- score / points language ------------------------------------------
    ("score_language", r"\b(credit\s+)?score\s+(of\s+|is\s+|was\s+)?\d{2,4}\b"),
    ("score_language", r"\d+\s*(points?|pts)\b"),
    ("score_language", r"(স্কোর|পয়েন্ট)\s*\d+"),
    ("score_language", r"\d+\s*(পয়েন্ট|pts)\s*(বাড়বে|বেড়েছে|বৃদ্ধি)"),
)

_COMPILED_BANNED: Tuple[Tuple[str, re.Pattern[str]], ...] = tuple(
    (category, re.compile(pattern, re.IGNORECASE)) for category, pattern in BANNED_PATTERNS
)

#: Prompt-injection markers, checked on *user* text only.
INJECTION_PATTERNS: Tuple[str, ...] = (
    r"\bignore\s+(all\s+)?(the\s+)?(previous|prior|above|earlier)\b",
    r"\bdisregard\s+(the\s+)?(system|previous|prior|rules|instructions)\b",
    r"\b(reveal|print|show|repeat|output)\s+(your|the)\s+(system\s+)?(prompt|instructions|rules)\b",
    r"\byou\s+are\s+now\s+(a|an|the)\b",
    r"\bact\s+as\s+(a|an|the)?\s*\w*(advisor|assistant|bank|loan|unrestricted)\b",
    r"\bdeveloper\s+mode\b|\bDAN\s+mode\b|\bjailbreak\b",
    r"\boverride\s+(your|the|all)\s+(rules|guardrails|instructions|policy)\b",
    r"(আগের|আগেরের|পূর্বের)\s*(নিয়ম|নির্দেশনা|ব্যবস্থা)\s*(ভুলে|বাদ দাও|অবহেলা)",
    r"(তোমার|আপনার)\s*(সিস্টেম|সিস্টেম প্রম্পট|নিয়ম)\s*(দেখাও|বলো|প্রকাশ)",
)

_COMPILED_INJECTION: Tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE) for pattern in INJECTION_PATTERNS
)

@dataclass(frozen=True)
class Violation:
    """One banned construct found in a piece of text."""

    category: str
    match: str


@dataclass(frozen=True)
class ScreenResult:
    """Outcome of :func:`screen`; ``clean`` means "safe to show the user"."""

    clean: bool
    violations: Tuple[Violation, ...] = ()

    @property
    def categories(self) -> Tuple[str, ...]:
        return tuple(dict.fromkeys(item.category for item in self.violations))


#: Shown whenever a generated answer is blocked, in both product languages.
#: It says what happened and what we do instead -- never a scolding.
SAFE_REFUSAL: dict[str, str] = {
    "bn": (
        "এই উত্তরটি দেখানো হয়নি, কারণ এতে বিক্রি বা ঋণ চাওয়ার কথা ছিল। "
        "আমরা শুধু টাকা বাঁচানোর পরামর্শ দিই: কমানো, সময় বদলানো, বা পেমেন্টের "
        "মাধ্যম বদলানো। আপনার লেনদেনের হিসাব দেখে সাহায্য করতে পারি।"
    ),
    "en": (
        "That answer was not shown because it read like an advertisement or a "
        "promise of credit. We only give advice that saves money: reduce, delay, "
        "or switch the channel. Ask about your transactions and I can help."
    ),
}


def _normalise(text: str) -> str:
    """Lowercase, NFKC-normalise and collapse whitespace."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(text or "")).lower())


def looks_like_injection(text: str) -> bool:
    """True when user text contains a prompt-injection marker."""
    normalised = _normalise(text)
    return any(pattern.search(normalised) for pattern in _COMPILED_INJECTION)


def screen(text: str) -> ScreenResult:
    """Run the banned-output filter over one piece of text.

    :data:`ALLOWED_PHRASES` are masked out first, so the refusals and the
    "not a loan decision" banner survive the filter that blocks loan offers.
    """
    normalised = _normalise(text)
    if not normalised:
        return ScreenResult(clean=True)
    for phrase in ALLOWED_PHRASES:
        normalised = normalised.replace(_normalise(phrase), " ")
    found: List[Violation] = []
    for category, pattern in _COMPILED_BANNED:
        match = pattern.search(normalised)
        if match:
            found.append(Violation(category=category, match=match.group(0)))
    return ScreenResult(clean=not found, violations=tuple(found))


def screen_all(parts: Iterable[str]) -> ScreenResult:
    """Screen several fields (answer + bullets) and merge the violations."""
    found: List[Violation] = []
    for part in parts:
        found.extend(screen(part).violations)
    return ScreenResult(clean=not found, violations=tuple(found))


def safe_refusal(language: str = "bn") -> str:
    """The neutral replacement text for a blocked or off-intent answer."""
    return SAFE_REFUSAL.get(language, SAFE_REFUSAL["en"])


def is_allowed_intent(intent: str) -> bool:
    """Guard against a caller passing an invented intent string."""
    return intent in ALLOWED_INTENTS


# ---------------------------------------------------------------------------
# intent classification
# ---------------------------------------------------------------------------
def classify_intent(message: str) -> Intent:
    """Map free Bangla/English text onto the intent whitelist.

    Never raises and never returns anything outside :data:`ALLOWED_INTENTS`:
    injection attempts and empty text both fall through to ``unknown``.
    """
    text = _normalise(message)
    if not text or looks_like_injection(text):
        return "unknown"
    scores: dict[str, int] = {}
    for intent, keywords in INTENT_KEYWORDS.items():
        hits = sum(1 for keyword in keywords if keyword in text)
        if hits:
            scores[intent] = hits
    if not scores:
        return "unknown"
    best = max(scores.items(), key=lambda item: (item[1], -_INTENT_PRIORITY.index(item[0])))
    return best[0]  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# number grounding: the mechanical "never invents numbers" check
# ---------------------------------------------------------------------------
_BENGALI_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

#: Trivial counts that carry no claim ("three reasons", "14-day") and so are
#: not required to appear verbatim in the context.
_TRIVIAL_NUMBERS = frozenset(range(0, 25)) | frozenset({30, 40, 50, 60, 100, 365})


def parse_number(text: str) -> str | None:
    """Normalise a number as written by a user or a model to bare digits.

    Handles Bangla digits, thousands separators, the taka sign and decimals.
    """
    if text is None:
        return None
    raw = str(text).translate(_BENGALI_DIGITS).strip()
    raw = raw.replace("৳", "").replace("BDT", "").replace("Tk", "")
    raw = re.sub(r"[,_\s]", "", raw)
    match = re.search(r"-?\d+(?:\.\d+)?", raw)
    if match is None:
        return None
    try:
        number = float(match.group(0))
    except ValueError:
        return None
    if number.is_integer():
        return str(int(number))
    return f"{number:.2f}".rstrip("0").rstrip(".")


def numbers_in(text: str) -> List[str]:
    """Every number in ``text``, normalised (see :func:`parse_number`)."""
    if not text:
        return []
    found: List[str] = []
    for match in re.finditer(r"-?\d[\d,]*(?:\.\d+)?", str(text).translate(_BENGALI_DIGITS)):
        value = parse_number(match.group(0))
        if value is not None:
            found.append(value)
    return found


def _variants(value: str) -> set[str]:
    """Display forms of one number that are still the *same* number.

    A template that shows "৳324" for 323.75, or drops the minus sign when reading
    a negative day out loud, has rounded a real figure — it has not invented
    one. Accepting these variants is what stops the grounding check from firing
    on honest rounding while still catching "9999".
    """
    try:
        number = float(value)
    except ValueError:
        return {value}
    out = {value}
    if number < 0:
        out.add(str(-number) if float(-number).is_integer() else f"{-number:.2f}".rstrip("0").rstrip("."))
    for digits in (0, 1, 2):
        rounded = round(number, digits)
        text = f"{rounded:.0f}" if digits == 0 or float(rounded).is_integer() else f"{rounded:.{digits}f}"
        out.add(text)
        out.add(text.lstrip("-"))
    return out


def _allowed_numbers(context: object) -> set[str]:
    """Every number reachable in a nested context dict/list, plus its variants."""
    allowed: set[str] = set()
    stack: List[object] = [context]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            stack.extend(item.values())
        elif isinstance(item, (list, tuple, set)):
            stack.extend(item)
        elif isinstance(item, bool) or item is None:
            continue
        elif isinstance(item, (int, float)):
            value = parse_number(str(item))
            if value is not None:
                allowed |= _variants(value)
        else:
            # Strings carry dates ("2026-02-28"), labels and ids; every number
            # inside one of those is context the answer may legitimately use.
            for value in numbers_in(str(item)):
                allowed |= _variants(value)
    return allowed


def ungrounded_numbers(text: str, context: object) -> List[str]:
    """Numbers in ``text`` that appear nowhere in ``context``.

    An empty list means every figure in the answer is traceable to the
    structured data -- the mechanical form of the plan's rule that the LLM
    only verbalises structured JSON.
    """
    allowed = _allowed_numbers(context) | {str(value) for value in _TRIVIAL_NUMBERS}
    return [value for value in numbers_in(text) if value not in allowed]


def contains_all(text: str, needles: Sequence[str]) -> bool:
    """Case-insensitive "all of these appear" helper (used by the tests)."""
    haystack = _normalise(text)
    return all(_normalise(needle) in haystack for needle in needles)
