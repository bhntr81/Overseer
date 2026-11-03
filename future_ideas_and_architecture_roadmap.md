# Overseer: Future Ideas & Architectural Roadmap

This document captures high-level architectural proposals and feature extensions for Overseer that are slated for future implementation after core runtime stabilization.

---

## 1. Dynamic Model-Selection Agent (`overseer/modelagent.py`)

### 1.1 Overview
The Model-Selection Agent is an intelligent pre-dispatch routing and classification engine. Rather than relying on static model selection or burning frontier tokens on routine tasks, the Model Agent dynamically evaluates the semantic complexity, structural risk, and scope of an incoming task to assign the optimal model tier.

### 1.2 Strategic Objectives
- **Dynamic Complexity Routing:** Route tasks based on real-time heuristic evaluation (scope, reasoning depth, dependency impact) rather than rigid string matches.
- **Generator-Verifier Review Pipeline:** Establish a "junior coder, senior auditor" workflow where lightweight, free, or local models (e.g., OpenCode free tier) can execute lower-tier tasks, automatically flagging output for higher-level review if critical boundaries are touched.
- **Token & Cost Optimization:** Preserve high-reasoning frontier models (e.g., top-tier Claude, Opus, Astra) for architectural decisions, complex algorithm design, and core state machines.
- **Graceful Fallback & Safety:** Maintain execution continuity if frontier credentials or rate limits are reached, falling back safely without exposing paid keys or interrupting worker loops.

---

## 2. Dynamic Complexity Heuristics

Rather than matching hardcoded task lists, the agent calculates a composite **Complexity & Risk Score ($C_{task}$)** based on three core pillars:

1. **Surface Area & Scope Depth:**
   - Number of target files and lines affected.
   - Position in dependency tree (e.g., core system runtime vs. isolated peripheral utility/test).
2. **Semantic Reasoning Depth:**
   - Presence of algorithmic design patterns, multi-file state management, concurrent routines, or complex math.
   - Nature of instruction (e.g., greenfield feature architecture vs. localized lint/formatting fix).
3. **Architectural Sensitivity:**
   - Direct modification of factory ledgers, execution engines, or safety invariants.

### Tier Routing Matrix

| Tier | Complexity & Risk | Target Profile | Recommended Runner / Model | Audit Policy |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1 (Frontier)** | High ($C_{task} \ge 0.7$) | Algorithmic state machines, GTO solvers, system architecture, core refactoring. | Top-tier Claude / Opus / Astra / High-end gateway | Direct execution; trusted output. |
| **Tier 2 (Worker)** | Standard / Low ($C_{task} < 0.7$) | Isolated functions, test creation, boilerplate adjustments, documentation, linting. | Free / Local / OpenCode (`opencode/*-free`) | Conditional audit trigger. |

---

## 3. Generator-Verifier Review Pipeline

When a Tier 2 worker handles a task that intersects high-risk or architectural components:

1. **Manifest Stamping:** The run evidence manifest is automatically tagged with:
   ```json
   {
     "review_required": true,
     "complexity_score": 0.68,
     "review_reason": "Tier 2 worker modified core ledger integration module."
   }
   ```
2. **Asynchronous Verification Pass:** A queued Tier 1 process reviews the generated diff against system invariants before final merge or downstream dispatch.

---

## 4. Additional Future Enhancements

- **Autonomous Benchmark Suite:** Continuous self-evaluating integration tests measuring task execution speed and token efficiency per model tier.
- **Multi-Agent Consensus Routing:** For critical architectural refactors, dispatch the prompt simultaneously to two independent frontier models and require consensus on structural proposals.
- **Distributed Attempt Workflows:** Parallelizing sub-tasks across multiple worker panes with automatic output aggregation by the factory.