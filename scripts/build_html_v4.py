# -*- coding: utf-8 -*-
"""
report_v4.md → report_v4_readable.html

独立生成器，不改动 md_to_html.py 与 report.html（v3 原文件保留）。
设计目标：左侧固定目录 + 右侧正文的证券研究报告电子阅读版。
- 图片 base64 内嵌（自包含，不留失效链接），10 张图全部保留并包成 figure/figcaption
- 稳定锚点 ch-1..ch-10 / sec-N-M，目录文字与正文标题同源生成
- 当前章节高亮（scroll + rAF 节流，快速滚动不闪烁）、第8章子目录折叠、移动端抽屉
- CSS 变量统一管理字体/字号/行高/颜色/间距/宽度；移动端与打印样式齐全
- 只做呈现：正文来自 report_v4.md，不新增或修改任何研究数据
"""
import base64
import re
from pathlib import Path

import markdown as _md

BASE = Path(__file__).parent
SRC = BASE / "report_v4.md"
DST = BASE / "report_v4_readable.html"

CSS = r"""
:root{
  --font:"Microsoft YaHei UI","Microsoft YaHei","PingFang SC","Noto Sans CJK SC","Source Han Sans SC","Heiti SC",Arial,sans-serif;
  --fz-h1:32px; --fz-sub:15px; --fz-h2:24px; --fz-h3:18px; --fz-h4:16px;
  --fz-body:16px; --fz-table:14px; --fz-th:14px; --fz-figcap:15px;
  --fz-notes:12.5px; --fz-source:12px; --fz-footer:12px; --fz-side:13.5px;
  --lh-body:1.85; --lh-h1:1.4; --lh-h2:1.45; --lh-h3:1.5; --lh-table:1.55; --lh-notes:1.55;
  --ink:#1F2937; --title:#172033; --muted:#64748B; --line:#E2E8F0;
  --accent:#315B9A; --accent-soft:#E8EEF6; --bg:#F5F7FA; --paper:#FFFFFF; --risk:#B42318;
  --sidebar-w:250px; --gap:36px; --page-max:1480px; --content-max:900px; --text-max:780px;
  --sp-para:14px; --sp-sub:24px; --sp-chapter:44px; --sp-head:12px;
}
*{box-sizing:border-box;}
html{scroll-behavior:smooth;-webkit-text-size-adjust:100%;}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--font);
     font-size:var(--fz-body);line-height:var(--lh-body);font-weight:400;
     font-variant-numeric:tabular-nums;font-feature-settings:"tnum";}
.page-layout{max-width:var(--page-max);margin:0 auto;padding:0 32px;
             display:grid;grid-template-columns:var(--sidebar-w) minmax(0,1fr);gap:var(--gap);align-items:start;}

/* ── 左侧目录 ── */
.sidebar{position:sticky;top:0;height:100vh;overflow-y:auto;overscroll-behavior:contain;
         padding:34px 12px 40px 0;border-right:1px solid var(--line);scrollbar-width:thin;}
.sidebar-head{font-size:12px;font-weight:600;letter-spacing:.08em;color:var(--muted);
              text-transform:none;margin:0 0 14px 10px;display:flex;align-items:center;justify-content:space-between;}
.sidebar-nav ul{list-style:none;margin:0;padding:0;}
.sidebar-nav .toc-list>li{margin:0;}
.sidebar-nav .toc-sub{padding:0 0 6px 14px;border-left:1px solid var(--line);margin-left:10px;}
.sidebar-nav a{display:block;padding:7px 10px;color:#475569;text-decoration:none;font-size:var(--fz-side);
               line-height:1.55;border-radius:3px;border-left:3px solid transparent;}
.sidebar-nav a:hover{background:#EEF2F7;color:var(--accent);}
.sidebar-nav a.active{background:var(--accent-soft);color:#1F3F6B;border-left-color:var(--accent);font-weight:600;}
.sidebar-nav a.active-parent{color:var(--accent);font-weight:600;}
.sidebar-nav .toc-sub a{font-size:12.5px;padding:5px 10px;color:var(--muted);}
.sidebar-nav .toc-sub a.active{color:#1F3F6B;}
.has-children{position:relative;}
.toc-toggle{position:absolute;right:2px;top:5px;width:22px;height:22px;line-height:20px;
            border:0;background:transparent;color:var(--muted);font-size:14px;cursor:pointer;border-radius:3px;}
.toc-toggle:hover{background:#EEF2F7;color:var(--accent);}
.toc-sub.collapsed{display:none;}
#menu-close{display:none;}

/* ── 右侧正文 ── */
.main-content{background:var(--paper);border:1px solid var(--line);border-top:0;
              min-height:100vh;padding:0 clamp(28px,5vw,72px) 72px;}
.report-header{padding:52px 0 28px;border-bottom:1px solid var(--line);margin-bottom:8px;}
.eyebrow{font-size:var(--fz-source);color:var(--accent);letter-spacing:.06em;margin:0 0 12px;font-weight:600;}
h1{font-size:var(--fz-h1);font-weight:600;line-height:var(--lh-h1);color:var(--title);
   margin:0 0 12px;letter-spacing:-.01em;}
.subtitle{font-size:var(--fz-sub);font-weight:400;color:var(--muted);line-height:1.6;margin:0 0 18px;}
.header-meta{font-size:var(--fz-source);color:var(--muted);line-height:1.6;}
.report-body{max-width:var(--content-max);}
.report-body>h2,.report-body>h3,.report-body>p,.report-body>ul,.report-body>ol,
.report-body>blockquote,.report-body>.exhibit-standalone{max-width:var(--text-max);}
h2{font-size:var(--fz-h2);font-weight:600;line-height:var(--lh-h2);color:var(--title);
   margin:var(--sp-chapter) 0 var(--sp-head);padding-bottom:10px;border-bottom:1px solid var(--line);
   scroll-margin-top:20px;}
h3{font-size:var(--fz-h3);font-weight:600;line-height:var(--lh-h3);color:var(--title);
   margin:var(--sp-sub) 0 10px;scroll-margin-top:20px;}
h4{font-size:var(--fz-h4);font-weight:600;line-height:1.5;margin:18px 0 8px;}
p{margin:0 0 var(--sp-para);}
strong{font-weight:600;color:var(--title);}
ul,ol{margin:0 0 var(--sp-para);padding-left:24px;}
li{margin:0 0 6px;}
a{color:var(--accent);text-decoration:none;}
a:hover{text-decoration:underline;}
code{font-size:.9em;background:#F1F5F9;padding:1px 5px;border-radius:3px;
     font-family:var(--font);}
pre{background:#F8FAFC;border:1px solid var(--line);border-radius:3px;padding:16px 18px;
    overflow-x:auto;font-size:var(--fz-source);line-height:1.7;max-width:var(--text-max);}
pre code{background:none;padding:0;}
blockquote{margin:16px 0 var(--sp-para);padding:10px 16px;background:#F8FAFC;
           border-left:3px solid #CBD5E1;color:#475569;font-size:var(--fz-notes);line-height:var(--lh-notes);}
blockquote p{margin:0 0 4px;}
blockquote p:last-child{margin:0;}
hr{border:0;border-top:1px solid var(--line);margin:36px 0;max-width:var(--text-max);}

/* ── 表格 ── */
.table-wrap{overflow-x:auto;margin:18px 0 22px;max-width:var(--content-max);
            -webkit-overflow-scrolling:touch;}
table{width:100%;border-collapse:collapse;font-size:var(--fz-table);line-height:var(--lh-table);}
th{background:#EEF2F7;color:#334155;font-size:var(--fz-th);font-weight:600;text-align:left;
   white-space:nowrap;padding:10px 12px;border-bottom:2px solid #CBD5E1;}
td{padding:9px 12px;border-bottom:1px solid var(--line);vertical-align:top;color:var(--ink);}
tbody tr:nth-child(even){background:#FAFBFC;}
tbody tr:last-child td{border-bottom:1px solid var(--line);}
th,td{font-variant-numeric:tabular-nums;font-feature-settings:"tnum";}
th[style*="right"],td[style*="right"]{text-align:right;white-space:nowrap;}
th[style*="center"],td[style*="center"]{text-align:center;}

/* ── 图表 ── */
figure.exhibit{margin:26px 0 30px;max-width:var(--content-max);break-inside:avoid;page-break-inside:avoid;}
figure.exhibit img{display:block;max-width:100%;height:auto;margin:0 auto;
                   border:1px solid var(--line);background:#fff;}
figcaption{margin-top:12px;font-size:var(--fz-notes);line-height:var(--lh-notes);color:var(--muted);}
.fig-title{display:block;font-size:var(--fz-figcap);font-weight:600;color:var(--title);
           line-height:1.5;margin-bottom:6px;}
.fig-notes{font-size:var(--fz-notes);color:var(--muted);line-height:var(--lh-notes);}
.fig-notes strong{color:var(--muted);font-weight:600;}
.fig-notes br{display:block;content:"";margin-top:2px;}

/* ── 页脚 ── */
.report-footer{margin-top:56px;padding-top:20px;border-top:1px solid var(--line);
               max-width:var(--text-max);font-size:var(--fz-footer);line-height:1.7;color:var(--muted);}
.footer-disclaimer{font-size:var(--fz-source);color:#475569;margin-bottom:14px;}
.footer-meta{margin-bottom:6px;}
.footer-scope{margin-bottom:10px;}
.report-footer a{color:var(--accent);}

/* ── 移动端顶栏 / 抽屉 / 返回顶部 ── */
.mobile-bar{display:none;}
.overlay{display:none;}
#to-top{position:fixed;right:22px;bottom:24px;width:38px;height:38px;border:1px solid var(--line);
        background:var(--paper);color:var(--accent);border-radius:3px;cursor:pointer;font-size:13px;
        font-family:var(--font);box-shadow:0 1px 4px rgba(15,23,42,.08);opacity:0;pointer-events:none;
        transition:opacity .18s;z-index:30;}
#to-top.show{opacity:1;pointer-events:auto;}

@media (max-width:1100px){
  .page-layout{padding:0 20px;gap:26px;grid-template-columns:220px minmax(0,1fr);}
  :root{--sidebar-w:220px;}
  .main-content{padding:0 clamp(22px,4vw,48px) 60px;}
}
@media (max-width:900px){
  .page-layout{display:block;padding:0;max-width:none;}
  .mobile-bar{display:flex;align-items:center;gap:12px;position:sticky;top:0;z-index:25;
              height:50px;padding:0 16px;background:var(--paper);border-bottom:1px solid var(--line);}
  .mobile-bar button{border:1px solid var(--line);background:#fff;color:var(--accent);
                     font-family:var(--font);font-size:14px;padding:5px 12px;border-radius:3px;cursor:pointer;}
  .mobile-bar .mb-title{font-size:13px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
  .sidebar{position:fixed;left:0;top:0;z-index:40;width:280px;max-width:82vw;height:100vh;
           background:var(--paper);border-right:1px solid var(--line);padding:20px 12px 40px;
           transform:translateX(-102%);transition:transform .2s ease;box-shadow:2px 0 12px rgba(15,23,42,.08);}
  .sidebar.open{transform:translateX(0);}
  #menu-close{display:block;border:0;background:transparent;color:var(--muted);
              font-size:20px;line-height:1;cursor:pointer;padding:0 4px;}
  .overlay{display:block;position:fixed;inset:0;background:rgba(15,23,42,.35);z-index:35;
           opacity:0;pointer-events:none;transition:opacity .2s;}
  .overlay.show{opacity:1;pointer-events:auto;}
  .main-content{border:0;padding:0 clamp(16px,5vw,36px) 56px;min-height:0;}
  .report-header{padding:32px 0 22px;}
  h1{font-size:26px;}
  h2{font-size:21px;scroll-margin-top:64px;}
  h3{scroll-margin-top:64px;}
  .fig-notes,.fig-title{font-size:13px;}
}
@media (max-width:420px){
  body{font-size:16px;}           /* 正文字号不缩小 */
  h1{font-size:23px;line-height:1.4;}
  h2{font-size:20px;}
  h3{font-size:17px;}
  .main-content{padding:0 16px 48px;}
  .table-wrap{margin-left:0;margin-right:0;}
  table{font-size:13.5px;}
  th,td{padding:8px 9px;}
  .report-header{padding:26px 0 18px;}
}

/* ── 打印 / PDF ── */
@media print{
  @page{margin:16mm 14mm;}
  :root{--fz-body:11pt;--fz-table:9pt;--fz-th:9pt;--fz-figcap:10.5pt;
        --fz-notes:8.5pt;--fz-footer:8.5pt;--fz-h1:20pt;--fz-h2:15pt;--fz-h3:12pt;
        --lh-body:1.6;--lh-table:1.4;}
  body{background:#fff;color:#000;}
  .page-layout{display:block;max-width:none;padding:0;}
  .sidebar,.mobile-bar,.overlay,#to-top,.toc-toggle{display:none !important;}
  .main-content{border:0;padding:0;min-height:0;}
  .report-header{padding:0 0 14px;margin-bottom:0;}
  .report-body,.report-body>h2,.report-body>h3,.report-body>p,.report-body>ul,
  .report-body>ol,.report-body>blockquote,.table-wrap,figure.exhibit,pre{max-width:none;}
  h2{break-after:avoid;page-break-after:avoid;}
  h3,h4{break-after:avoid;page-break-after:avoid;}
  p{orphans:3;widows:3;}
  .table-wrap{overflow:visible;}
  table{width:100%;}
  thead{display:table-header-group;}
  tr,figure.exhibit,blockquote,pre{break-inside:avoid;page-break-inside:avoid;}
  figure.exhibit img{max-height:150mm;object-fit:contain;}
  a{color:inherit;text-decoration:none;}
  a[href^="http"]::after{content:" (" attr(href) ")";font-size:8pt;}
  .report-footer{position:static;max-width:none;}
}
"""

