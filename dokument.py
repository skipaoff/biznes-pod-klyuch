# -*- coding: utf-8 -*-
"""Документ шага: идея, картинки, выводы и сам текст.

Перенесено из «Агента сайтов» (doc_page.py). Документ лежит в
dokumenty/<экран>/NN-имя.md, картинки к нему описаны в shagi/<экран>.json
полем viz. Экран разворачивает документ прямо на месте шага, а по желанию его
можно собрать и отдельной страницей:

    python3 dokument.py 03-video 3     →  build/Документ-03-video-03.html

Чего не делает:
1. Ничего не дописывает от себя: что в документе, то и на странице.
2. Не решает, какой документ показать: берёт тот, что указан у шага.
"""
import io
import json
import os
import re
import sys
from string import Template

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
BUILD = os.path.join(HERE, "build")

MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}


def data_uri(path):
    """Картинка уезжает в страницу целиком, ссылками артефакт не грузит."""
    import base64
    full = path if os.path.isabs(path) else os.path.join(ROOT, path)
    if not os.path.exists(full):
        return None
    mime = MIME.get(os.path.splitext(full)[1].lower())
    if not mime:
        return None
    return "data:" + mime + ";base64," + base64.b64encode(io.open(full, "rb").read()).decode("ascii")


def esc(v):
    s = "" if v is None else str(v)
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def inline(s):
    """Жирный, курсив, код и ссылки внутри строки."""
    s = esc(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    return s


def md(text):
    """Достаточный markdown: заголовки, списки, таблицы, цитаты, разделители."""
    out, i = [], 0
    lines = text.split("\n")
    n = len(lines)
    while i < n:
        line = lines[i].rstrip()

        if not line.strip():
            i += 1
            continue

        if line.startswith("|") and i + 1 < n and set(lines[i + 1].replace("|", "").strip()) <= set("-: "):
            head = [c.strip() for c in line.strip("|").split("|")]
            i += 2
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            th = "".join("<th>" + inline(c) + "</th>" for c in head)
            tb = "".join("<tr>" + "".join("<td>" + inline(c) + "</td>" for c in r) + "</tr>" for r in rows)
            out.append('<div class="tw"><table><thead><tr>' + th + "</tr></thead><tbody>" + tb + "</tbody></table></div>")
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            lvl = min(len(m.group(1)), 4)
            out.append("<h%d>%s</h%d>" % (lvl, inline(m.group(2)), lvl))
            i += 1
            continue

        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", line.strip()):
            out.append("<hr>")
            i += 1
            continue

        if line.lstrip().startswith(">"):
            buf = []
            while i < n and lines[i].lstrip().startswith(">"):
                buf.append(lines[i].lstrip()[1:].strip())
                i += 1
            out.append("<blockquote>" + "<br>".join(inline(b) for b in buf if b) + "</blockquote>")
            continue

        if re.match(r"^\s*[-*]\s+", line):
            items = []
            while i < n and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append(re.sub(r"^\s*[-*]\s+", "", lines[i].rstrip()))
                i += 1
            out.append("<ul>" + "".join("<li>" + inline(x) + "</li>" for x in items) + "</ul>")
            continue

        if re.match(r"^\s*\d+[.)]\s+", line):
            items = []
            start = int(re.match(r"^\s*(\d+)", line).group(1))
            while i < n and re.match(r"^\s*\d+[.)]\s+", lines[i]):
                items.append(re.sub(r"^\s*\d+[.)]\s+", "", lines[i].rstrip()))
                i += 1
            out.append(("<ol>" if start == 1 else '<ol start="%d">' % start)
                       + "".join("<li>" + inline(x) + "</li>" for x in items) + "</ol>")
            continue

        buf = []
        while i < n and lines[i].strip() and not re.match(r"^(#{1,6}\s|\s*[-*]\s|\s*\d+[.)]\s|\||>)", lines[i]):
            buf.append(lines[i].strip())
            i += 1
        if buf:
            out.append("<p>" + inline(" ".join(buf)) + "</p>")
    return "\n".join(out)




def viz_html(v):
    """Картинка этапа. Что описано в прогоне, то и рисуем, ничего не выдумываем."""
    if not v:
        return ""
    kind = v.get("type")
    head = '<span class="lab">' + esc(v.get("title", "")) + '</span>'
    note = ('<p class="vnote">' + esc(v["note"]) + '</p>') if v.get("note") else ""
    out = ""

    if kind == "scales":
        def col(side, mark, cls):
            lis = "".join('<li><i class="' + cls + '">' + mark + '</i>' + esc(x) + '</li>'
                          for x in side.get("items", []))
            return ('<div class="scol"><span class="slab">' + esc(side.get("label", ""))
                    + '</span><ul>' + lis + '</ul></div>')
        if v.get("neutral"):
            out = ('<div class="scales">' + col(v["left"], "&#9679;", "dot")
                   + col(v["right"], "&#9679;", "dot") + '</div>')
        else:
            out = ('<div class="scales">' + col(v["left"], "&#10003;", "yes")
                   + col(v["right"], "&#10005;", "no") + '</div>')

    elif kind == "bars":
        mx = max([x.get("v") or 0 for x in v["items"]] + [1])
        rows = []
        for x in v["items"]:
            val = x.get("v") or 0
            w = int(round(val * 100.0 / mx)) if val else 0
            label = (format(val, ",d").replace(",", " ") + " " + esc(v.get("unit", ""))) if val else "нет цены"
            rows.append('<div class="bar' + (' hl' if x.get("hl") else "") + (' none' if not val else "") + '">'
                        '<span class="bname">' + esc(x["name"]) + '</span>'
                        '<span class="btrack"><i style="--w:' + str(w) + '%"></i></span>'
                        '<span class="bval">' + label + '</span>'
                        + ('<span class="bsub">' + esc(x["sub"]) + '</span>' if x.get("sub") else "")
                        + '</div>')
        out = '<div class="bars">' + "".join(rows) + '</div>'

    elif kind == "persons":
        cards = []
        for x in v["items"]:
            cards.append('<div class="person' + (' hl' if x.get("hl") else "") + '">'
                         '<span class="pshare" style="--p:' + str(x.get("share", 0)) + '%">'
                         + str(x.get("share", 0)) + '%</span>'
                         '<h4>' + esc(x["name"]) + '</h4>'
                         '<span class="pwho">' + esc(x.get("who", "")) + '</span>'
                         '<p>' + esc(x.get("text", "")) + '</p>'
                         '<span class="pmoney">' + esc(x.get("money", "")) + '</span>'
                         '</div>')
        out = '<div class="persons">' + "".join(cards) + '</div>'

    elif kind == "ladder":
        rows = []
        for i, x in enumerate(v["items"]):
            rows.append('<div class="lstep' + (' hot' if x.get("hot") else "") + '"'
                        ' style="--i:' + str(i) + '">'
                        '<span class="lpct">' + str(x.get("pct", 0)) + '%</span>'
                        '<span class="lname">' + esc(x["name"]) + '</span>'
                        '<span class="lthink">' + esc(x.get("think", "")) + '</span>'
                        '</div>')
        out = '<div class="ladder">' + "".join(rows) + '</div>'

    elif kind == "price":
        parts = "".join('<div class="ppart"><span>' + esc(p["name"] if isinstance(p, dict) else p) + '</span>'
                        '<b>' + (format(p["v"], ",d").replace(",", " ") + " грн" if isinstance(p.get("v"), int) else esc(p.get("v", ""))) + '</b></div>'
                        for p in v.get("parts", []))
        extra = "".join('<li><span>' + esc(e["name"]) + '</span><b>' + esc(str(e["v"])) + '</b></li>'
                        for e in v.get("extra", []))
        cmp_ = v.get("compare") or {}
        out = ('<div class="price"><div class="ptotal"><span class="lab">всё вместе</span>'
               '<b>' + esc(v.get("total", "")) + '</b></div>'
               '<div class="pparts">' + parts + '</div>'
               + ('<ul class="pextra">' + extra + '</ul>' if extra else "")
               + ('<div class="pcmp"><span>' + esc(cmp_.get("name", "")) + '</span>'
                  '<b>' + esc(str(cmp_.get("v", ""))) + '</b>'
                  + ('<i>' + esc(cmp_["note"]) + '</i>' if cmp_.get("note") else "")
                  + '</div>' if cmp_ else "")
               + '</div>')

    elif kind == "map":
        leaves = "".join('<li style="--i:' + str(i) + '">' + esc(x) + '</li>'
                         for i, x in enumerate(v.get("items", [])))
        out = ('<div class="smap"><div class="sroot">' + esc(v.get("root", "")) + '</div>'
               '<ul class="sleaves">' + leaves + '</ul></div>')


    elif kind == "stat":
        cards = "".join('<div class="statc"><b>' + esc(x["v"]) + '</b><span>' + esc(x["t"]) + '</span>'
                        + ('<i>' + esc(x["sub"]) + '</i>' if x.get("sub") else "") + '</div>'
                        for x in v.get("items", []))
        out = '<div class="stats">' + cards + '</div>'

    elif kind == "quotes":
        cards = "".join('<figure class="quote"><blockquote>' + esc(x["q"]) + '</blockquote>'
                        + ('<figcaption>' + esc(x["who"]) + '</figcaption>' if x.get("who") else "")
                        + '</figure>' for x in v.get("items", []))
        out = '<div class="quotes">' + cards + '</div>'

    elif kind == "split":
        rows = "".join('<div class="sp" style="--p:' + str(x["pct"]) + '%">'
                       '<span class="spn">' + esc(x["name"]) + '</span>'
                       '<span class="spb"><i></i></span>'
                       '<span class="spp">' + str(x["pct"]) + '%</span></div>'
                       for x in v.get("items", []))
        out = '<div class="splits">' + rows + '</div>'

    elif kind == "steps":
        rows = "".join('<div class="stp" style="--i:' + str(i) + '">'
                       '<span class="stpn">' + ("%02d" % (i + 1)) + '</span>'
                       '<span class="stpt">' + esc(x) + '</span></div>'
                       for i, x in enumerate(v.get("items", [])))
        out = '<div class="stpwrap">' + rows + '</div>'

    elif kind == "matrix":
        cols = v.get("cols", [])
        # имя переменной раньше совпадало с заголовком блока и затирало его
        thead = "".join('<th>' + esc(c) + '</th>' for c in cols)
        rows = []
        for r in v.get("rows", []):
            cells = []
            for c in r.get("cells", []):
                if c is True:
                    cells.append('<td class="mok">&#10003;</td>')
                elif c is False:
                    cells.append('<td class="mno">&#10005;</td>')
                else:
                    cells.append('<td>' + esc(str(c)) + '</td>')
            rows.append('<tr><th class="mrow">' + esc(r["name"]) + '</th>' + "".join(cells) + '</tr>')
        out = ('<div class="tw matrix"><table><thead><tr><th></th>' + thead + '</tr></thead>'
               '<tbody>' + "".join(rows) + '</tbody></table></div>')


    elif kind == "frames":
        cards = []
        for i, x in enumerate(v.get("items", []), 1):
            uri = data_uri(x.get("img", ""))
            pic = ('<img src="' + uri + '" alt="' + esc(x.get("title", "")) + '">') if uri else ""
            cards.append('<figure class="frame" style="--i:' + str(i - 1) + '">'
                         '<div class="fpic">' + pic
                         + '<span class="fno">кадр ' + str(i) + '</span>'
                         + ('<span class="fsec">' + esc(x["sec"]) + '</span>' if x.get("sec") else "")
                         + '</div>'
                         '<figcaption><b>' + esc(x.get("title", "")) + '</b>'
                         + ('<span class="fmove">' + esc(x["move"]) + '</span>' if x.get("move") else "")
                         + ('<span class="ftext">' + esc(x["text"]) + '</span>' if x.get("text") else "")
                         + '</figcaption></figure>')
        out = '<div class="frames">' + "".join(cards) + '</div>'

    elif kind == "leaks":
        rows = "".join('<div class="leak"><span class="lwho">' + esc(x.get("who", "")) + '</span>'
                       '<b>' + esc(x["name"]) + '</b>'
                       '<span class="lfix">' + esc(x.get("fix", "")) + '</span></div>'
                       for x in v.get("items", []))
        out = '<div class="leaks">' + rows + '</div>'

    elif kind == "dialog":
        rows = []
        for i, x in enumerate(v.get("items", [])):
            side = "me" if x.get("from") in ("bot", "me", "он") else "them"
            rows.append('<div class="msg ' + side + '" style="--i:' + str(i) + '">'
                        + ('<span class="mwho">' + esc(x["who"]) + '</span>' if x.get("who") else "")
                        + '<p>' + esc(x.get("t", "")) + '</p></div>')
        out = '<div class="chat">' + "".join(rows) + '</div>'

    elif kind == "timeline":
        total = sum(float(x.get("w", 1)) for x in v.get("items", [])) or 1.0
        segs, rows = [], []
        for i, x in enumerate(v.get("items", [])):
            w = float(x.get("w", 1)) * 100.0 / total
            segs.append('<i class="tseg' + (' hl' if x.get("hl") else "") + '" style="--w:%.2f%%"><b>%s</b></i>'
                        % (w, esc(x.get("t", ""))))
            rows.append('<div class="trow"><span class="tt">' + esc(x.get("t", "")) + '</span>'
                        '<b>' + esc(x.get("name", "")) + '</b>'
                        + ('<span class="tx">' + esc(x["text"]) + '</span>' if x.get("text") else "")
                        + '</div>')
        out = ('<div class="tline"><div class="tbar">' + "".join(segs) + '</div>'
               '<div class="trows">' + "".join(rows) + '</div></div>')

    return '<section class="viz reveal">' + head + out + note + '</section>'


def viz_all(v):
    """На этап может быть одна картинка или несколько подряд."""
    if not v:
        return ""
    if isinstance(v, dict):
        v = [v]
    return "".join(viz_html(x) for x in v)



def idea_html(idea):
    """Главная мысль этапа. Первое, что видно на странице, до всего остального."""
    if not idea:
        return ""
    return ('<section class="idea reveal"><span class="lab">идея шага</span>'
            '<h2>' + esc(idea.get("head", "")) + '</h2>'
            '<p>' + esc(idea.get("text", "")) + '</p></section>')


PAGE = Template("""<title>$title</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Unbounded:wght@600;700&family=Manrope:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{
  /* тёмная, но читаемая: панель светлее фона, текст почти белый,
     приглушённый цвет всё равно контрастный, иначе подписи не прочесть */
  --void:#080b10; --panel:#141b24; --raise:#1c2530; --line:#2c3743; --line-hot:#3e4c5c;
  --ink:#f3f7fb; --mid:#c6d3e0; --dim:#9aabbd; --neon:#4fe8cb; --amber:#ffc46b;
}
*{box-sizing:border-box}
body{margin:0;background:var(--void);color:var(--ink);
  font:20px/1.75 Manrope,system-ui,-apple-system,sans-serif;-webkit-font-smoothing:antialiased;color-scheme:dark;
  background-image:radial-gradient(1000px 560px at 80% -12%,rgba(79,232,203,.10),transparent 62%);
  background-attachment:fixed}
button{color:inherit;appearance:none}
.wrap{max-width:960px;margin:0 auto;padding:38px 22px 100px}
.lab{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:13px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--dim);font-weight:500}
.head{border:1px solid var(--line-hot);border-radius:20px;background:linear-gradient(160deg,#18212c,#0d141c);
  padding:26px 26px 24px;position:relative;overflow:hidden}
.head::after{content:"";position:absolute;inset:0;pointer-events:none;
  background:linear-gradient(115deg,transparent 45%,rgba(79,232,203,.07) 50%,transparent 55%)}
.head h1{font-family:Unbounded,Manrope,sans-serif;font-weight:700;letter-spacing:-.03em;
  font-size:clamp(30px,5.2vw,50px);line-height:1.05;margin:10px 0 0;text-transform:uppercase}
.by{margin-top:14px;display:flex;flex-wrap:wrap;gap:8px}
.by span{border:1px solid var(--line-hot);border-radius:999px;padding:9px 16px;font-size:16px;color:var(--mid)}
.by span b{color:var(--neon);font-weight:600}
.vyvod{margin-top:20px;border:1px solid rgba(79,232,203,.4);border-radius:18px;
  background:rgba(79,232,203,.07);padding:24px 28px}
.vyvod .lab{color:var(--neon)}
.vyvod ul{margin:14px 0 0;padding-left:22px}
.vyvod li{margin:11px 0;font-size:18.5px;color:var(--ink)}
.body{margin-top:26px;border:1px solid var(--line);border-radius:20px;background:var(--panel);
  padding:32px 34px 38px}
.body h1,.body h2,.body h3,.body h4{font-family:Unbounded,Manrope,sans-serif;letter-spacing:-.025em;
  line-height:1.15;margin:30px 0 10px;text-transform:uppercase}
.body h1{font-size:34px;color:var(--neon)}
.body h2{font-size:28px;color:var(--ink)}
.body h3{font-size:22px;color:var(--ink);text-transform:none;font-family:Manrope,sans-serif;font-weight:700}
.body h4{font-size:18px;color:var(--mid);text-transform:none;font-family:Manrope,sans-serif}
.body > *:first-child{margin-top:0}
.body p{margin:16px 0;color:var(--ink)}
.body b{color:var(--ink)}
.body i{color:var(--mid)}
.body code{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:16px;
  background:var(--raise);border:1px solid var(--line);border-radius:5px;padding:1px 6px;color:var(--neon)}
.body ul,.body ol{margin:12px 0;padding-left:22px;color:var(--ink)}
.body li{margin:10px 0}
.body blockquote{margin:16px 0;padding:12px 18px;border-left:3px solid var(--neon);
  background:var(--raise);border-radius:0 12px 12px 0;color:var(--ink)}
.body hr{border:0;border-top:1px solid var(--line);margin:26px 0}
.tw{overflow-x:auto;margin:16px 0;border:1px solid var(--line);border-radius:12px}
table{border-collapse:collapse;width:100%;font-size:17.5px;min-width:420px}
th{background:var(--raise);text-align:left;padding:15px 18px;color:var(--neon);font-weight:600;
  font-size:15px;letter-spacing:.02em;border-bottom:1px solid var(--line)}
td{padding:15px 18px;border-bottom:1px solid var(--line);color:var(--ink);vertical-align:top}
tr:last-child td{border-bottom:0}

/* ---- картинки этапа ---- */
.viz{margin-top:22px;border:1px solid var(--line);border-radius:20px;background:var(--panel);padding:30px 32px}
.viz > .lab{display:block;margin-bottom:22px;color:var(--neon);font-size:12.5px}
.vnote{margin:18px 0 0;font-size:16px;color:var(--dim)}
.reveal{opacity:0;transform:translateY(18px);transition:opacity .7s ease,transform .7s ease}
.reveal.on{opacity:1;transform:none}

.scales{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.scol{border:1px solid var(--line);border-radius:14px;background:var(--raise);padding:16px 18px}
.slab{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:13px;letter-spacing:.12em;
  text-transform:uppercase;color:var(--mid)}
.scol ul{list-style:none;margin:12px 0 0;padding:0;display:flex;flex-direction:column;gap:10px}
.scol li{display:flex;gap:12px;align-items:flex-start;font-size:17px;color:var(--ink)}
.scol i{font-style:normal;flex:0 0 18px;width:18px;height:18px;border-radius:50%;display:grid;
  place-items:center;font-size:10px;margin-top:2px}
.scol i.yes{background:rgba(79,232,203,.13);color:var(--neon)}
.scol i.no{background:rgba(255,138,122,.16);color:#ff8a7a}
.scol i.dot{background:rgba(79,232,203,.13);color:var(--neon);font-size:8px}

.bars{display:flex;flex-direction:column;gap:14px}
.bar{display:grid;grid-template-columns:150px 1fr auto;gap:12px;align-items:center}
.bname{font-weight:700;font-size:18px}
.btrack{height:22px;border-radius:999px;background:#0d141c;border:1px solid var(--line);overflow:hidden}
.btrack i{display:block;height:100%;width:0;border-radius:999px;
  background:linear-gradient(90deg,#41566b,#6f9cff);transition:width 1.1s cubic-bezier(.2,.9,.25,1)}
.on .btrack i{width:var(--w)}
.bar.hl .btrack i{background:linear-gradient(90deg,#15705f,var(--neon))}
.bar.hl .bname{color:var(--neon)}
.bval{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:19px;white-space:nowrap;font-weight:600}
.bsub{grid-column:2 / -1;font-size:15px;color:var(--dim);margin-top:-4px}
.bar.none .bval{color:var(--dim)}
.bar.none .btrack{border-style:dashed;opacity:.5}

.persons{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:14px}
.person{border:1px solid var(--line);border-radius:16px;background:var(--raise);padding:18px;position:relative}
.person.hl{border-color:rgba(79,232,203,.45);background:rgba(60,224,192,.05)}
.person h4{font-family:Manrope,sans-serif;text-transform:none;font-size:21px;margin:12px 0 3px;color:var(--ink)}
.pwho{font-size:15px;color:var(--dim)}
.person p{font-size:16px;color:var(--ink);margin:10px 0 14px}
.pmoney{display:inline-block;border:1px solid var(--line-hot);border-radius:999px;padding:8px 16px;
  font-family:'JetBrains Mono',ui-monospace,monospace;font-size:16px;color:var(--neon)}
.pshare{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:15px;color:var(--mid)}

.ladder{display:flex;flex-direction:column;gap:8px}
.lstep{display:grid;grid-template-columns:76px 1fr auto;gap:16px;align-items:center;
  border:1px solid var(--line);border-radius:14px;background:var(--raise);padding:19px 22px;
  margin-left:calc(var(--i) * 14px);transition:.5s}
.lstep.hot{border-color:rgba(79,232,203,.4);background:rgba(79,232,203,.05)}
.lpct{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:24px;color:var(--neon);font-weight:600}
.lstep:not(.hot) .lpct{color:var(--dim)}
.lname{font-weight:700;font-size:18px}
.lthink{font-size:16.5px;color:var(--mid);text-align:right}

.price{display:flex;flex-direction:column;gap:14px}
.ptotal{border:1px solid rgba(79,232,203,.4);border-radius:16px;background:rgba(79,232,203,.06);
  padding:20px 22px;text-align:center}
.ptotal b{display:block;font-family:Unbounded,Manrope,sans-serif;font-size:clamp(30px,6vw,52px);
  color:var(--neon);letter-spacing:-.03em;margin-top:6px}
.pparts{display:flex;gap:12px;flex-wrap:wrap}
.ppart{flex:1 1 180px;border:1px solid var(--line);border-radius:14px;background:var(--raise);padding:15px 17px}
.ppart span{display:block;font-size:16px;color:var(--mid)}
.ppart b{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:26px;color:var(--ink)}
.pextra{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:9px}
.pextra li{display:flex;justify-content:space-between;gap:12px;font-size:17px;color:var(--ink);
  border-bottom:1px dashed var(--line);padding-bottom:9px}
.pextra b{color:var(--neon);font-family:'JetBrains Mono',ui-monospace,monospace;font-size:14px}
.pcmp{border:1px dashed var(--line-hot);border-radius:14px;padding:15px 17px}
.pcmp span{font-size:17px;color:var(--mid)}
.pcmp b{display:block;font-family:'JetBrains Mono',ui-monospace,monospace;font-size:21px;color:#a8600c;margin-top:4px}
.pcmp i{display:block;font-size:15.5px;color:var(--dim);margin-top:7px}

.smap .sroot{display:inline-block;border:1px solid rgba(79,232,203,.45);background:rgba(79,232,203,.07);
  border-radius:999px;padding:13px 28px;color:var(--neon);font-weight:700;font-size:19px}
.sleaves{list-style:none;margin:14px 0 0;padding:0 0 0 18px;display:flex;flex-wrap:wrap;gap:9px;
  border-left:1px solid var(--line)}
.sleaves li{border:1px solid var(--line);border-radius:12px;background:var(--raise);padding:13px 18px;
  font-size:17px;color:var(--ink);opacity:0;transform:translateX(-8px);
  transition:opacity .5s ease,transform .5s ease;transition-delay:calc(var(--i) * 60ms)}
.on .sleaves li{opacity:1;transform:none}

.leaks{display:flex;flex-direction:column;gap:11px}
.leak{border:1px solid var(--line);border-radius:14px;background:var(--raise);padding:15px 17px}
.lwho{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:10.5px;letter-spacing:.12em;
  text-transform:uppercase;color:#a8600c}
.leak b{display:block;margin:9px 0 10px;font-size:19px}
.lfix{display:flex;gap:10px;font-size:17px;color:var(--neon)}
.lfix::before{content:"\2713"}

@media (max-width:640px){
  .scales{grid-template-columns:1fr}
  .bar{grid-template-columns:1fr auto;gap:8px}
  .btrack{grid-column:1 / -1;order:3}
  .bsub{order:4}
  .lstep{grid-template-columns:52px 1fr;margin-left:0}
  .lthink{grid-column:2;text-align:left;color:var(--dim)}
  .viz{padding:18px 16px}
}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px}
.statc{border:1px solid var(--line);border-radius:16px;background:var(--raise);padding:22px 20px;text-align:center}
.statc b{display:block;font-family:Unbounded,Manrope,sans-serif;font-size:clamp(30px,5vw,46px);
  color:var(--neon);letter-spacing:-.03em;line-height:1}
.statc span{display:block;margin-top:10px;font-size:18px;color:var(--ink)}
.statc i{display:block;margin-top:8px;font-size:15.5px;color:var(--dim);font-style:normal}

.quotes{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}
.quote{margin:0;border:1px solid var(--line);border-radius:16px;background:var(--raise);padding:44px 26px 22px;
  position:relative}
.quote::before{content:"“";position:absolute;top:6px;left:20px;font-size:44px;color:var(--neon);opacity:.45;
  font-family:Georgia,serif;line-height:1}
.quote blockquote{margin:0;padding:0;border:0;background:none;font-size:23px;line-height:1.5;color:var(--ink)}
.quote figcaption{margin-top:14px;font-size:16px;color:var(--dim)}

.splits{display:flex;flex-direction:column;gap:14px}
.sp{display:grid;grid-template-columns:1fr 2fr auto;gap:14px;align-items:center}
.spn{font-size:17px;font-weight:600}
.spb{height:20px;border-radius:999px;background:#0d141c;border:1px solid var(--line);overflow:hidden}
.spb i{display:block;height:100%;width:0;border-radius:999px;
  background:linear-gradient(90deg,#15705f,var(--neon));transition:width 1.1s cubic-bezier(.2,.9,.25,1)}
.on .spb i{width:var(--p)}
.spp{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:20px;color:var(--neon);font-weight:600}

.stpwrap{display:flex;flex-direction:column;gap:10px}
.stp{display:flex;gap:16px;align-items:center;border:1px solid var(--line);border-radius:14px;
  background:var(--raise);padding:16px 20px;opacity:0;transform:translateY(10px);
  transition:opacity .5s ease,transform .5s ease;transition-delay:calc(var(--i) * 70ms)}
.on .stp{opacity:1;transform:none}
.stpn{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:18px;color:var(--neon);flex:0 0 auto}
.stpt{font-size:19px;color:var(--ink)}

.matrix table{font-size:18px}
.matrix .mrow{background:var(--raise);text-align:left;color:var(--ink);font-weight:600;white-space:nowrap}
.matrix td{text-align:center}
.matrix .mok{color:var(--neon);font-size:19px}
.matrix .mno{color:#ff8a7a;font-size:19px}

@media (max-width:640px){
  .sp{grid-template-columns:1fr auto}
  .spb{grid-column:1 / -1;order:3}
  .viz{padding:20px 16px}
}

.frames{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:18px}
.frame{margin:0;opacity:0;transform:translateY(14px);
  transition:opacity .55s ease,transform .55s ease;transition-delay:calc(var(--i) * 90ms)}
.on .frame{opacity:1;transform:none}
.fpic{position:relative;border:1px solid var(--line-hot);border-radius:14px;overflow:hidden;
  background:#0d141c;aspect-ratio:16/9}
.fpic img{width:100%;height:100%;object-fit:cover;display:block}
.fno{position:absolute;left:12px;top:12px;font-family:'JetBrains Mono',ui-monospace,monospace;
  font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:#0b1016;
  background:var(--neon);border-radius:999px;padding:5px 11px;font-weight:600}
.fsec{position:absolute;right:12px;bottom:12px;font-family:'JetBrains Mono',ui-monospace,monospace;
  font-size:13px;color:#f3f7fb;background:rgba(8,11,16,.78);border-radius:999px;padding:5px 11px}
.frame figcaption{display:block;margin-top:14px}
.frame figcaption b{display:block;font-size:19px;color:var(--ink);margin-bottom:7px}
.fmove{display:block;font-size:15.5px;color:var(--neon);margin-bottom:6px}
.ftext{display:block;font-size:16px;color:var(--mid);line-height:1.55}

.chat{display:flex;flex-direction:column;gap:10px;max-width:640px}
.msg{max-width:82%;border:1px solid var(--line);border-radius:16px;padding:12px 16px;background:var(--raise)}
.msg p{margin:0;font-size:17px;line-height:1.5;color:var(--ink)}
.msg.them{align-self:flex-start;border-bottom-left-radius:4px}
.msg.me{align-self:flex-end;border-bottom-right-radius:4px;background:rgba(79,232,203,.10);
  border-color:rgba(79,232,203,.4)}
.mwho{display:block;font-family:'JetBrains Mono',ui-monospace,monospace;font-size:11.5px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--dim);margin-bottom:5px}
.msg.me .mwho{color:var(--neon)}

.tbar{display:flex;gap:4px;height:46px;margin-bottom:18px}
.tseg{display:flex;align-items:center;justify-content:center;flex:0 0 var(--w);min-width:0;
  border-radius:10px;background:#1f2b38;border:1px solid var(--line-hot);overflow:hidden}
.tseg.hl{background:rgba(79,232,203,.16);border-color:rgba(79,232,203,.5)}
.tseg b{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:13px;color:var(--mid);white-space:nowrap;
  font-weight:500}
.tseg.hl b{color:var(--neon)}
.trows{display:flex;flex-direction:column;gap:9px}
.trow{display:grid;grid-template-columns:96px 1fr;gap:4px 16px;border-bottom:1px dashed var(--line);padding-bottom:9px}
.trow:last-child{border:0}
.tt{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:15px;color:var(--neon)}
.trow b{font-size:17.5px}
.tx{grid-column:2;font-size:15.5px;color:var(--mid)}
@media (max-width:640px){
  .msg{max-width:94%}
  .tseg b{font-size:10.5px}
  .trow{grid-template-columns:70px 1fr}
}

.idea{margin-top:22px;border:1px solid rgba(79,232,203,.45);border-radius:20px;
  background:linear-gradient(150deg,rgba(79,232,203,.10),rgba(79,232,203,.03));
  padding:32px 34px}
.idea > .lab{display:block;color:var(--neon);margin-bottom:14px}
.idea h2{font-family:Unbounded,Manrope,sans-serif;font-weight:700;letter-spacing:-.03em;
  font-size:clamp(23px,3.4vw,34px);line-height:1.15;margin:0;text-transform:uppercase;color:var(--ink)}
.idea p{margin:16px 0 0;font-size:clamp(17px,1.9vw,21px);line-height:1.6;color:var(--mid);max-width:62ch}
@media (max-width:640px){ .idea{padding:22px 18px} }

.foot{margin-top:28px;display:flex;flex-wrap:wrap;gap:10px 20px;color:var(--dim);font-size:16px;
  border-top:1px solid var(--line);padding-top:16px}
@media (max-width:600px){
  .wrap{padding:22px 14px 70px}
  .head{padding:20px 17px;border-radius:15px}
  .body{padding:20px 17px;border-radius:15px}
  body{font-size:16px}
}
</style>
<div class="wrap">
  <header class="head">
    <span class="lab">шаг $no из $total · $who</span>
    <h1>$title</h1>
    <div class="by">$meta</div>
  </header>
  $idea
  $viz
  $vyvod
  <article class="body">$body</article>
  <footer class="foot">$foot</footer>
</div>
<script>
(function(){
  var els = document.querySelectorAll('.reveal');
  if(!('IntersectionObserver' in window)){
    for(var i=0;i<els.length;i++) els[i].classList.add('on');
    return;
  }
  var io = new IntersectionObserver(function(rows){
    rows.forEach(function(r){ if(r.isIntersecting){ r.target.classList.add('on'); io.unobserve(r.target); } });
  }, {threshold: .2});
  els.forEach(function(e){ io.observe(e); });
})();
</script>
""")


def doc_path(step):
    """Файл документа шага: путь от папки скилла, как записан в состоянии."""
    doc = step.get("doc") or {}
    rel = doc.get("path") if isinstance(doc, dict) else doc
    if not rel:
        return None
    full = rel if os.path.isabs(rel) else os.path.join(HERE, rel)
    return full if os.path.exists(full) else None


def vyvod_html(step):
    items = [x if isinstance(x, str) else x.get("t", "") for x in (step.get("items") or [])]
    items = [x for x in items if x]
    if not items:
        return ""
    return ('<section class="vyvod"><span class="lab">что из этого следует</span><ul>'
            + "".join('<li>' + esc(x) + '</li>' for x in items[:6]) + '</ul></section>')


def main():
    if len(sys.argv) < 3:
        sys.exit("укажи экран и номер шага: python3 dokument.py 03-video 3")
    name, no = sys.argv[1], int(sys.argv[2])
    d = json.loads(io.open(os.path.join(HERE, "shagi", name + ".json"), encoding="utf-8").read())
    steps = d.get("steps", [])
    if not 1 <= no <= len(steps):
        sys.exit("шага %d нет, всего %d" % (no, len(steps)))
    step = steps[no - 1]
    path = doc_path(step)
    raw = io.open(path, encoding="utf-8").read() if path else ""
    team = d.get("team", [])
    who = team[step["who"]]["name"] if isinstance(step.get("who"), int) and step["who"] < len(team) else "агент"
    meta = "".join('<span><b>%s</b> %s</span>' % (esc(n.get("v", "")), esc(n.get("t", "")))
                   for n in (step.get("nums") or [])[:4])
    html = PAGE.substitute(
        no="%02d" % no, total="%02d" % len(steps), who=esc(who),
        title=esc(step.get("title", "")), meta=meta,
        idea=idea_html(step.get("idea")), viz=viz_all(step.get("viz")),
        vyvod=vyvod_html(step), body=md(raw),
        foot='<span>%s</span>' % esc(d.get("title", "")))
    os.makedirs(BUILD, exist_ok=True)
    out = os.path.join(BUILD, "Документ-%s-%02d.html" % (name, no))
    io.open(out, "w", encoding="utf-8").write(html)
    print(out)


def doc_css():
    """Стили документа с префиксом, чтобы не спорить со стилями экрана."""
    css = PAGE.template
    start = css.index("<style>") + len("<style>")
    end = css.index("</style>")
    body = css[start:end]
    # выкидываем правила, которые относятся к странице целиком
    body = re.sub(r":root\{[^}]*\}", "", body)
    body = re.sub(r"\*\{[^}]*\}", "", body)
    body = re.sub(r"body\{[^}]*\}", "", body)
    body = re.sub(r"button\{[^}]*\}", "", body)
    body = re.sub(r"\.wrap\{[^}]*\}", "", body)
    body = re.sub(r"\.head[^{]*\{[^}]*\}", "", body)
    body = re.sub(r"\.by[^{]*\{[^}]*\}", "", body)
    body = re.sub(r"\.foot[^{]*\{[^}]*\}", "", body)

    out = []
    for chunk in re.split(r"(@media[^{]*\{)", body):
        if chunk.startswith("@media"):
            out.append(chunk)
            continue
        # префиксуем каждый селектор
        def pref(m):
            sels = m.group(1)
            parts = [s.strip() for s in sels.split(",") if s.strip()]
            return ", ".join(".indoc " + s for s in parts) + "{"
        out.append(re.sub(r"([^{}@]+)\{", pref, chunk))
    css = "".join(out)
    # внутри экрана прогона нет наблюдателя прокрутки, поэтому состояния
    # появления схлопываем в готовые: иначе блоки прозрачные, столбики нулевые
    css = css.replace(".indoc .on ", ".indoc ")
    css = css.replace("opacity:0;transform:translateY(18px)", "opacity:1;transform:none")
    css = css.replace("opacity:0;transform:translateY(14px)", "opacity:1;transform:none")
    css = css.replace("opacity:0;transform:translateY(10px)", "opacity:1;transform:none")
    css = css.replace("opacity:0;transform:translateX(-8px)", "opacity:1;transform:none")
    css = css.replace("width:0;border-radius:999px", "width:var(--w,100%);border-radius:999px")
    return css


def doc_inline(step):
    """Содержимое документа шага для экрана: идея, картинки, выводы и текст."""
    path = doc_path(step)
    raw = io.open(path, encoding="utf-8").read() if path else ""
    if not (raw or step.get("idea") or step.get("viz")):
        return ""
    return ('<div class="indoc">'
            + idea_html(step.get("idea"))
            + viz_all(step.get("viz"))
            + vyvod_html(step)
            + ('<article class="body">' + md(raw) + '</article>' if raw else "")
            + '</div>')


if __name__ == "__main__":
    main()
