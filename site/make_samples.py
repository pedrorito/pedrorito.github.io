"""Preview builder (box only). Inputs:
  CV repo (generated data):  publications.bib, projects.bib, main.tex (publist/project order, \\begin{cvbio} bio),
                             supervision.bib (only the types in publications.yml `supervision` are shown: PhD + MSc)
  Site repo (hand-edited):   home.yml, publications.yml (sections / journals / series / supervision)
Outputs: index.html, publications.html.
Production: export_md.py writes content/*.md with YAML front matter and build.py renders Jinja2 templates; the
cell/row logic below is what those templates do."""
import html, json, os, re, collections, yaml
from bibmini import parse, clean, latex2html as L
from icons import icon_svg   # contact-link icons (inline SVG, currentColor)
CV = os.path.join(os.environ.get('CV_DIR', '/workspace/overleaf-cv'), '')      # checkout of the private CV repo
OUT = os.environ.get('OUT_DIR', '.')                                         # _site/ in CI
os.makedirs(OUT, exist_ok=True)
import datetime; YEAR = datetime.date.today().year
P = parse(CV + 'publications.bib'); J = parse(CV + 'projects.bib')
PUBCFG = yaml.safe_load(open('publications.yml'))   # sections / journals / series
CFG = PUBCFG['sections']
HOME = yaml.safe_load(open('home.yml'))
JOURNALS = {j['name']: j for j in PUBCFG['journals']}
SERIES = PUBCFG['series']
tex = open(CV + 'main.tex').read()
tex_nc = '\n'.join(l for l in tex.splitlines() if not l.lstrip().startswith('%'))
ORDER = {lab: re.findall(r'\\pub\{([^}]+)\}', body)
         for lab, body in re.findall(r'\\begin\{publist\}\[(\w+)\](.*?)\\end\{publist\}', tex_nc, re.S)}
PROJ_ORDER = {}
for head, body in re.findall(r'\\subsubsection\{(Ongoing|Finished) projects\}(.*?)(?=\\subsubsection|\\section|\\end\{document\})', tex_nc, re.S):
    PROJ_ORDER[head.lower()] = re.findall(r'\\project\{([^}]+)\}', body)
LISTED_PROJECTS = {k for ks in PROJ_ORDER.values() for k in ks}   # projects with a row (anchor) on projects.html
E_ = html.escape
MONTHS = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()
STATUS = {'published': 'Published', 'accepted': 'Accepted', 'submitted': 'Submitted', 'inpress': 'In press'}
NA = '<span class="na" title="not available">–</span>'
FUNNEL = '<svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true"><path d="M1.5 2h13l-5 6v5l-3 1.5V8z" fill="currentColor"/></svg>'

# ---------- publisher: bib `publisher` > publications.yml journals > same journal elsewhere in the bib > DOI prefix ----------
DOI_PUB = {'10.1109': 'IEEE', '10.23919': 'IEEE', '10.1016': 'Elsevier', '10.1364': 'Optica', '10.1145': 'ACM',
           '10.3390': 'MDPI', '10.1007': 'Springer', '10.1142': 'World Scientific', '10.5281': 'Zenodo',
           '10.14279': 'TU Berlin (DepositOnce)'}
def doi_pub(e):
    m = re.match(r'10\.\d+', e.get('doi', '')); return DOI_PUB.get(m.group(0)) if m else None
LEARNED = {}
for e in P.values():
    if e.get('journal') and doi_pub(e): LEARNED.setdefault(clean(e['journal']), doi_pub(e))
def publisher(e):
    if e.get('publisher'): return L(e['publisher'])
    j = clean(e.get('journal', ''))
    return E_((JOURNALS.get(j) or {}).get('publisher') or LEARNED.get(j) or doi_pub(e)
              or ('IEEE' if j.startswith('IEEE') else '') or '')
