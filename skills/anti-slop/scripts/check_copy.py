#!/usr/bin/env python3
"""Anti-slop copy checker. Enforces documented copy rules mechanically.
Usage: check_copy.py <file> [file...]      Exit 0 = pass, 1 = failures found.

Handles .md/.txt as prose; .tsx/.jsx/.ts/.js/.html are reduced to visible copy first.

"""
import re,sys,os

FAIL,WARN=[],[]
def fail(f,ln,rule,txt): FAIL.append((f,ln,rule,txt.strip()[:100]))
def warn(f,ln,rule,txt): WARN.append((f,ln,rule,txt.strip()[:100]))

EMOJI=re.compile("["
  "\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\U00002190-\U000021FF"
  "\U00002B00-\U00002BFF\U0000FE0F]",flags=re.UNICODE)

# unambiguous tics -> FAIL
HARD=[
 (r"[—–]",                                        "em-dash / en-dash"),
 (r"\b(?:it|that|this)\s*(?:is|'s|’s)\s+not\s+(?:just\s+)?\w[^.!?]{0,60}?,\s*(?:it|that)\s*(?:is|'s|’s)",
                                                  "antithesis flip (it's not X, it's Y)"),
 # Any subject, any pronoun: "a roofer who is a week late is not costing you a week of
 # roofing, they are costing you..." passed the it/that/this version (2026-10-07).
 (r"\b(?:is|are|was|were)\s+not\s+[^.!?]{0,80}?,\s*(?:they|it|we|you|he|she|that)\s*(?:are|is|were|was|'re|'s|’re|’s)\b",
                                                  "antithesis flip (X is not A, it is B)"),
 (r"\bisn['’]?t\s+just\b[^.!?]{0,60}?,?\s*it['’]?s\b",  "antithesis flip (isn't just X, it's Y)"),
 (r"\bnot\s+only\b[^.!?]{0,60}?\bbut\s+also\b",   "not only X but also Y"),
 (r"\bhere'?s\s+the\s+thing\b",                   "filler transition"),
 (r"\bthat\s+said\b",                             "filler transition"),
 (r"\bit'?s\s+worth\s+noting\b",                  "filler transition"),
 (r"\bin\s+today'?s\s+(?:fast[- ]paced\s+)?world\b","stock opener"),
 (r"\b(?:let'?s\s+dive\s+in|dive\s+deep(?:er)?\s+into)\b","stock phrase"),
 (r"\bNo\s+\w+\.\s*No\s+\w+\.\s*No\s+\w+\.",      "triad negation (No X. No Y. No Z.)"),
 (r"\bNot\s+\w+,\s*not\s+\w+,\s*(?:and\s+)?not\s+\w+",  "triad negation (Not X, not Y, not Z)"),
# "seamless" is an inflated abstraction in "seamless experience" and a PRODUCT
# CATEGORY in "seamless gutters" and "seamless aluminum", which is the trade name
# for gutter formed on site in one continuous run. It is also what homeowners
# search: 1,600/mo on "seamless gutters cost" at KD 1, measured 2026-09-13. The
# lookahead lets those two noun phrases through and nothing else, so the rule
# still catches every marketing use. The separator class covers the URL slug
# "seamless-aluminum" as well as the prose, which is what a route file holds.
# Added for the Acme Roofing gutter pages.
 (r"\b(?:unlock|unleash|elevate|revolutioniz|game[- ]chang|cutting[- ]edge|seamless(?:ly)?(?![\s-]+(?:aluminum|gutter))|robust|leverage\s+the\s+power)\w*",
                                                  "inflated abstraction"),
# Stand-in words: a pro-form doing the job of the plain noun or verb. "I'll say so"
# for "I'll tell you", "see yours" for "see your price", "ours comes in lower" for
# "our price comes in lower". Same family as synonym cycling: the writer dodges
# repeating a word, and the sentence gets clipped and clever instead of plain.
# the reviewer caught three rounds of it in the Acme estimator copy, 2026-09-25.
# Fix: name the thing again.
 (r"\b(?:say|do)\s+so\b",                         "stand-in word (say so / do so): say the plain thing"),
 (r"\b(?:yours|ours|theirs)\b",                   "stand-in word (yours/ours/theirs): name the noun"),
# Contrast framing: the copy defines the client by an imaginary worse roofer instead
# of stating what the customer gets. "An Acme Roofing crew, not a subcontractor", "one person
# rather than a dispatch number". The reviewer called the whole Acme Roofing guarantees section slop
# for this, 2026-09-29. Fix: state the fact on its own.
# Widened 2026-10-07 from "X, not a/the Y" to any word after "not": "clauses, not
# conversation", "more, not less", "data-backed decisions, not guesswork" all slipped
# through the article-only version. "not only" stays with its own rule.
 (r"\b\w+,\s+not\s+(?!only\b)\w+",                    "contrast framing (X, not Y): state the fact on its own"),
 (r"\brather\s+than\b",                          "contrast framing (rather than): state the fact on its own"),
 (r"\binstead\s+of\s+(?:a|an|the)\b",             "contrast framing (instead of a Y): state the fact on its own"),
# Trade jargon a homeowner does not know. "A square" is 100 sq ft of roof to a
# roofer and nothing to the buyer (the reviewer, 2026-09-29). "square feet" still passes.
 (r"\b(?:per|a|each|by\s+the)[\s-]+square\b(?![\s-]+f(?:oo|ee)t)|\bsquares\s+of\s+(?:roof|shingle)", "trade jargon (a square): say the price for the whole roof or per square foot"),
]

