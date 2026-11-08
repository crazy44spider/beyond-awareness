"""Self-contained, hover-driven theme explorer for Streamlit.

The HTML is an embedded client-side visualization. Person 3's Python analyzer
produces the theme counts and tagged comments; this file only renders a capped,
masked preview of those outputs. Hovering never triggers a Streamlit rerun.
No remote scripts, external assets, persistence, or network requests.
"""
from __future__ import annotations

import json
from typing import Any, Sequence


PALETTE = (
    "#174633",  # forest
    "#287859",  # jade
    "#A17C59",  # bark
    "#6A9B77",  # foliage
    "#D5B790",  # sand
    "#91B5A0",  # sage
    "#695940",  # walnut
    "#B9CBAA",  # moss
)


def _safe_payload_json(payload: dict[str, Any]) -> str:
    """JSON embedded in an HTML script element must not close that element."""
    return (
        json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )


def make_voice_explorer_html(
    entries: Sequence[dict[str, Any]],
    *,
    category: str,
    comment_count: int,
) -> str:
    """Build an accessible interactive SVG and adjacent live comment cards.

    Each entry contains label, count, comments (up to five masked previews).
    Entries with zero mentions are omitted; comments are never HTML-injected.
    """
    positive = [
        {
            "label": str(item["label"]),
            "count": int(item["count"]),
            "comments": [str(c) for c in item.get("comments", [])[:5]],
            "color": PALETTE[index % len(PALETTE)],
        }
        for index, item in enumerate(entries)
        if int(item["count"]) > 0
    ]
    payload = {
        "category": str(category),
        "comment_count": int(comment_count),
        "entries": positive,
    }
    html = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  *, *::before, *::after {box-sizing:border-box}
  :root {color-scheme:light}
  body {
    margin:0;background:transparent;color:#22392e;
    font-family:Inter,"Segoe UI",Arial,sans-serif;
    font-size:14px;
  }
  .workspace {
    display:grid;grid-template-columns:minmax(270px,.95fr) minmax(320px,1.05fr);
    gap:16px;align-items:stretch;width:100%;
  }
  .panel {
    background:#fff;border:1px solid #dce7dc;
    border-radius:20px;min-width:0;
    padding:22px 22px 20px;
    box-shadow:0 1px 5px rgba(20,62,48,.025);
  }
  .eyebrow {font-size:10px;letter-spacing:.12em;color:#617568;font-weight:800}
  h2 {font-size:20px;line-height:1.2;letter-spacing:-.025em;margin:7px 0 4px;color:#163e2c}
  .sub {color:#697d70;margin:0;font-size:12px;line-height:1.5}
  .chart-wrap {width:min(100%,300px);margin:3px auto 2px;position:relative}
  svg {width:100%;max-height:278px;display:block;overflow:visible}
  .slice {
    cursor:pointer;outline:none;transition:transform .16s ease,filter .16s ease,opacity .16s ease;
  }
  .slice[aria-pressed="true"] {
    filter:drop-shadow(0 2px 3px rgba(20,62,48,.20))
  }
  .slice:focus-visible {stroke:#143e30;stroke-width:2px}
  .legend-title {
    font-weight:750;letter-spacing:-.01em;margin:9px 0 8px;
    font-size:12px;color:#274736;
  }
  .legend {
    display:grid;grid-template-columns:1fr;gap:4px;
    max-height:215px;overflow-y:auto;padding:0 2px 2px 0;
  }
  .theme-button {
    font:inherit;display:flex;align-items:center;text-align:left;
    gap:9px;padding:8px 10px;border:1px solid transparent;
    border-radius:9px;background:transparent;color:#42594a;
    cursor:pointer;width:100%;min-height:34px;
    transition:background .13s ease,border .13s ease;
  }
  .theme-button:hover,.theme-button:focus-visible {
    background:#edf4ea;outline:none;border-color:#d2e2d0;
  }
  .theme-button.active {
    color:#163d2a;background:#e9f1e7;border-color:#b8d0be;
    font-weight:700;
  }
  .swatch {height:10px;width:10px;flex:0 0 10px;border-radius:50%}
  .theme-name {flex:1;min-width:0;line-height:1.25;font-size:12px}
  .theme-count {color:#577461;font-weight:750;font-variant-numeric:tabular-nums;font-size:12px}
  .note {margin:11px 0 0;font-size:11px;color:#6a7d70;line-height:1.5}
  .comments {
    border-top:4px solid #287859;
    background:linear-gradient(180deg,#f9fbf6 0%,#fff 36%);
    padding:22px 23px 20px;
    display:flex;flex-direction:column;
  }
  .comments h2 {margin-top:9px;font-size:22px}
  .comment-summary {font-size:12px;color:#617568;line-height:1.5;margin:8px 0 16px}
  .comment-list {display:grid;gap:9px;align-content:start}
  .quote {
    background:#fff;border:1px solid #e1e9e0;border-left:3px solid #b7c9b3;
    border-radius:10px;padding:12px 14px;
    line-height:1.5;font-size:13px;color:#314c39;
    overflow-wrap:anywhere;white-space:pre-wrap;
  }
  .comment-footer {
    font-size:11px;color:#728274;line-height:1.5;margin-top:auto;padding-top:14px
  }
  .center-count {fill:#163f2d;font-size:36px;font-weight:780;letter-spacing:-1.5px}
  .center-caption {fill:#718173;font-size:11px;font-weight:600}
  @media(max-width:740px) {
    .workspace {grid-template-columns:minmax(0,1fr);gap:12px}
    .panel {padding:17px}
    .comments {min-height:270px}
    .legend {max-height:188px}
    .chart-wrap{width:min(100%,270px)}
    svg{max-height:255px}
  }
  @media(prefers-reduced-motion:reduce) {
    .slice,.theme-button {transition:none!important}
  }
</style>
</head>
<body>
<div class="workspace">
  <section class="panel" aria-label="Interactive comment theme visualization">
    <div class="eyebrow">THEMES AT A GLANCE</div>
    <h2 id="chart-title">Explore what participants said</h2>
    <p class="sub">Hover, click, or use Tab and Enter to explore a theme.</p>
    <div class="chart-wrap">
      <svg viewBox="0 0 300 300" id="chart"
           role="group" aria-label="Interactive ring chart of theme mentions">
        <g id="arcs"></g>
        <text x="150" y="143" id="center-count" class="center-count" text-anchor="middle">0</text>
        <text x="150" y="161" class="center-caption" text-anchor="middle">theme</text>
        <text x="150" y="175" class="center-caption" text-anchor="middle">mentions</text>
      </svg>
    </div>
    <div class="legend-title">Explore themes</div>
    <div class="legend" id="legend" aria-label="Select a comment theme"></div>
    <p class="note">The chart shows coded theme mentions, not percentages of people. A comment can match multiple themes.</p>
  </section>
  <section class="panel comments" aria-label="Matching response examples" aria-live="polite">
    <div class="eyebrow">PARTICIPANTS, IN THEIR WORDS</div>
    <h2 id="theme-title">Select a theme</h2>
    <p class="comment-summary" id="theme-summary"></p>
    <div class="comment-list" id="comment-list"></div>
    <p class="comment-footer" id="comment-footer"></p>
  </section>
</div>
<script type="application/json" id="voice-data">__PAYLOAD_JSON__</script>
<script>
(function () {
  "use strict";
  const data = JSON.parse(document.getElementById("voice-data").textContent);
  const entries = data.entries || [];
  const arcs = document.getElementById("arcs");
  const legend = document.getElementById("legend");
  const centerCount = document.getElementById("center-count");
  const themeTitle = document.getElementById("theme-title");
  const themeSummary = document.getElementById("theme-summary");
  const commentList = document.getElementById("comment-list");
  const commentFooter = document.getElementById("comment-footer");
  const slices = [], buttons = [];
  let picked = 0;
  const cx = 150, cy = 150, outer = 118, inner = 69;
  const total = entries.reduce((sum, item) => sum + item.count, 0);

  function polar(radius, angle) {
    const radians = angle * Math.PI / 180;
    return [cx + radius*Math.cos(radians), cy + radius*Math.sin(radians)];
  }
  function donutPath(start, end) {
    const a = polar(outer,start), b = polar(outer,end);
    const c = polar(inner,end), d = polar(inner,start);
    const large = (end - start) > 180 ? 1 : 0;
    return "M "+a[0]+" "+a[1]+
           " A "+outer+" "+outer+" 0 "+large+" 1 "+b[0]+" "+b[1]+
           " L "+c[0]+" "+c[1]+
           " A "+inner+" "+inner+" 0 "+large+" 0 "+d[0]+" "+d[1]+" Z";
  }

  function show(index) {
    if (!entries[index]) return;
    const item = entries[index];
    centerCount.textContent = item.count.toLocaleString();
    themeTitle.textContent = item.label;
    themeSummary.textContent =
      item.count.toLocaleString() + " matching theme mentions · " +
      Math.min(item.comments.length,5) + " example" +
      (item.comments.length === 1 ? "" : "s") + " shown";
    commentList.replaceChildren();
    if (!item.comments.length) {
      const empty = document.createElement("p");
      empty.className = "sub";
      empty.textContent = "No complete comments are available to preview.";
      commentList.appendChild(empty);
    } else {
      item.comments.forEach((comment) => {
        const block = document.createElement("div");
        block.className = "quote";
        block.textContent = "“" + comment + "”";
        commentList.appendChild(block);
      });
    }
    commentFooter.textContent =
      "Basic masking is applied to previews. Theme assignments are rule-based " +
      "and should be interpreted as examples, not confirmed experiences.";
    for (let i=0; i<slices.length; i++) {
      const active = i === index;
      slices[i].setAttribute("aria-pressed",String(active));
      const mid = Number(slices[i].dataset.mid);
      const rad = mid*Math.PI/180;
      const distance = active ? 4 : 0;
      slices[i].style.transform = "translate(" +
        (distance*Math.cos(rad)).toFixed(2)+"px," +
        (distance*Math.sin(rad)).toFixed(2)+"px)";
      slices[i].style.opacity = active ? "1" : ".9";
      buttons[i].classList.toggle("active", active);
      buttons[i].setAttribute("aria-pressed",String(active));
    }
  }
  function select(index) {picked=index;show(index);}

  let angle = -90;
  for (let i=0; i<entries.length; i++) {
    const item=entries[i];
    const sweep=360*item.count/Math.max(1,total);
    const gap = Math.min(1.6,sweep*.18);
    const start=angle+gap/2, end=angle+sweep-gap/2;
    const path=document.createElementNS("http://www.w3.org/2000/svg","path");
    path.setAttribute("d",donutPath(start,Math.min(end,start+359.9)));
    path.setAttribute("fill",item.color);
    path.setAttribute("class","slice");
    path.setAttribute("role","button");
    path.setAttribute("tabindex","0");
    path.setAttribute("aria-label",
      item.label+", "+item.count+" mentions. Press Enter to select.");
    path.dataset.mid=String((start+end)/2);
    path.addEventListener("mouseenter",()=>show(i));
    path.addEventListener("mouseleave",()=>show(picked));
    path.addEventListener("focus",()=>show(i));
    path.addEventListener("blur",()=>show(picked));
    path.addEventListener("click",()=>select(i));
    path.addEventListener("keydown",(event)=>{
      if(event.key==="Enter" || event.key===" "){
        event.preventDefault(); select(i);
      }
    });
    arcs.appendChild(path);
    slices.push(path);

    const button=document.createElement("button");
    button.type="button";
    button.className="theme-button";
    button.setAttribute("aria-label","Explore "+item.label);
    const swatch=document.createElement("span");
    swatch.className="swatch";swatch.style.background=item.color;
    const name=document.createElement("span");
    name.className="theme-name";name.textContent=item.label;
    const count=document.createElement("span");
    count.className="theme-count";count.textContent=item.count.toLocaleString();
    button.append(swatch,name,count);
    button.addEventListener("mouseenter",()=>show(i));
    button.addEventListener("mouseleave",()=>show(picked));
    button.addEventListener("focus",()=>show(i));
    button.addEventListener("blur",()=>show(picked));
    button.addEventListener("click",()=>select(i));
    legend.appendChild(button);
    buttons.push(button);
    angle+=sweep;
  }
  if(entries.length){select(0);}
})();
</script>
</body>
</html>"""
    return html.replace("__PAYLOAD_JSON__", _safe_payload_json(payload))
