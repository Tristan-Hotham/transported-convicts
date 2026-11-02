"""Shared paths, constants and helpers for the transported-convicts project ("Transported: the convict ships").

Raw inputs (read in place by 01_parse.py only, never modified; everything later steps need is written to data/):
  raw/convicts_lists.json   Parsed English Wikipedia pages (HTML with revision ids), fetched in 2026. CC BY-SA 4.0.
      Voyage tables:
        Convict ships to New South Wales                one table per letter: Name, Date of arrival, Sailed from, Notes
        Convict ships to Tasmania                       the same four columns
        Convict ships to Norfolk Island                 1788 to 1804 arrivals from Sydney (Vessel, Master, Date of arrival,
                                                        Sailed from, Convicts embarked, Convicts landed); 1807 to 1813
                                                        removals from the island; 1840 to 1850 arrivals direct from
                                                        Britain and Ireland (same columns as the first table)
        List of convict ship voyages to Western Australia   Parkhurst apprentices 1842 to 1849 (Ship, Arrival, Number);
                                                        convict voyages 1850 to 1868 (Ship, Origin, Arrival, Number)
        First Fleet, Second Fleet (Australia), Third Fleet (Australia)   per-ship tables with departure, arrival,
                                                        duration and convicts (with deaths for the Third Fleet)
        Convict women in Australia                      convict population of New South Wales by sex, 1788 to 1841
      Context (facts quoted in the text, each checked against the page text in 01_parse.py):
        Convicts in Australia, Penal transportation, Transportation Act 1717, Indentured servitude in British America,
        Convict era of Western Australia, Moreton Bay Penal Settlement, Macquarie Harbour Penal Station,
        Port Arthur, Tasmania, Norfolk Island, Australian Convict Sites, Bagne (penal establishment), Cellular Jail,
        Royal Naval Dockyard, Bermuda, List of British prison hulks, Katorga
      __catmembers   members of the Wikipedia categories of convict ships (to NSW, Tasmania, WA, Norfolk Island, Australia)
      __shipinfo     section 0 wikitext (infobox and lead) and Wikidata id of 305 ship articles in those categories
  raw/convicts_wiki.json    A noisy search dump of Wikipedia wikitext (no revision ids). Only on-topic pages are used:
                            the full articles of a few convict ships (for departure dates, convicts embarked and deaths,
                            each kept only when its arrival date matches the voyage tables), and "Devil's Island",
                            "Penal colony", "Port Blair", "Sakhalin" and "Gulag" for figures on other penal systems.
  /home/claude/newdata/raw/geo/ne_50m_land.geojson, ne_50m_admin_0_countries.geojson   Natural Earth (public domain)
"""
import json, gzip, os, re, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.environ.get("TC_RAW", os.path.join(ROOT, "raw"))
GEO = os.environ.get("TC_GEO", "/home/claude/newdata/raw/geo")
FONTS = os.environ.get("TC_FONTS", "/home/claude/ref/fonts")
DATA = os.path.join(ROOT, "data")
SRC = os.path.join(DATA, "source_tables")
WORK = os.path.join(os.environ.get("TCTMP", "/dev/shm/transportedconvicts"), "work")   # intermediates live in memory
for d in (DATA, SRC, WORK):
    os.makedirs(d, exist_ok=True)

SLUG = "transported-convicts"
PAGE = f"https://maps.tristanhotham.com/{SLUG}/"
REPO = f"https://github.com/Tristan-Hotham/{SLUG}"
DOI = "10.5281/zenodo.23873537"                # filled in by the publisher
BLOG = "https://blog.tristanhotham.com/2026/10/31/transported-convicts/"          # filled in by the publisher
AI = ("I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped "
      "prepare the analysis code. I reviewed and checked all text and results.")
WIKI_URL = lambda t: "https://en.wikipedia.org/wiki/" + t.replace(" ", "_")
Y0, Y1 = 1787, 1868            # slider years: the First Fleet sailed in 1787, the last convict ship arrived in 1868

