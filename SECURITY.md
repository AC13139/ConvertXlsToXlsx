# Security Policy

## Supported Versions

| Version | Supported           |
|---------|---------------------|
| 0.1.x   | :white_check_mark: Yes |

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it
privately rather than opening a public issue.

- **How**: open a GitHub issue marked with the `security` label, or use
  GitHub's "Report a vulnerability" button on the repository page.
- **Response window**: we aim to acknowledge reports within 5 business days.

Please include:

- A description of the vulnerability and its impact.
- Steps to reproduce or a proof-of-concept.
- The affected version(s) and commit hash, if known.

We will coordinate disclosure and a fix before any public announcement.

## Scope

This is a file-conversion utility. The project processes untrusted document
content via a third-party converter (LibreOffice). The primary security
concerns we care about are:

- **Path traversal** in batch mode (the project mirrors directory trees under
  `--src-dir` and must not write outside `--dst-dir`).
- **Subprocess command injection** in converter backends (arguments must be
  passed as argv lists, never shell-joined strings).
- **Symlink following** during discovery (the project disables symlink follow
  by default for both reproducibility and safety).
- **Resource exhaustion** when converting huge directory trees (the project
  caps parallelism via `--workers`).

If you find a vulnerability in a third-party converter itself (LibreOffice),
please report it upstream rather than to this project.

## Threat Model Assumptions

- Input files may originate from untrusted sources.
- The host filesystem is otherwise trusted; we do not sandbox the converter
  subprocesses beyond what the host OS provides.
- The CLI is invoked by a single trusted user on a single trusted machine.
