"""The step plan: what to do, how many iterations each step gets, and how it is going.

``make_plan`` turns a sizing assessment into steps with an iteration budget
each. As the loop runs, ``record`` logs every iteration against the active
step, ``evaluate`` reads the log (how close, what the product is, whether the
estimate was right or wrong), and ``adjust`` changes the remaining plan to fit
what was seen. The plan is one JSON-serializable dict, so it can be written
beside the ledger and resumed.

Everything here is deterministic and reads only the dict it is given. It judges
from facts the loop already has: whether the acceptance checks passed, the
worker's own step markers, the files its status block names, and whether it
reported itself stuck. A step finishes only when its checks passed and the
worker said the step was done; a worker that never says so leaves the pace
unmeasured, and the evaluation says that instead of guessing. The thresholds
are starting policy, not measured results.
"""
import copy
import math

from . import sizing

GOALS = {
    "plan": "the approach and the files to touch are written down",
    "research": "the open questions are answered with evidence",
    "design": "the design is written and the interfaces are named",
    "skeleton": "the structure exists and the acceptance checks can run",
    "implement": "the change exists and the acceptance checks pass",
    "core": "the central behavior works under the acceptance checks",
    "integrate": "the parts work together under the acceptance checks",
    "verify": "the whole objective is checked end to end with evidence",
    "harden": "the failure cases and edge cases are handled and tested",
    "polish": "the loose ends are closed and the result is presentable",
}
DEFAULT_GOAL = "the step's deliverable exists and the acceptance checks pass"

PACE_LATE = 1.25       # finished steps cost this much more than planned: estimate too low
PACE_EARLY = 0.75      # ... this much less: estimate too high
PACE_RAISE = 1.5       # late enough to also ask for a stronger model
RESCALE_CAP = 2.0
HARD_CAP = 2.0         # total iterations beyond this multiple of the plan stop the loop
STALL_FAILURES = 3
STALL_NO_FILES = 3
FINISHED = ("done", "closed")


def make_plan(assessment, names=None):
    """Return a fresh plan for an assessment.

    ``names`` replaces the template's step names; the tier's iteration total is
    spread over them, at least one each.
    """
    template = sizing.TEMPLATES[assessment.tier]
    if names:
        names = list(names)
        if not names or len(set(names)) != len(names) or not all(
                isinstance(name, str) and name.strip() for name in names):
            raise ValueError("step names must be unique nonempty text")
        total = max(sum(count for _, count in template), len(names))
        base, extra = divmod(total, len(names))
        template = tuple((name, base + (1 if index < extra else 0))
                         for index, name in enumerate(names))
    steps = [{"name": name, "iterations": count, "used": 0, "status": "pending",
              "goal": GOALS.get(name, DEFAULT_GOAL)} for name, count in template]
    steps[0]["status"] = "active"
    return {"tier": assessment.tier, "strength": assessment.strength,
            "revision": 0, "steps": steps, "log": [], "history": [], "halt": None,
            "rescaled_at": 0, "raised_for_pace": False}


def _active(plan):
    return next((step for step in plan["steps"] if step["status"] == "active"), None)


def _bump(strength):
    return sizing._bump(strength)


def record(plan, passed, step_done=False, tests_claim=None, files=None, stuck=False):
    """Log one finished iteration against the active step and return a new plan.

    ``files`` is the number of files the worker's status block named, or None
    when it gave no valid block.
    """
    plan = copy.deepcopy(plan)
    step = _active(plan)
    if step is None:
        return plan
    step["used"] += 1
    plan["log"].append({"step": step["name"], "passed": bool(passed),
                        "tests_claim": tests_claim, "files": files, "stuck": bool(stuck)})
    if passed and step_done:
        step["status"] = "done"
        following = next((s for s in plan["steps"] if s["status"] == "pending"), None)
        if following is not None:
            following["status"] = "active"
    return plan


def complete(plan):
    """Close every unfinished step because the worker reported the objective done."""
    plan = copy.deepcopy(plan)
    for step in plan["steps"]:
        if step["status"] not in FINISHED:
            step["status"] = "closed"
    return plan


def finished(plan):
    """True when every step is done or closed."""
    return all(step["status"] in FINISHED for step in plan["steps"])


def _trailing_failures(log):
    count = 0
    for entry in reversed(log):
        if entry["passed"]:
            break
        count += 1
    return count


def evaluate(plan):
    """Read the log: how close are we, what do we have, and was the estimate right."""
    steps, log = plan["steps"], plan["log"]
    total = sum(step["iterations"] for step in steps)
    done = [step for step in steps if step["status"] == "done"]
    expected = sum(step["iterations"] for step in done)
    actual = sum(step["used"] for step in done)
    pace = round(actual / expected, 2) if expected else None
    current = _active(plan)
    failures = _trailing_failures(log)
    passes = sum(entry["passed"] for entry in log)
    all_finished = all(step["status"] in FINISHED for step in steps)

    if all_finished:
        product = "complete: every step is finished"
    elif passes == 0:
        product = "nothing passing yet: no iteration has met the acceptance checks"
    elif log and log[-1]["passed"]:
        product = "working: the last iteration passed and the active step is unfinished"
    else:
        product = "regressed: checks passed earlier and are failing now"

    recent = log[-STALL_NO_FILES:]
    no_files = (len(recent) == STALL_NO_FILES
                and all(entry["files"] == 0 for entry in recent))
    stalled = (failures >= STALL_FAILURES or no_files
               or bool(log and log[-1]["stuck"]))
    exhausted = len(log) > HARD_CAP * total

    if all_finished:
        verdict = "done"
    elif stalled:
        verdict = "stalled"
    elif exhausted:
        verdict = "exhausted"
    elif (current and current["used"] > current["iterations"]) or (pace and pace > PACE_LATE):
        verdict = "behind"
    elif pace and pace < PACE_EARLY:
        verdict = "ahead"
    else:
        verdict = "on_track"

    if pace is None:
        estimate = "unmeasured: no step has finished with the worker's step-done marker"
    elif pace > PACE_LATE:
        estimate = "too low: finished steps cost %.2fx their plan" % pace
    elif pace < PACE_EARLY:
        estimate = "too high: finished steps cost %.2fx their plan" % pace
    else:
        estimate = "about right: finished steps cost %.2fx their plan" % pace
    return {
        "verdict": verdict, "product": product, "estimate": estimate, "pace": pace,
        "iterations_used": len(log), "iterations_planned": total,
        "steps_done": len(done), "steps_total": len(steps),
        "fraction_done": round(expected / total, 2) if total else 0.0,
        "current_step": current["name"] if current else None,
        "current_used": current["used"] if current else 0,
        "current_budget": current["iterations"] if current else 0,
        "consecutive_failures": failures,
    }