# Softer stand-ins -> WARN. "it" after an action verb is often fine, and often a
# dodge ("If a repair will fix it", "You'll see it on the next screen"). Read each.
SOFT=[
 (r"\bMost\s+\w+(?:\s+\w+)?\s+(?:are|is|do|don['’]?t)\b",
                                                  "strawman comparison (Most X are...): say what the client does instead"),
# Honesty signaling: copy that keeps announcing it is honest reads as a pitch. The reviewer's
# humanizer pass on Acme Roofing cut 16 of these, 2026-10-07. WARN, because "both can be honest"
# about a quote is a plain use.
 (r"\b(?:honest(?:ly)?|straight\s+(?:answer|account|talk|description|recommendation)|stated\s+plainly)\b",
                                                  "honesty signaling: state the fact, the reader decides if it is honest"),
 (r"\b(?:see|fix|get|check|find|handle|compare|send)\s+it\b",
                                                  "stand-in word (verb + it): would the noun read better?"),
# Redundant modifier: the word it modifies already says it. The reviewer on "Six of Acme Roofing's 44 Google
# reviews, quoted word for word", 2026-11-14: "a redundant modifier, we should already have a
# rule for this". A quote is word for word; a gift is free.
 (r"\bquoted\s+(?:word\s+for\s+word|verbatim|in\s+full|whole|exactly)\b|\b(?:reviews?|quotes?)\b[^.]{0,40}\bword\s+for\s+word\b",
                                                  "redundant modifier: a quote is already word for word; cut the modifier"),
 (r"\b(?:each\s+and\s+every|any\s+and\s+all|first\s+and\s+foremost|end\s+result|final\s+outcome|past\s+(?:history|experience)|"
  r"free\s+gift|added\s+bonus|advance\s+(?:planning|notice|warning)|close\s+proximity|exact\s+same|completely\s+(?:free|finished|full)|"
  r"absolutely\s+(?:essential|free)|still\s+remains?|basic\s+fundamentals|new\s+innovations?|plan\s+ahead|join\s+together|"
  r"repeat\s+again|revert\s+back|true\s+facts?|unexpected\s+surprise|personal\s+opinion|completely\s+eliminate)\b",
                                                  "redundant modifier: one of the two words already says it; cut the other"),
]

