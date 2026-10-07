import { describe, expect, it } from "vitest";
import {
  DEFAULT_LANG,
  LANGUAGES,
  formatBDT,
  formatDigits,
  formatDistrict,
  formatFeatureName,
  formatIncomeBand,
  formatInteger,
  formatModelName,
  formatPersona,
  formatStatusBadge,
  formatWrittenDate,
  sanitizeBullet,
  t,
} from "@/lib/i18n";

describe("i18n formatting and translation utilities", () => {
  describe("Constants & metadata", () => {
    it("has DEFAULT_LANG as bn and lists supported languages", () => {
      expect(DEFAULT_LANG).toBe("bn");
      expect(LANGUAGES).toHaveLength(2);
      expect(LANGUAGES[0].code).toBe("bn");
      expect(LANGUAGES[1].code).toBe("en");
    });
  });

  describe("t() translation function", () => {
    it("returns correct translations for en and bn", () => {
      expect(t("en", "appName")).toBe("Shonchoy Copilot");
      expect(t("bn", "appName")).toBe("সঞ্চয় Copilot");
      expect(t("en", "forecast.title")).toBe("14-Day Cash Flow Forecast");
      expect(t("bn", "forecast.title")).toBe("আগামী ১৪ দিনের ক্যাশ ফ্লো");
    });

    it("handles fallback to en when dictionary lookup misses", () => {
      expect(t("bn", "banner.title")).toBe("মনে রাখুন");
      expect(t("en", "banner.title")).toBe("Please note");
    });
  });

  describe("formatInteger & formatBDT", () => {
    it("formats integers with comma separation and Bengali numerals when bn", () => {
      expect(formatInteger(12345, "en")).toBe("12,345");
      expect(formatInteger(12345, "bn")).toBe("১২,৩৪৫");
      expect(formatInteger(null, "en")).toBe("—");
      expect(formatInteger(undefined, "bn")).toBe("—");
      expect(formatInteger(NaN, "en")).toBe("—");
    });

    it("formats BDT amounts with ৳ symbol", () => {
      expect(formatBDT(5000, "en")).toBe("৳5,000");
      expect(formatBDT(5000, "bn")).toBe("৳৫,০০০");
      expect(formatBDT(0, "bn")).toBe("৳০");
      expect(formatBDT(null, "en")).toBe("—");
    });
  });

  describe("formatDigits", () => {
    it("replaces ASCII digits with Bengali numerals when lang is bn", () => {
      expect(formatDigits("Day 14 is 100% fine", "bn")).toBe("Day ১৪ is ১০০% fine");
      expect(formatDigits("Day 14 is 100% fine", "en")).toBe("Day 14 is 100% fine");
      expect(formatDigits("", "bn")).toBe("");
      expect(formatDigits(null as any, "bn")).toBe("");
    });
  });

  describe("formatWrittenDate", () => {
    it("formats ISO date strings to human written dates", () => {
      expect(formatWrittenDate("2026-10-01", "en")).toBe("1 October 2026");
      expect(formatWrittenDate("2026-10-01", "bn")).toBe("১ অক্টোবর ২০২৬");
      expect(formatWrittenDate(null, "en")).toBe("—");
      expect(formatWrittenDate("invalid-date", "en")).toBe("invalid-date");
    });

    it("formats different months correctly in English and Bengali", () => {
      expect(formatWrittenDate("2026-01-15", "en")).toBe("15 January 2026");
      expect(formatWrittenDate("2026-01-15", "bn")).toBe("১৫ জানুয়ারি ২০২৬");
      expect(formatWrittenDate("2026-12-31", "en")).toBe("31 December 2026");
      expect(formatWrittenDate("2026-12-31", "bn")).toBe("৩১ ডিসেম্বর ২০২৬");
    });
  });

  describe("Domain formatters", () => {
    it("formatModelName translates model identifiers", () => {
      expect(formatModelName("LightGBM", "en")).toBe("Our model");
      expect(formatModelName("LightGBM", "bn")).toBe("আমাদের মডেল");
      expect(formatModelName("trailing_average", "bn")).toBe("সাধারণ গড়");
      expect(formatModelName("IsolationForest", "bn")).toBe("অস্বাভাবিক লেনদেন শনাক্তকারী");
      expect(formatModelName("logistic", "bn")).toBe("ধারাবাহিকতা মডেল");
      expect(formatModelName("custom", "en")).toBe("custom");
      expect(formatModelName(null, "en")).toBe("—");
    });

    it("formatFeatureName translates known feature names", () => {
      expect(formatFeatureName("day_of_month", "en")).toBe("Day of the Month");
      expect(formatFeatureName("day_of_month", "bn")).toBe("মাসের কত তারিখ");
      expect(formatFeatureName("weekday", "en")).toBe("Weekday");
      expect(formatFeatureName("is_weekend", "en")).toBe("Weekend");
      expect(formatFeatureName("is_month_end", "bn")).toBe("মাস শেষ");
      expect(formatFeatureName("cash_out_count_per_month", "en")).toBe("Cash-Outs Per Month");
      expect(formatFeatureName("cash_out_count_per_month", "bn")).toBe("মাসে ক্যাশ-আউট সংখ্যা");
      expect(formatFeatureName("cash_out_share_of_outflow", "en")).toBe("Cash-Out Share of Outflow");
      expect(formatFeatureName("cash_out_volume_per_month_bdt", "bn")).toBe("মাসিক ক্যাশ-আউট পরিমাণ");
      expect(formatFeatureName("trailing_14d_outflow", "en")).toBe("14-Day Average Outflow");
      expect(formatFeatureName("fee_share_of_income", "bn")).toBe("আয়ের ফিতে ব্যয় অনুপাত");
      expect(formatFeatureName("shortfall_days_per_month", "en")).toBe("Shortfall Days Per Month");
      expect(formatFeatureName("balance_min_bdt", "bn")).toBe("সর্বনিম্ন ব্যালেন্স");
      expect(formatFeatureName("weekend_spend_ratio", "en")).toBe("Weekend Spend Ratio");
      expect(formatFeatureName("month_end_spend_ratio", "bn")).toBe("মাস শেষের খরচের অনুপাত");
      expect(formatFeatureName("income_days_per_month", "en")).toBe("Income Days Per Month");
      expect(formatFeatureName("income_cv", "bn")).toBe("আয়ের তারতম্য");
      expect(formatFeatureName("spend_cv", "en")).toBe("Spending Variability");
      expect(formatFeatureName(null, "en")).toBe("");
      expect(formatFeatureName("unknown_feature", "en")).toBe("unknown feature");
    });

    it("formatPersona formats persona names", () => {
      expect(formatPersona("shopkeeper", "en")).toBe("Shopkeeper");
      expect(formatPersona("shopkeeper", "bn")).toBe("দোকানদার");
      expect(formatPersona("daily_earner", "bn")).toBe("দৈনিক মজুর");
      expect(formatPersona("salaried", "bn")).toBe("চাকরিজীবী");
      expect(formatPersona("gig_rider", "bn")).toBe("গিগ রাইডার");
      expect(formatPersona("student", "bn")).toBe("শিক্ষার্থী");
      expect(formatPersona("other_persona", "en")).toBe("Other Persona");
      expect(formatPersona(null, "en")).toBe("—");
    });

    it("formatDistrict formats district names", () => {
      expect(formatDistrict("Dhaka", "en")).toBe("Dhaka");
      expect(formatDistrict("Dhaka", "bn")).toBe("ঢাকা");
      expect(formatDistrict("Chattogram", "bn")).toBe("চট্টগ্রাম");
      expect(formatDistrict("Sylhet", "bn")).toBe("সিলেট");
      expect(formatDistrict("Rajshahi", "bn")).toBe("রাজশাহী");
      expect(formatDistrict("Khulna", "bn")).toBe("খুলনা");
      expect(formatDistrict("Barishal", "bn")).toBe("বরিশাল");
      expect(formatDistrict("Rangpur", "bn")).toBe("রংপুর");
      expect(formatDistrict("Mymensingh", "bn")).toBe("ময়মনসিংহ");
      expect(formatDistrict("Cumilla", "bn")).toBe("কুমিল্লা");
      expect(formatDistrict("Bogura", "bn")).toBe("বগুড়া");
      expect(formatDistrict("Unknown", "bn")).toBe("Unknown");
      expect(formatDistrict(null, "en")).toBe("—");
    });

    it("formatIncomeBand formats income bands", () => {
      expect(formatIncomeBand("low", "en")).toBe("Low");
      expect(formatIncomeBand("low", "bn")).toBe("স্বল্প আয়");
      expect(formatIncomeBand("middle", "bn")).toBe("মধ্যম আয়");
      expect(formatIncomeBand("variable", "bn")).toBe("অনিয়মিত আয়");
      expect(formatIncomeBand("affluent", "bn")).toBe("উচ্চ আয়");
      expect(formatIncomeBand("unknown", "en")).toBe("Unknown");
      expect(formatIncomeBand(null, "en")).toBe("—");
    });

    it("formatStatusBadge formats badges", () => {
      expect(formatStatusBadge("Strong", "en")).toBe("Strong");
      expect(formatStatusBadge("Strong", "bn")).toBe("দৃঢ়");
      expect(formatStatusBadge("Building", "bn")).toBe("চলমান");
      expect(formatStatusBadge("Steady", "bn")).toBe("স্থিতিশীল");
      expect(formatStatusBadge("System Computed", "bn")).toBe("আমাদের হিসাবে");
      expect(formatStatusBadge("Rule Verified", "bn")).toBe("✓ যাচাইকৃত");
      expect(formatStatusBadge("Plain Language", "bn")).toBe("সহজ ভাষায়");
      expect(formatStatusBadge("Logistic Regression", "bn")).toBe("ধারাবাহিকতা মডেল");
      expect(formatStatusBadge("Isolation Forest", "bn")).toBe("অস্বাভাবিক লেনদেন শনাক্তকারী");
      expect(formatStatusBadge("LightGBM", "bn")).toBe("আমাদের মডেল");
      expect(formatStatusBadge("Educational", "bn")).toBe("শিক্ষামূলক");
      expect(formatStatusBadge("Custom", "en")).toBe("Custom");
      expect(formatStatusBadge(null, "en")).toBe("");
    });

    it("sanitizeBullet cleans technical variable triggers", () => {
      const b1 = "cash_out_count_per_month >= 3.0 (observed 5.0)";
      expect(sanitizeBullet(b1, "en")).toContain("Cash-out count ~5 times/month");
      expect(sanitizeBullet(b1, "bn")).toContain("মাসে ক্যাশ-আউট সংখ্যা ৫ বার");

      const b2 = "cash_out_share_of_outflow >= 0.25 (observed 0.40)";
      expect(sanitizeBullet(b2, "en")).toContain("40% of spending is in cash");
      expect(sanitizeBullet(b2, "bn")).toContain("খরচের ৪০% ক্যাশে হয়");

      const b3 = "cash_out_volume_per_month_bdt >= 10000.0 (observed 15000.0)";
      expect(sanitizeBullet(b3, "en")).toContain("Monthly cash-out volume");
      expect(sanitizeBullet(b3, "bn")).toContain("মাসিক ক্যাশ-আউট পরিমাণ");

      const b4 = "fee_share_of_income is high";
      expect(sanitizeBullet(b4, "bn")).toContain("আয়ের ফিতে ব্যয় অনুপাত");

      const b5 = "shortfall_days_per_month noticed";
      expect(sanitizeBullet(b5, "bn")).toContain("মাসে ঘাটতির দিন");

      const b6 = "balance_min_bdt low (trigger: rent_payment)";
      expect(sanitizeBullet(b6, "bn")).toContain("সর্বনিম্ন ব্যালেন্স");
      expect(sanitizeBullet(b6, "bn")).toContain("(কারণ:");

      const b7 = "ঐতিহাসিক ৫টি লেনদেন ৩ বার দেখা গেছে";
      expect(sanitizeBullet(b7, "bn")).toBe("পূর্বের ৫টি লেনদেন ৩ বার দেখা গেছে");

      expect(sanitizeBullet("", "en")).toBe("");
    });
  });
});
