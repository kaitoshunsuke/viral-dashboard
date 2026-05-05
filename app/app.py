# -*- coding: utf-8 -*-
import os
import sys
import json
# Windows環境でのUTF-8強制
if sys.platform == "win32":
    os.environ["PYTHONUTF8"] = "1"
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from fetcher import refresh_cache, load_cache

load_dotenv()

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
CORS(app)

# Daily refresh scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(refresh_cache, "interval", hours=24, id="daily_refresh")
scheduler.start()

HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Viral Tracker | PLATINUM</title>
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {
    --navy: #0f2334;
    --navy-mid: #50687c;
    --navy-light: #cfdbe6;
    --navy-pale: #e8eef4;
    --bg: #f0f5f9;
    --surface: #ffffff;
    --border: #cfdbe6;
    --text: #0f2334;
    --muted: #7990a5;
  }
  body { background: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; }
  .sidebar { background: var(--navy); min-height: 100vh; width: 220px; flex-shrink: 0; }
  .logo-mark { letter-spacing: 0.3em; font-size: 11px; font-weight: 700; color: var(--navy-light); }
  .nav-item { color: var(--muted); font-size: 13px; padding: 10px 20px; cursor: pointer; border-left: 2px solid transparent; transition: all 0.15s; }
  .nav-item:hover { color: #fff; background: rgba(207,219,230,0.08); }
  .nav-item.active { color: var(--navy-light); border-left-color: var(--navy-light); background: rgba(207,219,230,0.10); }
  .tag-btn { font-size: 12px; padding: 4px 14px; border-radius: 2px; border: 1px solid var(--border); color: var(--muted); cursor: pointer; transition: all 0.15s; background: white; }
  .tag-btn.active { background: var(--navy); color: var(--navy-light); border-color: var(--navy); }
  .tag-btn:hover:not(.active) { border-color: var(--navy-mid); color: var(--navy); }
  .card { background: white; border: 1px solid var(--border); border-radius: 3px; overflow: hidden; cursor: pointer; transition: box-shadow 0.2s, transform 0.2s; }
  .card:hover { box-shadow: 0 8px 32px rgba(15,35,52,0.12); transform: translateY(-2px); }
  .play-btn { width: 40px; height: 40px; background: rgba(15,35,52,0.65); border-radius: 50%; display: flex; align-items: center; justify-content: center; }
  .badge { font-size: 10px; font-weight: 600; letter-spacing: 0.05em; padding: 2px 7px; border-radius: 2px; background: rgba(15,35,52,0.75); color: var(--navy-light); }
  .stat-card { background: white; border: 1px solid var(--border); border-radius: 3px; padding: 16px 20px; }
  .modal-overlay { backdrop-filter: blur(6px); background: rgba(15,35,52,0.7); }
  .modal-inner { background: white; border-radius: 4px; overflow: hidden; }
  .coming-soon { font-size: 10px; color: var(--navy-light); background: rgba(207,219,230,0.15); border-radius: 2px; padding: 1px 5px; margin-left: 4px; }
  ::-webkit-scrollbar { width: 4px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--navy-light); border-radius: 2px; }
</style>
</head>
<body class="flex">

<!-- Sidebar -->
<aside class="sidebar flex flex-col py-8 px-0">
  <div class="px-6 mb-10">
    <div class="logo-mark mb-1">PLATINUM</div>
    <div style="font-size:10px;color:#555;letter-spacing:0.15em;">VIRAL TRACKER</div>
  </div>
  <nav class="flex flex-col gap-1 flex-1">
    <div style="font-size:10px;color:#445;letter-spacing:0.15em;padding:0 20px;margin-bottom:4px;">PLATFORM</div>
    <div class="nav-item active" onclick="setNav(this,'youtube')">YouTube</div>
    <div class="nav-item" onclick="setNav(this,'tiktok')">TikTok</div>
    <div class="nav-item" onclick="setNav(this,'instagram')">Instagram</div>
    <div style="font-size:10px;color:#445;letter-spacing:0.15em;padding:0 20px;margin-top:20px;margin-bottom:4px;">SAVED</div>
    <div class="nav-item" onclick="setNav(this,'all');setRegion('manual')">手動保存</div>
    <div style="font-size:10px;color:#445;letter-spacing:0.15em;padding:0 20px;margin-top:20px;margin-bottom:4px;">REGION</div>
    <div class="nav-item nav-region active-region" id="region-overseas" onclick="setRegion('overseas')">海外バイラル</div>
    <div class="nav-item nav-region" id="region-japan" onclick="setRegion('japan')">日本トレンド</div>
  </nav>
  <div class="px-6 mt-auto">
    <div id="updated-at" style="font-size:10px;color:#555;line-height:1.6;"></div>
    <button onclick="forceRefresh()" style="margin-top:8px;font-size:11px;color:#888;background:rgba(255,255,255,0.06);border:1px solid #333;border-radius:2px;padding:5px 12px;cursor:pointer;width:100%;transition:all 0.15s;" onmouseover="this.style.color='#fff'" onmouseout="this.style.color='#888'">手動更新</button>
  </div>
