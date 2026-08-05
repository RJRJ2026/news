#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每周新闻周刊 - RSS 自动生成脚本（由 GitHub Actions 每天运行）"""
import feedparser, urllib.parse, re, hashlib, datetime, html as H

FOREIGN_MARKERS = ['bbc', 'dw.com', 'rfi', '共同网', 'kyodo', '路透', '法新', '彭博',
                   '韩联社', 'yna', '半岛', 'aljazeera', '联合早报', 'zaobao',
                   'voa', '美国之音', 'nhk', 'nikkei', '纽约时报', '金融时报', 'ft.com',
                   '卫星通讯社', 'sputnik', '朝鲜日报', '中央日报', '韩民族', '东亚日报',
                   '自由亚洲', 'rfa', '华尔街日报', 'wsj', '日经', '读卖', '朝日新闻',
                   '共同社', '法国国际广播', '德国之声']

FOREIGN_SITES = 'site:bbc.com OR site:dw.com OR site:rfi.fr OR site:china.kyodonews.net OR site:cn.yna.co.kr OR site:voachinese.com'

def is_foreign(src):
    return any(m.lower() in src.lower() for m in FOREIGN_MARKERS)

def title_ok(title):
    if len(title) < 8: return False
    letters = sum(1 for ch in title if ch.isascii() and ch.isalpha())
    return letters / max(len(title), 1) < 0.6

def fetch_news(query, limit=25):
    url = f'https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans'
    d = feedparser.parse(url)
    seen, out = set(), []
    for e in d.entries:
        src = e.get('source', '?')
        src = src.title if hasattr(src, 'title') else str(src)
        title = re.sub(r'\s+', ' ', e.title).strip()
        if not title_ok(title): continue
        key = hashlib.md5(title.encode()).hexdigest()
        if key in seen: continue
        seen.add(key)
        try:
            dt = datetime.datetime(*e.published_parsed[:6])
        except Exception:
            dt = datetime.datetime.now()
        out.append({'title': title, 'src': src, 'link': e.link,
                    'date': dt, 'foreign': is_foreign(src)})
        if len(out) >= limit: break
    return out

def fetch_foreign(query, limit=8):
    q = f'{query} ({FOREIGN_SITES})'
    items = fetch_news(q, limit * 2)
    return [n for n in items if n['foreign']][:limit]

SECTIONS = [
    ('world',  '国际局势', 'World',      '国际 外交 when:2d'),
    ('mil',    '军事动态', 'Military',   '军事 军演 国防 when:2d'),
    ('finance', '财经商业', 'Finance',   '财经 股市 央行 when:2d'),
    ('tech',   '科技前沿', 'Technology', '人工智能 芯片 科技 when:2d'),
    ('life',   '社会民生', 'Society',    '民生 OR 教育 OR 医疗 when:2d'),
    ('sports', '体育赛事', 'Sports',     '体育 中超 篮球 when:2d'),
    ('auto',   '汽车动态', 'Auto',       '汽车 新能源 特斯拉 when:2d'),
]

COLORS = {'world':'var(--blue)','mil':'var(--red)','finance':'var(--teal)',
          'tech':'var(--violet)','life':'var(--amber)','sports':'var(--green)','auto':'var(--blue)'}
TAGS = {'world':'国际','mil':'军事','finance':'财经','tech':'科技','life':'民生','sports':'体育','auto':'汽车'}

def esc(s): return H.escape(s)

def card(sec, item, tag=None):
    label = tag or TAGS[sec]
    color = ('foreign' if item['foreign'] else 'red' if sec=='mil' else 'blue' if sec in ('world','auto') else 'teal' if sec=='finance' else 'violet' if sec=='tech' else 'amber' if sec=='life' else 'green')
    return f'''      <article class="card">
        <div class="row"><span class="tag {color}">{label}</span><span class="date">{item['date'].strftime('%m.%d')}</span></div>
        <h3><a href="{esc(item['link'])}" target="_blank" rel="noopener">{esc(item['title'])}</a></h3>
        <div class="src">来源：{esc(item['src'])}</div>
      </article>'''

CN_NUM = '一二三四五六七八九十'

