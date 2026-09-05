# Contributing to Agent-Canary

A small reproducible improvement is more useful than a large unverified claim.

## Development

Use Python 3.11+ on Linux or macOS, preferably in a virtual environment:

```sh
python -m pip install -e .
python -m unittest discover -s tests -v
python scripts/smoke.py
```

The bundled tests require no paid service or API key. Keep tests offline and add
both success and failure cases. Explain the user problem, the change, and the
commands you actually tested. Update the guide when public behavior changes.
Clearly label synthetic fixtures and simulated adapters.

Never turn missing dependencies, skipped work or timeouts into passing results.
Changes to subprocesses, path validation, archives or sandbox policies require
explicit security analysis. Temporary directories are not security sandboxes.
Do not contribute credentials, private source or unsanitized execution reports.

Report formats are early-release interfaces. Bump the schema when the meaning of
an existing field changes. Contributions are licensed under this repository's MIT
license. Be kind, specific and respectful when reviewing other people's work.
