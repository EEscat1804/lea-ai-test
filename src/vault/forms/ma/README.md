# MA protection-from-abuse forms

Blank, official Massachusetts Trial Court Chapter 209A forms. Public documents.
**Blank templates only — never commit a form filled with a survivor's
information.**

| Form | Title | Status |
|---|---|---|
| Complaint for Protection from Abuse | G.L. c. 209A | mapped (`form.py`) |
| Affidavit | abuse statement | mapped (within `form.py`) |
| Plaintiff Confidential Information Form | sealed contact info | partial (name/DOB/phone/email; home address never collected) |
| Defendant Information Form | defendant identifiers for police | mapped (within `form.py`) |

## Notes

- The 209A packet (TC0061) is four forms. The Vault maps the Complaint, the
  Affidavit statement, the confidential-form fields it safely has, and the
  Defendant Information Form (which uses the shared physical/vehicle blocks).
- **Protection by design:** the plaintiff's home/work/school address is **not
  collected** by intake (only a safe mailing address), so it never reaches the
  public complaint. The relief list also includes explicit "keep my address off
  the order" requests, recommended in the intake prompt. See `coverage.md`.
- The nature-of-abuse boxes and relief boxes are flagged `needs_legal_review`.
- Drop the official blank fillable PDFs here for lea-be-core's renderer. Source:
  mass.gov / Massachusetts Trial Court forms.
