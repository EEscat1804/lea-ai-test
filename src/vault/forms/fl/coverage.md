# 12.980(a) coverage map — intake → form (Florida)

How completely the current Vault intake fills the Florida **Petition for
Injunction for Protection Against Domestic Violence** (Fla. Sup. Ct. Approved
Family Law Form 12.980(a), Fla. Stat. § 741.30).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the relationship basis, the immediate-danger
assertion, and every relief box). Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The FL intake (shared Tier-2 blocks + the FL relief block) fills the
> FL-specific items end to end. The form is **alive**: intake →
> jurisdiction-aware questions → filled petition.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | County / Petitioner (+ DOB) / Respondent (+ address) | `fl.county` / `petitioner.legal_name` / `petitioner.dob` / `respondent.legal_name` / `.last_known_address` | ✅ |
| caption | Address kept confidential | derived (asserted) | ✅ |
| interpreter | Interpreter / language | `petitioner.interpreter_language` | ✅ |
| respondent desc | DOB / race / sex / height / weight / eyes / hair / marks | `respondent.dob` / `.race` / `.gender` / `.height` / `.weight` / `.eye_color` / `.hair_color` / `.distinguishing_marks` | ✅ |
| respondent desc | Employer (+ address + hours) / vehicle (+ color + plate) | `respondent.employer_*` / `respondent.vehicle_*` | ✅ |
| respondent desc | Carries firearm for work / active military / prior violent record | `respondent.is_law_enforcement` / `.is_active_military` / `.prior_criminal_history` | ✅ |
| relationship | Family/household member basis (+ live-together / child-in-common) | `relationship.type` / `.live_together_now` / `.lived_together_past` / `.children_in_common` | ✅⚖️ |
| immediate danger | Immediate and present danger | derived (asserted) | ✅⚖️ |
| statement | Date / location / narrative / injury / witnesses / police / weapon / frequency | `incidents[].*` (+ `.police_report_number`) | ✅ |
| other cases | Other injunctions/orders exist | `prior_orders.exists` | 🟡 existence only — **FG1** |
| other cases | Other pending cases (numbers/courts) | — | ❌ **FG1** |
| children | Minor children | `protected_persons.children[]` | 🟡 names; per-child DOB/residence for parenting plan — **FG2** |
| children | Why protection extends to children | `protected_persons.why` | ❌ CA-only intake — **FG2** |
| firearms | Firearms / ammunition / location | `firearm.respondent_has_access` / `.types[]` / `.locations[]` | ✅ |
| relief | Relief requested (+ shared-residence address, other detail) | `fl.relief` (+ `fl.residence_address`, `fl.other_relief`) | ✅⚖️ |
| support | Petitioner SSN (when child/spousal support requested) | `petitioner.ssn` (gated on `fl.relief`) | ✅ |
| signature | Petitioner signature | `petitioner.legal_name` | ✅ |

## Gaps — status

- **FG1** — item specifics for other pending cases (case numbers / courts /
  dates); only the existence of a prior order is collected.
- **FG2** — child-specific detail for the parenting-plan section (each child's
  DOB / current residence) and the "why protection extends to the children"
  statement.

## Open legal questions

- **Confirm `FORM_REVISION`** in `form.py` against the official blank 12.980(a)
  PDF before rendering.
- **Dating-only relationships:** `relationship_basis` is flagged — a dating
  relationship with no cohabitation or child in common may require the Dating
  Violence petition (12.980(n)), not 12.980(a).

**For Pranav:** confirm the `⚖️` rows — the family/household relationship basis,
the immediate-danger assertion, and every relief box. The wiring is done.