# Arrival colonies. key, name, short name, colour, arrival point (lat, lon), the list article
COLONIES = [
    ("nsw", "New South Wales", "NSW", "#2F5FA7", (-33.857, 151.210), "Sydney (Port Jackson)", "Convict ships to New South Wales"),
    ("vdl", "Van Diemen's Land (Tasmania)", "Tasmania", "#C2412D", (-42.882, 147.331), "Hobart", "Convict ships to Tasmania"),
    ("nfk", "Norfolk Island", "Norfolk Island", "#2E8A6E", (-29.056, 167.959), "Kingston", "Convict ships to Norfolk Island"),
    ("wa", "Western Australia", "Western Australia", "#D9961A", (-32.055, 115.745), "Fremantle", "List of convict ship voyages to Western Australia"),
]
COL = {k: dict(name=n, short=s, c=c, ll=ll, place=p, list=t) for k, n, s, c, ll, p, t in COLONIES}
CK = [k for k, *_ in COLONIES]

# Departure places. Coordinates are my own, rounded to the harbour or anchorage (documented in the paper).
# key: (display name, lat, lon, region)
PORTS = {
    "portsmouth": ("Portsmouth", 50.797, -1.108, "England"),
    "spithead": ("Spithead", 50.760, -1.090, "England"),
    "plymouth": ("Plymouth", 50.360, -4.140, "England"),
    "devonport": ("Devonport", 50.370, -4.180, "England"),
    "torbay": ("Torbay", 50.450, -3.520, "England"),
    "dartmouth": ("Dartmouth", 50.350, -3.570, "England"),
    "falmouth": ("Falmouth", 50.150, -5.060, "England"),
    "portland": ("Portland", 50.570, -2.440, "England"),
    "cowes": ("Cowes", 50.760, -1.300, "England"),
    "landsend": ("Land's End", 50.060, -5.720, "England"),
    "sheerness": ("Sheerness", 51.443, 0.762, "England"),
    "woolwich": ("Woolwich", 51.492, 0.068, "England"),
    "deptford": ("Deptford", 51.483, -0.026, "England"),
    "gravesend": ("Gravesend", 51.444, 0.369, "England"),
    "london": ("London", 51.505, -0.075, "England"),
    "downs": ("The Downs", 51.230, 1.460, "England"),
    "yarmouth": ("Yarmouth Roads", 52.600, 1.760, "England"),
    "england": ("England (port not given)", 50.900, -1.400, "England"),
    "cork": ("Cork (Cove of Cork)", 51.850, -8.295, "Ireland"),
    "dublin": ("Dublin (Kingstown)", 53.294, -6.134, "Ireland"),
    "waterford": ("Waterford", 52.260, -7.110, "Ireland"),
    "ireland": ("Ireland (port not given)", 51.900, -8.350, "Ireland"),
    "bermuda": ("Bermuda", 32.325, -64.835, "Other colonies"),
    "quebec": ("Quebec", 46.810, -71.200, "Other colonies"),
    "cape": ("Cape of Good Hope", -33.920, 18.420, "Other colonies"),
    "calcutta": ("Calcutta", 22.570, 88.350, "India and the Indian Ocean"),
    "madras": ("Madras", 13.090, 80.290, "India and the Indian Ocean"),
    "bombay": ("Bombay", 18.940, 72.840, "India and the Indian Ocean"),
    "india": ("India (port not given)", 21.000, 88.000, "India and the Indian Ocean"),
    "ceylon": ("Ceylon", 6.930, 79.840, "India and the Indian Ocean"),
    "mauritius": ("Mauritius (Port Louis)", -20.160, 57.500, "India and the Indian Ocean"),
    "singapore": ("Singapore", 1.290, 103.850, "India and the Indian Ocean"),
    "sydney": ("Sydney (Port Jackson)", -33.857, 151.210, "Within Australia"),
    "hobart": ("Hobart", -42.882, 147.331, "Within Australia"),
    "norfolk": ("Norfolk Island", -29.056, 167.959, "Within Australia"),
    "adelaide": ("Adelaide", -34.850, 138.500, "Within Australia"),
    "swan": ("Swan River (Fremantle)", -32.055, 115.745, "Within Australia"),
    "portphillip": ("Port Phillip", -37.840, 144.950, "Within Australia"),
}
REGIONS = [("England", "#5B6770"), ("Ireland", "#2E8A6E"), ("India and the Indian Ocean", "#B5651D"),
           ("Other colonies", "#7A4FA0"), ("Within Australia", "#9C9486"), ("Not given", "#C9C2B6")]
REG_C = dict(REGIONS)

