# It Built It. Now Prove It Holds.

### Experimentation with AI - Range community masterclass

This repository is the artefact from the masterclass: a salary benchmarking tool built live
in about half an hour, and the `comp-claim-check` skill that makes its numbers trustworthy.
This page is the walkthrough, so you can replicate the whole thing yourself.

- **Live app:** https://range-calculator-theta.vercel.app
- **The skill:** [`comp-claim-check/SKILL.md`](comp-claim-check/SKILL.md)
- **Speaker:** Alexander Sommer, Founder, Gen-Metrics

---

## The idea in one line

The tool can build almost anything now, so building is no longer the bottleneck. The hard part
moved from **building** to **thinking** - deciding what is worth building, and making sure what
you build is reliable enough to share. In compensation that matters more than almost anywhere
else: the output goes to many people and drives real pay decisions, so a confident-but-wrong
number is not an embarrassment, it is someone's offer.

## Where are you on the spectrum? (the four levels)

A simple way to locate how you use AI today. It usually goes left to right, and there is no
wrong level - the skill is noticing when a task would be better served one level up.

1. **Search engine** - a question-and-answer tool.
2. **First draft** - produce specific drafts.
3. **Thinking partner** - define the behaviour you want; use projects and more deliberate
   prompting to think a problem through.
4. **Build and automate** - agents and automation flows (n8n, Claude Code). Most practitioners
   now default to Claude directly rather than buying separate orchestration tools.

## What we built live

A People team wanted a user-friendly way to pull current market salary ranges for a role and
location, and check whether what they offer sits within range - without commissioning a survey
build that takes weeks. We built it in about thirty minutes.

The build order that works well:

> **Logic first → Design (the interface) → Code (deploy and scale).**

Keep prompts small and focused. Build the logic as a plain script first (an engineering habit:
get the core right before you dress it up), then wrap it in an interface, then ship it.

---

## Replicate it, step by step

### 0. Setup

- **Start from a blank `CLAUDE.md`.** Add only the context that matters: values your organisation
  already uses, and pointers to where the real data lives. Pull data from Google Drive or a
  shared repository through MCP connectors rather than pasting it in.
- **Model preferences:** use **Opus** for ideation, systems architecture, and impact analysis;
  let **Sonnet** execute the code. Set these as rules in your `CLAUDE.md`. (If your plan has the
  credits, you can use Opus for everything.)
- **Think about downstream impact before you build** (a light touch of systems thinking): who
  ends up using this output, and what decision rides on it? Run your idea against a "sparring
  partner" project before you write a line.

### 1. Logic first

In a fresh task, keep the instruction small:

```
Give me a simple Python script: I give it a role title and a location, it returns a recommended
salary band, a midpoint, and a short rationale a hiring manager could read. Make it run from the
terminal and work for a "Senior Compensation Analyst" in "London" out of the box.
```

Run it. In minutes you have a working benchmark - the part that used to be the hard part.

### 2. Design the interface

In the Claude desktop app, open **Design** (the button at the bottom). Start a new design and
hand it the script:

```
Build a clean, polished interface around this compensation calculator: inputs for role and
location, and a results card showing the band, the midpoint, and the rationale.
```

Keep prompts small and concise. With a light touch it asks useful clarifying questions about the
audience and use - things a non-designer would not think to specify.

### 3. Make it trustworthy - the skill (this is the crux)

The honeymoon ends the moment you test it. The first version produces **confident, fabricated
numbers**: invented anchor salaries, made-up seniority and location multipliers, fake names and
titles, and a confident figure even for a role it has never seen. None of that is safe to share.

So encode the checks you would run by hand into a **skill** - a set of explicit rules baked into
Claude that govern how it behaves. The four checks (see [`comp-claim-check/SKILL.md`](comp-claim-check/SKILL.md)):

1. **Checkable sources** - every figure traces to a real, named source, or it is flagged as
   unverifiable. No invented numbers dressed up as sourced.
2. **Governance and stability** - the same question returns the same answer; the tool is
   deterministic, not re-rolled each time.
3. **Edge cases** - a brand-new role, or one not in the data, returns a low-confidence
   "not enough data yet" flag instead of a fabricated number.
4. **Impact awareness** - understand the downstream effect of the output and who acts on it.

