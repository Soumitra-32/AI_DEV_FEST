"""Goal Copilot templates (rules layer).

The plan's Goal Copilot ships curated *shapes* for the five goals people most
often save for — education, an emergency fund, travel, a device and family
support — so a user can start from a realistic target instead of a blank box.

Two rules hold this module together:

* **A template is a shape, not a promise.** ``income_months`` says how many
  months of the user's own income the goal usually costs; the suggested amount is
  then scaled from *their* income, never a national average. The number is an
  assumption and says so in its ``provenance``.
* **The arithmetic is here, not in the LLM.** :func:`resolve` computes the
  suggested goal and the round monthly amount; the router only validates it and
  any LLM may only verbalise it.

Pure data + pure functions over a monthly-income number: no database, no model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

#: Round suggested goals to this many taka, because a coaching target of
#: "৳47,320" reads as a measured promise it is not.
ROUND_TO_BDT = 500.0


@dataclass(frozen=True)
class GoalTemplate:
    """One curated goal shape.

    ``income_months`` is how many months of the user's income the goal typically
    costs (an assumption, documented per goal). ``default_months`` is the horizon
    the card offers first.
    """

    key: str
    label_en: str
    label_bn: str
    description_en: str
    description_bn: str
    default_months: int
    income_months: float
    min_goal_bdt: float
    goal_label_bn: str
    goal_label_en: str
    factors: tuple[str, ...] = field(default_factory=tuple)

    def suggested_goal(self, monthly_income_bdt: float) -> float:
        """Scale the shape to this user's income, floored and rounded.

        ``monthly_income_bdt <= 0`` (a user with no observed income) yields the
        goal's ``min_goal_bdt`` rather than zero, so the card still offers a
        starting shape instead of an empty target.
        """
        income = max(float(monthly_income_bdt), 0.0)
        raw = income * float(self.income_months)
        floored = max(raw, float(self.min_goal_bdt))
        return float(round(floored / ROUND_TO_BDT) * ROUND_TO_BDT)

    def as_payload(self, monthly_income_bdt: float) -> dict[str, Any]:
        """The template plus its user-scaled goal and label, for the contract."""
        goal = self.suggested_goal(monthly_income_bdt)
        months = int(self.default_months)
        monthly = goal / months if months else goal
        return {
            "key": self.key,
            "label_en": self.label_en,
            "label_bn": self.label_bn,
            "description_en": self.description_en,
            "description_bn": self.description_bn,
            "default_months": months,
            "suggested_goal_bdt": goal,
            "goal_label_bn": self.goal_label_bn.format(
                amount=f"{goal:,.0f}", months=months
            ),
            "goal_label_en": self.goal_label_en.format(
                amount=f"{goal:,.0f}", months=months
            ),
            "factors": list(self.factors),
            "provenance": {
                "prediction": (
                    f"A {self.label_en.lower()} goal of about ৳{goal:,.0f} in "
                    f"{months} months is about ৳{monthly:,.0f} a month."
                ),
                "assumption": (
                    f"Sized as {self.income_months:g} month(s) of *your* monthly "
                    "income; the multiplier is a planning assumption, not a "
                    "quoted price."
                ),
                "explanation": self.description_en,
                "source": "template",
            },
        }



#: The five Goal Copilot templates (plan.txt §5).
GOAL_TEMPLATES: tuple[GoalTemplate, ...] = (
    GoalTemplate(
        key="education",
        label_en="Education",
        label_bn="শিক্ষা",
        description_en=(
            "Tuition, admission and exam fees usually arrive in one lump, so the "
            "target is set to cover a term."
        ),
        description_bn=(
            "টিউশন, ভর্তি ও পরীক্ষার ফি সাধারণত একসাথে আসে, তাই লক্ষ্যটি এক টার্ম "
            "কভার করার মতো ধরা হয়।"
        ),
        default_months=6,
        income_months=3.0,
        min_goal_bdt=5_000.0,
        goal_label_bn="{months} মাসে শিক্ষার জন্য ৳{amount} জমাতে চাই",
        goal_label_en="I want to save ৳{amount} in {months} months for education",
        factors=("tuition and admission", "exam and materials", "one term at a time"),
    ),
    GoalTemplate(
        key="emergency_fund",
        label_en="Emergency fund",
        label_bn="আপদকালীন তহবিল",
        description_en=(
            "Three months of spending held aside is what turns one bad week into "
            "an inconvenience instead of a debt."
        ),
        description_bn=(
            "তিন মাসের খরচ আলাদা রাখলে খারাপ একটা সপ্তাহ ঋণ না হয়ে শুধু একটা "
            "অসুবিধা হয়ে থাকে।"
        ),
        default_months=12,
        income_months=3.0,
        min_goal_bdt=5_000.0,
        goal_label_bn="{months} মাসে আপদকালীন তহবিলে ৳{amount} জমাতে চাই",
        goal_label_en="I want to build a ৳{amount} emergency fund in {months} months",
        factors=("months of outflow", "income volatility", "shortfall days"),
    ),
    GoalTemplate(
        key="travel",
        label_en="Travel",
        label_bn="ভ্রমণ",
        description_en=(
            "A trip is a short, lumpy goal: the amount is smaller, but it wants a "
            "fixed travel window rather than an open horizon."
        ),
        description_bn=(
            "ভ্রমণ একটি ছোট, এককালীন লক্ষ্য: টাকা কম লাগে, কিন্তু খোলা সময়সীমার "
            "বদলে নির্দিষ্ট তারিখ লাগে।"
        ),
        default_months=6,
        income_months=1.5,
        min_goal_bdt=3_000.0,
        goal_label_bn="{months} মাসে ভ্রমণের জন্য ৳{amount} জমাতে চাই",
        goal_label_en="I want to save ৳{amount} in {months} months for travel",
        factors=("tickets and fare", "lodging", "fixed travel window"),
    ),
    GoalTemplate(
        key="device",
        label_en="Device",
        label_bn="ডিভাইস",
        description_en=(
            "A phone or a laptop is a replacement you can usually time, which "
            "makes it the easiest goal to spread over a few months."
        ),
        description_bn=(
            "ফোন বা ল্যাপটপ সাধারণত সময় দেখে কেনা যায়, তাই কয়েক মাসে ভাগ করা "
            "সবচেয়ে সহজ লক্ষ্য।"
        ),
        default_months=4,
        income_months=0.8,
        min_goal_bdt=3_000.0,
        goal_label_bn="{months} মাসে ডিভাইস কেনার জন্য ৳{amount} জমাতে চাই",
        goal_label_en="I want to save ৳{amount} in {months} months for a device",
        factors=("device price", "replacement timing", "warranty"),
    ),
    GoalTemplate(
        key="family",
        label_en="Family",
        label_bn="পরিবার",
        description_en=(
            "Support for family — a wedding, a medical bill, a house repair — is "
            "planned around a known event, so the horizon matters as much as the "
            "amount."
        ),
        description_bn=(
            "পরিবারের জন্য খরচ — বিয়ে, চিকিৎসা, ঘর মেরামত — নির্দিষ্ট অনুষ্ঠানকে "
            "কেন্দ্র করে হয়, তাই সময়সীমা টাকার মতোই জরুরি।"
        ),
        default_months=9,
        income_months=2.0,
        min_goal_bdt=5_000.0,
        goal_label_bn="{months} মাসে পারিবারিক খরচের জন্য ৳{amount} জমাতে চাই",
        goal_label_en="I want to save ৳{amount} in {months} months for family needs",
        factors=("event date", "medical and social costs", "one-time expense"),
    ),
)

TEMPLATES_BY_KEY: Mapping[str, GoalTemplate] = {item.key: item for item in GOAL_TEMPLATES}


def template_keys() -> tuple[str, ...]:
    """Every template key, in display order."""
    return tuple(item.key for item in GOAL_TEMPLATES)


def get(key: str) -> GoalTemplate:
    """One template by key (``KeyError`` when it does not exist)."""
    return TEMPLATES_BY_KEY[str(key)]


def resolve(key: str, monthly_income_bdt: float) -> dict[str, Any]:
    """The template with its goal scaled to this user's income."""
    return get(key).as_payload(monthly_income_bdt)


def all_payloads(monthly_income_bdt: float) -> list[dict[str, Any]]:
    """Every template scaled to this user's income, in display order."""
    return [item.as_payload(monthly_income_bdt) for item in GOAL_TEMPLATES]
