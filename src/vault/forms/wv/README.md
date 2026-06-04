# WV protective-order forms

Blank, official West Virginia Supreme Court of Appeals forms for the
domestic-violence TEPO flow. Public documents. **Blank templates only — never
commit a form filled with a survivor's information.**

| Form | Title | Status |
|---|---|---|
| MDVTPET | Domestic Violence Petition for Temporary Emergency Protective (TEPO) Order | mapped (`form.py`) |
| MDVINFO | Civil Case Information Statement (Domestic Violence) | mapped inline (caption + respondent identifiers) |
| MDVDNYE | Appeal – Denial of Petition for Emergency Protective Order | not mapped |

## Notes

- MDVTPET (W. Va. Code § 48-27) covers the parties (with respondent identifiers
  for the National DV Registry), the relationship basis, children, the item-8
  acts checklist, the abuse narrative, prior orders, firearms, the requested PO
  duration (with § 48-27-505 reasons for 1-year / longer orders), and the
  permissive-relief list. WV's relief list is its own. See `coverage.md`.
- **Address protection:** the CCIS lets the petitioner seal their address; intake
  never collects a home address, and the seal box defaults on. Petitioner and
  respondent **SSNs are never collected** (sensitive).
- **Disability accommodations:** the CCIS has a disability-accommodations section,
  so WV is in the disability gate and `petitioner.disability_accommodation` maps.
- **Respondent identifiers** (sex/race/DOB/height/weight/eyes/hair/marks) come
  from the shared physical-description block (WV is a physical-description
  jurisdiction) — failure to list them can keep the order out of the registry.
- This is a magistrate/family-court combo; the TEPO is issued by the Magistrate
  Court and a longer DVPO follows after a Family Court hearing. Source:
  courtswv.gov forms.
