"""Template explanations in Bangla and English (built *before* the LLM).

Two jobs:

1. **The demo never breaks.** Every whitelisted intent has a deterministic
   answer built only from the structured context, so ``/chat-explain`` returns
   a useful Bangla/English explanation with no API key, no network and no
   model in the loop.
2. **The LLM is optional, the words are not.** ``genai.explain`` calls
   :func:`render` first and only replaces it when the model produced something
   that passes the guardrails *and* the number-grounding check. If it did not,
   these templates are what the user sees.

Every sentence is written to be readable aloud by someone who cannot see the
numbers on screen, and every figure is read out of the context dict -- the
templates never compute anything, which is why the LLM layer can safely be
added on top.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence

from backend.rules import guardrails

#: Bangla digits the UI renders; templates format through :func:`taka`.
_BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")

#: The one-line promise every answer repeats. "Not a decision" is a guardrail
#: requirement, not marketing.
BANNER_BN = "এটি ঋণ পাওয়ার সিদ্ধান্ত নয়। কোনো কিছু কেনা বা ধার নেওয়ার পরামর্শ দেওয়া হয় না।"
BANNER_EN = (
    "This is not a loan eligibility decision. We never suggest buying anything "
    "or taking a loan."
)

#: Shown when the user says something outside the whitelist.
OFF_INTENT_BN = (
    "আমি শুধু আপনার লেনদেন, ক্যাশ-ফ্লো, সঞ্চয়ের পরিকল্পনা, ফি, ধার consistency সিগন্যাল "
    "ও টিপস নিয়ে সাহায্য করতে পারি।"
)
OFF_INTENT_EN = (
    "I can help with your transactions, cash flow, savings plan, fees, your "
    "consistency signal and money tips."
)


@dataclass(frozen=True)
class TemplateAnswer:
    """A ready-to-serve explanation in one language."""

    answer: str
    bullets: list[str] = field(default_factory=list)

    def parts(self) -> list[str]:
        """Answer + bullets, so they can be screened and grounded in one pass."""
        return [self.answer, *self.bullets]


def taka(amount: float | int | None, language: str = "en") -> str:
    """Format a taka amount the way each language writes it.

    ``taka(5000, "bn")`` -> "৳৫,০০০" (Bangla digits), ``taka(5000, "en")`` ->
    "৳5,000". Both keep the taka sign: a bare number next to "months" reads as
    months.
    """
    if amount is None:
        return "0"
    value = float(amount)
    grouped = f"{int(round(abs(value))):,}"
    sign = "-" if value < 0 else ""
    return f"{sign}৳{grouped.translate(_BN_DIGITS)}" if language == "bn" else f"{sign}৳{grouped}"


def _get(context: Mapping[str, Any] | None, *path: str, default: Any = None) -> Any:
    """Read a nested key without raising on a missing section."""
    node: Any = context or {}
    for key in path:
        if not isinstance(node, Mapping) or key not in node:
            return default
        node = node[key]
    return default if node is None else node


def _pressure_phrase(dates: Sequence[Any], language: str) -> str:
    shown = ", ".join(str(item) for item in list(dates or [])[:3])
    if not shown:
        return (
            "এই ১৪ দিনে কোনো চাপের দিন নেই।"
            if language == "bn"
            else "No pressure day in the next 14 days."
        )
    return f"চাপের দিন: {shown}।" if language == "bn" else f"Pressure days: {shown}."


def _savings_plan(context: Mapping[str, Any], language: str) -> TemplateAnswer:
    """Explain the solver verdict: feasible or not, plus the do-nothing cost."""
    plan = _get(context, "plan", default={})
    if not plan:
        return _empty("savings_plan", language)
    goal = _get(plan, "goal_bdt", default=0.0)
    months = _get(plan, "months", default=0)
    required = _get(plan, "required_monthly_bdt", default=0.0)
    feasible_monthly = _get(plan, "feasible_monthly_bdt", default=0.0)
    buffer_bdt = _get(plan, "safety_buffer_bdt", default=0.0)
    surplus = _get(plan, "forecasted_surplus_bdt", default=0.0)
    feasible = bool(_get(plan, "feasible", default=False))
    do_nothing_cost = _get(plan, "do_nothing", "estimated_cost_bdt", default=0.0)
    pressure = _pressure_phrase(_get(plan, "pressure_days", default=[]), language)
    if language == "bn":
        verdict = "পরিকল্পনাটি সম্ভব" if feasible else "পরিকল্পনাটি এখনই সম্ভব নয়"
        answer = (
            f"{verdict}: {taka(goal, language)} জমাতে {months} মাস লাগবে, মাসে "
            f"{taka(required, language)}। আপনার সম্ভাব্য অতিরিক্ত টাকা {taka(surplus, language)}, "
            f"তার থেকে {taka(buffer_bdt, language)} নিরাপত্তা বালতি রেখে জমানোর জায়গা "
            f"{taka(feasible_monthly, language)}। {pressure}"
        )
        bullets = [
            f"প্রতি মাসে জমাতে হবে {taka(required, language)}",
            f"বালতি রাখার পরে জমানোর সুযোগ {taka(feasible_monthly, language)}",
            f"কিছু না বদলালে {months} মাসে ফি হিসেবে লাগবে প্রায় {taka(do_nothing_cost, language)}",
        ]
        if not feasible:
            bullets.append("কমিয়ে, সময় বাড়িয়ে, বা কম ক্যাশ-আউট করে পরিকল্পনাটি ঠিক করা যায়")
        bullets.append(BANNER_BN)
        return TemplateAnswer(answer=answer, bullets=bullets)
    verdict = "The plan fits" if feasible else "The plan does not fit as stated"
    answer = (
        f"{verdict}: {taka(goal, language)} in {months} months needs "
        f"{taka(required, language)} a month. Your forecast surplus is "
        f"{taka(surplus, language)}, and after keeping a {taka(buffer_bdt, language)} "
        f"safety buffer there is {taka(feasible_monthly, language)} a month to set "
        f"aside. {pressure}"
    )
    bullets = [
        f"Save about {taka(required, language)} each month",
        f"Room to save after the buffer: {taka(feasible_monthly, language)}",
        f"Change nothing and fees over {months} months: about {taka(do_nothing_cost, language)}",
    ]
    if not feasible:
        bullets.append("Free up monthly cash, take longer, or lower the goal to close the gap")
    bullets.append(BANNER_EN)
    return TemplateAnswer(answer=answer, bullets=bullets)


def _forecast(context: Mapping[str, Any], language: str) -> TemplateAnswer:
    """Explain the 14-day outlook and the month-end squeeze."""
    outlook = _get(context, "forecast", default={})
    if not outlook:
        return _empty("forecast", language)
    monthly_net = _get(outlook, "monthly_net", default=0.0)
    monthly_in = _get(outlook, "monthly_inflow", default=0.0)
    monthly_out = _get(outlook, "monthly_outflow", default=0.0)
    monthly_fees = _get(outlook, "monthly_fees", default=0.0)
    balance = _get(outlook, "opening_balance_bdt", default=0.0)
    horizon = len(_get(outlook, "days", default=[])) or 14
    pressure = _pressure_phrase(_get(outlook, "pressure_days", default=[]), language)
    drivers = _get(outlook, "drivers", default=[]) or []
    driver_lines = [str(item["detail"]) for item in drivers[:2] if item.get("detail")]
    if language == "bn":
        answer = (
            f"আগামী {horizon} দিনে মোট আয়ের ধারণা {taka(monthly_in, language)}, খরচের ধারণা "
            f"{taka(monthly_out, language)}, ফি {taka(monthly_fees, language)}। এখন ওয়ালেটে "
            f"{taka(balance, language)} থাকলে মাসিক ফলাফল প্রায় {taka(monthly_net, language)}। {pressure}"
        )
        bullets = [
            f"এখন ব্যালেন্স: {taka(balance, language)}",
            f"ফি প্রতি মাসে প্রায় {taka(monthly_fees, language)}",
            *driver_lines,
            BANNER_BN,
        ]
        return TemplateAnswer(answer=answer, bullets=bullets)
    answer = (
        f"Over the next {horizon} days the model expects about "
        f"{taka(monthly_in, language)} in, {taka(monthly_out, language)} out and "
        f"{taka(monthly_fees, language)} in fees. Starting from "
        f"{taka(balance, language)}, that is roughly {taka(monthly_net, language)} a "
        f"month. {pressure}"
    )
    bullets = [
        f"Balance today: {taka(balance, language)}",
        f"Fees run about {taka(monthly_fees, language)} a month",
        *driver_lines,
        BANNER_EN,
    ]
    return TemplateAnswer(answer=answer, bullets=bullets)


def _fees(context: Mapping[str, Any], language: str) -> TemplateAnswer:
    """Explain the avoidable cash-out fee, computed by the rules layer."""
    fees = _get(context, "fees", default={})
    if not fees:
        return _empty("fees", language)
    count = int(_get(fees, "cash_out_count", default=0))
    volume = _get(fees, "cash_out_volume_bdt", default=0.0)
    paid = _get(fees, "fee_paid_bdt", default=0.0)
    alternative = str(_get(fees, "alternative_channel", default="app transfer"))
    alt_fee = _get(fees, "alternative_fee_bdt", default=0.0)
    saving = _get(fees, "potential_saving_bdt", default=0.0)
    adoption = str(_get(fees, "adoption_range", default="20%-50%"))
    if language == "bn":
        answer = (
            f"শেষ ৩০ দিনে {count} বার ক্যাশ-আউটে {taka(volume, language)} নিয়েছেন, ফি দিয়েছেন "
            f"{taka(paid, language)}। একই টাকা {alternative}-এ পাঠালে ফি {taka(alt_fee, language)} "
            f"হতো, অর্থাৎ প্রায় {taka(saving, language)} বাঁচত। হিসাবটি অনুমান {adoption} "
            "ব্যবহার করে করা — পরিমাপ করা ফলাফল নয়।"
        )
        bullets = [
            f"{alternative} দিয়ে একই পরিমাণ পাঠালে ফি প্রায় {taka(alt_fee, language)}",
            f"সম্ভাব্য সাশ্রয় {taka(saving, language)} (ধরে নেওয়া অনুমান: {adoption})",
            "কমানো, সময় বদলানো, বা মাধ্যম বদলানো — এই তিনটিই আমরা পরামর্শ দিই",
            BANNER_BN,
        ]
        return TemplateAnswer(answer=answer, bullets=bullets)
    answer = (
        f"In the last 30 days you took out cash {count} times, {taka(volume, language)} "
        f"in total, and paid {taka(paid, language)} in fees. Sending the same money by "
        f"{alternative} would cost about {taka(alt_fee, language)}, so roughly "
        f"{taka(saving, language)} stays in your pocket. That uses an assumed adoption "
        f"of {adoption} — an assumption, not a measured result."
    )
    bullets = [
        f"The same amount by {alternative} costs about {taka(alt_fee, language)}",
        f"Potential saving {taka(saving, language)} (assumed adoption {adoption})",
        "We only ever suggest reduce, delay or switch",
        BANNER_EN,
    ]
    return TemplateAnswer(answer=answer, bullets=bullets)


def _consistency(context: Mapping[str, Any], language: str) -> TemplateAnswer:
    """Explain the consistency band -- never a score, never a decision."""
    signal = _get(context, "signal", default={})
    if not signal:
        return _empty("consistency", language)
    band = str(_get(signal, "band", default="Building"))
    factors = _get(signal, "factors", default=[]) or []
    improvements = _get(signal, "improvements", default=[]) or []
    reasons = [str(item["plain_language"]) for item in factors[:3] if item.get("plain_language")]
    if language == "bn":
        answer = (
            f"আপনার consistency সিগন্যাল এখন “{band}”। এটি কোনো স্কোর নয় এবং ঋণের যোগ্যতার "
            f"সিদ্ধান্ত নয় — এটি শুধু আপনার নিজের লেনদেনের ধারার ধারণা।"
        )
        bullets = [*reasons, *[f"উন্নত করতে: {item}" for item in improvements[:2]], BANNER_BN]
        return TemplateAnswer(answer=answer, bullets=bullets[:5])
    answer = (
        f"Your consistency signal is “{band}”. This is not a score and not a loan "
        f"eligibility decision — it is only a reading of your own transaction pattern."
    )
    bullets = [*reasons, *[f"What would help: {item}" for item in improvements[:2]], BANNER_EN]
    return TemplateAnswer(answer=answer, bullets=bullets[:5])


def _tips(context: Mapping[str, Any], language: str) -> TemplateAnswer:
    """List behaviour-triggered tips, each with the trigger that chose it."""
    tips = _get(context, "tips", default=[]) or []
    if not tips:
        return _empty("tips", language)
    if language == "bn":
        answer = (
            f"আপনার আচরণের উপর ভিত্তি করে {len(tips)}টি টিপ বাছাই করা হয়েছে। "
            "প্রতিটি টিপের সাথে কারণটিও দেওয়া আছে।"
        )
        bullets = [
            f"{item.get('title_bn') or item.get('title')}: "
            f"{item.get('body_bn') or item.get('body')} (কারণ: {item.get('trigger')})"
            for item in tips[:3]
        ]
        bullets.append(BANNER_BN)
        return TemplateAnswer(answer=answer, bullets=bullets)
    answer = (
        "These tips were chosen from your own behaviour. Each one shows the "
        "trigger that selected it."
    )
    bullets = [
        f"{item.get('title')}: {item.get('body')} (trigger: {item.get('trigger')})"
        for item in tips[:3]
    ]
    bullets.append(BANNER_EN)
    return TemplateAnswer(answer=answer, bullets=bullets)


def _transactions(context: Mapping[str, Any], language: str) -> TemplateAnswer:
    """Summarise the recent transactions in words, from the aggregated context."""
    summary = _get(context, "transactions", default={})
    if not summary:
        return _empty("explain_transactions", language)
    count = int(_get(summary, "count", default=0))
    inflow = _get(summary, "inflow_bdt", default=0.0)
    outflow = _get(summary, "outflow_bdt", default=0.0)
    fees = _get(summary, "fee_bdt", default=0.0)
    shortfall = int(_get(summary, "shortfall_events", default=0))
    top = _get(summary, "top_categories", default=[]) or []
    top_text = ", ".join(
        f"{item.get('label')} {taka(item.get('amount_bdt', 0.0), language)}" for item in top[:3]
    )
    # The story sentence (use 4): a measured share, never an impression.
    pattern = _get(summary, "pattern", default={}) or {}
    cash_out_count = int(_get(pattern, "cash_out_count", default=0))
    month_end = float(_get(pattern, "month_end_cash_out_share_pct", default=0.0))
    peak = _get(pattern, "peak_weekday")
    if cash_out_count and month_end >= 50.0:
        story_en = (
            f" Of your {cash_out_count} cash-outs, {month_end:g}% happened in the last third "
            "of the month."
        )
        story_bn = (
            f" আপনার {cash_out_count} টি ক্যাশ-আউটের {month_end:g}% মাসের শেষ তৃতীয়াংশে হয়েছে।"
        )
    elif cash_out_count:
        story_en = f" You took out cash {cash_out_count} times in this window."
        story_bn = f" এই সময়সীমায় আপনি {cash_out_count} বার ক্যাশ নিয়েছেন।"
    else:
        story_en, story_bn = " No cash-outs in this window.", " এই সময়সীমায় ক্যাশ-আউট নেই।"
    if peak:
        story_en += f" Most fall on a {peak}."
        story_bn += f" বেশিরভাগ হয় {peak}।"
    tail_en = f" The largest categories were: {top_text}.{story_en}" if top_text else story_en
    tail_bn = f" সবচেয়ে বেশি খরচ: {top_text}।{story_bn}" if top_text else story_bn
    if language == "bn":
        answer = (
            f"শেষ ৩০ দিনে {count} টি লেনদেন হয়েছে। মোট আয় {taka(inflow, language)}, মোট খরচ "
            f"{taka(outflow, language)}, ফি {taka(fees, language)}।{tail_bn}"
        )
        bullets = [
            f"ব্যালেন্স ঘাটতির দিন: {shortfall}",
            "সব হিসাব আপনার নিজের লেনদেন থেকে করা, অন্যের থেকে নয়",
            BANNER_BN,
        ]
        return TemplateAnswer(answer=answer, bullets=bullets)
    answer = (
        f"In the last 30 days there were {count} transactions: "
        f"{taka(inflow, language)} in, {taka(outflow, language)} out and "
        f"{taka(fees, language)} in fees.{tail_en}"
    )
    bullets = [
        f"Days the wallet came up short: {shortfall}",
        "Every figure comes from your own transactions, not anyone else's",
        BANNER_EN,
    ]
    return TemplateAnswer(answer=answer, bullets=bullets)


def _health_coach(context: Mapping[str, Any], language: str) -> TemplateAnswer:
    """A friendly habits summary built from the health-score components."""
    health = _get(context, "health", default={})
    if not health:
        return _empty("health_coach", language)
    band = str(_get(health, "band", default="Building"))
    components = _get(health, "components", default=[]) or []
    earned = [item for item in components if float(item.get("share", 0.0)) >= 0.7]
    weak = [item for item in components if float(item.get("share", 0.0)) <= 0.3]
    helpers = [str(item.get("detail_bn") or item.get("detail_en")) for item in earned[:2]]
    costs = [str(item.get("detail_bn") or item.get("detail_en")) for item in weak[:2]]
    if language == "bn":
        answer = (
            f"আপনার আর্থিক অভ্যাসের অবস্থা এখন “{band}”। নিচে যেসব অভ্যাস আপনাকে এগিয়ে "
            "নিচ্ছে, আর কোনটিতে সবচেয়ে বেশি টাকা চলে যাচ্ছে।"
        )
        bullets = [*helpers, *[f"এখানে সবচেয়ে বেশি লাভ: {item}" for item in costs], BANNER_BN]
        return TemplateAnswer(answer=answer, bullets=bullets[:5])
    answer = (
        f"Your money habits are currently “{band}”. Below are the habits helping you, "
        "and the one costing you the most."
    )
    bullets = [*helpers, *[f"Worth the most attention: {item}" for item in costs], BANNER_EN]
    return TemplateAnswer(answer=answer, bullets=bullets[:5])


def _anomalies(context: Mapping[str, Any], language: str) -> TemplateAnswer:
    """Explain the flagged payments: unusual for this user, never an accusation."""
    anomalies = _get(context, "anomalies", default={})
    if not anomalies:
        return _empty("anomalies", language)
    items = _get(anomalies, "items", default=[]) or []
    saving = _get(anomalies, "potential_saving_bdt", default=0.0)
    count = int(_get(anomalies, "flagged_count", default=len(items)))
    reasons = [str(item.get("reason")) for item in items[:3] if item.get("reason")]
    if language == "bn":
        answer = (
            f"আপনার সাম্প্রতিক {count} টি পেমেন্ট আপনার নিজের স্বাভাবিকের তুলনায় অস্বাভাবিক। "
            "এটি কোনো প্রতারণার প্রমাণ নয় — শুধু আপনার নিজের ইতিহাসের সাথে মিলিয়ে দেখা।"
        )
        bullets = [*reasons, f"ক্যাশ-আউট বদলালে সম্ভাব্য সাশ্রয়: {taka(saving, language)}", BANNER_BN]
        return TemplateAnswer(answer=answer, bullets=bullets[:5])
    answer = (
        f"{count} of your recent payments look unusual against your own usual pattern. "
        "This is not evidence of fraud — it is your own history compared with itself."
    )
    bullets = [*reasons, f"Possible saving by switching channel: {taka(saving, language)}", BANNER_EN]
    return TemplateAnswer(answer=answer, bullets=bullets[:5])


def _tradeoffs(context: Mapping[str, Any], language: str) -> TemplateAnswer:
    """Describe the solver's options and what each one costs."""
    plan = _get(context, "plan", default={}) or _get(context, "tradeoffs", default={})
    options = _get(plan, "trade_offs", default=[]) or _get(plan, "tradeoffs", default=[]) or []
    if not options:
        return _empty("tradeoffs", language)
    inaction = _get(plan, "do_nothing", default={}) or {}
    cost = _get(inaction, "estimated_cost_bdt", default=0.0)
    descriptions = [str(item.get("description")) for item in options[:3] if item.get("description")]
    if language == "bn":
        answer = "সমাধানটি ইতিমধ্যে হিসাব করা হয়েছে। নিচে প্রতিটি বিকল্প এবং তার খরচ:"
        bullets = [*descriptions, f"কিছু না করলে আনুমানিক খরচ: {taka(cost, language)}", BANNER_BN]
        return TemplateAnswer(answer=answer, bullets=bullets[:5])
    answer = "These options were already worked out for you. Here is each one and its cost:"
    bullets = [*descriptions, f"Doing nothing costs about: {taka(cost, language)}", BANNER_EN]
    return TemplateAnswer(answer=answer, bullets=bullets[:5])


