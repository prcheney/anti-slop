---
name: anti-slop
description: The anti-slop workflow for a website or landing page. Copy gate script, a decision-model second opinion, humanizer pass, sentence audit (dramatic commas, stranded pronouns), claims list, headline rule with a value proposition map, Impeccable, then a human visual review, in that order. Use when asked to "anti-slop the site", "de-AI this", "it looks generated", before any site or page launches, and after a large batch of AI-written copy.
argument-hint: "<repo path>"
---

# Anti-slop

Slop is anything a reader can tell a machine made: phrasing, structure, invented facts, templated
layout. Scripts catch the mechanical part, Claude catches the patterns scripts miss, and the reviewer
judges the rest on the review sheet. 

Run the stages in order. One commit per content file, so the reviewer can revert any one. Report each stage
in a line before starting the next.

**Before stage 1, mark the copy pass** so the Stop hook does not demand a review sheet after every
one-line fix (it did on Acme Roofing, 2026-11-14):

```bash
touch ~/.cache/quality-gate/copy-pass-<repo folder name>
```

Touch it again at the start of each later session of the same pass; it stops counting after six
hours. Remove it at stage 7, before the shoot. Never start a shoot while the reviewer is answering copy
fixes.

## 1. Copy gate (script, every visible file)

```bash
python3 scripts/check_copy.py <every content and page file>
```

Content often lives in `.ts` data files (`content/*.ts`), not just `.tsx`. Run it on all of them.
Fix every FAIL by stating the fact plainly. Never invent a claim, number or process step to fill a
sentence. Read every WARN; fix the honesty-signaling and strawman ones. Exit 0 before stage 2.

## 1b. Second opinion (script, flag-only, every content file)

After the gate exits 0, ask the decision model the judgment questions a regex cannot: templated,
no proof, contrast framing, choppy, vague reference, slogan headline, abstract wording.

```bash
python3 scripts/check_copy_jev.py <every content and page file>
```

- **Medical sites, and any copy that quotes a patient, a lead or a private message: add `--local`.**
  That runs Kev on this machine and nothing leaves it. The default sends the text to hosted Jev
  (TypeSafe). `--local` borrows the graphics card for the run (`kev_switch.py`); it refuses while
  OpenWhispr is recording, so wait for a dictation or meeting to finish.
- The flags are a reading list for stages 2, 3 and 5, not a verdict. Never fix a line on a flag
  alone and never rewrite to make a number go down. Read the flagged line; fix it only if it
  breaks a rule in this skill.
- Read 0.90 and up first. `choppy` is the noisiest question (85 of 319 Acme Roofing paragraphs the reviewer had
  already approved, 2026-11-14), so a `choppy` flag alone on a stat card or a spec line is
  usually nothing.
- Hosted Jev is the stronger reader: on the same 469 lines it flagged 144, Kev flagged 32, and
  they agreed 72% of the time. A clean `--local` run means less than a clean hosted run. Say
  which one ran when reporting the stage.
- Exit 2 means it could not run (no key, API down, card busy). Say so in the stage report and go
  on; this stage never blocks.

## 2. Humanizer pass (Claude, long-form only)

Extract the visible prose (articles, guides, anything over about 150 words) and run the `humanizer`
skill in detect mode on it. Fix only clusters, not lone tells: honesty signaling, "nobody tells you"
framing, aphorism closers, "would rather X than Y", overclaims. Targeted edits, no voice injection.
Any new pattern worth catching every time goes into `check_copy.py` the same session, tested first
against the client repos for false positives.

## 3. Sentence audit: dramatic commas and stranded pronouns (Claude, every page)

Built from the clinic audit, 2026-11-02 (28 fixes the reviewer approved one by one). The copy gate
catches "X, not Y"; it does not catch these. List every candidate with:

```bash
python3 scripts/sentence_audit.py http://localhost:<port> --repo <repo>
```

Read both lists by hand and fix:

