# -*- coding: utf-8 -*-
"""Собирает экран работы из состояния — один HTML-файл под артефакт.

Вид взят из «Агента сайтов»: сверху пиксельный офис, где за компьютер садится
тот, чей шаг идёт, под ним команда, дальше один шаг крупно. Пока шаг в работе,
видно, что агент сказал, беря его в руки, и саму работу: живую картинку и
строчки, которые проявляются по одной. Когда шаг готов, на его месте реплика с
итогом, документ шага (идея, картинки, выводы, текст), цифры и находки.

Состояние лежит в shagi/<экран>.json, документы шагов — в dokumenty/<экран>/,
готовая страница — в build/. Скилл двигает состояние через shag.py и
публикует страницу через инструмент Artifact по тому же пути: адрес не
меняется, страница дорастает прямо на глазах.

Запуск:  python3 ekran.py 01-sajt

Чего он не делает:
1. Ничего не придумывает: что в состоянии, то и на экране.
2. Не решает, какой шаг пройден: статусы ставит shag.py.
3. Не тянет ничего из сети, кроме шрифтов: картинки уезжают в страницу целиком.
"""
import base64
import io
import json
import os
import struct
import sys
from string import Template

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dokument  # noqa: E402
import ofis  # noqa: E402

LICA = os.path.join(HERE, "lica")
BUILD = os.path.join(HERE, "build")

IMYA = {"01-sajt": "Сайт.html", "02-prodavec": "Продавец.html",
        "03-video": "Ролик.html", "04-reklama": "Реклама.html"}

ST = {"done": "готово", "run": "в работе", "wait": "ждёт"}
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".webp": "image/webp", ".mp4": "video/mp4"}


def esc(v):
    s = "" if v is None else str(v)
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def kartinka(src):
    """Файл уезжает в страницу целиком: внешних адресов артефакт не пустит."""
    if not src:
        return ""
    if src.startswith("data:") or src.startswith("http"):
        return src
    path = src if os.path.isabs(src) else os.path.join(HERE, src)
    if not os.path.exists(path):
        return ""
    mime = MIME.get(os.path.splitext(path)[1].lower(), "image/jpeg")
    return ("data:%s;base64," % mime) + base64.b64encode(io.open(path, "rb").read()).decode("ascii")


def lico(name):
    return kartinka(os.path.join(LICA, name)) if name else ""


def storony(src):
    """Ширина и высота картинки, чтобы плитка не прыгала, пока грузится."""
    path = src if os.path.isabs(src) else os.path.join(HERE, src)
    if not os.path.exists(path):
        return None
    head = io.open(path, "rb").read(64)
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", head[16:24])
    if head[:2] == b"\xff\xd8":
        f = io.open(path, "rb")
        f.read(2)
        while True:
            b = f.read(1)
            if not b:
                return None
            if b != b"\xff":
                continue
            m = f.read(1)
            while m == b"\xff":
                m = f.read(1)
            if m in b"\xc0\xc1\xc2\xc3\xc5\xc6\xc7\xc9\xca\xcb\xcd\xce\xcf":
                f.read(3)
                h, w = struct.unpack(">HH", f.read(4))
                return w, h
            ln = struct.unpack(">H", f.read(2))[0]
            f.read(ln - 2)
    return None


# ---------- команда ----------

def first_step(steps, k):
    for i, s in enumerate(steps, 1):
        if s.get("who") == k:
            return i
    return None


def team_html(team, steps):
    """Команда под офисом. По тому, кто уже брался за работу, можно нажать:
    откроется его шаг со всем, что он сделал."""
    if not team:
        return ""
    cells = []
    for k, m in enumerate(team):
        st = m.get("status", "wait")
        face = lico(m.get("img"))
        pod = ('<span class="pod"><img class="face" src="%s" alt=""><i class="tick"></i></span>' % face
               if face else '<span class="pod"><i class="tick"></i></span>')
        inside = pod + '<span class="mname">' + esc(m.get("name", "")) + '</span>'
        n = first_step(steps, k)
        if n and st in ("done", "run"):
            cells.append('<li class="mate hot" data-s="%s" data-go="%d" title="%s">%s'
                          '<span class="mopen">показать работу</span></li>'
                          % (esc(st), n, esc(m.get("role", "")), inside))
        else:
            cells.append('<li class="mate" data-s="%s" title="%s">%s</li>'
                         % (esc(st), esc(m.get("role", "")), inside))
    return '<section class="team"><ul class="mates">' + "".join(cells) + '</ul></section>'