def visible_copy(text,path):
    """For code files, strip tags/attrs/imports and keep visible prose."""
    if os.path.splitext(path)[1].lower() not in (".tsx",".jsx",".ts",".js",".html"): return text
    # blank out comments FIRST, preserving line numbering: {/* .. */}, /* .. */, <!-- .. -->
    def blank(m): return re.sub(r"[^\n]"," ",m.group(0))
    for pat in (r"\{\s*/\*.*?\*/\s*\}", r"/\*.*?\*/", r"<!--.*?-->"):
        text=re.sub(pat,blank,text,flags=re.S)
    text=re.sub(r"//[^\n]*",blank,text)
    out=[]
    for i,line in enumerate(text.split("\n"),1):
        l=line
        if re.match(r"\s*(import|export\s+(default\s+)?(function|const)|//|/\*|\*)",l):
            out.append((i,"")); continue
        l=re.sub(r"\b[\w-]+=\{[^}]*\}","",l)          # jsx expression attrs
        l=re.sub(r"\b[\w-]+=\"[^\"]*\"","",l)           # string attrs (className, href...)
        l=re.sub(r"\b[\w-]+='[^']*'","",l)
        l=re.sub(r"<[^>]*>"," ",l)                       # tags
        l=re.sub(r"[{}]"," ",l)
        l=re.sub(r"\s+"," ",l).strip()
        # keep only things that read like prose: 2+ alphabetic words
        out.append((i,l if len(re.findall(r"[A-Za-z]{2,}",l))>=2 else ""))
    return out

def sentences(s): return [x for x in re.split(r"(?<=[.!?])\s+",s) if x.strip()]

# Slogan headlines. The reviewer rejected three on the Acme estimator (2026-09-25) and every one
# passed the phrase rules: "A Price That Holds After the Old Roof Comes Off", "A Roofer Who Spent
# 11 Years on the Homeowner's Side", "The Same Roof Without the Advertising Bill", over a hero of
# "Get the Same Roof". The replacements that passed his read state the offer or the fact:
# "Decking Priced in Writing Before We Start", "Priced by a Former Public Adjuster".
HEAD_HARD=[
 (r"^(?:get\s+)?it\b",                                  "stand-in headline (It.../Get it...): name the thing"),
 (r"^(?:get\s+)?(?:a|an|the)\b.*\b(?:that|who|which)\b", "slogan headline (A X That/Who Y): state the offer or the fact"),
# Same slogan with a count in place of the article: "Get five guarantees that are..." (2026-10-07).
 (r"^(?:get\s+)?(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b.*\b(?:that|who|which)\b", "slogan headline (Five X That Y): state the offer or the fact"),
 (r"\bwithout\s+the\b",                                  "slogan headline (X Without the Y): say what they get"),
]
HEAD_SOFT=[
 (r"\bthe\s+same\b",                                     "vague headline (\"the same\" what?)"),
]

# Assumed familiarity. The writer knows what "your number" is, so the headline calls the page's
# central deliverable by a vague label and the reader has to guess. A property manager's booking page
# opened with "Talk through your number with Sam" (2026-10-21) and meant the rent
# estimate. Applies only to headings, buttons and CTA strings; "the numbers" in body copy is
# fine. Fix: use the name the client's own page uses (rental report, estimate, price).
FAMILIAR=[
 (r"(?<!by )\b(?:your|the|our)\s+(?:number|numbers|figure|figures|answer|answers|result|results|plan|situation|details|options|goals|needs|process)\b",
  "assumed familiarity: name the thing (rent estimate, quote, price) instead of a vague label"),
]

# Abstract actor or object. "Get a price ... before anyone visits" (Acme Roofing home hero): the reviewer, 2026-11-14,
# "too cloudy, not specific enough". The fix named who and what: "online without a sales
# appointment". An indefinite pronoun in a headline or button stands where the reader needs a
# person or a thing. WARN, headings and CTA strings only; body copy uses these words normally.
ABSTRACT=[
 (r"\b(?:anyone|anybody|someone|somebody|everyone|everybody|anything|something|everything)\b",
  "abstract headline: name who or what (a salesperson, an inspector, the written quote) instead of an indefinite word"),
 # "Your price first and the rest in writing": the reviewer, 2026-11-14, "in writing where?" Name the document.
 (r"\b(?:in|on)\s+(?:writing|paper)\b|\bthe\s+rest\b",
  "abstract headline: \"in writing\" where? Name the document (the proposal you sign, the itemized quote)"),
 # Clipped stand-in noun: "get a ballpark", "see a number first". The reviewer, 2026-11-14: "you're using
 # ballpark as a noun". Say the whole thing: a ballpark estimate, a price range.
 (r"\ba\s+number\b|\bballpark\b(?!\s+(?:estimate|figure|range|price|quote)s?\b)",
  "clipped noun: say the whole thing (a ballpark estimate, a price range), not \"a ballpark\" or \"a number\""),
]

