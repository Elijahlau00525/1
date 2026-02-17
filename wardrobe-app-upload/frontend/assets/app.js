const TOKEN_KEY = "wardrobe_token_v1";
const THEME_KEY = "wardrobe_theme_v1";
const DEFAULT_THEME = "atelier";
const API_BASE = resolveApiBase();


const THEME_META = {
  atelier: "#1f6a53",
  metro: "#1f4d7a",
  sunset: "#a1454f",
};

const CATEGORY_LABELS = {
  top: "上衣",
  bottom: "下装",
  outer: "外套",
  shoes: "鞋子",
  accessory: "配饰",
};

const OCCASION_LABELS = {
  daily: "日常",
  work: "通勤",
  date: "约会",
  sport: "运动",
  all: "不限",
};

const FIT_LABELS = {
  slim: "修身",
  regular: "常规",
  loose: "宽松",
};

const state = {
  token: localStorage.getItem(TOKEN_KEY) || "",
  user: null,
  items: [],
  providerStatus: {},
};

const el = {
  authView: document.getElementById("auth-view"),
  appView: document.getElementById("app-view"),
  authMessage: document.getElementById("auth-message"),
  uploadMessage: document.getElementById("upload-message"),
  recommendMessage: document.getElementById("recommend-message"),
  welcomeTitle: document.getElementById("welcome-title"),
  themeSelect: document.getElementById("theme-select"),

  loginForm: document.getElementById("login-form"),
  registerForm: document.getElementById("register-form"),
  logoutBtn: document.getElementById("logout-btn"),

  wechatLoginBtn: document.getElementById("wechat-login"),
  qqLoginBtn: document.getElementById("qq-login"),
  socialStatus: document.getElementById("social-status"),

  uploadForm: document.getElementById("upload-form"),
  itemName: document.getElementById("item-name"),
  itemCategory: document.getElementById("item-category"),
  itemOccasion: document.getElementById("item-occasion"),
  itemFit: document.getElementById("item-fit"),
  itemWarmth: document.getElementById("item-warmth"),
  itemImage: document.getElementById("item-image"),

  recommendBtn: document.getElementById("recommend-btn"),
  recommendOccasion: document.getElementById("recommend-occasion"),
  outfitGrid: document.getElementById("outfit-grid"),

  closetGrid: document.getElementById("closet-grid"),
  itemCount: document.getElementById("item-count"),
  template: document.getElementById("item-template"),
};

boot();

function resolveApiBase() {
  const raw = window?.WARDROBE_CONFIG?.apiBase;
  if (typeof raw === "string" && raw.trim()) {
    return raw.replace(/\/+$/, "");
  }
  return "/api";
}


async function boot() {
  initTheme();
  bindEvents();
  bindAuthTabs();
  registerServiceWorker();
  consumeOAuthRedirectToken();
  await loadProviderStatus();

  if (!state.token) {
    showAuth();
    return;
  }

  const ok = await hydrateUser();
  if (!ok) {
    logout();
    showAuth("登录失效，请重新登录。");
    return;
  }

  showApp();
  await refreshItems();
}

function bindEvents() {
  el.loginForm.addEventListener("submit", onLogin);
  el.registerForm.addEventListener("submit", onRegister);
  el.logoutBtn.addEventListener("click", () => logout(true));

  el.wechatLoginBtn.addEventListener("click", () => startSocialLogin("wechat"));
  el.qqLoginBtn.addEventListener("click", () => startSocialLogin("qq"));

  el.uploadForm.addEventListener("submit", onUpload);
  el.recommendBtn.addEventListener("click", onRecommend);

  if (el.themeSelect) {
    el.themeSelect.addEventListener("change", (event) => applyTheme(event.target.value));
  }
}

function bindAuthTabs() {
  const tabs = Array.from(document.querySelectorAll(".tab"));
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((entry) => entry.classList.remove("active"));
      tab.classList.add("active");

      const target = tab.dataset.tab;
      el.loginForm.classList.toggle("hidden", target !== "login");
      el.registerForm.classList.toggle("hidden", target !== "register");
      setText(el.authMessage, "");
    });
  });
}

function initTheme() {
  const savedTheme = localStorage.getItem(THEME_KEY) || DEFAULT_THEME;
  applyTheme(savedTheme);
}

function applyTheme(theme) {
  const resolved = THEME_META[theme] ? theme : DEFAULT_THEME;
  document.body.dataset.theme = resolved;
  localStorage.setItem(THEME_KEY, resolved);

  if (el.themeSelect) {
    el.themeSelect.value = resolved;
  }

  const themeMeta = document.querySelector('meta[name="theme-color"]');
  if (themeMeta) {
    themeMeta.setAttribute("content", THEME_META[resolved]);
  }
}

function registerServiceWorker() {
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/sw.js").catch(() => {
        // Ignore silent registration failures for unsupported hosting setups.
      });
    });
  }
}

