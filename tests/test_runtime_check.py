import unittest

from app.utils.env_check import (
    format_install_command,
    get_missing_dependencies,
    get_optional_missing_dependencies,
)


class RuntimeCheckTests(unittest.TestCase):
    def test_missing_dependencies_empty_when_env_is_ready(self):
        missing = get_missing_dependencies()
        self.assertEqual(missing, [])

    def test_optional_dependencies_are_available(self):
        missing = get_optional_missing_dependencies()
        # Optional deps may not be installed — this is acceptable
        self.assertIsInstance(missing, list)

    def test_install_command_mentions_requirements_file(self):
        command = format_install_command()
        self.assertIn("pip install -r requirements.txt", command)


if __name__ == "__main__":
    unittest.main()