def adjust(plan, evaluation):
    """Return ``(new_plan, actions)``: the plan changed to fit what was seen."""
    plan = copy.deepcopy(plan)
    actions = []
    verdict = evaluation["verdict"]
    if verdict == "done":
        return plan, actions

    def note(kind, detail):
        actions.append({"action": kind, "detail": detail})

    if verdict in ("stalled", "exhausted"):
        reason = ("stalled: %d failures in a row, no files changed, or the worker reported itself stuck"
                  % evaluation["consecutive_failures"] if verdict == "stalled" else
                  "exhausted: %d iterations is over %.0fx the plan of %d"
                  % (evaluation["iterations_used"], HARD_CAP, evaluation["iterations_planned"]))
        plan["halt"] = reason
        note("ask_operator", reason)
    else:
        if evaluation["consecutive_failures"] >= 2 and plan["strength"] != "strong":
            plan["strength"] = _bump(plan["strength"])
            note("raise_strength", "two failures in a row; now %s" % plan["strength"])
        step = _active(plan)
        if step is not None and step["used"] >= step["iterations"] and evaluation["current_used"]:
            step["iterations"] += 1
            note("extend_step", "%s is at its %d iterations unfinished; given one more"
                 % (step["name"], step["iterations"] - 1))
        pace = evaluation["pace"]
        if pace is not None and evaluation["steps_done"] >= 2 \
                and evaluation["steps_done"] > plan["rescaled_at"]:
            late, early = pace > PACE_LATE, pace < PACE_EARLY
            if late or early:
                factor = min(pace, RESCALE_CAP) if late else max(pace, 0.5)
                for pending in plan["steps"]:
                    if pending["status"] == "pending":
                        pending["iterations"] = max(1, math.ceil(pending["iterations"] * factor))
                plan["rescaled_at"] = evaluation["steps_done"]
                note("rescale_remaining", "estimate was %s; remaining steps scaled by %.2f"
                     % ("too low" if late else "too high", factor))
            if pace >= PACE_RAISE and not plan["raised_for_pace"] and plan["strength"] != "strong":
                plan["strength"] = _bump(plan["strength"])
                plan["raised_for_pace"] = True
                note("raise_strength", "steps cost %.2fx their plan; now %s" % (pace, plan["strength"]))
    if actions:
        plan["revision"] += 1
        plan["history"].append({"revision": plan["revision"], "after_iteration": len(plan["log"]),
                                "verdict": verdict, "actions": actions})
    return plan, actions


def step_brief(plan):
    """Return the header that tells the worker which step it is on, or ''.

    It names the step, its place in the plan, what done means, and the two
    markers the evaluation reads. Without the step-done marker no step can
    finish, so the brief always asks for it.
    """
    step = _active(plan)
    if step is None:
        return ""
    number = [s["name"] for s in plan["steps"]].index(step["name"]) + 1
    return (
        "[Overseer plan] Step %d of %d, '%s' (iteration %d of %d). Done when: %s. "
        "When that is true and the acceptance checks pass, print OVERSEER_STEP_DONE on its "
        "own line. Print OVERSEER_DONE instead only if the whole objective is finished."
        % (number, len(plan["steps"]), step["name"], step["used"] + 1,
           step["iterations"], step["goal"]))


def render_plan(plan):
    lines = ["Plan (%s tier, revision %d, %s model): %d iteration(s) over %d step(s)"
             % (plan["tier"], plan["revision"], plan["strength"],
                sum(s["iterations"] for s in plan["steps"]), len(plan["steps"]))]
    for number, step in enumerate(plan["steps"], 1):
        lines.append("  %d. %-10s %2d iter  [%s, %d used]  %s"
                     % (number, step["name"], step["iterations"], step["status"],
                        step["used"], step["goal"]))
    return "\n".join(lines)


def render_evaluation(evaluation, actions=()):
    lines = [
        "Verdict: %s" % evaluation["verdict"],
        "Progress: %d/%d steps done, %d of %d planned iterations used (%.0f%% of the plan finished)"
        % (evaluation["steps_done"], evaluation["steps_total"], evaluation["iterations_used"],
           evaluation["iterations_planned"], evaluation["fraction_done"] * 100),
        "Product: " + evaluation["product"],
        "Estimate: " + evaluation["estimate"],
    ]
    if evaluation["current_step"]:
        lines.append("Now: %s, iteration %d of %d" % (
            evaluation["current_step"], evaluation["current_used"], evaluation["current_budget"]))
    lines.extend("Adjusted: %s: %s" % (a["action"], a["detail"]) for a in actions)
    return "\n".join(lines)