function consumeOAuthRedirectToken() {
  const params = new URLSearchParams(window.location.search);
  const token = params.get("token");
  if (!token) {
    return;
  }

  state.token = token;
  localStorage.setItem(TOKEN_KEY, token);

  params.delete("token");
  params.delete("provider");
  params.delete("username");

  const next = params.toString();
  const target = next ? `${window.location.pathname}?${next}` : window.location.pathname;
  window.history.replaceState({}, "", target);
}

async function onLogin(event) {
  event.preventDefault();
  const formData = new FormData(el.loginForm);

  try {
    const result = await apiFetch("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        username: String(formData.get("username") || ""),
        password: String(formData.get("password") || ""),
      }),
      skipAuth: true,
    });

    state.token = result.access_token;
    localStorage.setItem(TOKEN_KEY, state.token);

    await hydrateUser();
    showApp();
    await refreshItems();
  } catch (error) {
    showAuthMessage(error.message);
  }
}

async function onRegister(event) {
  event.preventDefault();
  const formData = new FormData(el.registerForm);

  try {
    const result = await apiFetch("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        username: String(formData.get("username") || ""),
        password: String(formData.get("password") || ""),
      }),
      skipAuth: true,
    });

    state.token = result.access_token;
    localStorage.setItem(TOKEN_KEY, state.token);

    await hydrateUser();
    showApp();
    await refreshItems();
  } catch (error) {
    showAuthMessage(error.message);
  }
}

async function startSocialLogin(provider) {
  const providerInfo = state.providerStatus?.[provider];
  if (providerInfo && !providerInfo.configured) {
    const missing = (providerInfo.required_env || []).join(", ");
    showAuthMessage(
      `${providerInfo.display_name} 登录尚未配置。请先在 backend/.env 填写: ${missing}`
    );
    return;
  }

  try {
    const frontRedirect = `${window.location.origin}${window.location.pathname}`;
    const result = await apiFetch(
      `/auth/${provider}/login?front_redirect=${encodeURIComponent(frontRedirect)}`,
      { skipAuth: true }
    );

    if (!result.authorization_url) {
      throw new Error("登录地址获取失败");
    }

    window.location.href = result.authorization_url;
  } catch (error) {
    showAuthMessage(error.message);
  }
}

async function loadProviderStatus() {
  try {
    const result = await apiFetch("/auth/providers/status", { skipAuth: true });
    state.providerStatus = result || {};
    updateSocialStatusUI();
  } catch {
    state.providerStatus = {};
    updateSocialStatusUI();
  }
}

function updateSocialStatusUI() {
  const wechatReady = !!state.providerStatus?.wechat?.configured;
  const qqReady = !!state.providerStatus?.qq?.configured;

  el.wechatLoginBtn.disabled = !wechatReady;
  el.qqLoginBtn.disabled = !qqReady;

  if (wechatReady || qqReady) {
    setText(
      el.socialStatus,
      `可用状态：微信 ${wechatReady ? "已配置" : "未配置"}，QQ ${qqReady ? "已配置" : "未配置"}`
    );
    return;
  }

  const wechatCallback = state.providerStatus?.wechat?.callback_url || "/api/auth/wechat/callback";
  const qqCallback = state.providerStatus?.qq?.callback_url || "/api/auth/qq/callback";
  setText(
    el.socialStatus,
    `社交登录未配置。先在开放平台配置回调：微信 ${wechatCallback}；QQ ${qqCallback}`
  );
}

async function hydrateUser() {
  try {
    const user = await apiFetch("/auth/me");
    state.user = user;
    el.welcomeTitle.textContent = `${user.username}，开始今天的搭配吧`;
    return true;
  } catch {
    return false;
  }
}

async function refreshItems() {
  try {
    const items = await apiFetch("/items");
    state.items = items;
    renderCloset();
  } catch (error) {
    setText(el.uploadMessage, error.message, true);
  }
}