def _empty(intent: str, language: str) -> TemplateAnswer:
    """What to say when the context for an intent is unavailable."""
    if language == "bn":
        return TemplateAnswer(
            answer="এই তথ্যের জন্য আরও কিছু লেনদেন দরকার। যা আছে তা দিয়েই সাহায্য করতে পারি।",
            bullets=[BANNER_BN],
        )
    return TemplateAnswer(
        answer="I need a few more transactions for that. I can still help with what I have.",
        bullets=[BANNER_EN],
    )


def _unknown(language: str) -> TemplateAnswer:
    """The off-intent answer: what we do, never a scolding."""
    if language == "bn":
        return TemplateAnswer(answer=OFF_INTENT_BN, bullets=[BANNER_BN])
    return TemplateAnswer(answer=OFF_INTENT_EN, bullets=[BANNER_EN])


#: intent -> renderer. Every whitelisted intent is present, which the tests
#: assert, so a new intent can never ship without a template.
RENDERERS = {
    "savings_plan": _savings_plan,
    "forecast": _forecast,
    "fees": _fees,
    "consistency": _consistency,
    "tips": _tips,
    "explain_transactions": _transactions,
    "health_coach": _health_coach,
    "anomalies": _anomalies,
    "tradeoffs": _tradeoffs,
}


