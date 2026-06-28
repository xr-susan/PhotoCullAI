from pathlib import Path

from app.core.summary import format_bytes, summarize_results
from app.core.types import MediaResult


def _result(path: str, verdict: str, category: str = "portrait", group: int = -1, keep: bool = False):
    return MediaResult(
        path=path,
        media_type="image",
        category=category,
        score=80.0 if verdict == "keep" else 40.0,
        verdict=verdict,
        reason="test",
        duplicate_group=group,
        duplicate_keep=keep,
    )


def test_format_bytes():
    assert format_bytes(0) == "0 B"
    assert format_bytes(1024) == "1.0 KB"
    assert format_bytes(1024 * 1024) == "1.0 MB"


def test_summarize_results_counts_and_space(tmp_path: Path):
    keep_file = tmp_path / "keep.jpg"
    junk_file = tmp_path / "junk.jpg"
    review_file = tmp_path / "review.jpg"
    keep_file.write_bytes(b"k" * 10)
    junk_file.write_bytes(b"j" * 2048)
    review_file.write_bytes(b"r" * 30)

    results = [
        _result(str(keep_file), "keep", "portrait,landscape", group=1, keep=True),
        _result(str(junk_file), "junk", "portrait", group=1),
        _result(str(review_file), "review", "text"),
    ]

    summary = summarize_results(results)

    assert summary["total"] == 3
    assert summary["keep"] == 1
    assert summary["review"] == 1
    assert summary["junk"] == 1
    assert summary["categories"]["portrait"] == 2
    assert summary["categories"]["landscape"] == 1
    assert summary["duplicate_groups"] == 1
    assert summary["duplicate_items"] == 2
    assert summary["duplicate_junk"] == 1
    assert summary["estimated_reclaimable_bytes"] == 2048
    assert summary["estimated_reclaimable"] == "2.0 KB"


def test_summarize_results_tracks_missing_files(tmp_path: Path):
    missing = tmp_path / "missing.jpg"
    summary = summarize_results([_result(str(missing), "junk")])

    assert summary["missing_files"] == 1
    assert summary["estimated_reclaimable_bytes"] == 0
