---
doc_kind: routing_map
canonical_id: by-task
topics: [routing, tasks, shortcuts, entrypoints]
generator: manual
---

# Routing by task (entry-point shortcuts)

Fast-path task-to-entrypoint mapping for common operational patterns. Match this table for 1-hop intent resolution, then load the target area's `AGENTS.md` strictly JIT.

When work requires mutating the repository, run worktree isolation (`python scripts/routing/spawn_worktree.py check --areas <csv> --json` -> `add`) before dispatching the specialist.

## Task dispatch matrix

| Task / Intent | Entry area | Default agent | Primary skill | Key verification / scripts |
| --- | --- | --- | --- | --- |
| **DCF valuation & WACC modeling** | `scripts/financial/` | [`financial-modeling-analyst`](../ai-tooling/agents/financial-modeling-analyst/AGENT.md) | [`dcf-valuation-model`](../ai-tooling/skills/financial/dcf-valuation-model/SKILL.md) | `python scripts/financial/dcf_calculator.py --fixture <path>` |
| **Comparable company benchmarking (comps)** | `scripts/financial/` | [`financial-modeling-analyst`](../ai-tooling/agents/financial-modeling-analyst/AGENT.md) | [`comps-financial-benchmark`](../ai-tooling/skills/financial/comps-financial-benchmark/SKILL.md) | `python scripts/financial/comps_calculator.py --fixture <path>` |
| **LBO capital structure & debt schedule** | `ai-tooling/skills/financial/` | [`financial-modeling-analyst`](../ai-tooling/agents/financial-modeling-analyst/AGENT.md) | [`lbo-debt-schedule`](../ai-tooling/skills/financial/lbo-debt-schedule/SKILL.md) | `python scripts/ai-tooling/validate_skill.py --skill lbo-debt-schedule --dry-run` |
| **Portfolio mean-variance optimization** | `scripts/financial/` | [`portfolio-strategy-operator`](../ai-tooling/agents/portfolio-strategy-operator/AGENT.md) | [`portfolio-optimization`](../ai-tooling/skills/financial/portfolio-optimization/SKILL.md) | `python scripts/financial/portfolio_optimizer.py --fixture <path>` |
| **Tax-loss harvesting & wash-sale audit** | `scripts/financial/` | [`portfolio-strategy-operator`](../ai-tooling/agents/portfolio-strategy-operator/AGENT.md) | [`tax-loss-harvesting`](../ai-tooling/skills/financial/tax-loss-harvesting/SKILL.md) | `python scripts/financial/wash_sale_detector.py --fixture <path>` |
| **Portfolio rebalancing & drift ledger** | `ai-tooling/skills/financial/` | [`portfolio-strategy-operator`](../ai-tooling/agents/portfolio-strategy-operator/AGENT.md) | [`rebalancing-drift-ledger`](../ai-tooling/skills/financial/rebalancing-drift-ledger/SKILL.md) | `python scripts/ai-tooling/validate_skill.py --skill rebalancing-drift-ledger --dry-run` |
| **Value-at-Risk (VaR) & CVaR simulation** | `scripts/financial/` | [`risk-stress-tester`](../ai-tooling/agents/risk-stress-tester/AGENT.md) | [`risk-stress-simulation`](../ai-tooling/skills/financial/risk-stress-simulation/SKILL.md) | `python scripts/financial/monte_carlo_var.py --fixture <path>` |
| **Macroeconomic scenario stress shocks** | `ai-tooling/skills/financial/` | [`risk-stress-tester`](../ai-tooling/agents/risk-stress-tester/AGENT.md) | [`macro-scenario-shocker`](../ai-tooling/skills/financial/macro-scenario-shocker/SKILL.md) | `python scripts/ai-tooling/validate_skill.py --skill macro-scenario-shocker --dry-run` |
| **SEC EDGAR companyfacts GAAP ingest** | `scripts/financial/` | [`sec-compliance-curator`](../ai-tooling/agents/sec-compliance-curator/AGENT.md) | [`sec-edgar-extract`](../ai-tooling/skills/financial/sec-edgar-extract/SKILL.md) | `python scripts/financial/edgar_ingest.py --fixture <path>` |
| **Form ADV Part 1 & 2A/2B compliance audit** | `ai-tooling/skills/financial/` | [`sec-compliance-curator`](../ai-tooling/agents/sec-compliance-curator/AGENT.md) | [`form-adv-compliance`](../ai-tooling/skills/financial/form-adv-compliance/SKILL.md) | `python scripts/ai-tooling/validate_skill.py --skill form-adv-compliance --dry-run` |
| **Adversarial audit & code review** | `scratch/` | [`detailed-activity`](../ai-tooling/agents/detailed-activity/AGENT.md) | [`antagonistic-review`](../ai-tooling/skills/meta/antagonistic-review/SKILL.md) | `python scripts/docs/validate_structure_fast.py --all` |
| **CWE / ATT&CK code-review report** | `results/reports/code-review/` | [`artifact-agent`](../ai-tooling/agents/artifact-agent/AGENT.md) | [`code-review-report`](../ai-tooling/skills/reporting/code-review-report/SKILL.md) | `python scripts/results/build_document.py` |
| **Author / revise standards or docs** | `docs/standards/` | [`documentation-ops`](../ai-tooling/agents/documentation-ops/AGENT.md) | [`doc-builder`](../ai-tooling/skills/meta/doc-builder/SKILL.md) | `python scripts/docs/validate_router_structure.py` |
| **Markdown lint & format cleanup** | `docs/`, `references/` | [`documentation-ops`](../ai-tooling/agents/documentation-ops/AGENT.md) | [`markdownlint`](../ai-tooling/skills/meta/markdownlint/SKILL.md) | `python scripts/docs/run_markdownlint.py` |
| **Deep research & empirical inquiry** | `research/`, `results/research/` | [`detailed-activity`](../ai-tooling/agents/detailed-activity/AGENT.md) | [`deep-research`](../ai-tooling/skills/meta/deep-research/SKILL.md) | Primary source verification against `references/valid-sources/` |
| **Fast git inspection & local branch sync** | Local checkout | [`git-fast-operator`](../ai-tooling/agents/git-fast-operator/AGENT.md) | [`git-basics`](../ai-tooling/skills/git/git-basics/SKILL.md) | `git status`, `git diff` |
| **GitHub PRs, issues, and remotes** | Remote repository | [`github-ops`](../ai-tooling/agents/github-ops/AGENT.md) | [`github-workflow`](../ai-tooling/skills/git/github-workflow/SKILL.md) | `gh auth status`, `gh pr status` |
| **Worktree isolation (mutate)** | `scratch/worktrees/` | [`router`](../ai-tooling/agents/router/AGENT.md) *(in-parent)* | [`isolate-work`](../ai-tooling/skills/meta/isolate-work/SKILL.md) | `python scripts/routing/spawn_worktree.py check --areas <csv> --json` |
| **Cost layers & context dry runs** | `supporting/`, `results/cost-layers/` | [`router-maintenance`](../ai-tooling/agents/router-maintenance/AGENT.md) | [`cost-layer-dry-run`](../ai-tooling/skills/cost-layers/cost-layer-dry-run/SKILL.md) | `python scripts/cost-layers/validate_cost_layers.py --dry-run` |
| **qmd search & collection health** | `supporting/qmd/` | [`qmd-ops`](../ai-tooling/agents/qmd-ops/AGENT.md) | [`qmd-usage`](../ai-tooling/skills/meta/qmd-usage/SKILL.md) | `python scripts/qmd/validate_qmd_retrieval.py` |
| **ast-grep structural fact extraction** | Codebase symbols | [`router-maintenance`](../ai-tooling/agents/router-maintenance/AGENT.md) | [`ast-grep`](../ai-tooling/skills/cost-layers/ast-grep/SKILL.md) | `python scripts/cost-layers/validate_ast_grep.py` |
| **Author / dry-run new skills** | `ai-tooling/skills/` | [`ai-tooling-ops`](../ai-tooling/agents/ai-tooling-ops/AGENT.md) | [`skill-builder`](../ai-tooling/skills/meta/skill-builder/SKILL.md) | `python scripts/ai-tooling/validate_skill.py` |
| **Author / revise agent definitions** | `ai-tooling/agents/` | [`ai-tooling-ops`](../ai-tooling/agents/ai-tooling-ops/AGENT.md) | [`agent-builder`](../ai-tooling/skills/meta/agent-builder/SKILL.md) | `python scripts/ai-tooling/validate_agent.py` |
| **Scratch & worktree hygiene** | `scratch/` | [`router-maintenance`](../ai-tooling/agents/router-maintenance/AGENT.md) | [`scratch-cleanup`](../ai-tooling/skills/meta/scratch-cleanup/SKILL.md) | `python scripts/routing/spawn_worktree.py list --json` |

---

## Related

- Full skill catalog: [`skill-dispatch.md`](./skill-dispatch.md)
- Specialist agent catalog: [`agent-dispatch.md`](./agent-dispatch.md)
- Area map: [`area-map.md`](./area-map.md)
- Worktree isolation: [`../ai-tooling/skills/isolate-work/SKILL.md`](../ai-tooling/skills/meta/isolate-work/SKILL.md)
