# Nexus IPL 2026 Changelog

## [Day 4] - NEXUS PURITY
### Added
- **My Performance History**: Created a dedicated user history dashboard showing match participation, session ID, and performance points linked directly to individual score breakdowns.
- **Autonomous Early-Finish Support**: Implemented new scoring distribution triggers to automatically assign points when matches end prematurely (prior to completely finishing the 20th over).
- **History Tracking API (`/users/me/history`)**: Added a backend endpoint that seamlessly aggregates prediction performance `session_scores` with official match intelligence.

### Changed
- **Pure MongoDB Architecture**: Completed full architectural transition away from Redis. Live leaderboard queries, prediction caching, and session storage now query MongoDB directly, ensuring enhanced persistence and eliminating connection instability.

### Removed
- Removed `redis` and `redis.asyncio` dependencies from the codebase.
- Deactivated Redis Pub/Sub mechanisms in WebSocket operations.
- Cleaned the main `scripts/` directory by archiving 9 debug/utility tools into a dedicated `tools/` folder.
- Purged temporary diagnostic scripts and log leftovers for production deployment readiness.

---

## [Day 3] - NEXUS RESILIENCE
### Added
- Resilient API scraping logic to dynamically bypass Cricbuzz payload anomalies.
- Gap-free sequential database integration for live match operations.
- PWA optimization and mobile fluidity fixes.

---

## [Day 2] - INFRASTRUCTURE & SPEED
### Added
- Implemented Nexus Production Logger for systematic backend monitoring.
- Established strict governance rules for 'Death Over' predictions (15.0 over cutoff).
- *Initial integration of Redis (Removed in Day 4)*.

---

## [Day 1] - THE FOUNDATION
### Added
- Created the core Python FastAPI Backend structure.
- Designed the "Nexus" Premium Glassmorphism UI syntax.
- Enabled secure Google OAuth2 One-Tap authentication.
- Implemented MongoDB Cluster integration for initial data warehousing.
