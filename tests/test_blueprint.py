"""The step plan: steps with iterations, progress evaluation, and strategy adjustment."""
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from overseer import blueprint
from overseer.__main__ import main
from overseer.sizing import assess

MEDIUM = assess("Build a new dashboard module with an api and a database")


def run(plan, *iterations):
    for passed, done in iterations:
        plan = blueprint.record(plan, passed, step_done=done, files=1)
    return plan


class BlueprintTests(unittest.TestCase):
    def test_plan_names_steps_with_iterations_and_one_active(self):
        plan = blueprint.make_plan(MEDIUM)
        self.assertGreaterEqual(len(plan["steps"]), 3)
        self.assertTrue(all(step["iterations"] >= 1 for step in plan["steps"]))
        self.assertEqual([s["status"] for s in plan["steps"]].count("active"), 1)

    def test_custom_step_names_share_the_tier_total(self):
        plan = blueprint.make_plan(MEDIUM, ["a", "b", "c"])
        self.assertEqual([s["name"] for s in plan["steps"]], ["a", "b", "c"])
        self.assertEqual(sum(s["iterations"] for s in plan["steps"]), 10)
        for bad in (["a", "a"], ["a", " "]):
            with self.assertRaises(ValueError):
                blueprint.make_plan(MEDIUM, bad)

    def test_a_step_finishes_only_on_a_passing_iteration_with_the_done_marker(self):
        plan = blueprint.make_plan(MEDIUM)
        plan = run(plan, (True, False), (False, True))
        self.assertEqual(plan["steps"][0]["status"], "active")
        plan = run(plan, (True, True))
        self.assertEqual(plan["steps"][0]["status"], "done")
        self.assertEqual(plan["steps"][1]["status"], "active")

    def test_on_pace_is_on_track_and_the_estimate_is_about_right(self):
        plan = blueprint.make_plan(MEDIUM)
        plan = run(plan, (True, True))  # plan step has 1 iteration
        ev = blueprint.evaluate(plan)
        self.assertEqual(ev["verdict"], "on_track")
        self.assertIn("about right", ev["estimate"])

    def test_slow_steps_make_the_estimate_too_low_and_rescale_what_remains(self):
        plan = blueprint.make_plan(MEDIUM)
        before = [s["iterations"] for s in plan["steps"][2:]]
        plan = run(plan, (True, True),                         # plan: 1 of 1
                   (True, False), (True, False), (True, False), (True, False), (True, True))  # core: 5 of 3
        ev = blueprint.evaluate(plan)
        self.assertIn("too low", ev["estimate"])
        plan, actions = blueprint.adjust(plan, ev)
        self.assertIn("rescale_remaining", [a["action"] for a in actions])
        after = [s["iterations"] for s in plan["steps"][2:]]
        self.assertTrue(all(a >= b for a, b in zip(after, before)) and after != before)
        # a second adjustment with no new finished step changes nothing
        again, actions = blueprint.adjust(plan, blueprint.evaluate(plan))
        self.assertNotIn("rescale_remaining", [a["action"] for a in actions])

    def test_fast_steps_make_the_estimate_too_high_and_shrink_what_remains(self):
        plan = blueprint.make_plan(MEDIUM, ["a", "b", "c", "d"])
        plan = run(plan, (True, True), (True, True))  # each budgeted 3, used 1
        ev = blueprint.evaluate(plan)
        self.assertIn("too high", ev["estimate"])
        plan, actions = blueprint.adjust(plan, ev)
        self.assertEqual(plan["steps"][2]["iterations"], 2)  # 3 planned x pace 0.33, floored at 0.5, rounded up

    def test_an_overrun_step_is_extended_by_one(self):
        plan = blueprint.make_plan(MEDIUM)
        plan = run(plan, (True, True), (True, False), (True, False), (True, False))
        plan, actions = blueprint.adjust(plan, blueprint.evaluate(plan))
        self.assertEqual(plan["steps"][1]["iterations"], 4)
        self.assertIn("extend_step", [a["action"] for a in actions])

    def test_failures_raise_strength_and_then_stall_to_the_operator(self):
        plan = blueprint.make_plan(assess("Add a button"))
        plan = run(plan, (False, False), (False, False))
        plan, actions = blueprint.adjust(plan, blueprint.evaluate(plan))
        self.assertEqual(plan["strength"], "standard")
        plan = run(plan, (False, False))
        ev = blueprint.evaluate(plan)
        self.assertEqual(ev["verdict"], "stalled")
        plan, actions = blueprint.adjust(plan, ev)
        self.assertIn("ask_operator", [a["action"] for a in actions])
        self.assertTrue(plan["halt"])

    def test_three_iterations_that_change_no_files_stall(self):
        plan = blueprint.make_plan(MEDIUM)
        for _ in range(3):
            plan = blueprint.record(plan, True, files=0)
        self.assertEqual(blueprint.evaluate(plan)["verdict"], "stalled")

    def test_unknown_files_do_not_count_as_no_progress(self):
        plan = blueprint.make_plan(MEDIUM)
        for _ in range(3):
            plan = blueprint.record(plan, True, files=None)
        self.assertNotEqual(blueprint.evaluate(plan)["verdict"], "stalled")

    def test_complete_closes_the_plan(self):
        plan = blueprint.complete(blueprint.make_plan(MEDIUM))
        ev = blueprint.evaluate(plan)
        self.assertEqual(ev["verdict"], "done")
        self.assertEqual(blueprint.adjust(plan, ev)[1], [])

    def test_functions_do_not_mutate_their_input(self):
        plan = blueprint.make_plan(MEDIUM)
        snapshot = json.dumps(plan, sort_keys=True)
        blueprint.record(plan, False)
        blueprint.adjust(plan, blueprint.evaluate(plan))
        self.assertEqual(json.dumps(plan, sort_keys=True), snapshot)

    def test_brief_names_the_step_and_asks_for_the_done_marker(self):
        plan = blueprint.make_plan(MEDIUM)
        brief = blueprint.step_brief(plan)
        for part in ("Step 1 of 5", "'plan'", "iteration 1 of 1", plan["steps"][0]["goal"],
                     "OVERSEER_STEP_DONE", "OVERSEER_DONE"):
            self.assertIn(part, brief)
        plan = run(plan, (True, True))
        self.assertIn("Step 2 of 5", blueprint.step_brief(plan))
        self.assertEqual(blueprint.step_brief(blueprint.complete(plan)), "")

    def test_cli_plan_and_progress(self):
        with patch("sys.argv", ["overseer", "assess", "Add a button", "--plan"]), \
                patch("sys.stdout", new=io.StringIO()) as out:
            self.assertEqual(main(), 0)
        self.assertIn("1. implement", out.getvalue())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "x.plan.json"
            plan = run(blueprint.make_plan(MEDIUM), (True, True))
            path.write_text(json.dumps({"objective": "x", "plan": plan}))
            with patch("sys.argv", ["overseer", "progress", str(path)]), \
                    patch("sys.stdout", new=io.StringIO()) as out:
                self.assertEqual(main(), 0)
        self.assertIn("Verdict:", out.getvalue())


if __name__ == "__main__":
    unittest.main()
