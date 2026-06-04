# GA family-violence protective-order forms

Blank, official Georgia Superior Court forms for the O.C.G.A. § 19-13 flow.
Public documents. **Blank templates only — never commit a form filled with a
survivor's information.**

| Form | Title | Status |
|---|---|---|
| SC-26 | Petition for Family Violence Protective Order | mapped (`form.py`) |
| SC-26 (Confidential Information) | sealed respondent fact sheet + protected-party identifiers | mapped (within `form.py`) |
| SC-26 (Verification) | notarized verification | court-completed (no data) |

## Notes

- SC-26 (O.C.G.A. § 19-13-1 et seq.) covers parties, the § 19-13 relationship
  basis, a free-text acts-of-violence statement, firearms, and a large relief
  checklist. The respondent fact sheet (DOB/sex/race + physical + vehicle +
  employer) goes on a **sealed** page and uses the shared physical/vehicle blocks.
- **Protection:** GA's relief list includes "keep my address confidential,"
  recommended to the survivor in the intake prompt; the identifying page is
  sealed; the survivor's home address is never collected by intake. See
  `coverage.md`.
- County forms vary slightly (the sample is Athens-Clarke / Superior Court);
  confirm the local SC-26 variant.
- Drop the official blank fillable PDFs here for lea-be-core's renderer. Source:
  georgiacourts.gov / county Superior Court forms.