</aside>

<!-- Main -->
<main class="flex-1 min-h-screen p-8 overflow-y-auto">
  <!-- Header -->
  <div class="flex items-start justify-between mb-8">
    <div>
      <h1 id="page-title" style="font-size:22px;font-weight:700;letter-spacing:-0.02em;">海外バイラル動画</h1>
      <p id="page-desc" style="font-size:13px;color:var(--muted);margin-top:4px;">100万再生超 ／ 日本未バズ ／ 毎日更新</p>
    </div>
    <!-- Stats -->
    <div class="flex gap-3">
      <div class="stat-card text-center" style="min-width:80px;">
        <div id="total-count" style="font-size:20px;font-weight:700;color:var(--platinum);">-</div>
        <div style="font-size:11px;color:var(--muted);">件</div>
      </div>
      <div class="stat-card text-center" style="min-width:80px;">
        <div id="total-views" style="font-size:20px;font-weight:700;color:var(--accent);">-</div>
        <div style="font-size:11px;color:var(--muted);">総再生</div>
      </div>
    </div>
  </div>

  <!-- Genre Dropdown -->
  <div class="flex items-center gap-3 mb-5">
    <label style="font-size:12px;color:var(--muted);white-space:nowrap;">カテゴリ</label>
    <select id="genre-select" onchange="setGenre(this.value)" style="font-size:13px;padding:6px 32px 6px 12px;border:1.5px solid var(--border);border-radius:3px;color:var(--text);background:white;cursor:pointer;outline:none;appearance:none;background-image:url('data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2212%22 height=%2212%22 viewBox=%220 0 24 24%22 fill=%22%237990a5%22><path d=%22M7 10l5 5 5-5z%22/></svg>');background-repeat:no-repeat;background-position:right 10px center;min-width:180px;">
      <option value="product_pr">商品PR・レビュー</option>
      <option value="skincare">スキンケア</option>
      <option value="makeup">メイク・コスメ</option>
      <option value="influencer">インフルエンサーPR</option>
      <option value="campaign">キャンペーン・新発売</option>
      <option value="entertainment">エンタメ・バズ動画</option>
    </select>
  </div>
  <!-- Shorts Filter -->
  <div class="flex gap-2 mb-6">
    <button class="tag-btn active" id="type-all" onclick="setType('all')">すべて</button>
    <button class="tag-btn" id="type-short" onclick="setType('short')">Shorts のみ</button>
    <button class="tag-btn" id="type-long" onclick="setType('long')">長尺のみ</button>
  </div>

  <!-- Platform Tabs (hidden, controlled by sidebar) -->
  <!-- Video Grid -->
  <div id="video-grid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"></div>

  <!-- Loading -->
  <div id="loading" class="hidden text-center py-24" style="color:var(--muted);font-size:13px;">読み込み中...</div>

  <!-- Empty -->
  <div id="empty" class="hidden text-center py-24">
    <p style="font-size:15px;color:var(--muted);">動画が見つかりません</p>
    <p style="font-size:12px;color:#bbb;margin-top:6px;">APIキーを設定してから「手動更新」を押してください</p>
  </div>
</main>

<!-- 分析結果モーダル -->
<div id="analysis-modal" class="hidden fixed inset-0 z-50 flex items-center justify-center modal-overlay" onclick="if(event.target===this)this.classList.add('hidden')">
  <div style="background:white;border-radius:4px;width:560px;max-height:85vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,0.3);" onclick="event.stopPropagation()">
    <div style="display:flex;align-items:center;justify-content:space-between;padding:14px 20px;border-bottom:1px solid var(--border);">
      <div style="font-size:13px;font-weight:700;color:var(--text);">動画分析レポート</div>
      <button onclick="document.getElementById('analysis-modal').classList.add('hidden')" style="color:var(--muted);font-size:20px;cursor:pointer;">&times;</button>
    </div>
    <div id="analysis-body" style="padding:20px;"></div>
  </div>
