# Tech Plan: Scout V2 Swipe Design

**Status:** Proposed · **Author:** Stephan · **Scope:** iOS + backend · **Design:** [06 / Swipe Card](https://www.figma.com/design/qEktHx6Uo52KgAYNt4VHw3/Scout-V2?node-id=33-2).

Build the complete swipe card and its collapsed/expanded navigation. Keep photos, availability browsing and card scrolling independent from Pass / Invite / Connect. Other tab screens and previous explorations are outside this plan.

## 1. Component status

| Status | Meaning |
| --- | --- |
| **Ready to go** | Existing implementation can be reused as-is for the stated role. Still needs V2 integration. |
| **Modification needed** | Existing implementation needs the specific change listed. |
| **New** | No matching reusable implementation found; the Swift name is a proposal. |

**Baseline:** local ScoutSports source at `0a5a5620de5d7adf8df11069acb0aa278c32ca29`, inspected for this revision. V2 `scout-ios` is README-only: these statuses describe legacy reuse, not completed V2 work. Existing names are exact Swift declarations; **(proposed)** names do not exist yet. Figma was inspected on 2026-09-25. JSON cells are small contract fragments; full examples follow.

### Navigation, actions and media

| Figma component | Status | Existing / planned Swift name | Exact iOS change | Backend requirement | Example JSON |
| --- | --- | --- | --- | --- | --- |
| Expanding Navigation | Modification needed | `ScoutBottomNavigationBar` + `ScoutHomeViewModel` | Existing bubble/bar toggle stays; add five-tab order, left action dock, 44-point targets and state preservation. Current `ScoutHomeTab` has only Swipe/Feed. | None; navigation is local | — local menu state |
| Action Bar | Modification needed | `ScoutActionDock` | Add horizontal/vertical layouts, pending/disabled states and labels. Replace Boost/Like meaning with approved Invite/Connect callbacks. | Decision endpoint + allowed actions | `{"allowedActions":["pass","invite","connect"]}` |
| Action Button | New | Private `ScoutActionDock.actionButton` → `SwipeActionButton` **(proposed)** | Extract reusable Pass/Invite/Connect button; match sizes/colors; explicit accessibility labels and pending state | Same decision endpoint, no separate button API | `{"action":"pass","candidateId":"player_123"}` (request fragment) |
| Icon / Heart | Modification needed | `Image(systemName: "heart")` in `ScoutActionDock` | Retain glyph approach or use exported vector to match Figma stroke/size; no new named wrapper needed | None | — |
| Icon / Bolt | Modification needed | `Image(systemName: "bolt.fill")` in `ScoutActionDock` | Match outlined Figma bolt; label its action Invite, not Boost | None | — |
| Photo Header | Modification needed | `PlayerBackgroundView` + `SwipeCardIdentitySection` | Photo-to-dark continuous fade, stable identity/distance overlays and right score rail; accessible image fallback | Ordered authorized media | `{"photos":[{"id":"photo_1","url":"https://example.invalid/photo.jpg"}]}` |
| Photo Carousel | New | `SwipePhotoCarousel` **(proposed)** | Horizontal paging with zero/one/many images; preserve selection; do not trigger deck decision gestures | Same `photos` list | `{"photos":[]}` → placeholder |
| Carousel Position | New | `SwipeCarouselPosition` **(proposed)** | Photo 1/2/3 examples become data-sized segments and local selected index | None beyond `photos` | — derived from media count/local index |
| Player Card | Modification needed | `PlayerSwipeScrollView` + `PlayerSwipeCardViewModel` | Assemble photo → vibe → availability → stats → highlights → bio/footer; keep actions outside scroll; replace hardcoded/mock assumptions | `player_card` typed payload | `{"type":"player_card","id":"player_123","payload":{}}` (shape only) |

### Identity, feedback and availability

| Figma component | Status | Existing / planned Swift name | Exact iOS change | Backend requirement | Example JSON |
| --- | --- | --- | --- | --- | --- |
| Identity | Modification needed | `SwipeCardIdentitySection` | Remove score capsule from identity; add intro, sport, skill system/value and provenance; retain optional age | Safe identity, no birth date | `{"identity":{"displayName":"Maya","age":28,"sportId":"tennis"}}` |
| Distance Chip | New | Distance label currently in `SwipeHeroTopBar` → `SwipeDistanceChip` **(proposed)** | Extract photo-overlay chip with Approximate/Hidden states; hidden means no distance text | Rounded distance/unit or hidden/unavailable | `{"distance":{"state":"approximate","value":2,"unit":"mi"}}` |
| Community Rating | Modification needed | `RatingsView` → extracted `SwipeCommunityRating` **(proposed)** | Replace star rows with Friendliness/Competitive numeric tiles; Rated/New variants and honest unrated state | Metric, scale, count; no invented score | `{"communityRatings":[{"metric":"friendliness","state":"unrated"}]}` |
| Highlight Row | New | `SwipeHighlightRow` **(proposed)** | Icon/title/detail row; Reliability/Games/Style variants | Public supported highlight kind + copy | `{"highlights":[{"kind":"games","title":"24 games","detail":"Tennis"}]}` |
| Sport Stats | Modification needed | `SwipeStatHighlightsSection` + `SwipeMetricTileView` | Format/games/attendance row; correct units and unknown values; responsive layout | Counts and attendance denominator | `{"stats":{"format":"doubles","gamesPlayed":24,"attendancePercent":null}}` |
| Vibe Tag | Modification needed | `SwipeTagPill` | Add leading marker and six variants: Similar vibe, Casual matchup, Tough matchup, Goofy, Finding your vibe, Interesting combo; distinguish fit/personality | Approved fit/personality codes | `{"fitCode":"similar_vibe","personalityCodes":["goofy"]}` (vibe fragment) |
| Trait Meter | New | `SwipeTraitMeter` **(proposed)** | Segmented labeled bar for all eight traits; text equivalent, no color-only meaning | Trait code/value/scale/label | `{"code":"friendliness","value":4,"max":5,"label":"Welcoming"}` (trait item) |
| Player Vibe | Modification needed | `SwipeCardMatchupSection` | Replace central matchup score/tiles with fit explanation, selected traits, personality tags and review count; Established/Early feedback | Aggregates + confidence; server-selected traits | `{"vibe":{"state":"insufficient","reviewCount":0,"traits":[]}}` |
| Availability Day | New | `SwipeAvailabilityDay` **(proposed)** | Dated day view and local-time lanes. `AvailabilityGridView.swift` declares `AvailabilityGridDemo`, not a production day component. | Shared dated intervals + viewer zone | `{"date":"2026-09-29","start":"2026-09-29T22:30:00Z","end":"2026-09-30T00:00:00Z"}` (window item) |
| Week Availability | New | `SwipeWeekAvailability` **(proposed)** | Mon–Sun selection and horizontal paging; initial day from useful overlap, not hardcoded Tuesday | Same overlap windows; no separate request per day | `{"availability":{"state":"available","timeZone":"America/New_York","windows":[]}}` |
| Availability Overlap | Modification needed | `SwipeBestOverlapTeaser` | Replace score/category bars with shared-window count, best fit and weekly browser; Great/Limited/None variants | Server overlap summary, no client threshold guesses | `{"summary":{"band":"great","sharedWindowCount":3,"bestWindowId":"window_1"}}` (availability fragment) |
| Score Heat Rail | New | `SwipeScoreHeatRail` **(proposed)** | Bottom-up 0–100 fill; Rest/Selected tap toggle reveals marker/exact value; unavailable state | Public score + calculation version, separate from ranking | `{"scoutScore":{"state":"available","value":88,"max":100,"calculationVersion":"proposal-v1"}}` |

All **21 Swipe families** are covered above. The eight trait codes are `friendliness`, `competitiveness`, `playfulness`, `skill`, `reliability`, `sportsmanship`, `communication`, `teamwork`. Figma main variants remain linked through the source page; screenshots below show composed results and feedback variants.

### Shared dependencies and screen composition

| Component / role | Status | Actual name | Work required | Backend / JSON |
| --- | --- | --- | --- | --- |
| Loading / empty / retry fallback | Ready to go | `ScoutStateCard` | Reuse current loading/empty/error states, title/message and action closure; map localized copy | `{"type":"empty_state","id":"discovery_empty","payload":{"reason":"no_candidates"}}` |
| Glass surfaces | Modification needed | `GlassCard` / `ScoutGlassPanel` alias | Parameterize material/radius to match Subtle/Standard/Elevated/Accent; confirm Reduce Transparency fallback | None |
| Deck header / filter entry | Modification needed | `SwipeHeroTopBar` | Replace large brand header with compact title/filter control; connect approved filters | Filter request, e.g. `{"sportId":"tennis"}` |
| Deck and scroll viewport | Modification needed | `SwipeDeckScreen`, `SwipeDeckView`, `SwipeCardOverlayScrollLayout` | Typed provider data, bounded viewport, safe-area dock, separate gestures, retry/empty states | `swipe_stack` + pagination; see BFF plan |
| Section headings / bio / privacy footer | Modification needed | `PlayerSwipeScrollView` composition | Add missing sections in the designed order using existing text styles; no new component needed | `{"bio":"Weeknight doubles are my happy place."}` |

Reuse tokens/icons only after comparing values with Figma; no other complete swipe component has been verified “ready to go.” `ScoutAvatar` and `ScoutTabBar` from the example request are not declared names in the inspected code and are not added as fictional existing components.

Source folders: `Scout/Scout/Swipe/Views`, `Scout/Scout/Swipe/ViewModels`, `Scout/Scout/App`, `Scout/Scout/Design/Components`, `Scout/ScoutDesign/Sources/ScoutDesign/Components` in ScoutSports. `ScoutStateCard` readiness refers to fallback behavior; it is not a claim of visual parity with an undesigned empty screen.

## 2. Example player-card JSON

**Contract proposal:** `version/components` envelope and factory rules are defined in [BFF PR #2](https://github.com/22annajohnson/scout-planning/pull/2). The following is one `player_card` nested inside `swipe_stack.payload.cards`. All values are illustrative; scores and fit thresholds need approval. URLs use a deliberately non-production domain.

```json
{
  "type": "player_card",
  "id": "player_123",
  "payload": {
    "revision": "r1",
    "identity": {
      "displayName": "Maya", "age": 28, "intro": "Good rallies. Better company.",
      "sportId": "tennis", "skill": {"system": "NTRP", "value": "3.5", "source": "self_rated"}
    },
    "photos": [{"id": "photo_1", "url": "https://example.invalid/photo.jpg", "expiresAt": "2026-09-25T18:00:00Z"}],
    "distance": {"state": "approximate", "value": 2, "unit": "mi"},
    "scoutScore": {"state": "available", "value": 88, "max": 100, "calculationVersion": "proposal-v1"},
    "communityRatings": [{"metric": "friendliness", "state": "rated", "value": 4.9, "max": 5, "reviewCount": 24}],
    "vibe": {
      "state": "available", "fitCode": "similar_vibe", "personalityCodes": ["goofy"],
      "explanation": "You both enjoy friendly games with a competitive edge.",
      "reviewCount": 24, "confidence": "established",
      "traits": [{"code": "friendliness", "value": 4, "max": 5, "label": "Welcoming"}]
    },
    "availability": {
      "state": "available", "timeZone": "America/New_York",
      "summary": {"band": "limited", "sharedWindowCount": 1, "bestWindowId": "window_1"},
      "windows": [{"id": "window_1", "date": "2026-09-29", "start": "2026-09-29T22:30:00Z", "end": "2026-09-30T00:00:00Z"}]
    },
    "stats": {"format": "doubles", "gamesPlayed": 24, "attendancePercent": 96, "attendanceSampleCount": 25},
    "highlights": [{"kind": "games", "title": "24 games with the community", "detail": "Tennis · Doubles & singles"}],
    "bio": "Weeknight doubles are my happy place.",
    "allowedActions": ["pass", "invite", "connect"]
  }
}
```

`windows` exposes shared time only. `date` is the start date in the viewer's stated zone; end time may cross midnight. Optional `viewerWindows` can support the viewer's own lane. Ratings, score and overlap bands are supplied by approved server rules, never inferred by the iOS factory. Missing/null metrics remain unknown, not zero.

### Decision request example

```json
{
  "candidateId": "player_123",
  "candidateRevision": "r1",
  "action": "pass",
  "idempotencyKey": "decision_123"
}
```

The same key is reused on retry. Invite/Connect outcomes and required invitation context must be approved before implementation. Do not map old `onBoost` directly to an unapproved business action.

## 3. Implementation checklist

### iOS

- [ ] Update the components above; fixture every Figma variant, including hidden distance, unrated feedback, no overlap, failed media and no score.
- [ ] Use provider → DTO/factory → typed model → view model → view. Views do not decode JSON or call Supabase; keep navigation state local.
- [ ] Isolate horizontal photo/day paging from vertical scrolling. Use explicit decision buttons first; deck-swipe thresholds need a product decision.
- [ ] Keep controls outside the scroll area; preserve card/photo/day/scroll state through menu expansion and tab changes. Do not hide the only route back to navigation.
- [ ] Add loading, retry, exhausted/filter-empty, offline and pending states. Freeze duplicate actions and retain the card on failure.
- [ ] Verify small screens, Dynamic Type, VoiceOver order/action labels, 44-point targets, contrast, Reduce Motion/Transparency and deployment-target glass fallback.

### Backend

- [ ] Supply ordered, cursor-paged `player_card` data through a thin TypeScript Supabase BFF; contract details in PR #2.
- [ ] Own eligibility, exclusions, scoring, fit, selected traits, feedback confidence and timezone-safe overlap computation. Do not ship Figma sample values as defaults.
- [ ] Authenticate caller; enforce RLS/privacy; expose authorized media, approximate location and shared time only. Recheck visibility/blocks/permissions when acting.
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
