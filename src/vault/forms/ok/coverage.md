# Petition for Protective Order coverage map — intake → form (Oklahoma)

How completely the current Vault intake fills the Oklahoma **AOC Petition for
Protective Order** (Protection from Domestic Abuse Act, 22 O.S. § 60.1; effective
Nov 1, 2023).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the §1 relationship basis, the §1B/§1C/§1D victim
characterization, the §2 jurisdiction statement, the §3 actions, the ex parte
election, and every §6 relief box). Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The OK intake (the `_ok_step` block + the shared physical-description and
> minor-filing gates) fills the OK-specific items end to end. The form is
> **alive**: intake → jurisdiction-aware questions → filled petition.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | County (District Court) | `ok.county` | ✅ |
| caption | Case number (PO-20__) / court phone | — | ❌ **OKG2** (clerk-assigned) |
| caption | Petitioner | `petitioner.legal_name` | ✅ |
| caption | Minor family member(s) — names / ages | `protected_persons.children[]` | 🟡 names only — **OKG3** |
| caption | Defendant | `respondent.legal_name` | ✅ |
| caption | Relationship to petitioner | `relationship.type` | ✅⚖️ |
| caption | Defendant address | `respondent.last_known_address` | ✅ |
| caption | Defendant sex / race / DOB | `respondent.gender` / `.race` / `.dob` | ✅ |
| caption | Defendant ht / wt / eyes / hair / features | `respondent.height` / `.weight` / `.eye_color` / `.hair_color` / `.distinguishing_marks` | ✅ (shared physical gate) |
| caption | Defendant driver's license | — | ❌ **OKG4** |
| 1A | Relationship basis (intimate partner / family-household) | `relationship.type` | ✅⚖️ |
| 1B/1C/1D | Victim type / acts / first-degree murder | — | ❌ **OKG5** (attorney-confirmed) |
| 2 | Jurisdiction statement (petitioner / defendant / abuse here) | `ok.jurisdiction_basis` | ✅⚖️ |
| 3 | Actions of the defendant (harm / threat / harass / stalk / crime) | `ok.actions` | ✅⚖️ |
| 3 | Name(s) per action | — | ❌ **OKG6** |
| 4 | Incident date(s) | `incidents[].date` | ✅ |
| 4 | Describe what happened | `incidents[].narrative` | ✅ |
| 4 | Where it happened | `incidents[].location` | ✅ |
| 5 | Other cases involving the parties | `prior_orders.exists` | 🟡 existence only — **OKG7** |
| 6 | Emergency ex parte election (A vs B) | `ok.ex_parte` | ✅⚖️ |
| 6.1 | No contact | `ok.relief` | ✅⚖️ |
| 6.2 | No injuring / abusing / threatening | `ok.relief` | ✅⚖️ |
| 6.3 | No fear-inducing conduct | `ok.relief` | ✅⚖️ |
| 6.4 | Leave residence (+ address, utilities) | `ok.relief` (+ `ok.move_out_address`) | ✅⚖️ |
| 6.5 | Law enforcement remove defendant's effects | `ok.relief` | ✅⚖️ |
| 6.6 | Civil standby for petitioner (+ address) | `ok.relief` (+ `ok.civil_standby_address`) | ✅⚖️ |
| 6.7 | Minor defendant leave residence | `ok.relief` | ✅⚖️ |
| 6.8 | Suspend / modify child visitation | `ok.relief` | ✅⚖️ |
| 6.9 | Domestic-abuse counseling / treatment | `ok.relief` | ✅⚖️ |
| 6.10 | Protect animals (no contact, possession to petitioner) | `ok.relief` | ✅⚖️ |
| 6.11 | GPS monitoring | `ok.relief` | ✅⚖️ |
| 6.12 | Transfer utilities / wireless (+ detail) | `ok.relief` (+ `ok.transfer_detail`) | ✅⚖️ |
| 6.13 | Surrender firearms / weapons | `ok.relief` | ✅⚖️ |
| 6.14 | Pay court costs / service fees | `ok.relief` | ✅⚖️ |
| 6.15 | Pay attorney's fees (+ amount) | `ok.relief` (+ `ok.attorney_fees_amount`) | ✅⚖️ |
| 6 | Additional relief requested | `ok.additional_relief` | ✅ |
| 6.13 | Defendant has / can access firearms (+ types, locations) | `firearm.respondent_has_access` (+ `firearm.types[]`, `firearm.locations[]`) | ✅ |
| 8 | Petitioner signature (sworn) | `petitioner.legal_name` | ✅ |
| 8 | Subscribed / sworn before clerk-notary | — | ❌ **OKG8** (at filing) |
| 8 | Law enforcement agencies to receive a copy | — | ❌ **OKG8** |

## Gaps — status

- **OKG1** — the form has no printed number; `FORM_ID` is descriptive. Confirm the
  identifier with legal before filing-render.
- **OKG2** — the case number (PO-20__) and court phone are assigned / filled by the
  clerk at filing.
- **OKG3** — per-minor age for the minor family members; intake holds names.
- **OKG4** — the defendant's driver's license (#, state, expiry).
- **OKG5** — the §1B/§1C/§1D victim-and-crime characterization (victim of DV /
  stalking / harassment / rape / other crime, or immediate family of a
  first-degree-murder victim); attorney-confirmed from the §3 actions and the
  relationship.
- **OKG6** — the per-action name blanks in §3, and the Appendix 1 police-report
  requirement for non-family / non-dating petitioners (a conditional eligibility
  check left to the attorney/advocate).
- **OKG7** — the §5 other-cases detail (case name / number / county-state); intake
  holds `prior_orders.exists` only.
- **OKG8** — the notary/clerk acknowledgment and the law-enforcement-agency
  distribution list, completed at filing.

**For Pranav:** confirm the `⚖️` rows — the §1 relationship basis, the §1B/§1C/§1D
victim characterization, the §2 jurisdiction statement, the §3 actions, the ex
parte election, and every §6 relief box. The wiring is done.
