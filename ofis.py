# -*- coding: utf-8 -*-
"""Пиксельный офис команды: специалисты ходят по комнате, а за компьютер
садится тот, чей шаг сейчас в работе.

Перенесено из «Агента сайтов» как есть: та же комната, те же места, то же
поведение. Спрайты лежат в pixel/ (набор MetroCity, автор JIK-A-4, лицензия
CC0, в раздаче пакета pixel-agents, MIT) и вшиваются в страницу целиком,
потому что артефакт не пускает внешние адреса.

Экран зовёт office(team) из ekran.py. Стол закреплён за специалистом полем
mesto в team («копирайтер», «видеограф»…): один и тот же человек сидит за
одним и тем же столом на всех четырёх экранах.

Чего не делает: не рисует прогресса, которого не было. Это сцена, а не отчёт.
"""
import base64
import glob
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PIX = os.path.join(HERE, "pixel")

TILE = 16          # размер тайла в пикселях спрайта
COLS, ROWS = 32, 11

# места в офисе по номеру человека в команде: кто был в «Агенте сайтов»,
# какой спрайт, поворот оттенка и клетка стула. Имена здесь только для памяти,
# на экране подписи берутся из shagi/*.json
CREW = [
    ("исследователь", "", 0,   0, (3, 3)),
    ("аналитик",      "", 1,   0, (7, 3)),
    ("маркетолог",    "", 2,   0, (11, 3)),
    ("стратег",       "", 3,   0, (15, 3)),
    ("копирайтер",    "", 4,   0, (19, 3)),
    ("дизайнер",      "", 5,   0, (23, 3)),
    ("продавец",      "", 0, 140, (3, 8)),
    ("видеограф",     "", 2, 210, (7, 8)),
    ("разработчик",   "", 4,  60, (11, 8)),
]


def uri(rel):
    full = os.path.join(PIX, rel)
    if not os.path.exists(full):
        return ""
    return "data:image/png;base64," + base64.b64encode(io.open(full, "rb").read()).decode("ascii")


def assets():
    """Что грузим в страницу. Ключ это имя, по которому зовём из раскладки."""
    need = {
        "floor": "floors/floor_2.png",
        "floor_alt": "floors/floor_5.png",
        "wall": "walls/wall_0.png",
        "carpet": "carpets/carpet_0.png",
        "desk_front": "furniture/DESK/DESK_FRONT.png",
        "desk_side": "furniture/DESK/DESK_SIDE.png",
        "pc_off": "furniture/PC/PC_FRONT_OFF.png",
        "pc_on1": "furniture/PC/PC_FRONT_ON_1.png",
        "pc_on2": "furniture/PC/PC_FRONT_ON_2.png",
        "pc_on3": "furniture/PC/PC_FRONT_ON_3.png",
        "chair_back": "furniture/WOODEN_CHAIR/WOODEN_CHAIR_BACK.png",
        "chair_front": "furniture/WOODEN_CHAIR/WOODEN_CHAIR_FRONT.png",
        "sofa": "furniture/SOFA/SOFA_FRONT.png",
        "small_table": "furniture/SMALL_TABLE/SMALL_TABLE_FRONT.png",
        "coffee_table": "furniture/COFFEE_TABLE/COFFEE_TABLE.png",
        "bookshelf": "furniture/BOOKSHELF/BOOKSHELF.png",
        "bookshelf2": "furniture/DOUBLE_BOOKSHELF/DOUBLE_BOOKSHELF.png",
        "plant": "furniture/PLANT/PLANT.png",
        "plant2": "furniture/PLANT_2/PLANT_2.png",
        "big_plant": "furniture/LARGE_PLANT/LARGE_PLANT.png",
        "cactus": "furniture/CACTUS/CACTUS.png",
        "board": "furniture/WHITEBOARD/WHITEBOARD.png",
        "painting": "furniture/LARGE_PAINTING/LARGE_PAINTING.png",
        "clock": "furniture/CLOCK/CLOCK.png",
        "coffee": "furniture/COFFEE/COFFEE.png",
        "bin": "furniture/BIN/BIN.png",
    }
    out = {}
    for key, rel in need.items():
        u = uri(rel)
        if u:
            out[key] = u
    for k in range(6):
        u = uri("characters/char_%d.png" % k)
        if u:
            out["char%d" % k] = u
    return out


