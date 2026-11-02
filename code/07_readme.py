"""Step 7. README.md, LICENSE and reddit/post.md, with numbers from data/results.json. 10.5281/zenodo.23873537 and https://blog.tristanhotham.com/2026/10/31/transported-convicts/ stay as
placeholders for the publisher."""
from common import *

R = jload(f"{DATA}/results.json")
s, pk, cv, ir, dd, de, wo, st, cl = R["source"], R["peak"], R["cover"], R["irish"], R["days"], R["deaths"], R["women"], R["stated"], R["col"]
N = lambda v: f"{round(v):,}"
readme = f"""# Transported: the convict ships to Australia, 1788 to 1868

A map and analysis of the {N(s['n_main'])} convict voyages from overseas to Australia in English Wikipedia's four colony lists of convict ships (New South Wales, Tasmania, Norfolk Island, Western Australia), {s['first_year']} to {s['last_year']}: where the ships sailed from, how long they took, how many convicts died, and how the Australian system compares with penal transportation by Britain, France, Russia and British India elsewhere.

Interactive page: {PAGE}
Paper: https://doi.org/{DOI}
Blog post: {BLOG}

## Headline results

- Voyages: {N(s['rows_total'])} listed voyages, of which {N(s['n_main'])} arrived from overseas ({cv['n_main_pct_806']:.0f}% of the {st['ships_806']} ships Wikipedia's "Convicts in Australia" gives). New South Wales {cl['nsw']['n']}, Van Diemen's Land {cl['vdl']['n']}, Norfolk Island {cl['nfk']['n']}, Western Australia {cl['wa']['n']}.
- Timing: busiest year {pk['year']} ({pk['n']} arrivals); {pk['pct_1815_1840']:.0f}% arrived between 1815 and 1840; from 1841 to 1849, {pk['vdl_4149']} to Van Diemen's Land, {pk['nfk_4149']} to Norfolk Island, {pk['nsw_4149']} to New South Wales. Last ship: Hougoumont, Fremantle, 9 January 1868.
- People: the articles give about {N(st['conv_162'])} convicts. The lists give convict numbers for only {cv['n_conv']} voyages ({N(cv['sum_conv'])} people), almost none for New South Wales and Tasmania; Western Australia's {R['wa']['n']} voyages sum to {N(R['wa']['sum'])} (the articles say {N(st['wa_668'])} and {N(st['wa_721'])}).
- Ports: Cork is the busiest single port ({ir['cork']}); Irish ports supplied {ir['pct']:.0f}% of voyages from the British Isles ({ir['nsw_pct']:.0f}% of New South Wales's, {ir['vdl_pct']:.0f}% of Van Diemen's Land's). {R['indian']['n']} voyages sailed from India, Ceylon, Mauritius and Singapore.
- Passage: median {dd['eras'][0]['median']} days for the first three fleets, {dd['eras'][2]['median']} in 1820 to 1839 ({dd['n']} voyages with both dates). Longest Lady Juliana ({dd['slow']['days']}), shortest Scindian ({dd['fast']['days']}).
- Deaths: Second Fleet {de['sf_pct']}% of embarked convicts; Third Fleet {de['tf_pct']:.1f}%; {de['art_pct']:.1f}% on {de['art_n']} later voyages whose ship articles give the figures.
- Women: about {N(st['women'])}, one in seven; women's share of the NSW convict population fell from {wo['pop_first_pct']:.0f}% (1788) to {wo['pop_last_pct']:.0f}% ({wo['pop_last_year']}). The lists identify only {wo['flagged']} women's voyages.

## Files

| File | What it is |
|---|---|
| `index.html` | The interactive page (built by `code/04_build_site.py`; all page data embedded). |
| `header.png` | Social card, 1200 x 630. |
| `data/voyages.csv` | Every listed voyage: colony, ship, Wikipedia article, arrival as listed and parsed, departure place as listed and matched, region, notes, convicts embarked and landed, women, deaths, departure date and voyage days where known (with source), flags (transfer within Australia, Parkhurst ship, listed twice), whether counted, route key. CC BY-SA 4.0. |
| `data/voyages_by_year.csv` | Voyages from overseas per year and colony, and convicts where given. |
| `data/ports.csv` | Departure places with my coordinates and region. |
| `data/ships.csv` | Ships with their listed voyages and infobox details (launch year, tons burthen, fate, voyages stated in the article). CC BY-SA 4.0. |
| `data/other_penal_systems.csv` | Other penal transportation systems with the years and numbers the articles state. |
| `data/source_tables/` | The tables as parsed from Wikipedia (voyage rows, fleet ships, NSW convict population by sex, Norfolk Island removals, prison hulks, ship articles, category members, voyage details from ship articles with the sentence quoted). CC BY-SA 4.0. |
| `data/source_quotes.json` | Every fact quoted from Wikipedia, with the exact phrase, sentence and revision id. |
| `data/results.json` | Every number used in the page, paper, blog, collage and post. |
| `data/site.json`, `data/routes.json`, `data/world.json` | Page data: voyages, stylised routes, Natural Earth outlines. |
| `code/` | Scripts, run in order (below), and the page, paper and blog templates. |
| `release/` | Paper PDF and LaTeX source with figures (`paper/`), blog post, figures and meta (`blog/`), Zenodo files (`zenodo/`). |
| `reddit/` | Collage (`collage.py`, PNG) and post text. |

## Method in brief

- Voyage from overseas: a list row with an arrival year and a departure place outside Australia, excluding Parkhurst apprentice ships and voyages listed by two colonies (same ship name, arrivals within {R['meta']['dup_days']} days). Prince of Wales (First Fleet), missing from the NSW list, is added from the First Fleet article. Years are arrival years.
- Numbers, departure dates and deaths: Norfolk Island and Western Australia tables, the First, Second and Third Fleet tables, and sentences in ship articles kept only where the article's arrival date is within {R['meta']['match_days']} days of the list's.
- Routes: stylised sailing tracks through open-sea waypoints, checked not to cross land. The lists give only port and colony.
- Other systems: only figures the articles state, each checked against the exact phrase.
- Caveats: volunteer lists, not checked against primary records; the Tasmania list is short; convict numbers for {cv['n_conv_pct']:.0f}% of voyages; duration and death samples small; the women's count is a floor.

## How to rerun

Needs Python 3 with numpy, pandas, shapely, pyproj, matplotlib, fontTools, beautifulsoup4 and lxml, xelatex and pdftotext; node with Playwright for `code/qa.js`. Step 1 reads the raw Wikipedia dumps in `raw/` (not published; the parsed tables are in `data/source_tables/`); later steps read `data/` only. Natural Earth is read from `/home/claude/newdata/raw/geo/` (set `TC_GEO`). Intermediates go to `/dev/shm/transportedconvicts/work` (set `TCTMP`).

```
python3 code/01_parse.py        # raw Wikipedia pages -> data/source_tables, data/source_quotes.json
python3 code/02_geo.py          # outlines and stylised routes
python3 code/03_results.py      # results.json, data tables, page data
python3 code/04_build_site.py   # index.html
python3 code/05_figures.py      # header, blog and paper figures
python3 code/06_paper.py        # paper PDF
python3 reddit/collage.py       # collage
python3 code/07_readme.py       # README, LICENSE, Reddit post
python3 code/08_release.py      # blog post, Zenodo files
```

## Sources and licences

- English Wikipedia (CC BY-SA 4.0): the four colony lists of convict ships, First Fleet, Second Fleet (Australia), Third Fleet (Australia), Convicts in Australia, Convict women in Australia, Penal transportation, Transportation Act 1717, Convict era of Western Australia, Norfolk Island, Moreton Bay Penal Settlement, Macquarie Harbour Penal Station, Port Arthur, Tasmania, Australian Convict Sites, Royal Naval Dockyard, Bermuda, List of British prison hulks, Bagne (penal establishment), Katorga, Cellular Jail, Devil's Island, Penal colony, Sakhalin, Gulag, Port Blair, Andaman Islands, Convict ship, Hulk (ship type) and {s['n_ship_articles']} convict ship articles. Revision ids are in `data/source_quotes.json` and the paper.
- Natural Earth land and countries (https://www.naturalearthdata.com/). Public domain.
- Optional shaded relief tiles on the page: Esri.

## Citation

Hotham, T. (2026) Transported: the convict ships to Australia, 1788 to 1868, and the wider world of penal transportation. Zenodo. https://doi.org/{DOI}

Dr Tristan Hotham, Independent researcher. ORCID 0000-0003-4931-9349.

{AI}
"""
open(os.path.join(ROOT, "README.md"), "w", encoding="utf-8").write(readme)

