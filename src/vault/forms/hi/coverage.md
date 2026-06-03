# 1F-P-752A coverage map — intake → form (Hawai'i)

How completely the current Vault intake fills the Hawai'i **Petition for an
Order for Protection** (1F-P-752A, HRS ch. 586, FC Adm 7/12/23).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** — the jurisdiction basis, the relationship mapping,
the acts-of-abuse / harm-type boxes, and the relief boxes. Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The HI intake section fills the HI-specific items end to end. The form is
> **alive**: intake → jurisdiction-aware questions → filled petition.

## Item-by-item

| Item | Field | Intake source | State |
|---|---|---|---|
| caption | Petitioner / Respondent | `petitioner.legal_name` / `respondent.legal_name` | ✅ |
| caption | Self-represented | fixed | ✅ |
| 2 | Petitioner age band (16-17 / 18+) | derived from `petitioner.dob` | ✅ |
| 3 | Jurisdiction basis | fixed (petitioner resides) | ✅⚖️ |
| 4 | Filing for myself / household members | fixed / `protected_persons.children[]` | 🟡 names; gender/year/relationship — **HG1** |
| 5 | Relationship (ch. 586) | `relationship.type` | ✅⚖️ |
| 6 | Incident date / narrative | `incidents[].date` / `.narrative` | ✅ |
| 6 | Acts-of-abuse boxes (+ other) | `hi.abuse_acts` (+ `hi.abuse_other`) | ✅⚖️ |
| 6 | Harm-type classification | `hi.harm_types` | ✅⚖️ |
| 7, 8 | Weapon / firearms (+ description, location) | `firearm.respondent_has_access` / `.types[]` / `.locations[]` | ✅ |
| 9 | Other court cases | `prior_orders.exists` | 🟡 existence only — **HG2** |
| II | Relief requested (TRO + protective order) | `hi.relief` | ✅⚖️ |
| II.5 | Order duration | `hi.duration` | ✅ |
| signature | Petitioner signature | `petitioner.legal_name` | ✅ |

## Gaps — status

- **HG1** — per-household-member gender, year of birth, and relationship
  (the section-4 table) plus protected animals.
- **HG2** — court-case specifics (item 9 sub-types and case numbers).
- Item 7 (respondent mental-illness / drug-use / armed-services / supervised
  visitation reason), item 10 (own/rent), item 11 (agency referral) — not
  collected (mostly optional).

## Notes for legal review

- Item 6 splits each incident into an **acts** checklist and a **harm-type**
  classification — both flagged `needs_legal_review`; the survivor's verbatim
  narrative drives the description.
- The form is the **First Circuit (O'ahu)** petition — confirm the circuit for
  non-O'ahu filings.

**For Pranav:** confirm the `⚖️` rows. The wiring is done.
