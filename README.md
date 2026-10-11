# ProofBound plugins for Claude Code

```
/plugin marketplace add Proofbound/claude-plugins
/plugin install proofbound@proofbound
```

Or, equivalently: `/plugin marketplace add https://proofbound.com/workshop/marketplace.json`

| Plugin | What it does |
|---|---|
| `proofbound` | Write a book in conversation with Claude, then publish it to your ProofBound library. ProofBound renders the PDF and stores the book. Needs a [ProofBound](https://proofbound.com) account; sign-in is a browser device flow. |
| `book-research` | Build a book's source dossier: scholarly search, BibTeX, filed materials. ([source](https://github.com/Proofbound/book-research-skill)) |
| `conference-booth-report` | Turn trade-show booth photos into an emailable HTML report. ([source](https://github.com/Proofbound/conference-booth-report)) |
| `photo-essay` | Turn a folder of photos into an HTML photo essay. ([source](https://github.com/Proofbound/photo-essay-skill)) |

Install any of them with `/plugin install <name>@proofbound`. Update with `/plugin marketplace update proofbound`.
