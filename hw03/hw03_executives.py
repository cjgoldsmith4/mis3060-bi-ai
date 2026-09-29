# =============================================================================
# Script:      hw03/hw03_executives.py
# Data source: SEC EDGAR Form 8-K filings, Item 5.02 (Departure of Directors
#              or Certain Officers; Election of Directors; Appointment of
#              Certain Officers)
# Companies:   AAPL, MSFT, NVDA, JPM, WMT
# Author:      Charlie
# Course:      MIS3060 Business Intelligence with AI, Villanova University
# Generated:   2026-09-28 (Claude Cowork, from Specification B)
#
# Run from the repository root:
#     python hw03/hw03_executives.py
# Output:
#     hw03/executive_events.csv
#     hw03/raw_text/<TICKER>_<filing_date>_item502.txt  (Item 5.02 text of
#     each filing, kept for validation)
# =============================================================================

import csv
import datetime as dt
import os
import re
import time

import requests
from bs4 import BeautifulSoup

# Run from the repository root no matter where the script is launched
# (terminal command or the VS Code Run button).
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# -----------------------------------------------------------------------------
# Settings
# -----------------------------------------------------------------------------
HEADERS = {"User-Agent": "MIS3060 Villanova cgolds04@villanova.edu"}
REQUEST_PAUSE = 0.25
LOOKBACK_DAYS = 365
NOT_FOUND = "NOT_FOUND"

OUTPUT_DIR = "hw03"
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "executive_events.csv")
RAW_TEXT_DIR = os.path.join(OUTPUT_DIR, "raw_text")

COMPANIES = [
    {"company": "Apple Inc.", "ticker": "AAPL", "cik": "0000320193"},
    {"company": "Microsoft Corporation", "ticker": "MSFT", "cik": "0000789019"},
    {"company": "NVIDIA Corporation", "ticker": "NVDA", "cik": "0001045810"},
    {"company": "JPMorgan Chase & Co.", "ticker": "JPM", "cik": "0000019617"},
    {"company": "Walmart Inc.", "ticker": "WMT", "cik": "0000104169"},
]

CSV_COLUMNS = ["company", "ticker", "cik", "filing_date", "event_type",
               "person_name", "title", "effective_date"]

# -----------------------------------------------------------------------------
# Keyword and regex patterns
# -----------------------------------------------------------------------------
MONTHS = (r"(?:January|February|March|April|May|June|July|August|September|"
          r"October|November|December)")
DATE_RE = re.compile(MONTHS + r"\s+\d{1,2},\s+\d{4}")

DEPARTURE_RE = re.compile(
    r"\b(retire[sd]?|retiring|retirement|resign(?:s|ed|ing|ation)?|step(?:s|ped|ping)?\s+down|"
    r"depart(?:s|ed|ing|ure)?|leav(?:e|es|ing)\s+the\s+(?:Company|Firm|Board)|"
    r"not\s+(?:to\s+)?stand\s+for\s+re-?election|will\s+not\s+stand|"
    r"cease[sd]?\s+to\s+serve|separat(?:e|ed|ion)\s+from|terminat(?:ed|ion)\s+of\s+(?:his|her)\s+employment)\b",
    re.I)
APPOINTMENT_RE = re.compile(
    r"\b(appoint(?:s|ed|ing|ment)?|(?<!re-)(?<!re)elect(?:s|ed|ing)?\b(?!\s+(?:not|to\s+defer))|"
    r"named\s+(?:as|to)|nam(?:e|es)\s+[A-Z]|promot(?:e|ed|ion|ions)|hired|"
    r"join(?:s|ed)?\s+(?:the\s+)?(?:Company|Board|Apple|NVIDIA|Walmart|Microsoft|JPMorgan)|"
    r"will\s+(?:become|serve\s+as)|assume[sd]?\s+the\s+role|appointment)\b",
    re.I)
# "Tim Cook will transition from his role as CEO to Executive Chair": one
# person leaves a role and takes another in the same breath.
BOTH_RE = re.compile(r"\btransition(?:s|ed|ing)?\s+from\s+(?:his|her|their)\s+(?:role|position)", re.I)
# "succeeds Chris Kondo": the person after the verb is the one leaving.
SUCCEEDS_RE = re.compile(r"\b(?:succeeds|succeeding|replaces|replacing|successor\s+to|"
                         r"transition\s+of\s+(?:duties|responsibilities)\s+from)\s+")