# ---------- куски шага ----------

def rabota(vid):
    """Маленькая живая картинка того, что человек делает прямо сейчас."""
    n = lambda k: "<i></i>" * k
    m = {
        "skan":    '<div class="br"><span class="dots">%s</span></div><div class="ln">%s</div>'
                   '<span class="scan"></span>' % (n(3), n(7)),
        "spisok":  '<div class="rows">%s</div>' % ("<div><b></b><u></u></div>" * 4),
        "pechat":  '<div class="type">%s<span class="car"></span></div>' % n(4),
        "bloki":   '<div class="lay">%s</div>' % n(5),
        "ekrany":  '<div class="dev desk"><span></span></div><div class="dev mob"><span></span></div>',
        "plitki":  '<div class="tiles">%s</div>' % n(5),
        "karta":   '<div class="map"><span class="ring"></span><span class="ring"></span>'
                   '<span class="ring"></span><span class="pin"></span></div>',
        "polosy":  '<div class="bars">%s</div>' % n(4),
        "dialog":  '<div class="talk"><span class="b l"></span><span class="b r"></span>'
                   '<span class="b l"></span><span class="b r"></span></div>',
        "kadry":   '<div class="film">%s</div>' % n(7),
        "golos":   '<div class="eq">%s</div>' % n(15),
        "montazh": '<div class="tl">%s<span class="head"></span></div>' % n(5),
    }
    if vid not in m:
        return ""
    return '<div class="rabota" data-vid="%s">%s</div>' % (esc(vid), m[vid])


def say_html(text):
    if not text:
        return ""
    return '<div class="say"><span class="bot">AI</span><p>' + esc(text) + '</p></div>'


def chips(arr):
    if not arr:
        return ""
    return '<ul class="chips">' + "".join('<li>' + esc(c) + '</li>' for c in arr) + '</ul>'


def facts(arr):
    if not arr:
        return ""
    rows = []
    for f in arr:
        t = f if isinstance(f, str) else f.get("t", "")
        rows.append('<li><span class="bul"></span>' + esc(t) + '</li>')
    return '<ul class="facts">' + "".join(rows) + '</ul>'


def nums(arr):
    if not arr:
        return ""
    return ('<div class="nums">' + "".join(
        '<div><b>' + esc(n.get("v", "")) + '</b><span>' + esc(n.get("t", "")) + '</span></div>'
        for n in arr) + '</div>')


def log(arr, live):
    """Строчки работы. На идущем шаге они проявляются по одной, на готовом стоят все."""
    if not arr:
        return ""
    out = []
    for n, line in enumerate(arr):
        at = (n + 1) / float(len(arr) + 1)
        out.append('<li%s data-at="%.3f">%s</li>' % (' class="hid"' if live else "", at, esc(line)))
    return '<ul class="log">' + "".join(out) + '</ul>'


def grid(arr):
    """Плитка с картинками: чего ещё нет — место под неё, с подписью."""
    if not arr:
        return ""
    out = []
    for n, g in enumerate(arr, 1):
        rel = g.get("file") or ""
        src = kartinka(rel)
        kino = rel.lower().endswith(".mp4")
        ratio = ""
        if src and not kino:
            wh = storony(rel)
            if wh:
                ratio = ' style="aspect-ratio:%d/%d"' % tuple(wh)
        elif kino:
            ratio = ' style="aspect-ratio:4/5"'
        if not src:
            inner = '<span class="hole">место под картинку %d</span>' % n
        elif kino:
            inner = '<video src="%s" autoplay muted loop playsinline%s></video>' % (src, ratio)
        else:
            inner = '<img src="%s" alt=""%s>' % (src, ratio)
        knopka = ('<button class="lupa" type="button" aria-label="Посмотреть целиком"></button>'
                  if src else "")
        out.append('<figure class="tile%s">%s%s<figcaption>%s</figcaption></figure>'
                   % ("" if src else " empty", inner, knopka, esc(g.get("text", ""))))
    return '<div class="grid">' + "".join(out) + "</div>"


def shots(step):
    """Снимки шага: раскадровка, сайт на компьютере и телефоне."""
    out = []
    for sh in step.get("shots") or []:
        src = kartinka(sh.get("file", ""))
        if not src:
            continue
        cls = ' class="phone"' if sh.get("phone") else ""
        out.append('<figure%s><img src="%s" alt="%s">%s</figure>'
                   % (cls, src, esc(sh.get("caption", "")),
                      '<figcaption>' + esc(sh["caption"]) + '</figcaption>' if sh.get("caption") else ""))
    return '<div class="shots">' + "".join(out) + '</div>' if out else ""