def slug(s): return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')
def series(e):
    """Conference series (id, label) from booktitle: publications.yml series alias > acronym in last (...) > leading ACRONYM 20xx."""
    b = clean(e.get('booktitle', '')) 
    if not b: return None
    for sid, s in SERIES.items():
        if re.search(s['match'], b): return sid, s['name']
    m = re.search(r'\(([^()]+)\)\s*$', b)
    name = re.sub(r'^(Proc\. |Proceedings of the )?((19|20)\d\d )?(IEEE )?(\d+(st|nd|rd|th) )?', '', b).strip()
    name = re.sub(r'IEEE (\d+(st|nd|rd|th) )', 'IEEE ', name)
    name = re.sub(r'\s*\([^()]+\)\s*$', '', name)
    if m: return m.group(1).replace(' ', ''), (('IEEE ' if 'IEEE' in b and not name.startswith('IEEE') else '') + name + f' ({m.group(1)})')
    m = re.match(r'([A-Z]{3,})\s+(19|20)\d\d', b)
    if m: return m.group(1), m.group(1)
    return slug(name)[:40], name
def fmt_date(d):
    if not d: return ''
    p = d.split('-'); return (MONTHS[int(p[1]) - 1] + ' ' if len(p) > 1 else '') + p[0]
def authors(e):
    out = []
    for a in clean(e.get('author', '')).split(' and '):
        last, _, first = a.partition(', '); n = L(f'{first} {last}'.strip())
        out.append(f'<span class="me">{n}</span>' if last == 'Rito' and first.startswith('Pedro') else n)
    return ', '.join(out)
def plabel(k):   # projects.bib `shorttitle`; fallback = title without quotes / " - suffix" (6 projects lack shorttitle)
    j = J.get(k, {})
    return clean(j.get('shorttitle') or re.split(r' - ', j.get('title', k))[0]).replace('“', '').replace('”', '')
def projs(e): return [p.strip() for p in e.get('projects', '').split(',') if p.strip()]
SUB2AREA = {st['id']: t['id'] for t in HOME['topics'] for st in t['subtopics']}
def topics_of(e):   # bib `keywords` that are homepage topic ids, plus the area of each sub-topic
    kw = [k.strip() for k in e.get('keywords', '').split(',') if k.strip()]
    out = [k for k in kw if k in SUB2AREA or k in SUB2AREA.values()]
    return list(dict.fromkeys(out + [SUB2AREA[k] for k in out if k in SUB2AREA]))
def status(e): return e.get('pubstate', 'published')
def filter_tag(kind, val, label):
    return (f'<a class="tag-filter" href="publications.html?{kind}={E_(val)}" data-filter="{kind}" data-value="{E_(val)}" '
            f'title="Show only {E_(label)}" aria-label="Filter: only {E_(label)}">{FUNNEL}</a>')

