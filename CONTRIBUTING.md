# Contributing

Thanks for taking the time to improve this demo. These are reference examples for the [stx-python SDK](https://pypi.org/project/stx-python/); the goal is clear, minimal, *working* snippets that a newcomer can clone and run.

## Where to file things

- **Bug report / example doesn't work** → open an [Issue](https://github.com/stxapp/stx-python-demo/issues/new/choose). The form walks you through the details that matter.
- **New example request / improvement** → also an Issue, using the "Feature request / example request" template.
- **Question about the SDK itself** (as opposed to these demos) → start with [the docs](https://docs.stxapp.io/sdks/python/quickstart). For bugs in the SDK (not this demo), file against the SDK package, not here.

## Filing a good issue

- One problem per issue.
- Include the exact command you ran + the exact output you got. Copy-paste beats paraphrasing.
- Mention your OS, `python3 --version`, and the `stx-python` version you're on (`pip show stx-python`).
- If you already know the root cause, say so — but don't wait until you do to file.

## Pull requests

Happy to take them. Before you start a large change, open an issue first so we can discuss scope.

Before opening a PR:

```bash
# Make sure every .py file at least parses.
python3 -m py_compile *.py

# If your change affects an example, run it against staging once:
export STX_EMAIL=... STX_PASSWORD=...
python3 quickstart.py   # or whichever file you changed
```

Keep diffs small and focused. One concern per PR makes review cheap.

## What *not* to submit

- Breaking changes to the shape of these examples without prior agreement (they're public reference; stability matters).
- Examples that require unreleased or private SDK versions — everything here must work against the latest published `stx-python` on PyPI.
- Credentials, tokens, or any real account data in example configs.

## Code of conduct

Be kind. Assume the person on the other end is trying to do good work. Reviews are a conversation, not a gate.
