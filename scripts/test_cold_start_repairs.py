import unittest
from compile_destination_profile import normalize_journey_phases
from validate_research_pack import validate, scaffold


class ColdStartRepairs(unittest.TestCase):
    def test_missing_phase_bindings_preserve_all_days(self):
        profile = {"itinerary": [{}, {}, {}, {}], "journey_phases": [{"title": "City"}, {"title": "Coast"}]}
        normalize_journey_phases(profile)
        self.assertEqual(profile["journey_phases"][0]["day_numbers"], [1, 2, 3, 4])

    def test_partial_and_duplicate_bindings_rejected(self):
        for numbers in ([1], [1, 1], [1, 3]):
            with self.assertRaises(SystemExit):
                normalize_journey_phases({"itinerary": [{}, {}], "journey_phases": [{"day_numbers": numbers}]})

    def test_valid_grouping_preserved(self):
        phases = [{"title": "First", "day_numbers": [1]}, {"title": "Next", "day_numbers": [2]}]
        profile = {"itinerary": [{}, {}], "journey_phases": phases}
        normalize_journey_phases(profile)
        self.assertEqual(profile["journey_phases"], phases)

    def test_menu_string_fails_at_pack_boundary(self):
        data = scaffold("modules-practical")
        data["food"]["menu_primer"] = ["plain string"]
        self.assertTrue(any(e["pointer"] == "/food/menu_primer/0" for e in validate("modules-practical", data)))


if __name__ == "__main__":
    unittest.main()
