# Changelog

All notable changes to the Nexavo Billing System will be documented in this file.

This project follows semantic versioning.

---

## v0.3.0 — 28 June 2026

### Added

* Client management module
* Package management
* Subscription management
* Wallet system
* Payment processing
* Invoice generation
* Billing engine
* Scheduled billing (Cron)
* MikroTik PPPoE automation
* MikroTik session management
* Daraja Paybill integration
* Daraja STK Push integration
* STK Push callback processing
* Africa's Talking SMS integration
* Notification logging
* Billing logging
* M-Pesa logging
* MikroTik logging

### Improved

* Atomic database transactions
* Duplicate payment protection
* Production-ready callback processing
* Git repository cleanup
* Repository versioning

### Security

* Environment variables moved to `.env`
* Virtual environment removed from Git tracking
* Log files removed from Git tracking
* Database removed from Git tracking

---

### Changed
- Added `.env.example` for easier setup.
- Improved installation instructions in `README.md`.
- Automatically create the `logs` directory during startup.
- Moved MikroTik configuration into environment variables.
- Renamed `scripts/mikrotik/services.py` to `mikrotik_services.py` to avoid module name collisions.
- Added `services/__init__.py` to make the package explicit.

# Changelog

## v0.3.1

### Added
- Customer portal dashboard service
- Dashboard base template
- Shared portal layout
- Portal navigation bar
- Bootstrap 5 integration
- Custom portal stylesheet
- Wallet summary
- Subscription summary
- Recent payments service

### Improved
- SMS service reliability
- Dashboard architecture
- Separation of business logic into services

### Fixed
- Duplicate PortalAccount lookup
- Dashboard context organization
Future releases will continue to be documented here.
