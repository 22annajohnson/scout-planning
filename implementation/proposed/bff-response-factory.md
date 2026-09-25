# Tech Plan: BFF Response Factory

**Status:** Proposed · **Author:** Stephan · **Scope:** iOS + Supabase backend, starting with Swipe.

## What we are building

A versioned response envelope and a typed iOS factory. The backend returns approved content types; iOS maps them into native models and views. The backend owns eligibility, scores, permissions and decision outcomes. iOS owns layout, gestures, localization and navigation.

**First slice:** `swipe_stack`, `player_card`, `empty_state`, `decision_result`. Adding an unknown type must not crash older apps, but rendering a new type still requires client support. This proposal replaces the earlier draft's `schemaVersion/data/cards` envelope with `version/components` consistently in both plans.

[Design plan and screenshots — PR #1](https://github.com/22annajohnson/scout-planning/pull/1) · [Figma source](https://www.figma.com/design/qEktHx6Uo52KgAYNt4VHw3/Scout-V2?node-id=33-2)

## 1. Implementation inventory

**Ready to go:** reuse as-is. **Modification needed:** change an existing type. **New:** proposed type to build. Existing names below were inspected in the local ScoutSports source; they are not yet ported into the README-only V2 repos. No BFF adapter is ready to reuse as-is.

| Status | Actual existing name → planned name | iOS work | Backend work |
| --- | --- | --- | --- |
| New | `BFFEnvelopeDTO`, `BFFComponentDTO` (proposed) | Decode `version`, `requestId`, `components`; typed discriminators with unknown case | Publish versioned schema and fixtures |
| New | `BFFClient` (proposed) | Authenticated transport, HTTP errors, cancellation, bounded retries | Authenticated Edge Function routes |
| Modification needed | `SwipeCardProviding` → `SwipeCardProviding` | Replace `fetchSwipeCandidates() → SwipeCandidateBatch` with paged typed-model result; add decision method; update mocks | Ordered cards, cursor and decision response |
| New | `BFFDiscoveryRepository` (proposed) | Implement `SwipeCardProviding`; transport → DTO → factory; preserve request generation | Privacy-safe projection; no SQL rows in response |
| New | `SwipeResponseFactory`, `PlayerCardModel`, `SwipeStackModel`, `EmptyStateModel`, `DecisionResultModel` (proposed) | Pure, testable DTO-to-model mapping; no networking | Stable type names and explicit unavailable states |
| Modification needed | `SwipeDeckViewModel`, `PlayerSwipeCardViewModel`, `CardViewModel` | Consume typed models; remove BFF-path dependence on `SwipeRankingContext` and `toCardViewModel()`; support pending/retry/page states | Server-owned ordering, scores and outcomes |
| Ready to go | `ScoutStateCard` | Reuse existing loading/empty/error view with localized mapped copy and retry closure | `empty_state.reason`; HTTP errors map locally |

Source: `Scout/Scout/Swipe/{Data,ViewModels,Models}` and `Scout/ScoutDesign/Sources/ScoutDesign/Components/ScoutStateCard.swift`; inspected baseline `0a5a5620de5d7adf8df11069acb0aa278c32ca29`. “Ready” applies to this fallback view's existing behavior, not proof of V2 integration or Figma visual parity.

## 2. Contract-to-iOS mapping

| BFF response | Factory output (proposed) | iOS consumer (existing) | Failure behavior | Backend requirement |
| --- | --- | --- | --- | --- |
| `swipe_stack` | `SwipeStackModel` | `SwipeDeckViewModel` → `SwipeDeckView` | Skip unsupported optional items; malformed required known card fails page | Ordered `cards`, explicit nullable `nextCursor` |
| `player_card` (nested in stack) | `PlayerCardModel` | `PlayerSwipeCardViewModel` → `PlayerSwipeScrollView` | Keep valid card when optional section fails; reject missing ID/identity | Stable ID/revision; typed privacy-safe fields |
| `empty_state` | `EmptyStateModel` | `SwipeDeckViewModel` → `ScoutStateCard` | Unknown reason uses local generic empty copy | Explicit reason; not an error disguised as empty |
| `decision_result` | `DecisionResultModel` | `SwipeDeckViewModel` | Unknown outcome stops automatic navigation and triggers reconciliation | Durable decision ID, candidate ID, authoritative outcome |
| Unknown `type` | `UnsupportedComponent` (proposed mapping result) | No view; redacted diagnostic | Skip optional unknown item; all-unknown response shows unsupported/retry, never empty | Additive types cannot replace required content for supported clients |

## 3. Response examples

All examples are **proposed JSON**, not deployed APIs. IDs/media and unavailable metrics are fixtures. `components` is a typed content list, not instructions to execute code, load arbitrary views or navigate to arbitrary URLs.

### Discovery envelope + swipe stack + player card

`GET /v1/discovery/cards?sportId=tennis&cursor=…` (logical route; deploy under the chosen Edge Function path).

```json
{
  "version": 1,
  "requestId": "req_123",
  "components": [{
    "type": "swipe_stack",
    "id": "deck_123",
    "payload": {
      "cards": [{
        "type": "player_card",
        "id": "player_123",
        "payload": {
          "revision": "r1",
          "identity": {"displayName": "Maya", "age": 28, "sportId": "tennis"},
          "photos": [],
          "distance": {"state": "approximate", "value": 2, "unit": "mi"},
          "scoutScore": {"state": "unavailable"},
          "communityRatings": [],
          "vibe": {"state": "insufficient", "reviewCount": 0, "traits": []},
          "availability": {"state": "available", "timeZone": "America/New_York", "windows": []},
          "stats": {"format": "doubles", "gamesPlayed": 0, "attendancePercent": null},
          "highlights": [],
          "bio": null,
          "allowedActions": ["pass"]
        }
      }],
      "nextCursor": null
    }
  }]
}
```

`player_card.id` is the candidate ID; do not duplicate it in `payload`. Exactly one recognized `swipe_stack` or `empty_state` is required for a discovery response. A stack's `cards` must contain at least one supported valid card; exhaustion is `empty_state`. `player_card` is not valid at the envelope root in v1. Reject duplicate IDs. `nextCursor: null` ends pagination. For a later empty page, preserve already loaded cards and stop pagination.

### Empty deck

```json
{
  "version": 1,
  "requestId": "req_124",
  "components": [{
    "type": "empty_state",
    "id": "discovery_empty",
    "payload": {"reason": "no_candidates"}
  }]
}
```

Reason codes: `no_candidates`, `filters_too_narrow`, `exhausted`. iOS supplies localized title/message and an allowlisted retry/filter action. Backend errors never become `empty_state`.

### Decision request and result

`POST /v1/discovery/decisions`; retries after a lost response use the **same** idempotency key.

```json
{
  "candidateId": "player_123",
  "candidateRevision": "r1",
  "action": "pass",
  "idempotencyKey": "decision_123"
}
```

```json
{
  "version": 1,
  "requestId": "req_125",
  "components": [{
    "type": "decision_result",
    "id": "decision_123",
    "payload": {"candidateId": "player_123", "outcome": "passed"}
  }]
}
```

Exactly one recognized `decision_result` is required for this route. `invite` and `connect` use the same request shape, with approved invitation context when needed. Their outcome enums and optional invitation/match IDs require domain approval; neither action implies immediate match creation. The example outcome `passed` is proposed too.

### Error envelope (HTTP 409 example)

```json
{
  "version": 1,
  "requestId": "req_126",
  "error": {"code": "stale_candidate", "message": "Refresh this player before acting.", "retryable": false}
}
```

Success has `components`; failure has `error`, never both. HTTP status remains authoritative. Localize by stable error code; tolerate HTML/empty proxy failures without JSON decoding crashes.

## 4. Field rules

| Field | Requirement |
| --- | --- |
| Identity / media | Required name + sport ID + revision; optional age/intro/skill system/value/provenance. Ordered photo IDs + authorized HTTPS URLs/expiry. Empty media renders placeholder. No DOB. |
| Distance / score / ratings | Explicit hidden/unavailable states; approximate units only. Public score 0–100 with calculation version when available; ratings include scale and sample count. No client scoring, no default sample numbers. |
| Vibe | Backend-selected fit/personality codes, traits with approved scale and confidence, review count. Unknown optional trait/tag is omitted. |
| Availability | Dated UTC start/end instants + viewer IANA zone; `windows` means shared overlap only. Optional `viewerWindows` may show the viewer's own time. No other player's schedule. Empty available list means no overlap; unavailable means unknown. |
| Stats / highlights / bio | Null means unknown; zero is real data. Attendance includes denominator when available. Stable highlight kinds and optional bio. |
| Allowed actions | Recognized `pass`, `invite`, `connect`; empty list disables actions. Unknown actions hidden. Server rechecks authorization. |

Full populated field examples are in [design PR #1](https://github.com/22annajohnson/scout-planning/pull/1). Commit canonical schemas/fixtures to `scout-backend` during implementation; pin that version in iOS. Database-generated types are not the public contract.

## 5. Implementation checklist

### Backend

- [ ] Approve schemas, enum values, max page/media/text sizes and client-version support window; generate shared fixtures.
- [ ] Verify JWT; derive viewer from token; apply caller-scoped RLS or explicitly authorize privileged operations. Recheck blocks/visibility/actions on writes.
- [ ] Compute eligibility, ordering, fit/score, aggregates and overlaps server-side. Return only approved public fields.
- [ ] Bind cursor to viewer/filter/snapshot; reject expired or mismatched cursors with restartable error. Never share account responses.
- [ ] Scope idempotency by actor/key; replay identical requests, reject changed payload with same key (409). Enforce decision/match uniqueness atomically in Postgres.
- [ ] Map fields to actual tables; propose only missing migrations, policies, indexes, retention/backfills. One Edge Function call alone does not make writes transactional.

### iOS

- [ ] Implement `BFFClient` → `BFFDiscoveryRepository` → `SwipeResponseFactory`; publish mapped state on the main actor.
- [ ] Decode `type` first. Decode each optional section independently so a malformed optional value cannot fail the entire synthesized `Decodable` card. Unknown payloads must not be decoded as known DTOs.
- [ ] Preserve photo/day/menu/scroll state by candidate ID; cancel or ignore stale account/filter requests.
- [ ] Use memory-only account-scoped cache; clear on sign-out. Offline display is stale and actions are disabled; no durable offline decision queue.
- [ ] Unknown version or malformed required card fails visibly. Suppress malformed optional section with diagnostic; never turn a bad page into “no players.” Do not clamp invalid scores into valid-looking data.
- [ ] Refresh session once on 401; then sign-in. On 403/404 or stale 409, disable stale action and reconcile. Bound retries for 429/5xx/timeouts; honor Retry-After. Writes only retry with original idempotency key.

## 6. Delivery and acceptance

- [ ] **Approve:** BFF adoption, availability privacy, score/trait definitions, Invite/Connect semantics and compatibility window.
- [ ] **Contract first:** canonical populated/empty/partial/unknown/error fixtures and schema validation; then separate small backend and iOS tickets.
- [ ] **Verify:** factory output, wrong versions, unknown types, all-unknown page, invalid required/optional fields, null versus zero, expired media and DST; auth isolation, block checks, pagination, concurrent duplicate writes and lost-response retry.
- [ ] **Release:** compatible backend first → flagged iOS cohort → monitor latency/errors/decoding/duplicate decisions → expand. Rollback disables feature while retaining API support for released apps.
- [ ] **Done:** approved decisions, linked tickets, provider/consumer/security checks, accessible UI fallback and human sign-off. No tickets or production changes in this PR.

## Reference and convention notes

Thin TypeScript Supabase Edge Functions are proposed; Postgres/Auth/Storage stay authoritative. Simple authorized CRUD can remain behind existing repositories. See [Edge Functions](https://supabase.com/docs/guides/functions), [authentication](https://supabase.com/docs/guides/functions/auth) and [RLS](https://supabase.com/docs/guides/database/postgres/row-level-security).

Uses legacy Scout `implementation/proposed/` convention; V2 has no template or CI. Reconcile with legacy `Scout/docs/architecture/API_BOUNDARIES.md` and approved Discovery/Profile domain guidance before tickets. V2 roadmap/owners remain unassigned. Documentation validation only; no app tests needed for this PR.
