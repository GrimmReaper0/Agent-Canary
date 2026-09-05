# Agent Canary

**Know which agent behaviors changed, with evidence.**

![Agent Canary: Know which agent behaviors changed, with evidence.](assets/banner.svg)

[![CI](https://github.com/GrimmReaper0/Agent-Canary/actions/workflows/ci.yml/badge.svg)](https://github.com/GrimmReaper0/Agent-Canary/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)
[![MIT license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Agent Canary is an executable compatibility harness for command-line coding
agents. Give it a repository fixture, a prompt and concrete file assertions. It
runs your adapter, captures changes and compares passing trials across versions.

**Not a model intelligence leaderboard.** Each result describes one fixture and
observed run, not general reliability or safety. The included adapter is a
**deterministic demo**, not Claude, Codex or another vendor. No vendor benchmark
results are fabricated in this repository.

## Install from source

Requires **Python 3.11+ on Linux or macOS**. No third-party Python runtime
dependencies. This is a source release, not an advertised PyPI publication.

```sh
git clone https://github.com/GrimmReaper0/Agent-Canary.git
cd Agent-Canary
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
agent-canary --help
```

## Run a working demo

```sh
agent-canary run cases --trust --label demo --agent-version good \
  --repeat 3 --json artifacts/good.json --html artifacts/good.html \
  --command python "$(pwd)/examples/demo_agent.py"
```

Three fixtures run three times. Open `artifacts/good.html` for the nine passing demo
trials. Introduce an intentional lockfile mutation:

```sh
agent-canary run cases --trust --label demo --agent-version broken \
  --repeat 3 --json artifacts/broken.json \
  --command python "$(pwd)/examples/demo_agent.py" --broken
agent-canary compare artifacts/good.json artifacts/broken.json
```

The broken run and comparison intentionally exit **1**. `preserve-lockfile` loses
three passing trials. This tests the harness against a deliberately broken demo;
it is not a claim about any vendor.

## Write a behavior test

```text
cases/my-case/
  case.json
  fixture/
    package-lock.json
```

```json
{
  "id": "preserve-lockfile",
  "prompt": "Add health.py without changing package-lock.json.",
  "checks": [
    {"type": "exists", "path": "health.py"},
    {"type": "unchanged", "path": "package-lock.json"}
  ]
}
```

Assertions support `exists`, `absent`, `contains`, `changed` and `unchanged`.
Fixtures, prompts and assertions are fingerprinted. Changed tests or different
trial counts are **not comparable**, rather than incorrectly labelled regressions.
JSON evidence includes actual output, file hashes and bounded unified diffs.

## Connect your agent

`--command` consumes the remaining arguments and must be last. The adapter receives
the prompt on stdin plus `CANARY_WORKSPACE` and `CANARY_PROMPT_FILE`. Whole-argument
placeholders `{workspace}`, `{prompt_file}` and `{prompt}` also work. Write a small
wrapper around your installed agent CLI and record its real version and model
using `--agent-version` and `--model`.

Credentials are not inherited by default. Use `--pass-env NAME` before `--command`
for required variables. User HOME is replaced, so saved CLI credentials are not
copied automatically. Your adapter may require an account and paid API calls.
There are no unverified vendor-specific CLI flags hidden in this harness.

## Safety and interpretation

`--trust` authorizes host execution. Temporary workspaces are **not a sandbox**.
Use a separately managed container or disposable machine for untrusted agents.
Inspect output and patches for secrets before sharing.

| Exit | Meaning |
| --- | --- |
| 0 | All assertions passed, or comparison found no regression. |
| 1 | A trial failed, or fewer comparable trials passed. |
| 2 | Invalid setup, or incomparable reports without a detected regression. |

Missing tools and timeouts cannot pass. Agent/model labels are supplied by the
caller, not authenticated identities. Keep operating system, configuration and
other conditions constant when comparing versions. Small trial counts are
observations, not statistically conclusive performance estimates.

## How it works

![Agent Canary workflow](assets/workflow.svg)

## Development and support

```sh
python -m unittest discover -s tests -v
python scripts/smoke.py
```

See the [usage guide](docs/guide.md), [verification record](docs/testing.md),
[contribution guide](CONTRIBUTING.md), [security policy](SECURITY.md) and
[release notes](CHANGELOG.md). Report bugs with a small, sanitized reproduction.

Prepared GitHub descriptions, topics and social-preview instructions are in
[repository setup](docs/repository-setup.md). Licensed under [MIT](LICENSE).
