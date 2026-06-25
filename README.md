# Salary Benchmark

**Sourced market salary ranges — or an honest "not enough data yet."**

A compensation benchmarking tool that returns a real percentile distribution from a
named wage survey (US BLS OEWS, May 2025) for a role + location — or, when the role or
location falls outside what the survey actually covers, says so plainly instead of
inventing a confident number.

🔗 **Live app:** https://range-calculator-theta.vercel.app

---

## 🎓 Built live at the Range community masterclass

This tool was built end to end during *"It Built It. Now Prove It Holds."* - a masterclass on
experimenting with AI, by Alexander Sommer (Gen-Metrics). If you came from the session, start here:

- **[MASTERCLASS.md](MASTERCLASS.md)** - the full walkthrough: the thesis, the four-level
  spectrum, and a step-by-step guide to replicate the tool yourself (logic → design → deploy).
- **[`comp-claim-check/SKILL.md`](comp-claim-check/SKILL.md)** - the skill that makes the numbers
  trustworthy. Copy the `comp-claim-check/` folder into your project's `.claude/skills/` to use it.

The four-check skill is the whole point: it is what turned a confident-but-fabricated first build
into the *sourced-or-silent* tool described below.

---

## Why it works this way

This project was built around a compensation-claim integrity principle: **a benchmark is
only as trustworthy as its source.** So the tool refuses the usual shortcuts that produce
plausible-but-fabricated pay numbers:

1. **Sourced or silent.** Every band is a real percentile row (P10/P25/P50/P75/P90) from a
   named survey, carrying the source, reference period, release date, and the exact
   geographic + occupational cut. There are no hand-typed "anchor" salaries and no
   invented seniority/location multipliers.
2. **Ranges, not false-precise points.** It leads with the P10–P90 spread and the P25–P75
   working band. The only single figure shown is the survey's own median (P50), labelled
   as such.
3. **"Not enough data" beats a confident guess.** If the role doesn't map to a covered
   occupation, or the location isn't a covered geography (e.g. any UK city), it returns
   *"not enough data to benchmark this yet"* and names what's missing — it does **not**
   fall back to a generic number.

## Coverage

- **8 occupations** (SOC-coded): Software Developers, Data Scientists, Accountants &
  Auditors, Financial & Investment Analysts, Compensation/Benefits Specialists, HR
  Specialists, Marketing Managers, Management Analysts.
- **3 US geographies:** United States (national), New York–Newark–Jersey City metro, and
  San Francisco–Oakland–Fremont metro.
- **Source:** U.S. Bureau of Labor Statistics — Occupational Employment and Wage
  Statistics (OEWS), May 2025 reference period. Base wages only (excludes bonus, equity,
  and benefits; no job-level granularity).

Anything outside that returns "not enough data" by design.

## What's in here

| Path | What it is |
| --- | --- |
| `index.html` | The deployed web app. Exported from a [Claude Design](https://claude.ai/design) project ("Salary Benchmark"), with the design runtime (`support.js`) and React vendored locally so it runs as a fully static site. |
| `support.js` | The Claude Design `dc-runtime` — interprets the `<x-dc>` template + component logic and mounts it with React. |
| `vendor/react*.min.js` | React 18.3.1 UMD (production), pinned and integrity-matched to `support.js`'s SRI hashes, so the app boots without a third-party CDN call. |
| `salary_benchmark.py` | A standalone CLI version of the same sourced-or-silent benchmark (no dependencies). |

## CLI usage

```bash
python3 salary_benchmark.py --role "Senior Software Engineer" --location "New York"
python3 salary_benchmark.py --role "Data Scientist" --location "San Francisco" --json
python3 salary_benchmark.py --list        # what's covered + the source
python3 salary_benchmark.py --selftest    # integrity checks
```

## Deployment

The site is static (just `index.html` + `support.js` + `vendor/`), deployed on
[Vercel](https://vercel.com) with no build step. To redeploy:

```bash
vercel deploy --prod
```

---

*Base wages from a broad government survey are a market reference, not an offer. Validate
against a leveled survey (Radford, Mercer, WTW, Pave) before committing a pay band.*
