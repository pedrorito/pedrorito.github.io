"""projects.html, supervision.html and per-entry bib/<key>.bib. Imported at the end of make_samples.py (shares its state)."""
import os, collections
from __main__ import *          # P, J, CV, OUT, HOME, page_shell, chip_nav, plabel, projs, authors, fmt_date, L, E_, NA, on, fin, pubs_listed
from bibmini import parse

def period(d):
    if not d: return NA
    a, _, b = d.partition('/')
    return f'{fmt_date(a)} – {fmt_date(b) if b else "present"}'

# ---------- projects.html: main.tex order + projects.bib (funding amounts deliberately not shown) ----------
def proj_row(k):
    j = J[k]
    head = f'<span class="title">{E_(plabel(k))}</span>' + (f'<span class="authors">{L(j["title"])}</span>' if j.get('title') else '')
    det = ''.join(f'<p><strong>{lab}:</strong> {L(j[f])}</p>' for f, lab in
                  (('summary', 'Summary'), ('contribution', 'My contribution'), ('programme', 'Programme'), ('grantnumber', 'Grant')) if j.get(f))
    if det: head += f'<details><summary>Details</summary>{det}</details>'
    links = f'<a href="{E_(j["url"])}">Website</a>' if j.get('url') else ''   # no project->publications link (only publications->projects)
    return (f'      <tr id="{k}"><td class="c-title" data-label="Project">{head}</td>'
            f'<td class="c-small" data-label="Period">{period(j.get("date"))}</td>'
            f'<td class="c-venue" data-label="Funder">{L(j.get("funder")) or NA}</td>'
            f'<td class="c-small" data-label="Role">{L(j.get("role")) or NA}</td>'
            f'<td class="c-links" data-label="Links">{links or NA}</td></tr>')
def proj_table(hid, heading, keys):
    return f'''  <section class="pub-section" id="{hid}" aria-labelledby="h-{hid}">
    <h2 id="h-{hid}">{heading} <span class="count-pill">{len(keys)}</span></h2>
    <div class="table-wrap">
    <table class="data">
      <caption class="visually-hidden">{heading}</caption>
      <thead><tr><th scope="col">Project</th><th scope="col">Period</th><th scope="col">Funder</th><th scope="col">Role</th><th scope="col">Links</th></tr></thead>
      <tbody>
{chr(10).join(proj_row(k) for k in keys)}
      </tbody>
    </table>
    </div>
  </section>'''
body = (proj_table('ongoing', 'Ongoing projects', on) + '\n' + proj_table('finished', 'Finished projects', fin))
open(os.path.join(OUT, 'projects.html'), 'w').write(page_shell('Projects', 'projects.html', body, 'Research projects of Pedro Rito.', wide=True,
    sections=[('#ongoing', 'Ongoing', len(on)), ('#finished', 'Finished', len(fin))]))

# ---------- supervision.html: CV supervision.bib (empty state until it exists) ----------
SUP = parse(CV + 'supervision.bib') if os.path.exists(CV + 'supervision.bib') else {}
def sup_row(e):
    chips = ''.join(f'<a class="badge project" href="projects.html#{p}">{E_(plabel(p))}</a>' for p in projs(e))
    return (f'      <tr id="{e["_key"]}"><td class="c-year" data-label="Period">{period(e.get("date"))}</td>'
            f'<td class="c-title" data-label="Title"><span class="title">{L(e.get("title"))}</span><span class="authors">{authors(e)}</span></td>'
            f'<td class="c-small" data-label="Role">{L(e.get("role", "")).title() or NA}</td>'
            f'<td class="c-venue" data-label="Institution">{L(e.get("institution") or e.get("funder")) or NA}</td>'
            f'<td class="c-small" data-label="Status">{L(e.get("status", "")).title() or NA}</td>'
            f'<td class="c-projects" data-label="Projects">{"<div class=badges>" + chips + "</div>" if chips else NA}</td>'
            f'<td class="c-links" data-label="Links">' + (f'<a href="{E_(e["url"])}">Link</a>' if e.get('url') else NA) + '</td></tr>')
def sup_table(hid, heading, entries):
    if not entries:
        return (f'  <section class="pub-section" id="{hid}" aria-labelledby="h-{hid}">\n    <h2 id="h-{hid}">{heading} <span class="count-pill">0</span></h2>\n'
                f'    <p class="muted">No entries yet (generated from <code>supervision.bib</code> in the CV repository).</p>\n  </section>')
    return f'''  <section class="pub-section" id="{hid}" aria-labelledby="h-{hid}">
    <h2 id="h-{hid}">{heading} <span class="count-pill">{len(entries)}</span></h2>
    <div class="table-wrap"><table class="data"><caption class="visually-hidden">{heading}</caption>
      <thead><tr><th scope="col">Period</th><th scope="col">Title &amp; student</th><th scope="col">Role</th><th scope="col">Institution</th><th scope="col">Status</th><th scope="col">Projects</th><th scope="col">Links</th></tr></thead>
      <tbody>
{chr(10).join(sup_row(e) for e in entries)}
      </tbody></table></div>
  </section>'''
G = [('phd', 'PhD theses', 'phdthesis'), ('msc', 'MSc theses', 'mathesis'), ('scholarships', 'Research scholarships', 'scholarship')]
by = {t: sorted([e for e in SUP.values() if e.get('type') == t], key=lambda e: e.get('date', ''), reverse=True) for _, _, t in G}
body = ('\n'.join(sup_table(h, t, by[k]) for h, t, k in G))
open(os.path.join(OUT, 'supervision.html'), 'w').write(page_shell('Supervision', 'supervision.html', body, 'Theses and scholarships supervised by Pedro Rito.', wide=True,
    intro=('' if SUP else '  <p class="sample-banner"><strong>Preview.</strong> <code>supervision.bib</code> does not exist in the CV repository yet, so the tables are empty.</p>\n'),
    sections=[(f'#{h}', t, len(by[k])) for h, t, k in G]))

# ---------- bib/<key>.bib: per-entry BibTeX re-emitted with STANDARD fields only ----------
# Never the raw CV files: custom fields (projects, award, pubstate, keywords, note, …) and % comments are dropped.
PUBLIC = ['author', 'title', 'journal', 'booktitle', 'publisher', 'volume', 'number', 'pages', 'eid', 'date', 'location', 'doi', 'url', 'issn', 'isbn']
os.makedirs(os.path.join(OUT, 'bib'), exist_ok=True)
for k in pubs_listed:
    e = P[k]; fs = ',\n'.join(f'  {f} = {{{e[f]}}}' for f in PUBLIC if e.get(f))
    open(os.path.join(OUT, 'bib', k + '.bib'), 'w').write(f'@{e["_type"]}{{{k},\n{fs}\n}}\n')
print('projects.html:', len(on), '+', len(fin), '| supervision.html entries:', len(SUP), '| bib files:', len(pubs_listed))
