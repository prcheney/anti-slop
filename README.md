# anti-slop

Claude Code skills for taking AI-written copy off a website, landing page or any other text. Two skills ship here:

- **`anti-slop`**: the full pre-launch workflow for a site. It runs seven stages in order: a regex copy gate, a Jev second opinion, a humanize pass, a sentence audit, a claims list, a headline pass and a visual review.
- **`humanize`**: a 35-item checklist for removing AI writing patterns from any text (general, academic or essay mode). `anti-slop` calls it in stage 2; it also works on its own for emails, posts and docs.

Every rule in it came from a real correction on a real site. The principles table in `SKILL.md` records each correction: the line that was rejected, the line that was approved, and the check that now catches it.

## Install

As a Claude Code plugin:

```
/plugin marketplace add prcheney/anti-slop
/plugin install anti-slop@anti-slop
```

Or copy `skills/anti-slop/` and `skills/humanize/` into `~/.claude/skills/`.

Then ask Claude to "anti-slop the site" from inside a website repo, or to "humanize this" on any text.

## What runs where

| Stage | Tool | Needs |
|---|---|---|
| 1. Copy gate | `scripts/check_copy.py` | Python 3, nothing else |
| 1b. Second opinion | `scripts/check_copy_jev.py` | A TypeSafe API key in the GNOME keyring, labelled `typesafe-api-key`. Optional: the stage never blocks |
| 2. Humanize | `skills/humanize` | Nothing, it ships in this repo |
| 3. Sentence audit | `scripts/sentence_audit.py` | The site running locally |
| 4-5. Claims, headlines | Claude and you | Nothing |
| 6. Impeccable | `npx impeccable detect` | Node |
| 7. Visual review | Your own screenshot review | Nothing |

`check_copy.py` works on its own as well:

```
python3 skills/anti-slop/scripts/check_copy.py src/app/page.tsx content/*.ts
```

Exit 0 means it passed. It reads `.md` as prose and pulls only the visible copy out of `.tsx`, `.jsx`, `.ts` and `.html`.

`check_copy_jev.py` sends copy to Jev (TypeSafe), so skip it on copy that quotes patients or private messages.

## Updates

This repo is published from a private working copy and updated whenever the skill changes. Issues are welcome. Pull requests may be applied by hand, since the source lives elsewhere.

## License

MIT