</div>

<!-- Refresh Overlay -->
<div id="refresh-overlay" class="hidden fixed inset-0 z-50 flex flex-col items-center justify-center" style="background:rgba(15,35,52,0.97);">
  <div style="width:340px;text-align:center;">
    <!-- 変なおじさん SVG -->
    <div id="claude-dancer" style="margin-bottom:20px;display:inline-block;">
      <svg width="120" height="160" viewBox="0 0 120 160" fill="none" xmlns="http://www.w3.org/2000/svg" style="overflow:visible;">
        <!-- 帽子 -->
        <ellipse cx="60" cy="18" rx="26" ry="6" fill="#222"/>
        <rect x="38" y="8" width="44" height="14" rx="4" fill="#333"/>
        <!-- 頭 -->
        <ellipse cx="60" cy="34" rx="20" ry="22" fill="#F5C98A"/>
        <!-- 眉毛（太い・変な） -->
        <path d="M44 26 Q52 22 56 27" stroke="#5a3a1a" stroke-width="3" fill="none" stroke-linecap="round"/>
        <path d="M64 27 Q68 22 76 26" stroke="#5a3a1a" stroke-width="3" fill="none" stroke-linecap="round"/>
        <!-- 目（ギョロ目） -->
        <circle cx="50" cy="33" r="6" fill="white"/>
        <circle cx="70" cy="33" r="6" fill="white"/>
        <circle id="ojisan-eye-l" cx="51" cy="34" r="3" fill="#1a1a1a"/>
        <circle id="ojisan-eye-r" cx="71" cy="34" r="3" fill="#1a1a1a"/>
        <circle cx="52" cy="33" r="1" fill="white"/>
        <circle cx="72" cy="33" r="1" fill="white"/>
        <!-- 鼻 -->
        <ellipse cx="60" cy="40" rx="5" ry="4" fill="#e8a87c"/>
        <!-- 口（ニヤリ） -->
        <path d="M48 48 Q60 58 72 48" stroke="#c0392b" stroke-width="2.5" fill="#ff8a80" stroke-linecap="round"/>
        <!-- 耳 -->
        <ellipse cx="40" cy="34" rx="5" ry="7" fill="#F5C98A"/>
        <ellipse cx="80" cy="34" rx="5" ry="7" fill="#F5C98A"/>
        <!-- 髭 -->
        <path d="M48 52 Q60 56 72 52" stroke="#888" stroke-width="1.5" fill="none"/>
        <!-- 体（派手なシャツ） -->
        <rect x="36" y="54" width="48" height="52" rx="8" fill="#e74c3c"/>
        <!-- シャツ柄 -->
        <circle cx="50" cy="68" r="3" fill="#f39c12" opacity="0.7"/>
        <circle cx="65" cy="75" r="3" fill="#f1c40f" opacity="0.7"/>
        <circle cx="52" cy="88" r="3" fill="#f39c12" opacity="0.7"/>
        <circle cx="70" cy="62" r="3" fill="#f1c40f" opacity="0.7"/>
        <!-- 左腕 -->
        <path id="arm-l" d="M38 62 Q18 55 10 40" stroke="#F5C98A" stroke-width="10" fill="none" stroke-linecap="round"/>
        <!-- 右腕 -->
        <path id="arm-r" d="M82 62 Q102 55 110 40" stroke="#F5C98A" stroke-width="10" fill="none" stroke-linecap="round"/>
        <!-- 左手（グー） -->
        <circle cx="10" cy="40" r="7" fill="#F5C98A"/>
        <!-- 右手（グー） -->
        <circle cx="110" cy="40" r="7" fill="#F5C98A"/>
        <!-- ズボン -->
        <rect x="36" y="100" width="20" height="50" rx="6" fill="#2c3e50"/>
        <rect x="64" y="100" width="20" height="50" rx="6" fill="#2c3e50"/>
        <!-- 靴 -->
        <ellipse cx="46" cy="150" rx="14" ry="7" fill="#1a1a1a"/>
        <ellipse cx="74" cy="150" rx="14" ry="7" fill="#1a1a1a"/>
      </svg>
    </div>
    <div id="refresh-msg" style="font-size:15px;color:#cfdbe6;font-weight:500;margin-bottom:6px;min-height:24px;transition:opacity 0.3s;"></div>
    <div style="font-size:12px;color:#50687c;margin-bottom:22px;" id="refresh-sub"></div>
    <!-- Progress bar -->
    <div style="background:rgba(207,219,230,0.12);border-radius:4px;height:4px;overflow:hidden;margin-bottom:10px;">
      <div id="progress-bar" style="height:100%;width:0%;background:linear-gradient(90deg,#CC785C,#cfdbe6);border-radius:4px;transition:width 0.5s ease;"></div>
    </div>
    <div style="display:flex;justify-content:space-between;font-size:11px;color:#50687c;">
      <span id="progress-pct">0%</span>
      <span id="progress-elapsed">0s</span>
    </div>
  </div>
