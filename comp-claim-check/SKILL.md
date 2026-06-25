---
name: comp-claim-check
description: >-
  Pressure-tests any compensation figure - a salary benchmark, market rate, pay band,
  or offer number - before it is trusted, shared, or published. Use whenever producing,
  quoting, or relying on a comp number a person will act on. Trigger phrases include:
  'salary benchmark', 'market rate', 'comp band', 'pay recommendation', 'what should we
  pay', 'benchmark this role', 'is this number right', 'ready to send to the hiring
  manager', 'before publishing'.
---

# comp-claim-check

Run this on a compensation number before you trust it. The risk is not that the number is
wrong everywhere. The risk is that it is wrong in one load-bearing place, and that place
reads perfectly. Work through four checks and state plainly what you find for each.

## 1. Checkable sources (provenance)
- Name a real, checkable source for every figure: the survey or dataset, the reference
  period, the release date, and the exact occupational and geographic cut.
- Tag each figure: cited / uncited / unverifiable. If you cannot name a real source in one
  line, the figure is unverifiable - say so. Never present an invented number as sourced.

## 2. Governance and stability
- Asked the same question again, would you give the same answer? A trustworthy number is
  deterministic, not re-rolled each time.
- If the figure would move on a re-run or a trivially reworded input (a nearby city, a
  slightly different title), the precision is false. Give a range, not a single confident point.

## 3. Edge cases
- Test the awkward inputs: a brand-new role, a role not in the data, part-time, an unusual
  geography or level.
- For anything outside what the data actually covers, return "not enough data to benchmark
  this yet" and name what is missing. Do not fall back to a generic number.

## 4. Impact awareness (stakes)
- Name who acts on this and how: a manager setting an offer, a raise decision, an equity grant.
- Calibrate scrutiny to the blast radius. The higher the stakes, the harder checks 1 to 3 must pass.

## Verdict
End with one verdict and three short fields:
- Verdict: Trust / Verify / Don't ship
  - Trust: sourced, stable, edge cases handled, low stakes.
  - Verify (default): directionally reasonable, but with a named source, stability, or
    framing gap a person must close first.
  - Don't ship: a load-bearing figure has no traceable source, or a number that moves the
    decision cannot be stood up. Show "not enough data" rather than the number.
- Headline: one sentence naming what survives and what does not.
- One fix: one specific, ten-minute edit - name the figure and the change, not "verify your sources".
- Confidence note: one line on what this check itself is unsure about. The checker is fallible too.

Avoid filler: "comprehensive", "robust", "stakeholders", "broadly", "best practice",
"consider verifying", "it is important to". Name the specific figure, the specific source,
the specific change.

If any check fails, raise it before the number is trusted, and do not publish it.

## Make it yours
- Set your own thresholds: what stakes force a Don't ship for you?
- Lead with your usual trap: if invented benchmarks bite you most, run Checkable sources first
  and hardest.

## How to use this
Copy this `comp-claim-check/` folder into your project's `.claude/skills/` directory, so the
path is `.claude/skills/comp-claim-check/SKILL.md`. Claude then invokes it automatically
whenever a comp number is in play.

In the masterclass this skill was built live, then applied to the salary calculator with a
single prompt ("apply this skill to the calculator"). That is what turned a confident-but-
fabricated tool into the sourced-or-silent one in this repo. See MASTERCLASS.md.
