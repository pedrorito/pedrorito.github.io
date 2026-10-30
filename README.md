# pedrorito.github.io
## Adding a page (shared nav + section chips)

Every page is rendered by one shared shell in `site/make_samples.py`, so a new page gets the same top menu,
theme toggle, section "chips" menu and footer automatically:

- `page_shell(title, cur, body, desc, wide=False, intro='', sections=None)` renders the full page.
- `chip_nav(items, label)` renders the in-page section menu (`<nav class="chips">`, the single `.chips` CSS class).
  It wraps onto the next line on phones and never scrolls sideways. `page_shell` calls it for you when you pass
  `sections=[('#id', 'Label', count_or_None), ...]`.

To add `new.html`: build its `body` (sections with `id="..."`) in `site/subpages.py`, write it with
`page_shell('Title', 'new.html', body, 'Meta description', sections=[...])`, and add `('new.html', 'Title')`
to `NAV_ITEMS` in `make_samples.py`.

Homepage ("technical" look): plain text, thin rules, big numerals for the counts; contact links are plain text
(`site/home.yml` → `contact`). Homepage-only CSS is scoped under `body.home` in `style.css`.

Supervision: only the `supervision.bib` types listed under `supervision: types:` in `site/publications.yml`
(default: PhD + MSc theses) appear on the site; other types (BSc, internships, scholarships, …) stay CV-only.

Favicon: `site/favicon/` (SVG adapts to light/dark tabs; 16/32 PNG, 180 apple-touch-icon and .ico generated from it).
The generator copies these files to the site root; `<link rel="icon">` tags are in the shared head (THEME_HEAD) of every page.
All pages use the HTML title "Pedro Rito"; external links in the homepage Contact section and "Outside the lab" line open in a new tab.
