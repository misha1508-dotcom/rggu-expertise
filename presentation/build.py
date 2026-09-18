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

def trend_paths(w=470.0, h=170.0, pad_l=30.0, pad_b=26.0, pad_t=12.0):
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
year_labels = "\n".join('<text class="ax" x="%.1f" y="164" text-anchor="middle">%s</text>' % (p[0], y)
                        for p, y in zip(pw, TREND_YEARS))
world_dots = "\n".join('<circle class="pt-w" cx="%.1f" cy="%.1f" r="3.1"/>' % p for p in pw)
ru_dots = "\n".join('<circle class="pt-r" cx="%.1f" cy="%.1f" r="2.6"/>' % p for p in pr)

grid = []
for v in (0, 25, 50, 75, 100):
    y = 12 + (170 - 12 - 26) * (1 - v / 100.0)
    grid.append('<line class="grid-l" x1="30" y1="%.1f" x2="492" y2="%.1f"/>' % (y, y))
    grid.append('<text class="ax" x="24" y="%.1f" text-anchor="end">%d</text>' % (y + 2.5, v))

# полки: 4 полки × 5 пачек по 6 бутылок
shelves = []
for sy in (104, 170, 236, 302):
    shelves.append('<line x1="55" y1="%d" x2="175" y2="%d" stroke="#C7D8D6" stroke-width="2.4"/>'
                   % (sy + 28, sy + 28))
    for pi in range(5):
        px = 57 + pi * 24
        shelves.append('<rect x="%d" y="%d" width="21" height="26" rx="2.6" '
                       'fill="#F6E7A8" stroke="#C9A94E" stroke-width="1.4"/>' % (px, sy + 2))
        for bi in range(3):
            shelves.append('<rect x="%.1f" y="%d" width="4.6" height="4" rx="1.2" fill="#6B6B6B"/>'
                           % (px + 2.4 + bi * 6, sy))
        shelves.append('<rect x="%.1f" y="%d" width="13" height="6" rx="1" fill="#fff" opacity=".92"/>'
                       % (px + 4, sy + 12))
shelves.append('<line x1="55" y1="366" x2="175" y2="366" stroke="#C7D8D6" stroke-width="2.4"/>')

callouts = [(206, 60, "1"), (206, 19, "2"), (16, 169, "3"), (206, 200, "4")]
bullets = []
for x, y, n in callouts:
    bullets.append('<circle class="bullet" cx="%d" cy="%d" r="7.4"/>'
                   '<text class="bullet-t" x="%d" y="%.1f" text-anchor="middle">%s</text>'
                   % (x, y, x, y + 2.8, n))
leads = "\n".join([
    '<line class="lead" x1="188" y1="60" x2="206" y2="60"/>',
    '<line class="lead" x1="132" y1="19" x2="206" y2="19"/>',
    '<line class="lead" x1="30" y1="169" x2="16" y2="169"/>',
    '<line class="lead" x1="188" y1="200" x2="206" y2="200"/>',
])