# "Sailed from" strings as written in the tables -> port key. Where a cell names two places, the first is the port of
# departure and the rest is kept as a note ('via').
SAILED = {
    "portsmouth": "portsmouth", "portsmouth england": "portsmouth", "spithead": "spithead", "plymouth": "plymouth",
    "devonport": "devonport", "torbay": "torbay", "dartmouth": "dartmouth", "falmouth": "falmouth", "portland": "portland",
    "cowes": "cowes", "land s end": "landsend", "sheerness": "sheerness", "sherness": "sheerness", "woolwich": "woolwich",
    "deptford": "deptford", "gravesend": "gravesend", "london": "london", "lonson": "london", "the downs": "downs", "downs": "downs",
    "yarmouth roads": "yarmouth", "england": "england", "cork": "cork", "dublin": "dublin", "kingstown dublin": "dublin",
    "kingstown": "dublin", "waterford": "waterford", "ireland": "ireland", "bermuda": "bermuda", "quebec": "quebec",
    "cape of good hope": "cape", "calcutta": "calcutta", "bengal": "calcutta", "madras": "madras", "bombay": "bombay",
    "india": "india", "ceylon": "ceylon", "mauritius": "mauritius", "isle de france": "mauritius", "ile de france mauritius": "mauritius",
    "port louis": "mauritius", "singapore": "singapore", "hobart town": "hobart", "hobart": "hobart", "port jackson": "sydney",
    "sydney": "sydney", "norfolk island": "norfolk", "adelaide": "adelaide", "swan river": "swan", "port phillip": "portphillip",
}


def jload(path):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def dash(v):
    """Remove em and en dashes and double hyphens from text (house style)."""
    if isinstance(v, str):
        v = re.sub(r"(\d)\s*[–—]\s*(\d)", r"\1 to \2", v)
        v = v.replace(" — ", ", ").replace("—", ", ").replace(" – ", ", ").replace("–", "-").replace("−", "-")
        while "--" in v:
            v = v.replace("--", "-")
        return v
    if isinstance(v, list):
        return [dash(x) for x in v]
    if isinstance(v, dict):
        return {k: dash(x) for k, x in v.items()}
    return v


def jsave(obj, path, indent=None):
    if os.path.abspath(path).startswith(DATA):
        obj = dash(obj)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent, separators=None if indent else (",", ":"))


def norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    return re.sub(r"[\W_]+", " ", s).strip()


def get(R, path):
    v = R
    for k in path.split("."):
        v = v[int(k)] if isinstance(v, list) else v[k]
    return v


def fmt(v, f=None):
    if f is None or f == "raw": return str(v)
    if f == "int": return f"{round(float(v)):,}"
    if f == "pc": return f"{round(float(v))}%"
    if f == "pc1": return f"{float(v):.1f}%"
    if f == "f1": return f"{float(v):.1f}"
    if f == "f2": return f"{float(v):.2f}"
    raise ValueError(f)


KEEP = ("DOI", "BLOG_URL", "DOI_URL")


def fill(text, R, keep=KEEP):
    """Replace {{path|format}} tokens with values from results.json; leave publisher placeholders and IMG tokens alone."""
    def rep(m):
        if m.group(1) in keep or m.group(1).startswith("IMG"):
            return m.group(0)
        return fmt(get(R, m.group(1)), m.group(3))
    return re.sub(r"\{\{([^}|]+)(\|(\w+))?\}\}", rep, text)


def visible_text_ok(s, where=""):
    for bad in ("—", "–", "--", "DSIT", "DCMS", "civil serv", "Civil Serv"):
        assert bad not in s, (where, bad, s[max(0, s.find(bad) - 80):s.find(bad) + 80])


MONTHS = {m: i + 1 for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                           "september", "october", "november", "december"])}
MONTHS.update({m[:3]: i for m, i in list(MONTHS.items())})


def parse_date(s):
    """'26 September 1791', 'October 1788', '1840', '7 Jan 1801', 'c.March 1830' -> (year, month, day) with None where
    missing; (None, None, None) if no year."""
    s = norm(s)
    m = re.search(r"(?:(\d{1,2}) )?(?:([a-z]+) )?(1[78]\d\d)\b", s)
    if not m:
        return None, None, None
    d, mo, y = m.group(1), m.group(2), int(m.group(3))
    mo = MONTHS.get(mo) if mo else None
    return y, mo, (int(d) if d and mo else None)
