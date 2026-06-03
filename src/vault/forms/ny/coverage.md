# UCS-FC8-2 coverage map — intake → form (New York)

How completely the current Vault intake fills the New York **Family Offense
Petition** (UCS-FC8-2, FCA 812/818/821, Rev. 05/2025).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** — especially the item-4 offense checklist and the
relationship mapping. Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The NY intake section fills the NY-specific items end to end. The form is
> **alive**: intake → jurisdiction-aware questions → filled petition.

## Item-by-item

| Item | Field | Intake source | State |
|---|---|---|---|
| caption | County / Petitioner / Respondent | `ny.county` / `petitioner.legal_name` / `respondent.legal_name` | ✅ |
| 1 | Address confidential / mailing address | fixed **Yes** / `petitioner.safe_mailing_address` | ✅ |
| 2 | Respondent address | `respondent.last_known_address` | ✅ |
| 3 | Relationship (FCA 812) | `relationship.type` | ✅⚖️ |
| 4 | **Offense checklist** | — | ❌⚖️ **NYG1 — legal characterization, left to attorney** |
| 4 | Offense details (date/location/injuries/weapons/narrative) | `incidents[].date` / `.location` / `.injury` / `.weapon_involved` / `.narrative` | ✅ |
| 5 | Criminal complaint filed | `incidents[].police_called` | 🟡 (court/docket detail not collected) |
| 6 | Household children | `protected_persons.children[]` | 🟡 names; DOB/relationship — **NYG2** |
| 8 | Violated OP / owns firearms / carries on job / used to threaten | `prior_orders.exists` / `firearm.respondent_has_access` / `respondent.is_law_enforcement` / `incidents[].weapon_involved` | ✅ |
| 9 | Criminal convictions | `respondent.prior_criminal_history` | 🟡 (conviction detail not collected) |
| 10a | Determine family offense | fixed (asserted) | ✅⚖️ |
| 10b | Enter order of protection | derived (checked if any condition) | ✅ |
| 10 | Relief conditions (stay-away/no-contact/surrender/aggravated/support) | `ny.relief` | ✅⚖️ |
| 11 | Petitioner signature | `petitioner.legal_name` | ✅ |

## Gaps — status

- **NYG1 — item 4 offense checklist.** Deliberately not collected: which
  penal-law offense applies is a legal characterization for the attorney, not
  something the Vault guesses. The narrative + details are mapped.
- **NYG2 — household children detail** (DOB, relationship to respondent/
  petitioner; the live-with vs. not-live-with split).
- Court/docket/conviction detail in items 5, 9, and the pending-cases /
  previous-application tables (items on pages 3, 5) — not collected.

## Protection notes

- **Address confidentiality defaults to Yes** — the petitioner's address is kept
  off the public petition and filed separately on UCS-FC GF-21.
- The narrative passes through **verbatim** (guardrail G-08); nothing is
  paraphrased or characterized.

**For Pranav:** confirm the `⚖️` rows — the FCA 812 relationship mapping, the
item-4 offense selection, and the relief conditions. The wiring is done.
