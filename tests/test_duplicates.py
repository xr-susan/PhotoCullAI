from app.core.union_find import UnionFind
from app.core.types import MediaResult


class TestUnionFind:
    def test_single_element(self):
        uf = UnionFind(1)
        assert uf.find(0) == 0
        assert uf.groups() == []

    def test_no_unions(self):
        uf = UnionFind(5)
        assert len(uf.groups()) == 0

    def test_union_creates_group(self):
        uf = UnionFind(5)
        uf.union(0, 1)
        groups = uf.groups()
        assert len(groups) == 1
        assert set(groups[0]) == {0, 1}

    def test_transitive_union(self):
        uf = UnionFind(5)
        uf.union(0, 1)
        uf.union(1, 2)
        groups = uf.groups()
        assert len(groups) == 1
        assert set(groups[0]) == {0, 1, 2}

    def test_separate_groups(self):
        uf = UnionFind(6)
        uf.union(0, 1)
        uf.union(2, 3)
        groups = uf.groups()
        assert len(groups) == 2

    def test_union_same_element(self):
        uf = UnionFind(3)
        uf.union(0, 0)
        assert uf.find(0) == 0

    def test_path_compression(self):
        uf = UnionFind(5)
        uf.union(0, 1)
        uf.union(1, 2)
        uf.union(2, 3)
        # All should have same root
        root = uf.find(0)
        assert uf.find(1) == root
        assert uf.find(2) == root
        assert uf.find(3) == root


class TestMediaResult:
    def test_basic_creation(self):
        r = MediaResult(
            path="test.jpg", media_type="image", category="portrait",
            score=80.0, verdict="keep", reason="ok"
        )
        assert r.path == "test.jpg"
        assert r.score == 80.0
        assert r.face_count == 0
        assert r.duplicate_group == -1

    def test_to_dict_excludes_embedding(self):
        r = MediaResult(
            path="test.jpg", media_type="image", category="portrait",
            score=80.0, verdict="keep", reason="ok",
            face_embedding=[1, 2, 3]
        )
        d = r.to_dict()
        assert "face_embedding" not in d
        assert d["path"] == "test.jpg"

    def test_no_dead_fields(self):
        r = MediaResult(
            path="test.jpg", media_type="image", category="portrait",
            score=80.0, verdict="keep", reason="ok"
        )
        assert not hasattr(r, "rotate_angle")
        assert not hasattr(r, "corrected_path")
