# Where ClaimGuard fits

ClaimGuard is **not** a full revenue-cycle management (RCM) platform and does not
try to be one. It is a narrow, pre-submission decision layer that sits **upstream**
of clearinghouse scrubbers and RCM suites — it decides *which claims a human should
look at before they are sent*, and why.

## Honest comparison

| Capability | athenahealth (athenaOne) | RapidClaims | ClaimGuard |
|---|---|---|---|
| Product scope | Full RCM + EHR + practice mgmt | Autonomous coding & RCM automation | Pre-submission risk & prioritization layer |
| Payer rule library / NCCI scrubbing | Extensive, maintained | Extensive, maintained | None — relies on downstream scrubbers |
| EHR-native workflow | Yes (native) | Integrations | No — sits beside/upstream, demo FHIR mapping only |
| Denial recovery / appeals ops | Full workflow + staff | Automated | Draft appeal letters only (clinician must verify) |
| Risk score provenance | Proprietary, payer-specific | Proprietary | Calibrated on **public CMS CERT audits**, reproducible |
| Score honesty | Marketed on outcomes | Marketed on outcomes | Improper-payment **proxy**, not claimed payer-denial accuracy |
| Auditor prioritization | Worklists | Automation-first | Expected-loss + treasury-urgency knapsack queue |
| Deploy footprint | Enterprise platform | Enterprise platform | Single service you point at your pipeline |

## What we deliberately do not do

- We do not maintain a payer-rule or NCCI edit library. Clearinghouse scrubbers and
  platforms like athenaOne already do this well; duplicating it would be worse and stale.
- We do not claim our score equals a specific payer's denial probability. The label is
  a documented CERT improper-payment proxy (see the README model card).
- We do not replace RCM staff or coding automation. We rank and explain, upstream of them.

## Where we are genuinely differentiated

1. **Provenance you can audit.** The risk model is trained and evaluated on public CMS
   CERT data with a temporal, leakage-free split and committed metrics — no black box.
2. **Calibration for money, not just ranking.** Probabilities are isotonic-calibrated so
   they can be multiplied by claim value to prioritize by expected dollars at risk.
3. **Treasury-aware queue.** Prioritization weights how fast each payer actually pays,
   not just denial risk — protecting cash flow, not only avoiding write-offs.

The intended integration is: **ClaimGuard scores and prioritizes → your scrubber /
athenaOne / RapidClaims / clearinghouse handles rules, submission, and recovery.**
