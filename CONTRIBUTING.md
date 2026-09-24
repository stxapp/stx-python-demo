# Contributing

Thanks for taking the time to improve this demo. These are reference examples for the STX Python SDK (`stx-python`, documented at [docs.stxapp.io/sdks/python](https://docs.stxapp.io/sdks/python/)). The goal is clear, minimal, working scripts that a newcomer can clone and run.

## Where to file things

- **A script does not work**: open an [issue](https://github.com/stxapp/stx-python-demo/issues/new/choose). The bug form asks for the details that matter.
- **A new example or an improvement**: also an issue, using the "Feature request / example request" template.
- **A question about the SDK itself** (rather than these demos): start with [the docs](https://docs.stxapp.io/sdks/python/quickstart). Bugs in the SDK belong with the SDK, not here.

## Filing a good issue

- One problem per issue.
- Include the exact command you ran and the exact output you got. Copy and paste beats paraphrasing.
- Mention your OS, `python3 --version`, and the `stx-python` version you are on (`pip show stx-python`).
- If you already know the root cause, say so, but do not wait until you do to file.

## Pull requests

Happy to take them. Before you start a large change, open an issue first so we can agree on scope.

Before opening a PR:

```bash
# Lint and make sure every script parses. This is what CI runs.
pip install ruff
ruff check .
python3 -m py_compile *.py

# If your change affects an example, run it once against the demo environment:
export STX_EMAIL=... STX_PASSWORD=...
python3 quickstart.py   # or whichever file you changed
```

Keep diffs small and focused. One concern per PR makes review cheap. Build the client through `demo_config.make_client()` (or `make_async_client()` / `make_ws()`) rather than constructing `STX(...)` directly, so the configuration story stays consistent across scripts.

## What not to submit

- Breaking changes to the shape of these examples without prior agreement. They are public reference material and stability matters.
- Examples that need unreleased or private SDK versions. Everything here must work against the latest published `stx-python`.
- Credentials, tokens, or any real account data, in code or in example configs.

## Code of conduct

Be kind. Assume the person on the other end is trying to do good work. Reviews are a conversation, not a gate.
