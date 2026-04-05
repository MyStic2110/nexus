# Nexus IPL 2026 Changelog

## [Day 7] - NEXUS VIRALITY
### Added
- **Reward Multipliers**: Launched dynamic scoring boosts based on real-time squad activity (Multiplier = Active Referrals).
- **Squad Fingerprinting**: Integrated canvas-based hardware signatures to prevent self-referral fraud and ensure fair play.
- **Referral Engine**: Unique high-entropy referral token generation and seamless URL parameter tracking (`?ref=CODE`).
- **Live Multiplier Dashboard**: New UI component with 30s polling for real-time squad participation status.

---

## [Day 6] - NEXUS ACCURACY
### Added
- **Scoring Completion Guards**: Implemented logic to prevent premature point distribution until an innings is statistically finalized.
- **Automated Result Rectification**: Deployed governance scripts to correct interchanged match results from high-volume API ingestions (e.g., LSG vs DC fix).
- **Session Data Resilience**: Enhanced ball-by-ball reporting to handle inconsistent API markers (e.g., Extras vs Legal balls for session 1/2).

---

## [Day 5] - NEXUS INSIGHTS
### Added
- **Playoff Probability Integration**: Extended Cricbuzz metadata to include official Points Table and playoff modeling.
- **Deeper Scorecard Analytics**: Real-time batting/bowling performance metrics integrated directly into the live match arena.
- **Growth Framework**: Initial architectural support for the Nexus Squads referral sequence.

---

## [Day 4] - NEXUS PURITY
### Added
- **My Performance History**: Created a dedicated user history dashboard showing match participation, session ID, and performance points linked directly to individual score breakdowns.
- **Autonomous Early-Finish Support**: Implemented new scoring distribution triggers to automatically assign points when matches end prematurely.
- **History Tracking API (`/users/me/history`)**: Added a backend endpoint that aggregates prediction performance.

### Changed
- **Pure MongoDB Architecture**: Completed full architectural transition away from Redis. Caching and session storage now query MongoDB directly, ensuring enhanced persistence.

### Removed
- Removed `redis` and `redis.asyncio` dependencies.
- Purged temporary diagnostic scripts and archived tools for production readiness.

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