TITLE_RE = re.compile(
    r"(Co-Presidents?(?:\s+and\s+(?:sole\s+)?CEO\s+of\s+(?:the\s+)?[A-Z][\w&']*(?:\s+(?:&\s+)?[A-Z][\w&']*)*)?"
    r"|(?:Executive|Senior)\s+Vice\s+President(?:,\s+[A-Z][\w&' ]{2,40}?(?=[,.;(]|\s+of\s)|\s+and\s+(?:Chief\s+[A-Z][a-z]+\s+Officer|Controller|Treasurer|General\s+Counsel))?"
    r"|Vice\s+President,?\s+(?:or\s+VP,\s+)?and\s+Chief\s+[A-Z][a-z]+\s+Officer"
    r"|(?:President\s+and\s+)?Chief\s+(?:[A-Z][a-z]+\s+){1,3}Officer"
    r"|(?:Co-)?CEO(?:\s+of\s+(?:the\s+)?(?:[A-Z][\w&']*\s*)+)?"
    r"|VP\s+and\s+CAO"
    r"|general\s+counsel"
    r"|Principal\s+(?:Accounting|Financial|Executive)\s+Officer"
    r"|Executive\s+Chair(?:man)?(?:\s+of\s+(?:the|Apple's)\s+Board(?:\s+of\s+Directors)?)?"
    r"|(?:Non-Executive\s+|Independent\s+)?(?:Chairman|Chair)\s+of\s+the\s+Board"
    r"|Lead\s+Independent\s+Director"
    r"|member\s+of\s+the\s+(?:Company's\s+)?Board(?:\s+of\s+Directors)?"
    r"|(?:independent\s+)?director\b"
    r"|(?:(?<=to\s)|(?<=from\s))(?:its|the)\s+Board(?:\s+of\s+Directors)?"
    r"|President(?:\s+and\s+Chief\s+Executive\s+Officer)?)",
    re.I)

NAME_STOPWORDS = {
    "the", "board", "directors", "director", "chief", "officer", "company",
    "inc", "corporation", "corp", "committee", "executive", "president", "vice",
    "senior", "financial", "operating", "technology", "apple", "apple's", "microsoft",
    "nvidia", "jpmorgan", "jpmorganchase", "chase", "walmart", "item", "section", "form",
    "securities", "exchange", "commission", "annual", "meeting", "shareholders",
    "stockholders", "compensation", "plan", "agreement", "united", "states",
    "general", "counsel", "human", "resources", "retail", "international",
    "club", "global", "chairman", "chair", "on", "effective", "january",
    "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december", "mr", "ms", "mrs", "dr",
    "report", "current", "registrant", "act", "rule", "exhibit", "press",
    "release", "bank", "america", "north", "new", "york", "delaware", "officers",
    "certain", "appointment", "departure", "election", "arrangements",
    "compensatory", "audit", "nominating", "governance", "risk", "public",
    "policy", "commercial", "consumer", "community", "asset", "wealth",
    "management", "investment", "banking", "markets", "corporate", "legal",
    "secretary", "treasurer", "controller", "accounting", "principal", "in",
    "as", "of", "and", "his", "her", "fiscal", "year", "target", "award", "base",
    "salary", "worldwide", "field", "operations", "people", "amended", "restated",
    "equity", "incentive", "performance", "restricted", "stock", "units", "firm",
    "ceo", "cfo", "coo", "vp", "cao", "co", "presidents", "following", "prior",
    "intel", "sam's", "sams", "u.s", "us", "store", "stores", "enterprise",
}

NAME = r"[A-Z][a-z]+(?:\s+[A-Z]\.)?(?:\s+[A-Z][a-zA-Z\-]+){1,3}"
HONORIFIC_RE = re.compile(r"\b(?:Mr|Ms|Mrs|Dr)\.?\s+((?:[A-Z][a-zA-Z\-]*\.?\s+){0,2}[A-Z][a-zA-Z\-]+)")
# Names in the positions 8-K filings put them: "Name, age 55,", "Name, 61,",
# "Name, Executive Vice President", "appointed Name", "On May 7, 2026, Name".
NAME_CONTEXT_RES = [
    re.compile(r"(" + NAME + r"),\s+(?:age\s+)?\d{2},"),
    re.compile(r"(" + NAME + r"),\s+(?:the\s+Company's\s+|a\s+|current\s+|its\s+)?"
               r"(?:member|Vice|Executive|Senior|Chief|President|Co-|CEO|General|Principal|Controller|Chair)"),
    re.compile(r"\b(?:appointed|elected|succeeds|succeeding|replacing|named)\s+(" + NAME + r")"),
    re.compile(r"\bOn\s+" + r"[A-Z][a-z]+\s+\d{1,2},\s+\d{4},\s+(" + NAME + r")\s+(?:notified|informed|resigned|announced|will|has|decided)"),
    re.compile(r"\bthat\s+(" + NAME + r")\s+(?:will|has|had|is|would)\b"),
]