def cell(col, e, n):
    st = status(e)
    if col == 'num':   return 'c-num', '#', str(n)
    if col == 'year':  return 'c-year', 'Year', e.get('date', '')[:4] or NA
    if col == 'date':  return 'c-year', 'Date', fmt_date(e.get('date')) or NA
    if col in ('journal', 'venue', 'event', 'repository'):
        lbl = {'journal': 'Journal', 'venue': 'Venue', 'event': 'Event', 'repository': 'Repository'}[col]
        if e.get('journal'):
            name = clean(e['journal']); j = JOURNALS.get(name)
            txt = f'<a class="jname" href="{E_(j["url"])}" title="Journal homepage">{L(e["journal"])}</a>' if j else L(e['journal'])
            return 'c-venue', lbl, txt + filter_tag('journal', slug(name), name)
        s = series(e)
        txt = L(e.get('booktitle') or e.get('publisher') or '') or NA
        return 'c-venue', lbl, txt + (filter_tag('venue', s[0], s[1]) if s and col == 'venue' else '')
    if col == 'publisher': return 'c-small', 'Publisher', publisher(e) or NA
    if col == 'volissue':
        v = L(e.get('volume', '') + (f" ({e['number']})" if e.get('number') else ''))
        return 'c-small', 'Vol. (Issue)', v or (f'<span class="status-text status-{st}">{STATUS[st]}</span>' if st != 'published' else NA)
    if col == 'pages':
        p = L(e.get('pages') or (f"art. {e['eid']}" if e.get('eid') else ''))
        return 'c-small', 'Pages', p or NA
    if col == 'location':  return 'c-small', 'Location', L(e.get('location')) or NA
    if col == 'projects':
        out = []
        for p in projs(e):
            j = J.get(p, {})
            if p in LISTED_PROJECTS:   # link only to projects that have a row on projects.html (no dead anchors)
                out.append(f'<a class="badge project" data-project="{p}" href="projects.html#{p}" title="{E_(clean(j.get("title", p)))}">{E_(plabel(p))}</a>')
            else:
                out.append(f'<span class="badge project" data-project="{p}" title="{E_(clean(j.get("title", p)))}">{E_(plabel(p))}</span>')
        return 'c-projects', 'Projects', ('<div class="badges">' + ''.join(out) + '</div>') if out else NA
    if col == 'links':
        Ls = [f'<a href="https://doi.org/{E_(e["doi"])}">DOI</a>'] if e.get('doi') else ([f'<a href="{E_(e["url"])}">Link</a>'] if e.get('url') else [])
        return 'c-links', 'Links', ' · '.join(Ls + [f'<a href="bib/{e["_key"]}.bib">BibTeX</a>'])
    if col == 'title':
        t = L(e['title']); url = f"https://doi.org/{e['doi']}" if e.get('doi') else e.get('url')
        b = []
        if st != 'published': b.append(f'<span class="badge status status-{st}">{STATUS[st]}</span>')
        if e.get('award'):    b.append(f'<span class="badge award">{E_(e["award"])}</span>')
        return 'c-title', 'Title', (f'<span class="title">{f"<a href={chr(34)}{E_(url)}{chr(34)}>{t}</a>" if url else t}</span>'
                                    f'<span class="authors">{authors(e)}</span>' + (f'<div class="badges">{"".join(b)}</div>' if b else ''))
    raise KeyError(col)
HEAD = {'num': '#', 'year': 'Year', 'date': 'Date', 'title': 'Title &amp; authors', 'journal': 'Journal', 'publisher': 'Publisher',
        'volissue': 'Vol. (Issue)', 'pages': 'Pages', 'venue': 'Venue', 'event': 'Event', 'location': 'Location',
        'repository': 'Repository', 'projects': 'Projects', 'links': 'Links'}

NAV_ITEMS = [('index.html', 'About'), ('publications.html', 'Publications'), ('projects.html', 'Projects'), ('supervision.html', 'Supervision')]
# Theme: default follows prefers-color-scheme; an explicit choice (toggle) is stored in localStorage and set as
# <html data-theme="light|dark">. Applied in <head> before first paint (no flash). Without JS the button stays hidden.
import hashlib   # cache-busting: ?v=<hash of style.css + site.js> so HTML and assets never mismatch
ASSET_V = hashlib.sha1(open('style.css', 'rb').read() + open('site.js', 'rb').read()).hexdigest()[:8]
THEME_HEAD = ('<script>try{var t=localStorage.getItem("theme");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}catch(e){}</script>\n'
              f'  <link rel="stylesheet" href="style.css?v={ASSET_V}">')
THEME_BTN = ('<button type="button" class="theme-toggle" id="theme-toggle" aria-label="Switch to dark mode" aria-pressed="false" hidden>'
             '<svg class="i-moon" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
             '<svg class="i-sun" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false"><g fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></g></svg>'
             '</button>\n'
             '<script>(function(){var d=document.documentElement,b=document.getElementById("theme-toggle"),m=matchMedia("(prefers-color-scheme: dark)");'
             'function cur(){return d.dataset.theme||(m.matches?"dark":"light")}'
             'function sync(){var k=cur()==="dark";b.setAttribute("aria-pressed",k);b.setAttribute("aria-label",k?"Switch to light mode":"Switch to dark mode");b.title=b.getAttribute("aria-label")}'
             'b.hidden=false;sync();m.addEventListener("change",sync);'
             'b.addEventListener("click",function(){var t=cur()==="dark"?"light":"dark";d.dataset.theme=t;try{localStorage.setItem("theme",t)}catch(e){}sync()})})()</script>')