</div>

<style>
@keyframes ojisan-dance {
  0%   { transform: rotate(-14deg) translateY(0px) scaleX(1); }
  20%  { transform: rotate(14deg) translateY(-14px) scaleX(0.93); }
  40%  { transform: rotate(-6deg) translateY(-5px) scaleX(1.06); }
  60%  { transform: rotate(16deg) translateY(-16px) scaleX(0.93); }
  80%  { transform: rotate(-10deg) translateY(-3px) scaleX(1); }
  100% { transform: rotate(-14deg) translateY(0px) scaleX(1); }
}
@keyframes arm-wave-l {
  0%,100% { transform-origin: 38px 62px; transform: rotate(0deg); }
  35%      { transform-origin: 38px 62px; transform: rotate(-40deg); }
  65%      { transform-origin: 38px 62px; transform: rotate(12deg); }
}
@keyframes arm-wave-r {
  0%,100% { transform-origin: 82px 62px; transform: rotate(0deg); }
  35%      { transform-origin: 82px 62px; transform: rotate(40deg); }
  65%      { transform-origin: 82px 62px; transform: rotate(-12deg); }
}
@keyframes eye-spin {
  0%,85%,100% { transform: translate(0,0); }
  45% { transform: translate(2px, -2px); }
}
#claude-dancer { animation: ojisan-dance 0.55s ease-in-out infinite; }
#arm-l { animation: arm-wave-l 0.55s ease-in-out infinite; }
#arm-r { animation: arm-wave-r 0.55s ease-in-out infinite; animation-delay: 0.27s; }
#ojisan-eye-l { animation: eye-spin 0.55s ease-in-out infinite; }
#ojisan-eye-r { animation: eye-spin 0.55s ease-in-out infinite; animation-delay: 0.15s; }
</style>

<!-- Modal -->
<div id="modal" class="hidden fixed inset-0 z-50 flex items-center justify-center modal-overlay" onclick="closeModal(event)">
  <div class="modal-inner w-full max-w-3xl mx-4 shadow-2xl" onclick="event.stopPropagation()">
    <div class="flex items-center justify-between px-5 py-3" style="border-bottom:1px solid var(--border);">
      <h3 id="modal-title" style="font-size:13px;font-weight:600;color:var(--text);" class="truncate pr-4"></h3>
      <button onclick="closeModal()" style="color:var(--muted);font-size:20px;line-height:1;cursor:pointer;">&times;</button>
    </div>
    <div id="modal-body" class="aspect-video">
      <iframe id="modal-iframe" src="" frameborder="0" allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen class="w-full h-full"></iframe>
    </div>
    <div id="modal-meta" class="px-5 py-3 flex gap-5" style="font-size:12px;color:var(--muted);border-top:1px solid var(--border);"></div>
  </div>
</div>


<script>
let currentPlatform = 'youtube';
let currentGenre = 'product_pr';
let currentType = 'all';
let currentRegion = 'overseas';
let allData = {};
let videoMap = {};

async function loadData() {
  try {
    const res = await fetch('/api/videos');
    const json = await res.json();
    allData = json.videos || {};
    if (json.updated_at) {
      document.getElementById('updated-at').textContent = '最終更新\\n' + json.updated_at.slice(0,16).replace('T', ' ');
    }
    render();
  } catch(e) {
    document.getElementById('loading').textContent = 'エラーが発生しました';
  }
}

