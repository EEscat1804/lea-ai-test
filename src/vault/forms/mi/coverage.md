# Form CC 375 coverage map — intake → form (Michigan)

How completely the current Vault intake fills the Michigan **Petition for Personal
Protection Order (Domestic Relationship)** (SCAO Form CC 375, MCL 600.2950 /
600.2950a, MCR 3.703, Rev. 3/23).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the relationship basis, the ex parte election, the
petitioner-address handling, and every §5 a-l relief box). Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The MI intake (Tier-1 core + the unconditional employer gate + the MI block)
> fills the MI-specific items end to end. The form is **alive**: intake →
> jurisdiction-aware questions → filled petition.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | County (circuit) / case number / judge | `mi.county` / clerk | ✅ (case no. — MIG1) |
| A | Petitioner name / age / address / phone | `petitioner.legal_name` / from `.dob` / `.safe_mailing_address` / `.safe_phone` | ✅⚖️ (address; age — MIG2) |
| A | Respondent name / address / age | `respondent.legal_name` / `.last_known_address` / — | ✅ (age — MIG2) |
| 1 | Domestic relationship basis | `mi.relationship` | ✅⚖️ |
| 2 | Respondent carries firearm for employment | `mi.respondent_carries_firearm` | ✅ |
| 3 | Other pending actions / orders | `prior_orders.exists` / `mi.other_cases_detail` | 🟡 existence + free text — MIG4 |
| 4 | Need for the order (narrative + date / location) | `incidents[].narrative` / `.date` / `.location` | ✅ |
| 5 a-l | Relief checklist | `mi.relief` | ✅⚖️ |
| 5b/5c/5g | Property address / assault names / threat names | `mi.other_property_address` / `mi.assault_names` / `mi.threat_names` | ✅ |
| 5e | Stalking sub-acts | `mi.stalking_acts` | ✅ |
| 5j | Animal sub-acts | `mi.animal_acts` | ✅ |
| 5l | Other relief detail | `mi.relief_other_detail` | ✅ |
| 6 | Ex parte election | `mi.ex_parte` | ✅⚖️ |
| 7 | Next friend (minor petitioner) | — | ❌ MIG5 |
| verification | Petitioner / next-friend signature | `petitioner.legal_name` | ✅ |

## Gaps — status

- **MIG1** — the case number / judge are assigned by the clerk at filing.
- **MIG2** — the petitioner age (computed from `petitioner.dob` at fill time) and
  the respondent age (not collected by intake for MI) caption fields.
- **MIG3** — CC 375 has no confidential-address affidavit; the petitioner's
  contact address is printed and served. Address confidentiality is a separate
  MCR process (flagged `needs_legal_review`).
- **MIG4** — the §3 other-actions case-number / court / judge tables; only
  protective-order existence + a free-text note are collected.
- **MIG5** — the §7 next-friend block for a minor petitioner is not collected; a
  minor MI petitioner files through a next friend (a distinct mechanism, so MI is
  not in the shared minor-self-filing gate).

**For Pranav:** confirm the `⚖️` rows — the §1 relationship basis, the §6 ex parte
election, the petitioner-address handling, and every §5 a-l relief box. The wiring
is done.
