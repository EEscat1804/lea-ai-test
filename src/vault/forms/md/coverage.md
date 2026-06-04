# CC-DC-DV-001 coverage map — intake → form (Maryland)

How completely the current Vault intake fills the Maryland **Petition for
Protection from Domestic Violence** (CC-DC-DV-001, FL § 4-504, Rev. 10/2025) +
the respondent-description addendum (CC-DC-DV-001A).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** — the relationship mapping, the acts-of-abuse boxes,
and the relief boxes. Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The MD intake section fills the MD-specific items end to end. The form is
> **alive**: intake → jurisdiction-aware questions → filled petition.

## Item-by-item

| Item | Field | Intake source | State |
|---|---|---|---|
| caption | Petitioner / Respondent (+ addresses) | `petitioner.legal_name` / `respondent.legal_name` / `.safe_mailing_address` / `.last_known_address` | ✅ |
| caption | Petition type: domestic violence | fixed | ✅ |
| caption | Address withheld | fixed **on** (protection) | ✅ |
| 1 | Relationship eligibility | `relationship.type` | ✅⚖️ |
| 2 | Abuser / whereabouts / date | `respondent.legal_name` / `.last_known_address` / `incidents[].date` | ✅ |
| 2 | Acts-of-abuse boxes (+ other) | `md.abuse_acts` (+ `md.abuse_other`) | ✅⚖️ |
| 2 | Details of what happened | `incidents[].narrative` | ✅ |
| 4 | Persons to protect | `protected_persons.children[]` | 🟡 names; birthdate/relationship — **MDG1** |
| 7, 8 | Court cases / prior final order | `prior_orders.exists` | 🟡 existence only — **MDG2** |
| 9 | Past injuries | `incidents[].injury` | ✅ |
| 10 | Firearms (+ description) | `firearm.respondent_has_access` / `.types[]` | ✅ |
| 11, 12 | Relief requested (+ home address / counseling type / vehicle / pets / other) | `md.relief` (+ `md.home_address`, `md.counseling_type`, `md.vehicle`, `md.pets`, `md.other_relief`) | ✅⚖️ |
| signature | Petitioner signature | `petitioner.legal_name` | ✅ |
| addendum | Respondent DOB / sex / race / employer | `respondent.dob` / `.gender` / `.race` / `.employer_name` | ✅ |
| addendum | Respondent physical (height/weight/eyes/hair) | — | ❌ **MDG3** (no physical block for MD) |

## Gaps — status

- **MDG1** — per-protected-person birthdate + relationship to respondent.
- **MDG2** — court-case specifics (court/kind/year/status) and prior-order dates.
- **MDG3** — respondent physical description (MD isn't in the shared physical
  block; only DOB/sex/race/employer collected for the addendum).
- Item 5 (military order), item 13 (Emergency Family Maintenance financials) —
  not collected.

## Protection notes

- The petitioner's address is **withheld by default** (the form expressly allows
  omitting it), and intake only ever holds a safe mailing address.
- The narrative passes through **verbatim** (guardrail G-08).

**For Pranav:** confirm the `⚖️` rows — the § 4-504 relationship mapping, the
acts-of-abuse boxes, and the relief boxes. The wiring is done.
