# FAPA Petition coverage map — intake → form (Oregon)

How completely the current Vault intake fills the Oregon **Petition for
Restraining Order to Prevent Abuse** (Family Abuse Prevention Act, ORS 107.700;
OJD Official, rev. Jan 2026).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the §3 relationship basis, the §4 abuse grounds, the
§6 imminent-danger declaration, and every relief box). Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The OR intake (the `_or_step` block + the shared interpreter and employer gates)
> fills the FAPA-specific items end to end. The form is **alive**: intake →
> jurisdiction-aware questions → filled petition. The UCCJEA / joint-children
> section is the main gap.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | County (Circuit Court) | `or.county` | ✅ |
| caption | Case number | — | ❌ **ORG2** (clerk-assigned) |
| caption | Interpreter (Spanish / ASL / other) | `petitioner.interpreter_language` | ✅ |
| parties | Petitioner | `petitioner.legal_name` | ✅ |
| 2 | Petitioner age | `petitioner.dob` (computed) | ✅ |
| parties | Respondent | `respondent.legal_name` | ✅ |
| 2 | Respondent age (18+) | `respondent.dob` (computed) | ✅ |
| 1 | Petitioner county / state of residence | `or.county` / — | 🟡 county assumed = filing — **ORG3** |
| 1 | Respondent county / state of residence | `respondent.last_known_address` | 🟡 not parsed — **ORG3** |
| 3 | Relationship basis (check-all) | `relationship.type` | ✅⚖️ |
| 3 | Relationship explain / dates | — | ❌ **ORG4** |
| 4 | Abuse within 180 days (4 grounds) | `or.abuse_types` | ✅⚖️ |
| 4 | Tolling — jail / 100+ miles (dates) | — | ❌ **ORG5** |
| 5A | Incident date / county / details | `incidents[].date` / `.location` / `.narrative` | ✅ |
| 5A | I was injured | `incidents[].injury` (derived) | ✅ |
| 5A | I sought medical care | — | ❌ **ORG6** |
| 5A | Respondent had a weapon | `incidents[].weapon_involved` | ✅ |
| 5A | Respondent using drugs / alcohol | — | ❌ **ORG6** |
| 5A | Police called | `incidents[].police_called` | ✅ |
| 5A | Respondent arrested | — | ❌ **ORG6** |
| 5B | Incidents more than 180 days ago | — | ❌ **ORG7** (most-recent only) |
| 6 | Imminent danger (+ explain) | `or.imminent_danger` / `or.imminent_danger_explain` | ✅⚖️ |
| 7 | Prohibit firearms / ammunition | `or.relief` | ✅⚖️ |
| 7 | Respondent has / can access firearms | `firearm.respondent_has_access` | ✅ |
| 7 | Respondent already prohibited | — | ❌ **ORG8** |
| 7 | Firearm types / locations | `firearm.types[]` / `firearm.locations[]` | ✅ |
| 8 | Existing restraining / stalking order | `prior_orders.exists` | 🟡 existence only — **ORG9** |
| 9 | Other family-law cases | — | ❌ **ORG9** |
| 10 | Move-out (+ basis: sole / joint / spouse-RDP) | `or.relief` (+ `or.move_out_basis`) | ✅⚖️ |
| 11 | Emergency money (+ amount, reason) | `or.relief` (+ `or.emergency_amount`, `or.emergency_reason`) | ✅⚖️ |
| 12 | Companion / service animals (+ detail) | `or.relief` (+ `or.animals_detail`) | ✅⚖️ |
| 13 | Minor children — names / ages | `protected_persons.children[]` | 🟡 names only — **ORG10** |
| 14-18 | Residence / 5-yr history / parentage / prior cases (UCCJEA) | — | ❌ **ORG11** |
| 19 | Custody assistance (peace officer) | `or.relief` | ✅⚖️ |
| 20 | DHS Child Welfare involvement | — | ❌ **ORG12** |
| 21 | Confidential Information Form (petitioner) | derived (checked) | ✅ |
| signature | Petitioner signature (sworn) | `petitioner.legal_name` | ✅ |
| signature | Contact address / phone / email (SAFE) | `petitioner.safe_mailing_address` / `.safe_phone` / `.safe_email` | ✅ |

## Gaps — status

- **ORG1** — the form has no printed number; `FORM_ID` is descriptive. Confirm the
  identifier with legal before filing-render.
- **ORG2** — the case number is assigned by the clerk at filing.
- **ORG3** — the §1 residency county/state fields; intake holds the filing county
  (assumed to be the petitioner's residence county) and the respondent's free-text
  last-known address (county/state not parsed).
- **ORG4** — the §3 blood-relative "explain" and intimate-relationship dates.
- **ORG5** — the §4 tolling facts (respondent in jail/prison or 100+ miles away)
  that extend the 180-day window.
- **ORG6** — the §5 per-incident checkboxes intake does not gather (sought medical
  care, drug/alcohol use, arrest).
- **ORG7** — incidents older than 180 days (§5B); intake holds the most-recent
  incident only.
- **ORG8** — whether the respondent is already prohibited from firearms (§7).
- **ORG9** — the §8 existing-order and §9 other-family-case detail (county / state
  / case#); intake holds `prior_orders.exists` only.
- **ORG10** — per-child age for the minor children (§13); intake holds names.
- **ORG11** — the §§14-18 UCCJEA section (current residence, five-year residence
  history, Oregon six-month residency, parentage, prior custody cases); the intake
  does not collect UCCJEA data.
- **ORG12** — DHS Child Welfare involvement (§20).

**For Pranav:** confirm the `⚖️` rows — the §3 relationship basis, the §4 abuse
grounds, the §6 imminent-danger declaration, and every relief box (§§7, 10, 11,
12, 19). The wiring is done; the UCCJEA section (§§13-20) is the known gap.