def docfold(step, label):
    """Документ шага прямо под репликой: это главный результат, его не прячем вниз."""
    inside = dokument.doc_inline(step)
    if not inside:
        return ""
    name = (step.get("doc") or {}).get("name") if isinstance(step.get("doc"), dict) else ""
    return ('<details class="docfold"><summary><span class="dicon"></span>'
            '<span class="dtxt"><b>' + esc(label) + '</b><i>' + esc(name or "нажми, чтобы открыть")
            + '</i></span><span class="arr">&#9662;</span></summary>' + inside + '</details>')


def result(step, label):
    """Всё, что шаг оставил после себя."""
    return (say_html(step.get("say"))
            + docfold(step, label)
            + nums(step.get("nums"))
            + chips(step.get("chips"))
            + facts(step.get("items"))
            + shots(step)
            + log(step.get("log"), False))


def who_of(step, team):
    k = step.get("who")
    if isinstance(k, int) and 0 <= k < len(team):
        return team[k]
    return {}


# ---------- шаг крупно ----------

def slide(i, s, total, team):
    """Один шаг во весь экран.

    Пока шаг в работе, показываем только то, что агент сказал, беря его в руки,
    и саму работу. Результата ещё нет и быть не должно: иначе выходит глупость,
    будто работа идёт, а итог уже лежит.
    """
    st = s.get("status", "wait")
    m = who_of(s, team)
    head = ('<div class="slidetop"><span class="no">%02d / %02d</span>'
            '<span class="who">%s</span><span class="pill">%s</span></div>'
            '<h2>%s</h2>' % (i, total, esc(m.get("name", "")), ST.get(st, st), esc(s.get("title", ""))))
    if st == "run":
        body = (say_html(s.get("take") or s.get("sub"))
                + '<div class="waiting"><div class="wtop"><i></i><i></i><i></i>'
                  '<span>' + esc(m.get("role") or "работает") + ', результат появится здесь</span></div>'
                + rabota(s.get("vid")) + log(s.get("log"), True) + '</div>')
    else:
        body = result(s, "Документ готов")
    return ('<section class="slide" data-s="%s" id="nowstep" data-dur="%d">%s%s</section>'
            % (esc(st), int(s.get("dur", 20)), head, body))


def past(rows, team, live):
    """Сделанные шаги. Каждый открывается по нажатию вместе со своим документом.
    Только что сделанный открыт сразу: его итог виден, пока идёт следующий."""
    if not rows:
        return ""
    items = []
    for n, (i, s) in enumerate(rows):
        fresh = live and n == len(rows) - 1
        res = ""
        if s.get("nums"):
            first = s["nums"][0]
            res = '<span class="r">' + esc("%s %s" % (first.get("v", ""), first.get("t", ""))) + '</span>'
        m = who_of(s, team)
        items.append(
            '<details class="pastone" id="step-%02d"%s><summary><span class="no">%02d</span>'
            '<b>%s</b><span class="pwho">%s</span>%s</summary><div class="pastbody">%s</div></details>'
            % (i, " open" if fresh else "", i, esc(s.get("title", "")), esc(m.get("name", "")), res,
               result(s, "Документ шага")))
    lab = "уже сделано: %d" % len(rows)
    if live:
        lab += " · последний шаг открыт"
    return ('<details class="past" open><summary><span class="lab">' + lab + '</span></summary>'
            '<div class="pastlist">' + "".join(items) + '</div></details>')


def ahead(rows):
    if not rows:
        return ""
    return ('<section class="ahead"><span class="lab">дальше по плану</span><ol>'
            + "".join('<li><span class="no">%02d</span>%s</li>' % (i, esc(s.get("title", "")))
                      for i, s in rows)
            + '</ol></section>')


def polka(steps):
    """Картинки, которые уже сделаны, остаются на экране до конца."""
    out = []
    for s in steps:
        if s.get("status") == "done" and s.get("grid"):
            out.append('<section class="polka"><span class="lab">%s</span>%s</section>'
                       % (esc(s.get("gridlab", "что нарисовали")), grid(s["grid"])))
    return "".join(out)


