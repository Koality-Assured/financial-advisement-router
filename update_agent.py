from pathlib import Path
path = Path("ai-tooling/agents/router/AGENT.md")
content = path.read_text(encoding="utf-8")
content = content.replace("- as-code-agent\n", "")
content = content.replace("- repo-sync-ops\n", "")
path.write_text(content, encoding="utf-8")
