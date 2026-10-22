"""Task sizing: the magnitude of an objective sets the plan, the model, and the budget."""
import io
import json
import unittest
from unittest.mock import patch

from overseer.__main__ import main
from overseer.factory import BUDGET_FIELDS, _validate_budget
from overseer.sizing import TIERS, assess, render

VECTORS = ("Improve the graphics of my vectors lab and add vector plane mechanics "
           "so wind changes the ground speed of the plane")
SOLVER = "Build a poker solver from scratch"


class SizingTests(unittest.TestCase):
    def test_lab_feature_is_small_and_cheap(self):
        result = assess(VECTORS)
        self.assertIn(result.tier, ("trivial", "small"))
        self.assertEqual(result.strength, "light")
        self.assertLessEqual(result.steps, 3)
        self.assertLessEqual(result.repair_allowance, 1)

    def test_solver_is_large_or_major_with_a_strong_model(self):
        result = assess(SOLVER)
        self.assertGreaterEqual(TIERS.index(result.tier), TIERS.index("large"))
        self.assertEqual(result.strength, "strong")
        self.assertGreater(result.steps, assess(VECTORS).steps)

    def test_budget_fits_the_factory_contract(self):
        for text in (VECTORS, SOLVER, "Rename a variable"):
            budget = assess(text).budget
            self.assertEqual(set(budget), set(BUDGET_FIELDS))
            _validate_budget(budget)
            self.assertIsNone(budget["token_limit"])
            self.assertIsNone(budget["cost_limit_usd"])

    def test_repairs_never_exceed_the_blueprint_bound(self):
        for text in (VECTORS, SOLVER, "Delete the production database"):
            self.assertLessEqual(assess(text).repair_allowance, 2)

    def test_one_severe_dimension_floors_the_tier_at_medium(self):
        result = assess("Delete the production database")
        self.assertGreaterEqual(TIERS.index(result.tier), TIERS.index("medium"))

    def test_risk_raises_model_strength(self):
        plain = assess("Add a button to the settings page")
        risky = assess("Add a button to the settings page that handles payment credentials")
        self.assertGreater(("light", "standard", "strong").index(risky.strength),
                           ("light", "standard", "strong").index(plain.strength))

    def test_override_replaces_the_keyword_reading(self):
        result = assess(VECTORS, {"breadth": 3, "novelty": 3, "uncertainty": 2})
        self.assertEqual(result.dimensions["breadth"], 3)
        self.assertGreater(TIERS.index(result.tier), TIERS.index(assess(VECTORS).tier))

    def test_invalid_input_is_rejected(self):
        for description, overrides in (("", None), ("   ", None), (None, None),
                                       ("task", {"size": 1}), ("task", {"risk": 4}),
                                       ("task", {"risk": True})):
            with self.assertRaises(ValueError):
                assess(description, overrides)

    def test_escalation_is_one_step_stronger_and_assessment_is_provisional(self):
        result = assess("Add a button")
        self.assertTrue(result.provisional)
        self.assertIn(result.escalation_strength, ("standard", "strong"))

    def test_cli_prints_text_and_json(self):
        with patch("sys.argv", ["overseer", "assess", VECTORS]), patch("sys.stdout", new=io.StringIO()) as out:
            self.assertEqual(main(), 0)
        self.assertIn("Tier:", out.getvalue())
        with patch("sys.argv", ["overseer", "assess", SOLVER, "--json", "--set", "risk=2"]), \
                patch("sys.stdout", new=io.StringIO()) as out:
            self.assertEqual(main(), 0)
        data = json.loads(out.getvalue())
        self.assertEqual(data["dimensions"]["risk"], 2)
        self.assertEqual(data["tier"], assess(SOLVER, {"risk": 2}).tier)

    def test_render_names_the_plan(self):
        text = render(assess(VECTORS))
        for word in ("Tier:", "Plan:", "Model:", "Wall time:"):
            self.assertIn(word, text)


if __name__ == "__main__":
    unittest.main()
