# FC-79 coverage map — intake → form (Rhode Island)

How completely the current Vault intake fills the Rhode Island **Complaint for an
Order of Protection and Motion for Temporary Ex Parte Order of Protection**
(FC-79; Family Court; rev. July 2025).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the case type, the §5 relationship basis, the §1
street-address mapping, the §7 abuse checklist, every relief box, and the ex parte
request). Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The RI intake (the `_ri_step` block + the unconditional employer gate) fills the
> RI-specific items end to end. The form is **alive**: intake →
> jurisdiction-aware questions → filled complaint.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | County (Newport / Washington / Kent / Providence-Bristol) | `ri.county` | ✅ |
| caption | Civil Action File Number | — | ❌ **RIG1** (clerk-assigned) |
| caption | Case type (4 boxes) | `ri.case_type` | ✅⚖️ |
| plaintiff | Plaintiff (+ DOB) | `petitioner.legal_name` / `.dob` | ✅ |
| plaintiff | Capacity (individually / parent / guardian / POA) | — | ❌ **RIG2** (assumes individually) |
| 1 | Plaintiff name / street address / city / state | `petitioner.safe_mailing_address` | 🟡⚖️ safe mailing only — **RIG3** |
| 2 | Former residence left to avoid abuse | `ri.former_residence` | ✅ |
| plaintiff | Children protected (a-e) | `protected_persons.children[]` | 🟡 names only — **RIG4** |
| defendant | Defendant (+ DOB) | `respondent.legal_name` / `respondent.dob` | ✅ |
| 3 | Defendant name / street address / city / state | `respondent.last_known_address` | ✅ |
| defendant | Capacity (individually / parent / guardian / POA) | — | ❌ **RIG2** |
| 4 | Other lawsuits / orders between the parties | `prior_orders.exists` | 🟡 existence only — **RIG5** |
| 5 | Relationship basis (check one) | `relationship.type` | ✅⚖️ |
| 5 | "The defendant is my ___" (relative) | — | ❌ **RIG6** |
| 6 | Servicemember certification | — | ❌ **RIG7** (standing statement) |
| 7 | Date of abuse ("on or about") | `incidents[].date` | ✅ |
| 7 | Abuse checklist (weapon / harm / fear / sexual / stalking / exploitation) | `ri.abuse_types` | ✅⚖️ |
| 7 | Weapon used / threatened (detail) | `ri.weapon_detail` | ✅ |
| 7 | Facts of abuse (verified complaint) | `incidents[].narrative` | ✅ |
| relief | No contact / restrain / enjoin | `ri.relief` | ✅⚖️ |
| relief | Surrender all firearms (72 hours) | `ri.relief` | ✅⚖️ |
| relief | Vacate / remain out of household (+ address) | `ri.relief` (+ `ri.vacate_address`) | ✅⚖️ |
| relief | No utility termination / disruption | `ri.relief` | ✅⚖️ |
| relief | Temporary custody of minor children (+ list) | `ri.relief` (+ `ri.custody_children`) | ✅⚖️ |
| relief | Child support (up to 90 days) | `ri.relief` | ✅⚖️ |
| relief | Safety / welfare of household animals (+ detail) | `ri.relief` (+ `ri.pets_detail`) | ✅⚖️ |
| motion | Request relief without notice (ex parte) | `ri.ex_parte` | ✅⚖️ |
| verification | Plaintiff signature (sworn) | `petitioner.legal_name` | ✅ |
| verification | Notary acknowledgment | — | ❌ **RIG8** (completed at filing) |

## Gaps — status

- **RIG1** — the Civil Action File Number is assigned by the clerk at filing.
- **RIG2** — the plaintiff/defendant capacity checkboxes (individually vs. as a
  parent/guardian/attorney-in-fact); intake assumes the plaintiff files
  individually and does not collect them.
- **RIG3** — FC-79 has no address-confidentiality checkbox; intake holds a safe
  mailing address, so the §1 street-address mapping is flagged for confirmation
  before any street address is printed.
- **RIG4** — per-child detail (DOB) for the protected children; intake holds names.
- **RIG5** — the other-court-cases list ("None" or the case numbers); intake holds
  `prior_orders.exists` only.
- **RIG6** — the "the defendant is my ___" relative free-text; not separately
  collected (the §5 box itself is mapped from `relationship.type`).
- **RIG7** — the §6 servicemember certification is a standing statement; the
  defendant's military status is not collected for RI.
- **RIG8** — the notary acknowledgment is completed before a notary at filing.

**For Pranav:** confirm the `⚖️` rows — the case type, the §5 relationship basis,
the §1 street-address mapping, the §7 abuse checklist, every relief box, and the
ex parte request. The wiring is done.
