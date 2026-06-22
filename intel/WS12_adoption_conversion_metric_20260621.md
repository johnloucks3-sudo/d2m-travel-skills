# WS-12 — Tech-Adoption Conversion Metric (ELON hunt, 2026-06-21)

NEED: harvester detects its own silence but not its own irrelevance. No
adoption-conversion-rate, no Watch->Adopt gate, no staleness alarm on
un-triaged HIGH findings >72h. Commander out-scouts the pipeline.

## VERDICT: NO_GOOD_OPTION (external) -> BUILD IN-HOUSE (reuse own CI pattern)

### Why no external tool fits
- Tech-radar tools (Backstage Tech Radar, qiwi/tech-radar, thoughtworks/build-your-own-radar,
  Zalando) = VISUALIZATIONS of a curated list. Fill 0/3: no conversion funnel,
  no 72h staleness SLA, no automated Watch->Adopt gate.
- Innovation-mgmt / stage-gate SaaS (ITONICS, Wellspring Scout/Accolade, Sopheon,
  Qmarkets) DO funnel + stage-gates conceptually -- but enterprise custom-priced,
  absurd scale/cost for a 1-advisor shop. Name-and-dismiss.
- actions/stale does staleness, but on GitHub issues/PRs, not a findings ledger;
  cron timing is "best effort" (no SLA).

### BEST (build, ~1 day, $0): findings ledger over existing CI registry pattern
Reuse VERBATIM what we already run:
- core/ci/registry.py: last_verified / currency_window_hours / reeval_cadence_days
  = staleness window + re-eval gate, ALREADY BUILT.
- core/ci/self_observability.py: breach -> dispatch autonomous fixer loop
  = the alarm + autonomous action, ALREADY BUILT.
Point that pattern at thunderbird_power_harvest.py output:
  each finding -> {status: surfaced|evaluating|adopted|rejected|watch,
                   rating, first_seen, last_triaged}
  - conversion metric = counts by status (surfaced vs evaluated vs adopted/rejected)
  - staleness alarm = HIGH-rated + status in {surfaced,watch} + age(last_triaged) > 72h
    -> breach -> dispatch (same self_observability dispatch path)
  - Watch->Adopt gate = status transition requires Sterling gate-owner sign (existing CI owner model)
Daily ci_sweep.py already runs 0600 MT -- add the ledger scan there.

### RUNNER-UP (adoptable substrate, TRIAL): GitHub Projects + scheduled Action
Already on GitHub. Status field = Watch->Adopt gate; views-by-status = conversion
metric; cron Action flags HIGH items un-triaged >72h. $0, real today. Weaker than
in-house because it duplicates the CI pattern we already own and adds a second
system to keep current.

## SOURCES
- https://github.com/thoughtworks/build-your-own-radar
- https://backstage.spotify.com/partners/spotify/plugin/techradar/
- https://github.com/qiwi/tech-radar
- https://www.itonics-innovation.com/pricing
- https://www.wellspring.com/tech-scouting
- https://github.com/actions/stale
