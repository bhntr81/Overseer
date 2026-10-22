"""Task sizing: how big is this project, and what should the blueprint spend on it?

Before a blueprint is written, the size of the objective decides how many steps
and repairs it plans, how strong a model the worker needs, and how large a
budget the contract carries. A weekend-sized lab feature does not need the
iterations or the model of a solver.

The assessment is deterministic and reads only the description it is given and
the signals the operator passes. It asks no model, runs no command, and touches
no file. Five dimensions are scored 0 to 3 from keywords in the description;
an operator or a prior agent who knows better overrides any of them. The tier
tables are starting policy choices, not measured results, so every assessment is
labelled provisional. Cost and token usage are unknown and stay null.
"""
from dataclasses import dataclass
import re

from .strikes import BLUEPRINT_BOUND

DIMENSIONS = ("breadth", "novelty", "uncertainty", "integration", "risk")
TIERS = ("trivial", "small", "medium", "large", "major")
STRENGTHS = ("light", "standard", "strong")
# Upper score bound of each tier; anything above the last bound is major.
BOUNDS = (2, 4, 7, 10)

# The steps of each tier's starting plan, as (name, iterations). The blueprint
# stage may replace the names; the iterations are spread over whatever it names.
TEMPLATES = {
    "trivial": (("implement", 2),),
    "small": (("implement", 2), ("verify", 1), ("polish", 1)),
    "medium": (("plan", 1), ("core", 3), ("integrate", 2), ("verify", 2), ("polish", 2)),
    "large": (("design", 2), ("skeleton", 3), ("core", 6), ("integrate", 4),
              ("verify", 4), ("harden", 3), ("polish", 2)),
    "major": (("research", 4), ("design", 4), ("skeleton", 6), ("core", 12),
              ("integrate", 8), ("verify", 8), ("harden", 6), ("polish", 4)),
}
# tier: (repair_allowance, strength, reasoning_effort, wall_time_seconds)
PLAN = {
    "trivial": (0, "light", "low", 600),
    "small": (1, "light", "medium", 1800),
    "medium": (2, "standard", "medium", 7200),
    "large": (2, "strong", "high", 21600),
    "major": (2, "strong", "high", 86400),
}

# Each pattern lists the words that put a dimension at that level; the highest
# matching level wins. Level 0 is the default.
SIGNALS = {
    "breadth": (
        (3, r"\bfrom scratch\b|\bsolver\b|\bcompiler\b|\bengine\b|\bplatform\b|\bframework\b"
            r"|\bentire\b|\bwhole (?:app|codebase|project)\b|\bre-?architect"),
        (2, r"\bapp(?:lication)?\b|\bmodule\b|\bfeature\b|\bdashboard\b|\bpipeline\b"
            r"|\brefactor|\bmigrat|\bseveral\b|\bmultiple\b|\bacross\b"
            r"|\bmechanics\b|\bphysics\b|\bsimulat|\banimat"),
        (1, r"\badd\b|\btweak|\bgraphics?\b|\bstyle\b|\bui\b|\blab\b|\bfix\b|\brename\b|\bpolish"),
    ),
    "novelty": (
        (3, r"\balgorithm\b|\bnovel\b|\bprove\b|\bfrom scratch\b|\binvent"),
        (2, r"\bbuild\b|\bnew\b|\bdesign\b|\bcreate\b|\bimplement\b|\bmechanics\b"),
        (1, r"\bextend\b|\bimprove\b|\badd\b|\bexisting\b|\bupgrade\b"),
    ),
    "uncertainty": (
        (3, r"\bunknown\b|\bunclear\b|\bundocumented\b|\breverse[- ]engineer|\bexperimental\b"),
        (2, r"\binvestigate\b|\bresearch\b|\bfigure out\b|\bexplore\b|\bsolver\b|\bnot sure\b"),
        (0, r"\bwell[- ]known\b|\bstandard\b|\bsimple\b|\bstraightforward\b"),
    ),
    "integration": (
        (2, r"\bapi\b|\bnetwork\b|\bdatabase\b|\bhardware\b|\bgpu\b|\boauth\b|\bdeploy"
            r"|\bserver\b|\bssh\b|\bthird[- ]party\b|\breal-?time\b|\bmulti-?player\b"),
        (1, r"\bbrowser\b|\bcanvas\b|\bfile\b|\bwindows\b|\bexternal\b"),
    ),
    "risk": (
        (3, r"\bpassword|\bcredential|\bprivate key|\bwallet\b|\bpayment|\bmoney\b"
            r"|\bproduction\b|\birreversible\b|\bdelete\b|\bwipe\b"),
        (2, r"\bsecurity\b|\bauth\b|\bmigration\b|\bpublish\b|\bdeploy"),
    ),
}
# Words that mark a standard, well-understood task pull uncertainty to zero
# only when nothing raises it; the table above already encodes that by level.
CLAUSES = re.compile(r"\band\b|,|;")