JS = r"""
(function(){
  var sidebar=document.getElementById('sidebar');
  var toggle=document.getElementById('menu-toggle');
  var closeBtn=document.getElementById('menu-close');
  var overlay=document.getElementById('overlay');
  var toTop=document.getElementById('to-top');

  function openDrawer(){sidebar.classList.add('open');overlay.classList.add('show');
    toggle.setAttribute('aria-expanded','true');}
  function closeDrawer(){sidebar.classList.remove('open');overlay.classList.remove('show');
    toggle.setAttribute('aria-expanded','false');}
  if(toggle) toggle.addEventListener('click',function(){
    sidebar.classList.contains('open')?closeDrawer():openDrawer();});
  if(closeBtn) closeBtn.addEventListener('click',closeDrawer);
  if(overlay) overlay.addEventListener('click',closeDrawer);
  document.addEventListener('keydown',function(e){if(e.key==='Escape')closeDrawer();});

  document.querySelectorAll('.toc-toggle').forEach(function(btn){
    btn.addEventListener('click',function(){
      var sub=btn.parentElement.querySelector('.toc-sub');
      var collapsed=sub.classList.toggle('collapsed');
      btn.setAttribute('aria-expanded',collapsed?'false':'true');
      btn.textContent=collapsed?'+':'\u2212';
      btn.setAttribute('aria-label',collapsed?'展开子章节':'折叠子章节');
    });
  });

  document.querySelectorAll('.sidebar-nav a').forEach(function(a){
    a.addEventListener('click',closeDrawer);
  });

  var links=Array.prototype.slice.call(document.querySelectorAll('.toc-link'));
  var heads=Array.prototype.slice.call(
    document.querySelectorAll('.report-body h2[id], .report-body h3[id]'));
  var ticking=false;
  function updateActive(){
    ticking=false;
    var cur=heads[0];
    for(var i=0;i<heads.length;i++){
      if(heads[i].getBoundingClientRect().top<=140){cur=heads[i];}else{break;}
    }
    links.forEach(function(a){a.classList.remove('active','active-parent');});
    if(!cur)return;
    var hit=null;
    for(var j=0;j<links.length;j++){
      if(links[j].getAttribute('data-target')===cur.id){hit=links[j];break;}
    }
    if(hit){
      hit.classList.add('active');
      var sub=hit.closest('.toc-sub');
      if(sub){var parentA=sub.parentElement.querySelector(':scope > a');
        if(parentA)parentA.classList.add('active-parent');}
    }
  }
  window.addEventListener('scroll',function(){
    if(!ticking){ticking=true;requestAnimationFrame(updateActive);}
  },{passive:true});
  window.addEventListener('resize',updateActive);
  window.addEventListener('scroll',function(){
    if(window.scrollY>600){toTop.classList.add('show');}else{toTop.classList.remove('show');}
  },{passive:true});
  if(toTop)toTop.addEventListener('click',function(){
    window.scrollTo({top:0,behavior:'smooth'});});
  updateActive();
})();
"""


