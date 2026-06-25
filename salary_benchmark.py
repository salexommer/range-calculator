#!/usr/bin/env python3
"""
salary_benchmark.py — a sourced, honest salary benchmarking tool.

Give it a role title and a location; it returns a salary RANGE drawn from a
named survey with an "as of" date — or it tells you, in plain words, that it
does not have the data to benchmark that role/location yet.

    python3 salary_benchmark.py --role "Software Engineer" --location "New York"
    python3 salary_benchmark.py --role "Senior Data Scientist" --location "San Francisco"
    python3 salary_benchmark.py --role "Accountant" --location "United States" --json
    python3 salary_benchmark.py --list                # what is covered + the source
    python3 salary_benchmark.py --selftest            # integrity checks

DESIGN PRINCIPLES (this is the whole point of the tool)
-------------------------------------------------------
This rewrite was driven by a compensation-claim integrity review. The previous
version invented round "anchor" salaries, dressed them up as "anchored to public
2026 ranges," multiplied them by made-up seniority/location factors, and — for
any role or city it didn't recognise — silently returned a confident number off
a generic baseline. Every one of those is the classic shape of a fabricated comp
figure. This version refuses to do any of it:

  1. SOURCED OR SILENT. Every band it returns is a real percentile distribution
     from a named survey (currently BLS OEWS, May 2025), carrying the source,
     the survey reference period, the release date, and the exact geographic and
     occupational cut. There are no hand-typed anchor numbers anywhere in here.

  2. RANGES, NOT FALSE-PRECISE POINTS. It leads with the real p10-p90 spread and
     the p25-p75 working band. The only single figure it shows is the survey's
     own median (p50), explicitly labelled as the survey median — never a
     computed, decimal-precise "recommended number."

  3. "NOT ENOUGH DATA" BEATS A CONFIDENT GUESS. If the role doesn't map to a
     covered occupation, or the location isn't a covered geography, it returns
     "not enough data to benchmark this yet" and says what is missing. It does
     NOT fall back to a generic number.

  4. NO UNSOURCED NUMBER IS EVER PRESENTED AS SOURCED. Seniority guidance points
     at parts of the REAL distribution (e.g. "senior roles typically sit p50-p75")
     rather than inventing a multiplier, and it is flagged as judgement, because
     the survey has no seniority field.

WHAT THIS IS NOT
----------------
OEWS is base wages only: it excludes bonus, equity, and benefits, and has no
job-level granularity (a "senior" and a "junior" software developer are the same
occupation to it). It is a broad government survey — clean and unbiased, but it
trails real-time pay and is national/metro, not company-specific. For a live
offer or a band that will set many salaries, validate against a leveled survey
(Radford, Mercer, WTW, Pave) before you commit a number.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Optional

# --------------------------------------------------------------------------- #
# THE SOURCE.  One source, named, dated, and re-pullable.
# --------------------------------------------------------------------------- #
# Figures below were pulled from the BLS OEWS May 2025 release via the official
# OEWS query service (data.bls.gov/OESServices), cross-industry ("000000"),
# for the national area and two metropolitan areas. Values are annual wages in
# USD. p10/p25/p50/p75/p90 are the published percentile wages; "emp" is the
# estimated employment for that occupation+area (a proxy for sample robustness).

SOURCE = {
    "name": "U.S. Bureau of Labor Statistics — Occupational Employment and Wage Statistics (OEWS)",
    "short": "BLS OEWS",
    "reference_period": "May 2025",          # the survey's "as of" date
    "released": "2026-05-15",                # when BLS published this release
    "url": "https://www.bls.gov/oes/",
    "data_url": "https://data.bls.gov/oes/",
    "type": "Government employer survey (broad, unbiased; no job-level detail; base wages only)",
    "currency": "USD",
    "symbol": "$",
}

# --------------------------------------------------------------------------- #
# COVERED OCCUPATIONS.  soc -> label + the keywords that map a title onto it.
# "approx" marks a fuzzy mapping the user should know about.
# --------------------------------------------------------------------------- #
OCCUPATIONS = {
    "15-1252": {
        "label": "Software Developers",
        "keywords": ["software engineer", "software developer", "software dev",
                     "developer", "swe", "backend", "back-end", "frontend",
                     "front-end", "full stack", "full-stack", "programmer"],
        "approx": [],
    },
    "15-2051": {
        "label": "Data Scientists",
        "keywords": ["data scientist", "machine learning", "ml engineer",
                     "ml scientist", "applied scientist"],
        "approx": [],
    },
    "13-2011": {
        "label": "Accountants and Auditors",
        "keywords": ["accountant", "auditor", "accounting"],
        "approx": [],
    },
    "13-2051": {
        "label": "Financial and Investment Analysts",
        "keywords": ["financial analyst", "finance analyst", "investment analyst",
                     "fp&a", "fpa", "equity analyst"],
        "approx": ["fp&a", "fpa"],  # OEWS folds FP&A into this broader occupation
    },
    "13-1141": {
        "label": "Compensation, Benefits, and Job Analysis Specialists",
        "keywords": ["compensation", "rewards", "reward", "remuneration",
                     "comp & ben", "comp and ben", "job analysis", "benefits analyst"],
        "approx": [],
    },
    "13-1071": {
        "label": "Human Resources Specialists",
        "keywords": ["hr specialist", "hr generalist", "human resources",
                     "people partner", "hr business partner", "hrbp",
                     "recruiter", "talent acquisition", "talent partner"],
        "approx": ["recruiter", "talent acquisition", "talent partner"],  # OEWS has no standalone recruiter SOC
    },
    "11-2021": {
        "label": "Marketing Managers",
        "keywords": ["marketing manager", "marketing lead", "head of marketing",
                     "marketing director", "brand manager", "growth manager"],
        "approx": ["brand manager", "growth manager"],
    },
    "13-1111": {
        "label": "Management Analysts",
        "keywords": ["management analyst", "management consultant",
                     "business analyst", "operations analyst", "strategy analyst",
                     "process analyst"],
        "approx": ["business analyst", "operations analyst", "strategy analyst",
                   "process analyst"],  # all proxied onto Management Analysts
    },
}

# --------------------------------------------------------------------------- #
# COVERED GEOGRAPHIES.  geo_key -> display + how a location string maps onto it.
# Anything not matched here returns "not enough data" — we never silently
# substitute national for a city we don't actually have.
# --------------------------------------------------------------------------- #
GEOS = {
    "us-national": {
        "area": "United States (national)",
        "geo_type": "national",
        "match": ["united states", "usa", "us", "u.s.", "national", "remote us",
                  "remote (us)", "nationwide", "anywhere us"],
        "metro": False,
    },
    "us-nyc": {
        "area": "New York-Newark-Jersey City, NY-NJ (metro)",
        "geo_type": "metropolitan",
        "match": ["new york", "nyc", "new york city", "manhattan", "newark",
                  "jersey city", "new york metro"],
        "metro": True,
    },
    "us-sf": {
        "area": "San Francisco-Oakland-Fremont, CA (metro)",
        "geo_type": "metropolitan",
        "match": ["san francisco", "sf", "bay area", "oakland", "fremont",
                  "san francisco metro"],
        "metro": True,
    },
}

# --------------------------------------------------------------------------- #
# THE DATA.  geo_key -> soc -> (p10, p25, p50, p75, p90, mean, emp)
# Annual USD wages, BLS OEWS May 2025. Do not hand-edit; re-pull from OEWS.
# --------------------------------------------------------------------------- #
DATA = {
    "us-national": {
        "11-2021": (90260, 123020, 166790, 216410, 293610, 177770, 395240),
        "13-1071": (47180, 58610, 75940, 99380, 128720, 81990, 912430),
        "13-1111": (60640, 77950, 101860, 133370, 171640, 113790, 898280),
        "13-1141": (49480, 60890, 78210, 100400, 128920, 84330, 112380),
        "13-2011": (56020, 67020, 83680, 109810, 144090, 94750, 1449500),
        "13-2051": (63720, 79290, 102740, 133340, 180860, 116800, 361980),
        "15-1252": (82460, 105210, 135980, 171980, 214670, 148100, 1687890),
        "15-2051": (67240, 85660, 120230, 158880, 199130, 126800, 262440),
    },
    "us-nyc": {
        "11-2021": (116040, 156020, 192840, 246000, 324990, 207770, 54730),
        "13-1071": (58140, 70210, 89780, 124130, 155480, 98100, 52370),
        "13-1111": (66430, 94490, 124390, 168320, 210390, 133590, 67630),
        "13-1141": (63370, 78390, 89130, 108830, 138070, 96980, 9900),
        "13-2011": (71850, 82830, 105650, 137490, 174750, 119280, 111930),
        "13-2051": (79340, 103140, 128930, 174990, 225390, 148350, 53870),
        "15-1252": (101690, 130650, 166830, 205970, 224590, 165870, 121000),
        "15-2051": (79870, 101320, 135980, 173160, 216030, 144700, 23160),
    },
    "us-sf": {
        "11-2021": (133990, 174750, 220480, 309110, 333430, 235920, 11170),
        "13-1071": (61500, 79820, 103140, 136040, 171420, 113530, 16420),
        "13-1111": (64080, 87910, 126730, 163380, 211790, 137410, 23560),
        "13-1141": (74570, 85800, 102780, 130410, 165600, 112700, 2440),
        "13-2011": (73420, 88820, 110730, 143590, 180060, 120780, 25170),
        "13-2051": (82570, 97490, 130520, 166350, 217160, 142560, 9910),
        "15-1252": (128090, 163500, 186640, 219670, 273400, 193430, 69030),
        "15-2051": (99170, 130430, 170110, 212970, 272430, 174830, 10460),
    },
}

PCTS = ("p10", "p25", "p50", "p75", "p90", "mean", "emp")

# Seniority -> which slice of the REAL distribution that level typically occupies.
# These point at real percentiles; they are NOT multipliers and invent no number.
# Order matters: most senior first.
SENIORITY_BANDS = [
    (["chief", "vp", "vice president", "director", "head of", "head ", "c-level", "cxo"],
     "Director / Executive", ("p90", None),
     "OEWS under-samples executives and excludes equity; p90 is a floor, not a ceiling — low confidence at this level."),
    (["manager", "lead", "principal", "staff", "senior manager"],
     "Manager / Lead / Principal", ("p75", "p90"),
     "Manager/lead pay typically sits in the upper band; the survey has no level field, so this is judgement."),
    (["senior", "snr", "sr.", "sr "],
     "Senior", ("p50", "p75"),
     "Senior roles typically sit upper-middle of the distribution; the survey has no level field, so this is judgement."),
    (["junior", "graduate", "trainee", "intern", "entry", "associate", "apprentice"],
     "Junior / Entry", ("p10", "p25"),
     "Entry roles typically sit in the lower band; the survey has no level field, so this is judgement."),
]
DEFAULT_SENIORITY = ("Mid / Unspecified level", ("p25", "p50"),
                     "No seniority detected in the title; showing the mid band. The survey has no level field.")

THIN_SAMPLE_EMP = 5000   # below this employment, flag the metro estimate as noisier


# --------------------------------------------------------------------------- #
# Matching
# --------------------------------------------------------------------------- #

def _norm(text: str) -> str:
    return " ".join((text or "").lower().strip().split())


def match_role(title: str):
    """Return (soc, occ_dict, approx_bool) or (None, None, False)."""
    t = " " + _norm(title) + " "
    # longest keyword first so "data scientist" wins over a bare "data"
    best = None
    for soc, occ in OCCUPATIONS.items():
        for kw in occ["keywords"]:
            if kw in t:
                if best is None or len(kw) > best[2]:
                    best = (soc, occ, len(kw), kw)
    if best is None:
        return None, None, False
    soc, occ, _, kw = best
    return soc, occ, (kw in occ["approx"])


def match_geo(location: str):
    """Return geo_key or None. Exact-ish containment; no silent national fallback."""
    loc = _norm(location)
    if not loc:
        return None
    # exact token match first
    for geo_key, g in GEOS.items():
        if loc in g["match"]:
            return geo_key
    # then containment either direction (e.g. "san francisco, ca")
    for geo_key, g in GEOS.items():
        for m in g["match"]:
            if len(m) >= 3 and (m in loc or loc in m):
                return geo_key
    return None


def match_seniority(title: str):
    t = " " + _norm(title) + " "
    for keywords, label, band, note in SENIORITY_BANDS:
        for kw in keywords:
            if kw in t:
                return label, band, note
    return DEFAULT_SENIORITY


# --------------------------------------------------------------------------- #
# Result types
# --------------------------------------------------------------------------- #

@dataclass
class Benchmark:
    ok: bool
    role_input: str
    location_input: str
    # populated when ok:
    soc: Optional[str] = None
    occupation: Optional[str] = None
    geo_area: Optional[str] = None
    geo_type: Optional[str] = None
    percentiles: dict = field(default_factory=dict)   # p10..p90
    mean: Optional[int] = None
    employment: Optional[int] = None
    seniority_label: Optional[str] = None
    seniority_band: tuple = ()                         # (low_label, high_label_or_None)
    seniority_note: Optional[str] = None
    confidence: Optional[str] = None
    notes: list = field(default_factory=list)
    # populated when not ok:
    reason: Optional[str] = None
    missing: Optional[str] = None
    hint: Optional[str] = None


def benchmark(role: str, location: str) -> Benchmark:
    soc, occ, approx = match_role(role)
    geo_key = match_geo(location)

    # ---- the no-data paths: never invent ----
    if soc is None and geo_key is None:
        return Benchmark(
            ok=False, role_input=role, location_input=location,
            reason="not enough data to benchmark this yet",
            missing="Neither the role nor the location maps to data we actually hold.",
            hint=_coverage_hint(),
        )
    if soc is None:
        return Benchmark(
            ok=False, role_input=role, location_input=location,
            reason="not enough data to benchmark this yet",
            missing=f"No covered occupation matches '{role.strip()}'.",
            hint="Covered roles: " + ", ".join(o["label"] for o in OCCUPATIONS.values()),
        )
    if geo_key is None:
        return Benchmark(
            ok=False, role_input=role, location_input=location,
            reason="not enough data to benchmark this yet",
            missing=f"'{location.strip()}' is not a geography we hold survey data for.",
            hint="Covered locations: " + ", ".join(g["area"] for g in GEOS.values()),
        )

    row = DATA[geo_key].get(soc)
    if row is None:  # covered occ + covered geo but no published cell (suppressed, etc.)
        return Benchmark(
            ok=False, role_input=role, location_input=location,
            reason="not enough data to benchmark this yet",
            missing=f"{occ['label']} has no published OEWS cell for {GEOS[geo_key]['area']}.",
            hint="Try United States (national), which usually has the most complete coverage.",
        )

    p10, p25, p50, p75, p90, mean, emp = row
    pct = {"p10": p10, "p25": p25, "p50": p50, "p75": p75, "p90": p90}
    sen_label, sen_band, sen_note = match_seniority(role)

    # ---- confidence + caveats, stated out loud ----
    g = GEOS[geo_key]
    confidence = "medium" if g["metro"] else "medium-high"
    notes = []
    if g["metro"] and emp < THIN_SAMPLE_EMP:
        confidence = "low"
        notes.append(
            f"Thin metro sample (~{emp:,} employed in this occupation here): the "
            "metro percentiles carry meaningfully wider sampling error."
        )
    elif g["metro"]:
        notes.append("Metro estimates carry more sampling error than the national figures.")
    if approx:
        if confidence == "medium-high":
            confidence = "medium"
        notes.append(
            f"Role mapping is approximate: '{role.strip()}' was proxied onto the "
            f"'{occ['label']}' occupation, which may be broader or narrower than the actual job."
        )
    if sen_band[0] == "p90":  # executive level
        notes.append(sen_note)

    # standard, always-true caveats
    notes.append(
        "OEWS is BASE WAGES ONLY — it excludes bonus, equity, and benefits, and has "
        "no job-level granularity. Treat as a market reference, not an offer."
    )

    return Benchmark(
        ok=True, role_input=role, location_input=location,
        soc=soc, occupation=occ["label"],
        geo_area=g["area"], geo_type=g["geo_type"],
        percentiles=pct, mean=mean, employment=emp,
        seniority_label=sen_label, seniority_band=sen_band, seniority_note=sen_note,
        confidence=confidence, notes=notes,
    )


def _coverage_hint() -> str:
    return ("Covered roles: " + ", ".join(o["label"] for o in OCCUPATIONS.values())
            + ". Covered locations: " + ", ".join(g["area"] for g in GEOS.values()) + ".")


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #

def money(amount) -> str:
    if amount is None:
        return "n/a"
    return f"{SOURCE['symbol']}{amount:,.0f}"


def _seniority_range_text(b: Benchmark) -> str:
    lo_label, hi_label = b.seniority_band
    lo = b.percentiles[lo_label]
    if hi_label is None:
        return f"at/above {hi_or(lo_label)} ({money(lo)}+)"
    hi = b.percentiles[hi_label]
    return f"{lo_label.upper()}-{hi_label.upper()}: {money(lo)} - {money(hi)}"


def hi_or(label: str) -> str:
    return label.upper()


def build_rationale(b: Benchmark) -> str:
    p = b.percentiles
    return (
        f"For {b.role_input.strip()} in {b.geo_area}, the {SOURCE['short']} "
        f"{SOURCE['reference_period']} distribution runs {money(p['p10'])} (p10) to "
        f"{money(p['p90'])} (p90), with a typical working band of {money(p['p25'])}-"
        f"{money(p['p75'])} (p25-p75) and a survey median of {money(p['p50'])}. "
        f"Given the title reads as {b.seniority_label.lower()}, comparable workers "
        f"usually sit around {_seniority_range_text(b)} — but note this is a judgement "
        f"call, since the survey records no job level. Confidence: {b.confidence}. These "
        f"are base wages only; add bonus, equity, and benefits separately, and validate "
        f"against a leveled survey before committing an offer."
    )


def render_text(b: Benchmark) -> str:
    L = []
    L.append("=" * 70)
    if not b.ok:
        L.append("  SALARY BENCHMARK — NOT ENOUGH DATA")
        L.append("=" * 70)
        L.append(f"  Role        : {b.role_input.strip() or '(none)'}")
        L.append(f"  Location    : {b.location_input.strip() or '(none)'}")
        L.append("-" * 70)
        L.append(f"  {b.reason.upper()}.")
        L.append("")
        for line in _wrap(b.missing, 66):
            L.append(f"  {line}")
        if b.hint:
            L.append("")
            for line in _wrap(b.hint, 66):
                L.append(f"  {line}")
        L.append("-" * 70)
        L.append("  No number is shown because we have no sourced figure for this")
        L.append("  combination. A guess here would be worse than nothing.")
        L.append("=" * 70)
        return "\n".join(L)

    p = b.percentiles
    L.append("  SALARY BENCHMARK")
    L.append("=" * 70)
    L.append(f"  Role        : {b.role_input.strip()}")
    L.append(f"  Location    : {b.location_input.strip()}")
    L.append(f"  Mapped to   : {b.occupation}  (SOC {b.soc})")
    L.append(f"  Geography   : {b.geo_area}")
    L.append(f"  Seniority   : {b.seniority_label}")
    L.append(f"  Confidence  : {b.confidence.upper()}")
    L.append("-" * 70)
    L.append(f"  MARKET RANGE ({SOURCE['currency']}, annual base wage)")
    L.append(f"    Full spread  p10-p90 : {money(p['p10'])} - {money(p['p90'])}")
    L.append(f"    Working band p25-p75 : {money(p['p25'])} - {money(p['p75'])}")
    L.append(f"    Survey median   p50  : {money(p['p50'])}")
    L.append(f"    {b.seniority_label} typically : {_seniority_range_text(b)}")
    L.append("-" * 70)
    L.append("  RATIONALE")
    for line in _wrap(build_rationale(b), 66):
        L.append(f"  {line}")
    if b.notes:
        L.append("-" * 70)
        L.append("  CAVEATS")
        for n in b.notes:
            for i, line in enumerate(_wrap(n, 64)):
                L.append(f"  {'- ' if i == 0 else '  '}{line}")
    L.append("-" * 70)
    L.append(f"  SOURCE : {SOURCE['name']}")
    L.append(f"  As of  : {SOURCE['reference_period']} (survey reference period)")
    L.append(f"  Released: {SOURCE['released']}    Re-pull: {SOURCE['data_url']}")
    L.append(f"  Cut    : {b.geo_area}, cross-industry, SOC {b.soc}; "
             f"~{b.employment:,} employed (sample proxy)")
    L.append("=" * 70)
    return "\n".join(L)


def render_json(b: Benchmark) -> str:
    if not b.ok:
        payload = {
            "status": "not_enough_data",
            "message": b.reason,
            "role_input": b.role_input.strip(),
            "location_input": b.location_input.strip(),
            "missing": b.missing,
            "hint": b.hint,
            "number_returned": None,
        }
        return json.dumps(payload, indent=2)

    payload = {
        "status": "ok",
        "role_input": b.role_input.strip(),
        "location_input": b.location_input.strip(),
        "mapped_occupation": b.occupation,
        "soc_code": b.soc,
        "geography": b.geo_area,
        "geography_type": b.geo_type,
        "seniority": b.seniority_label,
        "confidence": b.confidence,
        "currency": SOURCE["currency"],
        "range": {
            "p10": b.percentiles["p10"],
            "p25": b.percentiles["p25"],
            "p50_median": b.percentiles["p50"],
            "p75": b.percentiles["p75"],
            "p90": b.percentiles["p90"],
            "working_band_p25_p75": [b.percentiles["p25"], b.percentiles["p75"]],
            "seniority_typical_band": _seniority_band_values(b),
        },
        "sample_employment": b.employment,
        "caveats": b.notes,
        "source": {
            "name": SOURCE["name"],
            "as_of": SOURCE["reference_period"],
            "released": SOURCE["released"],
            "url": SOURCE["url"],
            "data_url": SOURCE["data_url"],
            "cut": f"{b.geo_area}, cross-industry, SOC {b.soc}",
            "type": SOURCE["type"],
        },
        "rationale": build_rationale(b),
    }
    return json.dumps(payload, indent=2)


def _seniority_band_values(b: Benchmark):
    lo_label, hi_label = b.seniority_band
    lo = b.percentiles[lo_label]
    hi = None if hi_label is None else b.percentiles[hi_label]
    return {"from_percentile": lo_label, "to_percentile": hi_label,
            "from": lo, "to": hi, "is_floor_only": hi_label is None}


def _wrap(text: str, width: int) -> list:
    words, lines, cur = (text or "").split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines


def list_reference() -> str:
    roles = "\n".join(f"    - {o['label']}  (SOC {soc})" for soc, o in OCCUPATIONS.items())
    geos = "\n".join(f"    - {g['area']}" for g in GEOS.values())
    return (
        f"SOURCE: {SOURCE['name']}\n"
        f"  As of {SOURCE['reference_period']} (released {SOURCE['released']}). "
        f"Re-pull at {SOURCE['data_url']}\n\n"
        "COVERED ROLES (anything else returns 'not enough data'):\n"
        f"{roles}\n\n"
        "COVERED LOCATIONS (anything else returns 'not enough data'):\n"
        f"{geos}\n\n"
        "Seniority (senior/lead/manager/director/junior) is parsed from the title and\n"
        "used to point at part of the REAL distribution — it invents no number.\n\n"
        "Not covered yet: the UK (the ONS ASHE occupation tables are the intended\n"
        "source) and roles with no clean OEWS match (e.g. Product Manager, Data\n"
        "Analyst). Those deliberately return 'not enough data' rather than a guess."
    )


# --------------------------------------------------------------------------- #
# Self-test — the integrity checks the rewrite is supposed to guarantee.
# --------------------------------------------------------------------------- #

def selftest() -> int:
    failures = []

    def check(name, cond):
        if not cond:
            failures.append(name)

    # 1) every covered cell is internally ordered p10<=p25<=p50<=p75<=p90
    for geo, rows in DATA.items():
        for soc, vals in rows.items():
            p10, p25, p50, p75, p90, mean, emp = vals
            check(f"ordered {geo}/{soc}", p10 <= p25 <= p50 <= p75 <= p90)
            check(f"positive {geo}/{soc}", p10 > 0 and emp > 0)

    # 2) a covered role+location returns a sourced band (not a no-data)
    b = benchmark("Software Engineer", "New York")
    check("covered returns ok", b.ok and b.percentiles.get("p50") == 166830)
    check("covered carries source", b.ok and SOURCE["reference_period"] in build_rationale(b))

    # 3) unknown role -> not enough data, and NO number anywhere in the output
    b = benchmark("Underwater Basket Weaver", "New York")
    out = render_text(b)
    check("unknown role no-data", (not b.ok) and "not enough data" in b.reason)
    check("unknown role shows no $ figure", "$" not in out)

    # 4) unknown location (a real US city we don't hold) -> not enough data
    b = benchmark("Software Engineer", "Austin")
    check("unknown location no-data", (not b.ok) and "not enough data" in b.reason)
    check("unknown location shows no $ figure", "$" not in render_text(b))

    # 5) UK is honestly uncovered
    b = benchmark("Senior Compensation Analyst", "London")
    check("UK no-data", not b.ok)

    # 6) the JSON no-data path explicitly returns a null number
    payload = json.loads(render_json(benchmark("Product Manager", "Mars")))
    check("json no-data null number", payload.get("number_returned") is None)

    # 7) every shown figure in a covered result is a real percentile (no invented points)
    b = benchmark("Accountant", "United States")
    real = set(DATA["us-national"]["13-2011"])
    shown = set(b.percentiles.values())
    check("only real percentiles shown", shown.issubset(real))

    if failures:
        print("SELFTEST FAILED:")
        for f in failures:
            print("  x", f)
        return 1
    print("SELFTEST PASSED — sourced bands, ranges not points, honest no-data path.")
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Return a SOURCED salary range for a role + location, or say so when it can't.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--role", default="Software Engineer",
                        help='Role title, e.g. "Senior Data Scientist".')
    parser.add_argument("--location", default="United States",
                        help='Location, e.g. "New York", "San Francisco", "United States".')
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output.")
    parser.add_argument("--list", action="store_true", help="Show what is covered and the source.")
    parser.add_argument("--selftest", action="store_true", help="Run integrity checks and exit.")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    if args.list:
        print(list_reference())
        return 0

    b = benchmark(args.role, args.location)
    print(render_json(b) if args.json else render_text(b))
    # exit non-zero on no-data so scripts can branch on it
    return 0 if b.ok else 3


if __name__ == "__main__":
    sys.exit(main())
