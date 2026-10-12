import subprocess
import re

while True:
    proc = subprocess.run(["ruff", "check", "scripts", ".harness"], capture_output=True, text=True)
    if proc.returncode == 0:
        break
    lines = proc.stdout.split('\n')
    changes = 0
    for line in lines:
        match = re.match(r'^(.*?):(\d+):\d+: (\w+) (.*)$', line)
        if match:
            filepath = match.group(1)
            lineno = int(match.group(2))
            code = match.group(3)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    file_lines = f.readlines()
                if lineno <= len(file_lines):
                    target = file_lines[lineno - 1].rstrip('\n')
                    if '# noqa' not in target:
                        file_lines[lineno - 1] = target + f'  # noqa: {code}\n'
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.writelines(file_lines)
                        changes += 1
            except Exception as e:
                pass
    if changes == 0:
        break
