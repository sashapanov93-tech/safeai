import os
import tempfile
import unittest

import database
from personal_memory import get_relevant_memory, learn_from_message


class PersonalMemoryTests(unittest.TestCase):
    def setUp(self):
        handle, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.original_db_name = database.DB_NAME
        database.DB_NAME = self.db_path
        database.create_tables()

    def tearDown(self):
        database.DB_NAME = self.original_db_name
        os.unlink(self.db_path)

    def test_remembers_a_calming_strategy_and_uses_it_when_distressed(self):
        learn_from_message(101, "Меня очень успокаивает прогулка у моря.")

        relevant = get_relevant_memory(101, "Мне опять плохо", limit=6)

        self.assertIn(("calming", "прогулка у моря"), relevant)

    def test_does_not_mix_users(self):
        learn_from_message(101, "Мне помогает дыхательная практика.")

        self.assertEqual(get_relevant_memory(202, "Мне плохо"), [])


if __name__ == "__main__":
    unittest.main()