def render(intent: str, context: Mapping[str, Any] | None, language: str = "bn") -> TemplateAnswer:
    """Build the deterministic answer for one intent in one language.

    Unknown intents and unknown languages fall back to ``unknown``/English
    rather than raising: this function is the demo's floor.
    """
    language = "bn" if str(language).lower().startswith("bn") else "en"
    if not guardrails.is_allowed_intent(intent) or intent == "unknown":
        return _unknown(language)
    renderer = RENDERERS.get(intent)
    return renderer(context or {}, language) if renderer else _unknown(language)


def both_languages(intent: str, context: Mapping[str, Any] | None) -> dict[str, TemplateAnswer]:
    """Render one intent in both product languages (the API returns both)."""
    return {
        "bn": render(intent, context, "bn"),
        "en": render(intent, context, "en"),
    }


# ---------------------------------------------------------------------------
# goal parsing: "৬ মাসে ৳৩০,০০০ জমাতে চাই"
# ---------------------------------------------------------------------------
_GOAL_HINT = re.compile(r"(save|জমা|জমানো|জমাতে|goal|টাকা)", re.IGNORECASE)
_MONTH_PATTERN = re.compile(r"(\d+)\s*(month|months|মাস|মাসে|মাসের)")

#: Bounds mirror ``SavingsPlanRequest`` so a parsed goal always validates.
MIN_MONTHS = 1
MAX_MONTHS = 36