async function onUpload(event) {
  event.preventDefault();

  const name = el.itemName.value.trim();
  const selectedCategory = el.itemCategory.value;
  const selectedOccasion = el.itemOccasion.value;
  const selectedFit = el.itemFit.value;
  const warmth = Number(el.itemWarmth.value || 2);

  const files = Array.from(el.itemImage.files || []);
  if (!name || !files.length) {
    setText(el.uploadMessage, "请填写名称并选择 PNG 图片。", true);
    return;
  }

  const pngFiles = files.filter((file) => file.type === "image/png");
  if (!pngFiles.length) {
    setText(el.uploadMessage, "当前仅支持 PNG 上传。", true);
    return;
  }

  try {
    let created = 0;
    for (let index = 0; index < pngFiles.length; index += 1) {
      const file = pngFiles[index];
      const base64 = await fileToDataUrl(file);

      let analysis = null;
      if (selectedCategory === "auto" || selectedFit === "auto") {
        analysis = await apiFetch("/items/analyze", {
          method: "POST",
          body: JSON.stringify({ image_base64: base64 }),
        });
      }

      const category = selectedCategory === "auto" ? analysis?.suggested_category || "top" : selectedCategory;
      const fit = selectedFit === "auto" ? analysis?.suggested_fit || "regular" : selectedFit;
      const tags = analysis?.suggested_style_tags || [];

      const payload = {
        name: pngFiles.length === 1 ? name : `${name} ${index + 1}`,
        category,
        occasion: selectedOccasion,
        image_base64: base64,
        fit,
        warmth,
        style_tags: tags,
      };

      await apiFetch("/items", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      created += 1;
    }

    el.uploadForm.reset();
    setText(el.uploadMessage, `上传成功，共 ${created} 件。`);
    await refreshItems();
  } catch (error) {
    setText(el.uploadMessage, error.message, true);
  }
}

async function onRecommend() {
  const occasion = el.recommendOccasion.value;

  try {
    const result = await apiFetch(`/recommend?occasion=${encodeURIComponent(occasion)}`);
    renderOutfit(result);
    const reasonText = result.reasons?.length ? `理由：${result.reasons.join("、")}` : "";
    setText(el.recommendMessage, reasonText);
  } catch (error) {
    renderOutfit(null);
    setText(el.recommendMessage, error.message, true);
  }
}

function renderCloset() {
  el.closetGrid.innerHTML = "";
  el.itemCount.textContent = `${state.items.length} 件`;

  if (!state.items.length) {
    el.closetGrid.innerHTML = '<p class="hint">还没有衣物，先上传几件吧。</p>';
    return;
  }

  for (const item of state.items) {
    const node = createItemNode(item, true);
    el.closetGrid.appendChild(node);
  }
}

function renderOutfit(result) {
  if (!result || !result.slots?.length) {
    el.outfitGrid.classList.add("empty");
    el.outfitGrid.textContent = "当前无法生成搭配，请先上传上衣、下装、鞋子。";
    return;
  }

  el.outfitGrid.classList.remove("empty");
  el.outfitGrid.innerHTML = "";

  for (const slot of result.slots) {
    const node = createItemNode(slot.item, false, slot.slot);
    el.outfitGrid.appendChild(node);
  }
}

function createItemNode(item, allowDelete, slotName = "") {
  const fragment = el.template.content.cloneNode(true);
  const root = fragment.querySelector(".item");
  const image = fragment.querySelector("img");
  const title = fragment.querySelector("h4");
  const line = fragment.querySelector(".line");
  const dot = fragment.querySelector(".dot");
  const hex = fragment.querySelector(".hex");
  const deleteBtn = fragment.querySelector(".danger-btn");

  image.src = item.image_base64;
  title.textContent = slotName ? `${slotLabel(slotName)} · ${item.name}` : item.name;
  line.textContent = `${CATEGORY_LABELS[item.category] || item.category} | ${OCCASION_LABELS[item.occasion] || item.occasion} | ${FIT_LABELS[item.fit] || item.fit}`;
  dot.style.backgroundColor = item.color_hex;
  hex.textContent = item.color_hex;

  if (!allowDelete) {
    deleteBtn.classList.add("hidden");
  } else {
    deleteBtn.addEventListener("click", async () => {
      try {
        await apiFetch(`/items/${item.id}`, { method: "DELETE" });
        await refreshItems();
      } catch (error) {
        setText(el.uploadMessage, error.message, true);
      }
    });
  }

  return root;
}

function slotLabel(slot) {
  switch (slot) {
    case "top":
      return "上衣";
    case "bottom":
      return "下装";
    case "shoes":
      return "鞋子";
    case "outer":
      return "外套";
    case "accessory":
      return "配饰";
    default:
      return slot;
  }
}

function showAuth(message = "") {
  el.authView.classList.remove("hidden");
  el.appView.classList.add("hidden");
  el.logoutBtn.classList.add("hidden");
  showAuthMessage(message);
}

function showApp() {
  el.authView.classList.add("hidden");
  el.appView.classList.remove("hidden");
  el.logoutBtn.classList.remove("hidden");
  showAuthMessage("");
}

function logout(showMsg = false) {
  state.token = "";
  state.user = null;
  state.items = [];
  localStorage.removeItem(TOKEN_KEY);

  showAuth(showMsg ? "你已退出登录。" : "");
}

function showAuthMessage(text) {
  setText(el.authMessage, text, !!text);
}

function setText(element, text, highlightError = false) {
  element.textContent = text || "";
  element.style.color = highlightError ? "#8f3535" : "#596a66";
}

async function apiFetch(path, options = {}) {
  const { skipAuth = false, ...rest } = options;
  const headers = new Headers(rest.headers || {});
  headers.set("Content-Type", "application/json");
  if (!skipAuth && state.token) {
    headers.set("Authorization", `Bearer ${state.token}`);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers,
  });

  if (response.status === 204) {
    return null;
  }

  const text = await response.text();
  const payload = text ? safeJsonParse(text) : {};

  if (!response.ok) {
    const detail = payload?.detail || `请求失败 (${response.status})`;
    throw new Error(detail);
  }

  return payload;
}

function safeJsonParse(text) {
  try {
    return JSON.parse(text);
  } catch {
    return {};
  }
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error("文件读取失败"));
    reader.readAsDataURL(file);
  });
}