@dataclass(frozen=True)
class Assessment:
    tier: str
    score: int
    dimensions: dict
    steps: int
    repair_allowance: int
    strength: str
    escalation_strength: str
    reasoning_effort: str
    budget: dict
    rationale: tuple
    provisional: bool = True

    def as_dict(self):
        return {
            "tier": self.tier,
            "score": self.score,
            "dimensions": dict(self.dimensions),
            "steps": self.steps,
            "repair_allowance": self.repair_allowance,
            "strength": self.strength,
            "escalation_strength": self.escalation_strength,
            "reasoning_effort": self.reasoning_effort,
            "budget": dict(self.budget),
            "rationale": list(self.rationale),
            "provisional": self.provisional,
        }


def _level(dimension, text):
    for level, pattern in SIGNALS[dimension]:
        if re.search(pattern, text):
            return level
    return 0


def _bump(strength):
    return STRENGTHS[min(STRENGTHS.index(strength) + 1, len(STRENGTHS) - 1)]


def assess(description, overrides=None):
    """Return the Assessment of one objective.

    ``overrides`` maps a dimension name to an integer from 0 to 3 and replaces
    the keyword reading of that dimension.
    """
    if not isinstance(description, str) or not description.strip():
        raise ValueError("description must be nonempty text")
    overrides = overrides or {}
    for name, value in overrides.items():
        if name not in DIMENSIONS:
            raise ValueError("unknown dimension: %s (use %s)" % (name, ", ".join(DIMENSIONS)))
        if type(value) is not int or not 0 <= value <= 3:
            raise ValueError("dimension %s must be an integer from 0 to 3" % name)

    text = description.lower()
    dimensions = {name: _level(name, text) for name in DIMENSIONS}
    # Several separate deliverables widen the work.
    clauses = len([part for part in CLAUSES.split(text) if part.strip()])
    if clauses >= 3 and dimensions["breadth"] < 3:
        dimensions["breadth"] += 1
    dimensions.update(overrides)

    score = sum(dimensions.values())
    index = next((i for i, bound in enumerate(BOUNDS) if score <= bound), len(BOUNDS))
    rationale = ["score %d from %s" % (score, ", ".join("%s %d" % item for item in dimensions.items()))]
    if max(dimensions.values()) == 3 and index < 2:
        index = 2
        rationale.append("a dimension at 3 raises the tier to at least medium")
    tier = TIERS[index]

    repairs, strength, effort, wall = PLAN[tier]
    steps = len(TEMPLATES[tier])
    repairs = min(repairs, BLUEPRINT_BOUND - 1)
    if dimensions["risk"] >= 2 or dimensions["uncertainty"] == 3:
        stronger = _bump(strength)
        if stronger != strength:
            rationale.append("risk or uncertainty raises the model strength to %s" % stronger)
        strength = stronger
    if _bump(strength) == strength:
        rationale.append("start with a %s model; no stronger model exists, so stop at the repair bound"
                         % strength)
    else:
        rationale.append("start with a %s model; escalate to %s after a failed repair"
                         % (strength, _bump(strength)))
    budget = {
        "wall_time_seconds": wall,
        "token_limit": None,
        "cost_limit_usd": None,
        "resource_limits": None,
        "repair_allowance": repairs,
    }
    return Assessment(tier, score, dimensions, steps, repairs, strength, _bump(strength),
                      effort, budget, tuple(rationale))


def render(assessment):
    lines = [
        "Tier: %s (score %d, provisional)" % (assessment.tier, assessment.score),
        "Plan: %d step(s), %d iteration(s), %d repair(s) allowed"
        % (assessment.steps, sum(n for _, n in TEMPLATES[assessment.tier]), assessment.repair_allowance),
        "Model: %s strength, %s reasoning%s"
        % (assessment.strength, assessment.reasoning_effort,
           "" if assessment.escalation_strength == assessment.strength else
           "; escalate to %s after a failed repair" % assessment.escalation_strength),
        "Wall time: %d s" % assessment.budget["wall_time_seconds"],
        "Dimensions: " + ", ".join("%s %d" % item for item in assessment.dimensions.items()),
    ]
    lines.extend("- " + reason for reason in assessment.rationale)
    return "\n".join(lines)
