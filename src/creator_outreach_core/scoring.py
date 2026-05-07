"""Creator scoring module — v1 heuristic scorer.

Dimensions and maximum points
------------------------------
audience_fit     0-30   (language + region)
contactability   0-25   (contact_email + link_in_bio)
commercial_signal 0-15  (bio keywords: shop/store/collab/partnership/business)
size_fit         0-15   (followers_count tier)
freshness        0-10   (last_enriched_at within 30 days)
risk_penalty     -10 per risk_flag

Tune weights by editing WEIGHTS below without touching the scoring logic.

Tier thresholds
---------------
high  >= 75
mid   50-74
low   < 50
"""
from __future__ import annotations

import datetime
from typing import Any

from creator_outreach_core.models import Creator

# ---------------------------------------------------------------------------
# Tunable weight constants
# ---------------------------------------------------------------------------

WEIGHTS: dict[str, int] = {
    # contactability
    "contact_email": 25,
    "link_in_bio": 5,
    # commercial_signal
    "commercial_keywords": 15,
    # size_fit tiers
    "size_10k_300k": 15,
    "size_300k_1m": 10,
    "size_1m_plus": 5,
    # audience_fit
    "language_en": 10,
    "region_us_eu": 20,
    # freshness
    "enriched_within_30d": 10,
    # risk
    "risk_per_flag": -10,
}

_COMMERCIAL_KEYWORDS = {"shop", "store", "collab", "partnership", "business"}
_TIER_HIGH = 75
_TIER_MID = 50
_FRESHNESS_DAYS = 30


def _now_utc() -> datetime.datetime:
    return datetime.datetime.utcnow()


def score_creator(creator: Creator) -> dict[str, Any]:
    """Return a scoring dict for *creator*.

    Returns
    -------
    dict with keys: ``score`` (int 0-100), ``tier`` (str),
    ``reasons`` (list[str]), ``risks`` (list[str]).
    """
    score = 0
    reasons: list[str] = []
    risks: list[str] = []

    # --- contactability ---
    if creator.contact_email:
        score += WEIGHTS["contact_email"]
        reasons.append("public_email")
    if creator.link_in_bio:
        score += WEIGHTS["link_in_bio"]
        reasons.append("link_in_bio")

    # --- commercial_signal ---
    bio_lower = (creator.bio or "").lower()
    if any(kw in bio_lower for kw in _COMMERCIAL_KEYWORDS):
        score += WEIGHTS["commercial_keywords"]
        reasons.append("shop_signal")

    # --- size_fit ---
    fc = creator.followers_count
    if fc is not None:
        if 10_000 <= fc < 300_000:
            score += WEIGHTS["size_10k_300k"]
            reasons.append("strong_size_fit")
        elif 300_000 <= fc < 1_000_000:
            score += WEIGHTS["size_300k_1m"]
            reasons.append("mid_size_fit")
        elif fc >= 1_000_000:
            score += WEIGHTS["size_1m_plus"]
            reasons.append("large_size_fit")
        # <5k: no bonus, no penalty

    # --- audience_fit ---
    if (creator.language or "").lower() == "en":
        score += WEIGHTS["language_en"]
        reasons.append("language_en")
    region = (creator.region or "").upper()
    if region in {"US", "EU"}:
        score += WEIGHTS["region_us_eu"]
        reasons.append("region_us_eu")

    # --- freshness ---
    if creator.last_enriched_at:
        try:
            enriched = datetime.datetime.fromisoformat(
                creator.last_enriched_at.replace("Z", "+00:00")
            )
            delta = _now_utc().replace(tzinfo=datetime.timezone.utc) - enriched
            if delta.days <= _FRESHNESS_DAYS:
                score += WEIGHTS["enriched_within_30d"]
                reasons.append("recently_enriched")
        except ValueError:
            pass

    # --- risk_penalty ---
    for flag in creator.risk_flags:
        if flag:
            score += WEIGHTS["risk_per_flag"]  # negative
            risks.append(flag)

    # Clamp to [0, 100]
    score = max(0, min(100, score))

    if score >= _TIER_HIGH:
        tier = "high"
    elif score >= _TIER_MID:
        tier = "mid"
    else:
        tier = "low"

    return {
        "score": score,
        "tier": tier,
        "reasons": reasons,
        "risks": risks,
    }