LAYOUT = [
    # на стене
    ("board", 2, 0), ("painting", 9, 0), ("painting", 17, 0), ("clock", 25, 0),
    ("bookshelf2", 5, 0), ("bookshelf", 13, 0), ("bookshelf", 21, 0), ("bookshelf2", 28, 0),

    # верхний ряд рабочих мест
    ("desk_front", 3, 2), ("desk_front", 7, 2), ("desk_front", 11, 2),
    ("desk_front", 15, 2), ("desk_front", 19, 2), ("desk_front", 23, 2),

    # нижний ряд рабочих мест
    ("desk_front", 3, 7), ("desk_front", 7, 7), ("desk_front", 11, 7),

    # зона отдыха справа
    ("sofa", 21, 8), ("coffee_table", 23, 9), ("sofa", 25, 8),
    ("big_plant", 19, 8), ("plant2", 27, 8), ("coffee", 20, 7),
    ("small_table", 28, 9),

    # зелень и мелочь
    ("plant", 1, 2), ("cactus", 1, 7), ("plant2", 30, 2),
    ("plant", 16, 7), ("bin", 14, 8), ("cactus", 30, 10),
    ("plant2", 1, 10), ("big_plant", 17, 10),

    # левый и правый край комнаты
    ("bookshelf", 0, 0), ("bookshelf2", 30, 0),
    ("big_plant", 0, 4), ("cactus", 31, 4),
    ("plant", 0, 8), ("plant2", 31, 7),
    ("bin", 0, 11), ("small_table", 31, 11),
]

# ковровая зона отдыха: с какого по какой тайл
CARPET = (20, 8, 29, 10)


def probe(found):
    """Часть спрайтов лежит под другими именами: подставляем, что нашлось."""
    fixes = {
        "sofa": "furniture/SOFA/*.png",
        "coffee_table": "furniture/COFFEE_TABLE/*.png",
        "bookshelf": "furniture/BOOKSHELF/*.png",
        "bookshelf2": "furniture/DOUBLE_BOOKSHELF/*.png",
        "plant": "furniture/PLANT/*.png",
        "plant2": "furniture/PLANT_2/*.png",
        "big_plant": "furniture/LARGE_PLANT/*.png",
        "cactus": "furniture/CACTUS/*.png",
        "board": "furniture/WHITEBOARD/*.png",
        "painting": "furniture/LARGE_PAINTING/*.png",
        "clock": "furniture/CLOCK/*.png",
        "coffee": "furniture/COFFEE/*.png",
        "bin": "furniture/BIN/*.png",
        "carpet": "carpets/*.png",
    }
    for key, pat in fixes.items():
        if key in found:
            continue
        hits = sorted(glob.glob(os.path.join(PIX, pat.replace("/", os.sep))))
        hits = [h for h in hits if not h.endswith("manifest.json")]
        if hits:
            found[key] = "data:image/png;base64," + base64.b64encode(
                io.open(hits[0], "rb").read()).decode("ascii")
    return found