def nav(cur):
    li = ''.join(f'<li><a class="nav-link" href="{h}"{" aria-current=" + chr(34) + "page" + chr(34) if h == cur else ""}>{t}</a></li>' for h, t in NAV_ITEMS)
    return f'<nav class="site-nav" aria-label="Main">\n  <div class="container{" wide" if cur == "publications.html" else ""}">\n    <a class="brand" href="index.html">{E_(HOME["site"]["name"])}</a>\n    {THEME_BTN}\n    <ul>{li}</ul>\n  </div>\n</nav>'

# ---------- shared page components (used by EVERY page; new pages get them for free) ----------
# chip_nav(items, label): the in-page section menu ("chips" row). ONE markup + ONE CSS class (.chips in style.css):
# wraps onto the next line on phones, never scrolls sideways. items = [(href, text, count|None, data_for|None), ...]
def chip_nav(items, label='Sections'):
    li = ''.join(f'<li><a class="chip" href="{E_(h)}">{E_(t)}'
                 + ('' if n is None else f' <span class="chip-count"{f" data-for={chr(34)}{d}{chr(34)}" if d else ""}>{n}</span>')
                 + '</a></li>' for h, t, n, d in ((list(i) + [None, None])[:4] for i in items))
    return f'<nav class="chips" aria-label="{E_(label)}"><ul>{li}</ul></nav>'

def footer(wide=False):
    return (f'<footer class="site-footer">\n  <div class="container{" wide" if wide else ""}">'
            f'<p class="copyright">&copy; {YEAR} {E_(HOME["footer"]["copyright"])}</p></div>\n</footer>')

# ================= publications.html =================
chips, blocks, total, empty = [], [], 0, {}
for s in CFG:
    keys = ORDER.get(s['id'], []); N = len(keys); total += N
    chips.append((f'#{s["id"]}', s['heading'], N, s['id']))
    rows, cnt = [], collections.Counter()
    for i, k in enumerate(keys):
        e = P[k]; n = i + 1
        cells = [(c, *cell(c, e, n)) for c in s['columns']]
        cols = [c for c, *_ in cells]
        if status(e) != 'published' and 'volissue' in cols and cols[cols.index('volissue') + 1:][:1] == ['pages'] \
                and not (e.get('volume') or e.get('pages') or e.get('eid')):   # one merged status cell instead of two blanks
            i_ = cols.index('volissue'); st_ = status(e)
            cells[i_:i_ + 2] = [('volpages', 'c-small c-status', 'Status', f'<span class="status-text status-{st_}">{STATUS[st_]}</span>')]
        for c, cl, lb, v in cells: cnt[c] += (v == NA)
        tds = ''.join(f'<td class="{cl}{" is-na" if v == NA else ""}" data-label="{lb}"{" colspan=" + chr(34) + "2" + chr(34) if c == "volpages" else ""}>{v}</td>' for c, cl, lb, v in cells)
        jn = clean(e.get('journal', '')); sr = series(e) if not jn else None
        attrs = (f'data-year="{e.get("date", "")[:4] or "in-review"}" data-projects="{" ".join(projs(e))}" '
                 f'data-topics="{" ".join(topics_of(e))}" '
                 f'data-award="{1 if e.get("award") else 0}" data-status="{status(e)}"'
                 + (f' data-journal="{slug(jn)}" data-journal-label="{E_(jn)}"' if jn else '')
                 + (f' data-venue="{E_(sr[0])}" data-venue-label="{E_(sr[1])}"' if sr else ''))
        rows.append(f'      <tr id="{k}" {attrs}>{tds}</tr>')
    empty[s['id']] = {HEAD[c].replace('&amp;', '&'): v for c, v in cnt.items() if v}
    sf = s.get('status_filter') or []
    sfh = ''
    if sf:
        opts = ''.join(f'<button type="button" data-status="{x}" aria-pressed="false">{STATUS[x]} <span class="n">{sum(status(P[k]) == x for k in keys)}</span></button>' for x in sf)
        sfh = (f'\n    <div class="status-filter" role="group" aria-label="{E_(s["heading"])}: status" data-section="{s["id"]}" hidden>'
               f'<button type="button" data-status="" aria-pressed="true">All</button>{opts}</div>')
    ths = ''.join(f'<th scope="col" class="h-{c}">{HEAD[c]}</th>' for c in s['columns'])
    note = f'\n    <p class="muted section-note">{E_(s["note"])}</p>' if s.get('note') else ''
    blocks.append(f'''  <section class="pub-section" id="{s["id"]}" aria-labelledby="h-{s["id"]}">
    <div class="section-head"><h2 id="h-{s["id"]}">{E_(s["heading"])} <span class="count-pill" data-for="{s["id"]}">{N}</span></h2>{sfh}</div>{note}
    <div class="table-wrap">
    <table class="data cols-{len(s["columns"])}" data-filterable data-section="{s["id"]}">
      <caption class="visually-hidden">{E_(s["heading"])}</caption>
      <thead><tr>{ths}</tr></thead>
      <tbody>
{chr(10).join(rows)}
      </tbody>
    </table>
    </div>
    <p class="empty-msg muted" hidden>No {E_(s["heading"].lower())} match the filters.</p>
  </section>''')
