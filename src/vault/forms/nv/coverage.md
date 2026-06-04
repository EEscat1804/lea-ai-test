# Application for Protection Order (DV) coverage map — intake → form (Nevada)

How completely the current Vault intake fills the Nevada **Application for
Protection Order Against Domestic Violence** (© 2022 Nevada Supreme Court, NRS 33).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the abuse grounds, the relationship basis, every
item-10 temporary protection, the order length, and every extended-relief box).
Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The NV intake (Tier-1 core + the shared interpreter gate + the NV block) fills
> the NV-specific items end to end. The form is **alive**: intake →
> jurisdiction-aware questions → filled application.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | Court type / township / county / applicant / adverse party / adult-minor | `nv.court_type` / `nv.township` / `nv.county` / `petitioner.legal_name` / `respondent.legal_name` / `nv.adverse_party_type` | ✅ |
| 1 | Interpreter (language) | `petitioner.interpreter_language` | ✅ |
| 2 | Adverse party in custody (+ where) | `nv.adverse_in_custody` | ✅ (where — NVG2) |
| 3 | Who needs protection (me / children) | `nv.who_needs_protection` / `protected_persons.children[]` | ✅ (chart 🟡 — NVG3) |
| 4 | Abuse grounds (DV against me / child) | `nv.protection_reason` | ✅⚖️ (parent/guardian — NVG4) |
| 5 | Relationship basis | `relationship.type` | ✅⚖️ |
| 6 | Other court cases | `prior_orders.exists` / `nv.other_cases_detail` | 🟡 existence + free text — NVG5 |
| 7 | Firearms possessed | `firearm.respondent_has_access` | 🟡 boolean vs No/Yes/Idk — NVG6 |
| 8 | Most recent event (date / location / weapon / police / narrative) | `incidents[].date` / `.location` / `.weapon_involved` / `.police_called` / `.narrative` | ✅ (arrest — NVG7) |
| 9 | Past events | — | ❌ NVG8 |
| 10 | Temporary protections (12 boxes) | `nv.temp_protections` | ✅⚖️ |
| 10 | Parenting contact method | `nv.contact_me_method` | ✅ |
| 10 | Address confidential | derived | ✅ |
| 10 | Live together / lease holder | `relationship.live_together_now` | 🟡 lease/move-in — NVG9 |
| 10 | Belongings retrieval address | `nv.belongings_address` | ✅ |
| 10 | Work employer / address (stay-away) | `respondent.employer_name` / `respondent.employer_address` | ✅ |
| 10 | Other places | `nv.other_places_detail` | ✅ |
| 10 (p7) | Custody / visitation | `nv.custody` / `nv.visitation_detail` | ✅ (UCCJEA — NVG10) |
| 11 | Temporary order requested | derived | ✅ |
| 11 | Order length (45-day / extended) | `nv.order_length` | ✅⚖️ |
| 11 | Extended relief (rent / support / etc.) | `nv.extended_relief` | ✅⚖️ |
| 14 | No NRS 603A.040 personal info | derived | ✅ |
| verification | Applicant signature | `petitioner.legal_name` | ✅ |

## Gaps — status

- **NVG1** — the form has no printed number; `FORM_ID` is descriptive.
- **NVG2** — the free-text "where" for an adverse party in custody.
- **NVG3** — per-child DOB and both parents for the item-3 children chart; only
  names are collected.
- **NVG4** — the parent-vs-legal-guardian election in item 4.
- **NVG5** — the full item-6 case table (type / county / state / number); only
  protective-order existence + a free-text note are collected.
- **NVG6** — the firearms answer is No / Yes / **I don't know** on the form; intake
  is a boolean, so "I don't know" cannot be expressed.
- **NVG7** — the "was anyone arrested (who)" detail in item 8.
- **NVG8** — the item-9 past-events dates/narratives (not collected separately from
  the most-recent statement).
- **NVG9** — the lease/title holder and move-in date in the item-10 current-residence
  block.
- **NVG10** — the UCCJEA Declaration required for temporary custody is not assembled.

**For Pranav:** confirm the `⚖️` rows — the abuse grounds, the relationship basis,
every item-10 temporary protection, the order length, and every extended-relief
box. The wiring is done.