Build it, then apply it:

```
Create a Claude skill that runs these four checks on any compensation figure before it is
presented: checkable sources, governance and stability, edge cases, and impact awareness.
```

```
Now apply this skill to the calculator and make it robust: source every band or say "not enough
data yet", show ranges instead of false-precise points, and never present an unsourced number as
if it were sourced.
```

That single "apply the skill" step is what turned this calculator from confident-but-fabricated
into **sourced or silent**. The skill is the rules of the game; once it exists, the tool plays by
them every time - and Claude runs it on itself, before it hands you a number.

### 4. Ship it

From Claude Code, one prompt does the whole deploy:

```
Initialise a Git repo for this project, commit, create a repo, deploy to Vercel, and give me the URL.
```

---

## Keeping it trustworthy over time

A benchmark is only as fresh as its data. Two ways to keep it current:

- **Point at data you own.** Have the tool read from a shared Google Drive doc, a repository, or
  a Sheet through connectors, so it pulls live values instead of hard-coded ones. Show an
  "as of" date so people know how current it is.
- **Build a refresh routine.** Even with hard-coded values, you can set up a routine in Claude to
  refresh the data on a regular cadence.

This is exactly what a BI dashboard does - pull from tables you trust, refresh on a schedule. The
only difference now is that you are the one designing the dashboard, on top of data you own and
control.

**Exporting to Google Sheets:** use the Google Workspace CLI (`gws-cli`) to build a skill that
populates Sheets through the API. It needs a Google Cloud project with the right scopes and
permissions - a one-time setup, ideally with a hand from someone technical.

## Sharing and hosting

| Option | When to use it |
| --- | --- |
| **HTML download** | Simplest. A standalone file you can share directly. |
| **Vercel** | Recommended for low user counts. Claude Code can deploy it for you (see step 4). |
| **SharePoint / Teams** | Possible but clunky. Set permissions at team level. |
| **Org-wide** | Needs DevOps to promote it to production securely. AI sped up building, not deploying and securing - if there is no process, be the one to propose it. |
| **Gated / confidential data** | Add an authentication layer so only the right people (e.g. the comp team) see the data. Get technical help for this part. |

## Treat it as a product

The moment something is worth sharing, it stops being an experiment and becomes a product:

- **Version-control everything** in a repository (think of GitHub as Google Drive for code).
- **Split the work:** HR and People teams should ideate and validate; hand technical maintenance
  to an engineering team. You should not own and fix code you cannot read.
- **Give it an owner.** Like any product, it needs ownership, maintenance, and security
  governance. The hundred thousand you save on the build still needs someone to keep it running.

---

## The deck and the polls

The talk ran on a short Range-branded deck (built with Claude to match the community's style) and
four live Slido polls. The deck is in this repo:
[`deck/it-built-it-now-prove-it-holds.pptx`](deck/it-built-it-now-prove-it-holds.pptx).

**Warm-up poll** - *What's the most ambitious thing you've asked AI to do lately?*
Find or look something up / Draft something / Think a problem through with me / Build or automate
something. (A quick read of where the room sits on the four levels.)

**The four break-it questions** - run as polls while testing the tool, then resolved into a verdict:

1. **Provenance** - where did this number actually come from?
2. **Stability** - run it again; will the number move?
3. **Edge case** - a brand-new role, no market data; what does it do?
4. **Stakes / verdict** - *a manager sets a real offer from this. Trust, Verify, or Don't ship?*

The close: **encode the check once, and let the agent run it from then on.** Try this week - take
one AI output you would have forwarded, and run the four questions on it first.

## Work with me

This session is part of how **Gen-Metrics** helps teams go from AI-curious to shipping AI they can
trust - org-wide programmes, workshops, keynotes, and custom AI labs that turn AI access into
adoption. If you'd like a session like this for your team, or help taking an experiment to something
that holds, get in touch:

- 🌐 Website: **[gen-metrics.com](https://gen-metrics.com)**
- 🎓 AI enablement & training: **[gen-metrics.com/ai-enablement.html](https://gen-metrics.com/ai-enablement.html)**

*Alexander Sommer - Founder, Gen-Metrics. A decade building production AI systems across finance,
logistics, and software, now helping teams use AI well in the real world.*
