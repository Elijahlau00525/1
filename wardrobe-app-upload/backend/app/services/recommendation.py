from __future__ import annotations

import itertools
import random
from dataclasses import dataclass

from ..models import ClothingItem


@dataclass
class OutfitResult:
    score: float
    reasons: list[str]
    slots: dict[str, ClothingItem]


def generate_outfit(items: list[ClothingItem], occasion: str = "all") -> OutfitResult | None:
    candidate_items = [item for item in items if _occasion_match(item.occasion, occasion)]

    groups = {
        "top": [i for i in candidate_items if i.category == "top"],
        "bottom": [i for i in candidate_items if i.category == "bottom"],
        "shoes": [i for i in candidate_items if i.category == "shoes"],
        "outer": [i for i in candidate_items if i.category == "outer"],
        "accessory": [i for i in candidate_items if i.category == "accessory"],
    }

    if not groups["top"] or not groups["bottom"] or not groups["shoes"]:
        return None

    best: OutfitResult | None = None

    top_pool = _sample(groups["top"], 12)
    bottom_pool = _sample(groups["bottom"], 12)
    shoes_pool = _sample(groups["shoes"], 10)
    outer_pool = _sample(groups["outer"], 8)
    accessory_pool = _sample(groups["accessory"], 8)

    for top, bottom, shoes in itertools.product(top_pool, bottom_pool, shoes_pool):
        slots = {
            "top": top,
            "bottom": bottom,
            "shoes": shoes,
        }

        if outer_pool:
            slots["outer"] = _pick_best_addon(outer_pool, [top, bottom, shoes])

        if accessory_pool:
            slots["accessory"] = _pick_best_addon(accessory_pool, [top, bottom, shoes])

        score, reasons = _score_outfit(slots, occasion)
        score += random.random() * 2.2

        if not best or score > best.score:
            best = OutfitResult(score=score, reasons=reasons, slots=slots)

    return best


def _score_outfit(slots: dict[str, ClothingItem], occasion: str) -> tuple[float, list[str]]:
    reasons: list[str] = []

    top = slots["top"]
    bottom = slots["bottom"]
    shoes = slots["shoes"]

    score = 0.0

    # Rule 1: tone harmony (inspired by high-engagement outfit posts)
    harmony = _pair_harmony(top, bottom) + _pair_harmony(bottom, shoes) + _pair_harmony(top, shoes)
    if harmony > 60:
        reasons.append("同色系或邻近色协调")
    score += harmony

    # Rule 2: depth contrast for visual layering
    light_span = max(top.lightness, bottom.lightness, shoes.lightness) - min(
        top.lightness, bottom.lightness, shoes.lightness
    )
    if 18 <= light_span <= 58:
        score += 16
        reasons.append("深浅对比清晰")

    # Rule 3: one accent color, others neutral
    sats = [top.saturation, bottom.saturation, shoes.saturation]
    if max(sats) >= 48 and (sum(sorted(sats)[:2]) / 2) <= 28:
        score += 10
        reasons.append("一处亮点配色")

    # Rule 4: silhouette balance
    if {top.fit, bottom.fit} == {"slim", "loose"}:
        score += 9
        reasons.append("松紧轮廓平衡")

    # Rule 5: occasion priority
    occasion_bonus = 0.0
    for item in slots.values():
        if item.occasion == occasion:
            occasion_bonus += 4
        elif item.occasion == "all":
            occasion_bonus += 1.6
    score += occasion_bonus

    # Rule 6: style tags that mirror popular clean/commute aesthetics
    tags = _collect_tags(slots)
    if "clean" in tags:
        score += 5
    if occasion == "work" and "neutral" in tags:
        score += 6
        reasons.append("通勤中性色稳定")
    if occasion == "date" and "accent" in tags:
        score += 6
        reasons.append("约会造型有记忆点")

    if not reasons:
        reasons.append("基础配色稳定")

    return round(score, 2), reasons


def _pair_harmony(a: ClothingItem, b: ClothingItem) -> float:
    hue_gap = _hue_distance(a.hue, b.hue)
    sat_gap = abs(a.saturation - b.saturation)

    result = 0.0
    if hue_gap <= 24:
        result += 25
    elif 150 <= hue_gap <= 210:
        result += 22
    elif hue_gap <= 60:
        result += 15
    else:
        result += max(4, 11 - hue_gap / 18)

    result += max(3, 12 - sat_gap * 0.5)
    return result


def _hue_distance(h1: float, h2: float) -> float:
    gap = abs(h1 - h2)
    return min(gap, 360 - gap)


def _occasion_match(item_occasion: str, selected: str) -> bool:
    if selected == "all":
        return True
    return item_occasion == selected or item_occasion == "all"


def _pick_best_addon(pool: list[ClothingItem], anchors: list[ClothingItem]) -> ClothingItem:
    return max(pool, key=lambda addon: sum(_pair_harmony(addon, a) for a in anchors))


def _sample(pool: list[ClothingItem], max_count: int) -> list[ClothingItem]:
    if len(pool) <= max_count:
        return pool
    copy = list(pool)
    random.shuffle(copy)
    return copy[:max_count]


def _collect_tags(slots: dict[str, ClothingItem]) -> set[str]:
    tags: set[str] = set()
    for item in slots.values():
        raw_tags = item.style_tags.strip()
        if raw_tags:
            for tag in raw_tags.split(","):
                clean = tag.strip()
                if clean:
                    tags.add(clean)
    return tags
