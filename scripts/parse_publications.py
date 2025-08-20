# scripts/parse_publications.py
import json, re, sys, pathlib, requests
from bs4 import BeautifulSoup

SRC = "https://raghavian.github.io/publications/"
OUT = pathlib.Path("_data/publications.json")

def normspace(s):
    return re.sub(r"\s+", " ", s or "").strip()

def extract_title_from_quotes(text):
    """
    Return (title, start_index, end_index) if we can find a quoted span,
    preferring smart quotes “ … ”, then straight quotes " … ".
    Choose the candidate with the most words to avoid grabbing tiny quoted bits.
    """
    candidates = []
    for m in re.finditer(r"“([^”]+)”", text):
        inner = m.group(1).strip()
        if len(inner) >= 6:
            word_count = len(re.findall(r"\w+", inner))
            candidates.append((word_count, len(inner), inner, m.start(), m.end()))
    for m in re.finditer(r'"([^"]+)"', text):
        inner = m.group(1).strip()
        if len(inner) >= 6:
            word_count = len(re.findall(r"\w+", inner))
            candidates.append((word_count, len(inner), inner, m.start(), m.end()))
    if not candidates:
        return None, None, None
    # sort by word count then by length, both descending
    candidates.sort(key=lambda t: (t[0], t[1]), reverse=True)
    _, _, title, start, end = candidates[0]
    return title, start, end

MONTHS = {
    "jan": "01","january":"01",
    "feb": "02","february":"02",
    "mar": "03","march":"03",
    "apr": "04","april":"04",
    "may": "05",
    "jun": "06","june":"06",
    "jul": "07","july":"07",
    "aug": "08","august":"08",
    "sep": "09","sept":"09","september":"09",
    "oct": "10","october":"10",
    "nov": "11","november":"11",
    "dec": "12","december":"12",
}

def guess_iso_date(text, year):
    if not year:
        return "0000-01-01"
    m = re.search(r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)", text, re.I)
    month = MONTHS.get(m.group(0).lower(), "01") if m else "01"
    d = re.search(r"\b([12][0-9]|3[01]|0?[1-9])\b", text)
    day = f"{int(d.group(1)):02d}" if d else "01"
    return f"{year}-{month}-{day}"

def split_authors_and_rest(text):
    """
    Fallback when there are no quotes. Try to choose the period that ends the author block,
    skipping initials like 'J.' and requiring the next sentence to look title-like.
    """
    STOPWORDS = {"the","a","an","of","with","for","to","and","in","on","by","using","via","from"}
    for m in re.finditer(r"\.\s", text):
        before = text[:m.start()]
        after = text[m.end():]
        if not ("," in before or " and " in before):
            continue
        nxt = after.find(".")
        sentence = after if nxt == -1 else after[:nxt]
        words = re.findall(r"[A-Za-z']+", sentence.lower())
        if len(words) >= 3 or any(w in STOPWORDS for w in words):
            return before.strip(), after.strip()
    return "", text.strip()

def parse_li(li, section_label):
    # Flatten to a single line so indexes are stable
    raw = normspace(" ".join(li.stripped_strings))

    # Pull resource links
    resources = []
    for a in li.find_all("a"):
        label = normspace(a.get_text())
        href = a.get("href", "").strip()
        if not href:
            continue
        if label.lower() in {"pdf", "arxiv", "code", "link", "doi"}:
            resources.append({"label": label, "url": href})
        else:
            resources.append({"label": label or "Link", "url": href})

    # Find year anywhere in the item
    year_match = list(re.finditer(r"(19|20)\d{2}", raw))
    year = year_match[-1].group(0) if year_match else ""

    # Prefer quoted title if present
    title, q_start, q_end = extract_title_from_quotes(raw)

    authors_list, venue = [], ""

    if title:
        # Authors are everything before the first opening quote, with dangling punctuation trimmed
        authors_text = raw[:q_start].rstrip(" .,:;")
        authors_list = [a.strip() for a in re.split(r",\s*|\s+and\s+", authors_text) if a.strip()]

        # Venue is taken from after the closing quote up to the year
        tail = raw[q_end:].strip()
        if year and year in tail:
            idx = tail.rfind(year)
            venue = normspace(tail[:idx]).strip(" ,.;:")
        else:
            # if year is missing here, take a conservative slice after quotes
            # and stop at the first two sentences to avoid pulling resource labels
            stop = tail.find(".")
            venue = normspace(tail[:stop]) if stop != -1 else normspace(tail)
    else:
        # Fall back to the conservative sentence split
        authors_text, rest = split_authors_and_rest(raw)
        authors_list = [a.strip() for a in re.split(r",\s*|\s+and\s+", authors_text) if a.strip()]
        # Title then venue heuristics
        title = ""
        tail = ""
        if rest:
            split = re.split(r"\s\.\s", rest, maxsplit=1)
            if len(split) == 2:
                title = split[0].strip()
                tail = split[1]
            else:
                m = re.search(r"\s,\s*(19|20)\d{2}", rest)
                if m:
                    title = rest[:m.start()].strip().rstrip(".")
                    tail = rest[m.start():]
                else:
                    title = rest
                    tail = ""
        if year and tail:
            idx = tail.rfind(year)
            if idx != -1:
                venue = normspace(tail[:idx]).strip(" ,.;:")

    primary = None
    if resources:
        for r in resources:
            if r["label"].lower() == "pdf":
                primary = r["url"]
                break
        primary = primary or resources[0]["url"]

    iso_date = guess_iso_date(raw, year)

    return {
        "title": title,
        "authors": authors_list,
        "venue": venue,
        "year": year,
        "date": iso_date,
        "link": primary,
        "resources": resources,
        "type": section_label
    }

def main():
    try:
        r = requests.get(SRC, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch {SRC}: {e}", file=sys.stderr)
        sys.exit(1)

    soup = BeautifulSoup(r.text, "lxml")

    label_map = {
        "Refereed Conference": "conference",
        "Journal": "journal",
        "Preprint": "preprint",
        "Monograph": "monograph",
    }

    items = []

    for h2 in soup.find_all(["h2", "h3"]):
        htxt = normspace(h2.get_text())
        section_label = next((v for k, v in label_map.items() if k in htxt), None)
        if not section_label:
            continue
        sib = h2.find_next_sibling()
        while sib and sib.name not in {"h2", "h3"}:
            if sib.name == "ol":
                for li in sib.find_all("li", recursive=False):
                    items.append(parse_li(li, section_label))
            for li in sib.find_all("li", recursive=True):
                if li.parent and li.parent.name != "ol":
                    items.append(parse_li(li, section_label))
            sib = sib.find_next_sibling()

    if not items:
        for li in soup.find_all("li"):
            items.append(parse_li(li, "unknown"))

    # Keep JSON grouped but your Jekyll template will order within groups
    items.sort(key=lambda x: (x.get("type",""), x.get("date","0000-01-01"), x.get("title","")), reverse=False)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()

