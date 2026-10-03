# Read-Aloud Audit & Professional Register Verification (Phase 5)

## 1. Automated Grep Gate Proof

Command:
```bash
grep -rEn "তুমি|দাও\b|করো\b|দেখো\b|বলো\b|একটু দাঁড়াও|কিছু পাওয়া গেল|Nice\.|Yep\.|Nope\.|gonna|grab |hang on|Basically,|Honestly," web/src
```
Output:
```
(No matches found - exit code 1)
```

Additional check for informal / casual colloquialisms:
```bash
grep -rEn "নাড়বে|গোনা|ক্যাশ গুনে|টান পড়বে না|একটু অপেক্ষা|আরেকটু|টানাটানি" web/src
```
Output:
```
(No matches found - exit code 1)
```

---

## 2. The Professional Register Bar (The Accountant / Doctor Test)
Every string read aloud sounds like a competent professional telling the user the numbers and stopping:
- Complete sentences, explicit grammatical subjects.
- No chatty texting abbreviations, contractions, or slang.
- Strict use of respectful **আপনি** in Bangla (never তুমি, never familiar imperatives).
- Mathematical and regulatory precision preserved verbatim.

---

## 3. High-Stakes Honesty Lock Verifications

### A. Cash-Out Fee vs Bangla QR (0% vs 1.4%)
- **Bank Notice (Too High)**: "Pursuant to BRPD Circular No. 12, retail cashless transactions via Bangla QR interoperable interface bear zero interchange surcharge whereas agent OTC withdrawals incur 1.49% statutory debit."
- **Texting / Casual (Too Low)**: "Skip the fee! Grab Bangla QR at shops for 0% instead of dumping 1.4% at the booth."
- **Target Professional (Shipped)**:
  - **EN**: "Under the 1 October 2026 regulation, merchant payments via Bangla QR incur 0% fee, saving an estimated ৳[amount] per month compared to cash-out."
  - **BN**: "১ অক্টোবর ২০২৬ তারিখের নির্দেশনা অনুযায়ী দোকানে বাংলা কিউআরে অর্থ পরিশোধ করলে ক্যাশ-আউট ফি ০%। এতে মাসে আনুমানিক ৳[amount] সাশ্রয় হতে পারে।"

### B. Forecast Caveat (Estimate vs Guarantee)
- **Bank Notice (Too High)**: "Projections depicted herein represent algorithmic stochastic extrapolations devoid of fiduciary commitment."
- **Texting / Casual (Too Low)**: "It's a guess. Not a promise. Don't bet your lunch on it."
- **Target Professional (Shipped)**:
  - **EN**: "This is an estimate based on your recent transaction patterns, not a guaranteed projection."
  - **BN**: "এটি আপনার সাম্প্রতিক লেনদেনের অভ্যাসের ওপর ভিত্তি করে তৈরি একটি ধারণা, কোনো নিশ্চিত প্রতিশ্রুতি নয়।"

### C. Government Incentive (0.20% Bonus Allocation)
- **Bank Notice (Too High)**: "Statutory fiscal incentive of 20 basis points disbursed under Ministry of Finance auspices accrues strictly to acquiring institutions."
- **Texting / Casual (Too Low)**: "Govt gives 0.20% bonus to Upay/banks, you won't see a dime of it directly."
- **Target Professional (Shipped)**:
  - **EN**: "The 0.20% government incentive goes to the payment service provider, not to the customer."
  - **BN**: "০.২০% সরকারি প্রণোদনা পেমেন্ট সেবা প্রদানকারী প্রতিষ্ঠানের জন্য প্রযোজ্য, সরাসরি গ্রাহকের জন্য নয়।"

---

## 4. Route-by-Route Read-Aloud Verification

| Route | English (Read Aloud) | বাংলা (উচ্চৈঃস্বরে পাঠ) | Evaluation |
|---|---|---|:---:|
| **Home (`/`)** | "This is information only. No funds move without your confirmation." | "আপনার নিশ্চিতকরণ ছাড়া কোনো অর্থ স্থানান্তরিত হয় না।" | Pass (Clear, professional) |
| **Forecast (`/forecast`)** | "Projected inflows, outflows, and net cash balance based on your verified transaction history." | "আপনার যাচাইকৃত লেনদেনের ইতিহাসের ভিত্তিতে আনুমানিক জমা, খরচ এবং মোট উদ্বৃত্তের হিসাব।" | Pass (Accountant tone) |
| **Plan (`/plan`)** | "Calculated from your actual cash surplus after reserving emergency safety funds." | "জরুরি প্রয়োজনের অর্থ আলাদা রাখার পর আপনার প্রকৃত উদ্বৃত্ত থেকে এই হিসাব করা হয়েছে।" | Pass (Clear, responsible) |
| **Spending (`/spending`)** | "Potential monthly fee savings by switching qualifying cash-outs to Bangla QR." | "উপযুক্ত লেনদেনে বাংলা কিউআর ব্যবহার করে মাসিক সম্ভাব্য ফি সাশ্রয়ের হিসাব।" | Pass (Direct, exact) |
| **Tips (`/tips`)** | "Practical cash management tips based on your transaction history." | "আপনার লেনদেনের ইতিহাসের ওপর ভিত্তি করে নগদ অর্থ ব্যবস্থাপনার বাস্তবসম্মত পরামর্শ।" | Pass (Professional coaching) |
| **Signal (`/signal`)** | "Payment consistency evaluation based on your transaction history. Loan decisions rest solely with licensed financial institutions." | "লেনদেনের ইতিহাসের ভিত্তিতে ধারাবাহিকতার মূল্যায়ন। ঋণের সিদ্ধান্ত সম্পূর্ণভাবে অনুমোদিত আর্থিক প্রতিষ্ঠানের ওপর নির্ভরশীল।" | Pass (Statutory clarity) |
| **Metrics (`/metrics`)** | "Model performance metrics and regulatory evaluation notes." | "মডেলের কার্যকারিতা পরিমাপ এবং প্রাতিষ্ঠানিক নীতিমালার বিবরণ।" | Pass (Objective science) |

All 7 routes pass the Read-Aloud Register Verification.
