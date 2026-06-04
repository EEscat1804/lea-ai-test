# NE protective-order forms

Blank, official Nebraska State Court forms for the domestic-abuse protection order
packet. Public documents (except DC 6:5.12, which is confidential). **Blank
templates only — never commit a form filled with a survivor's information.**

| Form | Title | Status |
|---|---|---|
| DC 19:8 | Petition and Affidavit to Obtain Domestic Abuse Protection Order | mapped (`form.py`) |
| DC 19:1 | Protection Order Praecipe (Request for Service) | partly mapped — respondent vehicle/employer/weapon fields share intake |
| DC 6:5.12 | Social Security Numbers, Gender, Birth Date (**confidential**) | not mapped — court-only, kept out of the public file |
| DC 3:03 | Confidential Address Information | not mapped — address confidentiality election |
| DC 19:46 | Additional petitioners overflow | not mapped |

## Notes

- DC 19:8 (Rev. 09/2025, Neb. Rev. Stat. §§ 26-101 et seq.) covers the parties, an
  interpreter request, the relationship basis, the respondent identity/description
  block, prior cases, the item-7 relief list, the abuse narrative, and the
  SA/Harassment fallback request. NE's relief list is its own. See `coverage.md`.
- **Multi-form packet:** the respondent's physical description appears on DC 19:8
  item 4, and the vehicle/employer/weapon description on the **DC 19:1 praecipe**.
  NE is in both `PHYSICAL_DESCRIPTION_STATES` and `VEHICLE_DESCRIPTION_STATES`, so
  intake collects both; the assembled map carries the DC 19:8 fields plus the
  praecipe respondent-service fields (prefixed `praecipe_`) so the collected data
  is not orphaned.
- **Interpreter:** item 1 ("I do not speak English") is a foreign-language request,
  so **NE is added to the interpreter gate** and `petitioner.interpreter_language`
  maps to it.
- **Minor petitioners:** NE is in `MINOR_FILING_STATES`; a minor applicant hits the
  shared minor-filing-path gate before the NE block.
- **Address confidentiality:** item 2 offers DC 3:03, the Secretary of State's
  Address Confidentiality Program, and a safe-house option; `address_confidential`
  defaults on and the home address is never written.
- **No SSN gate:** the petition requests no child/spousal support, and the only SSN
  field is on the *confidential* DC 6:5.12 (court-only), so NE is not added to the
  SSN-for-support gate.
- **Sworn / witnessed signature:** "Do not sign until the clerk of the district
  court or a notary is present and witnesses you signing."
- Source: supremecourt.nebraska.gov self-help / court forms (DC 19:8).