def embed_images(html):
    """把相对路径图片替换为 base64 data URI；文件不存在即报错（不允许失效链接）。"""
    def repl(m):
        tag = m.group(0)
        src = m.group(1)
        if src.startswith("data:"):
            return tag
        f = BASE / src
        if not f.exists():
            raise FileNotFoundError(f"图片缺失：{f}")
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "svg": "image/svg+xml", "gif": "image/gif", "webp": "image/webp"}[f.suffix.lower().lstrip(".")]
        b64 = base64.b64encode(f.read_bytes()).decode()
        return tag.replace(src, f"data:{mime};base64,{b64}")
    return re.sub(r'<img[^>]*src="([^"]+)"[^>]*>', repl, html)


def wrap_tables(html):
    return re.sub(r"<table>.*?</table>",
                  lambda m: '<div class="table-wrap">' + m.group(0) + "</div>",
                  html, flags=re.S)


def wrap_figures(html):
    """把 <p><img></p> + <p><strong>图N…</strong></p> + Notes blockquote 合成 figure。"""
    pat = re.compile(
        r'<p>\s*(<img[^>]*/>)\s*</p>\s*'
        r'<p>\s*<strong>(图\s*\d+[^<]*)</strong>\s*</p>\s*'
        r'(<blockquote>\s*<p>(.*?)</p>\s*</blockquote>)?',
        re.S)

    def repl(m):
        img, title = m.group(1), m.group(2).strip()
        notes = (m.group(4) or "").strip()
        cap = ('<figure class="exhibit">' + img +
               '<figcaption><span class="fig-title">' + title + '</span>')
        if notes:
            cap += '<div class="fig-notes">' + notes + '</div>'
        cap += '</figcaption></figure>'
        return cap
    return pat.subn(repl, html)


