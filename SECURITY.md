# Security policy

Agent-Canary 0.1.x is an early release, not independently security-audited software.

Commands may execute local code. Use trusted inputs unless a separately reviewed
OS/container boundary is in place. Temporary directories, checksums, minimal
environments and timeouts are not security sandboxes. Read the guide before use.

Reports can contain source text, paths, command arguments and program output.
Inspect them before sharing. Secret detection is best effort, never a guarantee.

Use GitHub private vulnerability reporting when enabled, or ask the maintainer for
a private channel without disclosing exploit details in a public issue. This source
release does not automatically change GitHub's security or account settings.
Security fixes target the latest 0.1.x source release.
