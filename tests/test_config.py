from app.utils.config import get, get_section, _deep_merge, _DEFAULTS


class TestDeepMerge:
    def test_merge_no_overlap(self):
        # _deep_merge iterates defaults only; keys only in overrides are dropped
        result = _deep_merge({"a": 1}, {"b": 2})
        assert result == {"a": 1}

    def test_merge_override(self):
        result = _deep_merge({"a": 1}, {"a": 2})
        assert result["a"] == 2

    def test_merge_nested(self):
        result = _deep_merge({"sec": {"k1": 1, "k2": 2}}, {"sec": {"k2": 99}})
        assert result["sec"]["k1"] == 1
        assert result["sec"]["k2"] == 99

    def test_merge_preserves_defaults(self):
        result = _deep_merge({"a": {"x": 1}}, {})
        assert result["a"]["x"] == 1


class TestGet:
    def test_get_existing_key(self):
        assert get("app", "window_title") == "PhotoCullAI"

    def test_get_threshold_keep_score(self):
        assert get("thresholds", "keep_score") == 65

    def test_get_missing_section(self):
        assert get("nonexistent", "key") is None

    def test_get_missing_key_with_default(self):
        assert get("app", "nonexistent", "fallback") == "fallback"

    def test_get_section_returns_dict(self):
        sec = get_section("thresholds")
        assert isinstance(sec, dict)
        assert "keep_score" in sec


class TestDeadKeysRemoved:
    def test_no_review_score(self):
        sec = get_section("thresholds")
        assert "review_score" not in sec

    def test_no_max_workers_in_defaults(self):
        # max_workers was re-added as a real config, so check it exists
        assert "max_workers" in _DEFAULTS["scan"]

    def test_no_thumbnail_size(self):
        sec = get_section("app")
        assert "thumbnail_size" not in sec

    def test_no_preview_size(self):
        sec = get_section("app")
        assert "preview_size" not in sec


class TestDefaultsStructure:
    def test_has_app_section(self):
        assert "app" in _DEFAULTS

    def test_has_thresholds_section(self):
        assert "thresholds" in _DEFAULTS

    def test_has_paths_section(self):
        assert "paths" in _DEFAULTS

    def test_has_scan_section(self):
        assert "scan" in _DEFAULTS