function render() {
  const grid = document.getElementById('video-grid');
  const loading = document.getElementById('loading');
  const empty = document.getElementById('empty');
  const regionData = allData[currentRegion] || {};
  // manualデータはplatformで横断検索、それ以外はジャンル＋プラットフォームで絞り込み
  let videos;
  if (currentRegion === 'manual') {
    videos = Object.values(regionData).flat().filter(v => currentPlatform === 'all' || v.platform === currentPlatform);
  } else {
    // YouTube以外のタブはmanualから該当platformを表示
    if (currentPlatform === 'tiktok' || currentPlatform === 'instagram') {
      const manualData = allData['manual'] || {};
      videos = Object.values(manualData).flat().filter(v => v.platform === currentPlatform);
    } else {
      videos = (regionData[currentGenre] || []).filter(v => v.platform === currentPlatform);
    }
  }
  if (currentType === 'short') videos = videos.filter(v => v.is_short);
  else if (currentType === 'long') videos = videos.filter(v => !v.is_short);
  loading.classList.add('hidden');
  if (videos.length === 0) {
    grid.innerHTML = '';
    empty.classList.remove('hidden');
    document.getElementById('total-count').textContent = '0';
    document.getElementById('total-views').textContent = '0';
    return;
  }
  empty.classList.add('hidden');
  document.getElementById('total-count').textContent = videos.length.toLocaleString();
  document.getElementById('total-views').textContent = formatViews(videos.reduce((s, v) => s + v.views, 0));
  videoMap = {};
  videos.forEach(v => { videoMap[v.id] = v; });
  grid.innerHTML = videos.map(v => `
    <div class="card" data-id="${v.id}">
      <div class="relative aspect-video" style="background:#f0f0ee;">
        <img src="${v.thumbnail}" alt="" class="w-full h-full object-cover" onerror="this.style.display='none'">
        <div class="absolute inset-0 flex items-center justify-center">
          <div class="play-btn"><svg width="16" height="16" fill="white" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg></div>
        </div>
        <div class="absolute top-2 left-2 badge">${v.region}</div>
        ${v.is_short ? '<div class="absolute top-2 right-2 badge" style="background:rgba(15,35,52,0.85);">Shorts</div>' : ''}
      </div>
      <div style="padding:12px 14px;">
        <p style="font-size:13px;font-weight:500;line-height:1.4;margin-bottom:4px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">${escapeHtml(v.title)}</p>
        <p style="font-size:11px;color:var(--muted);margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${escapeHtml(v.channel)}</p>
        ${v.url ? '<p style="font-size:10px;color:#50687c;margin-bottom:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="' + v.url + '">' + v.url.replace(/https?:\/\//, '').slice(0, 40) + '...</p>' : ''}
        <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--muted);">
          <span style="color:var(--accent);font-weight:600;">${formatViews(v.views)} 再生</span>
          <span>♥ ${formatViews(v.likes)}</span>
          <span>💬 ${formatViews(v.comments||0)}</span>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--muted);margin-top:3px;">
          <span>保存 ${formatViews(v.saves||0)}</span>
          <span>${v.published_at}</span>
        </div>
        <div style="display:flex;gap:6px;margin-top:10px;">
          <button class="analyze-btn" data-id="${v.id}" style="font-size:11px;font-weight:600;padding:7px 10px;background:#1a5276;color:white;border:none;border-radius:2px;cursor:pointer;">分析</button>
          <button class="edit-btn" data-id="${v.id}" style="flex:1;font-size:11px;font-weight:600;padding:7px 0;background:var(--navy);color:var(--navy-light);border:none;border-radius:2px;cursor:pointer;">編集</button>
          ${currentRegion === 'manual' ? '<button class="del-btn" data-id="' + v.id + '" style="font-size:11px;font-weight:600;padding:7px 10px;background:#e74c3c;color:white;border:none;border-radius:2px;cursor:pointer;">削除</button>' : ''}
        </div>
      </div>
    </div>
  `).join('');
  grid.querySelectorAll('.card').forEach(el => {
    const v = videoMap[el.dataset.id];
    el.addEventListener('click', () => {
      if (v.platform === 'tiktok') { openTiktokOverlay(v.url); }
      else { openModal(v.embed_url, v.title, v.views, v.likes, v.published_at, v.channel); }
    });
  });
  grid.querySelectorAll('.edit-btn').forEach(btn => {
    btn.addEventListener('click', e => { e.stopPropagation(); editLike(JSON.stringify(videoMap[btn.dataset.id])); });
  });
  grid.querySelectorAll('.analyze-btn').forEach(btn => {
    btn.addEventListener('click', e => { e.stopPropagation(); startAnalysis(btn, videoMap[btn.dataset.id]); });
  });
  grid.querySelectorAll('.del-btn').forEach(btn => {
    btn.addEventListener('click', e => { e.stopPropagation(); deleteVideo(btn.dataset.id); });
  });
}

