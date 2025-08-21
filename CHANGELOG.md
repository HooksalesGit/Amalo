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
### Added
- App displays version in top bar and autosaves session data.
- Refactored monolithic `app.py` into modular UI components with Pydantic models.
- Placeholders added for future credit report, property valuation and bank statement integrations.
- CI now runs ruff, black and pytest.
### Changed
- `dti` clips negative incomes to zero and additional test coverage was added.