def build():
    now = datetime.datetime.now()
    today = now.strftime('%Y-%m-%d')
    issue = f'{now.month}月{now.day}日刊'

    top_news = fetch_news('中国 要闻 when:1d', 12) or fetch_news('中国 要闻 when:2d', 12)
    hero_a = top_news[0] if top_news else None
    hero_b = top_news[1] if len(top_news) > 1 else None
    top4 = [n for n in top_news if n is not hero_a and n is not hero_b][:4]

    sections_html, flash_items = [], []
    for idx, (sec_id, sec_name, sec_en, query) in enumerate(SECTIONS):
        items = fetch_news(query, 30)
        dom = [n for n in items if not n['foreign']][:8]
        fgn = [n for n in items if n['foreign']][:4]
        fgn += fetch_foreign(query.replace('when:2d', '').strip() + ' when:2d', 6)
        seen = set(); fgn_u = []
        for n in fgn:
            k = hashlib.md5(n['title'].encode()).hexdigest()
            if k not in seen: seen.add(k); fgn_u.append(n)
        fgn = fgn_u[:6]
        if len(dom) < 8:
            extra = [n for n in items if not n['foreign'] and n not in dom][:8-len(dom)]
            dom = dom + extra
        for n in (dom + fgn)[:10]: flash_items.append(n)
        cards = ''.join(card(sec_id, n) for n in dom)
        if fgn:
            cards += '      <div class="grid-break">🌍 国外媒体视角</div>\n' + ''.join(card(sec_id, n) for n in fgn)
        sections_html.append(f'''  <section id="{sec_id}">
    <div class="sec-head">
      <span class="no" style="color:{COLORS[sec_id]}">{CN_NUM[idx]}</span>
      <h2>{sec_name}</h2>
      <span class="en">{sec_en}</span>
    </div>
    <div class="grid">
{cards}
    </div>
  </section>''')

    seen_f, flash = set(), []
    for n in flash_items:
        k = hashlib.md5(n['title'].encode()).hexdigest()
        if k in seen_f: continue
        seen_f.add(k); flash.append(n)
        if len(flash) >= 16: break
    flash_html = ''.join(f'      <li>{esc(n["title"])}</li>\n' for n in flash)

    def hero_card(item, kicker, dark):
        if not item: return ''
        cls = 'hero-card dark' if dark else 'hero-card light'
        return f'''    <div class="{cls}">
      <div>
        <div class="kicker">{kicker}</div>
        <h2>{esc(item["title"])}</h2>
      </div>
      <div class="meta">{item["src"]} · {item["date"].strftime("%m.%d")}</div>
      <a class="stretch" href="{esc(item["link"])}" target="_blank" rel="noopener"></a>
    </div>'''

    hero = ''
    if hero_a:
        hero += '  <div class="hero">\n' + hero_card(hero_a, '头 条 故 事', True)
        if hero_b:
            hero += '\n' + hero_card(hero_b, '重 要 新 闻', False)
        hero += '\n  </div>'

    top_cards = ''.join(f'''      <article class="card">
        <div class="row"><span class="tag red">头条</span><span class="date">{n["date"].strftime("%m.%d")}</span></div>
        <h3><a href="{esc(n["link"])}" target="_blank" rel="noopener">{esc(n["title"])}</a></h3>
        <div class="src">来源：{esc(n["src"])}</div>
      </article>
''' for n in top4)

    page = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>每周新闻周刊 · {issue}</title>