# -----------------------------------------------------------------------------
# HTTP helper: every request goes through here with the User-Agent header.
# -----------------------------------------------------------------------------
def sec_get(url):
    time.sleep(REQUEST_PAUSE)
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return response
    except requests.RequestException as err:
        print(f"    WARNING: request failed for {url}: {err}")
        return None


# -----------------------------------------------------------------------------
# Step 2: find Item 5.02 8-K filings from the past 12 months
# -----------------------------------------------------------------------------
def rows_from_block(block):
    keys = ["accessionNumber", "filingDate", "form", "items", "primaryDocument"]
    count = len(block.get("accessionNumber", []))
    return [{k: block.get(k, [""] * count)[i] for k in keys} for i in range(count)]


def get_recent_502_filings(cik, cutoff):
    """Return 8-K filings with Item 5.02 filed on or after the cutoff date.
    Reads older submission files when the 'recent' block does not reach
    back to the cutoff (JPM files thousands of other forms)."""
    response = sec_get(f"https://data.sec.gov/submissions/CIK{cik}.json")
    if response is None:
        return []
    data = response.json()
    rows = rows_from_block(data.get("filings", {}).get("recent", {}))
    oldest = min((r["filingDate"] for r in rows), default=cutoff)
    for extra in data.get("filings", {}).get("files", []):
        if oldest <= cutoff:
            break
        more = sec_get("https://data.sec.gov/submissions/" + extra["name"])
        if more is None:
            break
        extra_rows = rows_from_block(more.json())
        rows += extra_rows
        oldest = min([oldest] + [r["filingDate"] for r in extra_rows])

    found = [r for r in rows
             if r["form"] in ("8-K", "8-K/A")
             and "5.02" in (r["items"] or "")
             and r["filingDate"] >= cutoff]
    found.sort(key=lambda r: r["filingDate"])
    return found