# Meta copy: a subhead that describes or introduces what sits directly below it instead of saying
# something. The reviewer, 2026-11-14, on "Each page covers what the material costs, how long it lasts and
# which houses it suits": "this part is slop"; and on a reviews subhead: "just show the reviews".
# Checked on lead/subhead strings only. Link-card bodies describe another page and are exempt.
META=[
 (r"\b(?:each|every|this|the)\s+(?:page|section|guide|article)s?\s+(?:below\s+)?(?:covers?|explains?|shows?|describes?|walks?|goes\s+through|lays?\s+out)\b"
  r"|\bstart\s+wherever\b|\b(?:below|here)\s+(?:you(?:'ll| will)\s+find|is\s+(?:what|how|everything))\b",
  "meta copy: this describes the page instead of saying something; cut the subhead or state the fact"),
]

def lead_strings(raw,path):
    """(line, text) for lead/subhead/intro strings in code."""
    out=[]
    if os.path.splitext(path)[1].lower() in (".ts",".js",".tsx",".jsx"):
        for ln,line in enumerate(raw.split("\n"),1):
            for m in re.finditer(r"\b(?:lead|sub(?:head\w*|title)?|intro|kicker)\s*:\s*(?:\"([^\"]+)\"|'([^']+)'|`([^`]+)`)",line,re.I):
                out.append((ln,next(g for g in m.groups() if g).strip()))
    return out

def cta_strings(raw,path):
    """(line, text) for button text and cta/label/button strings in code."""
    out=[]
    ext=os.path.splitext(path)[1].lower()
    if ext in (".tsx",".jsx",".html"):
        for m in re.finditer(r"<button\b[^>]*>(.*?)</button>",raw,re.S|re.I):
            t=re.sub(r"<[^>]*>|\{[^}]*\}"," ",m.group(1)); t=re.sub(r"\s+"," ",t).strip()
            if len(re.findall(r"[A-Za-z]{2,}",t))>=2: out.append((raw[:m.start()].count("\n")+1,t))
    if ext in (".ts",".js",".tsx",".jsx"):
        for ln,line in enumerate(raw.split("\n"),1):
            for m in re.finditer(r"\b(?:cta\w*|button\w*|label)\s*:\s*(?:\"([^\"]+)\"|'([^']+)'|`([^`]+)`)",line,re.I):
                out.append((ln,next(g for g in m.groups() if g).strip()))
    return out

def headings(raw,path):
    """(line, text) for every heading: markdown #, JSX <h1-3>, and heading/headline/title strings in code."""
    out=[]
    ext=os.path.splitext(path)[1].lower()
    for ln,line in enumerate(raw.split("\n"),1):
        if ext in (".md",".txt") and re.match(r"^#{1,3} ",line):
            out.append((ln,re.sub(r"^#+\s*","",line).strip()))
        if ext in (".ts",".js",".tsx",".jsx"):
            for m in re.finditer(r"\b(?:heading|headline\w*|title)\s*:\s*(?:\"([^\"]+)\"|'([^']+)'|`([^`]+)`)",line,re.I):
                out.append((ln,next(g for g in m.groups() if g).strip()))
    if ext in (".tsx",".jsx",".html"):
        for m in re.finditer(r"<h[1-3]\b[^>]*>(.*?)</h[1-3]>",raw,re.S|re.I):
            t=re.sub(r"<[^>]*>|\{[^}]*\}"," ",m.group(1)); t=re.sub(r"\s+"," ",t).strip()
            if len(re.findall(r"[A-Za-z]{2,}",t))>=2: out.append((raw[:m.start()].count("\n")+1,t))
    return out

