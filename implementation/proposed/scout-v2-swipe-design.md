# Tech Plan: Scout V2 Swipe Design

**Status:** Proposed · **Author:** Stephan · **Scope:** iOS + backend · **Design:** [06 / Swipe Card](https://www.figma.com/design/qEktHx6Uo52KgAYNt4VHw3/Scout-V2?node-id=33-2).

**Backend stack:** Java + Spring Boot. All BFF endpoints, template composition and business logic run in the Spring Boot service; Supabase Edge Functions are not used. Database, identity and object-storage providers are separate infrastructure choices; this plan does not require a provider migration.

Build the complete swipe card and its collapsed/expanded navigation. Keep photos, availability browsing and card scrolling independent from Pass / Invite / Connect. Other tab screens and previous explorations are outside this plan.

## 1. Component status

**All iOS components are New.** Nothing has been implemented in the V2 `scout-ios` repository. Every Swift name below is a proposed implementation name, even when inspired by legacy Scout code. Legacy code is reference material only; estimates include building and integrating the V2 implementation, not modifying a delivered component.

Figma was inspected on 2026-09-25. JSON cells describe component-specific parameter fragments; the registry table maps each to its wire `item`. The endpoint returns an ordered component tree.

### Navigation, actions and media

| Figma component | Status | Proposed Swift name | Exact iOS change | Backend requirement | Example JSON |
| --- | --- | --- | --- | --- | --- |
| Expanding Navigation | New | `ScoutBottomNavigationBar` + `ScoutHomeViewModel` | Build bubble/bar toggle, five-tab routing shell, left action dock, 44-point targets and state preservation. | None; navigation is local | — local menu state |
| Action Bar | New | `ScoutActionDock` | Add horizontal/vertical layouts, pending/disabled states and labels. Implement approved Pass/Invite/Connect callbacks. | Decision endpoint + allowed actions | `{"allowedActions":["pass","invite","connect"]}` |
| Action Button | New | `SwipeActionButton` | Build reusable Pass/Invite/Connect button; match sizes/colors; explicit accessibility labels and pending state | Same decision endpoint, no separate button API | `{"action":"pass","candidateId":"player_123"}` (request fragment) |
| Icon / Heart | New | `Image(systemName: "heart")` in `ScoutActionDock` | Implement native glyph or exported vector to match Figma stroke/size; no new named wrapper needed | None | — |
| Icon / Bolt | New | `Image(systemName: "bolt.fill")` in `ScoutActionDock` | Match outlined Figma bolt; label its action Invite, not Boost | None | — |
| Photo Header | New | `PlayerBackgroundView` + `SwipeCardIdentitySection` | Photo-to-dark continuous fade, stable identity/distance overlays and right score rail; accessible image fallback | Ordered authorized media | `{"photos":[{"id":"photo_1","url":"https://example.invalid/photo.jpg"}]}` |
| Photo Carousel | New | `SwipePhotoCarousel` **(proposed)** | Horizontal paging with zero/one/many images; preserve selection; do not trigger deck decision gestures | Same `photos` list | `{"photos":[]}` → placeholder |
| Carousel Position | New | `SwipeCarouselPosition` **(proposed)** | Photo 1/2/3 examples become data-sized segments and local selected index | None beyond `photos` | — derived from media count/local index |
| Player Card | New | `PlayerSwipeScrollView` + `PlayerSwipeCardViewModel` | Assemble photo → vibe → availability → stats → highlights → bio/footer; keep actions outside scroll; use typed parameters and explicit unavailable states | Ordered `UserSwipeCard.components` | `{"candidateId":"player_123","revision":"r1"}` (card parameters) |

### Identity, feedback and availability

| Figma component | Status | Proposed Swift name | Exact iOS change | Backend requirement | Example JSON |
| --- | --- | --- | --- | --- | --- |
| Identity | New | `SwipeCardIdentitySection` | Build identity with intro, sport, skill system/value and provenance; retain optional age | Safe identity, no birth date | `{"identity":{"displayName":"Maya","age":28,"sportId":"tennis"}}` |
| Distance Chip | New | `SwipeDistanceChip` | Build photo-overlay chip with Approximate/Hidden states; hidden means no distance text | Rounded distance/unit or hidden/unavailable | `{"distance":{"state":"approximate","value":2,"unit":"mi"}}` |
| Community Rating | New | `SwipeCommunityRating` | Build Friendliness/Competitive numeric tiles; Rated/New variants and honest unrated state | Metric, scale, count; no invented score | `{"communityRatings":[{"metric":"friendliness","state":"unrated"}]}` |
| Highlight Row | New | `SwipeHighlightRow` **(proposed)** | Icon/title/detail row; Reliability/Games/Style variants | Public supported highlight kind + copy | `{"highlights":[{"kind":"games","title":"24 games","detail":"Tennis"}]}` |
| Sport Stats | New | `SwipeStatHighlightsSection` + `SwipeMetricTileView` | Format/games/attendance row; correct units and unknown values; responsive layout | Counts and attendance denominator | `{"stats":{"format":"doubles","gamesPlayed":24,"attendancePercent":null}}` |
| Vibe Tag | New | `SwipeTagPill` | Add leading marker and six variants: Similar vibe, Casual matchup, Tough matchup, Goofy, Finding your vibe, Interesting combo; distinguish fit/personality | Approved fit/personality codes | `{"fitCode":"similar_vibe","personalityCodes":["goofy"]}` (vibe fragment) |
| Trait Meter | New | `SwipeTraitMeter` **(proposed)** | Segmented labeled bar for all eight traits; text equivalent, no color-only meaning | Trait code/value/scale/label | `{"code":"friendliness","value":4,"max":5,"label":"Welcoming"}` (trait item) |
| Player Vibe | New | `SwipeCardMatchupSection` | Build fit explanation, selected traits, personality tags and review count; Established/Early feedback | Aggregates + confidence; server-selected traits | `{"vibe":{"state":"insufficient","reviewCount":0,"traits":[]}}` |
| Availability Day | New | `SwipeAvailabilityDay` **(proposed)** | Build dated day view and local-time lanes from approved shared intervals. | Shared dated intervals + viewer zone | `{"date":"2026-09-29","start":"2026-09-29T22:30:00Z","end":"2026-09-30T00:00:00Z"}` (window item) |
| Week Availability | New | `SwipeWeekAvailability` **(proposed)** | Mon–Sun selection and horizontal paging; initial day from useful overlap, not hardcoded Tuesday | Same overlap windows; no separate request per day | `{"availability":{"state":"available","timeZone":"America/New_York","windows":[]}}` |
| Availability Overlap | New | `SwipeBestOverlapTeaser` | Build shared-window count, best fit and weekly browser; Great/Limited/None variants | Server overlap summary, no client threshold guesses | `{"summary":{"band":"great","sharedWindowCount":3,"bestWindowId":"window_1"}}` (availability fragment) |
| Score Heat Rail | New | `SwipeScoreHeatRail` **(proposed)** | Bottom-up 0–100 fill; Rest/Selected tap toggle reveals marker/exact value; unavailable state | Public score + calculation version, separate from ranking | `{"scoutScore":{"state":"available","value":88,"max":100,"calculationVersion":"proposal-v1"}}` |

All **21 Swipe families** are covered above. The eight trait codes are `friendliness`, `competitiveness`, `playfulness`, `skill`, `reliability`, `sportsmanship`, `communication`, `teamwork`. Figma main variants remain linked through the source page; screenshots below show composed results and feedback variants.

### Shared dependencies and screen composition

| Component / role | Status | Proposed Swift name | Work required | Backend / JSON |
| --- | --- | --- | --- | --- |
| Loading / empty / retry fallback | New | `ScoutStateCard` | Build loading/empty/error states, title/message and retry closure; map localized copy | `{"reason":"no_candidates"}` (`ScoutStateCard` parameters) |
| Glass surfaces | New | `GlassCard` / `ScoutGlassPanel` | Parameterize material/radius to match Subtle/Standard/Elevated/Accent; confirm Reduce Transparency fallback | None |
| Deck header / filter entry | New | `SwipeHeroTopBar` | Build compact title/filter control; connect approved filters | Filter request, e.g. `{"sportId":"tennis"}` |
| Deck and scroll viewport | New | `SwipeDeckScreen`, `SwipeDeckView`, `SwipeCardOverlayScrollLayout` | Typed provider data, bounded viewport, safe-area dock, separate gestures, retry/empty states | `SwipeDeck` + ordered cards and pagination; see BFF plan |
| Section headings / bio / privacy footer | New | `PlayerSwipeScrollView` composition | Add `UserSwipeBio` and `SwipeText` adapters (proposed) for registered identity/bio/headings/footer composition; build native views and V2 text styles | `{"bio":"Weeknight doubles are my happy place."}` |

Build V2 typography, spacing, color, glass and icon foundations from the approved design. Legacy implementations can inform design decisions but do not count as completed work or as a prerequisite already available in `scout-ios`.

## 2. Component composition contract

The BFF chooses component order and component-specific parameters. iOS uses an allowlisted registry to render native SwiftUI. This replaces the earlier fixed `player_card.payload` contract. Wire names are stable API identifiers, even when the underlying Swift type has another name.

| Wire `item` (each at component version 1) | Native implementation / parameter contract |
| --- | --- |
| `SwipeDeck`, `UserSwipeCard` | Build native deck/card views; deck has `nextCursor`, card has `candidateId`/`revision`; ordered child `components` |
| `SwipePhotoCarousel` | Proposed carousel; `images[{id,url,expiresAt?}]`, `initialPhotoId`; ordered overlays in optional `components` |
| `SwipePhotoHeader`, `SwipeCarouselPosition` | Header adapter + proposed position view; header uses `image`; position reads parent carousel selection/count |
| `UserSwipeBio` | New registry adapter using `SwipeCardIdentitySection`; `name`, optional `age`, `intro`, `sportId`, `skill`, `bio` |
| `SwipeDistanceChip`, `SwipeScoreHeatRail` | Typed distance `state/value/unit`; score `state/value/max/calculationVersion` |
| `SwipeCommunityRating`, `SwipeHighlightRow`, `SwipeSportStats` | One rating item; one highlight item; stats object respectively |
| `SwipeVibeTag`, `SwipeTraitMeter`, `SwipePlayerVibe` | Fit/personality code; trait code/value/max/label; aggregate state/count/confidence plus ordered tag/meter children |
| `SwipeAvailabilityDay`, `SwipeWeekAvailability`, `SwipeAvailabilityOverlap` | Day windows; week zone/windows; overlap summary + weekly child. Only shared time and optional viewer windows |
| `SwipeActionButton`, `SwipeActionBar`, `SwipeExpandingNavigation` | Allowlisted `action`, action list, or native tab IDs. Pending/expanded state stays local |
| `SwipeHeartIcon`, `SwipeBoltIcon` | Native glyph adapters; size token only; action belongs to parent button |
| `Spacer` | Native fixed gap: `size` token `xs/sm/md/lg`; not an unbounded SwiftUI expanding spacer |
| `SwipeText`, `ScoutStateCard` | Allowlisted text role + text; or fallback reason. Neither accepts arbitrary styling/code |

Every registry entry needs its own typed parameter DTO, validation, renderer and fixtures. Child slots are defined by the parent schema; not every component can contain arbitrary children. The three new composition adapters (`Spacer`, `UserSwipeBio`, `SwipeText`) are additional implementation work, not additional Figma families.

### Example card endpoint

`GET /v1/swipe/cards/player_123` returns the versioned envelope described in [BFF PR #2](https://github.com/22annajohnson/scout-planning/pull/2), with this card inside its root `components` array. This shortened example demonstrates photo → gap → bio. The production template also includes the feedback, availability, stats and highlights above; the Figma template can place identity inside the carousel overlay slot.

```json
{
  "item": "UserSwipeCard",
  "id": "card_player_123",
  "version": 1,
  "parameters": {
    "candidateId": "player_123",
    "revision": "r1"
  },
  "components": [
    {
      "item": "SwipePhotoCarousel",
      "id": "photos_player_123",
      "version": 1,
      "parameters": {
        "images": [
          {
            "id": "photo_1",
            "url": "https://example.invalid/1.jpg"
          },
          {
            "id": "photo_2",
            "url": "https://example.invalid/2.jpg"
          },
          {
            "id": "photo_3",
            "url": "https://example.invalid/3.jpg"
          }
        ],
        "initialPhotoId": "photo_1"
      }
    },
    {
      "item": "Spacer",
      "id": "photo_bio_gap",
      "version": 1,
      "parameters": {
        "size": "md"
      }
    },
    {
      "item": "UserSwipeBio",
      "id": "bio_player_123",
      "version": 1,
      "parameters": {
        "name": "Mia",
        "age": 28,
        "intro": "Good rallies. Better company.",
        "sportId": "tennis"
      }
    }
  ]
}
```

Use image objects rather than bare `imageUrls` so selection, refresh and experiments refer to stable photo IDs. iOS renders the returned array order; the backend resolves numeric, randomized or experiment-based ordering before returning it. Menu expansion and selected photo remain local UI state.

### Decision request example

```json
{
  "candidateId": "player_123",
  "candidateRevision": "r1",
  "action": "pass",
  "idempotencyKey": "decision_123"
}
```

The same key is reused on retry. Invite/Connect outcomes and required invitation context must be approved before implementation. Action names must match approved business semantics.

## 3. Implementation checklist

### iOS

- [ ] Build the components above; fixture every Figma variant, including hidden distance, unrated feedback, no overlap, failed media and no score.
- [ ] Use provider → component decoder/registry → typed parameters → native renderer. Add a renderer/schema/fixtures for each new item; views do not decode JSON or call backend services directly. Keep interaction state local.
- [ ] Isolate horizontal photo/day paging from vertical scrolling. Use explicit decision buttons first; deck-swipe thresholds need a product decision.
- [ ] Keep controls outside the scroll area; preserve card/photo/day/scroll state through menu expansion and tab changes. Do not hide the only route back to navigation.
- [ ] Add loading, retry, exhausted/filter-empty, offline and pending states. Freeze duplicate actions and retain the card on failure.
- [ ] Verify small screens, Dynamic Type, VoiceOver order/action labels, 44-point targets, contrast, Reduce Motion/Transparency and deployment-target glass fallback.

### Backend

- [ ] Supply endpoint-specific ordered component trees through the Java/Spring Boot BFF. Compile versioned tab/card templates against client-supported component versions; contract details in PR #2.
- [ ] Resolve photo-order policy on the server; pin order per deck session and return stable photo IDs/assignment metadata for exposure attribution.
- [ ] Own eligibility, exclusions, scoring, fit, selected traits, feedback confidence and timezone-safe overlap computation. Do not ship Figma sample values as defaults.
- [ ] Authenticate callers with Spring Security; enforce service-layer authorization/privacy; expose authorized media, approximate location and shared time only. Recheck visibility/blocks/permissions when acting.
- [ ] Make decisions idempotent; return authoritative outcomes. Use transactional uniqueness for decisions/matches.
- [ ] Map fields to approved source tables. Propose missing migrations, indexes, policies and backfills separately; no schema changes in this PR.

## 4. Decisions needed before tickets

| Decision | Proposed default / unresolved requirement |
| --- | --- |
| Availability privacy | Figma lanes show You/Player/Both but notes say shared time only. Ship overlap + optional viewer lane; omit Player lane until visibility rules and revised UI are approved. |
| Metrics | Approve Scout score meaning/version, eight trait scales, review thresholds, fit labels, overlap bands and attendance denominator. |
| Actions / sport / routes | Approve Invite versus Connect, tennis/NTRP versus initial pickleball scope, filter behavior and the five tab destinations. Navigation shell does not implement those destination screens. |
| Catalog differences | Keep Community Rating and Action Bar reusable; latest full card uses Player Vibe and Expanding Navigation. Do not insert extra ratings because older captions mention them. Hidden/New variants must not leak their sample text. |

## 5. Delivery and acceptance

- [ ] **Approve:** decisions above, field-source mapping and BFF contract; then create small paired iOS/backend tickets.
- [ ] **Build:** components against fixtures → compatible backend → factory integration → navigation/actions.
- [ ] **Verify:** snapshots for all variants/small screens/large text; real-device nested gestures/accessibility; backend privacy/blocks/pagination/DST; duplicate actions and offline/lost-response retries.
- [ ] **Release:** backend first, feature-flagged iOS cohort, then expand. Monitor latency/decoding/action errors without profile payloads. Rollback disables the flag without deleting data.
- [ ] **Done:** every table row implemented or explicitly deferred, real authorized data, passing checks and human acceptance. No implementation tickets created by this proposal.

## Ticket breakdown and story points

**Draft tickets, not created Jira issues.** Create them after plan approval. All iOS work is new implementation in V2; no legacy component is assumed available.

Estimates use the agreed developer-effort scale in 0.25-point increments, including focused tests, review fixes and handoff. Waiting and unresolved product research are excluded. Every ticket must be **2 points or less**; split expanded scope before implementation. Section totals may exceed 2 because they contain multiple tickets.

This plan owns Swipe feature work. Shared envelope/compiler/registry, Spacer/text primitives, app/bootstrap/session/CI foundations, generic transport/retries, capability negotiation and photo-order experiments are estimated only in BFF PR #2. Each iOS feature ticket includes its own parameter DTO/renderer adapter and focused checks; the registration ticket wires them together rather than rebuilding them.

### Section effort summary

| Section | iOS points | BE points | Total points |
| --- | ---: | ---: | ---: |
| Component contracts and visual foundations | 2.25 | 1 | 3.25 |
| Media and identity | 5 | 0 | 5 |
| Feedback, stats and availability | 6.5 | 0 | 6.5 |
| Navigation, actions and card integration | 9 | 0 | 9 |
| Swipe backend domain and templates | 0 | 11 | 11 |
| Feature acceptance and rollout | 2 | 1.5 | 3.5 |
| **Total** | **24.75** | **13.5** | **38.25** |

### Component contracts and visual foundations

| Ticket | Points | Scope / acceptance |
| --- | ---: | --- |
| [iOS] Build V2 design tokens and typography | 1 | Color/spacing/type/radius tokens, asset setup, accessible semantic styles and preview foundation. |
| [BE] Define Swipe-specific parameter schemas | 1 | Schemas/fixtures for the inventory, approved field sources and unavailable states; use shared BFF envelope. |
| [iOS] Build glass surface components and variants | 1 | Required material/radius variants and Reduce Transparency fallback. |
| [iOS] Build Heart and Bolt glyph assets | 0.25 | Use approved native/vector glyphs with correct stroke/size; verify at action-button size. |

### Media and identity

| Ticket | Points | Scope / acceptance |
| --- | ---: | --- |
| [iOS] Build photo carousel and position indicator | 1.5 | Paging, stable photo selection, zero/one/many images and position segments. |
| [iOS] Build photo header and continuous fade | 1.25 | Responsive photo/fade composition and overlay slots; media failure state. |
| [iOS] Build identity, UserSwipeBio and distance components | 1.5 | Identity/intro/skill/bio mapping, optional age and hidden/approximate distance. |
| [iOS] Build Scout score heat rail | 0.75 | Rest/selected/unavailable states, exact-value marker and accessible text. |

### Feedback, stats and availability

| Ticket | Points | Scope / acceptance |
| --- | ---: | --- |
| [iOS] Build community rating and highlight rows | 1 | Rated/unrated metric tiles and Reliability/Games/Style rows. |
| [iOS] Build sport-stat tiles | 0.75 | Format/games/attendance units, null states and responsive layout. |
| [iOS] Build vibe tags and trait meters | 1.25 | Six tag variants and eight typed trait-meter variants with accessible equivalents. |
| [iOS] Build Player Vibe composition | 1 | Fit explanation, selected traits, personality tags, review count and early-feedback state. |
| [iOS] Build availability day and week browser | 1.5 | Dated shared intervals, local time, horizontal paging and day selection. |
| [iOS] Build overlap summary and unavailable states | 1 | Great/Limited/None and unknown states; best-window/week integration without private lanes. |

### Navigation, actions and card integration

| Ticket | Points | Scope / acceptance |
| --- | ---: | --- |
| [iOS] Build action buttons | 0.75 | Pass/Invite/Connect variants, labels, pending/disabled states and focused previews. |
| [iOS] Build horizontal and vertical action dock | 0.75 | Compose buttons into both layouts; native shell slot and pending-state integration. |
| [iOS] Build five-tab app routing shell | 1 | Root navigation state, typed routes and placeholder destinations; destination feature screens excluded. |
| [iOS] Build floating navigation and expanding-menu transition | 1.25 | Menu/dock transition, tab selection, 44-point targets and preserved local state. |
| [iOS] Build card scroll viewport and feature view models | 1.5 | New native card/deck view models, independent gestures, media selection and safe-area slots. |
| [iOS] Build deck header and filter entry | 0.75 | Compact title/filter control, typed filter state and accessible sheet/entry integration. |
| [iOS] Register Swipe renderers and compose card | 1.5 | Connect new feature adapters to shared registry; production template order, headings/bio/footer and safe-area slots. |
| [iOS] Integrate deck pagination and decision outcomes | 1.5 | Wire shared provider/dispatcher to Swipe screen, loading/retry/offline states and confirmed outcomes. |

### Swipe backend domain and templates

| Ticket | Points | Scope / acceptance |
| --- | ---: | --- |
| [BE] Build authorized identity and media projection | 1.5 | Direct-card/read paths enforce profile visibility; safe identity, skill, media expiry and approximate location. |
| [BE] Build public feedback and stats projection | 1.5 | Approved aggregate sources, public score version, confidence/traits/highlights; unknown states, no new scoring research. |
| [BE] Build availability overlap projection | 1.5 | Approved availability sources, viewer zone, dated intersections, summary and DST/midnight cases. |
| [BE] Build eligible candidate paging | 1.5 | Eligibility/exclusions, server ordering, viewer/filter/session-bound cursors and exhaustion. |
| [BE] Add Swipe tab and card templates/endpoints | 1 | Compile feature projections using shared compiler; compatible native slots and photo-policy integration. |
| [BE] Add decision persistence and idempotency | 1.5 | Reviewed constraints/migration, actor/key payload checks, replay and transactional uniqueness. |
| [BE] Implement Pass and Connect handlers | 1.5 | Approved semantics, visibility/block rechecks and authoritative result/match behavior. |
| [BE] Implement Invite handler | 1 | Approved context validation and invitation outcome; no chat/notification feature implementation. |

### Feature acceptance and rollout

| Ticket | Points | Scope / acceptance |
| --- | ---: | --- |
| [iOS] Verify component snapshots and accessibility | 1 | Inventory variants, small screens, Dynamic Type, VoiceOver and motion/transparency fallbacks. |
| [iOS] Verify device gestures and end-to-end deck flows | 1 | Nested scrolling, menu persistence, paging, duplicate actions, offline and lost responses. |
| [BE] Verify Swipe authorization and concurrency | 1 | Cross-user/direct-card privacy, blocked candidates, cursor changes and concurrent decision integration. |
| [BE] Enable Swipe feature rollout controls | 0.5 | Feature-specific flag/metrics, staged enablement and rollback check using shared template infrastructure. |

**Sequence:** Approve field sources/privacy/score/action semantics → shared BFF foundation in PR #2 → feature schemas → components and projections in parallel → templates/handlers → deck integration → feature acceptance. Invite/Connect depend on approved lifecycle rules; experiments are not required to finish the initial deck.

**Estimate boundary:** assumes approved domain rules, available authorized source data and an available Java/Spring Boot service environment with configured database, identity and object storage. V2 app/session/design foundations are explicitly ticketed across these plans. Missing profile/review/availability systems, new scoring algorithms, historical backfills or new destination screens need separate estimated tickets; do not hide them inside these rows. Cross-plan totals are additive because shared work is assigned once.

## Convention notes

Uses legacy Scout `implementation/proposed/` and compact tech-plan sections because V2 planning has no template. Reconcile approved legacy Discovery/Profile plans and `Scout/docs/architecture/API_BOUNDARIES.md` before implementation; no migration approval is implied. V2 owner/roadmap links remain unassigned. Documentation-only validation; no planning CI or app tests in this PR.

## Design Captures

Exported directly from Figma on 2026-09-25; fictional profile and generated sample photography. Images are reference evidence, not production assets.

[Full player card, node 40:1632](https://www.figma.com/design/qEktHx6Uo52KgAYNt4VHw3/Scout-V2?node-id=40-1632)

![Full player card](assets/scout-v2-swipe/player-card.png)

[Navigation states, node 132:9560](https://www.figma.com/design/qEktHx6Uo52KgAYNt4VHw3/Scout-V2?node-id=132-9560)

![Collapsed and expanded navigation](assets/scout-v2-swipe/navigation.png)

[Tags, eight traits and feedback states, node 52:2049](https://www.figma.com/design/qEktHx6Uo52KgAYNt4VHw3/Scout-V2?node-id=52-2049)

![Player vibe component variants](assets/scout-v2-swipe/vibe-components.png)
