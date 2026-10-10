# 📖 ProofBound Book Builder

Write a complete, professionally formatted book just by talking to Claude.

The Book Builder is a Claude skill. You describe the book you want — or hand over
your notes — and Claude interviews you, drafts the table of contents, and writes
the chapters, introduction, and summary right there in the conversation. When
you're happy, one command sends it to ProofBound, which lays it out, renders a
print-ready PDF, gives it a starter cover, and drops the finished book into your
library. No design tools, no LaTeX, no formatting headaches.

> **Using the ProofBound MCP connector?** If you've connected `mcp.proofbound.com`
> in Claude (the primary, no-install path), let it drive — its `get_book_workflow`
> is the canonical, always-current workflow. This skill is the standalone Claude
> Code / power-user path for when the connector isn't available.

---

## What you get

- A real book: title page, copyright page, table of contents, chapters,
  introduction, summary, and ProofBound colophon — all laid out for you.
- A print-ready **PDF**, available instantly at a `files.proofbound.com` link.
- A simple **placeholder cover** generated automatically — your title, subtitle,
  and name on a clean background — so the book looks finished in your dashboard
  right away. Swap in a designed cover whenever you like.
- The book saved to your **ProofBound dashboard**, ready for a designed cover and
  print-on-demand.
- The editable source, if you ever want it.

You stay the author. Claude is your co-writer and your typesetter.

---

## What you need

1. **Claude** — Claude Desktop or Claude Code, with the Book Builder skill
   installed.
2. **A ProofBound account** — free to create at [proofbound.com](https://proofbound.com).
   Publishing your book requires being signed in.
3. **A few minutes of setup** (below). After that, you mostly just chat.

You do **not** need to install Quarto, LaTeX, TinyTeX, or any publishing
software. ProofBound does all of the rendering on its servers.

---

## One-time setup

There's almost nothing to do. You need [`uv`](https://docs.astral.sh/uv/)
installed (it fetches everything else automatically). Then sign in **in your
browser** — no password to type:

```bash
uv run scripts/publish_book.py login
```

This opens a ProofBound sign-in page (and prints a link + short code). Sign in,
click **Approve**, and you're connected. Your login is saved securely at
`~/.proofbound/credentials.json` and refreshes itself, so you only do this once.

In most cases you don't run anything by hand — just tell Claude _"let's write a
book"_ and it walks you through signing in and does the rest.

---

## How to use it

Start a conversation with Claude and say something like:

> _"Help me write a book about backyard beekeeping for beginners."_
>
> _"Turn these notes into a book."_ (then attach or paste your material)

Claude walks you through six short phases. You're in control at every step —
review, tweak, regenerate, or keep going.

| Phase          | What happens                                                                  | Your part                              |
| -------------- | ----------------------------------------------------------------------------- | -------------------------------------- |
| **1. Intake**  | Claude asks about your topic, audience, and goals; reads any notes you share. | Answer a few questions.                |
| **2. Design**  | Sets the title, subtitle, author, style, and page size.                       | Confirm or adjust.                     |
| **3. Outline** | Drafts a chapter-by-chapter table of contents.                                | Reorder, rename, add, or cut chapters. |
| **4. Writing** | Writes each chapter, the introduction, and the summary.                       | Review previews; ask for rewrites.     |
| **5. Publish** | Sends everything to ProofBound to be laid out and rendered.                   | Confirm, then get your PDF link.       |
| **6. Revise**  | Rewrite anything and re-publish.                                              | Point out what to change.              |

Everything Claude drafts is saved to a folder on your computer (by default under
`~/Books/`) as you go, so a closed laptop or dropped connection never loses your
work — just come back and say _"let's continue my book."_

### Page sizes

Two trim sizes are supported: **6×9 inches** (standard trade paperback) and
**A5**. Claude will ask, or you can say which you prefer.

### Adding an author bio and photo

Optional, but nice on the back cover. Just tell Claude your bio (up to ~500
characters) and point it at a photo (JPEG or PNG, up to 5 MB). It gets included
automatically.

---

## Who writes the book — and what it costs

The Book Builder has two ways to generate the prose. **Neither one bills you
through ProofBound** for the writing.

- **Conversation mode (default, recommended).** Claude writes the book directly
  in your chat, using your existing Claude subscription. There's nothing extra to
  set up and no per-word charge — the Claude you're already talking to is the
  author. **This is what happens unless you ask otherwise.**

- **Batch mode (advanced).** If you'd rather generate many chapters
  unattended in one go, you can run a script that writes them using your own
  Anthropic API key (billed per word to you). This is opt-in and only for power
  users who want hands-off generation.

To switch to batch mode you explicitly run the generator script; to switch back,
just resume writing in the conversation. Most people never need batch mode.

> ProofBound only charges for what its platform does — laying out and rendering
> your book, storing it, and (optionally) covers and printing. The writing itself
> runs on your Claude.

---

## After your book is published

When publishing finishes, Claude shows you:

- a **`book_id`** (your book's reference),
- a **PDF link** on `files.proofbound.com`,
- and the book waiting in your **ProofBound dashboard**.

From there you can:

- **Download the editable source** — the full layout project, if you want to keep
  a copy or hand-edit it.
- **Replace the placeholder cover** — your book already has a simple auto-generated
  cover, so nothing looks unfinished. Design a proper one anytime from your
  ProofBound dashboard, or hand the `book_id` to the ProofBound Cover Generator.
- **Order prints** — send it on to print-on-demand once you're happy with the cover.

> **One book at a time.** ProofBound renders one of your books at a time. If you
> publish again while a render is still running, you'll be asked to wait a moment
> and retry.

---

## Revising a book

Revision is simple by design: **edit, then re-publish.**

1. Tell Claude what to change — _"rewrite chapter 3 to be more concise"_ or
   _"make the introduction warmer."_
2. Claude updates the local files.
3. Re-publish. You get a freshly rendered book reflecting the changes.

There's no fiddly per-chapter patching — your local book folder is the master
copy, and re-publishing rebuilds the whole thing cleanly.

---

## Frequently asked

**Do I need to know Markdown, LaTeX, or Quarto?**
No. You write in plain conversation; ProofBound handles all formatting.

**Where are my files kept?**
Your in-progress book lives in a local folder (default `~/Books/<your-book>/`).
Your login lives at `~/.proofbound/credentials.json`. The published book lives in
your ProofBound library.

**Can I resume a book later?**
Yes. Just open Claude and say _"continue my book"_ — it finds in-progress books
and picks up where you left off.

**Is my book private?**
It's saved to your own ProofBound account and library, tied to your login.

**The login expired / I get an "authentication" error.**
Run `uv run scripts/publish_book.py login` again.

**I want to start over.**
Tell Claude to start a fresh book, or delete the local book folder.

---

## A note on the commands

You rarely need to type anything beyond the one-time `login`. Claude runs the
publishing steps for you during the conversation. If you ever want to do it by
hand, the helper lives at `scripts/publish_book.py` and supports `login`,
`login-wait` (resume a sign-in that got interrupted), `logout`, `fetch-prompts`,
`publish`, `status`, and `download-src`.

---

Made with ProofBound. Happy writing. ✍️
