#!/usr/bin/env python3
"""Second-layer copy check. Asks Jev (TypeSafe AI) the judgment questions a regex cannot.
Usage: check_copy_jev.py <file> [file...] [--all] [--threshold 0.75] [--local] [--headings]

FLAG-ONLY. check_copy.py stays the pass/fail gate. This script never fails a file on
Jev's say-so: exit 0 = ran (flags or not), 2 = could not run (no key, API down).
Jev answers with a probability, not text, so every flag shows its number. --all also
prints paragraphs that passed, which is how to tune the threshold.

Key: GNOME login keyring entry labelled `typesafe-api-key`. Never read from a file or env var.
Do not run the hosted mode on the clinic site copy that quotes patient data: the text leaves the machine.

--local asks Kev (open local version of Jev, ~/kev) on this machine instead: no key, nothing
leaves the machine, safe for patient data. It borrows the graphics card through
kev_switch.py (OpenWhispr's cleanup model is unloaded for the run and reloads on the
next dictation) and hands it back when done.
"""
import os,re,sys,time
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from check_copy import visible_copy, headings

API="https://api.typesafe.ai/v1/systemone"
LOCAL_API="http://127.0.0.1:8009/v1/systemone"
SWITCH=os.path.join(os.path.dirname(os.path.abspath(__file__)),"kev_switch.py")
KEY_LABEL="typesafe-api-key"
MIN_WORDS=8
HEAD_ONLY=False   # --headings: score headings only (the empathy pass)
# Per-question thresholds that differ from --threshold. The model scores abstract wording lower
# and closer together than the other questions: the rejected Acme Roofing hero scored 0.68, its approved
# replacement 0.23, a plain concrete headline 0.63 (2026-11-14).
Q_THRESHOLD={"abstract":0.65,"weak_why":0.5}

def noul(instr,true,false): return {"type":"noul","instructions":instr,"criteria":{"true":true,"false":false}}

# Each question is a rule from documented copy rules that check_copy.py can only
# approximate with patterns. Keys are what the report prints.
PARA_Q={
 "templated":       noul("Does this read like generic AI-written marketing copy?",
                         "Generic and templated; could be pasted onto any competitor's site",
                         "Specific to one business; plain, concrete, sounds like a person wrote it"),
 "no_proof":        noul("Does this make a claim with no fact, number, name or detail behind it?",
                         "Asserts a benefit or quality (quality, trusted, best, peace of mind) with nothing to back it",
                         "Every claim comes with a concrete fact, number, name or specific detail"),
 "contrast_framing":noul("Does this define the business by contrast with an imagined worse competitor?",
                         "Describes what the business is NOT, or what other companies do wrong, to make its point",
                         "States what the customer gets directly, without a foil"),
 "choppy":          noul("Is the rhythm choppy, with short punchy fragments instead of flowing sentences?",
                         "Several short fragments or one-line sentences stacked for effect",
                         "Flowing sentences of natural varied length"),
 "vague_reference": noul("Does this use vague stand-ins (it, that, this, yours, the same) where it should name the thing?",
                         "A pronoun or stand-in word replaces a noun the reader needs named",
                         "Things are named plainly"),
}
# Abstract language. The reviewer, 2026-11-14, on "Get a price for your own roof in minutes, before anyone
# visits": "too cloudy, not specific enough". The fix was "online without a sales appointment".
ABSTRACT=noul("Does this use abstract or cloudy wording where it should name the specific person, thing, place, amount or action?",
              "Says anyone, someone, things, solutions, peace of mind, the process or a similar general word; the reader cannot picture who does what",
              "Names the specific person, thing, place, amount or action, e.g. 'online without a sales appointment', 'an itemized written quote'")
