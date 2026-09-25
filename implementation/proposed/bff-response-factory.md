# Tech Plan: Component-driven BFF and iOS Factory

**Status:** Proposed · **Author:** Stephan · **First slice:** Swipe · **Scope:** endpoint templates, Supabase BFF and native iOS component registry.

## 1. What we are building

The backend returns **ordered components with component-specific parameters**. iOS decodes each `item` through a registered native renderer. The backend can rearrange supported components and change their data without releasing new iOS code. A genuinely new component or incompatible parameter version still needs an app release first.

This replaces the previous fixed `player_card.payload` proposal. There are two contracts:

| Contract | Purpose | Lives in |
| --- | --- | --- |
| Backend template | Defines component tree, parameter bindings, defaults and policies such as photo ordering | Version-controlled `scout-backend` configuration |
| Endpoint response | Resolved component tree with actual authorized data; no unresolved bindings or executable expressions | JSON consumed by iOS |

[Component inventory and screenshots — PR #1](https://github.com/22annajohnson/scout-planning/pull/1) · [Figma](https://www.figma.com/design/qEktHx6Uo52KgAYNt4VHw3/Scout-V2?node-id=33-2)

## 2. Endpoint templates

Logical routes below are proposals; publish their deployed Edge Function paths in the API contract. One endpoint composes many components; do not create one network request per visual component.

| Endpoint | Template | Response root / responsibility |
| --- | --- | --- |
| `GET /v1/tabs/swipe?cursor=…&sportId=…` | `swipe_tab` | `SwipeDeck` containing ordered `UserSwipeCard` trees, `nextCursor`, plus native-shell navigation configuration |
| `GET /v1/swipe/cards/{candidateId}` | `swipe_card` | One authorized `UserSwipeCard` component tree; useful for refresh/deep-link entry |
| `GET /v1/tabs/feed` | `feed_tab` | Future feed template; same envelope, separate allowed registry subset |
| `GET /v1/tabs/chat` | `chat_tab` | Future chat template; authenticated conversation projection |
| `GET /v1/tabs/discover` | `discover_tab` | Future discovery template |
| `GET /v1/tabs/profile` | `profile_tab` | Future profile template; owner/public authorization remains explicit |
| `POST /v1/swipe/decisions` | No UI template | Typed business outcome; does not return a replacement arbitrary UI tree |

Only Swipe is implementation scope. Other tab routes establish the pattern, not approval to build those screens. Template identity never grants data access.

## 3. Resolved response example

```json
{
  "version": 1,
  "requestId": "req_123",
  "template": {"id": "swipe_card", "revision": 3},
  "components": [{
    "item": "UserSwipeCard",
    "id": "card_player_123",
    "version": 1,
    "parameters": {"candidateId": "player_123", "revision": "r1"},
    "components": [
      {
        "item": "SwipePhotoCarousel",
        "id": "photos_player_123",
        "version": 1,
        "parameters": {
          "images": [
            {"id": "photo_1", "url": "https://example.invalid/1.jpg"},
            {"id": "photo_2", "url": "https://example.invalid/2.jpg"},
            {"id": "photo_3", "url": "https://example.invalid/3.jpg"}
          ],
          "initialPhotoId": "photo_1"
        }
      },
      {"item": "Spacer", "id": "photo_bio_gap", "version": 1, "parameters": {"size": "md"}},
      {
        "item": "UserSwipeBio",
        "id": "bio_player_123",
        "version": 1,
        "parameters": {"name": "Mia", "age": 28, "sportId": "tennis"}
      }
    ]
  }]
}
```

Use `images` objects instead of bare URL strings for stable photo IDs, optional `expiresAt`, selection preservation and experiment attribution. URLs above are non-production fixtures. A `SwipeDeck` uses `parameters: {"nextCursor": null}` and contains card nodes in `components`. Exhausted initial results return `ScoutStateCard` with `parameters: {"reason":"no_candidates"}`; an exhausted pagination response must not erase previously loaded cards.

### Envelope and component rules

| Field | Meaning |
| --- | --- |
| Envelope `version` | Integer schema version, e.g. `1`; use a new major version for incompatible envelope changes |
| `template.id` / `revision` | Identifies server composition and immutable revision for diagnosis/rollback; not a client renderer version |
| Component `item` / `version` | Stable registry key and integer parameter/child-slot schema version. Never a class name loaded dynamically |
| Component `id` | Stable within the tree and unique across that response; retain across refresh/reorder for the same logical component |
| `parameters` | Validated DTO specific to `(item, version)`; not a shared bag with unrelated fields |
| `components` | Ordered children, only on containers that declare them; leaf components omit it |

Schema defines allowed parents, required slots and child cardinality. `UserSwipeCard.components` is a vertical content sequence; `SwipePhotoCarousel.components`, when present, is a constrained overlay slot for identity/distance/score/position. iOS keeps overlay anchoring and scrolling behavior native. Actions/navigation use separate shell slots outside the card scroll area. Proposed safety limits: 100 nodes per response, nesting depth 6; page size must respect the node budget. Validate these limits before release.

## 4. Backend template example

Configuration uses the **same component IDs/order**, but allows schema-defined `bindings` and server-only `policies`. Template compilation resolves bindings, permissions and policies into `parameters`, then validates the final response. It never ships executable binding expressions to iOS.

```json
{
  "templateId": "swipe_card",
  "revision": 3,
  "rootItem": "UserSwipeCard",
  "rootVersion": 1,
  "bindings": {"candidateId": "candidate.id", "revision": "candidate.revision"},
  "components": [
    {
      "item": "SwipePhotoCarousel", "id": "photos", "version": 1,
      "bindings": {"images": "candidate.authorizedPhotos"},
      "policies": {"photoPriority": "experiment", "experimentKey": "swipe_photo_order_v1"}
    },
    {"item": "Spacer", "id": "photo_bio_gap", "version": 1, "parameters": {"size": "md"}},
    {
      "item": "UserSwipeBio", "id": "bio", "version": 1,
      "bindings": {"name": "candidate.firstName", "age": "candidate.publicAge", "sportId": "candidate.sportId"}
    }
  ]
}
```

The compiler namespaces local template IDs by candidate ID, maps allowlisted binding names to server code and derives `initialPhotoId` from the resolved image order. Unavailable optional values are omitted or represented by the component's defined state; required binding failure is an error. Templates cannot read arbitrary database fields or bypass the projection's authorization.

Keep reusable component schemas/defaults separate from per-tab templates. A dictionary keyed only by component name cannot express repeated `Spacer`/bio components or reliable ordering, so use an array with stable IDs. Repeated components can have distinct parameters and policy overrides.

### Photo-order policies (backend only)

| `photoPriority` | Resolution |
| --- | --- |
| `numeric` | Sort by stored user photo position; stable photo ID breaks ties |
| `random` | Seeded shuffle pinned to viewer/candidate/deck session; retries/pagination preserve the same order |
| `experiment` | Assign a stable experiment variant, then resolve its ordering strategy; fall back to numeric when assignment is absent/disabled |

The app renders the returned order and reports actual visible photo exposure, not just payload delivery. Return an opaque exposure/assignment token in optional carousel parameters; record exposure ID, photo ID, position and session; deduplicate exposure events. Attribute later decisions/matches server-side to that assignment. Predefine the metric and eligibility rules; do not assume a match proves which photo caused it. iOS must not perform another random shuffle. Disabling the experiment preserves stable order for active sessions and uses numeric for new sessions.

## 5. Component factory table

Names marked **proposed** do not exist yet. Existing code was inspected in local ScoutSports baseline `0a5a5620de5d7adf8df11069acb0aa278c32ca29`; V2 repos are README-only.

| Wire item | Typed parameters → native output | Status / work | Failure behavior |
| --- | --- | --- | --- |
| `SwipeDeck` | `SwipeDeckParameters` → `SwipeDeckView` | Modify existing deck; registry DTO proposed | Required root failure shows retry/update state |
| `UserSwipeCard` | `UserSwipeCardParameters` → `PlayerSwipeScrollView` | Modify existing card to render ordered children | Missing candidate ID/revision rejects card response |
| `SwipePhotoCarousel` | `SwipePhotoCarouselParameters` → `SwipePhotoCarousel` | New DTO/view | Empty media shows placeholder; invalid optional media omitted |
| `UserSwipeBio` | `UserSwipeBioParameters` → `SwipeCardIdentitySection` adapter | New adapter, modify existing identity view | Missing required name fails required identity slot |
| `Spacer` | `SpacerParameters` → fixed native gap | New adapter; `xs/sm/md/lg` tokens | Invalid/unknown token uses approved default or omits optional gap |
| `SwipeScoreHeatRail` | `SwipeScoreHeatRailParameters` → native rail | New DTO/view | Invalid/unavailable score hides rail; never invents/clamps value |
| `ScoutStateCard` | `StateCardParameters` → `ScoutStateCard` | View ready to reuse; new registry adapter | Unknown reason uses localized generic fallback |
| Remaining Swipe items | One parameter DTO + renderer per inventory entry | Status and parameters in design PR #1 | Schema-declared optional/required policy |

`ComponentRegistry[(item, version)]` owns typed decoding, validation and renderer lookup. `BFFComponentDTO`, `ComponentRegistry`, `ComponentFactory`, `TemplateResponseDTO` and `BFFSwipeRepository` are proposed new types. Modify `SwipeCardProviding`, `SwipeDeckViewModel` and `PlayerSwipeCardViewModel` to consume trees instead of requiring all sections in one `CardViewModel`. Remove client ranking from this path. Never instantiate Swift classes by arbitrary server string.

### Compatibility and interaction rules

- Client reports a registry/capability revision mapping to supported `(item, version)` pairs. Backend chooses a compatible template, validates its component subset and keeps a previous compatible revision available. Capability claims do not authorize actions.
- Unknown **optional** item/version: omit with redacted diagnostic. Missing/unknown **required** slot: native retry/update fallback. The endpoint/template schema defines required slots; a server flag cannot override client validation. All-unsupported content is not an empty deck.
- Decode `item/version` before typed parameters. Decode optional children independently so one bad optional component does not fail the tree. Reject duplicate IDs, excessive depth/node count, malformed required data and unsupported envelope versions.
- BFF controls component selection/order/data/approved variants and spacing tokens. iOS owns accessibility, responsive size, gesture regions, photo/day/scroll/menu state and safe-area layout. It may adapt layout for large text. No arbitrary executable code, CSS or remotely selected network destinations.
- Buttons carry an allowlisted action such as `pass` plus candidate context. Native action dispatch maps it to the known decision endpoint. Backend still verifies eligibility and permission on every write; hiding a button is not authorization.

## 6. Decisions and errors

```json
{"candidateId":"player_123","candidateRevision":"r1","action":"pass","idempotencyKey":"decision_123"}
```

```json
{"version":1,"requestId":"req_125","result":{"decisionId":"decision_123","candidateId":"player_123","outcome":"passed"}}
```

```json
{"version":1,"requestId":"req_126","error":{"code":"stale_candidate","message":"Refresh this player before acting.","retryable":false}}
```

Decision success uses `result`; UI success uses `template/components`; failure uses `error` with meaningful HTTP status, never all together. Outcome enums, Invite/Connect context and match rules require approval. Unknown outcome blocks automatic navigation and triggers reconciliation. A lost-response retry uses the same idempotency key; backend scopes actor/key, checks payload hash and returns the original durable result. Coupled writes and match uniqueness need a database transaction.

## 7. Implementation checklist

### Backend

- [ ] Version component JSON Schemas + tab/card templates + canonical fixtures; define allowed child slots, variants, limits, action codes and required fields.
- [ ] Build template compiler over privacy-safe domain projections; resolve photo ordering and return component-capability-compatible responses. Validate output before sending.
- [ ] Verify JWT, caller RLS and visibility/block rules for both tab and direct card endpoints. Return authorized media, approximate location and shared availability only; no DOB, raw reviews or another player's calendar.
- [ ] Own eligibility, ranking, public score, feedback confidence and overlap computations. Keep absent metrics unavailable. Bind cursors to viewer/filters/session/template revision; restart safely when a revision becomes incompatible.
- [ ] Propose only missing migrations for decisions/idempotency/experiment exposure; include retention, policies, indexes and rollback. Template config stays versioned in code initially.

### iOS

- [ ] Add registry DTO/validation/renderer + fixtures for every new component version; use native design tokens. Stable IDs preserve state through template changes.
- [ ] Add repository/provider integration, capability revision and allowlisted action dispatcher; views do not call Supabase or decode raw JSON.
- [ ] Decode off the main actor and publish UI state on it; cancel/ignore stale account/filter responses. Clear account-scoped memory cache at sign-out.
- [ ] Keep actions pending until confirmed; show offline/stale state and disable writes. Refresh session once on 401; reconcile 403/404/409. Bound 429/5xx retries and honor Retry-After; write retries retain idempotency key.
- [ ] Add optional-component isolation, required-slot fallback and localized errors, including non-JSON transport failures. Never confuse unsupported content with no candidates.

### Tests, rollout and definition of done

- [ ] Shared schema/renderer fixtures: repeated components, different parameters, reordered tree, unknown item/version, required slot missing, malformed optional child, duplicate IDs, limits, empty/expired media, null versus zero, time zones/DST and accessible layout.
- [ ] Integration: auth isolation, direct-card exclusions, cursor/session consistency, stable photo assignment/retry, exposure deduplication, idempotent/concurrent decisions and old-client template negotiation.
- [ ] Approve component-driven UI architecture, score/privacy/experiment semantics and action outcomes; then create small backend/iOS tickets.
- [ ] Ship native renderers before enabling templates that need them; deploy backend fixtures/templates, flag a cohort, monitor mapping failures/latency/action errors. Roll back template revision or flag without breaking released clients; retain compatible schema versions.
- [ ] Done: reviewed contracts, all selected components registered, provider/consumer/security checks and human UI acceptance. This PR changes plans only.

## Ticket breakdown and story points

**Draft tickets, not created Jira issues.** Create them after plan approval. Ticket IDs below are local planning references, not Jira keys.

| Points | Developer time |
| --- | --- |
| 0.25 | 2 hours |
| 0.5 | 4 hours |
| 0.75 | 6 hours |
| 1 | 8 hours |
| 1.25 | 10 hours |
| 1.5 | 12 hours |
| 1.75 | 14 hours |
| 2 | 16 hours |

Estimates represent human developer time from implementation through focused tests, review fixes and handoff, not AI runtime. They exclude waiting for approval/CI/review and unresolved product research. No ticket may exceed **2 points**; if discovery expands scope, split it before implementation. Each 0.25-point increment is 2 developer hours. Section totals may exceed 2 because they contain multiple tickets.

This plan owns shared BFF/registry infrastructure and photo-policy/experiment plumbing. The design plan owns Swipe-specific component implementations, parameter schemas, data projection, business decisions and screen integration. Infrastructure tickets use fixtures/mock domain handlers; do not count production Swipe handlers here. Other tab implementations remain out of scope.

### Section effort summary

| Section | iOS points | BE points | Total points | Dev hours |
| --- | ---: | ---: | ---: | ---: |
| Contract and template foundation | 0.75 | 2 | 2.75 | 22 |
| Backend composition infrastructure | 0 | 5 | 5 | 40 |
| iOS rendering infrastructure | 7.5 | 0 | 7.5 | 60 |
| Photo policy and experiment infrastructure | 0.75 | 4.25 | 5 | 40 |
| Compatibility and release validation | 1.75 | 1.25 | 3 | 24 |
| **Total** | **10.75** | **12.5** | **23.25** | **186** |

### Contract and template foundation

| Ref | Ticket | Points | Dev hours | Scope / acceptance |
| --- | --- | ---: | ---: | --- |
| BFF-01 | [BE] Define envelope and component-node schemas | 1 | 8 | Version fields, stable IDs, child slots, limits and error envelope; valid/invalid fixtures. |
| BFF-02 | [BE] Define template bindings and reusable defaults | 1 | 8 | Allowlisted bindings, component defaults, template revision schema and repeated-node fixtures. |
| BFF-03 | [iOS] Define capability manifest and transport DTOs | 0.75 | 6 | Supported item/version manifest and envelope/header DTOs matching shared fixtures. |

### Backend composition infrastructure

| Ref | Ticket | Points | Dev hours | Scope / acceptance |
| --- | --- | ---: | ---: | --- |
| BFF-04 | [BE] Build template binding resolver | 1.5 | 12 | Resolve approved projection fields and missing-value policy; no arbitrary field lookup. |
| BFF-05 | [BE] Build tree assembly and schema validation | 1.5 | 12 | Ordered children, namespaced IDs, required slots and depth/node validation. |
| BFF-06 | [BE] Add compatible-template selection | 1 | 8 | Choose template from capability revision; previous compatible revision and unsupported-client error. |
| BFF-07 | [BE] Add authenticated endpoint and error scaffolding | 1 | 8 | Shared JWT/context handling, response serialization and redacted errors; no Swipe domain projection. |

### iOS rendering infrastructure

| Ref | Ticket | Points | Dev hours | Scope / acceptance |
| --- | --- | ---: | ---: | --- |
| BFF-08 | [iOS] Build registry decoder and parameter validation | 1.5 | 12 | Typed item/version dispatch, optional-child isolation and required-slot failures. |
| BFF-09 | [iOS] Build native renderer and container slots | 1.5 | 12 | Allowlisted renderer lookup, ordered children and native content/overlay/action slot plumbing. |
| BFF-10 | [iOS] Add Spacer and text primitive adapters | 0.5 | 4 | Fixed spacing tokens, supported text roles and token fallback; no arbitrary styling. |
| BFF-11 | [iOS] Add state-card adapter and unsupported fallback | 0.5 | 4 | Reuse ScoutStateCard; distinguish empty, malformed and unsupported responses. |
| BFF-12 | [iOS] Build authenticated BFF transport | 1 | 8 | Cancellation, one session refresh, non-JSON errors and bounded read retry. |
| BFF-13 | [iOS] Add provider integration and request lifecycle | 1.5 | 12 | Tree result interface, capability negotiation, stale-response rejection and account-scoped cache reset. |
| BFF-14 | [iOS] Add native action dispatch and retry coordination | 1 | 8 | Allowlisted intents, pending state and stable write idempotency key; mock decision transport. |

### Photo policy and experiment infrastructure

| Ref | Ticket | Points | Dev hours | Scope / acceptance |
| --- | --- | ---: | ---: | --- |
| BFF-15 | [BE] Implement numeric and session-stable random ordering | 0.75 | 6 | Stable photo IDs, position tie-breaks, seeded session ordering and retry fixtures. |
| BFF-16 | [BE] Add experiment assignment and policy fallback | 1 | 8 | Stable variant resolver, opaque assignment token and numeric fallback/disable behavior. |
| BFF-17 | [BE] Add exposure storage and ingestion | 1.5 | 12 | Reviewed migration, authenticated ingestion, deduplication, retention and RLS tests. |
| BFF-18 | [iOS] Report actual photo exposure | 0.75 | 6 | Visibility-based events with photo/position/session token; avoid payload-delivery counts. |
| BFF-19 | [BE] Add assignment-to-outcome attribution | 1 | 8 | Join authorized exposure/assignment to durable decision/match IDs; basic metric query and fixtures. |

### Compatibility and release validation

| Ref | Ticket | Points | Dev hours | Scope / acceptance |
| --- | --- | ---: | ---: | --- |
| BFF-20 | [BE] Add provider contract checks in CI | 0.75 | 6 | Validate canonical fixtures, compiler output and old-client compatible templates. |
| BFF-21 | [iOS] Add consumer contract checks in CI | 0.75 | 6 | Shared fixtures for malformed/unknown/duplicate/limit cases and renderer fallback. |
| BFF-22 | [BE] Add template rollout and rollback controls | 0.5 | 4 | Revision flag, diagnostics and rollback procedure preserving supported clients. |
| BFF-23 | [iOS] Verify renderer accessibility and compatibility | 1 | 8 | Small-screen/large-text slots, required fallback and old/new template integration. |

**Sequence:** Approve schemas and domain decisions → contract foundation → backend/iOS infrastructure → Swipe-specific tickets in design PR #1 → integrated validation. Experiment tickets depend on the carousel and durable decision/match IDs; they can ship behind a separate flag after the base deck.

**Estimate boundary:** assumes approved domain rules, available authorized source data and the existing Supabase/auth/design foundations. Missing profile/review/availability systems, new scoring algorithms, historical backfills or new destination screens need separate estimated tickets; do not hide them inside these rows. Cross-plan totals are additive because shared work is assigned once.

## References and conventions

Proposal: thin TypeScript Supabase Edge Functions over Postgres/Auth/Storage; see [Edge Functions](https://supabase.com/docs/guides/functions), [authentication](https://supabase.com/docs/guides/functions/auth), [RLS](https://supabase.com/docs/guides/database/postgres/row-level-security). Simple authorized CRUD can remain behind existing repositories.

Uses legacy `implementation/proposed/`; V2 has no template or CI. Reconcile legacy `Scout/docs/architecture/API_BOUNDARIES.md` and Discovery/Profile guidance before implementation. Roadmap/implementation owners remain unassigned. Documentation validation only; no app tests required for this PR.