page = (open('publications.tpl.html').read().replace('{{THEME_HEAD}}', THEME_HEAD).replace('src="site.js"', f'src="site.js?v={ASSET_V}"').replace('{{NAV}}', nav('publications.html')).replace('{{SECTION_NAV}}', chip_nav(chips, 'Sections'))
        .replace('{{SECTIONS}}', '\n\n'.join(blocks)).replace('{{FOOTER}}', footer(True)).replace('{{TOTAL}}', str(total)))
open(os.path.join(OUT, 'publications.html'), 'w').write(page)

# ================= index.html =================
def bio_from_tex():
    m = re.search(r'\\begin\{cvbio\}(.*?)\\end\{cvbio\}', tex_nc, re.S)
    src = 'main.tex'
    if not m and os.environ.get('STRICT') == '1':
        raise SystemExit('main.tex has no \\begin{cvbio}...\\end{cvbio} block (required in CI)')
    if not m:   # not yet in the real CV: use the proposed sample block (provisional placeholder)
        m = re.search(r'\\begin\{cvbio\}(.*?)\\end\{cvbio\}', '\n'.join(l for l in open('cv-sample/bio-snippet.tex').read().splitlines()
                                                                  if not l.lstrip().startswith('%')), re.S); src = 'cv-sample/bio-snippet.tex (PROVISIONAL)'
    paras = [re.sub(r'\s+', ' ', p).strip() for p in re.split(r'\n\s*\n', m.group(1)) if p.strip()]
    return ''.join(f'<p>{L(p)}</p>' for p in paras), src
bio, bio_src = bio_from_tex()
TAGCOUNT = collections.Counter(t for k in {k for sec in CFG for k in ORDER.get(sec['id'], [])} if k in P for t in topics_of(P[k]))
H = HOME; site = H['site']; C = H['contact']; R = H['outside_lab']['related']
same_as = [l['url'] for g in C['groups'] for l in g['links'] if l.get('rel_me')]
jsonld = {'@context': 'https://schema.org', '@graph': [
    {'@type': 'ProfilePage', '@id': site['url'] + '#page', 'url': site['url'], 'mainEntity': {'@id': site['url'] + '#person'},
     'mentions': {'@id': R['url'] + '#organization'}, 'relatedLink': [R['url']]},
    {'@type': 'Person', '@id': site['url'] + '#person', 'name': site['name'], 'alternateName': site['alternate_name'], 'url': site['url'],
     'affiliation': [{'@type': 'CollegeOrUniversity', 'name': 'University of Aveiro', 'url': 'https://www.ua.pt/'},
                     {'@type': 'ResearchOrganization', 'name': 'Instituto de Telecomunicações', 'url': 'https://www.it.pt/'}],
     'image': site['url'] + site['image'], 'knowsAbout': site['knows_about'], 'sameAs': same_as},
    {'@type': 'Organization', '@id': R['url'] + '#organization', 'name': R['name'], 'url': R['url'], 'sameAs': R['same_as']}]}