PARA_Q["abstract"]=ABSTRACT
HEAD_Q={
 "slogan_headline": noul("Is this headline a clever slogan rather than a plain statement of the offer or a fact?",
                         "A slogan, wordplay, or 'A X That Y' / 'X Without the Y' construction",
                         "States the offer or a concrete fact plainly, e.g. 'Decking Priced in Writing Before We Start'"),
 "abstract": ABSTRACT,
 # the reviewer, 2026-11-15: a headline must give the ideal prospect a strong reason to keep reading.
 # Tested on 20 Acme Roofing headlines he rejected or approved: 16 right at 0.5. It catches labels,
 # slogans and company facts; it misses headlines that sound useful but give a weak reason,
 # so page heroes also get a prospect card (anti-slop stage 5).
 "weak_why": noul("Read this headline as a homeowner who just landed on a roofing company's page. Does it fail to give them a strong reason to keep reading, something they want or fear?",
                  "States timing, a description of the company, how the company is organized, or what every such product does; a buyer shrugs",
                  "Names something the buyer wants or is afraid of, e.g. finding out whether to file a claim, a price range with no sales appointment"),
}

LABEL_Q={k:v for k,v in HEAD_Q.items() if k!="weak_why"}

def is_hero(src,ln):
    """A page's main headline: a `title:` with a `lead:` right under it in a content file, or an h1.
    weak_why runs on these only. On card titles and section labels ("TPO", "Roof replacement") it
    flagged 328 of 389 Acme Roofing headings, which is noise: a label is not supposed to sell."""
    if not 0<ln<=len(src): return False
    line=src[ln-1]
    if re.match(r"\s*#\s",line) or "<h1" in line: return True
    return bool(re.match(r"\s{2,6}title:",line)) and "lead:" in " ".join(src[ln:ln+2])

def get_key():
    try:
        import gi; gi.require_version("Secret","1")
        from gi.repository import Secret
    except Exception as e: sys.exit(f"ERROR: libsecret bindings unavailable ({e})")
    svc=Secret.Service.get_sync(Secret.ServiceFlags.LOAD_COLLECTIONS,None)
    for col in svc.get_collections():
        for it in col.get_items():
            if it.get_label()==KEY_LABEL:
                it.load_secret_sync(None); return it.get_secret().get_text().strip()
    print(f"ERROR: no keyring entry labelled {KEY_LABEL}"); sys.exit(2)

def ask(sess,key,state,questions):
    for attempt in range(5):
        if key is None:
            r=sess.post(LOCAL_API,json={"state":state,"model":"kev-latest","questions":questions},timeout=120)
        else:
            r=sess.post(API,headers={"Authorization":f"Bearer {key}"},
                        json={"state":state,"model":"jev-latest","questions":questions},timeout=30)
        if r.status_code in (429,529): time.sleep(2**attempt); continue
        r.raise_for_status()
        return {k:v["noul"] for k,v in r.json()["answers"].items()}
    raise RuntimeError(f"Jev still rate-limited after 5 tries ({r.status_code})")

# Content files hold copy as object fields: title: "...", body: "...". Each string is
# its own unit. Gluing neighbors together read as choppy and flagged every stat card.
# Heading fields go to HEAD_Q instead; class lists and links are not copy.
SKIP_KEYS=r"(?:title|heading|headline\w*|class(?:Name)?|href|src|icon|id|slug|kind|alt)"
STR=re.compile(r"(?:\b(\w+)\s*[:=]\s*)?(\"(?:[^\"\\\n]|\\.)*\"|`[^`]*`|'(?:[^'\\\n]|\\.)*')")

def strings(body):
    # comments quote the reviewer and the pain map, which is not page copy; keep line numbers
    blank=lambda m: re.sub(r"[^\n]"," ",m.group(0))
    body=re.sub(r"/\*.*?\*/",blank,body,flags=re.S)
    body=re.sub(r"(?<![:\w\"'])//[^\n]*",blank,body)
    out=[]
    for m in STR.finditer(body):
        if m.group(1) and re.fullmatch(SKIP_KEYS,m.group(1),re.I): continue
        t=m.group(2)[1:-1].strip()
        toks=t.split()
        if len(toks)<MIN_WORDS or sum(("-" in w or ":" in w or "/" in w) for w in toks)>len(toks)*0.3: continue
        out.append((body[:m.start()].count("\n")+1,re.sub(r"\s+"," ",t)))
    return out

