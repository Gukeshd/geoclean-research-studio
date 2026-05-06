import csv
from difflib import SequenceMatcher, get_close_matches

from app.core.config import get_settings


DISTRICT_MASTER: dict[str, list[str]] = {
    "Maharashtra": ["Mumbai Suburban", "Mumbai City", "Pune", "Nagpur", "Thane", "Nashik"],
    "Karnataka": ["Bengaluru Urban", "Bengaluru Rural", "Mysuru", "Dakshina Kannada"],
    "Assam": ["Kamrup Metropolitan", "Kamrup", "Dibrugarh", "Cachar"],
    "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Tiruchirappalli"],
    "Kerala": ["Ernakulam", "Thiruvananthapuram", "Kozhikode", "Thrissur"],
    "Bihar": ["Patna", "Gaya", "Muzaffarpur", "Nalanda"],
    "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot"],
}

ALIASES = {
    "mumbai suburb": "Mumbai Suburban",
    "mumbai suburban district": "Mumbai Suburban",
    "bangalore urban": "Bengaluru Urban",
    "kamrup metro": "Kamrup Metropolitan",
    "trivandrum": "Thiruvananthapuram",
}


def load_aliases() -> dict[str, str]:
    aliases = dict(ALIASES)
    path = get_settings().district_alias_path
    if not path.exists():
        return aliases
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            original = normalize_name(row.get("original"))
            standard = (row.get("standard") or "").strip()
            if original and standard:
                aliases[original] = standard
    return aliases


def normalize_name(value: object) -> str:
    return " ".join(str(value or "").strip().lower().replace(".", " ").split())


def harmonize_district(district: object, state: object | None = None) -> dict[str, object]:
    raw = str(district or "").strip()
    key = normalize_name(raw)
    if not raw:
        return {"raw": raw, "standard": None, "confidence": 0, "valid": False, "reason": "Missing district"}

    aliases = load_aliases()
    if key in aliases:
        standard = aliases[key]
        return {"raw": raw, "standard": standard, "confidence": 0.98, "valid": _valid_state(standard, state)}

    candidates = _state_candidates(state) or [district for values in DISTRICT_MASTER.values() for district in values]
    normalized_lookup = {normalize_name(candidate): candidate for candidate in candidates}
    if key in normalized_lookup:
        standard = normalized_lookup[key]
        return {"raw": raw, "standard": standard, "confidence": 1.0, "valid": True}

    matched_key, confidence = _best_fuzzy_match(key, list(normalized_lookup.keys()))
    if not matched_key:
        return {"raw": raw, "standard": None, "confidence": 0, "valid": False, "reason": "No close India district match"}

    standard = normalized_lookup[matched_key]
    return {"raw": raw, "standard": standard, "confidence": confidence, "valid": _valid_state(standard, state)}


def _best_fuzzy_match(key: str, candidates: list[str]) -> tuple[str | None, float]:
    try:
        from rapidfuzz import fuzz, process
    except ImportError:
        match = get_close_matches(key, candidates, n=1, cutoff=0.72)
        if not match:
            return None, 0
        return match[0], round(SequenceMatcher(None, key, match[0]).ratio(), 2)
    result = process.extractOne(key, candidates, scorer=fuzz.token_sort_ratio, score_cutoff=72)
    if result is None:
        return None, 0
    return str(result[0]), round(float(result[1]) / 100, 2)


def validate_state_district(state: object, district: object) -> dict[str, object]:
    standard = harmonize_district(district, state)
    if standard.get("standard") is None:
        return {**standard, "state": state, "mismatch": True}
    return {
        **standard,
        "state": state,
        "mismatch": not _valid_state(str(standard["standard"]), state),
    }


def _state_candidates(state: object | None) -> list[str]:
    if not state:
        return []
    state_key = normalize_name(state)
    for master_state, districts in DISTRICT_MASTER.items():
        if normalize_name(master_state) == state_key:
            return districts
    return []


def _valid_state(district: str, state: object | None) -> bool:
    candidates = _state_candidates(state)
    return not candidates or district in candidates
