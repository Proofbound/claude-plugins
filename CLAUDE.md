# CLAUDE.md — claude-plugins

Public Claude Code marketplace for ProofBound (`/plugin marketplace add Proofbound/claude-plugins`). Pure catalog: no build, no tests.

## Rules that the tree does not tell you

- `plugins/proofbound/skills/` is GENERATED. Never edit it here; edit the skill in the private `proofbound-monorepo` and run its `scripts/sync-public-plugins.sh`. That script's `PUBLIC_SKILLS` decides what ships.
- Only skills whose real work runs on the ProofBound server belong here. A skill that works locally (e.g. book-index) is given away once its source is public — keep it out.
- Other entries point at their own public repos (`source: github`); this repo only lists them.
- Bump `version` in `plugins/proofbound/.claude-plugin/plugin.json` on every sync, or installed users won't see the update.
- Validate before pushing: `claude plugin validate .`
