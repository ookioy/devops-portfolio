import unittest
from log_analyzer import parse_line, get_status_class


class TestLogAnalyzer(unittest.TestCase):

    def test_parse_valid_line(self):
        """Перевірка правильного розбору стандартного рядка Combined Log."""
        line = (
            '192.168.1.50 - - [10/Oct/2026:14:32:10 +0300] '
            '"GET /api/v1/users HTTP/1.1" 200 4523 '
            '"https://example.com/" "Mozilla/5.0"'
        )
        result = parse_line(line)
        self.assertIsNotNone(result)
        self.assertEqual(result["ip"], "192.168.1.50")
        self.assertEqual(result["status"], 200)
        self.assertEqual(result["hour"], "14:00")

    def test_parse_corrupted_line(self):
        """Перевірка стійкості: пошкоджений рядок має повертати None."""
        corrupted_line = "THIS IS A CORRUPTED LOG LINE WITHOUT PROPER FORMAT"
        result = parse_line(corrupted_line)
        self.assertIsNone(result)

    def test_parse_invalid_timestamp(self):
        """Перевірка рядка із некоректною датою."""
        invalid_date_line = (
            '10.0.0.1 - - [INVALID_DATE] "GET / HTTP/1.1" 200 100'
        )
        result = parse_line(invalid_date_line)
        self.assertIsNone(result)

    def test_parse_empty_line(self):
        """Порожній рядок має повертати None."""
        self.assertIsNone(parse_line(""))
        self.assertIsNone(parse_line("   \n"))

    def test_get_status_class(self):
        """Перевірка класифікації HTTP кодів."""
        self.assertEqual(get_status_class(200), "2xx")
        self.assertEqual(get_status_class(404), "4xx")
        self.assertEqual(get_status_class(503), "5xx")
        self.assertEqual(get_status_class(999), "Other")


if __name__ == "__main__":
    unittest.main()