JS = """
(function(){
  var A = window.__ART__, CREW = window.__CREW__, LAY = window.__LAY__;
  var TILE = 16, COLS = __COLS__, ROWS = __ROWS__, CARPET = window.__CARPET__;
  var cv = document.getElementById('office');
  if(!cv) return;
  var cx = cv.getContext('2d');
  cv.width = COLS * TILE; cv.height = ROWS * TILE;
  cx.imageSmoothingEnabled = false;

  var img = {}, left = 0;
  Object.keys(A).forEach(function(k){
    left++;
    var im = new Image();
    im.onload = im.onerror = function(){ left--; if(left === 0) start(); };
    im.src = A[k]; img[k] = im;
  });

  /* шесть исходных персонажей на девять агентов: лишних перекрашиваем */
  function tinted(im, deg){
    if(!deg) return im;
    var c = document.createElement('canvas');
    c.width = im.width; c.height = im.height;
    var g = c.getContext('2d');
    g.filter = 'hue-rotate(' + deg + 'deg) saturate(1.2)';
    g.drawImage(im, 0, 0);
    return c;
  }

  var ROW = {down: 0, side: 1, up: 2};

  function Agent(spec){
    this.name = spec.name; this.doing = spec.doing;
    this.sprite = spec.sprite; this.tint = spec.tint;
    this.home = {x: spec.home[0], y: spec.home[1]};
    this.x = spec.home[0] + 0.5; this.y = spec.home[1] + 0.5;
    this.dir = 'up'; this.flip = false; this.frame = 0; this.t = 0;
    this.state = 'sit'; this.path = []; this.wait = 1 + Math.random() * 5;
    this.atHome = true; this.busy = false;
  }

  Agent.prototype.draw = function(){
    var f = this.state === 'walk' ? (1 + (this.frame % 6)) : 0;
    var px = Math.round(this.x * TILE - 8);
    var py = Math.round(this.y * TILE - 26);
    if(this.flip){
      cx.save();
      cx.translate(px + 16, py);
      cx.scale(-1, 1);
      cx.drawImage(this.sheet, f * 16, ROW[this.dir] * 32, 16, 32, 0, 0, 16, 32);
      cx.restore();
    } else {
      cx.drawImage(this.sheet, f * 16, ROW[this.dir] * 32, 16, 32, px, py, 16, 32);
    }
  };

  /* ходим по двум коридорам, чтобы не лезть сквозь столы */
  var LANES = [5, 10];
  function routeTo(a, tx, ty){
    var lane = LANES.reduce(function(best, l){
      return Math.abs(l - a.y) < Math.abs(best - a.y) ? l : best;
    }, LANES[0]);
    a.path = [{x: a.x, y: lane + 0.5},
              {x: tx + 0.5, y: lane + 0.5},
              {x: tx + 0.5, y: ty + 0.5}];
  }

  function step(a, dt){
    if(a.state === 'walk' && a.path.length){
      var p = a.path[0], dx = p.x - a.x, dy = p.y - a.y;
      var d = Math.sqrt(dx * dx + dy * dy), v = 3.2 * dt;
      if(d <= v){
        a.x = p.x; a.y = p.y; a.path.shift();
        if(!a.path.length){
          a.state = a.atHome ? 'sit' : 'stand';
          a.dir = a.atHome ? 'up' : 'down';
          a.flip = false;
          a.wait = a.atHome ? 4 + Math.random() * 6 : 2 + Math.random() * 4;
        }
      } else {
        a.x += dx / d * v; a.y += dy / d * v;
        if(Math.abs(dx) > Math.abs(dy)){ a.dir = 'side'; a.flip = dx < 0; }
        else { a.dir = dy > 0 ? 'down' : 'up'; a.flip = false; }
        a.t += dt;
        if(a.t > 0.1){ a.t = 0; a.frame++; }
      }
      return;
    }
    a.wait -= dt;
    if(a.wait > 0) return;

    if(a.busy && !(a.atHome && a.state === 'sit')){
      a.atHome = true; a.state = 'walk';
      routeTo(a, a.home.x, a.home.y);
      return;
    }
    if(a.busy) { a.wait = 2; return; }

    a.atHome = Math.random() < 0.45;
    var tx, ty;
    if(a.atHome){ tx = a.home.x; ty = a.home.y; }
    else {
      tx = 2 + Math.floor(Math.random() * (COLS - 5));
      ty = LANES[Math.floor(Math.random() * LANES.length)];
    }
    a.state = 'walk';
    routeTo(a, tx, ty);
  }

  var agents = [], active = 0, blink = 0;

  /* фон статичен: рисуем один раз, тонируем под интерфейс и кэшируем */
  var bg = null;
  function buildBackground(){
    bg = document.createElement('canvas');
    bg.width = COLS * TILE; bg.height = ROWS * TILE;
    var b = bg.getContext('2d');
    b.imageSmoothingEnabled = false;

    for(var y = 0; y < ROWS; y++){
      for(var x = 0; x < COLS; x++){
        if(y < 1){
          if(img.wall) b.drawImage(img.wall, 16, 16, 16, 16, x * TILE, y * TILE, TILE, TILE);
        } else {
          var t = ((x * 3 + y * 5) % 11 === 0 && img.floor_alt) ? img.floor_alt : img.floor;
          if(t) b.drawImage(t, 0, 0, 16, 16, x * TILE, y * TILE, TILE, TILE);
        }
      }
    }
    if(img.carpet && CARPET){
      for(var cy = CARPET[1]; cy <= CARPET[3]; cy++)
        for(var k = CARPET[0]; k <= CARPET[2]; k++)
          b.drawImage(img.carpet, 0, 0, 16, 16, k * TILE, cy * TILE, TILE, TILE);
    }

    /* перекрашиваем пол и стены в палитру интерфейса */
    b.globalCompositeOperation = 'color';
    b.fillStyle = '#14293b';
    b.fillRect(0, 0, bg.width, bg.height);

    b.globalCompositeOperation = 'multiply';
    b.fillStyle = '#7d94b4';
    b.fillRect(0, 0, bg.width, bg.height);

    b.globalCompositeOperation = 'source-over';
    b.fillStyle = 'rgba(6,10,17,.55)';
    b.fillRect(0, 0, bg.width, 1 * TILE);
    var g = b.createLinearGradient(0, 1 * TILE, 0, bg.height);
    g.addColorStop(0, 'rgba(60,224,192,.05)');
    g.addColorStop(1, 'rgba(6,10,17,.35)');
    b.fillStyle = g;
    b.fillRect(0, 1 * TILE, bg.width, bg.height - 1 * TILE);
  }

  function drawFloor(){
    if(!bg) buildBackground();
    cx.drawImage(bg, 0, 0);
  }

  function pcOn(){
    var n = [img.pc_on1, img.pc_on2, img.pc_on3].filter(Boolean);
    return n.length ? n[Math.floor(blink) % n.length] : img.pc_off;
  }

  function frame(){
    drawFloor();
    var items = [];

    LAY.forEach(function(o){
      var im = img[o[0]];
      if(!im) return;
      items.push({y: o[2] * TILE + TILE, draw: function(){
        cx.save();
        cx.filter = 'saturate(.72) brightness(.86) hue-rotate(-8deg)';
        cx.drawImage(im, o[1] * TILE, o[2] * TILE + TILE - im.height);
        cx.restore();
      }});
    });

    agents.forEach(function(a){
      var working = a.busy && a.state === 'sit';
      var pc = working ? pcOn() : img.pc_off;
      if(pc){
        items.push({y: (a.home.y - 1) * TILE + TILE, draw: function(){
          cx.drawImage(pc, a.home.x * TILE, (a.home.y - 1) * TILE + TILE - pc.height);
        }});
      }
      if(working){
        items.push({y: a.y * TILE - 1, draw: function(){
          var g = cx.createRadialGradient(a.x * TILE, a.y * TILE - 6, 1, a.x * TILE, a.y * TILE - 6, 22);
          g.addColorStop(0, 'rgba(60,224,192,.28)');
          g.addColorStop(1, 'rgba(60,224,192,0)');
          cx.fillStyle = g;
          cx.fillRect(a.x * TILE - 22, a.y * TILE - 28, 44, 44);
        }});
      }
      items.push({y: a.y * TILE, draw: function(){ a.draw(); }});
      if(working){
        items.push({y: a.y * TILE + 1, draw: function(){
          var bob = Math.sin(blink * 2) > 0 ? 0 : 1;
          cx.fillStyle = 'rgba(60,224,192,.9)';
          cx.fillRect(Math.round(a.x * TILE) - 1, Math.round(a.y * TILE) - 34 - bob, 3, 3);
          cx.fillRect(Math.round(a.x * TILE) - 4, Math.round(a.y * TILE) - 31 - bob, 9, 2);
        }});
      }
    });

    items.sort(function(p, q){ return p.y - q.y; });
    items.forEach(function(it){ it.draw(); });
  }

  function start(){
    agents = CREW.map(function(c){
      var a = new Agent(c);
      a.sheet = tinted(img['char' + c.sprite], c.tint);
      return a;
    });

    /* строка состояния и карточки есть не на всякой странице: без них тоже работаем */
    var cards = [].slice.call(document.querySelectorAll('.card'));
    var who = document.getElementById('who'), what = document.getElementById('what');
    function setActive(k){
      agents.forEach(function(a, n){
        a.busy = (n === k);
        if(n === k) a.wait = Math.min(a.wait, 0.2);
      });
      cards.forEach(function(el, n){ el.setAttribute('data-on', n === k ? '1' : '0'); });
      if(who && CREW[k]) who.textContent = CREW[k].name;
      if(what && CREW[k]) what.textContent = CREW[k].doing;
    }
    window.__setActive = setActive;
    setActive(typeof window.__ACTIVE__ === 'number' ? window.__ACTIVE__ : 0);
    if(window.__LOOP_ACTIVE__){
      setInterval(function(){
        active = (active + 1) % CREW.length;
        setActive(active);
      }, 9000);
    }

    var last = performance.now();
    requestAnimationFrame(function loop(now){
      var dt = Math.min(0.05, (now - last) / 1000);
      last = now; blink += dt * 5;
      agents.forEach(function(a){ step(a, dt); });
      frame();
      requestAnimationFrame(loop);
    });
  }
})();
"""


