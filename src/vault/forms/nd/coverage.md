# Petition CPO coverage map — intake → form (North Dakota)

How completely the current Vault intake fills the North Dakota **Petition for
Civil Protection Order** (N.D.C.C. Ch. 14-07.7, Rev. Mar 2026).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the order type(s), the relationship basis, and every
relief box). Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The ND intake (`_nd_step` + the shared Tier-2 blocks) fills the ND-specific
> items end to end. The form is **alive**: intake → jurisdiction-aware questions
> → filled petition.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | County / judicial district / petitioner / respondent | `nd.county` / `nd.judicial_district` / `petitioner.legal_name` / `respondent.legal_name` | ✅ |
| 2 | Order type(s) (DV / sexual assault / disorderly conduct) | `nd.order_types` | ✅⚖️ |
| 3 | Venue basis | `nd.venue` | ✅ |
| 4 | Petitioner is victim / relationship | derived / `relationship.type` | ✅⚖️ |
| 4 | Minor child victims | `protected_persons.children[]` | 🟡 names; age/lives-with/relationship — **NDG1** |
| 5 | Not a minor child | derived from `petitioner.dob` | ✅ (minor path — **NDG2**) |
| 6 | Address kept confidential | derived | ✅ |
| 7 | Respondent address / employer | `respondent.last_known_address` / `.employer_name` | ✅ |
| 7 | Respondent SSN | — | ❌ **NDG3** |
| 8 | Respondent DOB / age | `respondent.dob` / derived | ✅ |
| 9 | Respondent gender/race/height/weight/eyes/hair/marks/vehicle/plate | `respondent.gender` / `.race` / `.height` / `.weight` / `.eye_color` / `.hair_color` / `.distinguishing_marks` / `.vehicle_make_model` / `.vehicle_plate` | ✅ |
| 9 | Respondent driver's license | — | ❌ **NDG3** |
| 10 | Current custody/parenting-time cases | — | ❌ **NDG4** |
| 11 | Other civil/criminal cases | `prior_orders.exists` | 🟡 existence only — **NDG4** |
| 12 | Most recent incidents (+ date) | `incidents[].narrative` / `incidents[].date` | ✅ |
| 13 | Past incidents | — | ❌ **NDG5** |
| 14 | Relief (restrain/exclude/contact/custody/parenting/firearms/animals/disorderly) | `nd.relief` | ✅⚖️ |
| 14 | Exclude-from places (+ distance) | `nd.exclude_places` / `nd.stay_away_feet` | ✅ |
| 14 | Firearms / animals detail | `nd.firearms_detail` / `nd.animals_detail` | ✅ |
| 15 | Request hearing + permanent order | derived | ✅ |
| 16 | Notification when served | `nd.notification` | ✅ |
| 17 | Petitioner signature | `petitioner.legal_name` | ✅ |

## Gaps — status

- **NDG1** — per-child age / lives-with / relationship-to-respondent (para 4 table).
- **NDG2** — the minor-petitioner path (para 5); the adult box is derived from the
  petitioner's age, but a minor filing on their own is a legal determination.
- **NDG3** — respondent SSN and driver's license (sensitive / not collected).
- **NDG4** — the para-10 custody/parenting-time case list and the full para-11
  other-cases list (only protective-order existence is collected).
- **NDG5** — para-13 past incidents (collected only as the most-recent statement).

**For Pranav:** confirm the `⚖️` rows — the order type(s), the para-4 relationship
basis, and every para-14 relief box. The court issues the single most-protective
order among the types selected. The wiring is done.