topics = []
for t in H['topics']:
    def chip(st):
        n = TAGCOUNT.get(st['id'], 0)
        return (f'<li><a class="chip" href="publications.html?topic={E_(st["id"])}">{E_(st["label"])} <span class="chip-count">{n}</span></a></li>' if n
                else f'<li><span class="chip chip-static">{E_(st["label"])}</span></li>')
    more = (f'\n        <p class="topic-more"><a href="publications.html?topic={t["id"]}">All {E_(t["title"])} publications →</a></p>'
            if TAGCOUNT.get(t['id']) else '')
    summ = f'\n        <p class="topic-summary">{E_(t["summary"])}</p>' if t.get('summary') else ''
    topics.append(f'''      <article class="topic-card topic-{t["id"]}" id="topic-{t["id"]}">
        <h3>{E_(t["title"])}</h3>{summ}
        <ul class="topic-subs" aria-label="{E_(t["title"])} sub-topics">{"".join(chip(st) for st in t["subtopics"])}</ul>{more}
      </article>''')
research_note = '<p class=\"muted\">Each linked sub-topic opens the matching publications.</p>' if any(TAGCOUNT.get(st['id']) for t in H['topics'] for st in t['subtopics']) else ''
cnt = {s['id']: len(ORDER.get(s['id'], [])) for s in CFG}
short = {'journals': 'journal', 'conferences': 'conference', 'posters': 'posters', 'magazines': 'magazine', 'datasets': 'datasets'}
pubs_listed = [k for s in CFG for k in ORDER.get(s['id'], [])]
on, fin = PROJ_ORDER.get('ongoing', []), PROJ_ORDER.get('finished', [])
# Supervision: ONLY the types listed in publications.yml `supervision.types` (default PhD + MSc) reach the site;
# other supervision.bib types (BSc, internships, scholarships, ...) stay CV-only. SUP is shared with subpages.py.
SUP_TYPES = (PUBCFG.get('supervision') or {}).get('types') or [
    {'type': 'phdthesis', 'id': 'phd', 'heading': 'PhD theses'}, {'type': 'mathesis', 'id': 'msc', 'heading': 'MSc theses'}]
def sup_type(e): return (e.get('type') or e['_type']).strip().lower()
SUP_ALL = parse(CV + 'supervision.bib') if os.path.exists(CV + 'supervision.bib') else {}
SUP = {k: e for k, e in SUP_ALL.items() if sup_type(e) in {t['type'] for t in SUP_TYPES}}
sup_n = str(len(SUP)) if SUP else '—'
sup_note = (' · '.join(f'{n} {t["heading"].split()[0]}' for t in SUP_TYPES if (n := sum(sup_type(e) == t['type'] for e in SUP.values())))
            if SUP else 'PhD and MSc (co)supervision')
glance = [
    f'<a class="card" href="publications.html"><div class="stat">{sum(cnt.values())}</div><h3>Publications</h3><p class="muted">' + ' · '.join(f'{v} {short[k]}' for k, v in cnt.items()) + '</p></a>',
    f'<a class="card" href="projects.html"><div class="stat">{len(on) + len(fin)}</div><h3>Projects</h3><p class="muted">{len(on)} ongoing · {len(fin)} finished · {E_(H.get("glance_notes", {}).get("projects", ""))}</p></a>',
    f'<a class="card" href="supervision.html"><div class="stat">{sup_n}</div><h3>Supervision</h3><p class="muted">{sup_note}</p></a>']
def proj_card(k):
    j = J[k]; name = E_(plabel(k))
    h = f'<a href="{E_(j["url"])}">{name}</a>' if j.get('url') else f'<a href="projects.html#{k}">{name}</a>'
    funder = re.split(r',| \(| and its', clean(j.get('funder', '')))[0].strip()
    start = (j.get('date') or '').split('/')[0][:4]
    desc = L(j['title']) if j.get('title') else ''
    b = ''.join(f'<span class="badge">{E_(x)}</span>' for x in (funder, start + '–' if start else '') if x)
    return f'      <article class="card"><h3>{h}</h3>' + (f'<p>{desc}</p>' if desc else '') + f'<div class="badges">{b}</div></article>'