# -----------------------------------------------------------------------------
# Step 3: download and isolate the Item 5.02 text
# -----------------------------------------------------------------------------
def html_to_text(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(" ")
    text = (text.replace("\xa0", " ").replace("’", "'")
                .replace("“", '"').replace("”", '"'))
    return re.sub(r"\s+", " ", text).strip()


def item_502_section(text):
    """Return the text from the Item 5.02 heading to the next Item heading or
    the signature block. Prefers the heading that is followed by the item
    title ("Departure of Directors..."), which skips cross-references."""
    matches = list(re.finditer(r"Item\s*5\.02", text, re.I))
    if not matches:
        return text
    headed = [m for m in matches if re.match(r"\.?\s*[\-:.]?\s*Departure", text[m.end():m.end() + 20], re.I)]
    start = (headed[-1] if headed else matches[0]).end()
    rest = text[start:]
    end = re.search(r"Item\s*\d\.\d{2}\s*[\-:.]?\s*[A-Z]|SIGNATURES?\b", rest)
    section = rest[:end.start()] if end else rest
    section = re.sub(r"^[^.]{0,250}Officers\.?\s*", "", section, count=1)
    return section.strip()


def split_sentences(text):
    safe = re.sub(r"\b(Mr|Ms|Mrs|Dr|Inc|Corp|Co|Jr|Sr|No|Messrs|Mses)\.", r"\1<DOT>", text)
    safe = re.sub(r"\bU\.S\.", "U<DOT>S<DOT>", safe)
    safe = re.sub(r"\b([A-Z])\.\s", r"\1<DOT> ", safe)  # middle initials
    parts = re.split(r"(?<=[.;])\s+(?=[A-Z\"(])", safe)
    return [p.replace("<DOT>", ".").strip() for p in parts if p.strip()]


# -----------------------------------------------------------------------------
# Step 3 continued: people, event types, titles, effective dates
# -----------------------------------------------------------------------------
def strip_possessive(name):
    return re.sub(r"'s?$", "", name.strip())


def clean_name(candidate):
    words = re.findall(r"[A-Za-z'\-]+", candidate)
    return len(words) >= 1 and not any(w.lower() in NAME_STOPWORDS for w in words)


def find_people(section):
    """Return a list of (full name, short name). Uses two signals: names the
    filing later calls Mr./Ms. <surname>, and names in the fixed positions
    8-K filings use to introduce officers and directors."""
    people = []

    def add(full, short):
        full, short = strip_possessive(full), strip_possessive(short)
        if not clean_name(full):
            return
        for i, (f, s) in enumerate(people):
            if full == f or full.endswith(" " + s) or f.endswith(" " + short) or s == short:
                if len(full) > len(f):          # keep the longest form
                    people[i] = (full, s)
                return
        people.append((full, short))

    for m in HONORIFIC_RE.finditer(section):
        short = strip_possessive(m.group(1))
        # Drop trailing words that are not part of a name ("Ternus will").
        words = short.split()
        while len(words) > 1 and words[-1].lower() in NAME_STOPWORDS:
            words.pop()
        short = " ".join(words)
        if not clean_name(short):
            continue
        full = re.search(r"\b([A-Z][a-z]+(?:\s+[A-Z]\.)?\s+(?:[A-Z][a-z]+\s+)?" + re.escape(short) + r")\b",
                         section)
        add(full.group(1) if full and clean_name(full.group(1)) else short, short)

    for pattern in NAME_CONTEXT_RES:
        for m in pattern.finditer(section):
            full = m.group(1)
            add(full, full.split()[-1])
    return people


def mentions(sentence, person):
    full, short = person
    names = {full, short, full.split()[0] + " " + full.split()[-1], short.split()[-1]}
    out = []
    for n in names:
        for m in re.finditer(r"\b" + re.escape(n) + r"(?:'s?)?(?![a-z])", sentence):
            out.append(m.start())
    return sorted(set(out))


def classify_people(section, people, filing_date):
    """Assign each departure/appointment keyword in a sentence to the person
    mentioned closest to it. A person with both kinds of keyword is 'both'."""
    info = {p: {"dep": False, "app": False, "title": NOT_FOUND, "eff": NOT_FOUND}
            for p in people}
    # Defined dates: 'September 1, 2026 (the "Transition Date")'
    defined = {m.group(2): m.group(1) for m in re.finditer(
        r"(" + MONTHS + r"\s+\d{1,2},\s+\d{4})\s*\(the\s+\"([^\"]+)\"\)", section)}
    for sentence in split_sentences(section):
        pos = {p: mentions(sentence, p) for p in people}
        present = [p for p in people if pos[p]]
        # Skip hypotheticals ("In the event of Mr. Cook's retirement...").
        if not present or re.search(r"\bin\s+the\s+event\s+of\b|\bif\s+(?:he|she|the)\b", sentence, re.I):
            continue

        def closest(idx):
            # The subject named just before a verb owns it ("X will retire").
            before = [(idx - x, p) for p in present for x in pos[p] if 0 <= idx - x <= 120]
            if before:
                return min(before)[1]
            return min(present, key=lambda p: min(abs(x - idx) for x in pos[p]))

        touched = {}   # person -> position of the keyword tied to them
        for m in DEPARTURE_RE.finditer(sentence):
            p = closest(m.start())
            info[p]["dep"] = True
            touched.setdefault(p, m.start())
        for m in APPOINTMENT_RE.finditer(sentence):
            p = closest(m.start())
            # "the appointment of Mr. Furner": the person follows the noun.
            if re.match(r"\s+of\s+", sentence[m.end():m.end() + 5]):
                after = [(x - m.end(), q) for q in present for x in pos[q] if 0 <= x - m.end() <= 12]
                if after:
                    p = min(after)[1]
            info[p]["app"] = True
            touched.setdefault(p, m.start())
        for m in BOTH_RE.finditer(sentence):
            p = closest(m.start())
            info[p]["dep"] = info[p]["app"] = True
            touched.setdefault(p, m.end())
        for m in SUCCEEDS_RE.finditer(sentence):
            after = [p for p in present if any(x >= m.end() and x - m.end() < 5 for x in pos[p])]
            for p in after:
                info[p]["dep"] = True
                touched.setdefault(p, m.start())

        on_date = re.search(r"\bOn\s+(" + MONTHS + r"\s+\d{1,2},\s+\d{4})", sentence)
        for term, date in defined.items():   # "effective on the Transition Date"
            sentence = re.sub(r"(?:effective\s+)?(?:on|as\s+of)\s+the\s+" + re.escape(term),
                              "effective " + date, sentence)
        for p in touched:
            if info[p]["title"] == NOT_FOUND:
                anchor = touched[p]
                cands = [t for t in TITLE_RE.finditer(sentence)]
                # "appointed John Ternus, ..., as Chief Executive Officer":
                # the new title follows "as" / "to" after the keyword.
                new_role = [t for t in cands if t.start() > anchor
                            and re.search(r"\b(?:as|to|role\s+of)\s+(?:the\s+|its\s+|Apple's\s+|a\s+)?$",
                                          sentence[max(0, t.start() - 20):t.start()])]
                if info[p]["app"] and new_role:
                    cands = new_role[:1]
                if cands:
                    t = min(cands, key=lambda t: abs(t.start() - anchor))
                    title = re.sub(r"\s+", " ", t.group(1)).strip(" ,")
                    if re.match(r"(?:its|the)\s+Board", title):
                        title = "member of the Board of Directors"
                    info[p]["title"] = re.sub(r"^Co-Presidents$", "Co-President", title)
            if info[p]["eff"] == NOT_FOUND:
                eff = re.search(r"effective\s+(?:as\s+of\s+)?(?:on\s+)?(" + MONTHS
                                + r"\s+\d{1,2},\s+\d{4})", sentence, re.I)
                if eff:
                    info[p]["eff"] = eff.group(1)
                elif re.search(r"effective\s+immediately", sentence, re.I):
                    info[p]["eff"] = on_date.group(1) if on_date else filing_date
                elif on_date:
                    info[p]["eff"] = on_date.group(1)
                else:
                    d = DATE_RE.search(sentence)
                    if d:
                        info[p]["eff"] = d.group(0)
    return info


def extract_events(section, filing_date):
    """Return a list of (event_type, name, title, effective_date), one per
    person with a departure or appointment in the Item 5.02 text."""
    people = find_people(section)
    info = classify_people(section, people, filing_date)
    events = []
    for p in people:
        i = info[p]
        if i["dep"] and i["app"]:
            event = "both"
        elif i["dep"]:
            event = "departure"
        elif i["app"]:
            event = "appointment"
        else:
            continue
        events.append((event, p[0], i["title"], i["eff"]))
    return events


# -----------------------------------------------------------------------------
# Main pipeline
# -----------------------------------------------------------------------------
def build_url(cik, filing):
    return ("https://www.sec.gov/Archives/edgar/data/"
            f"{int(cik)}/{filing['accessionNumber'].replace('-', '')}/"
            f"{filing['primaryDocument']}")


def main():
    cutoff = (dt.date.today() - dt.timedelta(days=LOOKBACK_DAYS)).isoformat()
    print(f"Looking for Item 5.02 8-K filings dated {cutoff} or later")
    all_rows = []

    for company in COMPANIES:
        ticker = company["ticker"]
        print(f"\n=== {ticker} ({company['company']}) ===")
        try:
            filings = get_recent_502_filings(company["cik"], cutoff)
        except Exception as err:
            print(f"    WARNING: could not read submissions for {ticker}: {err}")
            filings = []

        if not filings:
            print(f"{ticker}: No executive events in past 12 months")
            continue

        for filing in filings:
            base_row = {"company": company["company"], "ticker": ticker,
                        "cik": company["cik"], "filing_date": filing["filingDate"]}
            try:
                response = sec_get(build_url(company["cik"], filing))
                if response is None:
                    raise RuntimeError("download failed")
                section = item_502_section(html_to_text(response.text))
                os.makedirs(RAW_TEXT_DIR, exist_ok=True)
                with open(os.path.join(RAW_TEXT_DIR,
                                       f"{ticker}_{filing['filingDate']}_item502.txt"),
                          "w", encoding="utf-8") as f:
                    f.write(build_url(company["cik"], filing) + "\n\n" + section)
                events = extract_events(section, filing["filingDate"])
            except Exception as err:
                print(f"    WARNING: {ticker} {filing['filingDate']}: {err}")
                events = []

            if not events:
                # Keep the filing on record even when no name could be parsed.
                print(f"    WARNING: {ticker} {filing['filingDate']}: Item 5.02 filing "
                      f"found but no departure/appointment could be extracted")
                events = [(NOT_FOUND, NOT_FOUND, NOT_FOUND, NOT_FOUND)]

            for event_type, name, title, effective in events:
                row = dict(base_row, event_type=event_type, person_name=name,
                           title=title, effective_date=effective)
                all_rows.append(row)
                print(f"{ticker} | {filing['filingDate']} | {event_type} | {name} | {title}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"\nSaved {len(all_rows)} events to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
