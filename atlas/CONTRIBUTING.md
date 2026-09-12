# Contributing to Atlas Sanctum

Atlas is built with an ecosystem, not around a closed institution.

## What We Need

Code is one contribution. Others are equally valuable:

- Ideas, datasets, field observations
- Research papers, protocols, design proposals
- Lab experiments, field notes, hard questions

## Getting Started

```bash
cd atlas/
pip install -r requirements.txt

# Run a local node
python -m atlas.node.node --name my-node --role edge --location "Your City"
```

## Code Standards

- Python 3.12+, typed with dataclasses and type hints
- Minimal dependencies — earn every import
- No PII in code, tests, or commits
- All policy-sensitive logic goes through `core/policy/engine.py`

## Submitting Changes

1. Fork and branch from `main`
2. Keep changes focused — one concern per PR
3. Protocol changes require a proposal in `community/proposals/` first
4. All contributions are licensed under the project license

## Field Labs

If you are running Atlas in the real world, document it in `community/field-notes/`.
Real-world observations are among the most valuable contributions.
