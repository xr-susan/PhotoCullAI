from collections import Counter, defaultdict
from pathlib import Path

from app.core.types import MediaResult


def _file_size(path: str) -> int:
    try:
        return Path(path).stat().st_size
    except OSError:
        return 0


def format_bytes(size: int) -> str:
    units = ("B", "KB", "MB", "GB", "TB")
    value = float(max(0, size))
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024


def summarize_results(results: list[MediaResult]) -> dict:
    verdicts = Counter(r.verdict for r in results)
    media_types = Counter(r.media_type for r in results)
    categories = Counter()
    duplicate_groups = defaultdict(list)
    reclaimable_bytes = 0
    missing_files = 0

    for result in results:
        for category in result.category.split(","):
            category = category.strip() or "unknown"
            categories[category] += 1

        size = _file_size(result.path)
        if size == 0 and not Path(result.path).exists():
            missing_files += 1
        if result.verdict == "junk":
            reclaimable_bytes += size

        if result.duplicate_group >= 0:
            duplicate_groups[result.duplicate_group].append(result)

    duplicate_sets = [group for group in duplicate_groups.values() if len(group) > 1]
    duplicate_junk = sum(
        1
        for group in duplicate_sets
        for item in group
        if item.verdict == "junk" and not item.duplicate_keep
    )

    return {
        "total": len(results),
        "keep": verdicts.get("keep", 0),
        "review": verdicts.get("review", 0),
        "junk": verdicts.get("junk", 0),
        "media_types": dict(sorted(media_types.items())),
        "categories": dict(sorted(categories.items())),
        "duplicate_groups": len(duplicate_sets),
        "duplicate_items": sum(len(group) for group in duplicate_sets),
        "duplicate_junk": duplicate_junk,
        "estimated_reclaimable_bytes": reclaimable_bytes,
        "estimated_reclaimable": format_bytes(reclaimable_bytes),
        "missing_files": missing_files,
    }
