const DASHBOARD_URL = "http://localhost:5050";

function detectPlatform(url) {
  if (url.includes("tiktok.com")) return "tiktok";
  if (url.includes("instagram.com")) return "instagram";
  if (url.includes("youtube.com") || url.includes("youtu.be")) return "youtube";
  return "other";
}

function extractVideoId(url, platform) {
  try {
    if (platform === "tiktok") {
      const m = url.match(/\/video\/(\d+)/);
      return m ? m[1] : null;
    }
    if (platform === "instagram") {
      const m = url.match(/\/(p|reel|tv)\/([A-Za-z0-9_-]+)/);
      return m ? m[2] : null;
    }
    if (platform === "youtube") {
      const m = url.match(/[?&]v=([^&]+)/) || url.match(/shorts\/([^?]+)/);
      return m ? m[1] : null;
    }
  } catch(e) {}
  return null;
}

async function getCurrentTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

async function scrapePageInfo(tabId) {
  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId },
      func: () => {
        const title = document.title || "";
        const desc = document.querySelector('meta[name="description"]')?.content || "";
        const ogImage = document.querySelector('meta[property="og:image"]')?.content || "";
        const ogTitle = document.querySelector('meta[property="og:title"]')?.content || title;
        return { title: ogTitle || title, description: desc, thumbnail: ogImage };
      }
    });
    return results[0]?.result || {};
  } catch(e) {
    return {};
  }
}

async function loadSaved() {
  const { savedVideos = [] } = await chrome.storage.local.get("savedVideos");
  const countEl = document.getElementById("saved-count");
  const listEl = document.getElementById("saved-items");
  countEl.textContent = savedVideos.length;
  listEl.innerHTML = savedVideos.slice(-5).reverse().map(v =>
    `<div class="saved-item">▸ ${v.title || v.url}</div>`
  ).join("");
}

async function saveVideo() {
  const btn = document.getElementById("save-btn");
  const status = document.getElementById("status");
  btn.disabled = true;
  btn.textContent = "保存中...";

  try {
    const tab = await getCurrentTab();
    const url = tab.url;
    const platform = detectPlatform(url);
    const videoId = extractVideoId(url, platform);
    const pageInfo = await scrapePageInfo(tab.id);

    const video = {
      id: videoId || url,
      platform,
      url,
      title: pageInfo.title || url,
      thumbnail: pageInfo.thumbnail || "",
      description: pageInfo.description || "",
      views: 0,
      likes: 0,
      published_at: new Date().toISOString().slice(0, 10),
      channel: "",
      region: "manual",
      is_short: true,
      duration_sec: 30,
      embed_url: url,
      saved_at: new Date().toISOString(),
    };

    // ダッシュボードに送信
    await fetch(`${DASHBOARD_URL}/api/save-video`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(video),
    });

    // ローカルにも保存
    const { savedVideos = [] } = await chrome.storage.local.get("savedVideos");
    savedVideos.push(video);
    await chrome.storage.local.set({ savedVideos });

    btn.textContent = "✅ 保存完了！";
    btn.classList.add("success");
    status.textContent = platform.toUpperCase() + " の動画を保存しました";
    await loadSaved();

    setTimeout(() => {
      btn.textContent = "ダッシュボードに保存";
      btn.classList.remove("success");
      btn.disabled = false;
      status.textContent = "";
    }, 2000);

  } catch(e) {
    btn.textContent = "エラー";
    btn.classList.add("error");
    status.textContent = "失敗: " + e.message;
    console.error("[ViralTracker] save error:", e);
    setTimeout(() => {
      btn.textContent = "ダッシュボードに保存";
      btn.classList.remove("error");
      btn.disabled = false;
    }, 4000);
  }
}

// 初期化
document.getElementById("save-btn").addEventListener("click", saveVideo);

getCurrentTab().then(async (tab) => {
  const url = tab.url;
  const platform = detectPlatform(url);

  const badge = document.getElementById("platform-badge");
  badge.textContent = platform.toUpperCase();
  badge.className = `platform-badge platform-${platform}`;

  document.getElementById("url-display").textContent = url.length > 80 ? url.slice(0, 80) + "..." : url;

  // どのページでも保存可能

  await loadSaved();
});
