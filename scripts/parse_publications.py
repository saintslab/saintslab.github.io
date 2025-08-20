# scripts/parse_publications.py
import json, re, sys, pathlib, requests
from bs4 import BeautifulSoup

SRC = "https://raghavian.github.io/publications/"
OUT = pathlib.Path("_data/publications.json")

def normspace(s): 
    return re.sub(r"\s+", " ", s or "").strip()

def parse_li(li, section_label):
    # Collect visible text and normalize spacing
    txt = normspace(li.get_text(" ", strip=True))

    # Extract anchors for resources
    res = []
    for a in li.find_all("a"):
        label = normspace(a.get_text())
        href = a.get("href", "").strip()
        if not href:
            continue
        # Normalize common labels
        if label.lower() in {"pdf", "arxiv", "code", "link"}:
            res.append({"label": label, "url": href})
        else:
            # Fall back to generic link labels if the anchor text is something else
            res.append({"label": label or "Link", "url": href})

    # Year is the last 4-digit number that looks like a year
    year_match = list(re.finditer(r"(19|20)\d{2}", txt))
    year = year_match[-1].group(0) if year_match else ""

    # Split authors, title, venue heuristically.
    # Pattern on the site is:
    # "Author A, Author B. Title . Venue, YEAR."
    # We take authors as text up to first period, title as between first period and the period before venue,
    # and venue as the segment ending with the year.
    authors, title, venue = "", "", ""
    first_dot = txt.find(". ")
    if first_dot != -1:
        authors = txt[:first_dot].strip()
        rest = txt[first_dot+2:].strip()
        # Title is up to the first ' . ' sequence
        title_split = re.split(r"\s\.\s", rest, maxsplit=1)
        if len(title_split) == 2:
            title = title_split[0].strip()
            tail = title_split[1]
        else:
            # Fallback: stop at ' , 20xx'
            m = re.search(r"\s,\s*(19|20)\d{2}", rest)
            if m:
                title = rest[:m.start()].strip().rstrip(".")
                tail = rest[m.start():]
            else:
                title = rest
                tail = ""
        # Venue is whatever precedes the year
        if year:
            # take the substring ending right before the year occurrence
            idx = tail.rfind(year)
            if idx != -1:
                venue = normspace(tail[:idx]).strip(" ,.")
    else:
        # If no dot at all, treat everything as title
        title = txt

    authors_list = [a.strip() for a in re.split(r",\s*| and ", authors) if a.strip()]

    # Choose a primary link if present
    primary = None
    if res:
        # Prefer PDF if present
        for r in res:
            if r["label"].lower() == "pdf":
                primary = r["url"]
                break
        primary = primary or res[0]["url"]

    return {
        "title": title,
        "authors": authors_list,
        "venue": venue,
        "year": year,
        "link": primary,
        "resources": res,
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

    # Map section headings to a coarse type
    label_map = {
        "Refereed Conference": "conference",
        "Journal": "journal",
        "Preprint": "preprint",
        "Monograph": "monograph"
    }

    items = []

    # Iterate h2 sections and collect subsequent <ol><li> until the next h2
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
            # Some static sites emit <p> with numbers. Catch stray <li> as well.
            for li in sib.find_all("li", recursive=True):
                if li.parent and li.parent.name != "ol":
                    items.append(parse_li(li, section_label))
            sib = sib.find_next_sibling()

    # If nothing found, fall back to any <li> on the page
    if not items:
        for li in soup.find_all("li"):
            items.append(parse_li(li, "unknown"))

    # Stable sort newest to oldest inside each type, then by title
    items.sort(key=lambda x: (x.get("type",""), x.get("year",""), x.get("title","")), reverse=False)
    # Your SAINTS site expects newest first overall; reverse within type groups if you prefer

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()

