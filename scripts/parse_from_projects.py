# scripts/parse_from_projects.py
import json, re, sys, pathlib, requests
from bs4 import BeautifulSoup

PROJ_SRC = "https://raghavian.github.io/projects/"
OUT_PUBS = pathlib.Path("_data/publications.json")
OUT_THEMES = pathlib.Path("_data/project_themes.json")

def normspace(s): 
    return re.sub(r"\s+", " ", s or "").strip()

def quoted_title(txt: str):
    c=[]
    c += re.findall(r"“([^”]+)”", txt)          # smart quotes
    c += re.findall(r'"([^"]+)"', txt)          # straight quotes
    c=[t.strip() for t in c if len(t.strip())>=6]
    if not c: 
        return None
    c.sort(key=lambda t: (len(re.findall(r"\w+", t)), len(t)), reverse=True)
    return c[0]

def keyify_title(t: str):
    if not t: 
        return ""
    t=t.lower().replace("“","").replace("”","").replace('"',"")
    return re.sub(r"[^a-z0-9]+","",t)

MONTHS = {
    "jan":"01","january":"01","feb":"02","february":"02","mar":"03","march":"03","apr":"04","april":"04","may":"05",
    "jun":"06","june":"06","jul":"07","july":"07","aug":"08","august":"08","sep":"09","sept":"09","september":"09",
    "oct":"10","october":"10","nov":"11","november":"11","dec":"12","december":"12"
}

def guess_iso_date(text, year):
    if not year:
        return "0000-01-01"
    m = re.search(r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)", text, re.I)
    month = MONTHS.get(m.group(0).lower(), "01") if m else "01"
    d = re.search(r"\b([12][0-9]|3[01]|0?[1-9])\b", text)
    day = f"{int(d.group(1)):02d}" if d else "01"
    return f"{year}-{month}-{day}"

def parse_pub_li(li, theme_key, theme_label):
    raw = normspace(" ".join(li.stripped_strings))

    # collect resource links
    resources = []
    for a in li.find_all("a"):
        label = normspace(a.get_text())
        href = a.get("href", "").strip()
        if not href:
            continue
        resources.append({"label": label or "Link", "url": href})

    # title from quotes is authoritative on this page
    title = quoted_title(raw) or ""

    # authors are the text before the opening quote; venue is after closing quote up to the year
    authors_list, venue, year = [], "", ""
    if title:
        parts = raw.split(title, 1)
        before = parts[0].rstrip(' “”".,:;')
        after = parts[1].lstrip(' ”"').strip() if len(parts) > 1 else ""
        authors_list = [a.strip() for a in re.split(r",\s*|\s+and\s+", before) if a.strip()]
        ym = list(re.finditer(r"(19|20)\d{2}", raw))
        year = ym[-1].group(0) if ym else ""
        if year and year in after:
            idx = after.rfind(year)
            venue = normspace(after[:idx]).strip(" ,.;:")
        else:
            stop = after.find(".")
            venue = normspace(after[:stop]) if stop != -1 else normspace(after)
    else:
        # last-resort fallback: try to recover a year and treat the rest as title
        ym = list(re.finditer(r"(19|20)\d{2}", raw))
        year = ym[-1].group(0) if ym else ""
        venue = ""
        # naive title fallback: strip link labels like (pdf)
        title = re.sub(r"\((?:pdf|arxiv|code|link|doi)[^)]+\)", "", raw, flags=re.I).strip()

    # pick a primary link, prefer a PDF if present
    primary = None
    if resources:
        for r in resources:
            if r["label"].lower() == "pdf":
                primary = r["url"]; break
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
        "type": "from-projects",       # informational only
        "theme_key": theme_key,
        "theme_label": theme_label
    }

def main():
    try:
        r = requests.get(PROJ_SRC, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch {PROJ_SRC}: {e}", file=sys.stderr)
        sys.exit(1)

    soup = BeautifulSoup(r.text, "lxml")

    # discover themes in document order and parse their lists
    items = []
    theme_order = []
    seen_titles = set()  # avoid duplicates across themes

    for h in soup.find_all(["h2","h3"]):
        label = normspace(h.get_text())
        if not label:
            continue
        # treat every significant section as a theme; customize this set if your page has extra headings
        if label not in {"Sustainability of AI", "AI for Sciences", "Bio-Medical Image Analysis"}:
            continue

        key = re.sub(r"[^a-z0-9]+","-", label.lower()).strip("-")
        theme_order.append((key, label))

        sib = h.find_next_sibling()
        while sib and sib.name not in {"h2","h3"}:
            if sib.name in {"ol","ul"}:
                for li in sib.find_all("li", recursive=False):
                    rec = parse_pub_li(li, key, label)
                    nt = keyify_title(rec["title"])
                    if nt and nt not in seen_titles:
                        items.append(rec)
                        seen_titles.add(nt)
            sib = sib.find_next_sibling()

    # newest first overall; the template will still group by theme
    items.sort(key=lambda x: (x["date"], x["title"]), reverse=True)

    OUT_PUBS.parent.mkdir(parents=True, exist_ok=True)
    OUT_PUBS.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_THEMES.write_text(json.dumps({
        "order": [k for k,_ in theme_order],
        "labels": {k: lbl for k,lbl in theme_order}
    }, indent=2, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    main()