def add_heading_ids(html):
    """稳定锚点 + 目录项（目录文字直接取自正文标题，保证一致）。"""
    items = []
    n2 = [0]
    cur = [0]
    n3 = [0]

    def repl(m):
        lvl = int(m.group(1))
        inner = m.group(2)
        text = re.sub(r"<[^>]+>", "", inner).strip()
        if lvl == 2:
            n2[0] += 1
            cur[0] = n2[0]
            hid = "ch-%d" % cur[0]
            items.append({"lvl": 2, "text": text, "id": hid, "ch": cur[0], "subs": []})
        else:
            n3[0] += 1
            hid = "sec-%d-%d" % (cur[0], n3[0])
            if items:
                items[-1]["subs"].append({"lvl": 3, "text": text, "id": hid})
        return '<h%d id="%s">%s</h%d>' % (lvl, hid, inner, lvl)

    html = re.sub(r"<h([23])>(.*?)</h\1>", repl, html, flags=re.S)
    return html, items


def build_toc(items):
    out = ['<nav class="sidebar-nav" aria-label="报告目录"><ul class="toc-list">']
    for it in items:
        if it["subs"]:
            out.append('<li class="has-children">')
            out.append('<a class="toc-link" href="#%s" data-target="%s">%s</a>' %
                       (it["id"], it["id"], it["text"]))
            out.append('<button class="toc-toggle" type="button" aria-expanded="true" '
                       'aria-label="折叠子章节">\u2212</button>')
            out.append('<ul class="toc-sub">')
            for s in it["subs"]:
                out.append('<li><a class="toc-link" href="#%s" data-target="%s">%s</a></li>' %
                           (s["id"], s["id"], s["text"]))
            out.append('</ul></li>')
        else:
            out.append('<li><a class="toc-link" href="#%s" data-target="%s">%s</a></li>' %
                       (it["id"], it["id"], it["text"]))
    out.append('</ul></nav>')
    return "\n".join(out), len(items)


