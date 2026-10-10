# Skills

> [!IMPORTANT]
> **Human-Facing Documentation Only**: This README is maintained strictly for human developers and repository visitors. Autonomous AI agents MUST NOT ingest or utilize `README.md` files for operational instructions or context. All agent directives and navigation reside strictly in [`AGENTS.md`](./AGENTS.md) and [`routing/`](../../routing/).

Human overview: router skills live organized into domain families under `<family>/<name>/SKILL.md`.

**Agents do not use this README as a catalog.** They load [`../../routing/skill-dispatch.md`](../../routing/skill-dispatch.md) (regenerate with `python scripts/routing/generate_skill_dispatch.py`) and spawn `owner_agent`. Template: [`../../ai-tooling/skills/skill-conventions.md`](skill-conventions.md). Validate: `python scripts/ai-tooling/validate_skill.py --all`.

Human index (not agent SoT):

| Skill | Owner | Isolation |
| --- | --- | --- |
| [`agent-cost-estimator/`](./benchmarks/agent-cost-estimator/) | benchmark-agent | mutate |
| [`agent-fleet-benchmark/`](./benchmarks/agent-fleet-benchmark/) | benchmark-agent | mutate |
| [`retrieval-benchmark/`](./benchmarks/retrieval-benchmark/) | benchmark-agent | mutate |
| [`task-eval-benchmark/`](./benchmarks/task-eval-benchmark/) | benchmark-agent | mutate |
| [`tool-efficiency-benchmark/`](./benchmarks/tool-efficiency-benchmark/) | benchmark-agent | mutate |
| [`ast-grep/`](./cost-layers/ast-grep/) | harness-operator | read-only |
| [`cost-layer-dry-run/`](./cost-layers/cost-layer-dry-run/) | harness-operator | mutate |
| [`headroom/`](./cost-layers/headroom/) | harness-operator | read-only |
| [`comps-financial-benchmark/`](./financial/comps-financial-benchmark/) | financial-modeling-analyst | mutate |
| [`dcf-valuation-model/`](./financial/dcf-valuation-model/) | financial-modeling-analyst | mutate |
| [`form-adv-compliance/`](./financial/form-adv-compliance/) | sec-compliance-curator | mutate |
| [`lbo-debt-schedule/`](./financial/lbo-debt-schedule/) | financial-modeling-analyst | mutate |
| [`macro-scenario-shocker/`](./financial/macro-scenario-shocker/) | risk-stress-tester | mutate |
| [`portfolio-optimization/`](./financial/portfolio-optimization/) | portfolio-strategy-operator | mutate |
| [`rebalancing-drift-ledger/`](./financial/rebalancing-drift-ledger/) | portfolio-strategy-operator | mutate |
| [`risk-stress-simulation/`](./financial/risk-stress-simulation/) | risk-stress-tester | mutate |
| [`sec-edgar-extract/`](./financial/sec-edgar-extract/) | sec-compliance-curator | mutate |
| [`tax-loss-harvesting/`](./financial/tax-loss-harvesting/) | portfolio-strategy-operator | mutate |
| [`git-basics/`](./git/git-basics/) | git-fast-operator | mutate |
| [`github-paths/`](./git/github-paths/) | github-ops | read-only |
| [`github-workflow/`](./git/github-workflow/) | github-ops | mutate |
| [`harness-review/`](./harness-review/) | harness-operator | mutate |
| [`memory-adjust/`](./memory/memory-adjust/) | harness-operator | mutate |
| [`memory-cleanup/`](./memory/memory-cleanup/) | harness-operator | mutate |
| [`memory-create/`](./memory/memory-create/) | harness-operator | mutate |
| [`agent-builder/`](./meta/agent-builder/) | harness-operator | mutate |
| [`antagonistic-review/`](./meta/antagonistic-review/) | detailed-activity | read-only |
| [`deep-research/`](./meta/deep-research/) | research-operator | mutate |
| [`doc-builder/`](./meta/doc-builder/) | document-operator | mutate |
| [`isolate-work/`](./meta/isolate-work/) | router | mutate |
| [`markdownlint/`](./meta/markdownlint/) | document-operator | mutate |
| [`qmd-efficiency/`](./meta/qmd-efficiency/) | harness-operator | mutate |
| [`qmd-usage/`](./meta/qmd-usage/) | harness-operator | read-only |
| [`readme-maintain/`](./meta/readme-maintain/) | document-operator | mutate |
| [`reference-maintain/`](./meta/reference-maintain/) | document-operator | mutate |
| [`router-structure/`](./meta/router-structure/) | document-operator | read-only |
| [`scratch-cleanup/`](./meta/scratch-cleanup/) | harness-operator | mutate |
| [`script-builder/`](./meta/script-builder/) | harness-operator | mutate |
| [`skill-builder/`](./meta/skill-builder/) | harness-operator | mutate |
| [`skill-dry-run/`](./meta/skill-dry-run/) | harness-operator | read-only |
| [`model-memory-operate/`](./model-memory-operate/) | harness-operator | mutate |
| [`anti-slop/`](./reporting/anti-slop/) | document-operator | mutate |
| [`architecture-diagram/`](./reporting/architecture-diagram/) | document-operator | mutate |
| [`code-review-report/`](./reporting/code-review-report/) | artifact-agent | mutate |
| [`corpus-draft/`](./reporting/corpus-draft/) | document-operator | mutate |
| [`executive-report/`](./reporting/executive-report/) | document-operator | mutate |
| [`guidance-draft/`](./reporting/guidance-draft/) | document-operator | mutate |
| [`humanizer/`](./reporting/humanizer/) | document-operator | mutate |
| [`mermaid-diagram/`](./reporting/mermaid-diagram/) | document-operator | mutate |
| [`proposal-report/`](./reporting/proposal-report/) | document-operator | mutate |
| [`local-webfetch/`](./research/local-webfetch/) | research-operator | read-only |
