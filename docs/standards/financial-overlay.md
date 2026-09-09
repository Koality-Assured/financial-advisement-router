---
doc_kind: requirement
canonical_id: financial-overlay
purpose: [requirement]
rank: medium
topics: [financial, overlay]
rag_keywords: [financial, domain-overlay, spoke]
---

# financial domain overlay

This spoke is a `financial` harness scaffolded from `ai-harness-core`. Feed financial corpus here. Keep generic machinery in the core.

Do not copy this overlay, instance `projects/`, `research/`, or `ai-tooling/memory/` back to the generic core.

Pull core updates: `python scripts/sync/pull_harness_core.py --dry-run --json`.

Propose generic core changes: `python scripts/sync/propose_core_update.py --dry-run --json`.
