# -*- coding: utf-8 -*-
"""Сборка PDF-презентации БИОПРАЙМ (3 вертикальные страницы A4)."""
import math, random, subprocess, os, pathlib

ROOT = pathlib.Path(__file__).parent
OUT_HTML = ROOT / "bioprime.html"
OUT_PDF = ROOT / "bioprime.pdf"

# ---------------------------------------------------------------- график спроса
TREND_YEARS = ["2021", "2022", "2023", "2024", "2025", "2026"]
TREND_WORLD = [6, 15, 29, 48, 79, 100]   # индекс поискового интереса, 2026 = 100
TREND_RU    = [2, 5, 13, 31, 64, 96]

def trend_paths(w=300.0, h=74.0, pad_l=4.0, pad_b=14.0, pad_t=8.0):
    n = len(TREND_YEARS)
    def pt(i, v):
        return pad_l + (w - pad_l - 8) * i / (n - 1), pad_t + (h - pad_t - pad_b) * (1 - v / 100.0)
    def path(series):
        pts = [pt(i, v) for i, v in enumerate(series)]
        d = "M %.1f %.1f" % pts[0]
        for i in range(1, len(pts)):
            x0, y0 = pts[i - 1]; x1, y1 = pts[i]; cx = (x0 + x1) / 2
            d += " C %.1f %.1f %.1f %.1f %.1f %.1f" % (cx, y0, cx, y1, x1, y1)
        return d, pts
    dw, pw = path(TREND_WORLD)
    dr, pr = path(TREND_RU)
    base = pad_t + (h - pad_t - pad_b)
    area = dw + " L %.1f %.1f L %.1f %.1f Z" % (pw[-1][0], base, pw[0][0], base)
    return dw, dr, area, pw, pr

# ---------------------------------------------------------------- карта Москвы
def mkad_polygon(cx=250.0, cy=250.0, rx=205.0, ry=192.0, n=72):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        wob = 1 + 0.018 * math.sin(a * 5 + 1.1) + 0.012 * math.sin(a * 9 + 0.3)
        pts.append((cx + rx * wob * math.cos(a), cy + ry * wob * math.sin(a)))
    return pts

def poly_d(pts):
    return "M " + " L ".join("%.1f %.1f" % p for p in pts) + " Z"

def map_points(cx=250.0, cy=250.0, seed=21):
    """50 точек: 15 — волна 1 (центр/ТТК), 35 — волна 2 (весь город)."""
    rnd = random.Random(seed)
    pts = []
    for i in range(15):
        a = 2 * math.pi * (i / 15) + rnd.uniform(-0.18, 0.18)
        r = rnd.uniform(28, 96)
        pts.append((cx + r * math.cos(a) * 1.05, cy + r * math.sin(a) * 0.98, 1))
    for i in range(35):
        a = 2 * math.pi * (i / 35) + rnd.uniform(-0.09, 0.09)
        r = rnd.uniform(105, 182) * (0.93 + 0.07 * rnd.random())
        pts.append((cx + r * math.cos(a) * 1.04, cy + r * math.sin(a) * 0.95, 2))
    return pts

def svg_map():
    mk = mkad_polygon(); dots = map_points(); s = []
    s.append('<path d="%s" class="mk-fill"/>' % poly_d(mk))
    s.append('<path d="%s" class="mk-ring"/>' % poly_d(mk))
    s.append('<path class="river" d="M 70 168 C 140 150 160 236 232 246 '
             'C 300 256 296 178 372 196 C 424 208 414 268 372 316 '
             'C 330 364 268 356 214 396"/>')
    s.append('<ellipse cx="250" cy="250" rx="104" ry="97" class="ttk"/>')
    s.append('<ellipse cx="250" cy="250" rx="52" ry="48" class="sad"/>')
    for a in range(0, 360, 30):
        r = math.radians(a)
        s.append('<line class="radial" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>' % (
            250 + 20 * math.cos(r), 250 + 20 * math.sin(r),
            250 + 200 * math.cos(r) * 1.02, 250 + 188 * math.sin(r)))
    s.append('<circle cx="250" cy="250" r="5.4" class="kremlin"/>')
    for x, y, w in dots:
        if w == 2:
            s.append('<circle cx="%.1f" cy="%.1f" r="7.6" class="dot2-h"/>'
                     '<circle cx="%.1f" cy="%.1f" r="4.1" class="dot2"/>' % (x, y, x, y))
    for x, y, w in dots:
        if w == 1:
            s.append('<circle cx="%.1f" cy="%.1f" r="9.4" class="dot1-h"/>'
                     '<circle cx="%.1f" cy="%.1f" r="5.1" class="dot1"/>' % (x, y, x, y))
    return "\n".join(s)

