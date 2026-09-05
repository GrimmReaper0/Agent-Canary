import os
from pathlib import Path
import sys
prompt=Path(os.environ['CANARY_PROMPT_FILE']).read_text()
if 'health endpoint' in prompt: Path('health.py').write_text('def health():\n    return {"status": "ok"}\n')
elif 'nested instructions' in prompt:
    instructions=Path('package/AGENTS.md').read_text(); Path('package/result.txt').write_text('pnpm' if 'pnpm' in instructions else 'npm')
elif 'update greeting' in prompt: Path('greeting.txt').write_text('hello from canary\n')
if '--broken' in sys.argv: Path('package-lock.json').write_text('unexpected mutation\n')
