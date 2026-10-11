# CLAUDE.md — claude-plugins

Public Claude Code marketplace for ProofBound (`/plugin marketplace add Proofbound/claude-plugins`). Pure catalog: no build, no tests.

## Rules that the tree does not tell you

- `plugins/proofbound/skills/` is GENERATED. Never edit it here; edit the skill in the private `proofbound-monorepo` and run its `scripts/sync-public-plugins.sh`. That script's `PUBLIC_SKILLS` decides what ships.
- Only skills whose real work runs on the ProofBound server belong here. A skill that works locally (e.g. book-index) is given away once its source is public — keep it out.
- Every `source` is absolute (`git-subdir` for our own plugin, `github` for the others), never `./...`: proofbound.com/workshop/marketplace.json is this same file proxied by the worker-router, and a URL-added marketplace cannot resolve relative paths.
- Other entries point at their own public repos; this repo only lists them. `conference-booth-report` has no plugin.json (SKILL.md at its repo root), so its entry is `strict: false` with `skills: ["./"]` and the version lives here.
- Bump `version` in `plugins/proofbound/.claude-plugin/plugin.json` on every sync, or installed users won't see the update.
- Validate before pushing: `claude plugin validate .`