def esc(v):
    s = "" if v is None else str(v)
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def mesto(m, k):
    """Чей стол. Один и тот же специалист сидит за своим столом на всех экранах:
    в team у него поле mesto с ролью из CREW. Нет поля — стол по порядку."""
    want = str(m.get("mesto") or "").strip().lower()
    for n, c in enumerate(CREW):
        if c[0] == want:
            return n
    return k % len(CREW)


def office(team):
    """Офис для экрана: (блок со сценой, скрипты). Работает тот, у кого status run."""
    if not team:
        return "", ""
    crew, active = [], -1
    for k, m in enumerate(team[:len(CREW)]):
        _, _, sprite, tint, seat = CREW[mesto(m, k)]
        crew.append({"name": m.get("name", ""), "doing": m.get("role", ""),
                     "sprite": sprite, "tint": tint, "home": list(seat)})
        if m.get("status") == "run":
            active = k
    art = probe(assets())
    lay = [list(o) for o in LAYOUT]
    js = JS.replace("__COLS__", str(COLS)).replace("__ROWS__", str(ROWS))
    if active >= 0:
        right = "работает " + esc(team[active].get("name", ""))
    elif all(m.get("status") == "done" for m in team):
        right = "работа сдана, команда отдыхает"
    else:
        right = "команда на месте, ждёт старта"
    block = ('<section class="office">'
             '<div class="ohead"><span class="lab">офис команды</span>'
             '<span class="lab dim">' + right + '</span></div>'
             '<div class="stage"><canvas id="office"></canvas></div></section>')
    data = ("<script>window.__ART__=" + json.dumps(art) + ";"
            "window.__CREW__=" + json.dumps(crew, ensure_ascii=False) + ";"
            "window.__LAY__=" + json.dumps(lay) + ";"
            "window.__CARPET__=" + json.dumps(list(CARPET)) + ";"
            "window.__ACTIVE__=" + str(active) + ";</script>")
    return block, data + "<script>" + js + "</script>"
