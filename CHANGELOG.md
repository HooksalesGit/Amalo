# Changelog

All notable changes to this project will be documented in this file.

## [2025-08-21]
### Added
- Project guidelines for maintaining a changelog and adding tests for new features.
- Initial `CHANGELOG.md` file.
- Test ensuring the changelog contains at least one entry.

## [2025-08-22]
### Added
- Debt cards can be marked for payoff at closing and excluded from DTI.
- Upfront fees now adjust loan amount and LTV when financed.
- Max qualifiers solver computes maximum loan given DTI and cash inputs.

## [2025-08-23]
### Added
- Expanded rules engine to flag missing variable income months, total income declines, negative rental income, DTI limit breaches, and reserve prompts.

## [2025-08-24]
### Added
- Document checklist builder with checkboxes and PDF export support.

## [2025-08-25]
### Added
- Critical warnings now require an override reason before PDF export and the reason is captured for audit.
- Expanded disclaimer clarifies calculations are estimates and stresses AUS results, lender overlays, and income stability.
- Simple audit log utility records user changes with timestamps.
- Basic Spanish translations loaded from a JSON file with UI toggle support.

## [2025-08-26]

### Fixed
- Expanded single-line conditionals in `amalo/pdf_export.py` to multi-line blocks to satisfy style checks.


### Changed
- Split combined math/pandas import lines in calculators into separate statements.
- Removed unused variable in `default_gross_up_pct` to satisfy lint.


### Removed
- Unused `Optional` import from `amalo.models`.


### Fixed
- Split semicolon-separated assignments in rules modules into separate lines to satisfy style checks.


### Fixed
- Removed unused variable in `default_gross_up_pct` to resolve linter warning.
### Changed
- Reformatted codebase using `black`.

## [2025-08-27]
### Added
- Version display in top bar and session autosave/restore.
- Refactored `app.py` into modular UI components and state helpers.
- Pydantic `Housing` model ensures numeric input validation.
- API integration stubs for credit reports, valuation, and bank statements.
- Additional tests covering negative terms, large income, rental losses, and financed fees.
- CI pipeline now checks formatting with Black and lints with Ruff.



## [2025-08-28]
### Fixed
- Avoid persisting Streamlit widget keys so buttons like "Add Income Card" no longer crash on startup.