- **Dramatic comma**: a comma used for a pause or a reveal instead of grammar. "See Dr. Lee, at
  every visit". "Twenty four years as a physician, most of it in acute care". "Here is what changes,
  and why". "which of these you need, and in what order". "Then, and only then, the rest". Headings
  and table-of-contents labels count. Fix: one plain sentence, no pause ("See Dr. Lee at every
  visit"). List commas and clause commas are fine.
- **Verbless fragment strings**: "A small practice, enough time in the room, and a plan that goes
  after the cause." "Hormonal balance, read across time." Give it a subject and a verb.
- **Stranded pronoun**: It / This / That / These opening a sentence, a paragraph or an article when
  the noun it stands for is not in the sentence before. Also a pronoun in a subhead that points at
  nothing on screen ("before you pay for it"). Fix: say the noun.
- **Stand-in nouns**: "the number", "the testing", "the appointment", "the model", "this field",
  "the gap", "the second one". The writer knows what they mean; a stranger does not. Name the thing
  ("your test results", "a standard annual physical", "longevity medicine").

While rewriting, these got rejected on the clinic site and will be again:

- Overstating a fact to make the line shorter ("in emergency and intensive care" when twelve of
  the twenty four years were primary care). Check the client's own record before compressing.
- Social proof nobody can back ("plenty of members do" at a practice that opened this year).
- Promises that box the client in later: "we keep the practice small", "membership stays capped".
- Process steps nobody confirmed: "in writing", "once diet, sleep and exercise are in place",
  "you find out on the discovery call" (the testing decides, not the call).
- Two sections that describe the same steps. When a page has a process list and a "what happens
  next" list, one of them covers only the call and the other covers treatment.

Present fixes to the reviewer one at a time: the line now, why it fails in one sentence, the fix, "Use it,
or rewrite?" Never a batch.

## 4. Claims list (Claude, then the client)

Log every fact the site states about the client that nobody has confirmed: prices, crews, warranty
terms, process steps, counts, ratings. Group into yes/no questions in
`Clients/<Client>/website-claims-to-confirm-<date>.md`. Unsourced statistics get cut or sourced by
us; the rest go to the client. The reviewer sends; never email it.

## 5. Headline rule (Claude, then a headline pass with the reviewer)

Every headline implies "Get" (overt about 1 in 10, on heroes with a hard offer and final CTAs),
answers where am I / what can I do / why, and leads with what the reader gains. Short. No repeated
generic heads.

**The headline test (the reviewer, 2026-11-15). Run it on every headline before showing it to the reviewer.** Read
the headline as the page's ideal prospect and answer: why should I keep reading here instead of
going somewhere else? The headline has to imply three answers: where am I, what can I do here, and
why should I do it. The why has to be a strong reason for that prospect, the thing they came
wanting or the thing they are afraid of. A true but weak why fails ("for your insurance claim").
Name the ideal prospect in one line first (who, what just happened to them, what they want to
know), then write. When recommending a headline to the reviewer, state the three answers under it.
The ideal prospect is the likely visitor, and most traffic is exploratory: they arrive cold. Never
write for a prospect who has already had an experience the page cannot assume (a door knocker's
offer, a quote in hand, a denied claim). If the headline only makes sense after that experience,
put the situation in the headline (the reviewer, Acme Roofing deductible notice: "not enough context unless you
think the ideal prospect has already received a quote from a door knocker").
The why is what the prospect wants from the product, never how the company is organized. "The same
crew that does your roof" is a fact about Acme Roofing; a gutter buyer wants gutters. Before using any
company fact as the why, ask whether the prospect could read it as a negative (a roofer doing
gutters reads as a roofer working outside what it is good at). The reviewer, Acme Roofing gutters hero: "people
want new gutters. they don't care that it's from the same company that does the roof." Count the
words too: he called an eleven-word headline "too wordy". Aim for nine or fewer.

### The value proposition map (the reviewer, 2026-11-15)

A hero's reason is graded from the customer's side with three questions, in this order:

1. **Do I want this?** Appeal. It has to be something many of the page's visitors want.
2. **Can I get it anywhere else?** Exclusivity. If every competitor does it or says it, it is
   table stakes and a very weak reason. "Commercial roofing that starts with a condition report"
   failed here: "everyone starts with a condition report".
3. **Do I believe it?** Credibility. A fact, a number, a name or a document has to stand behind it.

A value proposition balances mass appeal against exclusivity: the widest want that the client can
still claim alone and prove. Write the three answers down for every hero before showing it to
the reviewer. If the client has nothing exclusive on a page, say that to the reviewer and ask; do not dress a
table-stakes fact as the reason.

### Empathy step (the reviewer, 2026-11-15): two tiers, so it stays cheap

Headlines kept missing because the reason in them came from the page's own copy, which is the
client describing itself. The fix is not a research run per headline.

1. **Jev sorts the heroes.** `check_copy_jev.py <content files> --headings` asks `weak_why` of
   every page hero (a `title:` with a `lead:` under it, or an h1) and flags at 0.50. It catches
   labels, slogans and company facts. On 20 Acme Roofing headlines the reviewer had judged it got 16 right. It
   misses a headline that sounds useful but gives a weak reason, which is what tier 2 is for. It
   does not run on card titles or section labels: a label is not supposed to sell.
2. **Heroes are written from a prospect card.** `Clients/<Client>/prospect-cards.md` holds one
   card per kind of visitor (not per page): what just happened, what they came to find out, what
   they want, what they fear, what reads as a negative. Every line cites the client's pain map
   (`voc-research`) or the reviewer's own words. Build the cards once from the pain map; no pain map, run
   `voc-research` first. When recommending a hero, name the card line the reason comes from.
   A card with no evidence says so, and a hero on that card goes to the reviewer as a question, never
   as an invented reason.

Section headings and signposts skip both tiers. They state the section's fact (principle 5).

Headline pass (the clinic site, 2026-11-02): walk the reviewer through every page's headline and subhead, one
pair per message, top of the page down: "Headline: ... Subhead: ... What's your rewrite?" He
answers keep, a rewrite, or "slop, recommend something". When recommending, give one option, not
a menu. Shared copy (a closing band, a section intro used on three pages) changes everywhere it
renders; say so once when applying it.

- Lead magnets and guides take the BuzzFeed template: a numeral plus a curiosity gap ("8 Questions
  Longevity Clinics Hope You Never Ask", "The 2 Numbers Researchers Link to Living Past 80"). The
  subhead keeps the gap open; naming the answer kills the click.
- Superlatives ("the best treatments available") draw state physician-advertising and Google Ads
  health-policy trouble on paid pages. Flag once when the reviewer writes one.

Abstract wording test (the reviewer, Acme Roofing home hero, 2026-11-14): "Get a price for your own roof in minutes,
before anyone visits" was "too cloudy, not specific enough". "Anyone" hid the person the reader
dreads and "visits" hid why. The approved line names both: "Get your roof's price range online
without a sales appointment". For every headline, subhead and button, ask who does what, where,
and with what; if a word could be swapped for "someone" or "something", name the person or the
thing. "In writing" failed the same way the same day ("in writing where?"): name the document, such as
the proposal the homeowner signs or the itemized quote. `check_copy.py` warns on indefinite words (anyone, somebody, everything), "in writing" and "the rest" in headings and
buttons, and the stage 1b model check scores `abstract` on every line. Fix each hit by hand.

### Principles mined from the reviewer's corrections

Every correction the reviewer makes in a pass is a rule, not a one-line fix. The moment he corrects a
line, before presenting the next one:

1. Name the principle in one sentence that would apply to another client's site.
2. Add it to this list with his words, the rejected line and the approved line.
3. If a script can see the failure, add a check to `check_copy.py` (regex) or `check_copy_jev.py`
   (model question) and run it on the client repos for false alarms.
4. Sweep the rest of the site for the same failure and fix or queue every hit.
5. Check your next recommendation against the whole list before showing it.

| # | Principle | The reviewer said | Rejected | Approved | Check |
|---|---|---|---|---|---|
| 1 | Name the actor and the thing. No indefinite words. | "too cloudy, not specific enough" | "before anyone visits" | "online without a sales appointment" | `check_copy.py` ABSTRACT; Jev `abstract` |
| 2 | Name the document. "In writing" is not a place. | "in writing where?" | "the rest in writing" | "in the proposal you sign" | `check_copy.py` ABSTRACT |
| 3 | Call a deliverable by its true precision. An estimate is not a price. | "I don't want to say it's the price" | "see the price first" | "get a ballpark estimate" | Per client; see the client's memory file |
| 4 | Do not clip a phrase into a stand-in noun. | "you're using ballpark as a noun" | "get a ballpark", "see a number" | "get a ballpark estimate" | `check_copy.py` ABSTRACT |
| 5 | A section heading states the section's fact, not an angle on it. | "why wouldn't we just say what our service area is here?" | "Local crews licensed on both sides of the state line" | "We roof northern Ohio and western Pennsylvania from Springfield" | By hand |
| 6 | Cut a modifier the word already contains. | "a redundant modifier" | "reviews, quoted word for word" | "reviews" | `check_copy.py` SOFT |
| 7 | No copy that introduces or describes what is directly below it. Show the thing. | "this isn't necessary. just show the reviews"; "this part is slop" | "Six of Acme Roofing's 44 Google reviews..."; "Each page covers what the material costs, how long it lasts and which houses it suits." | heading only, no subhead (section headings only: every page hero keeps a subhead, the reviewer 9/08 and again 11-15, so give the hero a fact instead) | `check_copy.py` META |
| 8 | Cite a number only when it impresses. A weak number is worse than none. | "44 isn't impressive" | "From 44 homeowner reviews" | "On Google reviews" | By hand, in stage 4 |
| 9 | Keep the qualifier on every mention. Shortening the name the second time drops the precision. | "ballpark estimate" (on a body line that said "the estimate") | "shows you the estimate online" | "shows you a ballpark estimate online" | By hand; grep the client's short form after each pass |
| 10 | Test every timing claim. Timing can be the benefit, but only when the reader can see what being earlier or faster gets them. If they have to work that out, state the gain. | "why would BEFORE be a value proposition?"; "timing can be a benefit. in this case it is not" | "Storm damage inspected before the adjuster arrives" | (see the storm damage hero) | By hand; grep headings for before / first / until and ask the question of each. "Before the deck gets wet" passes, "before the adjuster arrives" does not |

Assumed familiarity test: for every headline, button and opening line, ask whether a stranger who
just landed knows what each noun is. The writer knows what "your number" is; the reader does not.
Use the name the client's own page uses (rental report, estimate, price), never a label that
points at it. A property manager's booking page said "Talk through your number with Sam"
and meant the rent estimate. `check_copy.py` warns on the vague labels in headings and buttons;
the script cannot know the right name, so fix each hit by hand.

## 6. Impeccable (script, automatic)

Runs inside the visual review shoot at desktop and phone width on every template. Its findings
print on each template's card. To run it alone:

```bash
npx --yes impeccable detect --json <urls>
npx --yes impeccable detect --json --viewport 390x844 <urls>
```

Fix every finding except the two known false positives (`tight-leading`, a rounding bug, and
`body-text-viewport-edge` on swipe rows). A long H1 is fixed by tightening the copy or by the
smaller long-headline size, not by ignoring it.

## 7. Visual review (the reviewer)

First `rm -f ~/.cache/quality-gate/copy-pass-<repo folder name>`. Then run the `visual-review` skill: shoot, pre-pass notes, sheet. Tell the reviewer which template to start
with. His notes come back through Copy all notes; act on them, then shoot again.

## Never

- Never mark a stage passed on Claude's own read when a script exists for it.
- Never rewrite reviews, quotes, legal or contract text, or a headline the reviewer has tested in ads
  without asking.
- Never publish the review sheet or send the claims list.
- Never call the pass finished with the copy-pass marker still in place: stage 7 is the review the
  marker postponed.