def main():
    src = SRC.read_text(encoding="utf-8")
    md = _md.Markdown(extensions=["tables", "fenced_code", "sane_lists"])
    body = md.convert(src)

    body = embed_images(body)
    body = wrap_tables(body)
    body, nfig = wrap_figures(body)
    body, items = add_heading_ids(body)
    toc_html, nchap = build_toc(items)

    # 头部：h1 + 副标题
    head = re.match(r"\s*(<h1>.*?</h1>)\s*(<p>.*?</p>)\s*(.*)", body, re.S)
    disclaimer = ""
    if head:
        h1 = head.group(1)
        sub = head.group(2).replace("<p>", '<p class="subtitle">', 1)
        body = head.group(3)
    else:
        h1, sub = "", ""

    # 尾部：免责声明移入页脚，避免与页脚简版重复
    tail = re.search(r"<hr\s*/>\s*(<p><strong>免责声明</strong>.*?</p>)\s*$", body, re.S)
    if tail:
        disclaimer = tail.group(1)
        body = body[:tail.start()]

    header = (
        '<header class="report-header">'
        '<div class="eyebrow">行业深度研究 · A 股生猪养殖</div>'
        + h1 + sub +
        '<div class="header-meta">执行日 2026-11-15　·　研究版本 v3.0　·　文字与排版 v4.0'
        '　·　数据截止：财务 2026-09-30 / 行情 2026-11-13</div>'
        '</header>'
    )

    footer = (
        '<footer class="report-footer">'
        '<div class="footer-disclaimer">' +
        (disclaimer if disclaimer else
         '<p><strong>免责声明</strong>：本报告仅供参考，不构成投资建议。</p>') +
        '</div>'
        '<div class="footer-meta">版本 v4.0（阅读版）｜研究版本 v3.0｜生成日期 2026-11-16｜'
        '数据截止：财务 2026-09-30 / 行情 2026-11-13</div>'
        '<div class="footer-scope">校验范围限定：计算脚本校验 62/62 与结构校验通过，'
        '仅代表纳入脚本的计算与格式检查，不包含全面人工事实核对与原始来源逐条审查。'
        '来源登记册见 <a href="sources/source-register.md">sources/source-register.md</a>，'
        '数据问题台账见 <a href="data-issues/data-quality-issues.md">data-issues/data-quality-issues.md</a>。</div>'
        '</footer>'
    )

    doc = (
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>A 股生猪养殖企业穿越周期研究</title>'
        '<style>' + CSS + '</style></head><body>'
        '<div class="mobile-bar">'
        '<button id="menu-toggle" type="button" aria-controls="sidebar" aria-expanded="false">目录</button>'
        '<span class="mb-title">A 股生猪养殖企业穿越周期研究</span></div>'
        '<div class="overlay" id="overlay" aria-hidden="true"></div>'
        '<div class="page-layout">'
        '<aside class="sidebar" id="sidebar">'
        '<div class="sidebar-head"><span>报告目录</span>'
        '<button id="menu-close" type="button" aria-label="关闭目录">\u00d7</button></div>'
        + toc_html + '</aside>'
        '<main class="main-content">' + header +
        '<article class="report-body">' + body + '</article>' + footer +
        '</main></div>'
        '<button id="to-top" type="button" aria-label="返回顶部">\u2191</button>'
        '<script>' + JS + '</script></body></html>'
    )
    DST.write_text(doc, encoding="utf-8")

    ext = re.findall(r'src="(?!data:)[^"]+"', doc)
    print("已生成 %s（%s 字符）" % (DST.name, format(len(doc), ",")))
    print("章节 %d ｜ figure %d ｜ img %d ｜ 表格 %d ｜ 外部图片引用 %d" %
          (nchap, nfig, doc.count("<img"), doc.count("<table"), len(ext)))


if __name__ == "__main__":
    main()
