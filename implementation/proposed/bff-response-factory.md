# Tech Plan: BFF Response Interpretation and Factory

## Status / Owner / Planning Level

Proposed architecture — approval required before implementation tickets. Planning author: Stephan; iOS/backend implementation owners unassigned. Cross-cutting API proposal with Swipe as the first feature slice.

## Problem / Goals / Non-goals

Give iOS one predictable translation boundary between BFF responses and feature models. Prevent database rows, missing-data guesses and business rules from leaking into SwiftUI. “Factory” here means a typed response-to-model mapper; the Scout software factory must produce contract fixtures and paired iOS/backend work from this plan. It does not mean a backend-controlled SwiftUI layout engine.

Start with Discovery; avoid a universal component registry, new Java deployment, client-side scoring or a rewrite of every Supabase call.

## Context / References

- [Scout V2 swipe design](https://www.figma.com/design/qEktHx6Uo52KgAYNt4VHw3/Scout-V2?node-id=33-2): identity, photos, score, vibe, availability, stats and decisions are the first consumer.
- The new planning/iOS/backend repos contain only READMEs. Names and contracts below are proposals, not existing implementations. Use legacy `implementation/proposed/` and the tech-plan template's relevant sections until V2 conventions exist.
- Reconcile legacy ScoutSports `Scout/docs/architecture/API_BOUNDARIES.md` and approved Discovery/Profile domain guidance before implementation. This proposal does not silently supersede them. V2 foundation/roadmap/Jira references are not assigned yet.
- [Supabase Edge Functions](https://supabase.com/docs/guides/functions), [function authentication](https://supabase.com/docs/guides/functions/auth), [RLS](https://supabase.com/docs/guides/database/postgres/row-level-security): TypeScript/Deno runtime and caller-authorized data access are available foundations.

## Architecture / Ownership

`SwiftUI → @MainActor feature model → DiscoveryRepository → BFFClient → DTO decoder → DiscoveryCardFactory → domain/presentation model`

| Layer | Owns | Must not own |
| --- | --- | --- |
| Backend domain services | Eligibility, rank, fit/score calculations, visibility, decision/match semantics | iOS layout or navigation state |
| Edge Function BFF | Authenticated orchestration, privacy-safe projection, contract validation, HTTP errors | Duplicated domain rules per screen |
| BFFClient / repository | Session token, transport, decoding, pagination, cancellation, retry coordination | View construction |
| Pure factory | Validated DTO → typed model; explicit absent/unknown/error handling | Networking, persistence, ranking, match creation |
| Feature view model / SwiftUI | Loading/pending/error state, locale formatting, photo/day/menu selection, native rendering | Raw JSON, SQL rows, permission decisions |

Use Supabase Postgres/Auth/Storage and thin TypeScript Edge Functions initially. SQL constraints/transactions enforce integrity; services own business policy. Direct Supabase access can remain for simple authorized operations behind repositories. Only the selected BFF feature moves to the new boundary.

## API / Backend Requirements

Proposed logical routes: `GET /v1/discovery/cards?cursor=…&sportId=…` and `POST /v1/discovery/decisions`; map them under a deployed Edge Function route during implementation. Publish the exact paths in a versioned OpenAPI/JSON Schema contract in `scout-backend` with shared JSON fixtures. Generated database types are not the public DTO contract.

Success envelope: required `schemaVersion: 1`, `requestId`, `data`; page data contains `cards` and nullable `nextCursor`. Error envelope: `schemaVersion`, `requestId`, `error: {code, message, retryable}` with meaningful HTTP status. Do not return HTTP 200 for failure. Proxy/network failures may not contain JSON; iOS must handle those too.

| Card field | Contract / interpretation |
| --- | --- |
| `id`, `revision`, `identity` | Required stable candidate ID, revision, name and sport ID; optional age/intro/skill value with system and provenance. No DOB. |
| `photos[]` | Ordered stable photo IDs, authorized HTTPS URLs and optional expiry. Empty array is valid; never synthesize photos. |
| `distance` | Explicit hidden/unavailable/approximate state; approximate value + unit only, no coordinates. |
| `scoutScore` | Available with value 0–100 + calculation version, or unavailable; distinct from internal ranking. |
| `vibe` | Available/insufficient/unavailable state, fit code, explanation, personality codes, review count and selected traits. Backend selects traits and owns approved scale definitions/confidence. |
| `availability` | Available/unavailable state; dated overlap intervals with UTC instants, viewer IANA zone and optional viewer-only windows. Empty overlaps mean no shared time. No other player's full schedule. |
| `stats`, `highlights`, `bio` | Nullable metrics with units/denominators, stable highlight types and optional text. Unknown differs from zero. |
| `allowedActions[]` | Recognized `pass`, `invite`, `connect`; an empty list disables decisions. Permission is rechecked server-side. |

Optional sections must have defined schemas and state discriminators; they are not arbitrary dictionaries. Define maximum page size, media count and text lengths in the approved contract. Bind opaque cursors to viewer, filters and ordering snapshot; reject expired/mismatched cursors with a restartable error. Do not share discovery responses across accounts.

Decision request: `{candidateId, candidateRevision, action, idempotencyKey, invitationContext?}`. Response: `{decisionId, outcome, candidateId, invitationId?, matchId?}` inside the success envelope. Approve the outcome enum and Invite/Connect domain semantics before implementation; clients navigate only from a recognized authoritative outcome. Scope idempotency to actor/key, store payload hash/result, replay identical requests, reject key reuse with changed payload (409), and atomically enforce decision/match uniqueness. A retry after a lost response uses the same key.

Authenticate JWTs and derive viewer identity from the verified token. Use caller-scoped RLS for reads; authorize privileged operations explicitly. Recheck blocks, candidate visibility and action eligibility on writes. No service credentials, precise locations, hidden schedules or raw reviews in the app. Redact logs; retain request IDs, latency and stable error codes.

## iOS Factory / Error Policy

Implement `BFFEnvelope<T: Decodable>`, feature DTOs, `DiscoveryRepository` and a pure `DiscoveryCardFactory`. Decode DTOs off the main thread; publish UI state on the main actor. Inject transport and factory for fixtures. Views receive typed models, not DTOs. Keep photo/day/menu selection local and keyed by candidate ID; discard stale results when account/filter/request generation changes.

| Input / failure | Required behavior |
| --- | --- |
| Unknown additive JSON key | Ignore; backward compatible within v1 |
| Unsupported envelope version / malformed required card ID or identity | Fail the response visibly with retry/update state; log redacted contract error, never silently show an empty deck |
| Missing/null optional metric | Show unavailable or omit the section; never replace with 0, an invented score or fixture text |
| Malformed optional section / out-of-range score | Suppress that section with a recorded mapping error; do not clamp bad server data into credibility |
| Unknown optional trait/tag/highlight kind | Omit unsupported item; preserve the rest of the card |
| Unknown action / decision outcome | Hide unknown action; stop automatic outcome navigation and refresh/reconcile after a submitted decision |
| Invalid/expired media URL | Placeholder; repository refreshes authorized URL when appropriate; factory never fetches it |
| Empty valid `cards` | Empty-deck state, not a parsing error |
| 401 | Refresh session once, replay only with safe/idempotent semantics; then request sign-in |
| 403/404 candidate unavailable; 409 stale revision | Disable stale action and refresh/reconcile; do not claim success |
| 429 / transient 5xx / timeout | Bounded backoff with jitter and Retry-After; automatic reads only, writes require same idempotency key |
| Offline | Preserve only authorized in-memory display, show stale/offline state, disable decisions; no durable offline decision queue in v1 |

Factory maps semantic values; locale-aware dates, time zones, units and accessible strings belong to presentation formatting. Clear account-scoped memory on sign-out/account switch. Proposal: memory-only card cache for v1; persisted sensitive profiles require separate retention approval.

## Database Changes / Dependencies / Open Questions

No migration is part of this PR. Backend implementation must map approved source tables, identify required aggregate/read models, and propose only missing persistence for idempotency/decisions. Migrations must include RLS, uniqueness, indexes, retention and rollback/backfill requirements. A single Edge Function call is not automatically a transaction; use a transactional database operation for coupled writes.

Approve BFF adoption, public score and trait semantics, availability privacy, Invite versus Connect, API version support window and deployment target before dependent implementation. Prefer fixed typed feature contracts; revisit server-driven section composition only if a real release requirement justifies it.

## Software Factory Deliverables / Milestones

1. **Contract first:** approve schemas, field-source/privacy mapping, statuses and errors; commit valid, empty, partial, unknown-enum and failure fixtures. Keep one canonical fixture set; pin its version in both repos.
2. **Backend:** implement projection + decision handler; validate emitted responses against schema; add auth/RLS, exclusion, idempotency and transaction tests.
3. **iOS:** implement client/repository/factory against those fixtures; integrate one swipe screen and accessible fallback states. Do not generate one Swift view per database table.
4. **Integration:** CI consumes the same fixture version on both sides; contract-breaking changes require a new version and coordinated rollout. Create separate small backend/iOS tickets only after approval.

## Testing / Rollout / Definition of Done

Contract tests cover populated/empty/partial cards, wrong version, unknown enums, malformed required versus optional fields, null versus zero, expired media and date/DST cases. Integration tests cover account isolation, private-field absence, blocked candidates, paging/filter changes, duplicate and concurrent writes, lost-response retry and token expiry. UI tests cover pending/retry/empty states and preserving navigation state without duplicating decisions.

Deploy compatible backend contracts first, enable the iOS feature flag for a small cohort, monitor latency/HTTP errors/decode failures/duplicate decisions with request IDs, then expand. Rollback disables the feature or restores a compatible deployment; keep the supported API alive for released apps. No destructive migration rollback.

Done: approved contract and domain decisions; linked tickets implemented; shared fixtures and provider/consumer/security tests pass; old supported client contract still works; no raw response handling in views; rollout and human review complete. This PR changes documentation only; no tests or CI are configured in the planning repo. Jira breakdown follows approval.
