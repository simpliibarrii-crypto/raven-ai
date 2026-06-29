# Contributing

Thanks for helping improve the Raven ecosystem.

## Before opening a pull request

1. Open or reference an issue for substantial changes.
2. Keep changes focused and reviewable.
3. Add tests or explain why tests are not applicable.
4. Update documentation when behavior changes.
5. Consider security, privacy, and reproducibility impact.

## Development workflow

```bash
git checkout -b feature/short-description
# make changes
pytest -q || true
npm test --if-present || true
cargo test || true
```

Use the relevant commands for the repository stack.

## Standards

- Be explicit about assumptions.
- Keep clinical and biological claims bounded and evidence-linked.
- Avoid hidden telemetry, hardcoded credentials, and unreviewed network calls.
- Prefer small, composable modules over large opaque abstractions.