<meta name="description" content="你的专属新闻周刊：每天自动更新，聚合国际、军事、财经、科技、民生、体育、汽车大事。">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📰</text></svg>">
<meta name="theme-color" content="#f6f4ef">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="新闻周刊">
<style>
  :root {{
    color-scheme: light;
    --bg: #f6f4ef; --card: #ffffff; --ink: #1c1917; --ink-2: #57534e; --ink-3: #a8a29e;
    --line: #e7e2d9; --red: #c0272d; --blue: #2563eb; --teal: #0d9488;
    --violet: #7c3aed; --amber: #d97706; --green: #16a34a;
    --serif: "Noto Serif SC","Songti SC","STSong","SimSun",serif;
    --sans: "PingFang SC","Hiragino Sans GB","Microsoft YaHei",-apple-system,"Segoe UI",sans-serif;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html {{ scroll-behavior: smooth; }}
  body {{ background: var(--bg); color: var(--ink); font-family: var(--sans); line-height: 1.55;
    -webkit-font-smoothing: antialiased; -webkit-tap-highlight-color: transparent; }}
  a {{ color: inherit; text-decoration: none; }}
  .masthead {{ border-bottom: 3px double var(--ink); padding: 36px 24px 22px; text-align: center;
    background: linear-gradient(180deg, #fbfaf7 0%, var(--bg) 100%); }}
  .masthead .flag {{ display: inline-block; font-size: 11px; letter-spacing: 6px; color: var(--red);
    border: 1px solid var(--red); border-radius: 999px; padding: 3px 14px 3px 20px; margin-bottom: 14px; }}
  .masthead h1 {{ font-family: var(--serif); font-size: clamp(30px,5.5vw,50px); font-weight: 900;
    letter-spacing: 0.12em; text-indent: 0.12em; }}
  .masthead .date-range {{ margin-top: 8px; font-size: 13px; color: var(--ink-2); letter-spacing: 2px; }}
  .masthead .date-range b {{ color: var(--ink); font-weight: 600; }}
  nav {{ position: sticky; top: 0; z-index: 50; background: rgba(246,244,239,0.92);
    backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); border-bottom: 1px solid var(--line);
    padding: 8px 12px; display: flex; justify-content: center; align-items: center; gap: 6px;
    flex-wrap: wrap; }}
  nav a {{ font-size: 12.5px; padding: 6px 12px; border-radius: 999px; color: var(--ink-2);
    transition: all .2s; white-space: nowrap; }}
  nav a:hover {{ background: var(--ink); color: #fff; }}
  nav .refresh-btn {{ background: var(--ink); color: #fff; font-weight: 600; padding: 6px 15px;
    margin-left: 2px; display: inline-flex; align-items: center; gap: 5px; }}
  nav .refresh-btn:hover {{ background: var(--red); }}
  nav .refresh-btn:active {{ transform: scale(0.96); }}
  .wrap {{ max-width: 1280px; margin: 0 auto; padding: 0 20px 48px; }}
  .hero {{ display: grid; grid-template-columns: 1.15fr 1fr; gap: 14px; margin: 24px 0 6px; }}
  .hero-card {{ border-radius: 14px; overflow: hidden; padding: 24px 24px 20px;
    display: flex; flex-direction: column; justify-content: space-between; min-height: 240px; position: relative;
    transition: transform .25s ease, box-shadow .25s ease; }}
  .hero-card:hover {{ transform: translateY(-3px); }}
  .hero-card.dark {{ background: linear-gradient(135deg,#231f1c 0%,#3a2f2a 100%); color: #f5f2ec;
    box-shadow: 0 18px 40px -18px rgba(28,25,23,.55); }}
  .hero-card.light {{ background: var(--card); border: 1px solid var(--line);
    box-shadow: 0 18px 40px -22px rgba(28,25,23,.35); }}
  .hero-card .kicker {{ font-size: 11px; letter-spacing: 3px; margin-bottom: 10px; }}
  .hero-card.dark .kicker {{ color: #e8b4a0; }}
  .hero-card.light .kicker {{ color: var(--red); }}
  .hero-card h2 {{ font-family: var(--serif); font-size: clamp(19px,2.3vw,25px); font-weight: 800;
    line-height: 1.35; margin-bottom: 10px; }}
  .hero-card .meta {{ margin-top: 14px; font-size: 11.5px; opacity: .75; letter-spacing: 1px; }}
  .hero-card a.stretch::after {{ content: ""; position: absolute; inset: 0; }}
  section {{ margin-top: 34px; }}
  .sec-head {{ display: flex; align-items: baseline; gap: 12px; border-bottom: 2px solid var(--ink);
    padding-bottom: 8px; margin-bottom: 16px; }}
  .sec-head .no {{ font-family: var(--serif); font-size: 23px; font-weight: 900; line-height: 1; }}
  .sec-head h2 {{ font-family: var(--serif); font-size: 22px; font-weight: 800; }}
  .sec-head .en {{ font-size: 10px; letter-spacing: 3px; color: var(--ink-3); text-transform: uppercase; }}
  .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }}
  .grid-break {{ grid-column: 1 / -1; display: flex; align-items: center; gap: 10px; margin: 8px 0 0;
    font-size: 12px; font-weight: 700; letter-spacing: 2px; color: var(--ink-2); }}
  .grid-break::before, .grid-break::after {{ content: ""; flex: 1; height: 1px; background: var(--line); }}
  @media (max-width: 1120px) {{ .grid {{ grid-template-columns: repeat(3, 1fr); }} .hero {{ grid-template-columns: 1fr; }} }}
  @media (max-width: 860px) {{ .grid {{ grid-template-columns: repeat(2, 1fr); }} }}
  @media (max-width: 600px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  .card {{ background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 15px 14px 12px;
    display: flex; flex-direction: column; gap: 8px;
    transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease; }}
  .card:hover {{ transform: translateY(-2px); box-shadow: 0 12px 26px -16px rgba(28,25,23,.4); border-color: #d8d1c4; }}
  .card .row {{ display: flex; align-items: center; gap: 7px; }}
  .tag {{ font-size: 10.5px; padding: 1.5px 9px; border-radius: 999px; color: #fff;
    font-weight: 600; letter-spacing: 1px; white-space: nowrap; }}
  .tag.red {{ background: var(--red); }} .tag.blue {{ background: var(--blue); }}
  .tag.teal {{ background: var(--teal); }} .tag.violet {{ background: var(--violet); }}
  .tag.amber {{ background: var(--amber); }} .tag.green {{ background: var(--green); }}
  .tag.foreign {{ background: #44403c; }}
  .card .date {{ font-size: 11.5px; color: var(--ink-3); margin-left: auto; white-space: nowrap; }}
  .card h3 {{ font-size: 14.5px; font-weight: 700; line-height: 1.45; }}
  .card h3 a:hover {{ color: var(--red); }}
  .card p {{ font-size: 12.5px; color: var(--ink-2); flex: 1; line-height: 1.55; }}
  .card .src {{ font-size: 11px; color: var(--ink-3); border-top: 1px dashed var(--line); padding-top: 8px; }}
  .flash-list {{ background: var(--card); border: 1px solid var(--line); border-radius: 12px;
    padding: 18px 22px; columns: 3; column-gap: 32px; }}
  @media (max-width: 900px) {{ .flash-list {{ columns: 2; }} }}
  @media (max-width: 560px) {{ .flash-list {{ columns: 1; }} }}
  .flash-list li {{ list-style: none; font-size: 13px; color: var(--ink-2); padding: 6px 0 6px 16px;
    position: relative; break-inside: avoid; }}
  .flash-list li::before {{ content: ""; position: absolute; left: 0; top: 13.5px; width: 6px; height: 6px;
    border-radius: 2px; background: var(--red); opacity: .75; }}
  .modal-mask {{ position: fixed; inset: 0; background: rgba(28,25,23,0.55); backdrop-filter: blur(4px);
    display: none; align-items: center; justify-content: center; z-index: 100; padding: 20px; }}
  .modal-mask.show {{ display: flex; }}
  .modal {{ background: var(--card); border-radius: 18px; max-width: 430px; width: 100%;
    padding: 28px 26px 22px; box-shadow: 0 30px 60px -20px rgba(28,25,23,0.5); animation: modalIn .25s ease; }}
  @keyframes modalIn {{ from {{ opacity: 0; transform: translateY(14px) scale(.97); }} to {{ opacity: 1; transform: none; }} }}
  .modal h3 {{ font-family: var(--serif); font-size: 20px; font-weight: 800; margin-bottom: 4px; }}
  .modal .sub {{ font-size: 12.5px; color: var(--ink-3); margin-bottom: 18px; }}
  .modal .item {{ display: flex; gap: 12px; padding: 12px 0; border-top: 1px solid var(--line); }}
  .modal .item:last-of-type {{ border-bottom: 1px solid var(--line); }}
  .modal .ico {{ flex-shrink: 0; width: 36px; height: 36px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center; font-size: 17px; background: var(--bg); }}
  .modal .item b {{ font-size: 14px; display: block; margin-bottom: 2px; }}
  .modal .item p {{ font-size: 12.5px; color: var(--ink-2); }}
  .modal .actions {{ display: flex; gap: 10px; margin-top: 18px; }}
  .modal .btn {{ flex: 1; text-align: center; padding: 11px 0; border-radius: 10px; font-size: 14px;
    font-weight: 600; cursor: pointer; border: none; font-family: var(--sans); transition: opacity .2s; }}
  .modal .btn.primary {{ background: var(--ink); color: #fff; }}
  .modal .btn.ghost {{ background: var(--bg); color: var(--ink-2); }}
  .modal .btn:active {{ opacity: .75; transform: scale(.98); }}
  @media (max-width: 640px) {{
    .masthead {{ padding: 20px 12px 14px; }}
    .masthead h1 {{ font-size: 24px; letter-spacing: .08em; text-indent: .08em; }}
    .masthead .flag {{ font-size: 9px; letter-spacing: 3px; padding: 2px 10px 2px 14px; margin-bottom: 8px; }}
    .masthead .date-range {{ font-size: 11.5px; margin-top: 6px; }}
    nav {{ padding: 7px 8px; justify-content: flex-start; gap: 5px; }}
    .wrap {{ padding: 0 10px 30px; }}
    .hero {{ gap: 8px; margin-top: 12px; }}
    .hero-card {{ padding: 16px 14px 12px; min-height: 170px; }}
    .hero-card h2 {{ font-size: 16px; margin-bottom: 6px; }}
    .hero-card .meta {{ margin-top: 8px; font-size: 10.5px; }}
    section {{ margin-top: 20px; }}
    .sec-head {{ margin-bottom: 10px; padding-bottom: 6px; }}
    .sec-head h2 {{ font-size: 17px; }}
    .sec-head .no {{ font-size: 18px; }}
    .sec-head .en {{ display: none; }}
    .grid {{ gap: 7px; }}
    .card {{ padding: 10px 9px 8px; gap: 5px; border-radius: 9px; }}
    .card h3 {{ font-size: 13px; line-height: 1.4; }}
    .card .date {{ font-size: 10.5px; }}
    .card .src {{ font-size: 10px; padding-top: 5px; }}
    .tag {{ font-size: 9.5px; padding: 1px 7px; }}
    .grid-break {{ font-size: 11px; margin: 6px 0 0; }}
    .flash-list {{ padding: 10px 12px; }}
    .flash-list li {{ font-size: 12px; padding: 4px 0 4px 13px; }}
    .flash-list li::before {{ top: 10.5px; }}
    footer {{ margin-top: 28px; padding: 18px 10px 28px; }}
    footer p {{ font-size: 10.5px; }}
  }}
  footer {{ border-top: 3px double var(--ink); margin-top: 48px; padding: 24px 24px 40px;
    text-align: center; font-size: 11.5px; color: var(--ink-3); letter-spacing: 1px; }}
  footer .brand {{ font-family: var(--serif); font-size: 15px; color: var(--ink); font-weight: 700;
    letter-spacing: 4px; margin-bottom: 6px; }}
  footer p {{ line-height: 2; }}
</style>
</head>
<body>

<header class="masthead">
  <span class="flag">DAILY DIGEST</span>
  <h1>每周新闻周刊</h1>
  <div class="date-range">{now.month}月{now.day}日 · <b>每天早 8 点自动更新</b></div>
</header>

<nav>
  <a href="#top">本周头条</a>
  <a href="#world">国际局势</a>
  <a href="#mil">军事动态</a>
  <a href="#finance">财经商业</a>
  <a href="#tech">科技前沿</a>
  <a href="#life">社会民生</a>
  <a href="#sports">体育赛事</a>
  <a href="#auto">汽车动态</a>
  <a href="#flash">今日快讯</a>
  <a class="refresh-btn" href="javascript:void(0)" onclick="openRefresh()" title="检查新闻是否已更新">⟳ 刷新新闻</a>
</nav>

<main class="wrap" id="top">

{hero}

  <section id="topstories">
    <div class="sec-head">
      <span class="no" style="color:var(--red)">壹</span>
      <h2>今日头条</h2>
      <span class="en">Top Stories</span>
    </div>
    <div class="grid">
{top_cards}    </div>
  </section>

{''.join(sections_html)}

  <section id="flash">
    <div class="sec-head">
      <span class="no" style="color:var(--ink)">捌</span>
      <h2>今日快讯</h2>
      <span class="en">Briefs</span>
    </div>
    <ul class="flash-list">
{flash_html}    </ul>
  </section>

</main>

<div class="modal-mask" id="refreshModal" onclick="closeRefresh(event)">
  <div class="modal">
    <h3>⟳ 刷新新闻</h3>
    <div class="sub">正在检查是否有最新一期…</div>
    <div id="refreshResult">
      <div class="item"><div class="ico">⏳</div><div><b>检查中</b><p>正在连接服务器检查新闻是否已更新…</p></div></div>
    </div>
    <div class="actions">
      <button class="btn ghost" onclick="closeRefresh()">关闭</button>
      <button class="btn primary" onclick="location.reload()">立即刷新</button>
    </div>
  </div>
</div>

<footer>
  <div class="brand">每周新闻周刊</div>
  <p>本刊由 GitHub 服务器每天自动聚合 Google News 中文源生成 · 点击标题可查看原文</p>
  <p>每天自动更新 · 本期生成于 {today} · 点右上角"刷新新闻"按钮可检查新一期</p>
</footer>

<script>
  var PAGE_VERSION = "{today}";
  function openRefresh() {{
    document.getElementById('refreshModal').classList.add('show');
    document.body.style.overflow = 'hidden';
    checkUpdate();
  }}
  function checkUpdate() {{
    var box = document.getElementById('refreshResult');
    box.innerHTML = '<div class="item"><div class="ico">⏳</div><div><b>检查中</b><p>正在连接服务器检查新闻是否已更新…</p></div></div>';
    var req = new XMLHttpRequest();
    req.open('GET', 'version.json?t=' + Date.now(), true);
    req.timeout = 8000;
    req.onload = function () {{
      try {{
        var v = JSON.parse(req.responseText);
        var tip = document.querySelector('.modal .sub');
        if (v.date > PAGE_VERSION) {{
          box.innerHTML = '<div class="item"><div class="ico">🆕</div><div><b>发现新一期（' + v.issue + '）</b><p>点击下方"立即刷新"按钮，即可看到最新新闻。</p></div></div>';
          if (tip) tip.textContent = '有更新可用';
        }} else {{
          box.innerHTML = '<div class="item"><div class="ico">✅</div><div><b>已是最新一期（' + v.issue + '）</b><p>网站每天早 8 点自动更新。</p></div></div>';
          if (tip) tip.textContent = '当前已是最新';
        }}
      }} catch (e) {{
        box.innerHTML = '<div class="item"><div class="ico">⚠️</div><div><b>检查失败</b><p>无法连接服务器（本地或离线模式）。可点"立即刷新"重载页面。</p></div></div>';
      }}
    }};
    req.onerror = function () {{
      box.innerHTML = '<div class="item"><div class="ico">⚠️</div><div><b>检查失败</b><p>无法连接服务器（本地或离线模式）。可点"立即刷新"重载页面。</p></div></div>';
    }};
    req.send();
  }}
  function closeRefresh(e) {{
    if (e && e.target !== e.currentTarget && e.target.classList && !e.target.classList.contains('btn')) return;
    document.getElementById('refreshModal').classList.remove('show');
    document.body.style.overflow = '';
  }}
  document.addEventListener('keydown', function (e) {{ if (e.key === 'Escape') closeRefresh(); }});
</script>

</body>
</html>
'''
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(page)
    with open('version.json', 'w', encoding='utf-8') as f:
        f.write(f'{{"date": "{today}", "issue": "{issue}"}}')
    print(f'OK: {issue}, {len(page)} bytes, top={len(top_news)}, sections done')

if __name__ == '__main__':
    build()
