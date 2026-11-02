# Transported: the convict ships to Australia, 1788 to 1868

A map and analysis of the 745 convict voyages from overseas to Australia in English Wikipedia's four colony lists of convict ships (New South Wales, Tasmania, Norfolk Island, Western Australia), 1788 to 1868: where the ships sailed from, how long they took, how many convicts died, and how the Australian system compares with penal transportation by Britain, France, Russia and British India elsewhere.

Interactive page: https://maps.tristanhotham.com/transported-convicts/
Paper: https://doi.org/10.5281/zenodo.23873537
Blog post: https://blog.tristanhotham.com/2026/10/31/transported-convicts/

## Headline results

- Voyages: 834 listed voyages, of which 745 arrived from overseas (92% of the 806 ships Wikipedia's "Convicts in Australia" gives). New South Wales 556, Van Diemen's Land 132, Norfolk Island 14, Western Australia 43.
- Timing: busiest year 1833 (35 arrivals); 76% arrived between 1815 and 1840; from 1841 to 1849, 16 to Van Diemen's Land, 10 to Norfolk Island, 5 to New South Wales. Last ship: Hougoumont, Fremantle, 9 January 1868.
- People: the articles give about 162,000 convicts. The lists give convict numbers for only 108 voyages (21,871 people), almost none for New South Wales and Tasmania; Western Australia's 43 voyages sum to 9,674 (the articles say 9,668 and 9,721).
- Ports: Cork is the busiest single port (101); Irish ports supplied 26% of voyages from the British Isles (34% of New South Wales's, 6% of Van Diemen's Land's). 101 voyages sailed from India, Ceylon, Mauritius and Singapore.
- Passage: median 190 days for the first three fleets, 115 in 1820 to 1839 (53 voyages with both dates). Longest Lady Juliana (309), shortest Scindian (89).
- Deaths: Second Fleet 26% of embarked convicts; Third Fleet 8.8%; 0.8% on 24 later voyages whose ship articles give the figures.
- Women: about 24,000, one in seven; women's share of the NSW convict population fell from 26% (1788) to 12% (1841). The lists identify only 20 women's voyages.

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

- Voyage from overseas: a list row with an arrival year and a departure place outside Australia, excluding Parkhurst apprentice ships and voyages listed by two colonies (same ship name, arrivals within 75 days). Prince of Wales (First Fleet), missing from the NSW list, is added from the First Fleet article. Years are arrival years.
- Numbers, departure dates and deaths: Norfolk Island and Western Australia tables, the First, Second and Third Fleet tables, and sentences in ship articles kept only where the article's arrival date is within 3 days of the list's.
- Routes: stylised sailing tracks through open-sea waypoints, checked not to cross land. The lists give only port and colony.
- Other systems: only figures the articles state, each checked against the exact phrase.
- Caveats: volunteer lists, not checked against primary records; the Tasmania list is short; convict numbers for 14% of voyages; duration and death samples small; the women's count is a floor.

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

- English Wikipedia (CC BY-SA 4.0): the four colony lists of convict ships, First Fleet, Second Fleet (Australia), Third Fleet (Australia), Convicts in Australia, Convict women in Australia, Penal transportation, Transportation Act 1717, Convict era of Western Australia, Norfolk Island, Moreton Bay Penal Settlement, Macquarie Harbour Penal Station, Port Arthur, Tasmania, Australian Convict Sites, Royal Naval Dockyard, Bermuda, List of British prison hulks, Bagne (penal establishment), Katorga, Cellular Jail, Devil's Island, Penal colony, Sakhalin, Gulag, Port Blair, Andaman Islands, Convict ship, Hulk (ship type) and 305 convict ship articles. Revision ids are in `data/source_quotes.json` and the paper.
- Natural Earth land and countries (https://www.naturalearthdata.com/). Public domain.
- Optional shaded relief tiles on the page: Esri.

## Citation

Hotham, T. (2026) Transported: the convict ships to Australia, 1788 to 1868, and the wider world of penal transportation. Zenodo. https://doi.org/10.5281/zenodo.23873537

Dr Tristan Hotham, Independent researcher. ORCID 0000-0003-4931-9349.

I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped prepare the analysis code. I reviewed and checked all text and results.
