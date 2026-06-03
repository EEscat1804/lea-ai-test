# 209A Complaint coverage map — intake → form (Massachusetts)

How completely the current Vault intake fills the Massachusetts **Chapter 209A
Complaint Packet** (TC0061, G.L. c. 209A): Complaint, Affidavit, Plaintiff
Confidential Information Form, and Defendant Information Form.

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** — the relationship mapping, the nature-of-abuse
boxes, and the relief boxes. Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The MA intake section fills the MA-specific items end to end. The form is
> **alive**: intake → jurisdiction-aware questions → filled packet.

## Complaint + Affidavit

| Field | Intake source | State |
|---|---|---|
| Plaintiff / Defendant name | `petitioner.legal_name` / `respondent.legal_name` | ✅ |
| Date(s) of abuse | `incidents[].date` | ✅ |
| Nature-of-abuse boxes | `ma.abuse_types` | ✅⚖️ |
| Qualifying relationship | `relationship.type` | ✅⚖️ |
| Open/closed court matters | `prior_orders.exists` | 🟡 existence only — **MG1** |
| Request-for-relief boxes (+ compensation / contact methods / animals / other) | `ma.relief` (+ `ma.compensation`, `ma.contact_methods`, `ma.animals`, `ma.other_relief`) | ✅⚖️ |
| Children under 18 | `protected_persons.children[]` | 🟡 names; ages per child — **MG2** |
| Affidavit narrative | `incidents[].narrative` | ✅ |

## Plaintiff Confidential Information Form (sealed)

| Field | Intake source | State |
|---|---|---|
| Name / DOB / interpreter / email / cellphone | `petitioner.legal_name` / `.dob` / `.interpreter_language` / `.safe_email` / `.safe_phone` | ✅ |
| **Home / work / school address** | — | ❌ **by design — never collected (protection)** |

## Defendant Information Form (for police service)

| Field | Intake source | State |
|---|---|---|
| Name / DOB / sex / race | `respondent.legal_name` / `.dob` / `.gender` / `.race` | ✅ |
| Eyes / hair / height / weight / marks | `respondent.eye_color` / `.hair_color` / `.height` / `.weight` / `.distinguishing_marks` | ✅ |
| Home address / employer / work address | `respondent.last_known_address` / `.employer_name` / `.employer_address` | ✅ |
| Vehicle make-model / color / plate | `respondent.vehicle_make_model` / `.vehicle_color` / `.vehicle_plate` | ✅ |
| Firearms access | `firearm.respondent_has_access` | ✅ |
| SSN (last 4) / aliases / parents' names / contact | — | ❌ **MG3** (rarely known) |

## Gaps — status

- **MG1** — court-matter specifics (court name/type/open-closed).
- **MG2** — per-child age (page 2 children table) and the parenting-time /
  paternity / custody-proceeding sub-sections.
- **MG3** — defendant SSN last-4, aliases, parents' names, cell/email (optional,
  rarely known).

## Protection notes

- **Plaintiff home/work/school address is never collected** by intake — only a
  safe mailing address — so it cannot land on the public complaint.
- The relief list includes explicit **"keep my home/work/school address off the
  order"** requests, recommended to the survivor in the intake prompt.
- The affidavit narrative passes through **verbatim** (guardrail G-08).

**For Pranav:** confirm the `⚖️` rows — the relationship mapping, the
nature-of-abuse boxes, and the relief boxes. The wiring is done.