@dataclass(frozen=True)
class GoalRequest:
    """A savings goal parsed out of free text, when one is present."""

    goal_bdt: Optional[float] = None
    months: Optional[int] = None

    @property
    def is_complete(self) -> bool:
        """True when the solver has both halves it needs."""
        return self.goal_bdt is not None and self.months is not None


def parse_goal(message: str) -> GoalRequest:
    """Extract a goal amount and horizon from a Bangla or English sentence.

    A partial request returns the half that was found and ``None`` for the
    other, so the caller asks one follow-up question instead of inventing a
    horizon.
    """
    normalised = str(message or "").translate(str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")).lower()

    goal: Optional[float] = None
    # Prefer the largest taka-marked number: "৳৩০,০০০" beats a stray month count.
    for match in re.finditer(r"৳\s*([\d,]+(?:\.\d+)?)", normalised):
        parsed = guardrails.parse_number(match.group(1))
        if parsed is None:
            continue
        candidate = float(parsed)
        if candidate > 0 and (goal is None or candidate > goal):
            goal = candidate
    if goal is None and _GOAL_HINT.search(normalised):
        # No taka sign: only trust a bare number when a goal word is present,
        # so "6 months" is never read as a 6 taka goal.
        plausible = [
            float(value)
            for value in guardrails.numbers_in(normalised)
            if value is not None and float(value) >= 500
        ]
        if plausible:
            goal = max(plausible)

    months: Optional[int] = None
    month_match = _MONTH_PATTERN.search(normalised)
    if month_match:
        parsed = guardrails.parse_number(month_match.group(1))
        if parsed is not None and MIN_MONTHS <= float(parsed) <= MAX_MONTHS:
            months = int(float(parsed))
    return GoalRequest(goal_bdt=goal, months=months)


def missing_goal_prompt(goal: GoalRequest, language: str) -> TemplateAnswer:
    """Ask for the one half of the goal that is missing (never guess it)."""
    if goal.months is None and goal.goal_bdt is not None:
        if language == "bn":
            return TemplateAnswer(
                answer=(
                    f"{taka(goal.goal_bdt, language)} জমাতে চাচ্ছেন — কত মাসে? "
                    f"{MIN_MONTHS} থেকে {MAX_MONTHS} মাসের মধ্যে বলুন।"
                ),
                bullets=[BANNER_BN],
            )
        return TemplateAnswer(
            answer=(
                f"You want to save {taka(goal.goal_bdt, language)} — in how many months? "
                f"({MIN_MONTHS} to {MAX_MONTHS})"
            ),
            bullets=[BANNER_EN],
        )
    if goal.months is not None and goal.goal_bdt is None:
        if language == "bn":
            return TemplateAnswer(
                answer=f"{goal.months} মাসের জন্য — কত টাকা জমাতে চান?",
                bullets=[BANNER_BN],
            )
        return TemplateAnswer(
            answer=f"Over {goal.months} months — how much taka do you want to save?",
            bullets=[BANNER_EN],
        )
    return _unknown(language)

