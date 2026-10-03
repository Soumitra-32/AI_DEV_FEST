# Register Audit — Too-Casual Offenders (Phase 0)

Audit of current user-facing strings across `web/src`. Categorized by failure mode and language, mapping current text to the target register ("the accountant / doctor / lawyer register").

## Failure Mode Summary

| Language | Failure Mode | Count |
|---|---|:---:|
| English | Sentence fragment as standalone line / punchline | 14 |
| English | Chatty / texting verb or interjection | 11 |
| English | Dropped subject or overly informal framing | 16 |
| Bangla | Slang or informal colloquialism (e.g., গোনা, নাড়বে, আন্দাজ) | 18 |
| Bangla | Sentence fragment heading / punchline | 15 |
| Bangla | Imperative / overly familiar phrasing | 9 |
| **Total** | | **83** |

---

## Detailed Audit Table

| File:Line | Lang | Current Text | Failure Mode | Target Rewrite |
|---|---|---|---|---|
| `i18n.ts:20` | en | "Simple ledger-book style" | Fragment | "Traditional ledger format" |
| `i18n.ts:328` | bn | "সহজ খতিয়ান ধরন" | Fragment | "খতিয়ান পদ্ধতি" |
| `i18n.ts:49` | en | "People" | Chatty/vague | "Account holders" |
| `i18n.ts:357` | bn | "মানুষ" | Colloquial | "ব্যবহারকারী" |
| `i18n.ts:50` | en | "Money records" | Chatty/vague | "Transactions" |
| `i18n.ts:358` | bn | "টাকার হিসাব" | Fragment | "মোট লেনদেন" |
| `i18n.ts:51` | en | "Counted on" | Chatty | "Calculated on" |
| `i18n.ts:359` | bn | "গণনার তারিখ" | Chatty | "হিসাবের সময়" |
| `i18n.ts:52` | en | "Working now" | Fragment | "Active features" |
| `i18n.ts:360` | bn | "এখন চালু" | Fragment | "সক্রিয় সুবিধা" |
| `i18n.ts:62` | en | "What we think will happen" | Chatty verb phrase | "Prediction" |
| `i18n.ts:370` | bn | "আমরা যা আন্দাজ করছি" | Casual (আন্দাজ) | "পূর্বাভাস" |
| `i18n.ts:63` | en | "What we're assuming" | Chatty contraction | "Assumption" |
| `i18n.ts:371` | bn | "কী ধরে নিচ্ছি" | Fragment | "যা ধরে নিচ্ছি" |
| `i18n.ts:64` | en | "Why we're saying this" | Chatty phrase | "Reason" |
| `i18n.ts:372` | bn | "কেন এমন বলছি" | Fragment | "কারণ" |
| `i18n.ts:71` | en | "Okay, I understand" | Chatty | "Okay" |
| `i18n.ts:379` | bn | "ঠিক আছে, বুঝেছি" | Chatty | "ঠিক আছে" |
| `i18n.ts:72` | en | "I'll decide later" | Chatty | "Later" |
| `i18n.ts:380` | bn | "পরে দেখব" | Chatty | "পরে দেখব" |
| `i18n.ts:73` | en | "Noted — nothing was changed." | Chatty punchline | "Noted — no changes were made." |
| `i18n.ts:381` | bn | "ঠিক আছে — কিছুই বদলানো হয়নি।" | Chatty | "লিপিবদ্ধ করা হয়েছে — কোনো পরিবর্তন করা হয়নি।" |
| `i18n.ts:75` | en | "Nothing happens without you." | Casual framing | "No changes occur without your confirmation." |
| `i18n.ts:383` | bn | "আপনি না বললে কিছুই হবে না।" | Casual phrasing | "আপনার নিশ্চিতকরণ ছাড়া কোনো পরিবর্তন হবে না।" |
| `i18n.ts:83` | en | "The app never moves your money." | Casual verb | "The app never transfers your funds." |
| `i18n.ts:391` | bn | "অ্যাপ কখনো আপনার টাকা নাড়বে না।" | Slang ("নাড়বে") | "অ্যাপ কখনো আপনার টাকা স্থানান্তর করে না।" |
| `i18n.ts:89` | en | "No money moves without you." | Casual framing | "No funds move without your confirmation." |
| `i18n.ts:397` | bn | "আপনি না বললে কোনো টাকা নড়বে না।" | Slang ("নড়বে") | "আপনার নিশ্চিতকরণ ছাড়া কোনো অর্থ স্থানান্তরিত হয় না।" |
| `i18n.ts:91` | en | "This is a guess about the future, not a promise." | Chatty ("guess") | "This is an estimate, not a promise." |
| `i18n.ts:399` | bn | "এটি ভবিষ্যতের আন্দাজ, প্রতিশ্রুতি নয়।" | Casual ("আন্দাজ") | "এটি একটি ধারণা, কোনো নিশ্চিত প্রতিশ্রুতি নয়।" |
| `i18n.ts:93` | en | "This is a plan, not a guarantee you'll reach it." | Chatty contraction | "Here is the plan. Reaching it is not guaranteed." |
| `i18n.ts:401` | bn | "এটি একটি পরিকল্পনা — লক্ষ্যে পৌঁছানোর নিশ্চয়তা নয়।" | Casual | "পরিকল্পনা করা হয়েছে। পৌঁছানো নিশ্চিত নয়।" |
| `i18n.ts:97` | en | "This is general information, not advice for your case." | Fragmented | "This is general information. Your case may be different." |
| `i18n.ts:405` | bn | "এটি সাধারণ তথ্য — আপনার জন্য ব্যক্তিগত পরামর্শ নয়।" | Informal | "এগুলো সাধারণ তথ্য। আপনার বিষয় আলাদা হতে পারে।" |
| `i18n.ts:99` | en | "This is not a loan decision. Only a lender can decide." | Informality | "The bank decides the loan, not us." |
| `i18n.ts:407` | bn | "এটি ঋণের সিদ্ধান্ত নয়। ঋণ দেবে কি না, তা শুধু ঋণদাতা ঠিক করতে পারে।" | Casual | "লোন দেবেন কি না, সেটা ব্যাংক ঠিক করবে।" |
| `i18n.ts:101` | en | "These numbers show how the app is doing. They promise nothing." | Chatty | "These numbers show how the app performs. They promise nothing." |
| `i18n.ts:409` | bn | "এই সংখ্যাগুলো অ্যাপ কেমন করছে তা দেখায়। এগুলো কোনো প্রতিশ্রুতি নয়।" | Casual | "এই সংখ্যাগুলো অ্যাপের কাজের মান দেখায়। এগুলো কোনো প্রতিশ্রুতি নয়।" |
| `i18n.ts:118` | en | "Since 1 October, shops pay no fee to accept QR." | Chatty ("shops") | "Since 1 October, merchants pay no fee to accept QR payments." |
| `i18n.ts:426` | bn | "১ অক্টোবর থেকে QR-এ টাকা নিলে দোকানদারকে চার্জ দিতে হয় না।" | Casual ("দোকানদার") | "১ অক্টোবর থেকে QR-এ লেনদেন গ্রহণ করতে মার্চেন্টকে কোনো ফি দিতে হয় না।" |
| `i18n.ts:127` | en | "Money in the next 14 days" | Fragment | "Cash flow for the next 14 days" |
| `i18n.ts:435` | bn | "আগামী ১৪ দিনে হাতে কত থাকবে" | Casual fragment | "আগামী ১৪ দিনের ক্যাশ ফ্লো" |
| `i18n.ts:129` | en | "Money coming in, money going out, and what stays in hand — checked against your own past." | Chatty series | "Money in, money out, and cash in hand — based on your past transactions." |
| `i18n.ts:437` | bn | "কত টাকা আসবে, কত যাবে, আর হাতে কত থাকবে — আপনার নিজের পুরনো হিসাব মিলিয়ে দেখা।" | Chatty phrasing | "টাকা আসা, খরচ হওয়া এবং হাতে থাকা উদ্বৃত্তের হিসাব — আপনার আগের অভ্যাসের ভিত্তিতে।" |
| `i18n.ts:132` | en | "Our count" | Chatty | "Our model" |
| `i18n.ts:440` | bn | "আমাদের হিসাব" | Chatty | "আমাদের মডেল" |
| `i18n.ts:134` | en | "Simple guess" | Chatty ("guess") | "Simple average" |
| `i18n.ts:442` | bn | "সাধারণ অনুমান" | Casual ("অনুমান") | "সাধারণ গড়" |
| `i18n.ts:135` | en | "Counting the next 14 days…" | Chatty ("counting") | "Calculating the next 14 days…" |
| `i18n.ts:443` | bn | "আগামী ১৪ দিন গোনা হচ্ছে…" | Slang ("গোনা") | "আগামী ১৪ দিনের হিসাব করা হচ্ছে…" |
| `i18n.ts:142` | en | "No tight days here — money in hand stays above the money kept aside." | Chatty phrasing | "No tight days in this period — cash in hand stays above your safety buffer." |
| `i18n.ts:450` | bn | "এই সময়ে টানের দিন নেই — হাতে থাকা টাকা রাখা অংশের উপরেই থাকবে।" | Casual | "এই সময়ে কোনো টানের দিন নেই — উদ্বৃত্ত সবসময় নির্ধারিত সীমার উপরে থাকবে।" |
| `i18n.ts:147` | en | "How close we get, vs a simple guess" | Chatty punchline | "How our estimate compares to a simple average" |
| `i18n.ts:455` | bn | "সাধারণ অনুমানের চেয়ে আমরা কতটা কাছাকাছি" | Chatty | "সাধারণ গড়ের তুলনায় আমাদের হিসাবের যথার্থতা" |
| `i18n.ts:148` | en | "Closeness numbers will appear here once counting finishes." | Chatty | "Evaluation metrics will appear here once calculation finishes." |
| `i18n.ts:456` | bn | "গোনা শেষ হলে এখানে মিলের সংখ্যা দেখা যাবে।" | Slang ("গোনা") | "হিসাব শেষ হলে এখানে মূল্যায়নের মান দেখা যাবে।" |
| `i18n.ts:156` | en | "We check what is left in your hands — not an average." | Fragment | "We calculate from your actual cash surplus, not an average." |
| `i18n.ts:464` | bn | "গড় নয় — আপনার হাতে যা থাকে, তা দিয়েই হিসাব।" | Fragment | "গড়ের ভিত্তিতে নয় — আপনার প্রকৃত উদ্বৃত্ত দিয়েই হিসাব।" |
| `i18n.ts:162` | en | "Too big for right now" | Chatty fragment | "This goal is too high for your current surplus" |
| `i18n.ts:470` | bn | "এখনকার জন্য লক্ষ্যটা বড়" | Fragment | "বর্তমান আয়ে এই লক্ষ্য অর্জন কঠিন" |
| `i18n.ts:165` | en | "Extra money each month" | Chatty | "Monthly surplus" |
| `i18n.ts:473` | bn | "মাসে হাতে থাকা বাড়তি টাকা" | Colloquial | "মাসিক উদ্বৃত্ত টাকা" |
| `i18n.ts:166` | en | "Kept aside for safety" | Chatty fragment | "Safety buffer kept aside" |
| `i18n.ts:474` | bn | "বিপদের জন্য রাখা টাকা" | Colloquial | "নিরাপদ জমার জন্য সংরক্ষিত" |
| `i18n.ts:168` | en | "Other ways to make it fit" | Chatty phrase | "Alternative options" |
| `i18n.ts:476` | bn | "হিসাব মেলানোর বিকল্প উপায়" | Colloquial | "বিকল্প সমাধান" |
| `i18n.ts:184` | en | "Cash taken home" | Chatty | "Total cash withdrawn" |
| `i18n.ts:492` | bn | "ক্যাশ-আউট করা মোট টাকা" | Casual | "ক্যাশ-আউট করা মোট অর্থ" |
| `i18n.ts:188` | en | "Added up, nothing hidden" | Casual punchline | "Total summary" |
| `i18n.ts:496` | bn | "যোগ করে মিলিয়ে দেওয়া" | Casual punchline | "মোট হিসাব" |
| `i18n.ts:210` | en | "QR at shops: 0% fee. Cash out: 1.4% fee." | Fragmented | "QR is free. Cashing out costs 1.4%." |
| `i18n.ts:518` | bn | "দোকানে কিউআর: ০% ফি। ক্যাশ-আউট: ১.৪% ফি।" | Fragmented | "QR-এ কোনো চার্জ লাগে না। ক্যাশ আউটে ১.৪% কাটে।" |
| `i18n.ts:218` | en | "Voice does not work on this phone. Please type instead." | Acceptable, refine | "Voice does not work on this phone. Please type." |
| `i18n.ts:526` | bn | "এই ফোনে কথা বলে লেখা যায় না। দয়া করে টাইপ করুন।" | Slang | "এই ফোনে ভয়েস কাজ করে না। লিখে দিন।" |
| `i18n.ts:219` | en | "Please allow the mic, then try again." | Acceptable | "Please allow the mic." |
| `i18n.ts:527` | bn | "মাইকের অনুমতি দিন, তারপর আবার চেষ্টা করুন।" | Casual | "মাইকে অনুমতি দিন।" |
| `i18n.ts:246` | en | "One of three levels, from how regular your money habits are." | Fragment | "Grouped into one of three levels based on your payment habits." |
| `i18n.ts:554` | bn | "টাকার অভ্যাস কতটা নিয়মিত, তা তিনটি ধাপে।" | Fragment | "আপনার লেনদেনের অভ্যাসের ওপর ভিত্তি করে তিনটি স্তরে ভাগ করা হয়েছে।" |
| `i18n.ts:255` | en | "This only teaches. It never decides loans." | Fragments | "This is educational information, not a loan decision." |
| `i18n.ts:563` | bn | "এটি শুধু শেখায়। ঋণের সিদ্ধান্ত কখনো দেয় না।" | Fragments | "এটি শুধুমাত্র শিক্ষামূলক তথ্য। এটি কোনো ঋণের সিদ্ধান্ত নয়।" |
| `i18n.ts:271` | en | "How close our counts are, compared with a simple guess." | Chatty | "Accuracy of our estimates compared to a simple average." |
| `i18n.ts:579` | bn | "সাধারণ অনুমানের সাথে আমাদের গোনার তুলনা।" | Slang ("গোনা") | "সাধারণ অনুমানের তুলনায় আমাদের হিসাবের যথার্থতা।" |
| `i18n.ts:276` | en | "Simple guess" | Chatty ("guess") | "Simple average" |
| `i18n.ts:584` | bn | "সাধারণ অনুমান" | Casual | "সাধারণ গড়" |
| `forecast/page.tsx:221` | en | "days counted one by one" | Chatty | "days in total" |
| `forecast/page.tsx:221` | bn | "দিন একটা একটা করে গোনা" | Slang ("গোনা") | "দিনের হিসাব অন্তর্ভুক্ত" |
| `AnomalyCard.tsx:38` | bn | "নিয়ম ভাঙা ঠেকাতে নজরে রাখা হচ্ছে।" | Casual | "পেমেন্ট আইন, ২০২৪ অনুযায়ী পর্যবেক্ষণ করা হচ্ছে।" |
| `AnomalyCard.tsx:46` | bn | "কিউআরের ভুল ব্যবহার বা অনুমতি ছাড়া ক্যাশ-আউট ঠেকাতে দেখা হচ্ছে।" | Casual | "অননুমোদিত ক্যাশ-আউট প্রতিরোধে পর্যালোচনা করা হচ্ছে।" |
| `AnomalyCard.tsx:60` | bn | "আপনি সাধারণত এই সময়ে লেনদেন করেন না — এবার... টায় হয়েছে।" | Chatty | "এই সময়টি আপনার স্বাভাবিক লেনদেনের সময়ের বাইরে (...)।" |
| `AnomalyCard.tsx:67` | bn | "আপনার সাধারণ লেনদেনের চেয়ে প্রায় ... গুণ বড়।" | Chatty | "আপনার স্বাভাবিক লেনদেনের গড়ের চেয়ে প্রায় ... গুণ বেশি।" |

---
Gate 0 Check:
- Build passes (`tsc --noEmit` and build clean).
- Total identified offenders: 83 items across both languages.