anchors = chip_nav([(f'#{a["id"]}', a['label']) for a in H['anchors']], 'On this page')
groups = ''.join(f'<div class="contact-group"><h3>{E_(g["label"])}</h3><ul class="links">' + ''.join(
    f'<li><a{" rel=" + chr(34) + "me" + chr(34) if l.get("rel_me") else ""} href="{E_(l["url"])}">{icon_svg(l["url"], l.get("icon"))}<span>{E_(l["label"])}</span></a></li>' for l in g['links']) + '</ul></div>' for g in C['groups'])
contact = ('    <div class="contact-grid">\n'
           f'      <div class="contact-group"><h3>Address</h3>' + ''.join(f'<p>{E_(a)}</p>' for a in C['affiliation']) + '</div>\n      ' + groups + '\n    </div>')
idx = open('index.tpl.html').read()
for k, v in {'{{THEME_HEAD}}': THEME_HEAD, '{{NAV}}': nav('index.html'), '{{NAME}}': E_(site['name']), '{{DESCRIPTION}}': E_(site['description']),
             '{{HEADLINE}}': site['headline'], '{{BIO}}': bio, '{{SECTION_NAV}}': anchors, '{{TOPICS}}': '\n'.join(topics), '{{RESEARCH_NOTE}}': research_note, '{{IMG}}': site['image'].rsplit('-', 1)[0],
             '{{GLANCE}}': '\n'.join('      ' + g for g in glance), '{{ONGOING}}': '\n'.join(proj_card(k) for k in on),
             '{{OUTSIDE}}': H['outside_lab']['html'], '{{FOOTER}}': footer(), '{{CONTACT}}': contact,
             '{{JSONLD}}': '\n'.join('  ' + l for l in json.dumps(jsonld, ensure_ascii=False, indent=2).splitlines())}.items():
    idx = idx.replace(k, v)
open(os.path.join(OUT, 'index.html'), 'w').write(idx)
print('publications:', cnt, 'total', total)
print('empty cells (shown as –):', json.dumps(empty, ensure_ascii=False))
print('bio from:', bio_src, '| ongoing:', on, '| projects', len(on), '+', len(fin))
unl = sorted({clean(P[k]['journal']) for k in pubs_listed if P[k].get('journal') and clean(P[k]['journal']) not in JOURNALS})
print('journals without URL:', unl)
print('venue series:', sorted({series(P[k]) for k in ORDER['conferences']}));print( len({series(P[k])[0] for k in ORDER['conferences']}), sorted(collections.Counter(series(P[k])[0] for k in ORDER['conferences']).items(), key=lambda x: -x[1])[:12])

# page_shell(): full HTML page (head with theme script + fingerprinted CSS, shared nav, h1, intro, chip_nav, footer).
# HOW TO ADD A PAGE: build `body` (sections with id="..."), then
#   open(os.path.join(OUT, 'new.html'), 'w').write(page_shell('Title', 'new.html', body, 'Meta description',
#        intro='<p class="muted">…</p>', sections=[('#a', 'Section A', 3), ('#b', 'Section B')], wide=True))
# and add ('new.html', 'Title') to NAV_ITEMS for the top menu. Nav, theme toggle, chips and footer are then identical to the other pages.
def page_shell(title, cur, body, desc, wide=False, intro='', sections=None):
    menu = f'  {chip_nav(sections)}\n' if sections else ''
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{E_(title)} — Pedro Rito</title>
  <meta name="description" content="{E_(desc)}">
  {THEME_HEAD}
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
{nav(cur)}
<main id="main" class="container{" wide" if wide else ""}">
  <h1>{E_(title)}</h1>
{intro}{menu}{body}
</main>
{footer(wide)}
</body>
</html>
'''

import subpages  # noqa: E402,F401  projects.html, supervision.html, bib/<key>.bib

if os.environ.get('PREVIEW') == '0':   # production build: drop the "Preview." banners
    for f in os.listdir(OUT):
        if f.endswith('.html'):
            p = os.path.join(OUT, f); t = open(p).read()
            open(p, 'w').write(re.sub(r'\s*<p class="sample-banner">.*?</p>', '', t, flags=re.S))