def ask_block(a):
    """Вопрос человеку прямо на экране: что спросили и что ответили."""
    if not a:
        return ""
    rows = []
    for q in a.get("rows", []):
        got = q.get("answer")
        rows.append('<div class="qrow%s"><span class="q">%s</span><span class="a">%s</span></div>'
                    % ("" if got else " wait", esc(q.get("q", "")), esc(got) if got else "ждём ответ"))
    return ('<section class="ask"><span class="lab">%s</span>%s</section>'
            % (esc(a.get("title", "уточняю у тебя")), "".join(rows)))


def fin_block(f):
    if not f:
        return ""
    links = "".join('<a class="go%s" href="%s" target="_blank" rel="noopener">%s</a>'
                    % (" main" if n == 0 else "", esc(l.get("url", "#")), esc(l.get("text", "")))
                    for n, l in enumerate(f.get("links", [])))
    shot = ""
    if f.get("shot"):
        src = kartinka(f["shot"])
        if src:
            shot = '<img class="shot" src="%s" alt="%s">' % (src, esc(f.get("shotalt", "")))
        else:
            shot = '<div class="shot hole">%s</div>' % esc(f.get("shotalt", "место под скриншот"))
    return ('<section class="fin" id="fin"><span class="live" data-done="1"><i></i>готово</span>'
            '<h2>%s</h2><p>%s</p>%s<div class="gos">%s</div></section>'
            % (esc(f.get("title", "Готово")), esc(f.get("text", "")), shot, links))


# ---------- страница ----------

def build(name, tiho=False):
    path = os.path.join(HERE, "shagi", name + ".json")
    d = json.loads(io.open(path, encoding="utf-8").read())
    steps = d.get("steps", [])
    team = d.get("team", [])
    total = len(steps)

    current, done_rows, ahead_rows = None, [], []
    for i, s in enumerate(steps, 1):
        st = s.get("status", "wait")
        if st == "run" and current is None:
            current = (i, s)
        elif st == "done":
            done_rows.append((i, s))
        else:
            ahead_rows.append((i, s))
    live = current is not None
    # всё пройдено: последний сделанный шаг и есть итог
    if current is None and done_rows:
        current = done_rows.pop()
    done = sum(1 for s in steps if s.get("status") == "done")
    finished = bool(steps) and done == total

    rail = "".join('<li data-s="%s"></li>' % esc(s.get("status", "wait")) for s in steps)
    railwrap = ('<div class="railwrap"><span class="lab">шаг %02d из %02d</span><ul class="rail2">%s</ul></div>'
                % (current[0] if current else 0, total, rail))

    src = d.get("source")
    source = (('Взял в работу <b>' + esc(src) + '</b>') if src else "")
    if d.get("who"):
        source += ('<span>' if src else "") + esc(d["who"]) + ('</span>' if src else "")

    office_block, office_js = ofis.office(team)
    foot = d.get("foot") or "Персонажи и мебель офиса: набор MetroCity, автор JIK-A-4, лицензия CC0."

    page = Template(shablon()).substitute(
        title=esc(d.get("title", "Работа агента")),
        state=esc(d.get("state", "в работе" if live else "готово")),
        source=source,
        live="1" if live else "0",
        alldone="1" if finished else "0",
        key=esc(name),
        elapsed=int(d.get("elapsed", 0)),
        done=done,
        total=total,
        pct=int(round(100.0 * done / max(1, total))),
        office=office_block,
        officejs=office_js,
        team=team_html(team, steps),
        ask=ask_block(d.get("ask")),
        fin=fin_block(d.get("fin")) if finished else "",
        rail=railwrap if steps else "",
        now=slide(current[0], current[1], total, team) if current else "",
        polka=polka(steps),
        past=past(done_rows, team, live),
        ahead=ahead(ahead_rows),
        foot='<span>' + esc(foot) + '</span>',
        doccss=dokument.doc_css(),
    )
    out = os.path.join(BUILD, IMYA.get(name, name + ".html"))
    os.makedirs(BUILD, exist_ok=True)
    io.open(out, "w", encoding="utf-8").write(page)
    if not tiho:
        print("%s → %s (%d из %d, %s, %.2f МБ)" % (name, out, done, total,
                                                  "идёт" if live else "стоп",
                                                  os.path.getsize(out) / 1048576.0))
    return out


def shablon():
    return io.open(os.path.join(HERE, "shablon.html"), encoding="utf-8").read()


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "01-sajt")