def blocks(path):
    """(line, text) per paragraph of visible copy, headings excluded."""
    raw=open(path,encoding="utf-8",errors="ignore").read()
    body=re.sub(r"\A---\n.*?\n---\n","",raw,flags=re.S)
    body=re.sub(r"```.*?```","",body,flags=re.S)
    ext=os.path.splitext(path)[1].lower()
    if ext in (".ts",".js"): return body,strings(body)
    if ext in (".tsx",".jsx"):
        # object-field strings, plus JSX text with those fields blanked out
        found=strings(body)
        body_jsx=STR.sub(lambda m: " "*len(m.group(0)) if m.group(1) else m.group(0),body)
        _,jsx=blocks_from(visible_copy(body_jsx,path))
        return body,found+jsx
    return body,blocks_from(visible_copy(body,path) if ext==".html" else list(enumerate(body.split("\n"),1)))[1]

def blocks_from(lines):
    out,cur,start=[],[],None
    for ln,line in lines+[(None,"")]:
        if line.strip() and not re.match(r"^#{1,6} ",line):
            if not cur: start=ln
            cur.append(re.sub(r"^\s*(?:[-*]|\d+\.)\s+","",line.strip()))
        elif cur:
            out.append((start," ".join(cur))); cur=[]
    return None,[(ln,t) for ln,t in out if len(t.split())>=MIN_WORDS]

def main():
    args=sys.argv[1:]
    show_all="--all" in args
    thr=0.75
    if "--threshold" in args: thr=float(args[args.index("--threshold")+1])
    local="--local" in args
    global HEAD_ONLY; HEAD_ONLY="--headings" in args
    files=[a for i,a in enumerate(args) if not a.startswith("--") and (i==0 or args[i-1]!="--threshold")]
    if not files: print(__doc__); sys.exit(2)

    import requests,subprocess
    sess=requests.Session()
    started=False
    if local:
        key=None
        was_up=subprocess.run([sys.executable,SWITCH,"status"],capture_output=True,text=True).stdout.startswith("Kev: up")
        if not was_up:
            r=subprocess.run([sys.executable,SWITCH,"up"],capture_output=True,text=True)
            if r.returncode: print(f"ERROR: local Kev not available - {r.stdout.strip()}"); sys.exit(2)
            started=True
    else:
        key=get_key()
    try: run(files,sess,key,thr,show_all,"Kev (local)" if local else "Jev (hosted)")
    finally:
        if started: subprocess.run([sys.executable,SWITCH,"down"],capture_output=True)

def run(files,sess,key,thr,show_all,who):
    jobs=[]
    for f in files:
        if not os.path.exists(f): print(f"ERROR: not found - {f}"); sys.exit(2)
        body,paras=blocks(f)
        if not HEAD_ONLY: jobs+=[(f,ln,t,PARA_Q) for ln,t in paras]
        src=open(f,encoding="utf-8",errors="replace").read().split("\n")
        jobs+=[(f,ln,h,HEAD_Q if is_hero(src,ln) else LABEL_Q) for ln,h in headings(body,f)]

    try:
        with ThreadPoolExecutor(8) as ex:
            results=list(ex.map(lambda j: ask(sess,key,j[2],j[3]),jobs))
    except Exception as e:
        print(f"ERROR: {who} call failed - {e}"); sys.exit(2)

    flags=0
    for (f,ln,text,_),ans in zip(jobs,results):
        hits={k:p for k,p in ans.items() if p>=min(thr,Q_THRESHOLD.get(k,thr))}
        if not hits and not show_all: continue
        flags+=bool(hits)
        tag="FLAG" if hits else "ok  "
        shown=hits if hits else ans
        print(f"{tag} {os.path.relpath(f)}:{ln}  "+"  ".join(f"{k} {p:.2f}" for k,p in sorted(shown.items(),key=lambda x:-x[1])))
        print(f"       {text[:140]}")
    print(f"\n{flags} flagged of {len(jobs)} checked by {who} (threshold {thr}). Flags are for a human read, not a gate.")
    sys.exit(0)

if __name__=="__main__": main()
