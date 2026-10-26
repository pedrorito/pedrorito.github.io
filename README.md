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

Contact links on the homepage (`site/home.yml`) get an inline SVG icon (`site/icons.py`, simple-icons CC0 +
hand-made); set `icon:` per link to override the automatic detection from the URL domain.
