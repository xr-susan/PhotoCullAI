import tempfile
import unittest
from pathlib import Path

from app.utils.file_utils import normalize_input_paths, is_supported_media_path


class FileUtilsTests(unittest.TestCase):
    def test_normalize_input_paths_keeps_existing_unique_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            file_a = root / "a.jpg"
            file_b = root / "b.txt"
            file_a.write_text("x", encoding="utf-8")
            file_b.write_text("x", encoding="utf-8")

            result = normalize_input_paths(
                [
                    str(file_a),
                    str(file_a),
                    str(root),
                    str(file_b),
                ]
            )

            self.assertEqual(
                result,
                [
                    str(file_a.resolve()),
                    str(root.resolve()),
                    str(file_b.resolve()),
                ],
            )

    def test_is_supported_media_path(self):
        self.assertTrue(is_supported_media_path("/tmp/test.jpg"))
        self.assertTrue(is_supported_media_path("/tmp/test.mp4"))
        self.assertFalse(is_supported_media_path("/tmp/test.txt"))


if __name__ == "__main__":
    unittest.main()