# ---------------------------------------------------------------- фрагменты SVG
dw, dr, area, pw, pr = trend_paths()
world_dots = "\n".join('<circle class="pt-w" cx="%.1f" cy="%.1f" r="2.4"/>' % p for p in pw)


# полки: 4 полки × 5 пачек по 6 бутылок
shelves = []
for sy in (104, 170, 236, 302):
    shelves.append('<line x1="29" y1="%d" x2="149" y2="%d" stroke="#C7D8D6" stroke-width="2.4"/>'
                   % (sy + 28, sy + 28))
    for pi in range(5):
        px = 31 + pi * 24
        shelves.append('<rect x="%d" y="%d" width="21" height="26" rx="2.6" '
                       'fill="#F6E7A8" stroke="#C9A94E" stroke-width="1.4"/>' % (px, sy + 2))
        for bi in range(3):
            shelves.append('<rect x="%.1f" y="%d" width="4.6" height="4" rx="1.2" fill="#6B6B6B"/>'
                           % (px + 2.4 + bi * 6, sy))
        shelves.append('<rect x="%.1f" y="%d" width="13" height="6" rx="1" fill="#fff" opacity=".92"/>'
                       % (px + 4, sy + 12))
shelves.append('<line x1="29" y1="366" x2="149" y2="366" stroke="#C7D8D6" stroke-width="2.4"/>')