# ---------------------------------------------------------------- HTML
HTML = u"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<title>БИОПРАЙМ — презентация</title>
<link rel="stylesheet" href="fonts/manrope.css">
<style>
:root{--ink:#0C1A18;--ink2:#2C3E3B;--mut:#6E817D;--mint:#7FD9D1;--mint-l:#D8F4F1;
  --mint-d:#0E6F68;--gold:#E8C46A;--line:#E3E7E5;--panel:#F5F7F6;--dark:#0F2422}
*{box-sizing:border-box;margin:0;padding:0}
@page{size:A4 portrait;margin:0}
html,body{font-family:'Manrope','DejaVu Sans',sans-serif;color:var(--ink);
  -webkit-print-color-adjust:exact;print-color-adjust:exact}
.page{width:210mm;height:297mm;padding:14mm 14mm 10mm;position:relative;overflow:hidden;
  background:#fff;page-break-after:always;display:flex;flex-direction:column}
.page:last-child{page-break-after:auto}

.head{display:flex;align-items:center;justify-content:space-between;padding-bottom:3.6mm;
  border-bottom:1.6px solid var(--ink);margin-bottom:6mm;flex:0 0 auto}
.brand{display:flex;align-items:center;gap:2.6mm}
.mark{width:8.4mm;height:8.4mm;border-radius:2.4mm;background:var(--mint);display:flex;
  align-items:center;justify-content:center;font-weight:800;font-size:10.5pt;color:#0B3B37}
.bname{font-weight:800;font-size:12.6pt;letter-spacing:.09em}
.btag{font-size:6.6pt;color:var(--mut);letter-spacing:.16em;text-transform:uppercase;margin-top:.4mm}
.pnum{font-size:7.4pt;letter-spacing:.2em;text-transform:uppercase;color:var(--mut);
  font-weight:700;text-align:right}
.pnum b{display:block;font-size:20pt;letter-spacing:0;color:var(--ink);line-height:1}

h1{font-size:24pt;line-height:1.1;font-weight:800;letter-spacing:-.02em}
h1 em{font-style:normal;color:var(--mint-d)}
.sub{font-size:9.4pt;color:var(--ink2);line-height:1.45;margin-top:3mm;max-width:155mm}
.kicker{font-size:7.2pt;font-weight:800;letter-spacing:.2em;text-transform:uppercase;
  color:var(--mint-d);margin-bottom:2.4mm}
.card{background:var(--panel);border-radius:4mm;padding:5mm}
.card.out{background:#fff;border:1px solid var(--line)}
.dark{background:var(--dark);color:#fff}.dark .mut{color:#9FBDB8}
.mut{color:var(--mut)}
.ttl{font-size:8.4pt;font-weight:800;letter-spacing:.11em;text-transform:uppercase;color:var(--mut)}
.shot{border-radius:4mm;overflow:hidden;position:relative;background:#eee}
.shot img{width:100%;height:100%;object-fit:cover;display:block}
.shot .cap{position:absolute;left:0;right:0;bottom:0;padding:3mm;font-size:7pt;color:#fff;
  background:linear-gradient(transparent,rgba(6,20,18,.82))}

/* ---------- страница 1 ---------- */
.p1-hero{display:grid;grid-template-columns:60mm 1fr;gap:5mm;margin-top:7mm;flex:0 0 auto}
.chart-wrap{padding:4.5mm 5mm 3.5mm}
.legend{display:flex;gap:5mm;font-size:7.4pt;font-weight:700;margin-top:1.4mm}
.legend i{display:inline-block;width:3.4mm;height:1.5mm;border-radius:2px;margin-right:1.4mm;
  vertical-align:middle}
svg text.ax{font-family:'Manrope',sans-serif;font-size:7px;fill:#8C9C99;font-weight:700}
.grid-l{stroke:#E3E7E5;stroke-width:1}
.ln-w{fill:none;stroke:#0E6F68;stroke-width:2.6;stroke-linecap:round}
.ln-r{fill:none;stroke:#E8B93F;stroke-width:2.2;stroke-dasharray:4 3;stroke-linecap:round}
.pt-w{fill:#0E6F68}.pt-r{fill:#E8B93F}.ar{fill:url(#g1)}

.kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:3.4mm;margin-top:7mm;flex:1 1 auto}
.kpi{background:var(--panel);border-radius:3.4mm;padding:5mm 4.5mm;display:flex;
  flex-direction:column;justify-content:center}
.kpi b{display:block;font-size:21pt;font-weight:800;line-height:1;letter-spacing:-.02em;color:var(--mint-d)}
.kpi span{display:block;font-size:7.6pt;color:var(--ink2);margin-top:2.2mm;line-height:1.35}

.voices{display:grid;grid-template-columns:repeat(3,1fr);gap:3.4mm;margin-top:7mm;flex:1 1 auto}
.voice{border:1px solid var(--line);border-radius:3.4mm;padding:5mm 4.5mm;display:flex;
  flex-direction:column;justify-content:center}
.voice h4{font-size:10pt;font-weight:800;line-height:1.15}
.voice .role{font-size:7.4pt;color:var(--mut);margin-top:1.6mm;line-height:1.35}
.ava{width:7.4mm;height:7.4mm;border-radius:99px;background:var(--mint);margin-bottom:3mm;
  display:flex;align-items:center;justify-content:center;font-weight:800;font-size:8pt;color:#0B3B37}

.insight{margin-top:7mm;border-radius:4mm;padding:6mm;display:flex;gap:5mm;align-items:center}
.insight .big{font-size:29pt;font-weight:800;line-height:1;color:var(--mint);white-space:nowrap}
.insight .big s{text-decoration:none;display:block;font-size:8pt;color:#9FBDB8;margin-top:1.4mm;
  font-weight:700}
.insight p{font-size:9.4pt;line-height:1.45}
.insight p b{color:var(--mint)}

/* ---------- страница 2 ---------- */
.p2{display:grid;grid-template-columns:76mm 1fr;gap:5mm;margin-top:6mm;flex:1 1 auto}
.p2 .right{display:flex;flex-direction:column;gap:4.5mm}
.photos{display:grid;grid-template-columns:1fr 1fr;gap:3mm;height:60mm}
.photos .shot img{object-position:center 38%}
.clist{margin:4mm 0 0 0;padding:0;list-style:none;counter-reset:c}
.clist li{counter-increment:c;position:relative;padding-left:7mm;font-size:8pt;line-height:1.35;
  color:var(--ink2);margin-bottom:3mm}
.clist li:last-child{margin-bottom:0}
.clist li b{color:var(--ink);font-weight:800}
.clist li::before{content:counter(c);position:absolute;left:0;top:0;width:4.8mm;height:4.8mm;
  border-radius:99px;background:var(--mint-d);color:#fff;font-size:6.6pt;font-weight:800;
  display:flex;align-items:center;justify-content:center}
.flow{display:grid;grid-template-columns:repeat(3,1fr);gap:2.6mm}
.step{background:var(--panel);border-radius:3mm;padding:3.6mm}
.step b{display:block;font-size:7.4pt;color:var(--mint-d);font-weight:800;margin-bottom:1.4mm}
.step span{font-size:7.6pt;line-height:1.35;display:block}
.eco{border:1px solid var(--line);border-radius:4mm;padding:4.5mm 5mm}
.eco table{width:100%;border-collapse:collapse;font-size:8.4pt}
.eco td{padding:1.9mm 0;border-bottom:1px dashed var(--line)}
.eco td:last-child{text-align:right;font-weight:800;font-variant-numeric:tabular-nums}
.eco tr.tot td{border-bottom:none;padding-top:3mm;font-size:10pt;font-weight:800}
.eco tr.tot td:last-child{color:var(--mint-d);font-size:12.5pt}
.eco tr.neg td:last-child{color:#B4643C}
.mar{display:grid;grid-template-columns:28mm 1fr;gap:4mm;align-items:center}
.mar .lab{font-size:7.8pt;line-height:1.4}
svg .donut-bg{fill:none;stroke:#26403D;stroke-width:11}
svg .donut-v{fill:none;stroke:var(--mint);stroke-width:11;stroke-linecap:round}
.lead{stroke:#B9C6C3;stroke-width:1}
.bullet{fill:#0E6F68}
.bullet-t{font-family:'Manrope',sans-serif;font-size:7px;fill:#fff;font-weight:800}

/* ---------- страница 3 ---------- */
.p3{display:grid;grid-template-columns:1fr 64mm;gap:5mm;margin-top:6mm;flex:1 1 auto}
.p3>div:last-child{display:flex;flex-direction:column;gap:3.4mm}
.mapcard{background:var(--dark);border-radius:4mm;padding:4.5mm;display:flex;flex-direction:column}
.mk-fill{fill:#16332F}.mk-ring{fill:none;stroke:#3E6E68;stroke-width:2}
.ttk,.sad{fill:none;stroke:#2C544F;stroke-width:1.3}
.radial{stroke:#22453F;stroke-width:1}
.river{fill:none;stroke:#2E6E9E;stroke-width:3.4;stroke-linecap:round;opacity:.75}
.kremlin{fill:#E8C46A}
.dot1{fill:#7FD9D1}.dot1-h{fill:#7FD9D1;opacity:.22}
.dot2{fill:#E8C46A}.dot2-h{fill:#E8C46A;opacity:.18}
.maplegend{display:flex;gap:5mm;font-size:7.2pt;color:#CDE3E0;font-weight:700;margin-top:2mm}
.maplegend i{width:2.6mm;height:2.6mm;border-radius:99px;display:inline-block;margin-right:1.4mm}
.rung{border:1px solid var(--line);border-radius:3.4mm;padding:4mm 4.5mm}
.rung.now{background:var(--mint-l);border-color:#A9E4DE}
.rung .n{font-size:7pt;font-weight:800;letter-spacing:.14em;text-transform:uppercase;color:var(--mut)}
.rung .v{font-size:17pt;font-weight:800;line-height:1.05;margin-top:1.6mm;letter-spacing:-.02em}
.rung .d{font-size:7.6pt;color:var(--ink2);margin-top:1.4mm;line-height:1.35}
.val{border-radius:4mm;padding:5mm;margin-top:auto}
.val .v{font-size:29pt;font-weight:800;line-height:1;color:var(--mint);letter-spacing:-.03em}
.val .d{font-size:8.2pt;color:#B9D6D2;margin-top:2.6mm;line-height:1.45}
.tl{display:grid;grid-template-columns:repeat(3,1fr);gap:3mm;margin-top:5mm;flex:0 0 auto}
.tl .t{border-top:2.4px solid var(--mint);padding-top:3mm}
.tl .t b{display:block;font-size:9pt;font-weight:800}
.tl .t span{font-size:7.6pt;color:var(--ink2);line-height:1.35;display:block;margin-top:1mm}
.tl .t.g{border-color:var(--gold)}
.foot{margin-top:5mm;padding-top:2.8mm;border-top:1px solid var(--line);display:flex;
  justify-content:space-between;font-size:6.6pt;color:var(--mut);flex:0 0 auto}
</style></head><body>

<!-- ============================ СТРАНИЦА 1 ============================ -->
<section class="page">
  <div class="head">
    <div class="brand"><div class="mark">Б</div>
      <div><div class="bname">БИОПРАЙМ</div><div class="btag">Пробиотик L. reuteri · курс</div></div></div>
    <div class="pnum">Продукт и спрос<b>01</b></div>
  </div>

  <div class="kicker">Спрос создали врачи, а не маркетологи</div>
  <h1>Люди уже ищут <em>L. reuteri</em> по имени —<br>и варят её дома по 36 часов</h1>
  <p class="sub">Мы продаём готовый пробиотический продукт: бутылка 250 мл — порция на день,
  терапевтическая доза L.&nbsp;reuteri 1×10⁶&nbsp;КОЕ. Пачка из 6 бутылок — курс на неделю.</p>

  <div class="p1-hero">
    <div class="shot"><img src="assets/p_bottle.jpg" alt="Пачка БИОПРАЙМ">
      <div class="cap">Пачка 6 × 250 мл · курс на неделю</div></div>
    <div class="card chart-wrap">
      <div class="ttl">Поисковый интерес к «L. reuteri / йогурт реутери»</div>
      <svg viewBox="0 0 500 175" style="width:100%;height:auto;margin-top:2.4mm">
        <defs><linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#0E6F68" stop-opacity=".22"/>
          <stop offset="1" stop-color="#0E6F68" stop-opacity="0"/></linearGradient></defs>
        {GRID}<path class="ar" d="{AREA}"/><path class="ln-r" d="{DR}"/><path class="ln-w" d="{DW}"/>
        {PTW}{PTR}{YEARS}
      </svg>
      <div class="legend"><span><i style="background:#0E6F68"></i>мир</span>
        <span><i style="background:#E8B93F"></i>Россия</span>
        <span class="mut" style="font-weight:600">2026 = 100 · оценка по Google&nbsp;Trends / Яндекс&nbsp;Wordstat</span></div>
    </div>
  </div>

  <div class="kpis">
    <div class="kpi"><b>×16</b><span>рост поисковых запросов по штамму за 4 года</span></div>
    <div class="kpi"><b>250 мл</b><span>порция на день, терапевтическая доза 1×10⁶ КОЕ</span></div>
    <div class="kpi"><b>0</b><span>готовых конкурентов в формате «взял и выпил»</span></div>
  </div>

  <div class="voices">
    <div class="voice"><div class="ava">WD</div><h4>Доктор Уильям Дэвис</h4>
      <div class="role">Кардиолог, автор «Super Gut», №1 бестселлер NYT. Его протокол сделал L.&nbsp;reuteri массовым запросом</div></div>
    <div class="voice"><div class="ava">АЛ</div><h4>Анна Лиана</h4>
      <div class="role">YouTube-канал о ЗОЖ и ферментации — главный русскоязычный проводник протокола</div></div>
    <div class="voice"><div class="ava">RU</div><h4>Рынок подтверждён</h4>
      <div class="role">Telegram-сообщества, закваски на маркетплейсах и полка «Слобода&nbsp;L.&nbsp;REUTERI» в рознице</div></div>
  </div>

  <div class="insight card dark">
    <div class="big">1 250 ₽<s>пачка 6 × 250 мл</s></div>
    <p>Продаём не бутылку, а <b>курс</b>. Человек платит за 36 сэкономленных часов и
    гарантированный штамм — поэтому себестоимость держится в 25 % от цены,
    а валовая маржа продукта — <b>75&nbsp;%</b>.</p>
  </div>

  <div class="foot"><span>БИОПРАЙМ · инвестиционная презентация</span><span>Москва · 2026</span></div>
</section>

<!-- ============================ СТРАНИЦА 2 ============================ -->
<section class="page">
  <div class="head">
    <div class="brand"><div class="mark">Б</div>
      <div><div class="bname">БИОПРАЙМ</div><div class="btag">Пробиотик L. reuteri · курс</div></div></div>
    <div class="pnum">Единица масштабирования<b>02</b></div>
  </div>

  <div class="kicker">Один холодильник = одна точка продаж</div>
  <h1>Брендированный холодильник <em>с камерой</em><br>и оплатой без продавца</h1>
  <p class="sub">Автономная точка на 0,5 м² там, где уже есть наша аудитория: фитнес-клубы,
  клиники, БЦ. Ноль персонала, ноль аренды торговой площади.</p>

  <div class="p2">
    <div class="card out" style="padding:5mm 4.5mm;display:flex;flex-direction:column">
      <div class="ttl" style="margin-bottom:1.5mm">Точка продаж</div>
      <svg viewBox="0 0 230 396" style="width:100%;height:auto">
        <rect x="98" y="8" width="34" height="22" rx="5" fill="#1B2B29"/>
        <circle cx="115" cy="19" r="6.4" fill="#5BD6CE"/><circle cx="115" cy="19" r="3" fill="#0B1A19"/>
        <rect x="112" y="30" width="6" height="12" fill="#1B2B29"/>
        <line x1="102" y1="8" x2="94" y2="0" stroke="#1B2B29" stroke-width="2"/>
        <line x1="128" y1="8" x2="136" y2="0" stroke="#1B2B29" stroke-width="2"/>
        <rect x="42" y="42" width="146" height="36" rx="5" fill="#8EE0D9" stroke="#0F2422" stroke-width="2.4"/>
        <text x="115" y="59" text-anchor="middle" font-family="Manrope" font-size="10" font-weight="800" fill="#6A4A22">ЗДЕСЬ НАЧНЁТСЯ</text>
        <text x="115" y="72" text-anchor="middle" font-family="Manrope" font-size="11.5" font-weight="800" fill="#4A3214">ТВОЙ ПРАЙМ</text>
        <rect x="42" y="82" width="146" height="300" rx="7" fill="#101D1C"/>
        <rect x="51" y="91" width="128" height="282" rx="4" fill="#F4FBFA" stroke="#D3E3E1"/>
        {SHELVES}
        <path d="M 64 93 L 100 93 L 64 371 L 51 371 Z" fill="#fff" opacity=".32"/>
        <rect x="30" y="150" width="19" height="38" rx="4" fill="#12211F"/>
        <rect x="33" y="159" width="13" height="18" rx="2" fill="#BFE9FF"/>
        <rect x="46" y="222" width="5" height="42" rx="2.5" fill="#3B4F4C"/>
        <g stroke-linecap="round">{LEADS}</g>
        {BULLETS}
      </svg>
      <ol class="clist">
        <li><b>Лайтбокс-вывеска</b> — реклама бренда 24/7 в потоке клуба</li>
        <li><b>Камера с онлайн-доступом</b> — остатки и антивандал</li>
        <li><b>Терминал</b> — оплата картой или QR&nbsp;СБП</li>
        <li><b>20 пачек загрузки</b> — 4 полки × 5 пачек по 6 бутылок</li>
      </ol>
    </div>

    <div class="right">
      <div class="photos">
        <div class="shot"><img src="assets/p_fridge_cam.jpg" alt="Холодильник с камерой">
          <div class="cap">Реальная точка · камера 24/7</div></div>
        <div class="shot"><img src="assets/p_fridge_full.jpg" alt="Холодильник БИОПРАЙМ">
          <div class="cap">Загрузка — 20 пачек</div></div>
      </div>

      <div>
        <div class="ttl" style="margin-bottom:2.6mm">Система выдачи — без продавца</div>
        <div class="flow">
          <div class="step"><b>ШАГ 1</b><span>Оплата картой или QR&nbsp;СБП на терминале двери</span></div>
          <div class="step"><b>ШАГ 2</b><span>Замок открывается, покупатель берёт пачку</span></div>
          <div class="step"><b>ШАГ 3</b><span>Чек и остатки — сразу в CRM</span></div>
        </div>
      </div>

      <div class="eco">
        <div class="ttl" style="margin-bottom:3mm">Юнит-экономика точки · месяц</div>
        <table>
          <tr><td>Продажи: 18 пачек в день</td><td>540 пачек</td></tr>
          <tr><td>Выручка (1 250 ₽ за пачку)</td><td>675 000 ₽</td></tr>
          <tr class="neg"><td>Себестоимость продукта (25 %)</td><td>−168 750 ₽</td></tr>
          <tr class="neg"><td>Место, логистика, эквайринг, сервис</td><td>−58 500 ₽</td></tr>
          <tr class="tot"><td>Прибыль точки</td><td>≈ 447 000 ₽</td></tr>
        </table>
      </div>

      <div class="card dark" style="padding:4.5mm 5mm">
        <div class="mar">
          <svg viewBox="0 0 100 100" style="width:25mm;height:25mm">
            <circle class="donut-bg" cx="50" cy="50" r="38"/>
            <circle class="donut-v" cx="50" cy="50" r="38" stroke-dasharray="179 239" transform="rotate(-90 50 50)"/>
            <text x="50" y="46" text-anchor="middle" font-family="Manrope" font-size="22" font-weight="800" fill="#fff">75%</text>
            <text x="50" y="64" text-anchor="middle" font-family="Manrope" font-size="7.2" font-weight="700" fill="#9FBDB8">валовая маржа</text>
          </svg>
          <div class="lab"><b style="font-size:9.4pt">Откуда маржа 75 %</b><br>
            <span class="mut">Своё производство · нет продавца в ФОТ · договор о размещении
            вместо аренды торговой площади.<br>
            <b style="color:#fff">CAPEX точки ≈ 180 тыс. ₽ → окупаемость 1,5–2 месяца.</b></span></div>
        </div>
      </div>
    </div>
  </div>

  <div class="foot"><span>БИОПРАЙМ · единица масштабирования</span><span>02 / 03</span></div>
</section>

<!-- ============================ СТРАНИЦА 3 ============================ -->
<section class="page">
  <div class="head">
    <div class="brand"><div class="mark">Б</div>
      <div><div class="bname">БИОПРАЙМ</div><div class="btag">Пробиотик L. reuteri · курс</div></div></div>
    <div class="pnum">Масштабирование<b>03</b></div>
  </div>

  <div class="kicker">Тиражирование одной доказанной точки</div>
  <h1>50 холодильников в Москве —<br><em>20–25 млн ₽</em> прибыли в месяц</h1>
  <p class="sub">Каждая новая точка — тот же холодильник, тот же продукт и та же экономика.
  Рост ограничен логистикой производства, а не поиском покупателя.</p>

  <div class="p3">
    <div class="mapcard">
      <div style="display:flex;justify-content:space-between;align-items:flex-start">
        <div><div class="ttl" style="color:#9FBDB8">Карта развёртывания · Москва</div>
        <div style="font-size:12.5pt;font-weight:800;color:#fff;margin-top:1mm">50 точек внутри МКАД</div></div>
        <div style="text-align:right;color:#CDE3E0;font-size:7.2pt;line-height:1.4">
          фитнес-клубы · клиники<br>БЦ · wellness-студии</div>
      </div>
      <div style="flex:1 1 auto;display:flex;align-items:center">
        <svg viewBox="0 0 500 500" style="width:100%;height:auto">{MAP}</svg></div>
      <div class="maplegend">
        <span><i style="background:#7FD9D1"></i>волна 1 — 15 точек</span>
        <span><i style="background:#E8C46A"></i>волна 2 — 35 точек</span></div>
    </div>

    <div>
      <div class="rung now"><div class="n">Сегодня · 1 точка</div>
        <div class="v">0,45 млн ₽</div>
        <div class="d">прибыль в месяц — экономика подтверждена в работающем холодильнике</div></div>
      <div class="rung"><div class="n">9 мес. · 50 точек</div>
        <div class="v">20–25 млн ₽</div>
        <div class="d">прибыль в месяц при выручке 34–40 млн ₽</div></div>
      <div class="rung" style="border-color:#D8CFAE;background:#FCF8EC">
        <div class="n" style="color:#8A6D22">Нужно для роста</div>
        <div class="v" style="font-size:15pt">9 млн ₽ CAPEX</div>
        <div class="d">50 × 180 тыс. ₽ на точку + оборотный капитал и линия ферментации</div></div>
      <div class="val card dark"><div class="ttl" style="color:#9FBDB8">Оценка компании</div>
        <div class="v">1 млрд ₽</div>
        <div class="d">245–300 млн ₽ EBITDA в год при сети 50 точек — это
        ≈ <b style="color:#fff">3,5–4× годовой EBITDA</b>, консервативный мультипликатор
        для FMCG-сети со своим производством.</div></div>
    </div>
  </div>

  <div class="tl">
    <div class="t"><b>Q4 2026</b><span>15 точек · выход на плановую загрузку</span></div>
    <div class="t"><b>Q2 2027</b><span>50 точек · 20–25 млн ₽/мес, полный охват Москвы</span></div>
    <div class="t g"><b>2027+</b><span>Санкт-Петербург и города-миллионники</span></div>
  </div>

  <div class="foot"><span>Финансовые показатели — целевая модель на основе экономики действующей точки</span>
    <span>03 / 03</span></div>
</section>
</body></html>
"""

html = (HTML.replace("{GRID}", "\n".join(grid)).replace("{AREA}", area)
        .replace("{DW}", dw).replace("{DR}", dr)
        .replace("{PTW}", world_dots).replace("{PTR}", ru_dots).replace("{YEARS}", year_labels)
        .replace("{SHELVES}", "\n".join(shelves)).replace("{LEADS}", leads)
        .replace("{BULLETS}", "\n".join(bullets)).replace("{MAP}", svg_map()))

OUT_HTML.write_text(html, encoding="utf-8")
print("html:", len(html), "bytes")

CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
subprocess.run([CHROME, "--headless", "--no-sandbox", "--disable-gpu",
                "--virtual-time-budget=15000", "--run-all-compositor-stages-before-draw",
                "--no-pdf-header-footer", "--print-to-pdf=" + str(OUT_PDF),
                OUT_HTML.as_uri()], check=True)
print("pdf:", os.path.getsize(OUT_PDF) // 1024, "KB")