function cardOpen(e, tiktokUrl, modalData) {
  if (tiktokUrl) { openTiktokOverlay(tiktokUrl); return; }
  const [url, title, views, likes, date, channel] = modalData.split('|');
  openModal(url, title, Number(views), Number(likes), date, channel);
}

function openTiktokOverlay(url) {
  const w = 500, h = 800;
  const left = window.screenX + window.outerWidth - w - 20;
  const top = window.screenY + 40;
  window.open(url, 'tiktok_popup', `width=${w},height=${h},left=${left},top=${top},resizable=yes,scrollbars=yes`);
}

function setNav(el, platform) {
  currentPlatform = platform;
  document.querySelectorAll('.nav-item:not(.nav-region)').forEach(n => n.classList.remove('active'));
  el.classList.add('active');
  render();
}

function setRegion(r) {
  currentRegion = r;
  ['overseas','japan'].forEach(k => {
    document.getElementById('region-' + k).classList.toggle('active', k === r);
  });
  const isOverseas = r === 'overseas';
  document.getElementById('page-title').textContent = isOverseas ? '海外バイラル動画' : '日本トレンド動画';
  document.getElementById('page-desc').textContent = isOverseas ? '100万再生超 ／ 日本未バズ ／ 毎日更新' : 'YouTube 日本トレンド ／ 毎日更新';
  render();
}

function setGenre(g) {
  currentGenre = g;
  document.getElementById('genre-select').value = g;
  render();
}

function setType(t) {
  currentType = t;
  ['all','short','long'].forEach(k => {
    document.getElementById('type-' + k).className = k === t ? 'tag-btn active' : 'tag-btn';
  });
  render();
}

