"""Tiny dependency-free BibTeX reader (prototype; production would use bibtexparser/pybtex)."""
import re
def parse(path):
    txt=open(path,encoding='utf-8').read()
    txt='\n'.join(l for l in txt.splitlines() if not l.lstrip().startswith('%'))
    out={}
    for m in re.finditer(r'@(\w+)\s*\{\s*([^,\s]+)\s*,',txt):
        typ,key=m.group(1).lower(),m.group(2)
        i=m.end(); depth=1; j=i
        while depth and j<len(txt):
            depth+= {'{':1,'}':-1}.get(txt[j],0); j+=1
        body=txt[i:j-1]; f={}
        k=0
        while True:
            fm=re.compile(r'\s*(\w+)\s*=\s*').match(body,k)
            if not fm: break
            name=fm.group(1).lower(); k=fm.end()
            if body[k]=='{':
                d=0; s=k
                while True:
                    d+={'{':1,'}':-1}.get(body[k],0); k+=1
                    if d==0: break
                val=body[s+1:k-1]
            else:
                e=re.compile(r'[^,]*').match(body,k); val=e.group(0).strip(); k=e.end()
            f[name]=re.sub(r'\s+',' ',val).strip()
            c=re.compile(r'\s*,?').match(body,k); k=c.end()
        f['_type']=typ; f['_key']=key; out[key]=f
    return out
def clean(s):
    s=s.replace('\\&','&').replace('{\\textasciitilde}','~').replace('--','–')
    return re.sub(r'[{}]','',s)

# ---- LaTeX -> HTML (titles, venues, bio). Escape first, then translate the macros actually used in the CV.
import html as _html
_SYM = [(r'\textmu', 'µ'), (r'\textohm', 'Ω'), (r'\textquoteright', '’'), (r'\textquoteleft', '‘'),
        (r'\textasciitilde', '~'), (r'\textdegree', '°'), (r'\texttimes', '×'), (r'\euro', '€'), (r'\ldots', '…'),
        (r'\%', '%'), (r'\_', '_'), (r'\#', '#'), (r'\$', '$')]
_MATH = [(r'\sqrt{\mathrm{Hz}}', '√Hz'), (r'\sqrt{Hz}', '√Hz'), ('&lt;', '&lt;'), ('&gt;', '&gt;'), ('-', '−'),
         (r'\times', '×'), (r'\mu', 'µ'), (r'\Omega', 'Ω'), (r'\pm', '±'), (r'\leq', '≤'), (r'\geq', '≥')]
def latex2html(s):
    if not s: return ''
    s = _html.escape(s, quote=False)
    s = s.replace('\\&amp;', '&amp;')
    def math(m):
        t = m.group(1)
        for a, b in _MATH: t = t.replace(a, b)
        t = re.sub(r'\^\{?([^{}])\}?', r'<sup>\1</sup>', t); t = re.sub(r'_\{?([^{}])\}?', r'<sub>\1</sub>', t)
        t = re.sub(r'\\mathrm\{([^{}]*)\}', r'\1', t)
        return t.replace('{', '').replace('}', '')
    s = re.sub(r'\$([^$]*)\$', math, s)
    s = re.sub(r'\\href\{([^{}]*)\}\{([^{}]*)\}', lambda m: f'<a href="{m.group(1)}">{m.group(2)}</a>', s)
    s = re.sub(r'\\url\{([^{}]*)\}', r'<a href="\1">\1</a>', s)
    for mac, tag in (('textsuperscript', 'sup'), ('textsubscript', 'sub'), ('textbf', 'strong'), ('emph', 'em'), ('textit', 'em')):
        s = re.sub(r'\\' + mac + r'\{([^{}]*)\}', rf'<{tag}>\1</{tag}>', s)
    for a, b in _SYM: s = s.replace('{' + a + '}', b).replace(a + '{}', b).replace(a, b)
    s = s.replace('---', '—').replace('--', '–').replace('~', '&nbsp;').replace("''", '”').replace('``', '“')
    s = re.sub(r'\\[a-zA-Z]+\s*', '', s)    # drop any unknown macro name, keep its argument text
    return re.sub(r'[{}]', '', s).strip()
