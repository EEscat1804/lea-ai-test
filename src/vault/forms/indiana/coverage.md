# OJA-PO-0100 coverage map — intake → form (Indiana)

How completely the current Vault intake fills the Indiana **Petition for an Order
for Protection** (OJA-PO-0100, I.C. 34-26-5, Rev. 05/25).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the victim basis, the relationship basis, the venue,
the acts, the confidential-address election, the ex parte request, and every §9
relief box). Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The IN intake (Tier-1 core + the shared employer gate + the IN block) fills the
> IN-specific items end to end. The form is **alive**: intake →
> jurisdiction-aware questions → filled petition.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | Court / county / case number | `in.court` / `in.county` / clerk | ✅ (case no. — ING1) |
| parties | Petitioner / public address / respondent / age / employer | `petitioner.legal_name` / `.safe_mailing_address` / `respondent.legal_name` / `.age` / `.employer_name` / `.employer_address` | ✅⚖️ (address) |
| §6 | Confidential address (PO-0104) | derived | ✅⚖️ |
| 1 | Victim basis (DV / sex offense / stalking / harassment) | `in.victim_basis` | ✅⚖️ |
| 2 | Relationship basis | `in.relationship_basis` | ✅⚖️ |
| 4 | Other cases | `prior_orders.exists` | 🟡 existence — ING2 |
| 5 | Venue | `in.venue` | ✅⚖️ |
| 7 | Acts | `in.abuse_acts` | ✅⚖️ |
| 8 | Narrative (+ date / location / witnesses) | `incidents[].narrative` / `.date` / `.location` / `.witnesses_present` | ✅ |
| 9 | Protective relief | `in.relief` | ✅⚖️ |
| 9 | Stay-away / evict / possession / firearm / wireless detail | `in.stay_away_location` / `in.evict_address` / `in.possession_detail` / `in.firearm_detail` / `in.wireless_detail` | ✅ |
| 9 (hearing) | Custody / support / fees relief | `in.hearing_relief` | ✅⚖️ |
| 9 (hearing) | Support / expense detail | `in.support_detail` | ✅ |
| 10 | Ex parte request | derived | ✅⚖️ |
| verification | Petitioner signature | `petitioner.legal_name` | ✅ |

## Gaps — status

- **ING1** — the case number is assigned by the clerk at filing.
- **ING2** — the §4 other-cases table (case name / number / county-state) is not
  collected; only protective-order existence is mapped.

**For Pranav:** confirm the `⚖️` rows — the §1 victim basis, the §2 relationship
basis, the §5 venue, the §7 acts, the §6 confidential-address election, the §10 ex
parte request, and every §9 relief box (protective + after-hearing). The §9 relief
includes support, but no petitioner SSN field exists on this form, so IN is not in
the SSN gate. The wiring is done.