# ---------------------------------------------------------------- HTML
HTML = u"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<title>БИОПРАЙМ — презентация</title>
<link rel="stylesheet" href="fonts/manrope.css">
<style>
:root{--ink:#0C1A18;--ink2:#41524F;--mut:#8394910;--mut:#839491;--mint:#7FD9D1;
  --mint-l:#DCF4F1;--mint-d:#0E6F68;--gold:#E8C46A;--line:#E6EAE9;--dark:#0F2422}
*{box-sizing:border-box;margin:0;padding:0}
@page{size:A4 portrait;margin:0}
html,body{font-family:'Manrope','DejaVu Sans',sans-serif;color:var(--ink);
  -webkit-print-color-adjust:exact;print-color-adjust:exact}
.page{width:210mm;height:297mm;padding:13mm 16mm 11mm;overflow:hidden;background:#fff;
  page-break-after:always;display:flex;flex-direction:column}
.page:last-child{page-break-after:auto}

/* шапка */
.head{display:flex;align-items:baseline;justify-content:space-between;flex:0 0 auto}
.bname{font-weight:800;font-size:12pt;letter-spacing:.14em}
.tag{font-size:7.4pt;letter-spacing:.22em;text-transform:uppercase;color:var(--mut);font-weight:700}
.tag b{color:var(--ink);margin-left:2.6mm}

/* герой — во всю ширину листа */
.hero{margin:7mm -16mm 0;height:126mm;flex:0 0 auto;overflow:hidden;position:relative;
  background:#EFEFEF;display:flex}
.hero img{width:100%;height:100%;object-fit:cover;display:block}
.hero .half{width:50%;height:100%;overflow:hidden;position:relative}
.hero .half.tint{background:var(--mint-l);display:flex;align-items:center;justify-content:center;
  padding:9mm 6mm}
.hero .half.tint svg{height:100%;width:auto;max-width:100%}
.hero.map{background:var(--dark);align-items:center;justify-content:center;padding:3mm 10mm}
.hero.map svg{height:100%;width:auto}
.hero .side{position:absolute;top:0;bottom:0;display:flex;flex-direction:column;
  justify-content:center;gap:4mm;font-size:8.2pt;font-weight:700;color:#CFE4E1}
.hero .side.l{left:9mm}.hero .side.r{right:9mm;text-align:right}
.hero .side i{width:2.8mm;height:2.8mm;border-radius:99px;display:inline-block;margin-right:1.8mm}
.hero .side em{font-style:normal;display:block;color:#7E9B97;font-weight:600;font-size:7.4pt;
  margin-top:.8mm}

.say{flex:1 1 auto;min-height:0;display:flex;flex-direction:column;justify-content:center;
  padding:6mm 0}
h1{font-size:31pt;line-height:1.06;font-weight:800;letter-spacing:-.035em}
h1 em{font-style:normal;color:var(--mint-d)}
.lede{font-size:11pt;color:var(--ink2);line-height:1.35;margin-top:4.5mm;max-width:150mm}

/* цифры без рамок */
.stats{display:grid;grid-template-columns:repeat(3,1fr);flex:0 0 auto;
  border-top:1px solid var(--line);padding-top:6mm}
.stat{padding-left:7mm;padding-right:3mm;border-left:1px solid var(--line)}
.stat:first-child{padding-left:0;border-left:none}
.stat b{display:block;font-size:27pt;font-weight:800;line-height:1;letter-spacing:-.035em;
  color:var(--mint-d);white-space:nowrap}
.stat span{display:block;font-size:8.6pt;color:var(--ink2);margin-top:2.6mm;line-height:1.35;
  font-weight:600}

/* нижняя полоса */
.strip{margin-top:7mm;padding-top:5mm;border-top:1px solid var(--line);flex:0 0 auto;
  display:grid;grid-template-columns:auto 1fr auto;gap:8mm;align-items:center}
.strip .x{font-size:21pt;font-weight:800;line-height:1;color:var(--ink);letter-spacing:-.03em}
.strip .x s{text-decoration:none;display:block;font-size:8pt;color:var(--mut);font-weight:700;
  margin-top:1.4mm;letter-spacing:0}
.ln-w{fill:none;stroke:#0E6F68;stroke-width:3;stroke-linecap:round}
.ln-r{fill:none;stroke:#E8B93F;stroke-width:2.4;stroke-dasharray:4 3;stroke-linecap:round}
.pt-w{fill:#0E6F68}.ar{fill:url(#g1)}
svg text.ax{font-family:'Manrope',sans-serif;font-size:8px;fill:#A8B5B2;font-weight:700}
.who{text-align:right;font-size:8.2pt;font-weight:800;line-height:1.5;white-space:nowrap}
.who i{font-style:normal;color:var(--mut);font-weight:600}
.steps{margin-top:7mm;padding-top:5mm;border-top:1px solid var(--line);flex:0 0 auto;
  display:flex;align-items:center;gap:5mm;font-size:11pt;font-weight:800}
.steps s{text-decoration:none;color:var(--mint);font-size:13pt}
.tl{margin-top:7mm;padding-top:5mm;border-top:1px solid var(--line);flex:0 0 auto;
  display:grid;grid-template-columns:repeat(3,1fr);gap:7mm;font-size:8.6pt;font-weight:600;
  color:var(--ink2)}
.tl b{display:block;font-size:9.4pt;font-weight:800;color:var(--ink);margin-bottom:1.2mm}
.foot{margin-top:6mm;font-size:6.8pt;color:var(--mut);display:flex;justify-content:space-between;
  flex:0 0 auto}

/* карта */
.mk-fill{fill:#16332F}.mk-ring{fill:none;stroke:#3E6E68;stroke-width:2}
.ttk,.sad{fill:none;stroke:#2C544F;stroke-width:1.3}
.radial{stroke:#22453F;stroke-width:1}
.river{fill:none;stroke:#2E6E9E;stroke-width:3.4;stroke-linecap:round;opacity:.7}
.kremlin{fill:#E8C46A}
.dot1{fill:#7FD9D1}.dot1-h{fill:#7FD9D1;opacity:.22}
.dot2{fill:#E8C46A}.dot2-h{fill:#E8C46A;opacity:.18}
</style></head><body>

<!-- ============ 1 ============ -->
<section class="page">
  <div class="head"><div class="bname">БИОПРАЙМ</div>
    <div class="tag">Продукт <b>01</b></div></div>

  <div class="hero"><img src="assets/p_hero_packs.jpg" alt="Партия БИОПРАЙМ"></div>

  <div class="say"><h1>Живой пробиотик <em>L. reuteri</em></h1>
    <p class="lede">Дома его варят 36 часов. У нас — взял из холодильника и выпил.</p></div>

  <div class="stats">
    <div class="stat"><b>250 мл</b><span>порция на день, доза 1×10⁶ КОЕ</span></div>
    <div class="stat"><b style="font-size:26pt">1 250 ₽</b><span>курс — пачка из 6 бутылок</span></div>
    <div class="stat"><b>75 %</b><span>валовая маржа продукта</span></div>
  </div>

  <div class="strip">
    <div class="x">×16<s>спрос за 4 года</s></div>
    <svg viewBox="0 0 300 74" style="width:100%;height:auto">
      <defs><linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#0E6F68" stop-opacity=".18"/>
        <stop offset="1" stop-color="#0E6F68" stop-opacity="0"/></linearGradient></defs>
      <path class="ar" d="{AREA}"/><path class="ln-r" d="{DR}"/><path class="ln-w" d="{DW}"/>{PTW}
      <text class="ax" x="2" y="70">2021</text>
      <text class="ax" x="298" y="70" text-anchor="end">2026</text>
    </svg>
    <div class="who">Доктор Уильям Дэвис <i>· «Super Gut»</i><br>Анна Лиана <i>· YouTube</i></div>
  </div>

  <div class="foot"><span>БИОПРАЙМ</span><span>01 / 03</span></div>
</section>

<!-- ============ 2 ============ -->
<section class="page">
  <div class="head"><div class="bname">БИОПРАЙМ</div>
    <div class="tag">Точка продаж <b>02</b></div></div>

  <div class="hero">
    <div class="half tint">
      <svg viewBox="0 0 176 400" preserveAspectRatio="xMidYMid meet">
        <rect x="72" y="8" width="34" height="22" rx="5" fill="#1B2B29"/>
        <circle cx="89" cy="19" r="6.4" fill="#5BD6CE"/><circle cx="89" cy="19" r="3" fill="#0B1A19"/>
        <rect x="86" y="30" width="6" height="12" fill="#1B2B29"/>
        <line x1="76" y1="8" x2="68" y2="0" stroke="#1B2B29" stroke-width="2"/>
        <line x1="102" y1="8" x2="110" y2="0" stroke="#1B2B29" stroke-width="2"/>
        <rect x="16" y="42" width="146" height="36" rx="5" fill="#8EE0D9" stroke="#0F2422" stroke-width="2.4"/>
        <text x="89" y="59" text-anchor="middle" font-family="Manrope" font-size="10" font-weight="800" fill="#6A4A22">ЗДЕСЬ НАЧНЁТСЯ</text>
        <text x="89" y="72" text-anchor="middle" font-family="Manrope" font-size="11.5" font-weight="800" fill="#4A3214">ТВОЙ ПРАЙМ</text>
        <rect x="16" y="82" width="146" height="300" rx="7" fill="#101D1C"/>
        <rect x="25" y="91" width="128" height="282" rx="4" fill="#F4FBFA" stroke="#D3E3E1"/>
        {SHELVES}
        <path d="M 38 93 L 74 93 L 38 371 L 25 371 Z" fill="#fff" opacity=".32"/>
        <rect x="4" y="150" width="19" height="38" rx="4" fill="#12211F"/>
        <rect x="7" y="159" width="13" height="18" rx="2" fill="#BFE9FF"/>
        <rect x="20" y="222" width="5" height="42" rx="2.5" fill="#3B4F4C"/>
      </svg>
    </div>
    <div class="half"><img src="assets/p_fridge_cam.jpg" alt="Точка БИОПРАЙМ"
      style="object-position:38% 40%"></div>
  </div>

  <div class="say"><h1>Холодильник с камерой.<br><em>Без продавца и без аренды.</em></h1>
    <p class="lede">Занимает 0,5 м² в фитнес-клубе или клинике. Внутри — 20 пачек.</p></div>

  <div class="stats">
    <div class="stat"><b style="font-size:24pt">675 тыс. ₽</b><span>выручка точки в месяц</span></div>
    <div class="stat"><b style="font-size:24pt">447 тыс. ₽</b><span>прибыль точки в месяц</span></div>
    <div class="stat"><b>1,5 мес.</b><span>окупаемость холодильника</span></div>
  </div>

  <div class="steps"><span>Оплатил картой или QR</span><s>→</s><span>Замок открылся</span>
    <s>→</s><span>Забрал пачку</span></div>

  <div class="foot"><span>БИОПРАЙМ</span><span>02 / 03</span></div>
</section>

<!-- ============ 3 ============ -->
<section class="page">
  <div class="head"><div class="bname">БИОПРАЙМ</div>
    <div class="tag">Масштаб <b>03</b></div></div>

  <div class="hero map">
    <div class="side l"><span><i style="background:#7FD9D1"></i>волна 1<em>15 точек</em></span>
      <span><i style="background:#E8C46A"></i>волна 2<em>35 точек</em></span></div>
    <svg viewBox="28 28 444 444" preserveAspectRatio="xMidYMid meet">{MAP}</svg>
    <div class="side r"><span>фитнес-клубы<em>клиники, БЦ</em></span>
      <span>внутри МКАД<em>Москва</em></span></div>
  </div>

  <div class="say"><h1>50 таких точек<br><em>по Москве</em></h1>
    <p class="lede">Каждая новая точка — тот же холодильник и та же экономика.</p></div>

  <div class="stats">
    <div class="stat"><b>50</b><span>точек в Москве</span></div>
    <div class="stat"><b style="font-size:22pt">20–25 млн ₽</b><span>прибыль в месяц</span></div>
    <div class="stat"><b style="font-size:24pt">1 млрд ₽</b><span>оценка компании</span></div>
  </div>

  <div class="tl">
    <div><b>Q4 2026</b>15 точек</div>
    <div><b>Q2 2027</b>50 точек, вся Москва</div>
    <div><b>2027+</b>города-миллионники</div>
  </div>

  <div class="foot"><span>Целевая модель на основе экономики действующей точки</span>
    <span>03 / 03</span></div>
</section>
</body></html>
"""

html = (HTML.replace("{AREA}", area).replace("{DW}", dw).replace("{DR}", dr)
        .replace("{PTW}", world_dots).replace("{SHELVES}", "\n".join(shelves))
        .replace("{MAP}", svg_map()))
OUT_HTML.write_text(html, encoding="utf-8")
print("html:", len(html), "bytes")

CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
subprocess.run([CHROME, "--headless", "--no-sandbox", "--disable-gpu",
                "--virtual-time-budget=15000", "--run-all-compositor-stages-before-draw",
                "--no-pdf-header-footer", "--print-to-pdf=" + str(OUT_PDF),
                OUT_HTML.as_uri()], check=True)
print("pdf:", os.path.getsize(OUT_PDF) // 1024, "KB")