function openModal(embedUrl, title, views, likes, date, channel) {
  document.getElementById('modal-iframe').src = embedUrl + '?autoplay=1';
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-meta').innerHTML = `
    <span style="color:var(--accent);font-weight:600;">${formatViews(views)} 回再生</span>
    <span>♥ ${formatViews(likes)}</span>
    <span>${date}</span>
    <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escapeHtml(channel)}</span>
  `;
  document.getElementById('modal').classList.remove('hidden');
}

function closeModal(e) {
  if (!e || e.target === document.getElementById('modal')) {
    document.getElementById('modal').classList.add('hidden');
    document.getElementById('modal-iframe').src = '';
  }
}

const REFRESH_MSGS = [
  ['🌍 海外トレンドをスキャン中...', 'US・GB・IN・BRのデータを取得しています'],
  ['📊 再生数を集計中...', '100万再生超の動画をフィルタリング'],
  ['🇯🇵 日本エンゲージをチェック中...', '日本未バズかどうか確認しています'],
  ['⚡ Shortsを検出中...', '60秒以下の動画を分類しています'],
  ['🎯 カテゴリに振り分け中...', '商品PR・ブランディング・キャンペーンを整理'],
  ['✨ もうすぐ完了...', 'データを最終処理しています'],
];

async function forceRefresh() {
  const overlay = document.getElementById('refresh-overlay');
  const bar = document.getElementById('progress-bar');
  const pct = document.getElementById('progress-pct');
  const elapsed = document.getElementById('progress-elapsed');
  const msg = document.getElementById('refresh-msg');
  const sub = document.getElementById('refresh-sub');

  overlay.classList.remove('hidden');
  document.getElementById('video-grid').innerHTML = '';

  const startTime = Date.now();
  const DURATION = 11000; // ~11秒
  let msgIdx = 0;

  const setMsg = (i) => {
    msg.style.opacity = 0;
    setTimeout(() => {
      msg.textContent = REFRESH_MSGS[i][0];
      sub.textContent = REFRESH_MSGS[i][1];
      msg.style.opacity = 1;
    }, 200);
  };
  setMsg(0);

  const timer = setInterval(() => {
    const elapsedMs = Date.now() - startTime;
    const progress = Math.min(elapsedMs / DURATION * 95, 95);
    bar.style.width = progress + '%';
    pct.textContent = Math.round(progress) + '%';
    elapsed.textContent = (elapsedMs / 1000).toFixed(1) + 's';

    const newIdx = Math.min(Math.floor(progress / 16), REFRESH_MSGS.length - 1);
    if (newIdx !== msgIdx) { msgIdx = newIdx; setMsg(msgIdx); }
  }, 200);

  await fetch('/api/refresh', {method: 'POST'});
  clearInterval(timer);

  bar.style.width = '100%';
  pct.textContent = '100%';
  elapsed.textContent = ((Date.now() - startTime) / 1000).toFixed(1) + 's';
  msg.textContent = '✅ 取得完了！';
  sub.textContent = '';

  await new Promise(r => setTimeout(r, 800));
  overlay.classList.add('hidden');
  await loadData();
}

function formatViews(n) {
  if (n >= 100_000_000) return (n / 100_000_000).toFixed(1) + '億';
  if (n >= 10_000) return (n / 10_000).toFixed(1) + '万';
  return n.toLocaleString();
}

function escapeHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function escapeAttr(s) {
  return String(s).replace(/'/g,"\\'").replace(/"/g,'&quot;');
}

async function startAnalysis(btn, video) {
  btn.textContent = '分析中...';
  btn.disabled = true;
  await fetch('/api/analyze', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(video)
  });
  // ポーリングで結果を待つ
  const id = video.id;
  const poll = setInterval(async () => {
    const res = await fetch('/api/analysis-result/' + id);
    const data = await res.json();
    if (data.status !== 'pending' && !data.error) {
      clearInterval(poll);
      btn.textContent = '分析完了';
      showAnalysis(data);
    } else if (data.error) {
      clearInterval(poll);
      btn.textContent = '分析失敗';
      btn.disabled = false;
    }
  }, 3000);
}

function showAnalysis(d) {
  const breakdown = Object.entries(d.score_breakdown || {}).map(([k,v]) => `<span style="background:#f0f5f9;padding:2px 8px;border-radius:2px;font-size:11px;">${k}: ${v}</span>`).join(' ');
  const transcript = (d.transcript || []).map(t => `<li style="margin-bottom:4px;">${t}</li>`).join('');
  document.getElementById('analysis-body').innerHTML = `
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">
      <div style="font-size:36px;font-weight:700;color:#0f2334;">${d.score}</div>
      <div style="font-size:12px;color:#7990a5;">/ 100点</div>
      <div style="flex:1;display:flex;flex-wrap:wrap;gap:4px;">${breakdown}</div>
    </div>
    <table style="width:100%;font-size:12px;border-collapse:collapse;margin-bottom:12px;">
      <tr><td style="padding:4px 8px;color:#7990a5;width:120px;">尺</td><td>${d.duration_sec}秒</td></tr>
      <tr><td style="padding:4px 8px;color:#7990a5;">縦型</td><td>${d.is_vertical ? 'はい' : 'いいえ'}</td></tr>
      <tr><td style="padding:4px 8px;color:#7990a5;">カット数</td><td>${d.cut_count}カット（平均${d.avg_cut_sec}秒/カット・${d.tempo}）</td></tr>
      <tr><td style="padding:4px 8px;color:#7990a5;">BGM</td><td>${d.has_bgm ? 'あり' : 'なし'}</td></tr>
      <tr><td style="padding:4px 8px;color:#7990a5;">フック型</td><td>${d.hook_type}</td></tr>
      <tr><td style="padding:4px 8px;color:#7990a5;">冒頭テキスト</td><td style="color:#333;">"${d.hook_text}"</td></tr>
      <tr><td style="padding:4px 8px;color:#7990a5;">話速</td><td>${d.speech_pace} 文字/秒</td></tr>
      <tr><td style="padding:4px 8px;color:#7990a5;">CTA</td><td>${d.cta && d.cta.length ? d.cta.join('・') : 'なし'}</td></tr>
    </table>
    <div style="font-size:11px;color:#7990a5;margin-bottom:4px;">台本（Whisper文字起こし）</div>
    <ol style="font-size:12px;color:#333;padding-left:16px;line-height:1.8;">${transcript}</ol>
  `;
  document.getElementById('analysis-modal').classList.remove('hidden');
}

async function deleteVideo(id) {
  if (!confirm('削除しますか？')) return;
  await fetch('/api/delete-video', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({id})
  });
  await loadData();
}

async function editLike(videoJson) {
  const video = typeof videoJson === 'string' ? JSON.parse(videoJson) : videoJson;
  const btn = event.target;
  btn.textContent = '⏳ 生成中...';
  btn.disabled = true;
  try {
    const res = await fetch('/api/edit-like', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(video)
    });
    const data = await res.json();
    btn.textContent = '✅ 生成開始！';
    btn.style.background = '#1a5c3a';
    setTimeout(() => {
      btn.textContent = 'この動画っぽく編集';
      btn.style.background = 'var(--navy)';
      btn.disabled = false;
    }, 3000);
  } catch(e) {
    btn.textContent = 'エラー';
    btn.disabled = false;
  }
}

loadData();
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/videos")
def api_videos():
    return jsonify(load_cache())


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    data = refresh_cache()
    return jsonify({"status": "ok", "updated_at": data["updated_at"]})


@app.route("/api/save-video", methods=["POST"])
def api_save_video():
    from fetcher import load_cache, CACHE_FILE
    import datetime, urllib.request, urllib.parse
    video = request.json
    data = load_cache()
    genre = "entertainment"

    # yt-dlpでメタデータ取得（サムネ・再生数・いいね・コメント・タイトル）
    import re, subprocess, sys as _sys
    url = video.get("url", "")
    try:
        r = subprocess.run(
            [_sys.executable, "-m", "yt_dlp", "--dump-json", "--no-download", url],
            capture_output=True, text=True, timeout=20, encoding="utf-8"
        )
        if r.returncode == 0:
            meta = json.loads(r.stdout.strip().splitlines()[-1])
            video["title"] = meta.get("title", video.get("title", ""))
            video["thumbnail"] = meta.get("thumbnail", video.get("thumbnail", ""))
            video["views"] = meta.get("view_count", 0) or 0
            video["likes"] = meta.get("like_count", 0) or 0
            video["comments"] = meta.get("comment_count", 0) or 0
            video["saves"] = meta.get("save_count", 0) or 0
            video["channel"] = f"@{meta.get('uploader', '')}"
            video["duration_sec"] = meta.get("duration", 30) or 30
    except Exception:
        # フォールバック：URLからアカウント名だけ抽出
        m = re.search(r'/@([^/]+)/video/(\d+)', url)
        if m:
            video["channel"] = f"@{m.group(1)}"
            video["id"] = m.group(2)
            if not video.get("title") or "検索" in video.get("title", ""):
                video["title"] = f"@{m.group(1)} の動画"

    if "manual" not in data["videos"]:
        data["videos"]["manual"] = {g: [] for g in ["product_pr","skincare","makeup","influencer","campaign","entertainment"]}

    existing = data["videos"]["manual"].get(genre, [])
    if not any(v["id"] == video["id"] for v in existing):
        data["videos"]["manual"][genre].insert(0, video)

    data["updated_at"] = datetime.datetime.now().isoformat()
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return jsonify({"status": "saved"})


@app.route("/api/delete-video", methods=["POST"])
def api_delete_video():
    from fetcher import load_cache, CACHE_FILE
    import datetime
    video_id = request.json.get("id")
    data = load_cache()
    manual = data["videos"].get("manual", {})
    for genre in manual:
        manual[genre] = [v for v in manual[genre] if v["id"] != video_id]
    data["updated_at"] = datetime.datetime.now().isoformat()
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return jsonify({"status": "deleted"})


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    import threading
    video = request.json
    url = video.get("url", "")
    video_id = video.get("id", url)
    if not url:
        return jsonify({"error": "URLが必要です"}), 400

    def run_analysis():
        from analyzer import analyze
        import os
        result = analyze(url, meta=video)
        result["video_id"] = video_id
        # cache.jsonに結果を保存
        from fetcher import load_cache, CACHE_FILE
        data = load_cache()
        for region in data["videos"].values():
            for genre_videos in (region.values() if isinstance(region, dict) else []):
                for v in (genre_videos if isinstance(genre_videos, list) else []):
                    if v.get("id") == video_id or v.get("url") == url:
                        v["analysis"] = result
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    thread = threading.Thread(target=run_analysis)
    thread.daemon = True
    thread.start()
    return jsonify({"status": "analyzing", "video_id": video_id})


@app.route("/api/analysis-result/<video_id>")
def api_analysis_result(video_id):
    from fetcher import load_cache
    data = load_cache()
    for region in data["videos"].values():
        for genre_videos in (region.values() if isinstance(region, dict) else []):
            for v in (genre_videos if isinstance(genre_videos, list) else []):
                if v.get("id") == video_id and v.get("analysis"):
                    return jsonify(v["analysis"])
    return jsonify({"status": "pending"})


@app.route("/api/edit-like", methods=["POST"])
def api_edit_like():
    import subprocess, sys
    video = request.json
    script_path = os.path.join(os.path.dirname(__file__), "..", "..", "video-edit", "edit_like.py")
    subprocess.Popen([sys.executable, os.path.abspath(script_path), json.dumps(video, ensure_ascii=False)])
    return jsonify({"status": "started", "title": video.get("title", "")})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(debug=False, host="0.0.0.0", port=port)