def check(path):
    try: raw=open(path,encoding="utf-8",errors="ignore").read()
    except FileNotFoundError: print(f"ERROR: not found - {path}"); return False
    # strip markdown frontmatter and fenced code
    body=re.sub(r"\A---\n.*?\n---\n","",raw,flags=re.S)
    body=re.sub(r"```.*?```","",body,flags=re.S)
    body=re.sub(r"`[^`\n]+`","",body)

    numbered=visible_copy(body,path)
    lines=numbered if isinstance(numbered,list) else list(enumerate(body.split("\n"),1))

    for ln,line in lines:
        if not line.strip(): continue
        for pat,rule in HARD:
            seen=set()
            for m in re.finditer(pat,line,re.I):
                g=m.group(0).lower()
                if g in seen: continue
                seen.add(g); fail(path,ln,rule,m.group(0))
        for pat,rule in SOFT:
            for m in re.finditer(pat,line,re.I): warn(path,ln,rule,m.group(0))
        if EMOJI.search(line): fail(path,ln,"emoji",EMOJI.search(line).group(0))

        # staccato: 3+ consecutive sentences under 6 words
        run=0
        for s in sentences(line):
            run = run+1 if len(s.split())<=5 else 0
            if run>=3: warn(path,ln,"staccato run (3+ short sentences)",line); break

    # markdown headings
    for ln,line in list(enumerate(body.split("\n"),1)):
        if re.match(r"^#{1,3} ",line):
            h=re.sub(r"^#+\s*","",line)
            if len(h)>65: warn(path,ln,f"headline too long ({len(h)} chars, wraps)",h)

    # slogan headlines, and every heading built on one template
    heads=headings(body,path)
    raw_lines=body.split("\n")
    for ln,h in heads:
        for pat,rule in HEAD_HARD:
            if re.search(pat,h,re.I): fail(path,ln,rule,h)
        for pat,rule in HEAD_SOFT:
            if re.search(pat,h,re.I): warn(path,ln,rule,h)
    for ln,h in heads+cta_strings(body,path):
        for pat,rule in FAMILIAR+ABSTRACT:
            m=re.search(pat,h,re.I)
            if m: warn(path,ln,rule,h)
    for ln,h in lead_strings(body,path):
        for pat,rule in META:
            if re.search(pat,h,re.I): warn(path,ln,rule,h)
    # Section headings only. List-item titles SHOULD share one structure (the reviewer,
    # 2026-09-29: "there's no parallel structure for each of the guarantees").
    heads_sec=[(ln,h) for ln,h in heads if not re.search(r"\btitle\s*:\s*[\"'`]"+re.escape(h),raw_lines[ln-1] if ln-1<len(raw_lines) else "")]
    starts=[re.match(r"(?:get\s+)?(a|an|the)\b",h,re.I) for _,h in heads_sec]
    np_heads=[heads_sec[i] for i,m in enumerate(starts) if m]
    if len(heads_sec)>=3 and len(np_heads)>=3:
        warn(path,np_heads[2][0],f"{len(np_heads)} headings share one template (A/The + noun phrase)",
             " | ".join(h for _,h in np_heads[:3]))

    # tricolon budget: max one per file
    tri=[(ln,l) for ln,l in list(enumerate(body.split("\n"),1))
         if re.search(r"\b\w+,\s+\w+,\s+and\s+\w+\b",l)]
    for ln,l in tri[1:]: warn(path,ln,f"tricolon #{tri.index((ln,l))+1} (max 1 per page)",l)
    return True

# Guarded so check_copy_jev.py can import visible_copy and headings.
if __name__=="__main__":
    if len(sys.argv)<2: print(__doc__); sys.exit(2)
    for p in sys.argv[1:]: check(p)

    for f,ln,rule,txt in FAIL: print(f"FAIL {os.path.basename(f)}:{ln}  {rule}\n       {txt}")
    for f,ln,rule,txt in WARN: print(f"WARN {os.path.basename(f)}:{ln}  {rule}\n       {txt}")
    print(f"\n{len(FAIL)} FAIL, {len(WARN)} WARN")
    sys.exit(1 if FAIL else 0)