lic = open("/home/claude/studies/rocket-launches/LICENSE", encoding="utf-8").read().split("\n\n\nThis licence covers")[0]
lic += """


This licence covers the code in code/, reddit/collage.py and the page scripts.
The text of the page, paper and blog post, the figures and the derived data
files in data/ are released under CC BY 4.0, except the tables derived from
English Wikipedia, which are released under CC BY-SA 4.0: data/voyages.csv,
data/ships.csv, data/source_tables/, data/source_quotes.json and the voyage
data embedded in data/site.json and index.html. Please credit "English
Wikipedia contributors" for those. Natural Earth is public domain.
"""
open(os.path.join(ROOT, "LICENSE"), "w", encoding="utf-8").write(lic)

post = f"""## Title

[OC] Every convict ship to Australia in Wikipedia's lists: {N(s['n_main'])} voyages, 1788 to 1868. Arrivals peaked at {pk['n']} in {pk['year']}, the busiest port was Cork, and the Second Fleet lost a quarter of its convicts at sea

## Body

Britain transported about {N(st['conv_162'])} convicts to Australia. I combined Wikipedia's four colony lists of convict ships and drew every voyage from overseas on the usual sailing route of the time, south through the Atlantic, past the Cape and across the Southern Ocean. {pk['pct_1815_1840']:.0f}% of the voyages arrived between 1815 and 1840. Cork sent {ir['cork']} ships, more than any other port, and {ir['nsw_pct']:.0f}% of New South Wales's ships from the British Isles were Irish. The first three fleets took a median of {dd['eras'][0]['median']} days; by the 1820s and 1830s it was {dd['eras'][2]['median']}. The Second Fleet's contractors were paid per head "whether they landed alive or not", and {de['sf_pct']}% of its convicts died at sea; on {de['art_n']} later voyages with figures, {de['art_pct']:.1f}%. Caveats: the lists give convict numbers for only {cv['n_conv']} voyages, so they map the ships, not the people; routes are stylised, not logged tracks. Interactive map with a play button: {PAGE}

## Source comment

Source: English Wikipedia (CC BY-SA 4.0), "Convict ships to New South Wales", "Convict ships to Tasmania", "Convict ships to Norfolk Island", "List of convict ship voyages to Western Australia", the First, Second and Third Fleet articles, ship articles, and "Convicts in Australia" and "Penal transportation" for totals and context. A voyage counts once, by its year of arrival; transfers between Australian ports are left out. Outlines: Natural Earth.

Tools: Python (pandas, shapely, pyproj, matplotlib); MapLibre for the interactive map.

Interactive version: {PAGE}
Paper: https://doi.org/{DOI}
Blog post: {BLOG}
"""
for t in (readme, post):
    visible_text_ok(t.replace("```", "").replace("|---|---|", ""), "readme/post")
os.makedirs(os.path.join(ROOT, "reddit"), exist_ok=True)
open(os.path.join(ROOT, "reddit", "post.md"), "w", encoding="utf-8").write(post)
print("readme, licence, post ok")
