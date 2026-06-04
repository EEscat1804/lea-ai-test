# SC-26 coverage map — intake → form (Georgia)

How completely the current Vault intake fills the Georgia **Petition for Family
Violence Protective Order** (SC-26, O.C.G.A. § 19-13-1 et seq.).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** — the relationship mapping and every relief box.
Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The GA intake section fills the GA-specific items end to end. The form is
> **alive**: intake → jurisdiction-aware questions → filled petition.

## Petition + relief

| Item | Field | Intake source | State |
|---|---|---|---|
| caption | Petitioner / Respondent | `petitioner.legal_name` / `respondent.legal_name` | ✅ |
| 1, 2 | Petitioner county / respondent address | `ga.county` / `respondent.last_known_address` | ✅ |
| 3 | Relationship (§ 19-13) | `relationship.type` | ✅⚖️ |
| 4 | Acts of family violence (date + statement + firearm) | `incidents[].date` / `.narrative` / `.weapon_involved` | ✅ |
| 6 | Substantial likelihood of future violence | fixed (asserted) | ✅ |
| 7 | Children under 18 | `protected_persons.children[]` | 🟡 names; year/sex/age — **GAG1** |
| 14, 15 | Criminal record / firearms (+ desc) | `respondent.prior_criminal_history` / `firearm.respondent_has_access` / `.types[]` | ✅ |
| relief | Relief checklist (+ residence address / vehicle / property-return / other) | `ga.relief` (+ `ga.residence_address`, `ga.vehicle`, `ga.return_property_desc`, `ga.other_relief`) | ✅⚖️ |
| signature | Petitioner signature | `petitioner.legal_name` | ✅ |

## Sealed Confidential Information page (respondent fact sheet)

| Field | Intake source | State |
|---|---|---|
| DOB / sex / race | `respondent.dob` / `.gender` / `.race` | ✅ |
| Hair / eyes / height / weight / marks | `respondent.hair_color` / `.eye_color` / `.height` / `.weight` / `.distinguishing_marks` | ✅ |
| Vehicle / plate / home address / employer | `respondent.vehicle_make_model` / `.vehicle_plate` / `.last_known_address` / `.employer_name` | ✅ |
| SSN / driver's license / ethnic background | — | ❌ **GAG2** (rarely known) |

## Gaps — status

- **GAG1** — per-child year-of-birth / sex / age and the custody/residency
  sub-sections (items 7-13 detail).
- **GAG2** — respondent SSN, driver's license, ethnic background (optional).
- Item 5 (history of other acts) — pattern collected, no separate statement.

## Protection notes

- GA's relief list includes **"keep my address confidential"**, recommended to
  the survivor in the intake prompt; the identifying page is filed **under seal**.
- The survivor's home address is never collected by intake (only a safe mailing
  address); the narrative passes through **verbatim** (guardrail G-08).

**For Pranav:** confirm the `⚖️` rows — the § 19-13 relationship mapping and the
relief boxes. The wiring is done.
