// V4.8.2 ARCHIVE — moderation and integrity UI.
const DB = "khazina_db",
  STORE = "items";
let db,
  frontImg = "",
  backImg = "",
  frontImageRemoved = false,
  backImageRemoved = false,
  promptInstall,
  isSaving = false,
 mediaPicking = false,
editingItemId = "";
let latestItems = [];
function newId() {
  try {
    if (globalThis.crypto && typeof globalThis.crypto.randomUUID === "function")
      return globalThis.crypto.randomUUID();
  } catch (e) {}
  return (
    "k-" +
    Date.now().toString(36) +
    "-" +
    Math.random().toString(36).slice(2) +
    "-" +
    Math.random().toString(36).slice(2)
  );
}
const $ = (x) => document.getElementById(x),
  v = (x) => {
    const el = $(x);
    return el ? String(el.value ?? "").trim() : "";
  },
  n = (x) => {
    const el = $(x);
    return Number(el?.value || 0);
  };

function selectedCountryValue() {
  const sel = $("country");
  if (!sel) return "";
  if (sel.value === "__other__") return v("countryOther");
  return String(sel.value || "").trim();
}
function updateCountryUI() {
  const sel = $("country"), wrap = $("countryOtherWrap"), other = $("countryOther");
  if (!sel || !wrap || !other) return;
  const isOther = sel.value === "__other__";
  wrap.hidden = !isOther;
  other.required = isOther;
  if (!isOther) other.value = "";
}
function setCountryValue(value) {
  const sel = $("country"), other = $("countryOther");
  if (!sel) return;
  const wanted = String(value || "").trim();
  if (!wanted) { sel.value = ""; if (other) other.value = ""; updateCountryUI(); return; }
  const exists = Array.from(sel.options).some((o) => o.value === wanted);
  if (exists) {
    sel.value = wanted;
    if (other) other.value = "";
  } else {
    sel.value = "__other__";
    if (other) other.value = wanted;
  }
  updateCountryUI();
}
async function api(path, opt = {}) {
  let req = {
      ...opt,
      headers: { "Content-Type": "application/json", ...(opt.headers || {}) },
      cache: "no-store",
    },
    r,
    j = null,
    lastErr = null,
    maxAttempts = path === "/api/item" || path === "/api/items" ? 3 : 1;
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    try {
      r = await fetch(path, req);
      lastErr = null;
      break;
    } catch (e) {
      lastErr = e;
      if (attempt < maxAttempts - 1) {
        await new Promise((ok) => setTimeout(ok, 450 * (attempt + 1)));
        continue;
      }
    }
  }
  if (!r) {
    throw new Error(
      lastErr?.message === "Failed to fetch"
        ? "تعذر الوصول إلى خادم الحفظ. تحقق أن نافذة تشغيل البرنامج ما زالت مفتوحة ثم أعد المحاولة."
        : lastErr?.message || "تعذر الاتصال بالخادم",
    );
  }
  try {
    j = await r.json();
  } catch (e) {}
  if (r.status === 401) {
    location.href = "/admin-login";
    throw new Error("انتهت جلسة الإدارة؛ جارٍ فتح صفحة الدخول من جديد.");
  }
  if (!r.ok || j?.ok === false)
    throw new Error(j?.error || "تعذر الاتصال بقاعدة البيانات المشتركة");
  return j || {};
}
async function all() {
  return ((await api("/api/items")).items || []).filter(i => !['archived','removed'].includes(i.moderationStatus||'') && !i.ownerArchived);
}
async function archivedItems(){ return (await api('/api/archive/items')).items || []; }
async function put(x) {
  return api("/api/item", {
    method: "POST",
    body: JSON.stringify({ item: x }),
  });
}
async function del(id) {
  return api("/api/item/" + encodeURIComponent(id), { method: "DELETE" });
}


// Stage 4.2: unified administration notification.
// Previous releases called toast() without defining it in every administration page.
window.toast = window.toast || function(message, timeout=2600) {
  try {
    let box = document.getElementById("nawader-global-toast");
    if (!box) {
      box = document.createElement("div");
      box.id = "nawader-global-toast";
      box.setAttribute("role","status");
      box.style.cssText = "position:fixed;z-index:99999;left:50%;bottom:28px;transform:translateX(-50%);background:#0d1b3b;color:#fff;border:1px solid #c79245;border-radius:12px;padding:11px 18px;font-weight:700;box-shadow:0 8px 28px #0005;max-width:min(88vw,620px);text-align:center;display:none";
      document.body.appendChild(box);
    }
    box.textContent = String(message ?? "");
    box.style.display = "block";
    clearTimeout(window.__nawaderToastTimer);
    window.__nawaderToastTimer = setTimeout(()=>{ box.style.display="none"; }, Math.max(1200, Number(timeout)||2600));
  } catch (_) {
    try { alert(String(message ?? "")); } catch(__) {}
  }
};
const toast = (...args) => window.toast(...args);

// V4 Stage 4: one controlled movement path between administration sections.
function itemStoreKey(i){return (i?.storeType==='collectibles'||i?.fantasiaEnabled)?'collectibles':'coins';}
function itemStoreQuery(i){return '?store='+itemStoreKey(i);}
function adminItemLocation(i) {
  if (i?.sold || Number(i?.soldQuantity || 0) >= Number(i?.quantity || 1)) return "sold";
  if (i?.archived) return "archived";
  if (["warehouse","market","auction","special","outside"].includes(i?.adminLocation)) return i.adminLocation;
  if (i?.forAuction) return "auction";
  if (i?.forMarket) return "market";
  if (i?.specialNumberEnabled) return "special";
  if (i?.outsideDisplay) return "outside";
  return "warehouse";
}
function moveDestinationLabel(v) {
  return ({warehouse:"المستودع",market:"السوق العام",auction:"المزاد",special:"المميزة والنادرة",outside:"خارج العرض"})[v] || v;
}
function adminMoveNotice(msg) {
  try {
    if (typeof window.toast === "function") return window.toast(msg);
    if (typeof toast === "function") return toast(msg);
  } catch(_) {}
  alert(msg);
}


// V4 Stage 4.1 SAFETY: never increase the collectible's original quantity when an order is returned.
// Returned stock is resolved by the server inventory ledger, which preserves the invariant:
// current = warehouse + market + auction + reserved + returned.
window.restoreOrderItemToWarehouse = async (itemId, qty=1) => {
  const q = Math.max(1, Number(qty || 1));
  const result = await api("/api/inventory/return-resolution", {
    method: "POST",
    body: JSON.stringify({ itemId, action: "warehouse", quantity: q })
  });
  await refresh(true);
  return result;
};

window.moveAdminItem = async (id, target) => {
  try {
    const rows = await all(), old = rows.find(x => String(x.id) === String(id));
    if (!old) throw new Error("المقتنى غير موجود");
    const current = adminItemLocation(old);
    if (["sold","archived"].includes(current)) throw new Error("المقتنى المباع أو المؤرشف لا يدخل في النقل العادي");
    if (current === "auction")
      throw new Error("لا يتم نقل المقتنى من المزاد النشط. انتظر انتهاء المزاد وترحيله إلى قسم المزادات المنتهية، ثم نفّذ الإجراء من هناك.");
    if (current === target) return adminMoveNotice("المقتنى موجود بالفعل في " + moveDestinationLabel(target));
    if (!confirm(`نقل المقتنى من ${moveDestinationLabel(current)} إلى ${moveDestinationLabel(target)}؟\nلن يتم إنشاء نسخة جديدة ولن تُحذف الصور أو بيانات التقييم.`)) return;
    const item = {...old};
    // A collectible has one administration display location at a time.
    item.forMarket = false; item.marketApproved = false;
    item.forAuction = false; item.auctionApproved = false;
    item.specialNumberEnabled = false; item.outsideDisplay = false;
    if (target === "market") { item.forMarket = true; item.marketApproved = true; }
    else if (target === "auction") { item.forAuction = true; item.auctionApproved = false; }
    else if (target === "special") item.specialNumberEnabled = true;
    else if (target === "outside") item.outsideDisplay = true;
    item.adminLocation = target;
    item.inWarehouse = (target === "warehouse");
    item.warehouseAvailable = (target === "warehouse");
    item.locationUpdatedAt = new Date().toISOString();
    item.updated = Date.now();
    const saved = await put(item);
    if (!saved?.saved || String(saved.saved.id) !== String(id)) throw new Error("لم يؤكد الخادم حفظ نفس المقتنى");
    await refresh(true);
    adminMoveNotice(target === "auction" ? "تم النقل إلى المزاد. أكمل إعداد وقت المزاد وحد البيع ثم اعتمده." : `تم نقل المقتنى إلى ${moveDestinationLabel(target)}.`);
  } catch(e) { alert("تعذر النقل: " + e.message); }
};
function isWarehouseItem(i) { return adminItemLocation(i) === "warehouse"; }
function isMarketItem(i) { return adminItemLocation(i) === "market"; }
function isAuctionItem(i) { return adminItemLocation(i) === "auction"; }
function isSpecialItem(i) { return adminItemLocation(i) === "special"; }
function adminMoveButtons(i, current) {
  const id = String(i.id || i.itemId || "").replace(/'/g,"\\'");
  const targets = ["warehouse","market","auction","special","outside"].filter(x => x !== current);
  return `<details class="admin-move-menu"><summary>نقل إلى</summary><div class="admin-move-options">${targets.map(t=>`<button type="button" class="ghost" onclick="moveAdminItem('${id}','${t}')">${moveDestinationLabel(t)}</button>`).join("")}</div></details>`;
}
window.returnEndedAuctionToWarehouse = async (id) => {
  try {
    const rows = await all(), old = rows.find(x => String(x.id) === String(id));
    if (!old) throw new Error("المقتنى غير موجود");
    if (String(old.auctionOutcome || "") === "sold" || old.sold || Number(old.soldQuantity || 0) >= Number(old.quantity || 1))
      throw new Error("المزاد ناجح ومغلق؛ لا يمكن إعادته للمستودع إلا بعد استثناء موثق قبل اكتمال البيع");
    const item = {...old};
    // Returning an ended auction to the warehouse must also stop any stale market listing.
    // This prevents the same physical collectible from remaining visible in two stock locations.
    item.forAuction = false;
    item.auctionApproved = false;
    item.forMarket = false;
    item.marketApproved = false;
    item.adminLocation = "warehouse";
    item.inWarehouse = true;
    item.warehouseAvailable = true;
    item.locationUpdatedAt = new Date().toISOString();
    item.updated = Date.now();
    const saved = await put(item);
    if (!saved?.saved || String(saved.saved.id) !== String(id)) throw new Error("لم يؤكد الخادم حفظ نفس المقتنى");
    await refresh(true);
    adminMoveNotice("تمت إعادة المقتنى من المزادات المنتهية إلى المستودع.");
  } catch(e) { alert("تعذر الإرجاع: " + e.message); }
};
async function clearDB() {
  return api("/api/clear", { method: "POST", body: "{}" });
}
async function migrateLocal() {
  try {
    let old = await new Promise((ok, no) => {
      let r = indexedDB.open(DB, 1);
      r.onupgradeneeded = () => {
        if (!r.result.objectStoreNames.contains(STORE))
          r.result.createObjectStore(STORE, { keyPath: "id" });
      };
      r.onsuccess = () => {
        let d = r.result,
          t = d.transaction(STORE).objectStore(STORE).getAll();
        t.onsuccess = () => ok(t.result || []);
        t.onerror = () => no(t.error);
      };
      r.onerror = () => no(r.error);
    });
    if (old.length) {
      let z = await api("/api/merge", {
        method: "POST",
        body: JSON.stringify({ items: old }),
      });
      console.log("تم دمج البيانات المحلية:", z.added);
    }
  } catch (e) {
    console.warn("تعذر ترحيل البيانات المحلية", e);
  }
}
function esc(s) {
  return String(s ?? "").replace(
    /[&<>"']/g,
    (m) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        m
      ],
  );
}
function money(x) {
  return Number(x || 0).toLocaleString("ar-SA") + " ر.س";
}
function serial(s) {
  s = (s || "").replace(/\D/g, "");
  if (!s) return "";
  if (/^(\d)\1+$/.test(s)) return "موحد";
  if (s === s.split("").reverse().join("")) return "رادار";
  if (s.length % 2 === 0 && s.slice(0, s.length / 2) === s.slice(s.length / 2))
    return "مكرر";
  if ("01234567890123456789".includes(s)) return "متتابع صاعد";
  if ("98765432109876543210".includes(s)) return "متتابع نازل";
  return "عادي";
}
function loc(i) {
  return (
    [
      ["مستودع", i.warehouse],
      ["خزانة", i.cabinet],
      ["رف", i.shelf],
      ["صندوق", i.box],
      ["ألبوم", i.album],
      ["صفحة/جيب", i.pocket],
    ]
      .filter((x) => x[1])
      .map((x) => x.join(" "))
      .join(" ← ") || "غير محدد"
  );
}
async function compressImageForUpload(f) {
  if (!f) return f;
  if (!/^image\//.test(f.type || "")) throw new Error("الملف ليس صورة");
  if (f.size > 50 * 1024 * 1024)
    throw new Error(
      "الصورة أكبر من 50 ميجابايت؛ خفّض دقة الكاميرا أو اختر صورة أصغر",
    );
  if (f.size <= 900 * 1024 && /image\/(jpeg|webp)/i.test(f.type || ""))
    return f;
  let source,
    url = "";
  try {
    if (typeof createImageBitmap === "function")
      source = await createImageBitmap(f);
    else {
      url = URL.createObjectURL(f);
      source = await new Promise((ok, no) => {
        let im = new Image();
        im.onload = () => ok(im);
        im.onerror = () => no(new Error("تعذر قراءة الصورة"));
        im.src = url;
      });
    }
    let w = source.width || source.naturalWidth,
      h = source.height || source.naturalHeight,
      scale = Math.min(1, 1600 / Math.max(w, h)),
      canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(w * scale));
    canvas.height = Math.max(1, Math.round(h * scale));
    let ctx = canvas.getContext("2d", { alpha: false });
    ctx.fillStyle = "#fff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(source, 0, 0, canvas.width, canvas.height);
    let blob = await new Promise((ok) => canvas.toBlob(ok, "image/jpeg", 0.8));
    if (!blob) throw new Error("تعذر ضغط الصورة");
    return new File(
      [blob],
      (f.name || "photo").replace(/\.[^.]+$/, "") + ".jpg",
      {
        type: "image/jpeg",
        lastModified: Date.now(),
      },
    );
  } catch (e) {
    throw new Error(
      "تعذر تجهيز الصورة. اختر صورة JPG أصغر من المعرض ثم حاول مرة أخرى.",
    );
  } finally {
    if (source && typeof source.close === "function") source.close();
    if (url) URL.revokeObjectURL(url);
  }
}
async function imgFile(f) {
  if (!f) return "";
  let ready = await compressImageForUpload(f);
  let r = await fetch("/api/upload", {
    method: "POST",
    headers: {
      "Content-Type": ready.type || "application/octet-stream",
      "X-File-Name": encodeURIComponent(ready.name || "photo.jpg"),
    },
    body: ready,
    cache: "no-store",
  });
  if (!r.ok) {
    let t = "";
    try {
      t = (await r.json()).error || "";
    } catch (e) {}
    throw new Error(t || "تعذر رفع الصورة إلى الحفظ الدائم");
  }
  return (await r.json()).url || "";
}
function setPreview(which, data) {
  let el = $(which + "Preview"),
    btn = $(which === "front" ? "editFrontImage" : "editBackImage"),
    clr = $(which === "front" ? "clearFrontImage" : "clearBackImage");
  if (data) {
    el.src = data;
    el.hidden = false;
    if (btn) btn.hidden = false;
    if (clr) clr.hidden = false;
  } else {
    el.removeAttribute("src");
    el.hidden = true;
    if (btn) btn.hidden = true;
    if (clr) clr.hidden = true;
  }
}
let generatedSerials = [];
function serialValues() {
  if ($("autoSerialEnabled")?.checked) return generatedSerials.slice();
  return [...document.querySelectorAll(".serial-input")]
    .map((x) => x.value.trim())
    .filter(Boolean);
}
function renderSerialFields(values) {
  if ($("autoSerialEnabled")?.checked) {
    $("serialFields").innerHTML = generatedSerials.length
      ? `<details><summary>تم توليد ${generatedSerials.length} رقمًا — اضغط لعرض القائمة</summary><div class="serial-generated-list">${generatedSerials.map((x) => `<span dir="ltr">${esc(x)}</span>`).join("")}</div></details>`
      : '<p class="muted">أدخل أول رقم ثم اضغط «توليد ومعاينة».</p>';
    return;
  }
  let q = Math.max(1, n("quantity") || 1),
    old = Array.isArray(values)
      ? values
      : [...document.querySelectorAll(".serial-input")].map((x) => x.value),
    manualCount = Math.min(q, 200),
    fields = Array.from(
      { length: manualCount },
      (_, i) =>
        `<label>القطعة ${i + 1}<input class="serial-input" data-i="${i}" value="${esc(old[i] || "")}" placeholder="الرقم التسلسلي"><small class="muted serial-analysis">${esc(serial(old[i] || ""))}</small></label>`,
    ).join("");
  $("serialFields").innerHTML =
    q > 3
      ? `<details ${q <= 5 ? "open" : ""}><summary>إدخال ${manualCount} أرقام تسلسلية — اضغط للفتح أو الإغلاق</summary><div class="serial-fields-inner">${fields}</div>${q > manualCount ? '<p class="muted">للكميات الكبيرة استخدم التوليد الآلي حتى لا تتكدس الصفحة.</p>' : ""}</details>`
      : `<div class="serial-fields-inner">${fields}</div>`;
  document
    .querySelectorAll(".serial-input")
    .forEach(
      (x) =>
        (x.oninput = () =>
          (x.parentElement.querySelector(".serial-analysis").textContent =
            serial(x.value))),
    );
}
function inventoryUnitLabel(type) {
  return ({ piece: "ورقة/قطعة", coin: "عملة معدنية", set: "طقم", bundle: "حزمة", strap: "ربطة", lot: "بندل/مجموعة" })[type] || "وحدة";
}
function updateInventoryQuantity() {
  let units = Math.max(1, n("inventoryUnitCount") || 1),
    pieces = Math.max(1, n("piecesPerUnit") || 1),
    total = units * pieces;
  $("quantity").value = total;
  if ($("inventoryQuantityPreview"))
    $("inventoryQuantityPreview").textContent = `${units} ${inventoryUnitLabel(v("inventoryUnitType"))} × ${pieces} = ${total} ورقة/قطعة`;
  if ($("serialCount") && !$('serialCount').dataset.userChanged) $("serialCount").value = total;
  renderSerialFields();
}
function generateSerialSequence(start, count) {
  start = String(start || "").trim();
  count = Math.max(1, Math.min(5000, Number(count) || 1));
  let match = start.match(/^(.*?[\/\-:]\s*)(\d(?:\s*\d)*)(\D*)$/) || start.match(/^(.*?)(\d+)(\D*)$/);
  if (!match) throw new Error("يجب أن ينتهي الرقم الأول بجزء رقمي يمكن تسلسله");
  let prefix = match[1], digits = match[2].replace(/\s/g, ""), suffix = match[3] || "", first = BigInt(digits), width = digits.length;
  return Array.from({ length: count }, (_, i) => prefix + (first + BigInt(i)).toString().padStart(width, "0") + suffix);
}
function updateAutoSerialUI() {
  let enabled = !!$("autoSerialEnabled")?.checked;
  if ($("autoSerialFields")) $("autoSerialFields").hidden = !enabled;
  if (!enabled) generatedSerials = [];
  renderSerialFields();
}
function auctionText(end) {
  if (!end) return "";
  let d = new Date(end).getTime() - Date.now();
  if (d <= 0) return "انتهى المزاد";
  let days = Math.floor(d / 86400000);
  d %= 86400000;
  let h = Math.floor(d / 3600000);
  d %= 3600000;
  let m = Math.floor(d / 60000);
  let sec = Math.floor((d % 60000) / 1000);
  return `${days} يوم، ${h} ساعة، ${m} دقيقة، ${sec} ثانية`;
}
function updateAuctionUI() {
  $("auctionFields").hidden = !$("forAuction").checked;
  $("auctionCountdown").textContent = $("forAuction").checked
    ? auctionText($("auctionEnd").value)
    : "";
}
function updateEditionUI() {
  if ($("issueEditionOtherWrap"))
    $("issueEditionOtherWrap").hidden = $("issueEdition").value !== "أخرى";
}
function updateYearUI() {
  let range = $("yearMode").value === "range";
  if ($("yearToWrap")) $("yearToWrap").hidden = !range;
  if (!range && $("yearTo")) $("yearTo").value = "";
}
function gradingCompanyKey(name) {
  return String(name || "").trim().toLocaleLowerCase("ar");
}
function loadCustomGradingCompanies() {
  try {
    let arr = JSON.parse(localStorage.getItem("nawaderCustomGradingCompanies") || "[]");
    return Array.isArray(arr) ? arr.filter(Boolean).map((x) => String(x).trim()).filter(Boolean) : [];
  } catch (_) {
    return [];
  }
}
function saveCustomGradingCompanies(arr) {
  try {
    localStorage.setItem("nawaderCustomGradingCompanies", JSON.stringify(arr));
  } catch (_) {}
}
function ensureGradingCompanyOption(name) {
  let sel = $("gradingCompany"), clean = String(name || "").trim();
  if (!sel || !clean) return;
  let key = gradingCompanyKey(clean);
  let found = Array.from(sel.options).find((o) => gradingCompanyKey(o.value) === key);
  if (!found) sel.add(new Option(clean, clean));
}
function initGradingCompanies() {
  loadCustomGradingCompanies().forEach(ensureGradingCompanyOption);
}
function openAddGradingCompany() {
  let wrap = $("addGradingCompanyWrap");
  if (!wrap) return;
  wrap.hidden = false;
  let input = $("newGradingCompany");
  if (input) { input.value = ""; setTimeout(() => input.focus(), 0); }
}
function closeAddGradingCompany() {
  let wrap = $("addGradingCompanyWrap");
  if (wrap) wrap.hidden = true;
  if ($("newGradingCompany")) $("newGradingCompany").value = "";
}
function addGradingCompany() {
  let input = $("newGradingCompany"), sel = $("gradingCompany");
  let name = String(input?.value || "").trim();
  if (!name) { alert("اكتب اسم جهة التقييم أولاً."); return; }
  ensureGradingCompanyOption(name);
  let arr = loadCustomGradingCompanies();
  if (!arr.some((x) => gradingCompanyKey(x) === gradingCompanyKey(name))) {
    arr.push(name);
    saveCustomGradingCompanies(arr);
  }
  if (sel) sel.value = name;
  closeAddGradingCompany();
}
function updateGradingUI() {
  if ($("gradingFields")) $("gradingFields").hidden = !$("isGraded").checked;
  if (!$("isGraded")?.checked) closeAddGradingCompany();
}
function composedYear() {
  let a = v("yearFrom"),
    b = v("yearTo");
  return $("yearMode").value === "range" && b
    ? a && b
      ? a + "–" + b
      : a || b
    : a;
}
function fillYearFields(value, from = "", to = "") {
  let y = String(value || "").trim();
  let a = String(from || "").trim(),
    b = String(to || "").trim();
  if (!a && y) {
    let m = y.match(/^\s*([^–—-]+)\s*[–—-]\s*([^–—-]+)\s*$/);
    if (m) {
      a = m[1].trim();
      b = m[2].trim();
    } else a = y;
  }
  if ($("yearFrom")) $("yearFrom").value = a;
  if ($("yearTo")) $("yearTo").value = b;
  if ($("yearMode")) $("yearMode").value = b ? "range" : "single";
  updateYearUI();
}


// V4.2.5 — قوائم موقع التخزين المترابطة مع الحفاظ على نفس حقول الحفظ القديمة
const STORAGE_FIELDS = ["warehouse", "cabinet", "shelf", "box", "album", "pocket"];
const STORAGE_LABELS = {
  warehouse: "المستودع",
  cabinet: "الخزانة",
  shelf: "الرف",
  box: "الصندوق",
  album: "الألبوم",
  pocket: "الصفحة أو الجيب",
};
let storageCatalogRows = [];
const storageManualValues = Object.fromEntries(STORAGE_FIELDS.map((k) => [k, new Set()]));
function cleanStorageValue(x) { return String(x ?? "").trim(); }
function storageRowFromItem(i = {}) {
  return Object.fromEntries(STORAGE_FIELDS.map((k) => [k, cleanStorageValue(i[k])]));
}
function updateStorageCatalogFromItems(items = []) {
  storageCatalogRows = (Array.isArray(items) ? items : []).map(storageRowFromItem);
}
function storageParentsMatch(row, field, selected) {
  const ix = STORAGE_FIELDS.indexOf(field);
  for (let n = 0; n < ix; n++) {
    const p = STORAGE_FIELDS[n], wanted = cleanStorageValue(selected[p]);
    if (wanted && cleanStorageValue(row[p]) !== wanted) return false;
  }
  return true;
}
function storageSelectedValues() {
  return Object.fromEntries(STORAGE_FIELDS.map((k) => [k, cleanStorageValue($(k)?.value)]));
}
function renderStorageSelectors(preferred = {}) {
  const selected = { ...storageSelectedValues(), ...Object.fromEntries(STORAGE_FIELDS.map((k) => [k, preferred[k] !== undefined ? cleanStorageValue(preferred[k]) : storageSelectedValues()[k]])) };
  STORAGE_FIELDS.forEach((field) => {
    const el = $(field); if (!el || el.tagName !== "SELECT") return;
    const values = new Set();
    storageCatalogRows.forEach((row) => {
      if (storageParentsMatch(row, field, selected) && cleanStorageValue(row[field])) values.add(cleanStorageValue(row[field]));
    });
    storageManualValues[field].forEach((x) => x && values.add(x));
    if (field === "warehouse") values.add("المستودع الرئيسي");
    if (selected[field]) values.add(selected[field]);
    const placeholder = `اختر ${STORAGE_LABELS[field]}...`;
    el.innerHTML = `<option value="">${placeholder}</option>` +
      [...values].sort((a,b) => a.localeCompare(b, "ar")).map((x) => `<option value="${esc(x)}">${esc(x)}</option>`).join("") +
      `<option value="__new__">＋ إضافة جديد...</option>`;
    el.value = selected[field] || "";
  });
}
function clearStorageBelow(field) {
  const ix = STORAGE_FIELDS.indexOf(field);
  STORAGE_FIELDS.slice(ix + 1).forEach((k) => { if ($(k)) $(k).value = ""; });
}
async function loadStorageCatalog(preferred = {}) {
  try { updateStorageCatalogFromItems(await all()); } catch (e) { console.warn("تعذر تحديث قائمة مواقع التخزين", e); }
  renderStorageSelectors(preferred);
}
function setupStorageSelectors() {
  STORAGE_FIELDS.forEach((field) => {
    const el = $(field); if (!el || el.tagName !== "SELECT") return;
    el.addEventListener("change", () => {
      if (el.value === "__new__") {
        const name = cleanStorageValue(prompt(`اكتب اسم ${STORAGE_LABELS[field]} الجديد:`) || "");
        if (!name) { el.value = ""; renderStorageSelectors(); return; }
        storageManualValues[field].add(name);
        el.value = name;
      }
      const current = storageSelectedValues();
      current[field] = cleanStorageValue(el.value);
      clearStorageBelow(field);
      STORAGE_FIELDS.slice(STORAGE_FIELDS.indexOf(field) + 1).forEach((k) => current[k] = "");
      renderStorageSelectors(current);
    });
  });
  loadStorageCatalog();
  document.querySelectorAll('nav button[data-v="add"],.dashboard-go[data-go="add"]').forEach((b) =>
    b.addEventListener("click", () => loadStorageCatalog(storageSelectedValues()))
  );
}
if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", setupStorageSelectors);
else setupStorageSelectors();

function show(vw) {
  document
    .querySelectorAll(".view")
    .forEach((x) => x.classList.toggle("active", x.id === vw || (vw === "warehouse" && x.id === "warehouseView")));
  document
    .querySelectorAll("nav button")
    .forEach((x) => x.classList.toggle("active", x.dataset.v === vw));
}
document.querySelectorAll("nav button").forEach(
  (b) =>
    (b.onclick = async () => {
      show(b.dataset.v);
      if (
        [
          "home",
          "warehouse",
          "special",
          "transitional",
          "fantasia",
          "list",
          "auction",
          "ended-auctions",
          "market",
          "finance",
          "participants",
        ].includes(b.dataset.v)
      )
        await refresh(true);
      if (b.dataset.v === "participants") await renderParticipants();
      if (b.dataset.v === "warehouse") await renderWarehouse();
      if (b.dataset.v === "special") await renderSpecialAdmin();
      if (b.dataset.v === "transitional") await renderTransitionalAdmin();
      if (b.dataset.v === "fantasia") await renderFantasiaAdmin();
      if (b.dataset.v === "ended-auctions") await renderEndedAuctions();
      if (b.dataset.v === "market") await renderMarketAdmin();
      if (b.dataset.v === "finance") await renderFinance();
    }),
);
document.querySelectorAll(".dashboard-go").forEach((b) =>
  b.addEventListener("click", async () => {
    let vw = b.dataset.go;
    if (!vw) return;
    show(vw);
    if (
      [
        "home",
        "warehouse",
        "special",
        "transitional",
        "fantasia",
        "list",
        "auction",
        "ended-auctions",
        "market",
        "finance",
        "participants",
      ].includes(vw)
    )
      await refresh(true);
    if (vw === "participants") await renderParticipants();
    if (vw === "warehouse") await renderWarehouse();
    if (vw === "special") await renderSpecialAdmin();
    if (vw === "transitional") await renderTransitionalAdmin();
    if (vw === "fantasia") await renderFantasiaAdmin();
    if (vw === "ended-auctions") await renderEndedAuctions();
    if (vw === "market") await renderMarketAdmin();
    if (vw === "finance") await renderFinance();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }),
);
let adminAuctionImageGroups = {};
window.openAdminAuctionImages = (id, idx = 0) => {
  let g = adminAuctionImageGroups[id] || [];
  if (g.length) openCoinLightbox(g, Math.min(idx, g.length - 1), "صور المزاد");
};
function auctionCard(i) {
  let left = auctionText(i.auctionEnd),
    ended = left === "انتهى المزاد";
  adminAuctionImageGroups[i.id] = [
    i.frontImg,
    i.backImg,
    i.gradingCertImage,
    ...(i.additionalImages || []),
  ].filter(Boolean);
  let successfulClosed = ended && endedAuctionSuccessful(i), exception = ended && endedAuctionException(i);
  let endedActions = successfulClosed
    ? `<button class="danger-outline" onclick="openAuctionException('${i.id}')">استثناء</button>`
    : `<button class="gold-action" onclick="openRelaunch('${i.id}')">♻ إعادة المزاد</button><button class="ghost" onclick="returnEndedAuctionToWarehouse('${i.id}')">إعادة للمستودع</button>`;
  return `<article class="item auction-item ${successfulClosed ? "successful-locked" : ""}">${i.frontImg ? `<div class="auction-card-image"><img src="${i.frontImg}" onclick="openAdminAuctionImages('${i.id}',0)" title="اضغط لفتح عارض الصور" style="cursor:zoom-in"><span class="auction-state ${successfulClosed ? "sold" : exception ? "exception" : ended ? "ended" : "live"}">${successfulClosed ? "ناجح — مغلق" : exception ? "استثناء" : ended ? "منتهي" : "نشط"}</span></div>` : '<div class="auction-card-image no-photo">لا توجد صورة</div>'}<div class="auction-card-body"><div class="auction-card-title"><h3>${esc(i.country)} — ${esc(i.denomination)} ${transitionalBadge(i)}</h3><span class="approval-chip ${successfulClosed ? "ok" : i.auctionApproved ? "ok" : "pending"}">${successfulClosed ? "🏆 مزاد ناجح" : i.auctionApproved ? "✓ نشط" : "موقوف/غير منشور"}</span></div><p class="auction-clock ${ended ? "ended" : ""}" data-end="${esc(i.auctionEnd || "")}">${esc(left || "بدون وقت انتهاء")}</p><div class="auction-admin-metrics"><div><span>السعر الحالي</span><b>${money(i.auctionCurrentPrice || 0)}</b></div><div><span>سعر الفتح</span><b>${money(i.auctionOpeningPrice || i.auctionStartPrice || 0)}</b></div><div><span>قيمة الزيادة</span><b>${money(i.auctionBidStep || 1)}</b></div><div class="private-metric"><span>حد البيع • إدارة فقط</span><b>${money(i.auctionTargetPrice || Number(i.auctionStartPrice || 0) + 1)}</b></div></div>${successfulClosed ? '<p class="sold-order-note">🔒 أُغلق المزاد بنجاح؛ لا عودة ولا إعادة مزايدة إلا باستثناء موثق.</p>' : ""}<p class="round-chip">الجولة ${Number(i.auctionRound || 1)}</p><div class="actions auction-actions"><button onclick="detail('${i.id}')">عرض</button>${archiveButton(i.id)}${!successfulClosed ? `<button class="ghost" onclick="editItem('${i.id}')">✎ تعديل المقتنى</button>${!ended ? `<button class="ghost auction-quick-edit-btn" onclick="openAuctionQuickEdit('${i.id}')">⚙️ تعديل المزاد</button><button class="danger" onclick="cancelActiveAuction('${i.id}')">⛔ إلغاء المزاد</button>` : ""}` : ""}${ended ? endedActions : ""}<a class="public-link" href="/auction${itemStoreQuery(i)}#${i.id}" target="_blank">مشاركة</a></div><div class="bid-list" id="bids-${i.id}" data-round="${Number(i.auctionRound || 1)}"></div></div></article>`;
}

function endedReserveReached(i) {
  return (
    Number(i.auctionCurrentPrice || 0) >=
    Number(i.auctionTargetPrice || Number(i.auctionStartPrice || 0) + 1)
  );
}
function endedAuctionSuccessful(i) {
  // The server outcome is the authoritative result because the reserve price may be edited later.
  return String(i.auctionOutcome || "") === "sold";
}
function endedAuctionException(i) {
  return String(i.auctionOutcome || "") === "exception" || !!i.auctionExceptionAt;
}
function endedAuctionCancelled(i) {
  return String(i.auctionOutcome || "") === "cancelled" || !!i.auctionCancelledAt;
}
function auctionExceptionLabel(reason) {
  return ({
    non_payment: "عدم الدفع",
    bidder_withdrawal: "انسحاب المزايد",
    winner_ineligible: "عدم أهلية الفائز",
    admin_exception: "استثناء إداري",
    other: "سبب آخر",
  })[String(reason || "")] || "استثناء مسجل";
}
function endedAuctionCard(i) {
  let sold = endedAuctionSuccessful(i),
    exception = endedAuctionException(i),
    cancelled = endedAuctionCancelled(i),
    reached = endedReserveReached(i);
  let stateText = sold ? "✓ مزاد ناجح" : exception ? "⚠ استثناء مسجل" : cancelled ? "⛔ ملغي من الإدارة" : "انتهى دون بيع";
  let stateClass = sold ? "sold" : exception ? "exception" : cancelled ? "cancelled" : "ended";
  let chipText = sold ? "🏆 ناجح — مغلق" : exception ? "⚠ قابل لإعادة الإدراج" : cancelled ? "⛔ ملغي من الإدارة" : reached ? "بلغ حد البيع دون إرساء" : "دون حد البيع";
  let exceptionNote = exception ? `<p class="auction-exception-note"><b>الاستثناء:</b> ${esc(auctionExceptionLabel(i.auctionExceptionReason))}${i.auctionExceptionNote ? ` — ${esc(i.auctionExceptionNote)}` : ""}${i.auctionExceptionAt ? `<br><small>${new Date(i.auctionExceptionAt).toLocaleString("ar-SA")}</small>` : ""}</p>` : "";
  let cancelNote = cancelled ? `<p class="auction-exception-note"><b>سبب الإلغاء:</b> ${esc(i.auctionCancelReason || "إلغاء إداري")}${i.auctionCancelledAt ? `<br><small>${new Date(i.auctionCancelledAt).toLocaleString("ar-SA")}</small>` : ""}</p>` : "";
  let actions = sold
    ? `<button onclick="detail('${i.id}')">عرض السجل</button><button class="danger-outline" onclick="openAuctionException('${i.id}')">استثناء</button>`
    : cancelled ? `<button onclick="detail('${i.id}')">عرض السجل</button>`
    : `<button onclick="detail('${i.id}')">عرض السجل</button><button class="ghost" onclick="editItem('${i.id}')">✎ تعديل المقتنى</button>${archiveButton(i.id)}<button class="gold-action" onclick="openRelaunch('${i.id}')">♻ إعادة إدراج</button>`;
  return `<article class="item auction-item ended-admin-card ${sold ? "sold-ended successful-locked" : exception ? "exception-ended" : ""}">${i.frontImg ? `<div class="auction-card-image"><img src="${i.frontImg}" onclick="detail('${i.id}')"><span class="auction-state ${stateClass}">${stateText}</span></div>` : '<div class="auction-card-image no-photo">لا توجد صورة</div>'}<div class="auction-card-body"><div class="auction-card-title"><h3>${esc(i.country)} — ${esc(i.denomination)} ${transitionalBadge(i)}</h3><span class="approval-chip ${sold ? "ok" : exception ? "warning" : "pending"}">${chipText}</span></div><p class="ended-date">انتهى: ${esc(i.auctionEnd || "—")}</p><div class="auction-admin-metrics"><div><span>آخر سعر</span><b>${money(i.auctionCurrentPrice || 0)}</b></div><div><span>سعر الفتح السابق</span><b>${money(i.auctionOpeningPrice || i.auctionStartPrice || 0)}</b></div><div><span>الزيادة السابقة</span><b>${money(i.auctionBidStep || 1)}</b></div><div class="private-metric"><span>حد البيع السابق</span><b>${money(i.auctionTargetPrice || Number(i.auctionStartPrice || 0) + 1)}</b></div></div>${sold ? '<p class="sold-order-note">🔒 مزاد ناجح نهائي — لا عودة للمستودع ولا إعادة مزايدة. الاستثناء فقط للحالات الموثقة قبل اكتمال البيع.</p>' : ""}${exceptionNote}${cancelNote}<p class="round-chip">الجولة المنتهية ${Number(i.auctionRound || 1)}</p><div class="actions auction-actions">${actions}</div></div></article>`;
}
async function renderEndedAuctions(a) {
  a = a || (await all());
  let q = (
      document.getElementById("endedAuctionSearch")?.value || ""
    ).toLowerCase(),
    f = document.getElementById("endedAuctionFilter")?.value || "all";
  let ended = a.filter(
    (i) => (i.forAuction && auctionText(i.auctionEnd) === "انتهى المزاد") || endedAuctionCancelled(i),
  );
  let successful = ended.filter(endedAuctionSuccessful),
    exceptions = ended.filter(endedAuctionException),
    unsuccessful = ended.filter((i) => !endedAuctionSuccessful(i) && !endedAuctionException(i));
  if ($("endedPageCount")) $("endedPageCount").textContent = ended.length;
  if ($("endedReachedTarget")) $("endedReachedTarget").textContent = successful.length;
  if ($("endedBelowTarget")) $("endedBelowTarget").textContent = unsuccessful.length;
  if ($("endedExceptionCount")) $("endedExceptionCount").textContent = exceptions.length;
  if ($("endedAuctionsBadge")) {
    $("endedAuctionsBadge").textContent = ended.length;
    $("endedAuctionsBadge").hidden = !ended.length;
  }
  let rows = ended.filter(
    (i) =>
      (f === "all" ||
        (f === "successful" && endedAuctionSuccessful(i)) ||
        (f === "unsuccessful" && !endedAuctionSuccessful(i) && !endedAuctionException(i)) ||
        (f === "exceptions" && endedAuctionException(i))) &&
      (!q || JSON.stringify(i).toLowerCase().includes(q)),
  );
  rows.sort((a, b) =>
    String(b.auctionEnd || "").localeCompare(String(a.auctionEnd || "")),
  );
  if ($("endedAuctionItems"))
    $("endedAuctionItems").innerHTML =
      rows.map(endedAuctionCard).join("") ||
      '<p class="empty-ended">لا توجد مزادات منتهية مطابقة.</p>';
}
function renderAuctions(a) {
  let z = a.filter((i) => i.forAuction),
    active = z.filter((i) => auctionText(i.auctionEnd) !== "انتهى المزاد"),
    ended = z.filter((i) => auctionText(i.auctionEnd) === "انتهى المزاد");
  $("auctionActiveCount").textContent = active.length;
  $("auctionEndedCount").textContent = ended.length;
  $("auctionApprovedCount").textContent = z.filter(
    (i) => i.auctionApproved,
  ).length;
  $("auctionItems").innerHTML =
    [...active, ...ended].map(auctionCard).join("") ||
    "<p>لا توجد عملات مخصصة للمزاد.</p>";
}
function card(i) {
  let remain = Math.max(
    0,
    (Number(i.quantity) || 0) - (Number(i.soldQuantity) || 0),
  );
  let auctionState = i.forAuction
    ? auctionText(i.auctionEnd) === "انتهى المزاد"
      ? endedReserveReached(i)
        ? "تم البيع / فائز"
        : "انتهى دون بيع"
      : i.auctionApproved
        ? "نشط"
        : "غير نشط"
    : "غير مخصص";
  let marketState = i.forMarket
    ? i.marketApproved
      ? "نشط"
      : "غير نشط"
    : "غير مخصص";
  const recordImages = [
    [i.frontImg, "الوجه الأمامي"],
    [i.backImg, "الوجه الخلفي"],
  ].filter(([src]) => src);
  const photo = recordImages.length
    ? `<div class="record-card-images">${recordImages.map(([src, label]) => `<figure><img src="${esc(src)}" alt="${esc(label)}" loading="lazy"><figcaption>${label}</figcaption></figure>`).join("")}</div>`
    : '<div class="record-no-photo" aria-label="لا توجد صورة"><span>🖼️</span><b>لا توجد صورة</b></div>';
  return `<article class="item record-card">${photo}<div class="record-card-body"><h3>${esc(i.country)} — ${esc(i.denomination)} ${transitionalBadge(i)}</h3><div class="record-strips record-strips-v403"><div><span>الفئة</span><b>${esc(i.denomination || "—")}</b></div><div><span>حالة الحفظ</span><b>${esc(i.condition || "—")}</b></div><div class="quantity-stack"><span>الكميات</span><b><em>الكمية الأصلية</em><strong>${Number(i.quantity || 0)}</strong></b><b><em>المباعة</em><strong>${Number(i.soldQuantity || 0)}</strong></b><b><em>المتبقية</em><strong>${remain}</strong></b></div><div class="display-status"><span>حالة العرض</span><b><em>السوق العام</em><strong class="state ${marketState === "نشط" ? "on" : marketState === "غير نشط" ? "off" : "neutral"}">${marketState}</strong></b><b><em>المزاد</em><strong class="state ${auctionState === "نشط" || auctionState.includes("فائز") ? "on" : auctionState === "غير نشط" || auctionState.includes("دون بيع") ? "off" : "neutral"}">${auctionState}</strong></b></div><div><span>موقع التخزين</span><b>${esc(loc(i))}</b></div></div><div class="actions record-actions"><button onclick="detail('${i.id}')">عرض</button><button class="ghost" onclick="editItem('${i.id}')">تعديل</button><button class="danger" onclick="removeItem('${i.id}')">حذف</button></div></div></article>`;
}
let refreshBusy = false,
  lastDataToken = "";
function dataToken(a) {
  return a
    .map((i) =>
      [
        i.id,
        i.updated,
        i.quantity,
        i.inventoryUnitType,
        i.inventoryUnitCount,
        i.piecesPerUnit,
        i.soldQuantity,
        i.damagedQuantity,
        (i.serials || []).join(","),
        i.forAuction,
        i.auctionEnd,
        i.auctionQuantity,
        i.forMarket,
        i.marketApproved,
        i.marketSalePrice,
        i.marketUnitPrice,
        i.marketQuantity,
        i.ownerName,
        i.ownerPhone,
        i.ownerCountry,
        i.purchase,
        i.shipping,
        i.other,
        i.expectedPrice,
        i.fantasiaEnabled,
        i.fantasiaType,
        i.fantasiaIssuer,
        i.fantasiaNotes,
        i.specialNumberEnabled,
        (i.specialNumberTypes || []).join(","),
        i.transitionalIssueEnabled,
        i.transitionalIssueType,
      ].join(":"),
    )
    .sort()
    .join("|");
}
async function refresh(force = false) {
  if (refreshBusy) return;
  refreshBusy = true;
  try {
    let a = await all();
    latestItems = a.slice();
    updateStorageCatalogFromItems(a);
    if (document.getElementById("add")?.classList.contains("active")) renderStorageSelectors();
    let token = dataToken(a);
    if (!force && token === lastDataToken) return;
    lastDataToken = token;
    a.sort((x, y) => (Number(y.updated) || 0) - (Number(x.updated) || 0));
    $("records").textContent = a.length;
    $("qty").textContent = a.reduce((s, i) => s + (Number(i.quantity) || 0), 0);
    $("soldQty").textContent = a.reduce(
      (s, i) =>
        s + Math.min(Number(i.quantity) || 0, Number(i.soldQuantity) || 0),
      0,
    );
    $("remainingQty").textContent = a.reduce(
      (s, i) =>
        s +
        Math.max(0, (Number(i.quantity) || 0) - (Number(i.soldQuantity) || 0)),
      0,
    );
    $("capital").textContent = money(
      a.reduce(
        (s, i) =>
          s +
          ((Number(i.purchase) || 0) +
            (Number(i.shipping) || 0) +
            (Number(i.other) || 0)) *
            (Number(i.quantity) || 0),
        0,
      ),
    );
    $("expected").textContent = money(
      a.reduce(
        (s, i) =>
          s + (Number(i.expectedPrice) || 0) * (Number(i.quantity) || 0),
        0,
      ),
    );
    let az = a.filter((i) => i.forAuction);
    $("activeAuctions").textContent = az.filter(
      (i) => auctionText(i.auctionEnd) !== "انتهى المزاد",
    ).length;
    $("endedAuctions").textContent = az.filter(
      (i) => auctionText(i.auctionEnd) === "انتهى المزاد",
    ).length;
    renderAuctions(a);
    renderEndedAuctions(a);
    loadAdminBids();
    renderMarketAdmin(a);
    if (document.getElementById("finance")?.classList.contains("active"))
      renderFinance();
    $("recent").innerHTML =
      a.slice(0, 12).map(card).join("") || "<p>لا توجد بيانات.</p>";
    renderList(a);
    if (document.getElementById("warehouseView")?.classList.contains("active"))
      await renderWarehouse();
    if (document.getElementById("special")?.classList.contains("active"))
      await renderSpecialAdmin(a);
    if (document.getElementById("transitional")?.classList.contains("active"))
      await renderTransitionalAdmin(a);
    if (document.getElementById("fantasia")?.classList.contains("active"))
      await renderFantasiaAdmin(a);
  } catch (e) {
    console.warn("تعذر تحديث البيانات المشتركة", e);
  } finally {
    refreshBusy = false;
  }
}
let recordFilter = "all",
  recordSetFilter = "all",
  marketFilter = "all",
  marketSetFilter = "all";
function isSet(i) {
  // هوية المقتنى مستقلة عن مكان/طريقة عرضه.
  // لا يجوز أن يتحول المقتنى إلى "طقم" لمجرد اختيار عرض السوق كطقم.
  return (
    i.inventoryClassification === "set" ||
    i.collectionClass === "set" ||
    i.isSet === true
  );
}
function effectiveGradingStatus(i) {
  if (String(i.gradingStatus || "").toLowerCase() === "graded") return "graded";
  if (String(i.gradingStatus || "").toLowerCase() === "ungraded") return "ungraded";
  return i.isGraded === true ? "graded" : "ungraded";
}
function setSizeClass(i) {
  let p = Number(i.marketSetPieces || i.setPieces || i.quantity || 0);
  return p <= 3 ? "mini" : p <= 5 ? "small" : p <= 10 ? "medium" : "large";
}
function effectiveClassification(i) {
  // التصنيف البنيوي (طقم/مفرد) منفصل عن حالة التقييم ومكان العرض.
  if (isSet(i)) return "set";
  return effectiveGradingStatus(i);
}
function classMatch(i, f, sf) {
  let classification = effectiveClassification(i);
  if (f === "graded" && classification !== "graded") return false;
  if (f === "ungraded" && classification !== "ungraded") return false;
  if (f === "sets" && classification !== "set") return false;
  if (f === "sets" && sf !== "all" && setSizeClass(i) !== sf) return false;
  return true;
}
function renderList(a) {
  let q = v("search").toLowerCase();
  if ($("rfAll")) $("rfAll").textContent = a.length;
  if ($("rfGraded"))
    $("rfGraded").textContent = a.filter((i) => i.isGraded && !isSet(i)).length;
  if ($("rfUngraded"))
    $("rfUngraded").textContent = a.filter(
      (i) => !i.isGraded && !isSet(i),
    ).length;
  if ($("rfSets")) $("rfSets").textContent = a.filter(isSet).length;
  $("items").innerHTML =
    a
      .filter((i) => classMatch(i, recordFilter, recordSetFilter))
      .filter((i) => !q || JSON.stringify(i).toLowerCase().includes(q))
      .map(card)
      .join("") || "<p>لا توجد نتيجة في هذا التصنيف.</p>";
}
let inventoryFilter = "warehouse",
  lastInventoryRows = [],
  warehouseCountryFilter = "";

// Warehouse smart browse/search — generated only from actual warehouse stock.
function normalizeWarehouseText(value) {
  return String(value ?? "")
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u064b-\u065f\u0670]/g, "")
    .replace(/[إأآٱ]/g, "ا")
    .replace(/ى/g, "ي")
    .replace(/ؤ/g, "و")
    .replace(/ئ/g, "ي")
    .replace(/ة/g, "ه")
    .replace(/[٠-٩]/g, (d) => "0123456789"["٠١٢٣٤٥٦٧٨٩".indexOf(d)])
    .replace(/[۰-۹]/g, (d) => "0123456789"["۰۱۲۳۴۵۶۷۸۹".indexOf(d)])
    .replace(/[،,:;؛|/\\()\[\]{}_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}
function warehouseFieldText(values) {
  return normalizeWarehouseText((Array.isArray(values) ? values : [values]).filter((v) => v !== null && v !== undefined && v !== "").join(" "));
}
function warehouseSearchFields(x) {
  const original = x._source || {};
  const sourceForClass = Object.keys(original).length ? original : x;
  const classification = effectiveClassification(sourceForClass);
  const grading = effectiveGradingStatus(sourceForClass);
  const serials = Array.isArray(original.serials) ? original.serials : [];
  const classAliases = classification === "set"
    ? "طقم اطقم مجموعه مجموعة set sets"
    : grading === "graded"
      ? "مقيم مقيمه مقيمة تقييم معتمد graded"
      : "غير مقيم غير مقيمه غير مقيمة بدون تقييم غير معتمد ungraded";
  return {
    country: warehouseFieldText([x.country, original.country]),
    denomination: warehouseFieldText([x.denomination, original.denomination]),
    year: warehouseFieldText([x.year, original.year]),
    classification: warehouseFieldText(classAliases),
    issue: warehouseFieldText([original.issueEdition, original.issue, original.type]),
    condition: warehouseFieldText([original.condition]),
    gradingCompany: warehouseFieldText([original.gradingCompany]),
    grade: warehouseFieldText([original.gradeValue, original.gradePercent, original.gradingVerificationStatus]),
    certificate: warehouseFieldText([original.gradingCertNumber]),
    serial: warehouseFieldText([original.serial, ...serials]),
    id: warehouseFieldText([x.itemId, original.id]),
    location: warehouseFieldText([
      warehouseLocationText(x.location || {}),
      original.warehouse, original.cabinet, original.shelf, original.box, original.album, original.pocket
    ]),
    notes: warehouseFieldText([original.gradingNotes, original.notes])
  };
}
function warehouseSearchText(x) {
  return Object.values(warehouseSearchFields(x)).join(" ");
}
function warehouseQueryParts(query) {
  const filters = {};
  const fieldMap = {
    "الدوله":"country", "بلد":"country",
    "الفئه":"denomination", "العمله":"denomination",
    "السنه":"year", "الاصدار":"issue",
    "التقييم":"grade", "درجه":"grade",
    "الشركه":"gradingCompany", "جهه":"gradingCompany",
    "الشهاده":"certificate",
    "الرقم":"serial", "التسلسلي":"serial",
    "الموقع":"location", "التخزين":"location", "الحاله":"condition"
  };
  let freeRaw = String(query ?? "").replace(/([^\s:：]+)\s*[:：]\s*("[^"]+"|'[^']+'|[^\s]+)/g, (whole, key, value) => {
    const mapped = fieldMap[normalizeWarehouseText(key)];
    if (!mapped) return whole;
    filters[mapped] = normalizeWarehouseText(String(value).replace(/^['"]|['"]$/g, ""));
    return " ";
  });
  let q = normalizeWarehouseText(freeRaw);
  const aliases = [
    { re: /(^| )غير مقيم(?:ه)?(?= |$)/g, key: "classification", value: "ungraded" },
    { re: /(^| )بدون تقييم(?= |$)/g, key: "classification", value: "ungraded" },
    { re: /(^| )مقيم(?:ه)?(?= |$)/g, key: "classification", value: "graded" },
    { re: /(^| )طقم(?= |$)/g, key: "classification", value: "set" },
    { re: /(^| )اطقم(?= |$)/g, key: "classification", value: "set" }
  ];
  aliases.forEach(({re,key,value}) => {
    if (re.test(q)) {
      filters[key] = value;
      q = q.replace(re, " ");
    }
    re.lastIndex = 0;
  });
  const terms = q.split(" ").map((v) => v.trim()).filter(Boolean);
  return { terms, filters };
}
function warehouseSmartMatch(x, query) {
  if (!String(query || "").trim()) return true;
  const { terms, filters } = warehouseQueryParts(query);
  const fields = warehouseSearchFields(x);
  const original = x._source || {};
  const sourceForClass = Object.keys(original).length ? original : x;
  const classification = effectiveClassification(sourceForClass);
  const grading = effectiveGradingStatus(sourceForClass);

  if (filters.classification === "set" && classification !== "set") return false;
  if (filters.classification === "graded" && (classification === "set" || grading !== "graded")) return false;
  if (filters.classification === "ungraded" && (classification === "set" || grading !== "ungraded")) return false;

  for (const [key, value] of Object.entries(filters)) {
    if (key === "classification" || !value) continue;
    const field = fields[key] || "";
    if (!field.includes(value)) return false;
  }

  const allText = Object.values(fields).join(" ");
  // Every free word must match somewhere. This makes multi-word searches precise instead of broad OR matching.
  return terms.every((term) => allText.includes(term));
}
function ensureWarehouseCountryUI() {
  const search = $("warehouseSearch");
  if (search) search.placeholder = "بحث ذكي: السعودية 50 ريال | PMG 66 | طقم | غير مقيم | الدولة:قطر | الرقم:1234";
  if ($("warehouseCountries")) return;
  const controls = document.querySelector("#warehouse .warehouse-controls");
  if (!controls) return;
  const box = document.createElement("div");
  box.id = "warehouseCountries";
  box.setAttribute("aria-label", "الدول الموجودة فعليًا في المستودع");
  box.style.cssText = "display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:4px 0 15px;padding:10px 12px;border:1px solid #e2d3aa;border-radius:14px;background:#fffaf0";
  controls.insertAdjacentElement("afterend", box);
}
function renderWarehouseCountries() {
  ensureWarehouseCountryUI();
  const box = $("warehouseCountries");
  if (!box) return;
  const counts = new Map();
  lastInventoryRows.forEach((x) => {
    if (Number(x.warehouse || 0) <= 0) return;
    const country = String(x.country || "غير محدد").trim() || "غير محدد";
    counts.set(country, (counts.get(country) || 0) + Number(x.warehouse || 0));
  });
  const countries = [...counts.entries()].sort((a,b) => a[0].localeCompare(b[0], "ar"));
  const activeStyle = "background:#102659;color:#fff;border-color:#c99848";
  const normalStyle = "background:#fff;color:#102659;border-color:#d9dfeb";
  box.innerHTML = `<b style="color:#102659;margin-inline-end:4px">الدول الموجودة في المستودع:</b>` +
    `<button type="button" data-warehouse-country="" style="border:1px solid;border-radius:999px;padding:7px 12px;font-weight:800;cursor:pointer;${warehouseCountryFilter ? normalStyle : activeStyle}">الكل</button>` +
    countries.map(([country,count]) => `<button type="button" data-warehouse-country="${esc(country)}" style="border:1px solid;border-radius:999px;padding:7px 12px;font-weight:800;cursor:pointer;${warehouseCountryFilter === country ? activeStyle : normalStyle}">${esc(country)} <span style="opacity:.8">(${Number(count).toLocaleString("ar-SA")})</span></button>`).join("");
  box.querySelectorAll("[data-warehouse-country]").forEach((button) => button.addEventListener("click", () => {
    warehouseCountryFilter = button.dataset.warehouseCountry || "";
    inventoryFilter = "warehouse";
    document.querySelectorAll(".warehouse-metric").forEach((x) => x.classList.toggle("active", x.dataset.inventoryFilter === "warehouse"));
    renderWarehouseCountries();
    renderWarehouseRows();
  }));
}
function warehouseLocationText(location = {}) {
  return [
    ["مستودع", location.warehouse], ["خزانة", location.cabinet],
    ["رف", location.shelf], ["صندوق", location.box],
    ["ألبوم", location.album], ["صفحة/جيب", location.pocket],
  ].filter((x) => x[1]).map((x) => x.join(" ")).join(" ← ") || "غير محدد";
}
function renderWarehouseRows() {
  let q = String($("warehouseSearch")?.value || "").trim().toLowerCase(),
    rows = lastInventoryRows
      .filter((x) => inventoryFilter === "all" ? x.adminLocation === "warehouse" : Number(x[inventoryFilter] || 0) > 0)
      .filter((x) => !warehouseCountryFilter || String(x.country || "") === warehouseCountryFilter)
      .filter((x) => warehouseSmartMatch(x, q));
  $("warehouseItems").innerHTML = rows.map((x) => {
    let location = warehouseLocationText(x.location || {});
    const warehouseImages = [
      [x.frontImg, "الوجه"],
      [x.backImg, "الخلف"],
    ].filter(([src]) => src);
    const photo = warehouseImages.length
      ? `<div class="warehouse-thumb-pair">${warehouseImages.map(([src, label]) => `<figure><img src="${esc(src)}" alt="${esc(label)}" loading="lazy"><figcaption>${label}</figcaption></figure>`).join("")}</div>`
      : '<div class="warehouse-no-photo">لا توجد صورة</div>';
    let returnActions = Number(x.returned || 0) > 0 ? `<button onclick="resolveInventoryReturn('${x.itemId}','warehouse')">↩ إعادة للمستودع</button><button class="danger" onclick="resolveInventoryReturn('${x.itemId}','damaged')">تسجيل تالف</button>` : "";
    let classification = ({graded:"مُقيَّم",ungraded:"غير مُقيَّم",set:"طقم"})[effectiveClassification(x)] || "غير مُقيَّم";
    return `<article class="warehouse-item">${photo}<div class="warehouse-item-main"><div class="warehouse-item-title"><h3>${esc(x.country)} — ${esc(x.denomination)} ${transitionalBadge(x._source||x)}</h3><span>${esc(x.year || "بدون سنة")}</span></div><div class="warehouse-item-quantities"><span>التصنيف <b>${classification}</b></span><span>الإجمالي <b>${x.total}</b></span><span>المتاح <b>${x.warehouse}</b></span><span>السوق <b>${x.market}</b></span><span>المزاد <b>${x.auction}</b></span><span>المحجوز <b>${x.reserved}</b></span><span>المرتجع <b>${x.returned}</b></span><span>المباع <b>${x.sold}</b></span></div><p class="storage-path">${esc(location)}</p><small>${x.unitCount} ${esc(inventoryUnitLabel(x.unitType))} × ${x.piecesPerUnit} ورقة/قطعة${x.sourceSubmissionId ? " — محوّل من طلب اعتماد" : ""}</small></div><div class="actions"><button onclick="detail('${x.itemId}')">عرض</button><button class="ghost" onclick="editItem('${x.itemId}')">تعديل</button>${archiveButton(x.itemId)}${adminMoveButtons({id:x.itemId},"warehouse")}${returnActions}</div></article>`;
  }).join("") || '<p class="muted">لا توجد مقتنيات في هذا المؤشر.</p>';
}
async function renderWarehouse() {
  try {
    let data = await api("/api/inventory/summary"), totals = data.totals || {};
    const sourceItems = await all();
    const sourceById = new Map(sourceItems.map((item) => [String(item.id || ""), item]));
    lastInventoryRows = (data.items || []).map((row) => {
      const source = sourceById.get(String(row.itemId || "")) || {};
      return { ...row, adminLocation: adminItemLocation(source), _source: source };
    });
    renderWarehouseCountries();
    let ids = { total: "invTotal", current: "invCurrent", warehouse: "invWarehouse", market: "invMarket", auction: "invAuction", special: "invSpecial", reserved: "invReserved", sold: "invSold", returned: "invReturned", damaged: "invDamaged" };
    Object.entries(ids).forEach(([key, id]) => { if ($(id)) $(id).textContent = Number(totals[key] || 0).toLocaleString("ar-SA"); });
    if ($("warehouseEquation")) $("warehouseEquation").textContent = `الرصيد الحالي ${Number(totals.current || 0).toLocaleString("ar-SA")} = المستودع ${Number(totals.warehouse || 0).toLocaleString("ar-SA")} + السوق ${Number(totals.market || 0).toLocaleString("ar-SA")} + المزاد ${Number(totals.auction || 0).toLocaleString("ar-SA")} + المحجوز ${Number(totals.reserved || 0).toLocaleString("ar-SA")} + المرتجع للفحص ${Number(totals.returned || 0).toLocaleString("ar-SA")}`;
    renderWarehouseRows();
  } catch (e) {
    $("warehouseItems").innerHTML = `<p class="analysis-warn">تعذر تحميل المستودع: ${esc(e.message)}</p>`;
  }
}
document.querySelectorAll(".warehouse-metric").forEach((b) => b.addEventListener("click", () => {
  inventoryFilter = b.dataset.inventoryFilter || "all";
  if (inventoryFilter !== "warehouse") warehouseCountryFilter = "";
  document.querySelectorAll(".warehouse-metric").forEach((x) => x.classList.toggle("active", x === b));
  renderWarehouseCountries();
  renderWarehouseRows();
}));
if ($("warehouseSearch")) $("warehouseSearch").oninput = renderWarehouseRows;
if ($("refreshWarehouse")) $("refreshWarehouse").onclick = async () => {
  const b=$("refreshWarehouse"), old=b.textContent;
  try{ b.disabled=true; b.textContent="جارٍ التحديث..."; await refresh(true); await renderWarehouse(); toast("تم تحديث مؤشرات المستودع."); }
  catch(e){ alert("تعذر تحديث مؤشرات المستودع: "+e.message); }
  finally{ b.disabled=false; b.textContent=old; }
};
if ($("repairWarehouseSubmissions")) $("repairWarehouseSubmissions").onclick = async () => {
  if (!confirm("فحص المقتنيات المعتمدة سابقًا وإصلاح ربطها بالمستودع؟ لن يتم نشر أي مقتنى في السوق أو المزاد.")) return;
  try {
    let result = await api("/api/inventory/repair-approved-submissions", { method: "POST", body: "{}" });
    await refresh(true); await renderWarehouse(); await renderCollectibleApprovals();
    toast(`اكتمل الفحص: أُصلح ${Number(result.repaired || 0)}، وأُعيد إنشاء ${Number(result.created || 0)}.`);
  } catch (e) { alert(e.message); }
};
window.resolveInventoryReturn = async (itemId, action) => {
  let label = action === "warehouse" ? "إعادة المرتجع إلى المستودع وإيقاف عرضه الحالي؟" : "تسجيل الكمية المرتجعة كتالف/مفقود؟";
  if (!confirm(label)) return;
  try {
    await api("/api/inventory/return-resolution", { method: "POST", body: JSON.stringify({ itemId, action }) });
    await refresh(true); await renderWarehouse(); toast(action === "warehouse" ? "تمت إعادة المرتجع إلى المستودع." : "تم تسجيل المرتجع كتالف.");
  } catch (e) { alert("تعذر معالجة المرتجع: " + e.message); }
};

const TRANSITIONAL_TYPE_LABELS = {
  "signature-change": "انتقال توقيع",
  "last-before-change": "آخر إصدار قبل تغيير",
  "first-after-change": "أول إصدار بعد تغيير",
  "design-change": "انتقال تصميم / مواصفات",
  "authority-change": "انتقال جهة / سلطة إصدار",
  other: "حالة انتقالية أخرى",
};
const TRANSITIONAL_RARITY_LABELS = {
  documented: "موثق / معروف",
  scarce: "قليل الظهور",
  rare: "نادر",
  "very-rare": "نادر جدًا",
};
function transitionalBadge(i) {
  return i?.transitionalIssueEnabled ? '<span class="transitional-badge">⇄ إصدار انتقالي</span>' : '';
}
function renderTransitionalAdminCard(i) {
  const imgs=[i.frontImg,i.backImg].filter(Boolean);
  const type=TRANSITIONAL_TYPE_LABELS[i.transitionalIssueType] || "إصدار انتقالي";
  const rarity=TRANSITIONAL_RARITY_LABELS[i.transitionalRarity] || "—";
  const title=`${i.country || "—"} — ${i.denomination || "—"}`;
  return `<article class="transitional-admin-card">
    <div class="transitional-admin-images">${imgs.length?imgs.map((src,idx)=>`<img src="${esc(src)}" alt="${idx?'الخلف':'الوجه'}" loading="lazy" onclick='openCoinLightbox(${JSON.stringify(imgs)},${idx},${JSON.stringify(title)})'>`).join(''):'<div class="special-no-photo">لا توجد صورة</div>'}</div>
    <div class="transitional-admin-body"><div class="transitional-title-row"><h3>${esc(title)}</h3>${transitionalBadge(i)}</div>
      <div class="transitional-type-chip">${esc(type)}</div>
      <div class="transitional-data"><span>السنة<b>${esc(i.year||"—")}</b></span><span>الندرة<b>${esc(rarity)}</b></span><span>الإصدار السابق<b>${esc(i.transitionalPreviousIssue||"—")}</b></span><span>الإصدار اللاحق<b>${esc(i.transitionalNextIssue||"—")}</b></span><span>التوفر التقديري<b>${esc(i.transitionalEstimatedPopulation||"—")}</b></span><span>القيمة المرجعية<b>${Number(i.transitionalReferenceValue||0)>0?money(i.transitionalReferenceValue):"—"}</b></span></div>
      <p class="special-reason"><b>سبب التصنيف:</b> ${esc(i.transitionalReason||"—")}</p>${i.transitionalNotes?`<p class="special-reason"><b>ملاحظات:</b> ${esc(i.transitionalNotes)}</p>`:""}
    </div>
    <div class="actions special-admin-actions"><button onclick="detail('${esc(i.id)}')">عرض</button><button class="ghost" onclick="editItem('${esc(i.id)}')">✎ تعديل</button>${archiveButton(i.id)}${adminMoveButtons(i,adminItemLocation(i))}</div>
  </article>`;
}
async function renderTransitionalAdmin(){
  const rows=(await all()).filter(i=>i.transitionalIssueEnabled);
  const q=String($("transitionalSearch")?.value||"").trim().toLowerCase();
  const t=$("transitionalTypeFilter")?.value||"all";
  const filtered=rows.filter(i=>(t==="all"||i.transitionalIssueType===t)&&(!q||JSON.stringify([i.country,i.denomination,i.year,i.transitionalIssueType,TRANSITIONAL_TYPE_LABELS[i.transitionalIssueType],i.transitionalReason,i.transitionalPreviousIssue,i.transitionalNextIssue,i.transitionalNotes]).toLowerCase().includes(q)));
  if ($("transitionalAdminItems")) $("transitionalAdminItems").innerHTML=filtered.map(renderTransitionalAdminCard).join("")||'<div class="special-empty">لا توجد إصدارات انتقالية مطابقة حاليًا.</div>';
}
window.renderTransitionalAdmin=renderTransitionalAdmin;
const SPECIAL_TYPE_LABELS = {
  repeated: "أرقام متكررة",
  sequential: "أرقام متسلسلة",
  matching: "أرقام متطابقة",
  radar: "أرقام متناظرة / رادار",
  ascending: "أرقام تصاعدية",
  descending: "أرقام تنازلية",
  rare: "أرقام نادرة / مميزة",
  errors: "عملات بأخطاء نادرة",
};
let specialAdminFilter = "all", specialAdminRows = [];
function specialTypesOf(i) {
  let a = Array.isArray(i.specialNumberTypes) ? i.specialNumberTypes : [i.specialNumberType].filter(Boolean);
  return [...new Set(a.filter(Boolean))];
}
function specialIsForSale(i) {
  let price = Number(i.marketSalePrice || i.marketUnitPrice || 0);
  return !!(i.forMarket && i.marketApproved && price > 0);
}
function specialAdminCard(i) {
  let types = specialTypesOf(i), serials = Array.isArray(i.serials) ? i.serials.filter(Boolean) : [], price = Number(i.marketSalePrice || i.marketUnitPrice || 0);
  let sale = specialIsForSale(i), imgs = [i.frontImg, i.backImg].filter(Boolean);
  let tags = types.map(t => `<span class="special-tag ${t === "errors" ? "error" : ""}">${esc(SPECIAL_TYPE_LABELS[t] || t)}</span>`).join("");
  return `<article class="special-admin-card">
    <div class="special-admin-images">${imgs.length ? imgs.map((src,idx)=>`<img src="${esc(src)}" alt="${idx?"الخلف":"الوجه"}" loading="lazy" onclick="openCoinLightbox(${JSON.stringify(imgs).replace(/"/g,'&quot;')},${idx},'صور المميزة والنادرة')">`).join("") : '<div class="special-no-photo">لا توجد صورة</div>'}</div>
    <div class="special-admin-main">
      <div class="special-admin-title"><div><h3>${esc(i.country || "—")} — ${esc(i.denomination || "—")}</h3><small>${esc(i.year || "بدون سنة")} • رقم السجل ${esc(i.id || "")}</small></div><span class="approval-chip ${sale ? "ok" : "pending"}">${sale ? "للبيع" : "عرض فقط"}</span></div>
      <div class="special-tags">${tags || '<span class="special-tag">غير محدد</span>'}</div>
      <p class="special-reason">${esc(i.specialNumberReason || "لا يوجد وصف لسبب التميز بعد.")}</p>
      <div class="special-admin-data"><span>السعر <b>${price > 0 ? money(price) : "غير محدد"}</b></span><span>الكمية <b>${Number(i.marketQuantity || i.quantity || 0)}</b></span><span>الأرقام <b>${serials.length}</b></span><span>الموقع <b>${esc(loc(i))}</b></span></div>
      ${serials.length ? `<details class="special-serials"><summary>عرض الأرقام التسلسلية (${serials.length})</summary><div>${serials.slice(0,200).map(x=>`<span dir="ltr">${esc(x)}</span>`).join("")}${serials.length>200?`<em>+ ${serials.length-200} رقم إضافي</em>`:""}</div></details>` : ""}
    </div>
    <div class="actions special-admin-actions"><button onclick="detail('${esc(i.id)}')">عرض</button><button class="ghost" onclick="editItem('${esc(i.id)}')">✎ تعديل التصنيف والسعر</button>${archiveButton(i.id)}${adminMoveButtons(i,"special")}<a class="public-link" href="/special-numbers#item-${encodeURIComponent(i.id)}" target="_blank">معاينة للعميل</a><button class="danger" onclick="disableSpecialItem('${esc(i.id)}')">إيقاف من الصفحة</button></div>
  </article>`;
}
function renderSpecialAdminRows() {
  if (!$("specialAdminItems")) return;
  let q = String($("specialSearch")?.value || "").trim().toLowerCase(), tf = $("specialTypeFilter")?.value || "all";
  let rows = specialAdminRows.filter(i => isSpecialItem(i)).filter(i => {
    if (specialAdminFilter === "sale" && !specialIsForSale(i)) return false;
    if (specialAdminFilter === "display" && specialIsForSale(i)) return false;
    if (specialAdminFilter === "errors" && !specialTypesOf(i).includes("errors")) return false;
    if (specialAdminFilter === "serial" && specialTypesOf(i).includes("errors") && specialTypesOf(i).length === 1) return false;
    if (tf !== "all" && !specialTypesOf(i).includes(tf)) return false;
    return !q || JSON.stringify(i).toLowerCase().includes(q);
  });
  $("specialAdminItems").innerHTML = rows.map(specialAdminCard).join("") || '<p class="muted special-empty">لا توجد مقتنيات مطابقة لهذا الفلتر.</p>';
}
async function renderSpecialAdmin(items = null) {
  try {
    specialAdminRows = Array.isArray(items) ? items : await all();
    let rows = specialAdminRows.filter(i => isSpecialItem(i)), errors = rows.filter(i => specialTypesOf(i).includes("errors"));
    if ($("specialTotal")) $("specialTotal").textContent = rows.length.toLocaleString("ar-SA");
    if ($("specialForSale")) $("specialForSale").textContent = rows.filter(specialIsForSale).length.toLocaleString("ar-SA");
    if ($("specialDisplayOnly")) $("specialDisplayOnly").textContent = rows.filter(i => !specialIsForSale(i)).length.toLocaleString("ar-SA");
    if ($("specialErrors")) $("specialErrors").textContent = errors.length.toLocaleString("ar-SA");
    if ($("specialSerials")) $("specialSerials").textContent = rows.filter(i => specialTypesOf(i).some(t => t !== "errors")).length.toLocaleString("ar-SA");
    renderSpecialAdminRows();
  } catch (e) {
    if ($("specialAdminItems")) $("specialAdminItems").innerHTML = `<p class="analysis-warn">تعذر تحميل قسم المميزة والنادرة: ${esc(e.message)}</p>`;
  }
}
window.disableSpecialItem = async (id) => {
  if (!confirm("إيقاف ظهور هذا المقتنى في صفحة الأرقام المميزة والأخطاء النادرة؟ لن يُحذف من المستودع ولن تُحذف بيانات التميز.")) return;
  try {
    let rows = await all(), item = rows.find(x => String(x.id) === String(id));
    if (!item) throw new Error("المقتنى غير موجود");
    item = { ...item, specialNumberEnabled: false, updated: Date.now() };
    await put(item); await refresh(true); await renderSpecialAdmin();
    toast("تم إيقاف المقتنى من صفحة المميزة والنادرة مع بقائه في المستودع.");
  } catch (e) { alert("تعذر الإيقاف: " + e.message); }
};
document.querySelectorAll(".special-metric").forEach(b => b.addEventListener("click", () => {
  specialAdminFilter = b.dataset.specialFilter || "all";
  document.querySelectorAll(".special-metric").forEach(x => x.classList.toggle("active", x === b));
  renderSpecialAdminRows();
}));
if ($("specialSearch")) $("specialSearch").oninput = renderSpecialAdminRows;
if ($("specialTypeFilter")) $("specialTypeFilter").onchange = renderSpecialAdminRows;
if ($("refreshSpecial")) $("refreshSpecial").onclick = async () => { const b=$("refreshSpecial"),old=b.textContent; try{b.disabled=true;b.textContent="جارٍ التحديث...";await refresh(true);await renderSpecialAdmin();toast("تم تحديث قسم الأرقام المميزة.");}catch(e){alert(e.message)}finally{b.disabled=false;b.textContent=old;} };
if ($("specialAddNew")) $("specialAddNew").onclick = () => { show("add"); setTimeout(() => $("specialNumberEnabled")?.scrollIntoView({behavior:"smooth",block:"center"}), 80); };

window.removeItem = async (id) => {
  let reason=(prompt("سيتم نقل المقتنى إلى الأرشيف ولن يحذف نهائيًا. اكتب سبب الحذف:","")||"").trim();
  if(!reason)return;
  if(!confirm("نقل هذا المقتنى إلى الأرشيف؟ يمكن استعادته لاحقًا."))return;
  try {
    await api('/api/archive/item',{method:'POST',body:JSON.stringify({itemId:id,reason})});
    await refresh(true); await renderArchive();
    toast("تم نقل المقتنى إلى الأرشيف.");
  } catch (error) { alert("تعذر نقل المقتنى إلى الأرشيف: " + (error?.message || "خطأ غير معروف")); }
};
window.archiveButton=(id)=>`<button class="danger" onclick="removeItem('${esc(id)}')">حذف</button>`;
window.detail = async (id) => {
  let i = (await all()).find((x) => String(x.id) === String(id)),
    rows = [
      ["الدولة", i.country],
      ["الفئة", i.denomination],
      [
        "الإصدار",
        i.issueEdition === "أخرى"
          ? i.issueEditionOther || "أخرى"
          : i.issueEdition || "—",
      ],
      ["السنة", i.year],
      [
        "التقييم",
        i.isGraded
          ? "مُقيَّم — " +
            (i.gradingCompany || "جهة غير محددة") +
            " — " +
            (i.gradeValue || "بدون درجة")
          : "غير مُقيَّم",
      ],
      ["رقم شهادة التقييم", i.isGraded ? i.gradingCertNumber || "—" : "—"],
      [
        "نسبة التقييم",
        i.isGraded && i.gradePercent ? i.gradePercent + "%" : "—",
      ],
      [
        "التحقق من الشهادة",
        i.isGraded
          ? i.gradingVerificationStatus === "verified"
            ? "تم التحقق"
            : "غير متحقق"
          : "—",
      ],
      ["ملاحظات التقييم", i.isGraded ? i.gradingNotes || "—" : "—"],
      ["النوع", i.type],
      ["الحالة", i.condition],
      ["نوع الوحدة", inventoryUnitLabel(i.inventoryUnitType || "piece")],
      ["عدد الوحدات", i.inventoryUnitCount || i.quantity || 1],
      ["القطع في الوحدة", i.piecesPerUnit || 1],
      ["إجمالي الأوراق/القطع", i.quantity],
      ["المباعة", i.soldQuantity || 0],
      ["التالفة/المفقودة", i.damagedQuantity || 0],
      [
        "المتبقية",
        Math.max(0, (Number(i.quantity) || 0) - (Number(i.soldQuantity) || 0)),
      ],
      [
        "الأرقام التسلسلية",
        (i.serials || [i.serial]).filter(Boolean).join("، "),
      ],
      [
        "المزاد",
        i.forAuction
          ? auctionText(i.auctionEnd) + " — " + (i.auctionEnd || "")
          : "غير مخصص",
      ],
      [
        "حالة نشر المزاد",
        i.forAuction ? (i.auctionApproved ? "نشط" : "غير منشور") : "—",
      ],
      ["كمية المزاد", i.forAuction ? i.auctionQuantity || 1 : "—"],
      [
        "سعر فتح المزايدة",
        i.forAuction
          ? money(i.auctionOpeningPrice || i.auctionStartPrice || 0)
          : "—",
      ],
      ["قيمة الزيادة", i.forAuction ? money(i.auctionBidStep || 1) : "—"],
      [
        "حد تحقق البيع",
        i.forAuction
          ? money(i.auctionTargetPrice || Number(i.auctionStartPrice || 0) + 1)
          : "—",
      ],
      ["السعر الحالي", i.forAuction ? money(i.auctionCurrentPrice || 0) : "—"],
      [
        "التفاوض",
        i.forAuction && i.negotiationEnabled
          ? "مسموح حتى " + Number(i.negotiationPercent || 0) + "%"
          : "غير مفعّل",
      ],
      [
        "السوق العام",
        i.forMarket ? (i.marketApproved ? "نشط" : "غير نشط") : "غير مخصص",
      ],
      ["نوع عرض السوق", i.forMarket ? i.marketOfferType || "—" : "—"],
      [
        "سعر السوق",
        i.forMarket ? money(i.marketSalePrice || i.marketUnitPrice || 0) : "—",
      ],
      ["كمية السوق", i.forMarket ? i.marketQuantity || 1 : "—"],
      [
        "تفاوض السوق",
        i.forMarket && i.marketNegotiationEnabled
          ? "حتى " + Number(i.marketNegotiationPercent || 0) + "%"
          : "غير مفعّل",
      ],
      ["الموقع", loc(i)],
      ["صاحب المقتنى / البائع", i.ownerName || "—"],
      ["جوال البائع", i.ownerPhone || "—"],
      ["سعر الشراء", money(i.purchase)],
      ["الشحن", money(i.shipping)],
      ["تكاليف أخرى", money(i.other)],
      ["سعر متوقع", money(i.expectedPrice)],
      ["ملاحظات", i.notes],
    ];
  $("details").innerHTML =
    `<h2>${esc(i.country)} — ${esc(i.denomination)}</h2>${viewerHtml(i.frontImg, "الوجه")}${viewerHtml(i.backImg, "الخلف")}<table>${rows.map((r) => `<tr><td>${r[0]}</td><td>${esc(r[1])}</td></tr>`).join("")}</table>`;
  $("dlg").showModal();
  initViewers();
};
function viewerHtml(src, label) {
  if (!src) return "";
  let vid = "vw-" + Math.random().toString(36).slice(2);
  return `<h3>${label}</h3><div class="viewer-tools" data-target="${vid}"><button type="button" data-act="zin">＋ تكبير</button><button type="button" data-act="zout">－ تصغير</button><button type="button" data-act="rl">↺ تدوير يسار</button><button type="button" data-act="rr">↻ تدوير يمين</button><button type="button" data-act="reset">إعادة ضبط</button></div><div class="image-viewer" id="${vid}"><img src="${src}"></div>`;
}
function initViewers() {
  document.querySelectorAll(".image-viewer").forEach((box) => {
    let img = box.querySelector("img"),
      st = { scale: 1, rot: 0, x: 0, y: 0, drag: false, sx: 0, sy: 0 };
    let draw = () =>
      (img.style.transform = `translate(${st.x}px,${st.y}px) scale(${st.scale}) rotate(${st.rot}deg)`);
    let tools = document.querySelector(
      `.viewer-tools[data-target="${box.id}"]`,
    );
    tools?.querySelectorAll("button").forEach(
      (b) =>
        (b.onclick = () => {
          let a = b.dataset.act;
          if (a === "zin") st.scale = Math.min(5, st.scale + 0.25);
          if (a === "zout") st.scale = Math.max(0.25, st.scale - 0.25);
          if (a === "rl") st.rot -= 90;
          if (a === "rr") st.rot += 90;
          if (a === "reset")
            Object.assign(st, { scale: 1, rot: 0, x: 0, y: 0 });
          draw();
        }),
    );
    box.onpointerdown = (e) => {
      st.drag = true;
      st.sx = e.clientX - st.x;
      st.sy = e.clientY - st.y;
      box.setPointerCapture(e.pointerId);
    };
    box.onpointermove = (e) => {
      if (!st.drag) return;
      st.x = e.clientX - st.sx;
      st.y = e.clientY - st.sy;
      draw();
    };
    box.onpointerup = box.onpointercancel = () => (st.drag = false);
    box.onwheel = (e) => {
      e.preventDefault();
      st.scale = Math.max(
        0.25,
        Math.min(5, st.scale + (e.deltaY < 0 ? 0.15 : -0.15)),
      );
      draw();
    };
  });
}
let participantFilter = "all";
const approvalMeta = {new:["طلب جديد","new"],preliminary:["اعتماد مبدئي","preliminary"],final:["اعتماد نهائي","final"],suspended:["معلّق","suspended"],stopped:["موقوف","stopped"],cancelled:["ملغى","cancelled"]};
function approvalBadge(x){let s=x.approvalStatus||"new",m=approvalMeta[s]||approvalMeta.new;return `<span class="approval-badge ${m[1]}">${m[0]}</span>`}
function participantActions(x){
  if((x.approvalStatus||"")==="cancelled")
    return `<button class="participant-history" onclick="showParticipantHistory('${x.id}')">عرض سجل المستخدم</button>`;
  let wa=x.whatsappPending?`<button class="approval-final" onclick="participantWhatsAppDecision('${x.id}','${x.whatsappPendingRequestId}','approve')">✅ مطابقة واتساب واعتماد كامل</button><button class="approval-cancelled" onclick="participantWhatsAppDecision('${x.id}','${x.whatsappPendingRequestId}','reject')">رفض طلب واتساب</button>`:"";
  return `${wa}<button class="approval-preliminary" onclick="participantSetStatus('${x.id}','preliminary')">توثيق مبدئي</button>
  <button class="approval-final" onclick="participantSetStatus('${x.id}','final')">توثيق كامل</button>
  <button class="approval-suspended" onclick="participantSetStatus('${x.id}','suspended')">تعليق الحساب</button>
  <button class="approval-stopped" onclick="participantSetStatus('${x.id}','stopped')">إيقاف الحساب</button>
  <button class="approval-cancelled" onclick="participantSetStatus('${x.id}','cancelled')">إلغاء الحساب</button>
  <button class="ghost" onclick="resetParticipantPin('${x.id}')">🔑 رمز الدخول</button>
  <button class="participant-history" onclick="showParticipantHistory('${x.id}')">عرض سجل المستخدم</button>`;
}
window.resetParticipantPin=async id=>{
  let pin=(prompt("اكتب رمز دخول جديد للحساب (4 خانات أو أكثر):","")||"").trim();
  if(!pin)return;
  if(pin.length<4){alert("الرمز قصير جدًا");return}
  if(!confirm("سيتم إنهاء أي جلسة دخول قديمة لهذا الحساب. متابعة؟"))return;
  try{await api("/api/participant/reset-pin",{method:"POST",body:JSON.stringify({id,pin})});alert("تم تحديث رمز الدخول. أعطه لصاحب الحساب بطريقة آمنة.")}catch(e){alert(e.message)}
};
async function renderParticipants() {
  try {
    let r = await api("/api/participants");
    let all=[...(r.participants||[]),...(r.archive||[])],counts=r.counts||{};
    let a=participantFilter==="all"?all:all.filter(x=>(x.approvalStatus||"new")===participantFilter);
    if ($("pendingParticipantsCount"))
      $("pendingParticipantsCount").textContent = r.pending || 0;
    if ($("participantsTotalCount"))
      $("participantsTotalCount").textContent = r.total || a.length;
    if ($("participantsArchiveCount"))
      $("participantsArchiveCount").textContent = Number(r.archived || 0);
    document.querySelectorAll("[data-count]").forEach(el=>el.textContent=counts[el.dataset.count]||0);
    $("participantsList").innerHTML=a.map(x=>`<div class="participant status-${esc(x.approvalStatus||'new')}"><div class="participant-head"><b>${esc(x.name||"")}</b>${approvalBadge(x)}</div><div>${esc(x.phone||"")}</div><small class="muted">رمز المشاركة: ${esc(x.id||"")} ${x.created?"— التسجيل: "+new Date(x.created).toLocaleString("ar-SA"):""}</small>${x.whatsappPending?`<p class="participant-reason"><b>طلب واتساب قيد الانتظار:</b> ${esc(x.whatsappPendingCode||"")}</p>`:""}${x.archiveReason?`<p class="participant-reason">السبب: ${esc(x.archiveReason)}</p>`:""}<div class="actions participant-approval-actions">${participantActions(x)}</div></div>`).join("")||"<p>لا يوجد مشاركون في هذا التصنيف.</p>";
    window.__participantRows=all;
    await refreshParticipantBadge();
  } catch (e) {
    $("participantsList").innerHTML = `<p>تعذر تحميل المشاركين: ${esc(e.message || "خطأ غير معروف")}</p>`;
  }
}
async function refreshParticipantBadge() {
  try {
    let r = await api("/api/participants/summary"),
      b = $("pendingParticipantsBadge");
    if (b) {
      b.textContent = r.pending || 0;
      b.hidden = !(r.pending > 0);
    }
    if ($("pendingParticipantsCount"))
      $("pendingParticipantsCount").textContent = r.pending || 0;
    if ($("participantsTotalCount"))
      $("participantsTotalCount").textContent = r.total || 0;
    if ($("participantsArchiveCount"))
      $("participantsArchiveCount").textContent = r.archived || 0;
    if ($("dashboardParticipantsPending"))
      $("dashboardParticipantsPending").textContent = r.pending || 0;
  } catch (e) {}
}
window.participantWhatsAppDecision=async(id,requestId,action)=>{let label=action==="approve"?"اعتماد التوثيق الكامل بعد مطابقة رسالة واتساب":"رفض طلب التوثيق عبر واتساب";if(!confirm(`تأكيد ${label}؟`))return;try{await api("/api/participant/whatsapp-decision",{method:"POST",body:JSON.stringify({id,requestId,action})});await renderParticipants();await renderAdminNotifications();alert(action==="approve"?"تم اعتماد الحساب بالكامل وأصبح بإمكانه المزايدة.":"تم رفض طلب واتساب.")}catch(e){alert("تعذر تنفيذ القرار: "+e.message)}};
window.participantSetStatus=async(id,status)=>{let labels={preliminary:"التوثيق المبدئي",final:"التوثيق الكامل",suspended:"تعليق الحساب",stopped:"إيقاف الحساب",cancelled:"إلغاء الحساب نهائيًا"},reason="";if(["suspended","stopped","cancelled"].includes(status)){reason=prompt("اكتب سبب القرار (إلزامي):","")?.trim()||"";if(!reason){alert("لم ينفذ القرار: كتابة السبب إلزامية.");return}}if(!confirm(`تأكيد ${labels[status]} لهذا المستخدم؟${reason?"\nالسبب: "+reason:""}`))return;try{await api("/api/participant/approval-status",{method:"POST",body:JSON.stringify({id,status,reason})});await renderParticipants();await renderAdminNotifications()}catch(e){alert("تعذر تحديث حالة الحساب: "+e.message)}};
window.showParticipantHistory=id=>{let x=(window.__participantRows||[]).find(p=>p.id===id),rows=x?.approvalHistory||[];let lines=rows.length?rows.slice().reverse().map(h=>`${new Date(h.at).toLocaleString("ar-SA")} — ${(approvalMeta[h.status]||[h.status])[0]} — ${h.actor||"الإدارة"}${h.reason?" — "+h.reason:""}`).join("\n"):"لا يوجد سجل سابق.";alert(`سجل المستخدم: ${x?.name||""}\n\n${lines}`)};
document.querySelectorAll("[data-participant-filter]").forEach(b=>b.addEventListener("click",()=>{document.querySelectorAll("[data-participant-filter]").forEach(x=>x.classList.remove("active"));b.classList.add("active");participantFilter=b.dataset.participantFilter;renderParticipants()}));
async function loadAdminBids() {
  try {
    let r = await api("/api/bids");
    let bids = r.bids || [];
    document.querySelectorAll('[id^="bids-"]').forEach((el) => {
      let id = el.id.slice(5),
        round = Number(el.dataset.round || 1),
        z = bids
          .filter(
            (b) => b.itemId === id && Number(b.auctionRound || 1) === round,
          )
          .sort((a, b) => b.amount - a.amount),
        count = z.length;
      el.innerHTML = `<button type="button" class="bid-toggle" aria-expanded="false">مزايدات الجولة الحالية (${count}) ▼</button><div class="bid-content" hidden>${
        count
          ? z
              .slice(0, 5)
              .map(
                (b) => `<p>${money(b.amount)} — ${esc(b.bidderName || "")} <span class="approval-badge ${esc(b.approvalStatus||'new')}">${esc(b.approvalLabel||'طلب جديد')}</span></p>`,
              )
              .join("")
          : "<p>لا توجد مزايدات في هذه الجولة</p>"
      }</div>`;
      let btn = el.querySelector(".bid-toggle"),
        box = el.querySelector(".bid-content");
      btn.onclick = () => {
        let open = box.hidden;
        box.hidden = !open;
        btn.setAttribute("aria-expanded", String(open));
        btn.textContent = `مزايدات الجولة الحالية (${count}) ${open ? "▲" : "▼"}`;
      };
    });
  } catch (e) {}
}
async function analyzeCurrentImage() {
  let st = $("analysisStatus"),
    urls = [frontImg, backImg].filter(Boolean);
  if (!urls.length) {
    alert("اختر أو صوّر صورة واحدة على الأقل أولاً");
    return;
  }
  st.textContent = "جارٍ تحليل صور المقتنى...";
  st.className = "muted";
  try {
    let mergedFields = {},
      notes = [],
      success = false,
      rawTexts = [];
    for (let url of urls) {
      try {
        let r = await fetch("/api/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url }),
            cache: "no-store",
          }),
          j = {};
        try {
          j = await r.json();
        } catch (_e) {}
        if (!r.ok) {
          notes.push(j.error || "تعذر الوصول إلى خدمة تحليل الصور");
          continue;
        }
        success = success || !!j.ok;
        let payload = j.data || {},
          fields = payload.fields || {};
        if (payload.rawText) rawTexts.push(payload.rawText);
        for (let [k, vv] of Object.entries(fields)) {
          if (!vv || !vv.value) continue;
          let prev = mergedFields[k];
          if (
            !prev ||
            Number(vv.confidence || 0) > Number(prev.confidence || 0)
          )
            mergedFields[k] = vv;
        }
        if (j.note) notes.push(j.note);
      } catch (e) {
        notes.push(
          e?.message === "Failed to fetch"
            ? "خدمة تحليل الصور غير متصلة بالخادم المحلي. أعد تشغيل البرنامج ثم حاول مرة أخرى."
            : e.message || "تعذر تحليل الصورة",
        );
      }
    }
    let labels = {
      country: "الدولة",
      denomination: "الفئة / القيمة",
      year: "السنة",
      serial: "الرقم التسلسلي",
    };
    let high = [],
      medium = [];
    for (let [k, vv] of Object.entries(mergedFields)) {
      let c = Number(vv.confidence || 0),
        level = vv.level || (c >= 0.82 ? "high" : c >= 0.55 ? "medium" : "low");
      if (level === "high") high.push([k, vv]);
      else if (level === "medium") medium.push([k, vv]);
    }
    // High-confidence fields only: fill empty form fields automatically, never overwrite user data.
    for (let [k, vv] of high) {
      if (k === "country" && !selectedCountryValue()) setCountryValue(vv.value);
      else if (["denomination", "year"].includes(k) && $(k) && !v(k))
        $(k).value = vv.value;
      if (
        k === "serial" &&
        document.querySelector(".serial-input") &&
        !document.querySelector(".serial-input").value
      ) {
        let el = document.querySelector(".serial-input");
        el.value = vv.value;
        el.dispatchEvent(new Event("input"));
      }
    }
    let box = document.getElementById("ocrSuggestionBox");
    if (!box) {
      box = document.createElement("div");
      box.id = "ocrSuggestionBox";
      box.className = "ocr-suggestion-box";
      st.parentElement?.appendChild(box);
    }
    box.innerHTML = "";
    if (high.length || medium.length) {
      let title = document.createElement("div");
      title.className = "ocr-suggestion-title";
      title.textContent = "نتائج تحليل الصورة";
      box.appendChild(title);
      for (let [k, vv] of [...high, ...medium]) {
        let row = document.createElement("div");
        row.className =
          "ocr-suggestion-row " +
          ((vv.level || "") === "high" ? "high" : "medium");
        let pct = Math.round(Number(vv.confidence || 0) * 100),
          isHigh = vv.level === "high" || Number(vv.confidence) >= 0.82;
        row.innerHTML = `<div><b>${labels[k] || k}:</b> <span>${vv.value}</span><small>${isHigh ? "ثقة عالية" : "اقتراح للمراجعة"} — ${pct}%</small></div>`;
        if (!isHigh) {
          let b = document.createElement("button");
          b.type = "button";
          b.className = "ghost ocr-accept";
          b.textContent = "اعتماد الاقتراح";
          b.onclick = () => {
            if (k === "country") setCountryValue(vv.value);
            else if (["denomination", "year"].includes(k) && $(k))
              $(k).value = vv.value;
            if (k === "serial" && document.querySelector(".serial-input")) {
              let el = document.querySelector(".serial-input");
              el.value = vv.value;
              el.dispatchEvent(new Event("input"));
            }
            row.classList.add("accepted");
            b.textContent = "✓ تم الاعتماد";
            b.disabled = true;
          };
          row.appendChild(b);
        }
        box.appendChild(row);
      }
      if (rawTexts.length) {
        let det = document.createElement("details");
        det.className = "ocr-raw-details";
        det.innerHTML = "<summary>عرض النص الذي قرأه OCR</summary><pre></pre>";
        det.querySelector("pre").textContent = rawTexts
          .join("\n---\n")
          .slice(0, 3500);
        box.appendChild(det);
      }
    }
    let highCount = high.length,
      medCount = medium.length;
    if (highCount || medCount) {
      st.textContent = `✅ تم التحليل: ${highCount} بيانات عالية الثقة${medCount ? `، و${medCount} اقتراحات تحتاج مراجعة` : ""}. لن يتم استبدال أي بيانات أدخلتها يدويًا.`;
      st.className = "analysis-ok";
    } else {
      st.textContent =
        notes.filter(Boolean).join(" — ") ||
        "لم يتم العثور على بيانات موثوقة. يمكنك إدخال البيانات يدويًا وحفظ المقتنى بصورة طبيعية.";
      st.className = "analysis-warn";
    }
  } catch (e) {
    st.textContent =
      "⚠️ تعذر تحليل الصور فقط؛ رفع الصور وحفظ المقتنى ما زالا يعملان: " +
      (e.message || "خطأ غير معروف");
    st.className = "analysis-warn";
  }
}
$("analyzeImage").onclick = analyzeCurrentImage;
window.editItem = async (id) => {
  let i = (await all()).find((x) => String(x.id) === String(id));
  if (!i) {
    alert("تعذر العثور على المقتنى. حدّث صفحة المستودع ثم حاول مرة أخرى.");
    return;
  }
resetItemForm();
await loadStorageCatalog(i);
editingItemId = String(i.id || id);
$("id").value = editingItemId;
let saveBtn = $("form")?.querySelector("button[type=submit]");
if (saveBtn) saveBtn.disabled = false;
  Object.keys(i).forEach((k) => {
    if ($(k) && !["front", "back", "year", "country"].includes(k)) $(k).value = i[k] ?? "";
  });
  if ($("storeType")) $("storeType").value = i.storeType || (i.fantasiaEnabled ? "collectibles" : "coins");
  if ($("collectibleCategory")) $("collectibleCategory").value = i.collectibleCategory || (i.fantasiaEnabled ? "fantasia" : "");
  if ($("collectibleCategoryWrap")) $("collectibleCategoryWrap").hidden = $("storeType")?.value !== "collectibles";
  setCountryValue(i.country || "");
  renderStorageSelectors(i);
  if ($("issueEdition")) $("issueEdition").value = i.issueEdition || "";
  if ($("issueEditionOther"))
    $("issueEditionOther").value = i.issueEditionOther || "";
  updateEditionUI();
  fillYearFields(i.year, i.yearFrom, i.yearTo);
  if ($("isGraded")) $("isGraded").checked = !!i.isGraded;
  if (i.gradingCompany) ensureGradingCompanyOption(i.gradingCompany);
  if ($("gradingCompany")) $("gradingCompany").value = i.gradingCompany || "";
  updateGradingUI();
  $("forAuction").checked = !!i.forAuction;
  $("auctionApproved").checked = !!i.auctionApproved;
  if ($("negotiationEnabled"))
    $("negotiationEnabled").checked = !!i.negotiationEnabled;
  if ($("negotiationPercent"))
    $("negotiationPercent").value = String(i.negotiationPercent || 5);
  if ($("specialNumberEnabled"))
    $("specialNumberEnabled").checked = !!i.specialNumberEnabled;
  document
    .querySelectorAll(".special-number-type")
    .forEach(
      (x) =>
        (x.checked = (
          Array.isArray(i.specialNumberTypes)
            ? i.specialNumberTypes
            : [i.specialNumberType].filter(Boolean)
        ).includes(x.value)),
    );
  if ($("specialNumberReason"))
    $("specialNumberReason").value = i.specialNumberReason || "";
  if ($("specialNumberFields"))
    $("specialNumberFields").hidden = !i.specialNumberEnabled;
  if ($("fantasiaEnabled")) $("fantasiaEnabled").checked = !!i.fantasiaEnabled;
  if ($("fantasiaType")) $("fantasiaType").value = i.fantasiaType || "banknote";
  if ($("fantasiaIssuer")) $("fantasiaIssuer").value = i.fantasiaIssuer || "";
  if ($("fantasiaNotes")) $("fantasiaNotes").value = i.fantasiaNotes || "";
  if ($("fantasiaFields")) $("fantasiaFields").hidden = !i.fantasiaEnabled;
  if ($("transitionalIssueEnabled")) $("transitionalIssueEnabled").checked = !!i.transitionalIssueEnabled;
  ["transitionalIssueType","transitionalPreviousIssue","transitionalNextIssue","transitionalRarity","transitionalEstimatedPopulation","transitionalReferenceValue","transitionalReason","transitionalNotes"].forEach(k=>{ if ($(k)) $(k).value = i[k] ?? ""; });
  if ($("transitionalIssueFields")) $("transitionalIssueFields").hidden = !i.transitionalIssueEnabled;
  if ($("advancedSerialSection")) $("advancedSerialSection").open = !!((i.serialNumbers || []).length || i.autoSerialEnabled);
  if ($("storageDetails")) $("storageDetails").open = !!([i.warehouse,i.cabinet,i.shelf,i.box,i.album,i.pocket].some(x=>String(x||"").trim()));
  if ($("financialDetails")) $("financialDetails").open = !!(Number(i.purchase||0) || Number(i.shipping||0) || Number(i.other||0) || Number(i.expectedPrice||0) || String(i.notes||"").trim());
  if ($("forMarket")) $("forMarket").checked = !!i.forMarket;
  if ($("marketApproved")) $("marketApproved").checked = !!i.marketApproved;
  if ($("marketCategory")) $("marketCategory").value = marketCategoryKey(i.marketCategory || (i.fantasiaEnabled?"fantasia":i.specialNumberEnabled?"special":i.transitionalIssueEnabled?"transitional":"coins-stamps"));
  if ($("marketPartialAllowed"))
    $("marketPartialAllowed").checked = !!i.marketPartialAllowed;
  if ($("marketNegotiationEnabled"))
    $("marketNegotiationEnabled").checked = !!i.marketNegotiationEnabled;
  if ($("homeFeatured")) $("homeFeatured").checked = !!i.homeFeatured;
  if ($("homeQuickDeal")) $("homeQuickDeal").checked = !!i.homeQuickDeal;
  if ($("homeDiscounted")) $("homeDiscounted").checked = !!i.homeDiscounted;
  if ($("homeDiscountPercent")) $("homeDiscountPercent").value = Number(i.homeDiscountPercent || 0);
  if ($("homePromoUntil")) $("homePromoUntil").value = String(i.homePromoUntil || "").slice(0,16);
  if ($("inventoryUnitType")) $("inventoryUnitType").value = i.inventoryUnitType || "piece";
  if ($("inventoryUnitCount")) $("inventoryUnitCount").value = Number(i.inventoryUnitCount || i.quantity || 1);
  if ($("piecesPerUnit")) $("piecesPerUnit").value = Number(i.piecesPerUnit || 1);
  updateInventoryQuantity();
  if (
    !i.marketPriceUnit &&
    i.marketOfferType === "set" &&
    Number(i.marketUnitPrice || 0) > 0 &&
    $("marketSalePrice")
  )
    $("marketSalePrice").value = Number(i.marketUnitPrice);
  updateMarketUI();
  frontImg = i.frontImg || "";
  backImg = i.backImg || "";
  frontImageRemoved = backImageRemoved = false;
  setPreview("front", frontImg);
  setPreview("back", backImg);
  if ($("autoSerialEnabled")) $("autoSerialEnabled").checked = !!i.autoSerialEnabled;
  if ($("serialStart")) $("serialStart").value = i.serialStart || "";
  if ($("serialCount")) $("serialCount").value = Number(i.serialCount || (i.serials || []).length || i.quantity || 1);
  generatedSerials = i.autoSerialEnabled ? (i.serials || [i.serial || ""]).filter(Boolean) : [];
  updateAutoSerialUI();
  renderSerialFields(i.serials || [i.serial || ""]);
  updateAuctionUI();
  updateMarketUI();
  show("add");
  window.scrollTo({ top: 0, behavior: "smooth" });
};
$("close").onclick = () => $("dlg").close();
if ($("inventoryUnitType")) $("inventoryUnitType").onchange = () => {
  if ($("inventoryUnitType").value === "strap" && Number($("piecesPerUnit").value || 1) === 1) $("piecesPerUnit").value = 100;
  updateInventoryQuantity();
};
if ($("inventoryUnitCount")) $("inventoryUnitCount").oninput = updateInventoryQuantity;
if ($("piecesPerUnit")) $("piecesPerUnit").oninput = updateInventoryQuantity;
if ($("autoSerialEnabled")) $("autoSerialEnabled").onchange = updateAutoSerialUI;
if ($("serialCount")) $("serialCount").oninput = () => { $("serialCount").dataset.userChanged = "1"; };
if ($("generateSerials")) $("generateSerials").onclick = () => {
  try {
    generatedSerials = generateSerialSequence(v("serialStart"), n("serialCount"));
    let first = generatedSerials[0], last = generatedSerials[generatedSerials.length - 1];
    $("serialRangePreview").textContent = `من ${first} إلى ${last} — العدد ${generatedSerials.length}`;
    renderSerialFields();
  } catch (e) {
    generatedSerials = []; $("serialRangePreview").textContent = "⚠️ " + e.message; renderSerialFields();
  }
};
$("forAuction").onchange = () => {
  updateAuctionUI();
};
if ($("forMarket"))
  $("forMarket").onchange = () => {
    updateMarketUI();
  };
if ($("marketOfferType")) $("marketOfferType").onchange = updateMarketUI;
if ($("marketPriceUnit")) $("marketPriceUnit").onchange = updateMarketUI;
if ($("marketQuantity")) $("marketQuantity").oninput = updateMarketUI;
if ($("marketSetPieces")) $("marketSetPieces").oninput = updateMarketUI;
if ($("marketSalePrice")) $("marketSalePrice").oninput = updateMarketUI;
$("auctionEnd").oninput = updateAuctionUI;
if ($("country")) $("country").onchange = updateCountryUI;
updateCountryUI();
if ($("issueEdition")) $("issueEdition").onchange = updateEditionUI;
if ($("yearMode")) $("yearMode").onchange = updateYearUI;
if ($("isGraded")) $("isGraded").onchange = updateGradingUI;
if ($("addGradingCompanyBtn")) $("addGradingCompanyBtn").onclick = openAddGradingCompany;
if ($("saveGradingCompanyBtn")) $("saveGradingCompanyBtn").onclick = addGradingCompany;
if ($("cancelGradingCompanyBtn")) $("cancelGradingCompanyBtn").onclick = closeAddGradingCompany;
if ($("newGradingCompany")) $("newGradingCompany").onkeydown = (e) => {
  if (e.key === "Enter") { e.preventDefault(); addGradingCompany(); }
  if (e.key === "Escape") closeAddGradingCompany();
};
initGradingCompanies();
function wirePhotoInput(id, which) {
  let el = $(id);
  if (!el) return;
  el.onchange = async (e) => {
    mediaPicking = true;
    let status = $("analysisStatus");
    try {
      let f = e.target.files && e.target.files[0];
      if (!f) return;
      status.textContent = "جارٍ رفع الصورة...";
      status.className = "muted";
      let url = await imgFile(f);
      if (which === "front") frontImg = url;
      else backImg = url;
      if (which === "front") frontImageRemoved = false;
      else backImageRemoved = false;
      setPreview(which, url);
      status.textContent =
        "✅ تم رفع الصورة وحفظها. يمكنك الآن تدويرها وقصها أو متابعة الحفظ.";
      status.className = "analysis-ok";
    } catch (x) {
      console.error(x);
      alert(x.message);
      status.textContent = "⚠️ " + x.message;
      status.className = "analysis-warn";
    } finally {
      mediaPicking = false;
      e.target.value = "";
    }
  };
}
["frontCamera", "frontGallery"].forEach((id) => wirePhotoInput(id, "front"));
["backCamera", "backGallery"].forEach((id) => wirePhotoInput(id, "back"));
$("form").onsubmit = async (e) => {
  e.preventDefault();
  if (isSaving) return;
  isSaving = true;
  let btn = $("form").querySelector("button[type=submit]"),
    oldText = btn.textContent;
  btn.disabled = true;
  btn.textContent = "جارٍ الحفظ والتحقق...";
  try {
  let id = editingItemId || v("id") || newId(),
    old = (await all()).find((x) => String(x.id) === String(id));
    let year = composedYear();
    $("year").value = year;
    let wantsAuction = $("forAuction").checked,
      wantsMarket = !!$("forMarket")?.checked,
      auctionPublish = wantsAuction && $("auctionApproved").checked,
      marketPublish = wantsMarket && !!$("marketApproved")?.checked;
    // تعديل بيانات المستودع لا يعيد فتح مزاد قديم منتهٍ.
    // الموعد المستقبلي مطلوب فقط للنشر الجديد أو عند تغيير موعد الانتهاء.
    let oldAuctionApproved = !!(old?.forAuction && old?.auctionApproved),
      auctionEndChanged = String(v("auctionEnd") || "") !== String(old?.auctionEnd || ""),
      auctionNeedsFreshSchedule = auctionPublish &&
        (!old || !oldAuctionApproved || auctionEndChanged),
      auctionEndMs = auctionPublish ? new Date(v("auctionEnd")).getTime() : NaN;
    if (auctionPublish) {
      let end = v("auctionEnd");
      if (!end)
        throw new Error(
          "نشر المزاد يتطلب تحديد تاريخ ووقت انتهاء المزاد",
        );
      if (!Number.isFinite(auctionEndMs))
        throw new Error("صيغة تاريخ انتهاء المزاد غير صحيحة");
      if (auctionNeedsFreshSchedule && auctionEndMs <= Date.now())
        throw new Error("موعد انتهاء المزاد يجب أن يكون في المستقبل");
    }
    if (marketPublish) {
      if (n("marketSalePrice") <= 0)
        throw new Error("نشر العرض في السوق يتطلب سعر بيع أكبر من صفر");
      if ((n("marketQuantity") || 0) < 1)
        throw new Error("الكمية المعروضة في السوق يجب أن تكون 1 على الأقل");
    }
    if (!selectedCountryValue()) throw new Error("اختر الدولة من القائمة، أو اكتب اسم دولة / جهة إصدار أخرى");
    if ($("country")?.value === "__other__" && !v("countryOther")) throw new Error("اكتب اسم الدولة / جهة الإصدار الأخرى");
    if ($("autoSerialEnabled")?.checked) {
      if (!generatedSerials.length) generatedSerials = generateSerialSequence(v("serialStart"), n("serialCount"));
      if (generatedSerials.length !== Math.max(1, n("serialCount") || 1)) throw new Error("تعذر إكمال التسلسل الآلي بالأعداد المطلوبة");
    }
    let totalPhysical = n("quantity") || 1,
      piecesPerUnit = Math.max(1, n("piecesPerUnit") || 1),
      marketPhysical = marketPublish ? (n("marketQuantity") || 1) * (v("marketOfferType") === "set" ? Math.max(1, n("marketSetPieces") || piecesPerUnit) : v("marketOfferType") === "bundle" ? piecesPerUnit : 1) : 0,
      auctionPhysical = auctionPublish ? Math.max(1, n("auctionQuantity") || 1) : 0;
    if (!old && n("soldQuantity") + n("damagedQuantity") + marketPhysical + auctionPhysical > totalPhysical)
      throw new Error(`توزيع الكمية يتجاوز الرصيد الفعلي ${totalPhysical}. خفّض كمية السوق أو المزاد أو الكميات الخارجة.`);
    let payload = {
      id,
      storeType: v("storeType") || "coins",
      collectibleCategory: v("storeType") === "collectibles" ? v("collectibleCategory") : "",
      country: selectedCountryValue(),
      denomination: v("denomination"),
      issueEdition: v("issueEdition"),
      issueEditionOther: v("issueEditionOther"),
      year,
      yearFrom: v("yearFrom"),
      yearTo: $("yearMode").value === "range" ? v("yearTo") : "",
      yearMode: v("yearMode"),
      isGraded: $("isGraded").checked,
      gradingStatus: $("isGraded").checked ? "graded" : "ungraded",
      gradingCompany: $("isGraded").checked ? v("gradingCompany") : "",
      gradeValue: $("isGraded").checked ? v("gradeValue") : "",
      gradePercent: $("isGraded").checked ? n("gradePercent") : 0,
      gradingCertNumber: $("isGraded").checked ? v("gradingCertNumber") : "",
      gradingVerificationStatus: $("isGraded").checked
        ? v("gradingVerificationStatus")
        : "",
      gradingNotes: $("isGraded").checked ? v("gradingNotes") : "",
      type: v("type"),
      condition: v("condition"),
      inventoryUnitType: v("inventoryUnitType") || "piece",
      inventoryUnitCount: Math.max(1, n("inventoryUnitCount") || 1),
      piecesPerUnit,
      quantity: totalPhysical,
      soldQuantity: Math.min(
        totalPhysical,
        Math.max(0, n("soldQuantity")),
      ),
      damagedQuantity: Math.min(totalPhysical, Math.max(0, n("damagedQuantity"))),
      serials: serialValues(),
      serial: serialValues()[0] || "",
      serialType: serial(serialValues()[0] || ""),
      autoSerialEnabled: !!$("autoSerialEnabled")?.checked,
      serialStart: $("autoSerialEnabled")?.checked ? v("serialStart") : "",
      serialCount: $("autoSerialEnabled")?.checked ? generatedSerials.length : serialValues().length,
      specialNumberEnabled: !!$("specialNumberEnabled")?.checked,
      specialNumberTypes: $("specialNumberEnabled")?.checked
        ? [...document.querySelectorAll(".special-number-type:checked")].map(
            (x) => x.value,
          )
        : [],
      specialNumberType: $("specialNumberEnabled")?.checked
        ? [...document.querySelectorAll(".special-number-type:checked")].map(
            (x) => x.value,
          )[0] || ""
        : "",
      specialNumberReason: $("specialNumberEnabled")?.checked
        ? v("specialNumberReason")
        : "",
      fantasiaEnabled: !!$("fantasiaEnabled")?.checked,
      fantasiaType: $("fantasiaEnabled")?.checked ? v("fantasiaType") : "",
      fantasiaIssuer: $("fantasiaEnabled")?.checked ? v("fantasiaIssuer") : "",
      fantasiaNotes: $("fantasiaEnabled")?.checked ? v("fantasiaNotes") : "",
      transitionalIssueEnabled: !!$("transitionalIssueEnabled")?.checked,
      transitionalIssueType: $("transitionalIssueEnabled")?.checked ? v("transitionalIssueType") : "",
      transitionalPreviousIssue: $("transitionalIssueEnabled")?.checked ? v("transitionalPreviousIssue") : "",
      transitionalNextIssue: $("transitionalIssueEnabled")?.checked ? v("transitionalNextIssue") : "",
      transitionalRarity: $("transitionalIssueEnabled")?.checked ? v("transitionalRarity") : "",
      transitionalEstimatedPopulation: $("transitionalIssueEnabled")?.checked ? v("transitionalEstimatedPopulation") : "",
      transitionalReferenceValue: $("transitionalIssueEnabled")?.checked ? n("transitionalReferenceValue") : 0,
      transitionalReason: $("transitionalIssueEnabled")?.checked ? v("transitionalReason") : "",
      transitionalNotes: $("transitionalIssueEnabled")?.checked ? v("transitionalNotes") : "",
      forAuction: wantsAuction,
      auctionEnd: wantsAuction ? v("auctionEnd") : "",
      auctionStartPrice: n("auctionStartPrice"),
      auctionOpeningPrice: n("auctionOpeningPrice"),
      auctionBidStep: n("auctionBidStep") || 1,
      auctionTargetPrice: n("auctionTargetPrice"),
      auctionCurrentPrice: n("auctionCurrentPrice"),
      auctionQuantity: wantsAuction ? Math.max(1, n("auctionQuantity") || 1) : 0,
      auctionApproved: auctionPublish,
      negotiationEnabled: wantsAuction && $("negotiationEnabled").checked,
      negotiationPercent: n("negotiationPercent") || 5,
      forMarket: wantsMarket,
      marketApproved: marketPublish,
      marketCategory: wantsMarket ? v("marketCategory") : "",
      marketOfferType: wantsMarket ? v("marketOfferType") : "",
      marketTitle: wantsMarket ? v("marketTitle") : "",
      marketSalePrice: wantsMarket ? n("marketSalePrice") : 0,
      marketUnitPrice: wantsMarket ? n("marketUnitPrice") : 0,
      marketQuantity: wantsMarket ? n("marketQuantity") || 1 : 0,
      marketSoldQuantity: old?.marketSoldQuantity || 0,
      marketSetPieces: wantsMarket ? n("marketSetPieces") : 0,
      marketSetSize: wantsMarket ? v("marketSetSize") : "",
      marketSetCurrencyMode: wantsMarket ? v("marketSetCurrencyMode") : "",
      marketPriceUnit: wantsMarket ? v("marketPriceUnit") : "",
      marketPartialAllowed: wantsMarket && $("marketPartialAllowed")?.checked,
      marketNegotiationEnabled:
        wantsMarket && $("marketNegotiationEnabled")?.checked,
      marketNegotiationPercent: n("marketNegotiationPercent") || 5,
      homeFeatured: wantsMarket && !!$("homeFeatured")?.checked,
      homeQuickDeal: wantsMarket && !!$("homeQuickDeal")?.checked,
      homeDiscounted: wantsMarket && !!$("homeDiscounted")?.checked,
      homeDiscountPercent: wantsMarket ? Math.max(0, Math.min(100, n("homeDiscountPercent"))) : 0,
      homePromoUntil: wantsMarket ? v("homePromoUntil") : "",
      frontImg: frontImageRemoved ? "" : frontImg || old?.frontImg || "",
      backImg: backImageRemoved ? "" : backImg || old?.backImg || "",
      warehouse: v("warehouse"),
      cabinet: v("cabinet"),
      shelf: v("shelf"),
      box: v("box"),
      album: v("album"),
      pocket: v("pocket"),
      ownerName: v("ownerName"),
      ownerPhone: v("ownerPhone"),
      ownerCountry: v("ownerCountry") || "المملكة العربية السعودية",
      purchase: n("purchase"),
      shipping: n("shipping"),
      other: n("other"),
      expectedPrice: n("expectedPrice"),
      notes: v("notes"),
      updated: Date.now(),
    };
    if (payload.transitionalIssueEnabled && !payload.transitionalIssueType)
      throw new Error("اختر نوع الإصدار الانتقالي");
    if (payload.transitionalIssueEnabled && !String(payload.transitionalReason || "").trim())
      throw new Error("اكتب سبب تصنيف المقتنى كإصدار انتقالي");
    if (
      payload.specialNumberEnabled &&
      (!Array.isArray(payload.specialNumberTypes) ||
        !payload.specialNumberTypes.length)
    )
      throw new Error(
        "اختر التصنيف: متكرر أو متسلسل أو متطابق أو متناظر أو تصاعدي أو تنازلي أو نادر أو أخطاء نادرة",
      );
   console.log("EDIT SAVE", {
  editingItemId,
  id,
  old,
  payload
});

let savedResult = await put(payload);
    if (
      savedResult?.verified !== true ||
      String(savedResult?.saved?.id || "") !== String(id)
    )
      throw new Error("أعاد الخادم نتيجة غير مؤكدة للحفظ؛ بقي النموذج كما هو");
    let verifiedItems = await all();
    let sameIdRows = verifiedItems.filter((x) => String(x.id) === String(id));
    if (sameIdRows.length !== 1)
      throw new Error("فشل التحقق من سلامة التعديل: يجب أن يوجد السجل مرة واحدة فقط بعد الحفظ");
    if (payload.specialNumberEnabled) {
      let savedTypes = Array.isArray(savedResult?.saved?.specialNumberTypes)
        ? savedResult.saved.specialNumberTypes
        : [];
      let missing = payload.specialNumberTypes.filter(
        (t) => !savedTypes.includes(t),
      );
      if (!savedResult.saved.specialNumberEnabled || missing.length)
        throw new Error(
          "تم حفظ السجل لكن لم يثبت تصنيف الأرقام المميزة بالكامل؛ بقي النموذج كما هو",
        );
    }
    let published = [];
    // المزادات العامة تعرض النشط فقط؛ المزاد المنتهي يبقى محفوظًا في السجل.
    if (auctionPublish && auctionEndMs > Date.now()) {
      let pub = await api("/api/public/auctions");
      if (!(pub.items || []).some((x) => String(x.id) === String(id)))
        throw new Error(
          "تم حفظ المقتنى لكن تعذر التحقق من ظهوره في المزاد؛ راجع وقت الانتهاء والاعتماد",
        );
      published.push("المزاد");
    }
    if (marketPublish) {
      let pub = await api("/api/public/market");
      if (!(pub.items || []).some((x) => String(x.id) === String(id)))
        throw new Error(
          "تم حفظ المقتنى لكن تعذر التحقق من ظهوره في السوق العام؛ راجع السعر والاعتماد",
        );
      published.push("السوق العام");
    }
    await refresh(true);
    resetItemForm();
    show("list");
    let suffix = published.length
      ? " وتم نشره والتحقق منه في " + published.join(" و ")
      : " (محفوظ وغير نشط حتى الاعتماد)";
    alert("✅ تم الحفظ والتحقق من السجل بنجاح" + suffix);
  } catch (err) {
    console.error(err);
    alert(
      "تعذر الحفظ أو النشر: " +
        (err && err.message ? err.message : "خطأ غير معروف"),
    );
  } finally {
    isSaving = false;
    btn.disabled = false;
    btn.textContent = oldText;
  }
};
function resetItemForm() {
editingItemId = "";
  let f = $("form");
  if (f && typeof f.reset === "function") f.reset();
  setCountryValue("");
  $("id").value = "";
  $("year").value = "";
  $("quantity").value = 1;
  $("soldQuantity").value = 0;
  if ($("damagedQuantity")) $("damagedQuantity").value = 0;
  if ($("ownerCountry")) $("ownerCountry").value = "المملكة العربية السعودية";
  if ($("inventoryUnitType")) $("inventoryUnitType").value = "piece";
  if ($("inventoryUnitCount")) $("inventoryUnitCount").value = 1;
  if ($("piecesPerUnit")) $("piecesPerUnit").value = 1;
  if ($("auctionQuantity")) $("auctionQuantity").value = 1;
  if ($("autoSerialEnabled")) $("autoSerialEnabled").checked = false;
  if ($("autoSerialFields")) $("autoSerialFields").hidden = true;
  if ($("serialStart")) $("serialStart").value = "";
  if ($("serialCount")) { $("serialCount").value = 1; delete $("serialCount").dataset.userChanged; }
  if ($("serialRangePreview")) $("serialRangePreview").textContent = "";
  generatedSerials = [];
  frontImg = backImg = "";
  frontImageRemoved = backImageRemoved = false;
  setPreview("front", "");
  setPreview("back", "");
  renderSerialFields([]);
  if ($("analysisStatus")) {
    $("analysisStatus").textContent = "";
    $("analysisStatus").className = "muted";
  }
  if ($("auctionBidStep")) $("auctionBidStep").value = 5;
  if ($("negotiationPercent")) $("negotiationPercent").value = "5";
  if ($("negotiationEnabled")) $("negotiationEnabled").checked = false;
  if ($("issueEdition")) $("issueEdition").value = "";
  if ($("issueEditionOther")) $("issueEditionOther").value = "";
  if ($("yearMode")) $("yearMode").value = "single";
  if ($("yearFrom")) $("yearFrom").value = "";
  if ($("yearTo")) $("yearTo").value = "";
  if ($("isGraded")) $("isGraded").checked = false;
  if ($("specialNumberEnabled")) $("specialNumberEnabled").checked = false;
  if ($("storeType")) $("storeType").value = "coins";
  if ($("collectibleCategory")) $("collectibleCategory").value = "";
  if ($("collectibleCategoryWrap")) $("collectibleCategoryWrap").hidden = true;
  if ($("fantasiaEnabled")) $("fantasiaEnabled").checked = false;
  if ($("fantasiaFields")) $("fantasiaFields").hidden = true;
  if ($("fantasiaType")) $("fantasiaType").value = "banknote";
  if ($("fantasiaIssuer")) $("fantasiaIssuer").value = "";
  if ($("fantasiaNotes")) $("fantasiaNotes").value = "";
  if ($("transitionalIssueEnabled")) $("transitionalIssueEnabled").checked = false;
  if ($("transitionalIssueFields")) $("transitionalIssueFields").hidden = true;
  ["transitionalPreviousIssue","transitionalNextIssue","transitionalEstimatedPopulation","transitionalReferenceValue","transitionalReason","transitionalNotes"].forEach(k=>{if($(k))$(k).value="";});
  if ($("transitionalIssueType")) $("transitionalIssueType").value="signature-change";
  if ($("transitionalRarity")) $("transitionalRarity").value="documented";
  document
    .querySelectorAll(".special-number-type")
    .forEach((x) => (x.checked = false));
  if ($("specialNumberReason")) $("specialNumberReason").value = "";
  if ($("specialNumberFields")) $("specialNumberFields").hidden = true;
  if ($("advancedSerialSection")) $("advancedSerialSection").open = false;
  if ($("storageDetails")) $("storageDetails").open = false;
  if ($("financialDetails")) $("financialDetails").open = false;
  if ($("forMarket")) $("forMarket").checked = false;
  if ($("marketApproved")) $("marketApproved").checked = false;
  if ($("marketCategory")) $("marketCategory").value = "coins-stamps";
  if ($("marketOfferType")) $("marketOfferType").value = "single";
  if ($("marketPriceUnit")) $("marketPriceUnit").value = "piece";
  if ($("marketQuantity")) $("marketQuantity").value = "1";
  if ($("marketSetPieces")) $("marketSetPieces").value = "1";
  if ($("marketSetSize")) $("marketSetSize").value = "mini";
  if ($("marketNegotiationPercent")) $("marketNegotiationPercent").value = "5";
  if ($("marketNegotiationEnabled"))
    $("marketNegotiationEnabled").checked = false;
  if ($("marketPartialAllowed")) $("marketPartialAllowed").checked = false;
  if ($("homeFeatured")) $("homeFeatured").checked = false;
  if ($("homeQuickDeal")) $("homeQuickDeal").checked = false;
  if ($("homeDiscounted")) $("homeDiscounted").checked = false;
  if ($("homeDiscountPercent")) $("homeDiscountPercent").value = "0";
  if ($("homePromoUntil")) $("homePromoUntil").value = "";
  renderStorageSelectors({ warehouse: "", cabinet: "", shelf: "", box: "", album: "", pocket: "" });
  updateEditionUI();
  updateYearUI();
  updateGradingUI();
  updateAuctionUI();
  updateMarketUI();
  updateInventoryQuantity();
}
if ($("reset"))
  $("reset").addEventListener("click", (e) => {
    e.preventDefault();
    resetItemForm();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
$("search").oninput = async () => renderList(await all());
$("quick").oninput = async () => {
  let q = v("quick").toLowerCase(),
    a = (await all()).filter((i) =>
      JSON.stringify(i).toLowerCase().includes(q),
    );
  $("quickResults").innerHTML = a
    .slice(0, 15)
    .map(
      (i) =>
        `<p onclick="detail('${i.id}')"><b>${esc(i.country)} — ${esc(i.denomination)}</b><br><span class="muted">${esc(loc(i))}</span></p>`,
    )
    .join("");
};
function download(blob, name) {
  let a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
}
async function exportFullBackup() {
  let btn = $("exportFull"),
    old = btn.textContent;
  try {
    btn.disabled = true;
    btn.textContent = "جارٍ تجهيز النسخة الكاملة...";
    let r = await fetch("/api/backup/full", { cache: "no-store" });
    if (!r.ok) throw new Error("تعذر إنشاء النسخة الكاملة");
    let blob = await r.blob(),
      stamp = new Date().toISOString().slice(0, 19).replaceAll(":", "-");
    download(blob, "khazina_full_" + stamp + ".khzbackup");
  } catch (e) {
    alert(e.message || "تعذر إنشاء النسخة الكاملة");
  } finally {
    btn.disabled = false;
    btn.textContent = old;
  }
}
async function importFullBackup(file) {
  if (!file) return;
  if (
    !confirm(
      "سيتم استبدال البيانات والصور الحالية بمحتويات النسخة الكاملة. ينشئ النظام نسخة أمان تلقائية قبل الاستعادة. متابعة؟",
    )
  )
    return;
  let label = $("importFull")?.closest("label"),
    old = label?.childNodes?.[0]?.textContent || "";
  try {
    if (label) label.style.opacity = ".55";
    let r = await fetch("/api/backup/restore", {
        method: "POST",
        headers: { "Content-Type": "application/octet-stream" },
        body: file,
        cache: "no-store",
      }),
      d = await r.json();
    if (!r.ok) throw new Error(d.error || "تعذر الاستعادة");
    alert(`✅ تمت الاستعادة الكاملة بنجاح
السجلات: ${d.items}
الصور: ${d.images}`);
    await refresh(true);
  } catch (e) {
    alert(e.message || "تعذر استعادة النسخة الكاملة");
  } finally {
    if (label) label.style.opacity = "";
    if ($("importFull")) $("importFull").value = "";
  }
}
if ($("exportFull")) $("exportFull").onclick = exportFullBackup;
if ($("importFull"))
  $("importFull").onchange = (e) => importFullBackup(e.target.files?.[0]);
$("export").onclick = async () =>
  download(
    new Blob([JSON.stringify({ version: 1, items: await all() })], {
      type: "application/json",
    }),
    "khazina_backup.json",
  );
$("import").onchange = async (e) => {
  try {
    let d = JSON.parse(await e.target.files[0].text());
    for (let i of d.items) await put(i);
    await refresh(true);
  } catch {
    alert("ملف غير صالح");
  }
};
$("csv").onclick = async () => {
  let a = await all(),
    cols = [
      "country",
      "denomination",
      "year",
      "type",
      "condition",
      "quantity",
      "soldQuantity",
      "serial",
      "serials",
      "serialType",
      "forAuction",
      "auctionEnd",
      "warehouse",
      "cabinet",
      "shelf",
      "box",
      "album",
      "pocket",
      "purchase",
      "shipping",
      "other",
      "expectedPrice",
      "notes",
    ],
    csv =
      "\uFEFF" +
      [
        cols.join(","),
        ...a.map((i) =>
          cols
            .map((c) => `"${String(i[c] ?? "").replaceAll('"', '""')}"`)
            .join(","),
        ),
      ].join("\n");
  download(new Blob([csv]), "khazina.csv");
};
$("clear").onclick = async () => {
  if (confirm("هل لديك نسخة احتياطية؟") && confirm("تأكيد الحذف؟")) {
    await clearDB();
    await refresh(true);
  }
};
window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  promptInstall = e;
  $("installBtn").hidden = false;
});
$("installBtn").onclick = async () => {
  promptInstall.prompt();
  await promptInstall.userChoice;
  $("installBtn").hidden = true;
};
if ("serviceWorker" in navigator)
  navigator.serviceWorker
    .getRegistrations()
    .then((rs) => rs.forEach((r) => r.unregister()));
migrateLocal()
  .then(() => refresh(true))
  .catch((e) => alert("تعذر فتح القاعدة المشتركة: " + e.message));
window.addEventListener("focus", () => {
  if (!mediaPicking) refresh(true);
});
document.addEventListener("visibilitychange", () => {
  if (!document.hidden && !mediaPicking) refresh(true);
});
setInterval(() => {
  if (!document.hidden && !mediaPicking) refresh(false);
}, 3000);
setInterval(() => {
  if (!document.hidden) {
    refreshParticipantBadge();
    if (document.getElementById("participants")?.classList.contains("active"))
      renderParticipants();
  }
}, 2000);
refreshParticipantBadge();
renderSerialFields([]);
updateInventoryQuantity();
updateAuctionUI();
function paintAdminAuctionClocks() {
  document.querySelectorAll(".auction-clock").forEach((x) => {
    x.textContent = auctionText(x.dataset.end) || "بدون وقت انتهاء";
    let d = new Date(x.dataset.end).getTime() - Date.now();
    x.classList.remove("clock-hour", "clock-ten", "clock-minute");
    if (d > 0 && d <= 60000) x.classList.add("clock-minute");
    else if (d > 0 && d <= 600000) x.classList.add("clock-ten");
    else if (d > 0 && d <= 3600000) x.classList.add("clock-hour");
  });
}
setInterval(() => {
  updateAuctionUI();
  paintAdminAuctionClocks();
}, 1000);

// V2.0 محرر صور محلي: تدوير + قص بإطار قابل للسحب قبل تثبيت الصورة.
const imageEditor = {
  which: null,
  work: null,
  crop: null,
  drag: null,
  display: { scale: 1, ox: 0, oy: 0 },
};
function editorCanvas() {
  return $("imageEditorCanvas");
}
function clamp(x, a, b) {
  return Math.max(a, Math.min(b, x));
}
function resetEditorCrop() {
  if (!imageEditor.work) return;
  imageEditor.crop = {
    x: 0,
    y: 0,
    w: imageEditor.work.width,
    h: imageEditor.work.height,
  };
  drawImageEditor();
}
function drawImageEditor() {
  let c = editorCanvas(),
    ctx = c.getContext("2d"),
    w = imageEditor.work;
  if (!w) return;
  let cssW = Math.max(300, Math.min(900, c.parentElement.clientWidth || 900)),
    cssH = Math.max(320, Math.min(560, Math.round(cssW * 0.62)));
  let dpr = Math.min(2, window.devicePixelRatio || 1);
  c.width = Math.round(cssW * dpr);
  c.height = Math.round(cssH * dpr);
  c.style.width = cssW + "px";
  c.style.height = cssH + "px";
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cssW, cssH);
  ctx.fillStyle = "#151918";
  ctx.fillRect(0, 0, cssW, cssH);
  let scale = Math.min((cssW - 20) / w.width, (cssH - 20) / w.height),
    dw = w.width * scale,
    dh = w.height * scale,
    ox = (cssW - dw) / 2,
    oy = (cssH - dh) / 2;
  imageEditor.display = { scale, ox, oy, cssW, cssH };
  ctx.drawImage(w, ox, oy, dw, dh);
  let r = imageEditor.crop || { x: 0, y: 0, w: w.width, h: w.height },
    rx = ox + r.x * scale,
    ry = oy + r.y * scale,
    rw = r.w * scale,
    rh = r.h * scale;
  ctx.save();
  ctx.fillStyle = "rgba(0,0,0,.5)";
  ctx.fillRect(0, 0, cssW, ry);
  ctx.fillRect(0, ry, rx, rh);
  ctx.fillRect(rx + rw, ry, cssW - (rx + rw), rh);
  ctx.fillRect(0, ry + rh, cssW, cssH - (ry + rh));
  ctx.strokeStyle = "#fff";
  ctx.lineWidth = 2;
  ctx.strokeRect(rx, ry, rw, rh);
  let hs = 12;
  ctx.fillStyle = "#fff";
  [
    [rx, ry],
    [rx + rw, ry],
    [rx, ry + rh],
    [rx + rw, ry + rh],
  ].forEach(([x, y]) => ctx.fillRect(x - hs / 2, y - hs / 2, hs, hs));
  ctx.restore();
}
function eventToImage(e) {
  let c = editorCanvas(),
    b = c.getBoundingClientRect(),
    d = imageEditor.display;
  return {
    x: (e.clientX - b.left - d.ox) / d.scale,
    y: (e.clientY - b.top - d.oy) / d.scale,
  };
}
function editorHit(p) {
  let r = imageEditor.crop,
    w = imageEditor.work,
    t = 24 / imageEditor.display.scale;
  if (!r || !w) return null;
  let near = (x, y) => Math.hypot(p.x - x, p.y - y) <= t;
  if (near(r.x, r.y)) return "tl";
  if (near(r.x + r.w, r.y)) return "tr";
  if (near(r.x, r.y + r.h)) return "bl";
  if (near(r.x + r.w, r.y + r.h)) return "br";
  if (p.x >= r.x && p.x <= r.x + r.w && p.y >= r.y && p.y <= r.y + r.h)
    return "move";
  return null;
}
function rotateWork(dir) {
  let src = imageEditor.work;
  if (!src) return;
  let out = document.createElement("canvas");
  out.width = src.height;
  out.height = src.width;
  let x = out.getContext("2d");
  x.translate(out.width / 2, out.height / 2);
  x.rotate((dir * Math.PI) / 2);
  x.drawImage(src, -src.width / 2, -src.height / 2);
  imageEditor.work = out;
  resetEditorCrop();
}
async function openImageEditor(which) {
  let src = which === "front" ? frontImg : backImg;
  if (!src) {
    alert("اختر صورة أولًا");
    return;
  }
  imageEditor.which = which;
  $("imageEditorStatus").textContent = "جارٍ فتح الصورة...";
  let im = new Image();
  im.onload = () => {
    let max = 2600,
      scale = Math.min(1, max / Math.max(im.naturalWidth, im.naturalHeight)),
      c = document.createElement("canvas");
    c.width = Math.max(1, Math.round(im.naturalWidth * scale));
    c.height = Math.max(1, Math.round(im.naturalHeight * scale));
    c.getContext("2d").drawImage(im, 0, 0, c.width, c.height);
    imageEditor.work = c;
    imageEditor.crop = { x: 0, y: 0, w: c.width, h: c.height };
    $("imageEditorDlg").showModal();
    $("imageEditorStatus").textContent =
      "حرّك الإطار لتحديد الجزء الذي تريد الاحتفاظ به.";
    setTimeout(drawImageEditor, 50);
  };
  im.onerror = () => alert("تعذر فتح الصورة للتعديل");
  im.src = src + "?edit=" + Date.now();
}
async function saveImageEditor() {
  let w = imageEditor.work,
    r = imageEditor.crop,
    st = $("imageEditorStatus");
  if (!w || !r) return;
  st.textContent = "جارٍ تثبيت الصورة المعدلة...";
  let out = document.createElement("canvas"),
    max = 2200,
    scale = Math.min(1, max / Math.max(r.w, r.h));
  out.width = Math.max(1, Math.round(r.w * scale));
  out.height = Math.max(1, Math.round(r.h * scale));
  out
    .getContext("2d")
    .drawImage(w, r.x, r.y, r.w, r.h, 0, 0, out.width, out.height);
  let blob = await new Promise((ok) => out.toBlob(ok, "image/jpeg", 0.9));
  if (!blob) {
    st.textContent = "تعذر تجهيز الصورة";
    return;
  }
  try {
    let url = await imgFile(blob);
    if (imageEditor.which === "front") frontImg = url;
    else backImg = url;
    if (imageEditor.which === "front") frontImageRemoved = false;
    else backImageRemoved = false;
    setPreview(imageEditor.which, url);
    st.textContent = "✅ تم تثبيت الصورة المعدلة.";
    setTimeout(() => $("imageEditorDlg").close(), 250);
  } catch (e) {
    st.textContent = "⚠️ " + e.message;
  }
}
if ($("editFrontImage"))
  $("editFrontImage").onclick = () => openImageEditor("front");
if ($("editBackImage"))
  $("editBackImage").onclick = () => openImageEditor("back");
if ($("clearFrontImage"))
  $("clearFrontImage").onclick = () => {
    frontImg = "";
    frontImageRemoved = true;
    setPreview("front", "");
    if ($("analysisStatus"))
      $("analysisStatus").textContent = "تمت إزالة صورة الوجه من النموذج.";
  };
if ($("clearBackImage"))
  $("clearBackImage").onclick = () => {
    backImg = "";
    backImageRemoved = true;
    setPreview("back", "");
    if ($("analysisStatus"))
      $("analysisStatus").textContent = "تمت إزالة صورة الخلف من النموذج.";
  };
if ($("closeImageEditor"))
  $("closeImageEditor").onclick = () => $("imageEditorDlg").close();
if ($("rotateImageLeft")) $("rotateImageLeft").onclick = () => rotateWork(-1);
if ($("rotateImageRight")) $("rotateImageRight").onclick = () => rotateWork(1);
if ($("resetImageCrop")) $("resetImageCrop").onclick = resetEditorCrop;
if ($("saveEditedImage")) $("saveEditedImage").onclick = saveImageEditor;
if (editorCanvas()) {
  let c = editorCanvas();
  c.onpointerdown = (e) => {
    if (!imageEditor.work) return;
    let p = eventToImage(e),
      mode = editorHit(p);
    if (!mode) return;
    let r = imageEditor.crop;
    imageEditor.drag = { mode, start: p, orig: { ...r } };
    c.setPointerCapture(e.pointerId);
  };
  c.onpointermove = (e) => {
    let d = imageEditor.drag,
      w = imageEditor.work;
    if (!d || !w) return;
    let p = eventToImage(e),
      dx = p.x - d.start.x,
      dy = p.y - d.start.y,
      o = d.orig,
      min = Math.max(30, Math.min(w.width, w.height) * 0.08),
      r = { ...o };
    if (d.mode === "move") {
      r.x = clamp(o.x + dx, 0, w.width - o.w);
      r.y = clamp(o.y + dy, 0, w.height - o.h);
    } else {
      let left = o.x,
        top = o.y,
        right = o.x + o.w,
        bottom = o.y + o.h;
      if (d.mode.includes("l")) left = clamp(o.x + dx, 0, right - min);
      if (d.mode.includes("r"))
        right = clamp(o.x + o.w + dx, left + min, w.width);
      if (d.mode.includes("t")) top = clamp(o.y + dy, 0, bottom - min);
      if (d.mode.includes("b"))
        bottom = clamp(o.y + o.h + dy, top + min, w.height);
      r = { x: left, y: top, w: right - left, h: bottom - top };
    }
    imageEditor.crop = r;
    drawImageEditor();
  };
  c.onpointerup = c.onpointercancel = () => (imageEditor.drag = null);
  window.addEventListener("resize", () => {
    if ($("imageEditorDlg")?.open) drawImageEditor();
  });
}

async function refreshDailyQr() {
  try {
    let r = await api("/api/daily-qr-info");
    let info = $("dailyQrInfo");
    if (info)
      info.textContent =
        "رمز ثابت للتصفح العام — لا تنتهي صلاحيته ولا يحتاج إلى تجديد يومي.";
    window.dailyAuctionUrl = r.url;
    let img = $("dailyQr");
    if (img && !img.src.includes("/api/daily-qr")) img.src = "/api/daily-qr";
  } catch (e) {}
}
if ($("copyDailyLink"))
  $("copyDailyLink").onclick = async () => {
    await refreshDailyQr();
    try {
      await navigator.clipboard.writeText(window.dailyAuctionUrl || "");
      alert("تم نسخ رابط التصفح العام");
    } catch (e) {
      prompt("انسخ الرابط:", window.dailyAuctionUrl || "");
    }
  };
if ($("printDailyQr"))
  $("printDailyQr").onclick = async () => {
    await refreshDailyQr();
    let w = window.open("", "_blank");
    w.document.write(
      `<html dir="rtl"><title>QR الدخول العام</title><body style="font-family:sans-serif;text-align:center;padding:30px"><h2>الدخول العام إلى المزادات</h2><img src="${location.origin}/api/daily-qr" style="width:360px"><p>${window.dailyAuctionUrl || ""}</p><script>setTimeout(()=>print(),500)<\/script></body></html>`,
    );
    w.document.close();
  };
refreshDailyQr();

// V3.5.2 — بطاقات QR عامة احترافية للسوق والمزاد
async function refreshVisitorQrLinks() {
  try {
    let [market, auction] = await Promise.all([
      api("/api/market-qr-info"),
      api("/api/daily-qr-info"),
    ]);
    window.marketVisitorUrl = market.url || "";
    window.auctionVisitorUrl = auction.url || "";
  } catch (e) {}
}
async function copyVisitorLink(kind) {
  await refreshVisitorQrLinks();
  let url =
    kind === "market"
      ? window.marketVisitorUrl || ""
      : window.auctionVisitorUrl || "";
  try {
    await navigator.clipboard.writeText(url);
    alert("تم نسخ رابط الدخول العام");
  } catch (e) {
    prompt("انسخ الرابط:", url);
  }
}
function visitorPrintHtml(kind, url) {
  let market = kind === "market";
  let title = market ? "الدخول إلى السوق العام" : "الدخول إلى المزادات";
  let subtitle = market
    ? "بيع وشراء العملات والمقتنيات النادرة"
    : "تصفح المزادات والمشاركة بعد التوثيق والاعتماد";
  let qr = market ? "/api/market-qr" : "/api/daily-qr";
  return `<html dir="rtl"><head><meta charset="utf-8"><title>${title} — نوادر العملات</title><style>*{box-sizing:border-box}body{margin:0;background:#eef2f6;font-family:Tahoma,Arial,sans-serif;color:#071b35;padding:24px}.pass{width:620px;max-width:100%;margin:auto;background:#fff;border:3px solid #c89b3c;border-radius:28px;overflow:hidden;text-align:center}.brand{background:#071b35;color:#fff;padding:22px;display:flex;align-items:center;justify-content:center;gap:16px}.brand img{width:82px;height:82px;border-radius:50%;object-fit:cover;border:3px solid #e7c878}.brand b{display:block;color:#e7c878;font-size:30px}.brand span{font-size:18px}.content{padding:28px}.content h1{margin:0 0 8px;font-size:32px}.content p{font-size:18px;color:#46566e}.qr{width:360px;height:360px;max-width:86%;margin:20px auto;border:10px solid #071b35;outline:3px solid #c89b3c;border-radius:22px;padding:12px;background:#fff}.qr img{width:100%;height:100%;object-fit:contain}.hint{font-weight:800;color:#071b35}.url{font-size:12px;direction:ltr;word-break:break-all;color:#6a7381;margin-top:18px}@media print{body{background:#fff;padding:0}.pass{box-shadow:none;break-inside:avoid}}</style></head><body><section class="pass"><div class="brand"><img src="${location.origin}/assets/nawader-logo.jpg"><div><b>نوادر العملات</b><span>${subtitle}</span></div></div><div class="content"><h1>${title}</h1><div class="qr"><img src="${location.origin}${qr}"></div><p class="hint">امسح الرمز للدخول مباشرة</p><p class="url">${url || ""}</p></div></section><script>setTimeout(()=>print(),700)<\/script></body></html>`;
}
async function printVisitorQr(kind) {
  await refreshVisitorQrLinks();
  let url =
    kind === "market"
      ? window.marketVisitorUrl || ""
      : window.auctionVisitorUrl || "";
  let w = window.open("", "_blank");
  if (!w) return;
  w.document.write(visitorPrintHtml(kind, url));
  w.document.close();
}
if ($("copyMarketVisitorLink"))
  $("copyMarketVisitorLink").onclick = () => copyVisitorLink("market");
if ($("copyAuctionVisitorLink"))
  $("copyAuctionVisitorLink").onclick = () => copyVisitorLink("auction");
if ($("printMarketVisitorQr"))
  $("printMarketVisitorQr").onclick = () => printVisitorQr("market");
if ($("printAuctionVisitorQr"))
  $("printAuctionVisitorQr").onclick = () => printVisitorQr("auction");
refreshVisitorQrLinks();

window.openAuctionException = async (id) => {
  let i = (await all()).find((x) => String(x.id) === String(id));
  if (!i) return;
  $("auctionExceptionItemId").value = id;
  $("auctionExceptionReason").value = "non_payment";
  $("auctionExceptionNote").value = "";
  $("auctionExceptionStatus").textContent =
    "سيبقى سجل الجولة والفائز محفوظين، ويُفتح المقتنى لإعادة الإدراج فقط بعد اعتماد الاستثناء.";
  $("auctionExceptionDlg").showModal();
};
if ($("closeAuctionException"))
  $("closeAuctionException").onclick = () => $("auctionExceptionDlg").close();
if ($("auctionExceptionForm"))
  $("auctionExceptionForm").onsubmit = async (ev) => {
    ev.preventDefault();
    let reason = $("auctionExceptionReason").value,
      note = $("auctionExceptionNote").value.trim(),
      st = $("auctionExceptionStatus"),
      btn = ev.submitter;
    if (reason === "other" && !note) {
      st.textContent = "اكتب سبب الاستثناء عند اختيار «سبب آخر».";
      return;
    }
    try {
      if (btn) btn.disabled = true;
      st.textContent = "جارٍ اعتماد الاستثناء وتوثيق العملية...";
      await api("/api/auction/exception", {
        method: "POST",
        body: JSON.stringify({
          id: $("auctionExceptionItemId").value,
          reason,
          note,
        }),
      });
      st.textContent = "✓ تم اعتماد الاستثناء وحفظه في سجل المزاد.";
      lastDataToken = "";
      await refresh(true);
      await renderEndedAuctions();
      setTimeout(() => $("auctionExceptionDlg").close(), 650);
    } catch (e) {
      st.textContent = e.message || "تعذر اعتماد الاستثناء.";
    } finally {
      if (btn) btn.disabled = false;
    }
  };

// تعديل شامل وسريع للجولة النشطة: الوقت، حد البيع، الزيادة، وسعر الافتتاح قبل أول مزايدة.
window.cancelActiveAuction = async (id) => {
  try {
    const rows = await all(), item = rows.find(x => String(x.id) === String(id));
    if (!item) throw new Error("المزاد غير موجود");
    if (auctionText(item.auctionEnd) === "انتهى المزاد") throw new Error("المزاد منتهٍ بالفعل");
    const bids = await api(`/api/bids?itemId=${encodeURIComponent(id)}`);
    const round = Number(item.auctionRound || 1);
    const roundBids = (Array.isArray(bids) ? bids : (bids?.bids || [])).filter(b => String(b.itemId) === String(id) && Number(b.auctionRound || 1) === round);
    let reason = "إلغاء إداري قبل وجود مزايدات";
    if (roundBids.length) {
      reason = prompt(`يوجد ${roundBids.length} مزايدة في هذه الجولة. اكتب سبب إلغاء المزاد ليُحفظ ويُبلّغ به المزايدون:`) || "";
      if (!reason.trim()) return;
      if (!confirm("سيتم إلغاء المزاد وإشعار المزايدين وإعادة المقتنى للمستودع. هل تعتمد الإلغاء؟")) return;
    } else if (!confirm("إلغاء هذا المزاد وإعادة المقتنى إلى المستودع؟")) return;
    const r = await api("/api/auction/cancel", {method:"POST", body:JSON.stringify({id, reason:reason.trim()})});
    if (!r?.ok) throw new Error(r?.error || "تعذر إلغاء المزاد");
    await refresh(true);
    alert("تم إلغاء المزاد وإعادة المقتنى إلى المستودع مع حفظ سجل الإلغاء.");
  } catch(e) { alert("تعذر إلغاء المزاد: " + e.message); }
};

window.openAuctionQuickEdit = async (id) => {
  try {
    let i = (await all()).find((x) => String(x.id) === String(id));
    if (!i) return;
    let br = await api("/api/bids"),
      round = Number(i.auctionRound || 1),
      bids = (br.bids || []).filter((b) => String(b.itemId) === String(id) && Number(b.auctionRound || 1) === round),
      hasBids = bids.length > 0,
      current = Math.max(...bids.map((b) => Number(b.amount || 0)), Number(i.auctionCurrentPrice || 0), 0);
    $("auctionQuickEditItemId").value = id;
    $("auctionQuickEditEnd").value = i.auctionEnd ? localDateTimeValue(new Date(i.auctionEnd)) : localDateTimeValue(new Date(Date.now() + 24*60*60*1000));
    $("auctionQuickEditOpening").value = Number(i.auctionOpeningPrice || i.auctionStartPrice || 0);
    $("auctionQuickEditStep").value = Number(i.auctionBidStep || 1);
    $("auctionQuickEditTarget").value = Number(i.auctionTargetPrice || (Number(i.auctionStartPrice || 0) + 1));
    $("auctionQuickEditCurrent").value = money(current);
    $("auctionQuickEditTerms").value = i.auctionAdditionalTerms || "";
    $("auctionQuickEditOpening").disabled = hasBids;
    $("auctionQuickEditOpening").title = hasBids ? "لا يمكن تغيير سعر الافتتاح بعد تسجيل أول مزايدة" : "";
    $("auctionQuickEditHint").textContent = hasBids
      ? `يوجد ${bids.length} مزايدة في الجولة الحالية. تم قفل سعر الافتتاح، ويمكن تصحيح الوقت وحد البيع وقيمة الزيادة. سيُسجل التعديل ويُنبه المزايدون.`
      : "لا توجد مزايدات حتى الآن؛ يمكن تعديل جميع إعدادات المزاد.";
    $("auctionQuickEditStatus").textContent = "";
    $("auctionQuickEditDlg").showModal();
  } catch (e) { alert("تعذر فتح تعديل المزاد: " + e.message); }
};
if ($("closeAuctionQuickEdit")) $("closeAuctionQuickEdit").onclick = () => $("auctionQuickEditDlg").close();
if ($("auctionQuickEditToday")) $("auctionQuickEditToday").onclick = () => {
  let d = new Date(); d.setHours(23,59,0,0);
  if (d <= new Date()) d = new Date(Date.now()+60*60*1000);
  $("auctionQuickEditEnd").value = localDateTimeValue(d);
};
if ($("confirmAuctionQuickEdit")) $("confirmAuctionQuickEdit").onclick = async () => {
  let btn=$("confirmAuctionQuickEdit"), st=$("auctionQuickEditStatus");
  try {
    btn.disabled=true; st.textContent="جارٍ حفظ تعديل المزاد...";
    let payload={
      id: $("auctionQuickEditItemId").value,
      auctionEnd: $("auctionQuickEditEnd").value,
      auctionBidStep: Number($("auctionQuickEditStep").value || 0),
      auctionTargetPrice: Number($("auctionQuickEditTarget").value || 0),
      auctionAdditionalTerms: $("auctionQuickEditTerms").value.trim()
    };
    if (!$("auctionQuickEditOpening").disabled) payload.auctionOpeningPrice=Number($("auctionQuickEditOpening").value || 0);
    let r=await api("/api/auction/quick-edit",{method:"POST",body:JSON.stringify(payload)});
    st.textContent = `✅ تم حفظ التعديل${r.bidCount ? ` وإشعار ${r.notifiedCount || 0} من المزايدين` : ""}.`;
    await refresh(true);
    setTimeout(()=>$("auctionQuickEditDlg").close(),650);
  } catch(e) { st.textContent="⚠️ "+e.message; }
  finally { btn.disabled=false; }
};

// V2.1 إعادة المزاد: جولة مستقلة تحفظ سجل الجولة السابقة ولا تخلط مزايداتها بالجولة الجديدة.
function localDateTimeValue(d) {
  let z = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}T${z(d.getHours())}:${z(d.getMinutes())}`;
}
window.openRelaunch = async (id) => {
  let i = (await all()).find((x) => String(x.id) === String(id));
  if (!i) return;
  $("relaunchItemId").value = id;
  $("relaunchOpening").value = Number(
    i.auctionOpeningPrice || i.auctionStartPrice || 0,
  );
  $("relaunchStep").value = Number(i.auctionBidStep || 1);
  $("relaunchTarget").value = Number(
    i.auctionTargetPrice || Number(i.auctionStartPrice || 0) + 1,
  );
  let d = new Date(Date.now() + 24 * 60 * 60 * 1000);
  $("relaunchEnd").value = localDateTimeValue(d);
  $("relaunchStatus").textContent =
    `الجولة الحالية ${Number(i.auctionRound || 1)}. عند الاعتماد ستبدأ جولة جديدة مستقلة.`;
  $("relaunchDlg").showModal();
};
if ($("closeRelaunch"))
  $("closeRelaunch").onclick = () => $("relaunchDlg").close();
if ($("relaunchToday"))
  $("relaunchToday").onclick = () => {
    let d = new Date();
    d.setHours(23, 59, 0, 0);
    if (d <= new Date()) d = new Date(Date.now() + 60 * 60 * 1000);
    $("relaunchEnd").value = localDateTimeValue(d);
  };
if ($("confirmRelaunch"))
  $("confirmRelaunch").onclick = async () => {
    let btn = $("confirmRelaunch"),
      st = $("relaunchStatus");
    try {
      btn.disabled = true;
      st.textContent = "جارٍ إنشاء جولة المزاد الجديدة...";
      let d = await api("/api/auction/relaunch", {
        method: "POST",
        body: JSON.stringify({
          id: $("relaunchItemId").value,
          auctionEnd: $("relaunchEnd").value,
          auctionOpeningPrice: Number($("relaunchOpening").value || 0),
          auctionBidStep: Number($("relaunchStep").value || 1),
          auctionTargetPrice: Number($("relaunchTarget").value || 0),
          auctionApproved: true,
        }),
      });
      st.textContent = `✅ تم اعتماد الجولة ${d.auctionRound} ونشرها تلقائيًا.`;
      await refresh(true);
      setTimeout(() => $("relaunchDlg").close(), 500);
    } catch (e) {
      st.textContent = "⚠️ " + e.message;
    } finally {
      btn.disabled = false;
    }
  };

// V2.7 السوق العام والبيع المباشر
function updateMarketUI() {
  if (!$("marketFields")) return;
  let on = !!$("forMarket")?.checked;
  $("marketFields").hidden = !on;
  let type = $("marketOfferType")?.value || "single",
    pu = $("marketPriceUnit")?.value || "";
  if (
    !pu ||
    (type === "set" && pu !== "set" && pu !== "piece" && pu !== "sheet") ||
    (type === "single" && pu !== "piece" && pu !== "sheet") ||
    (type === "bundle" && pu !== "bundle" && pu !== "piece" && pu !== "sheet")
  ) {
    pu = type === "set" ? "set" : type === "bundle" ? "bundle" : "piece";
    if ($("marketPriceUnit")) $("marketPriceUnit").value = pu;
  }
  if ($("marketSetPiecesWrap"))
    $("marketSetPiecesWrap").hidden = !(type === "set" || type === "bundle");
  if ($("marketSetSizeWrap")) $("marketSetSizeWrap").hidden = type !== "set";
  if ($("marketSetCurrencyModeWrap"))
    $("marketSetCurrencyModeWrap").hidden = type !== "set";
  if ($("marketPartialWrap")) $("marketPartialWrap").hidden = type !== "bundle";
  let unitLabel =
    pu === "set"
      ? "الطقم"
      : pu === "bundle"
        ? "الحزمة / البندل"
        : pu === "sheet"
          ? "الورقة"
          : "القطعة";
  if ($("marketSalePriceLabel"))
    $("marketSalePriceLabel").textContent = "سعر " + unitLabel;
  if ($("marketQuantityLabel"))
    $("marketQuantityLabel").textContent =
      "عدد " +
      (type === "set"
        ? "الأطقم"
        : type === "bundle"
          ? "الحزم / البندلات"
          : pu === "sheet"
            ? "الأوراق"
            : "القطع") +
      " المعروضة";
  if ($("marketPiecesLabel"))
    $("marketPiecesLabel").textContent =
      type === "set"
        ? "عدد أوراق / قطع كل طقم"
        : "عدد القطع / الأوراق داخل كل حزمة";
  let q = Math.max(1, Number($("marketQuantity")?.value || 1)),
    pieces = Math.max(1, Number($("marketSetPieces")?.value || 1)),
    price = Number($("marketSalePrice")?.value || 0);
  if ($("marketExample"))
    $("marketExample").textContent =
      type === "set"
        ? `مثال العرض الحالي: ${q} طقم متاح × ${pieces} ورقة/قطعة في كل طقم × سعر الطقم ${price || 0} ر.س.`
        : type === "bundle"
          ? `مثال العرض الحالي: ${q} حزمة متاحة × ${pieces} قطعة/ورقة داخل الحزمة × سعر ${unitLabel} ${price || 0} ر.س.`
          : `مثال العرض الحالي: ${q} ${pu === "sheet" ? "ورقة" : "قطعة"} متاحة × سعر ${unitLabel} ${price || 0} ر.س.`;
  if ($("marketUnitPrice")) $("marketUnitPrice").value = price || 0;
}
function marketTypeLabel(t) {
  return t === "bundle" ? "حزمة / بندل" : t === "set" ? "طقم" : "قطعة واحدة";
}
function marketCategoryKey(c){return ["banknote","coin","set",null,undefined,""] .includes(c)?"coins-stamps":c}
function marketCategoryLabel(c){return ({"coins-stamps":"العملات والطوابع",collectibles:"المقتنيات",games:"الألعاب",tcg:"TCG",diecast:"دايكاست",lamps:"مصابيح",fantasia:"فانتازيا",special:"أرقام مميزة وأخطاء نادرة",transitional:"إصدارات انتقالية",other:"أخرى"})[marketCategoryKey(c)]||"العملات والطوابع"}
function marketAdminCard(i) {
  let qty = Number(i.marketQuantity || i.quantity || 1),
    sold = Number(i.marketSoldQuantity || 0),
    left = Math.max(0, qty - sold),
    price = Number(i.marketSalePrice || i.marketUnitPrice || 0),
    pu =
      i.marketPriceUnit ||
      (i.marketOfferType === "set"
        ? "set"
        : i.marketOfferType === "bundle"
          ? "bundle"
          : "piece"),
    ul =
      pu === "set"
        ? "الطقم"
        : pu === "bundle"
          ? "الحزمة"
          : pu === "sheet"
            ? "الورقة"
            : "القطعة",
    imgs = [
      i.frontImg,
      i.backImg,
      i.gradingCertImage,
      ...(i.additionalImages || []),
    ].filter(Boolean),
    title = i.marketTitle || `${i.country} — ${i.denomination}`;
  return `<article class="item market-admin-card">${i.frontImg ? `<button type="button" class="market-image-button" onclick='openCoinLightbox(${JSON.stringify(imgs)},0,${JSON.stringify(title)})' title="فتح عارض الصور"><img src="${i.frontImg}" alt="${esc(title)}"><span class="market-image-hint">⛶ تكبير الصور</span></button>` : '<div class="market-image-button market-no-photo">لا توجد صورة</div>'}<div class="market-admin-body"><h3>${esc(title)} ${transitionalBadge(i)}</h3><p class="market-status-row"><span class="badge market-badge">${marketCategoryLabel(i.marketCategory)}</span> <span class="badge market-badge">${marketTypeLabel(i.marketOfferType)}</span> <span class="approval-chip ${i.marketApproved ? "ok" : "bad"}">${i.marketApproved ? "نشط" : "غير نشط"}</span></p><div class="market-admin-metrics"><b>سعر ${ul}: ${money(price)}</b><span>المتاح ${left} من ${qty} ${i.marketOfferType === "set" ? "طقم" : i.marketOfferType === "bundle" ? "حزمة" : "وحدة"}</span>${i.marketSetPieces ? `<span>داخل الوحدة ${Number(i.marketSetPieces)} قطعة/ورقة</span>` : ""}</div><p class="market-negotiation">${i.marketNegotiationEnabled ? `التفاوض حتى ${Number(i.marketNegotiationPercent || 0)}%` : "سعر ثابت"}</p><div class="actions market-admin-actions">${imgs.length ? `<button class="ghost" onclick='openCoinLightbox(${JSON.stringify(imgs)},0,${JSON.stringify(title)})'>⛶ الصور</button>` : ""}<button onclick="editItem('${i.id}')">تعديل</button>${archiveButton(i.id)}${adminMoveButtons(i,"market")}<a class="public-link" href="/market${itemStoreQuery(i)}#${i.id}" target="_blank">عرض في السوق</a></div></div></article>`;
}
function marketStatusLabel(st) {
  return st === "accepted"
    ? "مقبول"
    : st === "shipped"
      ? "تم الشحن"
      : st === "completed"
        ? "مكتمل"
        : st === "rejected"
          ? "مرفوض"
          : "بانتظار المراجعة";
}
function marketStatusClass(st) {
  return st === "accepted" || st === "completed"
    ? "ok"
    : st === "rejected"
      ? "bad"
      : "wait";
}

function marketSearchFields(i) {
  const classification = effectiveClassification(i);
  const grading = effectiveGradingStatus(i);
  const serials = Array.isArray(i.serials) ? i.serials : [];
  const classAliases = classification === "set"
    ? "طقم اطقم مجموعه مجموعة set sets"
    : grading === "graded"
      ? "مقيم مقيمه مقيمة تقييم معتمد graded"
      : "غير مقيم غير مقيمه غير مقيمة بدون تقييم غير معتمد ungraded";
  const statusAliases = i.marketApproved ? "نشط معتمد منشور active approved" : "غير نشط غير معتمد غير منشور inactive";
  const offerAliases = i.marketOfferType === "set"
    ? "طقم set"
    : i.marketOfferType === "bundle"
      ? "حزمه حزمة بندل bundle"
      : "قطعه قطعة مفرد single piece";
  return {
    country: warehouseFieldText(i.country),
    denomination: warehouseFieldText([i.denomination, i.currencyName, i.marketTitle]),
    year: warehouseFieldText(i.year),
    classification: warehouseFieldText(classAliases),
    issue: warehouseFieldText([i.issueEdition, i.issue, i.type]),
    condition: warehouseFieldText(i.condition),
    gradingCompany: warehouseFieldText(i.gradingCompany),
    grade: warehouseFieldText([i.gradeValue, i.gradePercent, i.gradingVerificationStatus]),
    certificate: warehouseFieldText(i.gradingCertNumber),
    serial: warehouseFieldText([i.serial, ...serials]),
    id: warehouseFieldText(i.id),
    location: warehouseFieldText([i.warehouse, i.cabinet, i.shelf, i.box, i.album, i.page, i.pocket]),
    title: warehouseFieldText(i.marketTitle),
    category: warehouseFieldText(i.marketCategory),
    price: warehouseFieldText([i.marketSalePrice, i.marketUnitPrice]),
    quantity: warehouseFieldText([i.marketQuantity, i.quantity, i.marketSetPieces]),
    offerType: warehouseFieldText(offerAliases),
    status: warehouseFieldText(statusAliases),
    negotiation: warehouseFieldText([i.marketNegotiationEnabled ? "تفاوض قابل للتفاوض" : "سعر ثابت بدون تفاوض", i.marketNegotiationPercent]),
    notes: warehouseFieldText([i.gradingNotes, i.notes])
  };
}
function marketQueryParts(query) {
  const filters = {};
  const fieldMap = {
    "الدوله":"country", "بلد":"country",
    "الفئه":"denomination", "العمله":"denomination", "العنوان":"title",
    "السنه":"year", "الاصدار":"issue",
    "التقييم":"grade", "درجه":"grade",
    "الشركه":"gradingCompany", "جهه":"gradingCompany",
    "الشهاده":"certificate",
    "الرقم":"serial", "التسلسلي":"serial",
    "الموقع":"location", "التخزين":"location",
    "السعر":"price", "الكميه":"quantity",
    "العرض":"offerType", "النوع":"offerType",
    "الحاله":"status", "التفاوض":"negotiation"
  };
  let freeRaw = String(query ?? "").replace(/([^\s:：]+)\s*[:：]\s*("[^"]+"|'[^']+'|[^\s]+)/g, (whole, key, value) => {
    const mapped = fieldMap[normalizeWarehouseText(key)];
    if (!mapped) return whole;
    filters[mapped] = normalizeWarehouseText(String(value).replace(/^['"]|['"]$/g, ""));
    return " ";
  });
  let q = normalizeWarehouseText(freeRaw);
  const aliases = [
    { re: /(^| )غير مقيم(?:ه)?(?= |$)/g, key: "classification", value: "ungraded" },
    { re: /(^| )بدون تقييم(?= |$)/g, key: "classification", value: "ungraded" },
    { re: /(^| )مقيم(?:ه)?(?= |$)/g, key: "classification", value: "graded" },
    { re: /(^| )طقم(?= |$)/g, key: "classification", value: "set" },
    { re: /(^| )اطقم(?= |$)/g, key: "classification", value: "set" },
    { re: /(^| )غير نشط(?= |$)/g, key: "status", value: "غير نشط" },
    { re: /(^| )نشط(?= |$)/g, key: "status", value: "نشط" }
  ];
  aliases.forEach(({re,key,value}) => {
    if (re.test(q)) {
      filters[key] = value;
      q = q.replace(re, " ");
    }
    re.lastIndex = 0;
  });
  return { terms: q.split(" ").map(v => v.trim()).filter(Boolean), filters };
}
function marketSmartMatch(i, query) {
  if (!String(query || "").trim()) return true;
  const { terms, filters } = marketQueryParts(query);
  const fields = marketSearchFields(i);
  const classification = effectiveClassification(i);
  const grading = effectiveGradingStatus(i);
  if (filters.classification === "set" && classification !== "set") return false;
  if (filters.classification === "graded" && (classification === "set" || grading !== "graded")) return false;
  if (filters.classification === "ungraded" && (classification === "set" || grading !== "ungraded")) return false;
  for (const [key, value] of Object.entries(filters)) {
    if (key === "classification" || !value) continue;
    if (!(fields[key] || "").includes(normalizeWarehouseText(value))) return false;
  }
  const allText = Object.values(fields).join(" ");
  return terms.every(term => allText.includes(term));
}

async function renderMarketAdmin(items) {
  if (!$("marketAdminItems")) return;
  let a = Array.isArray(items) ? items : await all(),
    m = a.filter((i) => i.forMarket),
    map = Object.fromEntries(a.map((i) => [String(i.id), i])),
    marketQuery = $("marketSearch")?.value || "",
    categoryFilter = $("marketCategoryFilter")?.value || "all";
  $("marketPublishedCount").textContent = m.filter(
    (i) => i.marketApproved,
  ).length;
  $("marketAdminItems").innerHTML =
    m
      .filter((i) => classMatch(i, marketFilter, marketSetFilter))
      .filter((i) => categoryFilter==="all"||marketCategoryKey(i.marketCategory)===categoryFilter)
      .filter((i) => marketSmartMatch(i, marketQuery))
      .map(marketAdminCard)
      .join("") || "<p>لا توجد مقتنيات في هذا التصنيف.</p>";
  try {
    let r = await api("/api/market/requests"),
      req = r.requests || [];
    $("marketRequestsCount").textContent = req.length;
    $("marketPendingCount").textContent = req.filter(
      (x) => x.status === "pending",
    ).length;
    if ($("dashboardMarketPending"))
      $("dashboardMarketPending").textContent = req.filter(
        (x) => x.status === "pending",
      ).length;
    $("marketRequests").innerHTML =
      req
        .map((x) => {
          let it = map[String(x.itemId)] || {},
            title =
              x.itemTitle ||
              it.marketTitle ||
              `${it.country || ""} — ${it.denomination || ""}`,
            owner = x.ownerName || it.ownerName || "الإدارة / غير محدد",
            listed = Number(x.listedAmount || 0),
            offered = Number(x.offeredAmount || 0),
            action = x.action === "offer" ? "عرض تفاوض" : "طلب شراء",
            imgs = [
              ...(x.images || []),
              it.frontImg,
              it.backImg,
              it.gradingCertImage,
              ...(it.additionalImages || []),
            ].filter(Boolean),
            thumb = imgs[0] || "";
          return `<div class="market-request-card ${x.status === "rejected" ? "request-rejected" : ""}">${thumb ? `<div class="market-request-image"><img src="${esc(thumb)}" alt="${esc(title)}" onclick='openCoinLightbox(${JSON.stringify(imgs)},0,${JSON.stringify(title)})'></div>` : `<div class="market-request-image no-request-image">لا توجد صورة</div>`}<div class="market-request-main"><div class="market-request-title"><b>${esc(title)}</b> <span class="status-ar ${marketStatusClass(x.status)}">${marketStatusLabel(x.status)}</span></div><div class="market-request-meta"><span>البائع / المالك: <b>${esc(owner)}</b></span><span>المشتري: <b>${esc(x.name)}</b> — ${esc(x.phone)}</span><span>نوع الطلب: <b>${action}</b></span><span>الكمية: <b>${Number(x.quantity || 1)}</b></span><span>السعر المعلن: <b>${money(listed)}</b></span><span class="market-request-money">${x.action === "offer" ? "عرض العميل" : "قيمة الطلب"}: ${money(offered)}</span><span>رسوم المشتري: <b>${money(Number(x.buyerFeeAmount || 0))}</b> (${Number(x.buyerFeePercent || 0)}%)</span><span>إجمالي المطلوب من المشتري: <b>${money(Number(x.buyerTotal || offered))}</b></span><span>التاريخ: ${new Date(x.created).toLocaleString("ar-SA")}</span></div></div><div class="actions"><button onclick="marketRequestStatus('${x.id}','accepted')">قبول</button><button class="ghost" onclick="marketRequestShip('${x.id}')">تم الشحن</button><button class="danger" onclick="marketRequestStatus('${x.id}','rejected')">رفض</button></div></div>`;
        })
        .join("") || "<p>لا توجد طلبات شراء أو تفاوض حتى الآن.</p>";
  } catch (e) {
    console.warn(e);
  }
}
window.marketRequestShip = async (id) => {
  let shippingCompany = prompt("اسم شركة التوصيل (اختياري):", "") || "",
    trackingNumber = prompt("رقم التتبع (اختياري):", "") || "";
  try {
    await api("/api/market/request/respond", {
      method: "POST",
      body: JSON.stringify({
        id,
        status: "shipped",
        shippingCompany,
        trackingNumber,
      }),
    });
    await renderMarketAdmin();
  } catch (e) {
    alert(e.message);
  }
};
window.marketRequestStatus = async (id, status) => {
  try {
    await api("/api/market/request/respond", {
      method: "POST",
      body: JSON.stringify({ id, status }),
    });
    await renderMarketAdmin();
  } catch (e) {
    alert(e.message);
  }
};
async function renderFinance() {
  if (!$("finCapital")) return;
  let st = $("financeRefreshState");
  try {
    if (st) st.textContent = "جارٍ تحديث المؤشرات...";
    let [items, reqData, subData, settings] = await Promise.all([
      all(),
      api("/api/market/requests"),
      api("/api/subscriptions"),
      api("/api/settings/public"),
    ]);
    let req = reqData.requests || [],
      subs = subData.subscriptions || [];
    let completed = req.filter((x) => x.status === "completed");
    let totalCapital = 0,
      remainingCapital = 0,
      soldUnits = 0;
    for (let i of items) {
      let qty = Number(i.quantity || 0),
        sold = Math.min(qty, Number(i.soldQuantity || 0)),
        unitCost =
          Number(i.purchase || 0) +
          Number(i.shipping || 0) +
          Number(i.other || 0);
      totalCapital += unitCost * qty;
      remainingCapital += unitCost * Math.max(0, qty - sold);
      soldUnits += sold;
    }
    let completedSales = completed.reduce(
      (s, x) => s + Number(x.offeredAmount || 0),
      0,
    );
    let costSold = 0;
    for (let x of completed) {
      let i = items.find((z) => String(z.id) === String(x.itemId));
      if (i)
        costSold +=
          (Number(i.purchase || 0) +
            Number(i.shipping || 0) +
            Number(i.other || 0)) *
          Number(x.quantity || 1);
    }
    let estimatedProfit = completedSales - costSold,
      buyerFee = Number(settings.buyerFeePercent || 2.5),
      platformIncome = (completedSales * buyerFee) / 100;
    let sums = { daily: 0, seasonal: 0, package: 0 };
    for (let x of subs)
      if (sums[x.type] !== undefined) sums[x.type] += Number(x.amount || 0);
    $("finCapital").textContent = money(totalCapital);
    $("finRemainingCapital").textContent = money(remainingCapital);
    $("finSoldUnits").textContent = soldUnits.toLocaleString("ar-SA");
    $("finCompletedSales").textContent = money(completedSales);
    $("finEstimatedProfit").textContent = money(estimatedProfit);
    $("finPlatformIncome").textContent = money(platformIncome);
    $("finDailySubs").textContent = money(sums.daily);
    $("finSeasonSubs").textContent = money(sums.seasonal);
    $("finPackageSubs").textContent = money(sums.package);
    let subsTotal = sums.daily + sums.seasonal + sums.package;
    $("finSubsTotal").textContent = money(subsTotal);
    let grossPlatformProfit = estimatedProfit + platformIncome + subsTotal,
      charityPct = Number(settings.charityProfitPercent || 0),
      charityAmount = (Math.max(0, grossPlatformProfit) * charityPct) / 100,
      netPlatformProfit = grossPlatformProfit - charityAmount;
    if ($("finGrossProfit"))
      $("finGrossProfit").textContent = money(grossPlatformProfit);
    if ($("finCharityPct")) $("finCharityPct").textContent = charityPct + "%";
    if ($("finCharityAmount"))
      $("finCharityAmount").textContent = money(charityAmount);
    if ($("finNetProfit"))
      $("finNetProfit").textContent = money(netPlatformProfit);
    if ($("finNetProfitStrip"))
      $("finNetProfitStrip").classList.toggle(
        "negative",
        netPlatformProfit < 0,
      );
    if ($("finNetProfitNote"))
      $("finNetProfitNote").textContent =
        "بعد خصم مخصص الأعمال الخيرية " +
        charityPct +
        "% (" +
        money(charityAmount) +
        ")";
    $("subscriptionList").innerHTML =
      subs
        .slice()
        .reverse()
        .map(
          (x) =>
            `<div class="subscription-row"><b>${x.type === "daily" ? "اشتراك يومي" : x.type === "seasonal" ? "اشتراك موسمي" : "باقة"}</b> — ${money(x.amount)} ${x.customer ? `• ${esc(x.customer)}` : ""}<br><span class="muted">${esc(x.note || "")} ${x.created ? "• " + new Date(x.created).toLocaleString("ar-SA") : ""}</span></div>`,
        )
        .join("") || '<p class="muted">لا توجد اشتراكات مسجلة بعد.</p>';
    if (st)
      st.textContent =
        "تم تحديث المالية • " +
        new Date().toLocaleTimeString("ar-SA", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        });
  } catch (e) {
    if (st) st.textContent = "تعذر تحديث المالية: " + e.message;
    console.warn("تعذر تحميل اللوحة المالية", e);
    throw e;
  }
}
if ($("refreshFinance"))
  $("refreshFinance").onclick = async () => {
    let b = $("refreshFinance");
    if (b.disabled) return;
    b.disabled = true;
    let old = b.textContent;
    b.textContent = "↻ جارٍ التحديث...";
    try {
      await renderFinance();
    } catch (e) {
      alert("تعذر تحديث المالية: " + e.message);
    } finally {
      b.disabled = false;
      b.textContent = old;
    }
  };
if ($("addSubscription"))
  $("addSubscription").onclick = async () => {
    try {
      let amount = n("subAmount");
      if (amount <= 0) {
        alert("أدخل مبلغ الاشتراك");
        return;
      }
      await api("/api/subscription/add", {
        method: "POST",
        body: JSON.stringify({
          type: v("subType"),
          customer: v("subCustomer"),
          amount,
          note: v("subNote"),
        }),
      });
      $("subCustomer").value = "";
      $("subAmount").value = "";
      $("subNote").value = "";
      await renderFinance();
    } catch (e) {
      alert(e.message);
    }
  };
try {
  updateMarketUI();
} catch (e) {}

try {
  updateEditionUI();
  updateYearUI();
  updateGradingUI();
  updateMarketUI();
} catch (e) {}

if ($("refreshEndedAuctions"))
  $("refreshEndedAuctions").onclick = async () => {
    let b = $("refreshEndedAuctions");
    if (b.disabled) return;
    b.disabled = true;
    let old = b.textContent;
    b.textContent = "↻ جارٍ التحديث...";
    try {
      lastDataToken = "";
      let a = await all();
      await renderEndedAuctions(a);
      b.textContent = "✓ تم التحديث";
      setTimeout(() => {
        if (b) b.textContent = old;
      }, 900);
    } catch (e) {
      alert("تعذر تحديث المزادات المنتهية: " + e.message);
      b.textContent = old;
    } finally {
      b.disabled = false;
    }
  };
if ($("endedAuctionSearch"))
  $("endedAuctionSearch").oninput = () => renderEndedAuctions();
if ($("endedAuctionFilter"))
  $("endedAuctionFilter").onchange = () => renderEndedAuctions();

// V3.9.3 safe upgrade: settings panel. Backup/restore handlers above remain unchanged.
async function loadAdminSettingsPanel() {
  if (!$("settingsBuyerFee")) return;
  try {
    let r = await api("/api/settings/admin"),
      st = r.settings || {};
    $("settingsBuyerFee").value = Number(st.buyerFeePercent || 0);
    $("settingsCharity").value = Number(st.charityProfitPercent || 0);
    $("settingsEntryFee").value = Number(st.auctionEntryFee || 0);
    $("settingsEntryEnabled").checked = !!st.entryFeeEnabled;
    let vs = st.visitorSections || {};
    if ($("visitorSectionMarket")) $("visitorSectionMarket").checked = vs.market !== false;
    if ($("visitorSectionAuction")) $("visitorSectionAuction").checked = vs.auction !== false;
    if ($("visitorSectionSpecialNumbers")) $("visitorSectionSpecialNumbers").checked = vs.specialNumbers !== false;
    if ($("visitorSectionTransitional")) $("visitorSectionTransitional").checked = vs.transitionalIssues !== false;
    if ($("visitorSectionFantasia")) $("visitorSectionFantasia").checked = vs.fantasia !== false;
    $("platformName").value = st.platformName || "نوادر العملات";
    $("adminEmail").value = st.adminEmail || "";
    if ($("ocrTesseractPath"))
      $("ocrTesseractPath").value = st.ocrTesseractPath || "";
  } catch (e) {
    if ($("settingsStatus"))
      $("settingsStatus").textContent = "تعذر تحميل الإعدادات: " + e.message;
  }
}
if ($("saveSettings"))
  $("saveSettings").onclick = async () => {
    let st = $("settingsStatus");
    try {
      let saveResult = await api("/api/settings", {
        method: "POST",
        body: JSON.stringify({
          buyerFeePercent: Number($("settingsBuyerFee").value || 0),
          charityProfitPercent: Number($("settingsCharity").value || 0),
          auctionEntryFee: Number($("settingsEntryFee").value || 0),
          entryFeeEnabled: !!$("settingsEntryEnabled").checked,
          visitorSections: {
            market: $("visitorSectionMarket") ? !!$("visitorSectionMarket").checked : true,
            auction: $("visitorSectionAuction") ? !!$("visitorSectionAuction").checked : true,
            specialNumbers: $("visitorSectionSpecialNumbers") ? !!$("visitorSectionSpecialNumbers").checked : true,
            transitionalIssues: $("visitorSectionTransitional") ? !!$("visitorSectionTransitional").checked : true,
            fantasia: $("visitorSectionFantasia") ? !!$("visitorSectionFantasia").checked : true,
          },
          platformName: $("platformName").value.trim() || "نوادر العملات",
          adminEmail: $("adminEmail").value.trim(),
          ocrTesseractPath: $("ocrTesseractPath")
            ? $("ocrTesseractPath").value.trim()
            : "",
        }),
      });
      let savedVs = (saveResult && saveResult.settings && saveResult.settings.visitorSections) || {};
      if ($("visitorSectionMarket")) $("visitorSectionMarket").checked = savedVs.market !== false;
      if ($("visitorSectionAuction")) $("visitorSectionAuction").checked = savedVs.auction !== false;
      if ($("visitorSectionSpecialNumbers")) $("visitorSectionSpecialNumbers").checked = savedVs.specialNumbers !== false;
      if ($("visitorSectionTransitional")) $("visitorSectionTransitional").checked = savedVs.transitionalIssues !== false;
      if ($("visitorSectionFantasia")) $("visitorSectionFantasia").checked = savedVs.fantasia !== false;
      st.textContent = "✅ تم حفظ الإعدادات وتأكيدها من الخادم.";
    } catch (e) {
      st.textContent = "⚠️ " + e.message;
    }
  };
document
  .querySelectorAll('.dashboard-go[data-go="settings"]')
  .forEach((b) =>
    b.addEventListener("click", () => setTimeout(loadAdminSettingsPanel, 0)),
  );
if ($("testOcr"))
  $("testOcr").onclick = async () => {
    let st = $("settingsStatus");
    st.textContent = "جارٍ فحص محرك OCR...";
    try {
      let r = await api("/api/ocr/status");
      if (r.ok)
        st.textContent =
          "✅ " +
          (r.version || "Tesseract") +
          " — " +
          (r.path || "") +
          " — العربية: " +
          (r.hasArabic ? "متوفرة" : "غير متوفرة") +
          " — الإنجليزية: " +
          (r.hasEnglish ? "متوفرة" : "غير متوفرة");
      else
        st.textContent =
          "⚠️ لم يتم العثور على Tesseract. " +
          (r.diagnostics || []).slice(-2).join(" — ");
    } catch (e) {
      st.textContent = "⚠️ تعذر اختبار OCR: " + e.message;
    }
  };

// V3.9.5 — permissions, notifications and 24-hour auction dues. Existing backup/restore handlers remain untouched.
let adminNotificationFilter = "all";
function fmtDate(x) {
  try {
    return new Date(x).toLocaleString("ar-SA");
  } catch (e) {
    return x || "";
  }
}
function notificationIcon(c) {
  return c === "auction"
    ? "⚖"
    : c === "approval"
      ? "✓"
      : c === "market"
        ? "🛍"
        : c === "finance"
          ? "💳"
          : "🔔";
}
async function renderAdminNotifications() {
  if (!$("adminNotificationsList")) return;
  try {
    let r = await api("/api/notifications/admin"),
      rows = r.notifications || [];
    if ($("adminNotificationsBadge")) {
      $("adminNotificationsBadge").textContent = r.unread || 0;
      $("adminNotificationsBadge").hidden = !(r.unread > 0);
    }
    let show =
      adminNotificationFilter === "all"
        ? rows
        : rows.filter((x) => x.category === adminNotificationFilter);
    $("adminNotificationsList").innerHTML =
      show
        .map((x) => {
          let approval = x.category === "approval" && x.participantId;
          return `<article class="notification-row ${x.read ? "" : "unread"}"><span class="notification-icon">${notificationIcon(x.category)}</span><div><b>${esc(x.title)}</b><p>${esc(x.message)}</p><small>${fmtDate(x.created)}</small></div><div class="actions notification-actions">${approval ? `<button type="button" class="ghost" onclick="openParticipantsFromNotification()">فتح إدارة الاعتماد</button>` : x.actionUrl ? `<a href="${esc(x.actionUrl)}" class="ghost button-link">فتح</a>` : ""}</div></article>`;
        })
        .join("") || '<p class="muted">لا توجد إشعارات في هذا القسم.</p>';
  } catch (e) {
    $("adminNotificationsList").textContent =
      "تعذر تحميل الإشعارات: " + e.message;
  }
}
document.querySelectorAll(".notification-filter").forEach((b) =>
  b.addEventListener("click", () => {
    document
      .querySelectorAll(".notification-filter")
      .forEach((x) => x.classList.remove("active"));
    b.classList.add("active");
    adminNotificationFilter = b.dataset.filter || "all";
    renderAdminNotifications();
  }),
);
if ($("markAdminNotificationsRead"))
  $("markAdminNotificationsRead").onclick = async () => {
    try {
      await api("/api/notifications/admin/read", {
        method: "POST",
        body: "{}",
      });
      await renderAdminNotifications();
    } catch (e) {
      alert(e.message);
    }
  };
window.openParticipantsFromNotification = async () => {
  show("participants");
  await renderParticipants();
  window.scrollTo({ top: 0, behavior: "smooth" });
};

function permissionCheck(pid, key, checked) {
  let m = {
      sellerEndedAuctions: [
        "⚖",
        "المزادات المنتهية",
        "عرض وإدارة مزاداته المنتهية",
        "auction",
      ],
      sellerMarket: [
        "🛍",
        "متابعة السوق",
        "متابعة عروضه وطلباته في السوق",
        "market",
      ],
      liveBroadcast: [
        "🔴",
        "البث المباشر",
        "فتح كاميرا وبث مزاد مباشر من حسابه الموثق",
        "auction",
      ],
      marketSupervision: [
        "🛍",
        "إشراف السوق",
        "الإشراف على عروض وطلبات السوق",
        "market",
      ],
      auctionSupervision: [
        "⚖",
        "إشراف المزاد",
        "الإشراف على المزادات والمزايدات",
        "auction",
      ],
      ordersView: [
        "📦",
        "عرض الطلبات",
        "مشاهدة الطلبات والشحن المصرح بها",
        "orders",
      ],
      ordersManage: [
        "🚚",
        "إدارة الطلبات",
        "تحديث السداد والتجهيز والشحن",
        "orders",
      ],
    },
    z = m[key] || ["•", key, "", "general"];
  return `<label class="permission-check permission-${z[3]}"><span class="permission-card-icon">${z[0]}</span><span class="permission-copy"><b>${z[1]}</b><small>${z[2]}</small></span><input type="checkbox" data-pid="${esc(pid)}" data-perm="${key}" ${checked ? "checked" : ""}><span class="permission-state">${checked ? "مفعّلة" : "غير مفعّلة"}</span></label>`;
}
async function renderPermissions() {
  if (!$("permissionsList")) return;
  try {
    let r = await api("/api/permissions"),
      rows = r.participants || [];
    $("permissionsList").innerHTML =
      rows
        .map((x) => {
          let p = x.permissions || {};
          return `<article class="permission-row"><div class="permission-user"><b>${esc(x.name || "مشارك")}</b><span>${esc(x.phone || "")}</span><small>${x.verified ? "موثق" : "غير موثق"} • ${x.approved ? "معتمد" : "غير معتمد"}</small></div><div class="permission-options">${permissionCheck(x.id, "sellerEndedAuctions", p.sellerEndedAuctions)}${permissionCheck(x.id, "sellerMarket", p.sellerMarket)}${permissionCheck(x.id, "liveBroadcast", p.liveBroadcast)}${permissionCheck(x.id, "marketSupervision", p.marketSupervision)}${permissionCheck(x.id, "auctionSupervision", p.auctionSupervision)}${permissionCheck(x.id, "ordersView", p.ordersView)}${permissionCheck(x.id, "ordersManage", p.ordersManage)}</div><button type="button" class="save-permissions" data-pid="${esc(x.id)}">حفظ الصلاحيات</button></article>`;
        })
        .join("") || '<p class="muted">لا يوجد مشاركون مسجلون.</p>';
    document.querySelectorAll(".permission-check").forEach((l) => {
      let inp = l.querySelector("input");
      let sync = () => {
        l.classList.toggle("selected", !!inp.checked);
        let st = l.querySelector(".permission-state");
        if (st) st.textContent = inp.checked ? "مفعّلة" : "غير مفعّلة";
      };
      inp?.addEventListener("change", sync);
      sync();
    });
    document.querySelectorAll(".save-permissions").forEach(
      (b) =>
        (b.onclick = async () => {
          let pid = b.dataset.pid,
            body = { participantId: pid };
          document.querySelectorAll("input[data-pid]").forEach((c) => {
            if (c.dataset.pid === pid) body[c.dataset.perm] = c.checked;
          });
          try {
            await api("/api/permissions/update", {
              method: "POST",
              body: JSON.stringify(body),
            });
            b.textContent = "✓ تم الحفظ";
            setTimeout(() => (b.textContent = "حفظ الصلاحيات"), 1200);
          } catch (e) {
            alert(e.message);
          }
        }),
    );
    document.querySelectorAll(".permission-check input[type=checkbox]").forEach(
      (c) =>
        (c.onchange = () => {
          let l = c.closest(".permission-check"),
            st = l?.querySelector(".permission-state");
          if (st) st.textContent = c.checked ? "مفعّلة" : "غير مفعّلة";
        }),
    );
  } catch (e) {
    $("permissionsList").textContent = "تعذر تحميل الصلاحيات: " + e.message;
  }
}
if ($("refreshPermissions"))
  $("refreshPermissions").onclick = renderPermissions;

function dueStatusLabel(x) {
  return x.status === "paid"
    ? "مسدد"
    : x.status === "cancelled"
      ? "ملغي"
      : "غير مسدد";
}
async function renderDues() {
  if (!$("duesList")) return;
  try {
    let r = await api("/api/dues"),
      rows = r.dues || [],
      now = Date.now();
    let unpaid = rows.filter((x) => x.status === "unpaid"),
      overdue = unpaid.filter(
        (x) => new Date(x.paymentDeadline).getTime() <= now,
      ),
      paid = rows.filter((x) => x.status === "paid");
    $("duesUnpaidCount").textContent = unpaid.length;
    $("duesOverdueCount").textContent = overdue.length;
    $("duesPaidCount").textContent = paid.length;
    $("duesList").innerHTML =
      rows
        .map((x) => {
          let isOver =
            x.status === "unpaid" &&
            new Date(x.paymentDeadline).getTime() <= now;
          return `<article class="due-row ${isOver ? "overdue" : ""}"><div><b>${esc(x.itemTitle || "مقتنى")}</b><p>${esc(x.participantName || "مشارك")} — ${esc(x.participantPhone || "")}</p><small>قيمة الفوز: ${money(x.amount)} • مهلة السداد: ${fmtDate(x.paymentDeadline)}</small></div><span class="due-status ${x.status}">${isOver ? "متأخر +24 ساعة" : dueStatusLabel(x)}</span><div class="actions due-actions"><button class="due-paid ${x.status === "paid" ? "is-current" : ""}" data-due="${esc(x.id)}" data-status="paid" ${x.status === "paid" ? "disabled" : ""}>${x.status === "paid" ? "✓ تم السداد" : "اعتماد السداد"}</button><button class="due-cancel" data-due="${esc(x.id)}" data-status="cancelled" ${x.status === "cancelled" ? "disabled" : ""}>إلغاء المستحق</button><button class="due-unpaid" data-due="${esc(x.id)}" data-status="unpaid" ${x.status === "unpaid" ? "disabled" : ""}>↩ إرجاع لغير مسدد</button></div></article>`;
        })
        .join("") ||
      '<p class="muted">لا توجد مستحقات مزادات مسجلة حتى الآن.</p>';
    document.querySelectorAll("[data-due][data-status]").forEach(
      (b) =>
        (b.onclick = async () => {
          try {
            await api("/api/dues/status", {
              method: "POST",
              body: JSON.stringify({
                id: b.dataset.due,
                status: b.dataset.status,
              }),
            });
            await renderDues();
            await renderAdminNotifications();
          } catch (e) {
            alert(e.message);
          }
        }),
    );
  } catch (e) {
    $("duesList").textContent = "تعذر تحميل المستحقات: " + e.message;
  }
}
if ($("refreshDues")) $("refreshDues").onclick = renderDues;

async function renderOperations() {
  if (!$("operationsList")) return;
  try {
    let r = await api("/api/operations"),
      rows = r.events || [];
    $("operationsList").innerHTML =
      rows
        .map(
          (x) =>
            `<article class="operation-row"><b>${esc(x.action)}</b><span>${esc(x.actor || "الإدارة")}</span><small>${fmtDate(x.created)}</small><code>${esc(JSON.stringify(x.details || {}))}</code></article>`,
        )
        .join("") || '<p class="muted">لا توجد عمليات مسجلة بعد.</p>';
  } catch (e) {
    $("operationsList").textContent = "تعذر تحميل سجل العمليات: " + e.message;
  }
}
if ($("refreshOperations")) $("refreshOperations").onclick = renderOperations;

async function loadV395Page(vw) {
  if (vw === "notifications") await renderAdminNotifications();
  if (vw === "dues") await renderDues();
  if (vw === "operations") await renderOperations();
  if (vw === "settings") await loadAdminSettingsPanel();
}
document
  .querySelectorAll("nav button")
  .forEach((b) => b.addEventListener("click", () => loadV395Page(b.dataset.v)));
document
  .querySelectorAll(".dashboard-go")
  .forEach((b) =>
    b.addEventListener("click", () => loadV395Page(b.dataset.go)),
  );
setTimeout(() => renderAdminNotifications().catch(() => {}), 700);

// V4.0.1 — Orders & Shipping
const ORDER_LABELS = {
  new: "طلب جديد",
  awaiting_payment: "بانتظار السداد",
  paid: "تم السداد",
  preparing: "قيد التجهيز",
  ready_to_ship: "جاهز للشحن",
  shipped: "تم الشحن",
  received: "تم الاستلام",
  completed: "مكتمل",
  stalled: "متعثر",
  cancelled: "ملغي",
  returned: "مرتجع",
};
let orderFilter = "active";
function storageText(s = {}) {
  return (
    [
      ["المستودع", s.warehouse],
      ["الخزانة", s.cabinet],
      ["الرف", s.shelf],
      [s.box ? "الصندوق" : "الألبوم", s.box || s.album],
      ["الصفحة/الجيب", s.pocket],
    ]
      .filter((x) => x[1])
      .map((x) => x[0] + ": " + x[1])
      .join(" ← ") || "موقع التخزين غير محدد"
  );
}
function orderNextButtons(o) {
  if (o.archived) return "";
  let map = {
    awaiting_payment: [["paid", "تأكيد السداد"]],
    paid: [["preparing", "بدء التجهيز"]],
    preparing: [["ready_to_ship", "جاهز للشحن"]],
    ready_to_ship: [["shipped", "تم الشحن"]],
    shipped: [["received", "تم الاستلام"]],
    received: [["completed", "إكمال وأرشفة"]],
  };
  let b = (map[o.status] || [])
    .map(
      (x) =>
        `<button onclick="orderStatus('${o.id}','${x[0]}')">${x[1]}</button>`,
    )
    .join("");
  let requests="";
  if(o.cancellationStatus==="requested")requests=`<button class="danger" onclick="processOrderRequest('${o.id}','approve_cancel')">اعتماد الإلغاء وإعادة الكمية</button><button class="ghost" onclick="processOrderRequest('${o.id}','reject')">رفض الطلب</button>`;
  if(o.refundStatus==="requested")requests=`<button class="danger" onclick="processOrderRequest('${o.id}','complete_refund')">تسجيل الاسترداد وإعادة الكمية</button><button class="ghost" onclick="processOrderRequest('${o.id}','reject')">رفض الطلب</button>`;
  let release=o.paymentStatus==="paid"&&["paid","preparing","ready_to_ship"].includes(o.status)&&o.refundStatus!=="requested"?`<button class="danger" onclick="processOrderRequest('${o.id}','complete_refund')">تسجيل الاسترداد وإعادة الكمية</button>`:o.paymentStatus!=="paid"&&["new","awaiting_payment","stalled"].includes(o.status)?`<button class="danger" onclick="orderStatus('${o.id}','cancelled')">إلغاء وإعادة الكمية</button>`:"";
  return b+requests+`<button class="ghost" onclick="orderStatus('${o.id}','stalled')">متعثر</button><button class="ghost" onclick="orderStatus('${o.id}','returned')">مرتجع</button>`+release;
}
function orderCard(o) {
  let imgs = (o.items || []).flatMap((x) => x.images || []).filter(Boolean);
  let itemHtml = (o.items || [])
    .map(
      (x) =>
        `<div class="order-item">${(x.images || [])[0] ? `<img class="order-thumb" style="width:96px;height:72px;max-width:96px;max-height:72px;object-fit:contain" src="${esc((x.images || [])[0])}" onclick='openCoinLightbox(${JSON.stringify(x.images || [])},0,${JSON.stringify(x.title || "")})'>` : ""}<div><b>${esc(x.title || "مقتنى")}</b><div>الكمية: ${Number(x.quantity || 1)} • ${money(x.total || 0)}</div><div class="storage-path">${esc(storageText(x.storage || {}))}</div></div></div>`,
    )
    .join("");
  let requestNotice=o.refundStatus==="requested"?'<div class="notice danger"><b>طلب استرداد معلق من العميل</b></div>':o.cancellationStatus==="requested"?'<div class="notice danger"><b>طلب إلغاء معلق من العميل</b></div>':'';
  return `<article class="order-card ${o.archived ? "archived-order" : ""}"><div class="order-head"><div><h3>${esc(o.orderNumber || o.id)}</h3><small>${new Date(o.created).toLocaleString("ar-SA")}</small></div><div><span class="source-chip">${o.source === "auction" ? "مزاد" : "السوق العام"}</span> <span class="order-status">${ORDER_LABELS[o.status] || esc(o.status)}</span></div></div><div class="order-body">${requestNotice}<div class="order-grid"><div class="order-info"><span>العميل</span><b>${esc(o.customerName || "—")}</b><br>${esc(o.customerPhone || "")}</div><div class="order-info"><span>السداد</span><b>${o.paymentStatus === "paid" ? "تم السداد" : o.paymentStatus==="refunded"?"تم الاسترداد":"غير مسدد"}</b></div><div class="order-info"><span>الإجمالي</span><b>${money(o.total || 0)}</b><br><small>الشحن: ${o.shippingFeeConfirmed ? money(o.shippingFee || 0) : "غير محدد"}</small></div><div class="order-info"><span>الشحن</span><b>${esc(o.shippingCompany || "لم يسجل")}</b><br>${esc(o.trackingNumber || "")}</div><div class="order-info"><span>عنوان التسليم</span><b>${esc((o.shippingAddress||{}).city || "غير مكتمل")}</b><br><small>${esc([(o.shippingAddress||{}).district,(o.shippingAddress||{}).addressLine].filter(Boolean).join(' — '))}</small></div></div>${itemHtml}<div class="order-shipping-fields"><input id="shipfee-${o.id}" type="number" min="0" step="0.01" value="${Number(o.shippingFee || 0)}" placeholder="مبلغ الشحن (0 = مجاني)" ${o.paymentStatus === "paid" ? "disabled" : ""}><input id="shipco-${o.id}" value="${esc(o.shippingCompany || "")}" placeholder="شركة الشحن"><input id="track-${o.id}" value="${esc(o.trackingNumber || "")}" placeholder="رقم التتبع"></div><div class="order-actions"><button class="ghost" onclick="saveShipping('${o.id}')">اعتماد مبلغ الشحن وحفظ بياناته</button>${orderNextButtons(o)}<button class="ghost" onclick="printOrder('${o.id}')">🖨 طباعة ملخص/فاتورة</button></div></div></article>`;
}
async function renderOrders() {
  if (!$("ordersList")) return;
  try {
    let r = await api("/api/orders"),
      rows = r.orders || [],
      activeRows = rows.filter((x) => !x.archived);
    $("ordersActiveCount").textContent = r.active || activeRows.length;
    $("ordersArchivedCount").textContent =
      r.archived || rows.filter((x) => x.archived).length;
    $("ordersAwaitingCount").textContent = activeRows.filter(
      (x) => x.status === "awaiting_payment",
    ).length;
    $("ordersShippingCount").textContent = activeRows.filter((x) =>
      ["preparing", "ready_to_ship", "shipped"].includes(x.status),
    ).length;
    let countMap = {
      ofActive: activeRows.length,
      ofAwaiting: activeRows.filter((x) => x.status === "awaiting_payment")
        .length,
      ofPaid: activeRows.filter((x) => x.status === "paid").length,
      ofPreparing: activeRows.filter((x) => x.status === "preparing").length,
      ofReady: activeRows.filter((x) => x.status === "ready_to_ship").length,
      ofShipped: activeRows.filter((x) => x.status === "shipped").length,
      ofReceived: activeRows.filter((x) => x.status === "received").length,
      ofCompleted: activeRows.filter((x) => x.status === "completed").length,
      ofStalled: activeRows.filter((x) => x.status === "stalled").length,
      ofCancelled: activeRows.filter((x) => x.status === "cancelled").length,
      ofReturned: activeRows.filter((x) => x.status === "returned").length,
      ofArchived: rows.filter((x) => x.archived).length,
      ofAll: rows.length,
    };
    for (let [id, c] of Object.entries(countMap))
      if ($(id)) $(id).textContent = c;
    let badge = $("ordersBadge");
    if (badge) {
      let c = activeRows.length;
      badge.textContent = c;
      badge.hidden = !c;
    }
    let out = rows.filter((x) => {
      if (orderFilter === "all") return true;
      if (orderFilter === "active") return !x.archived;
      if (orderFilter === "archived") return !!x.archived;
      return !x.archived && x.status === orderFilter;
    });
    $("ordersList").innerHTML =
      out.map(orderCard).join("") ||
      '<p class="muted">لا توجد طلبات في هذا القسم.</p>';
  } catch (e) {
    $("ordersList").textContent = "تعذر تحميل الطلبات: " + e.message;
  }
}
window.orderStatus = async (id, status) => {
  try {
    await api("/api/order/update", {
      method: "POST",
      body: JSON.stringify({ id, status }),
    });
    await renderOrders();
    if (status === "paid") await renderDues();
  } catch (e) {
    alert(e.message);
  }
};
window.processOrderRequest=async(id,action)=>{
  let label=action==='approve_cancel'?'اعتماد الإلغاء وإعادة الكمية؟':action==='complete_refund'?'هل تم رد المبلغ فعليًا وتريد تسجيل الاسترداد وإعادة الكمية؟':'رفض طلب الإلغاء/الاسترداد؟';
  if(!confirm(label))return;
  try{await api('/api/order/request/resolve',{method:'POST',body:JSON.stringify({id,action})});await renderOrders();await renderDues()}catch(e){alert(e.message)}
};
window.saveShipping = async (id) => {
  try {
    const fee = Number($("shipfee-" + id)?.value || 0);
    await api("/api/order/shipping", {
      method: "POST",
      body: JSON.stringify({
        id,
        shippingFee: fee,
        shippingCompany: $("shipco-" + id)?.value || "",
        trackingNumber: $("track-" + id)?.value || "",
      }),
    });
    await renderOrders();
    toast(`تم اعتماد مبلغ الشحن ${money(fee)} وحفظ بيانات الشحن.`);
  } catch (e) {
    alert(e.message);
  }
};
window.printOrder = async (id) => {
  let r = await api("/api/orders"),
    o = (r.orders || []).find((x) => x.id === id);
  if (!o) return;
  let w = window.open("", "_blank");
  w.document.write(
    `<html dir="rtl"><head><title>${esc(o.orderNumber)}</title><style>body{font-family:Tahoma;padding:30px}h1{color:#071b35}.box{border:1px solid #ccc;padding:12px;margin:8px 0;border-radius:10px}</style></head><body><h1>نوادر العملات — ملخص الطلب</h1><div class="box"><b>رقم الطلب:</b> ${esc(o.orderNumber)}<br><b>المصدر:</b> ${o.source === "auction" ? "مزاد" : "السوق العام"}<br><b>العميل:</b> ${esc(o.customerName)} — ${esc(o.customerPhone)}<br><b>الحالة:</b> ${ORDER_LABELS[o.status] || o.status}<br><b>الإجمالي:</b> ${money(o.total)}</div>${(o.items || []).map((x) => `<div class="box"><b>${esc(x.title)}</b><br>الكمية: ${x.quantity}<br>${esc(storageText(x.storage || {}))}</div>`).join("")}<div class="box"><b>شركة الشحن:</b> ${esc(o.shippingCompany || "—")}<br><b>رقم التتبع:</b> ${esc(o.trackingNumber || "—")}</div></body></html>`,
  );
  w.document.close();
  w.print();
};
if ($("refreshOrders")) $("refreshOrders").onclick = renderOrders;
document.querySelectorAll(".order-filter").forEach(
  (b) =>
    (b.onclick = () => {
      document
        .querySelectorAll(".order-filter")
        .forEach((x) => x.classList.remove("active"));
      b.classList.add("active");
      orderFilter = b.dataset.ofilter;
      renderOrders();
    }),
);
// Include orders in navigation refresh
for (const b of document.querySelectorAll(
  'nav button[data-v="orders"],.dashboard-go[data-go="orders"]',
))
  b.addEventListener("click", () => renderOrders());

// Unified professional coin lightbox (mouse, touch/pinch, navigation)
let LB = {
  imgs: [],
  idx: 0,
  scale: 1,
  rot: 0,
  x: 0,
  y: 0,
  pointers: new Map(),
  lastDist: 0,
  caption: "",
};
function lbDraw() {
  let im = $("coinLightboxImg");
  if (im)
    im.style.transform = `translate(${LB.x}px,${LB.y}px) scale(${LB.scale}) rotate(${LB.rot}deg)`;
}
window.openCoinLightbox = (imgs, idx = 0, caption = "") => {
  LB.imgs = (Array.isArray(imgs) ? imgs : [imgs]).filter(Boolean);
  if (!LB.imgs.length) return;
  LB.idx = Math.max(0, Math.min(idx, LB.imgs.length - 1));
  LB.caption = caption;
  LB.scale = 1;
  LB.rot = 0;
  LB.x = LB.y = 0;
  $("coinLightboxImg").src = LB.imgs[LB.idx];
  $("coinLightboxCaption").textContent =
    (caption ? caption + " — " : "") + (LB.idx + 1) + " / " + LB.imgs.length;
  $("coinLightbox").showModal();
  lbDraw();
};
function lbMove(d) {
  if (!LB.imgs.length) return;
  LB.idx = (LB.idx + d + LB.imgs.length) % LB.imgs.length;
  LB.scale = 1;
  LB.rot = 0;
  LB.x = LB.y = 0;
  $("coinLightboxImg").src = LB.imgs[LB.idx];
  $("coinLightboxCaption").textContent =
    (LB.caption ? LB.caption + " — " : "") +
    (LB.idx + 1) +
    " / " +
    LB.imgs.length;
  lbDraw();
}
if ($("coinLightboxClose"))
  $("coinLightboxClose").onclick = () => $("coinLightbox").close();
document.querySelectorAll("[data-lb]").forEach(
  (b) =>
    (b.onclick = () => {
      let a = b.dataset.lb;
      if (a === "prev") lbMove(-1);
      if (a === "next") lbMove(1);
      if (a === "zin") LB.scale = Math.min(6, LB.scale + 0.25);
      if (a === "zout") LB.scale = Math.max(0.5, LB.scale - 0.25);
      if (a === "rl") LB.rot -= 90;
      if (a === "rr") LB.rot += 90;
      if (a === "center") {
        LB.x = LB.y = 0;
      }
      if (a === "reset") {
        LB.scale = 1;
        LB.rot = 0;
        LB.x = LB.y = 0;
      }
      if (a === "full") {
        let d = $("coinLightbox");
        if (!document.fullscreenElement) d?.requestFullscreen?.();
        else document.exitFullscreen?.();
      }
      lbDraw();
    }),
);
if ($("coinLightboxStage")) {
  let st = $("coinLightboxStage");
  st.onpointerdown = (e) => {
    LB.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    st.setPointerCapture(e.pointerId);
  };
  st.onpointermove = (e) => {
    if (!LB.pointers.has(e.pointerId)) return;
    let old = LB.pointers.get(e.pointerId);
    LB.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    let vals = [...LB.pointers.values()];
    if (vals.length === 1) {
      LB.x += e.clientX - old.x;
      LB.y += e.clientY - old.y;
    } else if (vals.length === 2) {
      let d = Math.hypot(vals[0].x - vals[1].x, vals[0].y - vals[1].y);
      if (LB.lastDist)
        LB.scale = Math.max(0.5, Math.min(6, (LB.scale * d) / LB.lastDist));
      LB.lastDist = d;
    }
    lbDraw();
  };
  st.onpointerup = st.onpointercancel = (e) => {
    LB.pointers.delete(e.pointerId);
    if (LB.pointers.size < 2) LB.lastDist = 0;
  };
  st.onwheel = (e) => {
    e.preventDefault();
    LB.scale = Math.max(
      0.5,
      Math.min(6, LB.scale + (e.deltaY < 0 ? 0.2 : -0.2)),
    );
    lbDraw();
  };
}
// Make record and warehouse images open together in the lightbox.
setInterval(
  () =>
    document.querySelectorAll(".record-card-images img, .warehouse-thumb-pair img").forEach((img) => {
      if (img.dataset.lbready) return;
      img.dataset.lbready = "1";
      img.style.cursor = "zoom-in";
      img.addEventListener("click", (e) => {
        e.stopPropagation();
        const group = img.closest(".record-card-images, .warehouse-thumb-pair");
        const images = [...group.querySelectorAll("img")].map((node) => node.src);
        openCoinLightbox(images, Math.max(0, images.indexOf(img.src)), "صور المقتنى — الوجه والخلف");
      });
    }),
  1200,
);

if ($("specialNumberEnabled"))
  $("specialNumberEnabled").addEventListener("change", () => {
    if ($("specialNumberFields"))
      $("specialNumberFields").hidden = !$("specialNumberEnabled").checked;
  });
function syncSpecialVisuals() {
  let main = $("specialNumberEnabled");
  let lab = main?.closest(".special-number-toggle");
  lab?.classList.toggle("selected", !!main?.checked);
  document
    .querySelectorAll(".special-type-grid .check")
    .forEach((l) =>
      l.classList.toggle("selected", !!l.querySelector("input")?.checked),
    );
}
$("specialNumberEnabled")?.addEventListener("change", syncSpecialVisuals);
document
  .querySelectorAll(".special-number-type")
  .forEach((x) => x.addEventListener("change", syncSpecialVisuals));
document.addEventListener("click", (e) => {
  if (e.target.closest?.(".special-type-grid .check,.special-number-toggle"))
    setTimeout(syncSpecialVisuals, 0);
});
setTimeout(syncSpecialVisuals, 0);

// V4.0.10.1 explicit finance refresh on navigation
document
  .querySelectorAll('[data-v="finance"],.dashboard-go[data-go="finance"]')
  .forEach((b) =>
    b.addEventListener("click", () => setTimeout(() => renderFinance(), 50)),
  );

// V4.8.2 — direct publishing moderation workflow
function moderationLabel(s){
  return ({active:"نشط",hidden:"مخفي",suspended:"موقوف",archived:"مؤرشف"})[s||"active"]||"نشط";
}
async function renderCollectibleApprovals(){
  if(!$("collectibleApprovalsList"))return;
  try{
    let r=await api("/api/items"),rows=r.items||[];
    let active=rows.filter(x=>(x.moderationStatus||"active")==="active").length;
    let restricted=rows.length-active;
    $("collectiblePendingCount").textContent=active;
    $("collectibleNeedsCount").textContent=restricted;
    $("collectibleTotalCount").textContent=rows.length;
    let badge=$("collectibleApprovalsBadge");if(badge){badge.textContent=restricted;badge.hidden=!restricted}
    $("collectibleApprovalsList").innerHTML=rows.slice().sort((a,b)=>Number(b.updated||0)-Number(a.updated||0)).map(i=>{
      let s=i.moderationStatus||"active",imgs=[i.frontImg,i.backImg].filter(Boolean);
      return `<article class="collectible-approval-card">
        <div class="collectible-approval-images">${imgs.slice(0,2).map((src,idx)=>`<img src="${esc(src)}" onclick='openCoinLightbox(${JSON.stringify(imgs)},${idx},${JSON.stringify((i.country||"")+" — "+(i.denomination||""))})'>`).join("")}</div>
        <div class="collectible-approval-info">
          <h3>${esc(i.country||"—")} — ${esc(i.denomination||"—")}</h3>
          <div><b>${esc(i.ownerName||"صاحب المنصة")}</b> ${i.ownerCountry?`— ${esc(i.ownerCountry)}`:""}</div>
          <div class="collectible-meta"><span>${esc(i.year||"بدون سنة")}</span><span>السوق: ${i.forMarket&&i.marketApproved?"منشور":"—"}</span><span>المزاد: ${i.forAuction&&i.auctionApproved?"منشور":"—"}</span><span class="collectible-state">${moderationLabel(s)}</span></div>
          ${i.moderationReason?`<p><b>سبب آخر إجراء:</b> ${esc(i.moderationReason)}</p>`:""}
          <div class="collectible-actions">
            ${s!=="active"?`<button class="approve" onclick="setItemModeration('${esc(i.id)}','active')">✓ تفعيل</button>`:""}
            <button class="changes" onclick="setItemModeration('${esc(i.id)}','hidden')">إخفاء</button>
            <button class="changes" onclick="setItemModeration('${esc(i.id)}','suspended')">إيقاف</button>
            <button class="reject" onclick="removeItem('${esc(i.id)}')">حذف ← الأرشيف</button>
          </div>
        </div>
      </article>`;
    }).join("")||'<p class="muted">لا توجد مقتنيات.</p>';
  }catch(e){$("collectibleApprovalsList").textContent="تعذر تحميل مراقبة المقتنيات: "+e.message}
}
window.setItemModeration=async(id,status)=>{
  let reason="";
  if(status!=="active"){reason=(prompt("اكتب سبب الإجراء (إلزامي):","")||"").trim();if(!reason)return}
  if(!confirm(`${status==="active"?"إعادة تفعيل":"تطبيق الإجراء"} على هذا المقتنى؟`))return;
  try{await api("/api/moderation/item",{method:"POST",body:JSON.stringify({itemId:id,status,reason})});await renderCollectibleApprovals();await refresh(true);await renderAdminNotifications()}catch(e){alert(e.message)}
};
if($("refreshCollectibleApprovals"))$("refreshCollectibleApprovals").onclick=renderCollectibleApprovals;
document.querySelectorAll('nav button[data-v="collectible-approvals"],.dashboard-go[data-go="collectible-approvals"]').forEach(b=>b.addEventListener("click",renderCollectibleApprovals));
setTimeout(renderCollectibleApprovals,600);

async function renderArchive(){
  if(!$('archiveList'))return;
  try{
    let rows=await archivedItems();
    $('archiveCount').textContent=rows.length; $('archiveRestoreCount').textContent=rows.length;
    let badge=$('archiveBadge'); if(badge){badge.textContent=rows.length;badge.hidden=!rows.length}
    $('archiveList').innerHTML=rows.map(i=>{
      let imgs=[i.frontImg,i.backImg].filter(Boolean),title=`${i.country||'—'} — ${i.denomination||'—'}`;
      return `<article class="collectible-approval-card"><div class="collectible-approval-images">${imgs.slice(0,2).map((src,n)=>`<img src="${esc(src)}" onclick='openCoinLightbox(${JSON.stringify(imgs)},${n},${JSON.stringify(title)})'>`).join('')}</div><div class="collectible-approval-info"><h3>${esc(title)}</h3><div><b>المالك:</b> ${esc(i.ownerName||'صاحب المنصة')}</div><div class="collectible-meta"><span>الحذف: ${i.archivedAt?new Date(i.archivedAt).toLocaleString('ar-SA'):'—'}</span><span>بواسطة: ${esc(i.archivedBy|| (i.ownerArchived?'صاحب المقتنى':'الإدارة'))}</span></div><p><b>السبب:</b> ${esc(i.archiveReason||i.moderationReason||'غير مسجل')}</p><div class="actions"><button class="approve" onclick="restoreArchiveItem('${esc(i.id)}')">↩ استعادة</button><button class="reject" onclick="purgeArchiveItem('${esc(i.id)}')">🗑 إزالة نهائية</button><button class="ghost" onclick="detailArchived('${esc(i.id)}')">عرض البيانات</button></div></div></article>`;
    }).join('')||'<p class="muted">الأرشيف فارغ.</p>';
  }catch(e){$('archiveList').textContent='تعذر تحميل الأرشيف: '+e.message}
}
window.restoreArchiveItem=async id=>{
  if(!confirm('استعادة هذا المقتنى من الأرشيف؟'))return;
  try{let r=await api('/api/archive/restore',{method:'POST',body:JSON.stringify({itemId:id})});await renderArchive();await refresh(true);toast('تمت استعادة المقتنى.');if(r.warning)alert(r.warning)}catch(e){alert('تعذر الاستعادة: '+e.message)}
};
window.purgeArchiveItem=async id=>{
  let reason=(prompt('اكتب سبب الإزالة النهائية:', '')||'').trim(); if(!reason)return;
  let confirmText=(prompt('هذه العملية تزيل سجل المقتنى نهائيًا مع إبقاء تاريخ الطلبات والمزايدات. اكتب: إزالة نهائية','')||'').trim();
  if(confirmText!=='إزالة نهائية'){alert('لم يتم التأكيد.');return}
  if(!confirm('تأكيد أخير: لا يمكن استعادة المقتنى بعد الإزالة النهائية.'))return;
  try{let r=await api('/api/archive/purge',{method:'POST',body:JSON.stringify({itemId:id,reason,confirmText})});await renderArchive();await refresh(true);toast('تمت إزالة المقتنى نهائيًا من الأرشيف، وبقي تاريخ المعاملات محفوظًا.')}catch(e){alert('تعذر الإزالة النهائية: '+e.message)}
};
window.detailArchived=async id=>{
  let i=(await archivedItems()).find(x=>String(x.id)===String(id));if(!i)return;
  alert(`${i.country||'—'} — ${i.denomination||'—'}\nالسنة: ${i.year||'—'}\nالحالة: ${i.condition||'—'}\nالرقم: ${i.serial||'—'}\nسبب الأرشفة: ${i.archiveReason||i.moderationReason||'—'}`)
};
if($('refreshArchive'))$('refreshArchive').onclick=renderArchive;
document.querySelectorAll('nav button[data-v="archive"],.dashboard-go[data-go="archive"]').forEach(b=>b.addEventListener('click',renderArchive));
setTimeout(renderArchive,900);

async function renderIntegrity(){
  if(!$("integrityIssues"))return;
  try{
    let r=await api("/api/integrity"),issues=r.issues||{},count=Number(r.issueCount||0);
    $("integritySummary").innerHTML=`<article><span>المقتنيات</span><b>${Number(r.counts?.items||0)}</b></article><article><span>الحسابات</span><b>${Number(r.counts?.participants||0)}</b></article><article><span>ملاحظات السلامة</span><b>${count}</b></article>`;
    const labels={duplicateIds:"معرّفات مقتنيات مكررة",duplicateSerials:"أرقام تسلسلية مكررة",duplicatePhones:"حسابات جوال مكررة",orphanOwners:"مقتنيات مرتبطة بمالك غير موجود",zeroPriceMarket:"عروض سوق بسعر صفر",invalidAuctions:"مزادات ناقصة الإعداد",orphanSubmissions:"روابط سجل يتيمة",missingImages:"مقتنيات بلا صور"};
    let cards=[];
    for(const [key,val] of Object.entries(issues)){
      let n=Array.isArray(val)?val.length:Object.keys(val||{}).length;
      cards.push(`<article class="collectible-approval-card"><div class="collectible-approval-info"><h3>${labels[key]||key}</h3><p><b>${n}</b> حالة</p>${n?`<details><summary>عرض التفاصيل</summary><pre style="white-space:pre-wrap">${esc(JSON.stringify(val,null,2))}</pre></details>`:"<p>✓ لا توجد مشكلة</p>"}</div></article>`);
    }
    $("integrityIssues").innerHTML=cards.join("");
  }catch(e){$("integrityIssues").textContent="تعذر فحص سلامة المنصة: "+e.message}
}
window.renderIntegrity=renderIntegrity;
if($("refreshIntegrity"))$("refreshIntegrity").onclick=renderIntegrity;
document.querySelectorAll('nav button[data-v="integrity"],.dashboard-go[data-go="integrity"]').forEach(b=>b.addEventListener("click",renderIntegrity));

function setupClassificationFilters() {
  document.querySelectorAll(".record-filter").forEach(
    (b) =>
      (b.onclick = async () => {
        recordFilter = b.dataset.recordFilter;
        document
          .querySelectorAll(".record-filter")
          .forEach((x) => x.classList.toggle("active", x === b));
        $("recordSetFilters").hidden = recordFilter !== "sets";
        renderList(await all());
      }),
  );
  document.querySelectorAll(".set-filter").forEach(
    (b) =>
      (b.onclick = async () => {
        recordSetFilter = b.dataset.setFilter;
        document
          .querySelectorAll(".set-filter")
          .forEach((x) => x.classList.toggle("active", x === b));
        renderList(await all());
      }),
  );
  if ($("marketSearch")) {
    $("marketSearch").placeholder = "بحث ذكي: السعودية 50 ريال | PMG 66 | نشط | طقم | السعر:250 | الرقم:1234";
    $("marketSearch").oninput = async () => await renderMarketAdmin();
  }
  if ($("marketCategoryFilter")) $("marketCategoryFilter").onchange=async()=>await renderMarketAdmin();
  document.querySelectorAll(".market-filter").forEach(
    (b) =>
      (b.onclick = async () => {
        marketFilter = b.dataset.marketFilter;
        document
          .querySelectorAll(".market-filter")
          .forEach((x) => x.classList.toggle("active", x === b));
        $("marketSetFilters").hidden = marketFilter !== "sets";
        await renderMarketAdmin();
      }),
  );
  document.querySelectorAll(".market-set-filter").forEach(
    (b) =>
      (b.onclick = async () => {
        marketSetFilter = b.dataset.marketSetFilter;
        document
          .querySelectorAll(".market-set-filter")
          .forEach((x) => x.classList.toggle("active", x === b));
        await renderMarketAdmin();
      }),
  );
}
if (document.readyState === "loading")
  document.addEventListener("DOMContentLoaded", setupClassificationFilters);
else setupClassificationFilters();

// V4.0.24.1 — force market request images to remain small on desktop and mobile.
// Kept in JavaScript so the repair works even when an older stylesheet is cached.
function enforceMarketRequestImageSize() {
  const list = document.getElementById("marketRequests");
  if (!list) return;
  list.style.maxWidth = "100%";
  list.style.overflowX = "hidden";
  list.querySelectorAll(".market-request-card").forEach((card) => {
    card.style.setProperty("display", "grid", "important");
    card.style.setProperty(
      "grid-template-columns",
      window.innerWidth <= 700
        ? "96px minmax(0,1fr)"
        : "140px minmax(0,1fr) auto",
      "important",
    );
    card.style.setProperty("width", "100%", "important");
    card.style.setProperty("max-width", "100%", "important");
    card.style.setProperty("overflow", "hidden", "important");
    card.style.setProperty("box-sizing", "border-box", "important");
    const box = card.querySelector(".market-request-image");
    if (box) {
      const w = window.innerWidth <= 700 ? "96px" : "140px",
        h = window.innerWidth <= 700 ? "82px" : "105px";
      ["width", "min-width", "max-width"].forEach((p) =>
        box.style.setProperty(p, w, "important"),
      );
      ["height", "min-height", "max-height"].forEach((p) =>
        box.style.setProperty(p, h, "important"),
      );
      box.style.setProperty("overflow", "hidden", "important");
      box.style.setProperty("box-sizing", "border-box", "important");
      const img = box.querySelector("img");
      if (img) {
        img.style.setProperty("display", "block", "important");
        img.style.setProperty("width", "100%", "important");
        img.style.setProperty("height", "100%", "important");
        img.style.setProperty("max-width", "100%", "important");
        img.style.setProperty("max-height", "100%", "important");
        img.style.setProperty("object-fit", "contain", "important");
        img.style.setProperty("margin", "0", "important");
      }
    }
    const actions = card.querySelector(":scope > .actions");
    if (actions && window.innerWidth <= 700)
      actions.style.setProperty("grid-column", "1 / -1", "important");
  });
}
const marketRequestObserver = new MutationObserver(
  enforceMarketRequestImageSize,
);
if (document.readyState === "loading")
  document.addEventListener("DOMContentLoaded", () => {
    const list = document.getElementById("marketRequests");
    if (list)
      marketRequestObserver.observe(list, { childList: true, subtree: true });
    enforceMarketRequestImageSize();
  });
else {
  const list = document.getElementById("marketRequests");
  if (list)
    marketRequestObserver.observe(list, { childList: true, subtree: true });
  enforceMarketRequestImageSize();
}
window.addEventListener("resize", enforceMarketRequestImageSize);


// V4.2.4 — مساعدة صغيرة للأقسام المطوية بدون تغيير منطق الحفظ
document.addEventListener("click", (e) => {
  const btn = e.target.closest?.(".mini-help");
  if (!btn) return;
  e.preventDefault();
  e.stopPropagation();
  alert(btn.dataset.help || "تفاصيل إضافية عند الحاجة.");
});

// V5.2.4 — قسم فانتازيا: مصدر موحد مع بيانات الإدارة، بدون حالة محلية وهمية.
async function renderFantasiaAdmin(items=null){
  const box=$("fantasiaAdminItems"); if(!box)return;
  let source;
  if(Array.isArray(items)) source=items;
  else if(Array.isArray(latestItems) && latestItems.length) source=latestItems;
  else source=await all();
  latestItems=source.slice();
  const q=($("fantasiaSearch")?.value||"").trim().toLowerCase();
  const rows=source.filter(i=>i && i.fantasiaEnabled===true).filter(i=>!q||[i.country,i.denomination,i.year,i.fantasiaIssuer,i.fantasiaType,i.fantasiaNotes].join(" ").toLowerCase().includes(q));
  box.innerHTML=rows.map(i=>{const imgs=[i.frontImg,i.backImg,...(i.additionalImages||[])].filter(Boolean);const title=`🎭 ${i.country||"—"} — ${i.denomination||"—"}`;return `<article class="item auction-item fantasia-admin-card">${imgs.length?`<div class="auction-card-image"><img src="${imgs[0]}" alt="${esc(title)}" onclick='openCoinLightbox(${JSON.stringify(imgs)},0,${JSON.stringify(title)})' title="اضغط لفتح صور الوجه والخلف" style="cursor:zoom-in"><span class="auction-state live">فانتازيا</span></div>`:'<div class="auction-card-image no-photo">لا توجد صورة</div>'}<div class="auction-card-body"><div class="auction-card-title"><h3>${esc(title)}</h3><span class="approval-chip ok">${imgs.length} صورة</span></div><p class="ended-date">${esc(i.year||"—")} ${i.fantasiaIssuer?"— "+esc(i.fantasiaIssuer):""}</p><p class="muted">${esc(i.fantasiaNotes||"")}</p><div class="actions auction-actions">${imgs.length?`<button class="ghost" onclick='openCoinLightbox(${JSON.stringify(imgs)},0,${JSON.stringify(title)})'>⛶ الصور (${imgs.length})</button>`:""}<button onclick="editItem('${i.id}')">تعديل</button>${archiveButton(i.id)}${adminMoveButtons(i,"warehouse")}<a class="public-link" href="/fantasia#item-${i.id}" target="_blank">عرض للزوار</a></div></div></article>`}).join("")||'<div class="empty">لا توجد مقتنيات فانتازيا حاليًا.</div>';
}
function syncDarStoreFields(){
  const isCollectibles=$("storeType")?.value==="collectibles";
  if ($("collectibleCategoryWrap")) $("collectibleCategoryWrap").hidden=!isCollectibles;
  if (!isCollectibles && $("collectibleCategory")) $("collectibleCategory").value="";
}
if ($("storeType")) $("storeType").addEventListener("change",syncDarStoreFields);
if ($("collectibleCategory")) $("collectibleCategory").addEventListener("change",()=>{if($("collectibleCategory").value==="fantasia"&&$("fantasiaEnabled")){$("fantasiaEnabled").checked=true;if($("fantasiaFields"))$("fantasiaFields").hidden=false;}});
if ($("fantasiaEnabled")) $("fantasiaEnabled").addEventListener("change",()=>{if($("fantasiaFields"))$("fantasiaFields").hidden=!$("fantasiaEnabled").checked;if($("fantasiaEnabled").checked&&$("storeType")){$("storeType").value="collectibles";syncDarStoreFields();if($("collectibleCategory")&&!$("collectibleCategory").value)$("collectibleCategory").value="fantasia";}});
syncDarStoreFields();
if ($("fantasiaSearch")) $("fantasiaSearch").addEventListener("input",()=>renderFantasiaAdmin().catch(e=>console.warn(e)));
if ($("fantasiaAddNew")) $("fantasiaAddNew").onclick=()=>{show("add");setTimeout(()=>$("fantasiaEnabled")?.scrollIntoView({behavior:"smooth",block:"center"}),80);};

// V4.3.1 — الإصدارات الانتقالية: صفة للمقتنى نفسه دون إنشاء مخزون جديد.
if ($("transitionalIssueEnabled")) $("transitionalIssueEnabled").addEventListener("change",()=>{
  if ($("transitionalIssueFields")) $("transitionalIssueFields").hidden=!$("transitionalIssueEnabled").checked;
});
if ($("transitionalSearch")) $("transitionalSearch").addEventListener("input",renderTransitionalAdmin);
if ($("transitionalTypeFilter")) $("transitionalTypeFilter").addEventListener("change",renderTransitionalAdmin);

if ($("transitionalAddNew")) $("transitionalAddNew").onclick=()=>{show("add");setTimeout(()=>$("transitionalIssueEnabled")?.scrollIntoView({behavior:"smooth",block:"center"}),80);};


// V5.2.4 — طبقة موحدة لأزرار التحديث في الإدارة.
async function runAdminRefreshButton(id, task, successMessage){
  const b=$(id); if(!b || b.disabled)return;
  const old=b.textContent;
  b.disabled=true; b.setAttribute('aria-busy','true'); b.textContent='↻ جارٍ التحديث...';
  try{
    await task();
    b.textContent='✓ تم التحديث';
    if(successMessage) toast(successMessage);
    setTimeout(()=>{ if(b && !b.disabled) b.textContent=old; },900);
  }catch(e){
    console.error('فشل التحديث',id,e);
    alert('تعذر التحديث: '+(e?.message||e));
    b.textContent=old;
  }finally{
    b.disabled=false; b.removeAttribute('aria-busy');
    setTimeout(()=>{ if(b) b.textContent=old; },1100);
  }
}
function bindAdminRefresh(id, task, message){ const b=$(id); if(b)b.onclick=()=>runAdminRefreshButton(id,task,message); }
bindAdminRefresh('refreshWarehouse', async()=>{await refresh(true);await renderWarehouse();}, 'تم تحديث مؤشرات المستودع.');
bindAdminRefresh('refreshSpecial', async()=>{await refresh(true);await renderSpecialAdmin(latestItems);}, 'تم تحديث الأرقام المميزة والأخطاء النادرة.');
bindAdminRefresh('refreshFantasia', async()=>{await refresh(true);await renderFantasiaAdmin(latestItems);}, 'تم تحديث فانتازيا من المصدر المشترك.');
bindAdminRefresh('refreshTransitional', async()=>{await refresh(true);await renderTransitionalAdmin(latestItems);}, 'تم تحديث الإصدارات الانتقالية.');
bindAdminRefresh('refreshEndedAuctions', async()=>{lastDataToken='';const a=await all();latestItems=a.slice();await renderEndedAuctions(a);}, 'تم تحديث المزادات المنتهية.');
bindAdminRefresh('refreshOrders', async()=>{await renderOrders();}, 'تم تحديث الطلبات والشحن.');
bindAdminRefresh('refreshFinance', async()=>{await renderFinance();}, 'تم تحديث المالية.');
bindAdminRefresh('refreshCollectibleApprovals', async()=>{await renderCollectibleApprovals();}, 'تم تحديث مراقبة المقتنيات.');
bindAdminRefresh('refreshDues', async()=>{await renderDues();}, 'تم تحديث المستحقات.');
bindAdminRefresh('refreshOperations', async()=>{await renderOperations();}, 'تم تحديث سجل العمليات.');
bindAdminRefresh('refreshArchive', async()=>{await renderArchive();}, 'تم تحديث الأرشيف.');
bindAdminRefresh('refreshIntegrity', async()=>{await renderIntegrity();}, 'تم تحديث فحص سلامة المنصة.');


// V5.2.5 — قنوات موحدة: السوق/المزاد/التمييز/البث المباشر بدون تكرار السجل الأصلي.
function goAddWithChannel(channel){
  document.querySelector('nav button[data-v="add"]')?.click();
  setTimeout(()=>{ if($("forMarket")) $("forMarket").checked=channel==="market"; if($("forAuction")) $("forAuction").checked=channel==="auction"; $("forMarket")?.dispatchEvent(new Event("change")); $("forAuction")?.dispatchEvent(new Event("change")); },80);
}
$("marketAddNew")?.addEventListener("click",()=>goAddWithChannel("market"));
$("auctionAddNew")?.addEventListener("click",()=>goAddWithChannel("auction"));

function promoActive(i){ return !!(i.homeFeatured||i.homeQuickDeal||i.homeDiscounted); }
function promoCard(i){
 const title=i.marketTitle||`${i.country||""} — ${i.denomination||""}`;
 return `<article class="item market-admin-card">${i.frontImg?`<img src="${i.frontImg}" alt="${esc(title)}">`:""}<div class="market-admin-body"><h3>${esc(title)}</h3><p>${promoActive(i)?'<span class="approval-chip ok">مميز حاليًا</span>':'<span class="approval-chip">غير مميز</span>'}</p><div class="form-grid"><label class="check"><input type="checkbox" data-pf="${i.id}" ${i.homeFeatured?'checked':''}> مميز</label><label class="check"><input type="checkbox" data-pq="${i.id}" ${i.homeQuickDeal?'checked':''}> سريع</label><label class="check"><input type="checkbox" data-pd="${i.id}" ${i.homeDiscounted?'checked':''}> مخفض</label><label>الخصم %<input type="number" min="0" max="100" data-pp="${i.id}" value="${Number(i.homeDiscountPercent||0)}"></label><label>شارة العرض<input data-pb="${i.id}" value="${esc(i.homePromoBadge||'')}"></label><label>حتى<input type="datetime-local" data-pu="${i.id}" value="${esc((i.homePromoUntil||'').slice(0,16))}"></label></div><div class="actions"><button class="gold-action" onclick="savePromotion('${i.id}')">حفظ التمييز</button><button class="ghost" onclick="editItem('${i.id}')">تعديل المقتنى</button></div></div></article>`;
}
async function renderPromotions(){ if(!$("promotionAdminItems"))return; const items=await all(); const q=($('promotionSearch')?.value||'').toLowerCase(); const rows=items.filter(i=>!i.archived&&(i.forMarket||i.forAuction||i.fantasiaEnabled||i.specialNumberEnabled||i.transitionalIssueEnabled)).filter(i=>!q||JSON.stringify(i).toLowerCase().includes(q)); $("promotionAdminItems").innerHTML=rows.map(promoCard).join('')||'<p>لا توجد مقتنيات متاحة.</p>'; }
async function savePromotion(id){ const body={itemId:id,featured:document.querySelector(`[data-pf="${id}"]`)?.checked,quick:document.querySelector(`[data-pq="${id}"]`)?.checked,discounted:document.querySelector(`[data-pd="${id}"]`)?.checked,discountPercent:document.querySelector(`[data-pp="${id}"]`)?.value,badge:document.querySelector(`[data-pb="${id}"]`)?.value,until:document.querySelector(`[data-pu="${id}"]`)?.value}; await api('/api/promotions/update',{method:'POST',body:JSON.stringify(body)}); await renderPromotions(); }
window.savePromotion=savePromotion;
document.querySelectorAll('[data-v="promotions"],.dashboard-go[data-go="promotions"]').forEach(b=>b.addEventListener('click',renderPromotions));
$("refreshPromotions")?.addEventListener('click',renderPromotions); $("promotionSearch")?.addEventListener('input',renderPromotions);

// V5.4.2 — اسم آمن للمقتنى داخل إدارة البث المباشر.
function item_title(i={}){
  return String(
    i.marketTitle || i.title || i.itemTitle ||
    [i.country, i.denomination, i.year].filter(Boolean).join(" — ") ||
    "مقتنى"
  ).trim();
}
function liveSessionDate(s){const raw=s.startedAt||s.startAt||s.created||'';if(!raw)return 'بدون تاريخ';try{return new Date(raw).toLocaleDateString('ar-SA',{year:'numeric',month:'2-digit',day:'2-digit'})}catch{return String(raw).slice(0,10)}}
function liveSessionCard(s,items,archived=false){
 const mode=s.mode||((s.itemIds||[]).length?'prepared':'camera'), lot=s.currentLot; const opened=lot?.title||item_title(items.find(i=>String(i.id)===String(s.currentItemId))||{});
 const itemButtons=(s.itemIds||[]).map(iid=>{const it=items.find(i=>String(i.id)===String(iid));return `<button class="ghost" onclick="liveOpenItem('${s.id}','${iid}')">فتح: ${esc(item_title(it||{}))}</button>`}).join('');
 if(archived)return `<article class="participant-card"><h3>${esc(s.title||'مزاد مباشر')} <span class="approval-chip">أرشيف</span></h3><p>📅 ${esc(liveSessionDate(s))} — ${esc(s.endedAt||s.updated||'')}</p><p>${mode==='camera'?'📹 كاميرا حرة':'📦 مُحضّر'} — ${(s.history||[]).length} قطعة أغلقت خلال الجلسة</p><div class="actions"><button onclick="editLiveSession('${s.id}')">عرض / تعديل</button><button class="danger" onclick="liveControl('${s.id}','delete')">حذف نهائي</button></div></article>`;
 return `<article class="participant-card"><h3>${esc(s.title||'مزاد مباشر')} <span class="approval-chip ${s.status==='live'?'ok':''}">${esc(s.status||'scheduled')}</span> <span class="live-session-badge ${mode==='camera'?'camera':''}">${mode==='camera'?'📹 كاميرا حرة':'📦 مُحضّر'}</span> ${s.marketEnabled?'<span class="approval-chip ok">🛍️ السوق مفعل</span>':''}</h3><p>📅 ${esc(liveSessionDate(s))} — ${esc(s.startAt||'بدون موعد')} — ${(s.itemIds||[]).length} مقتنى محضّر — زيادة ${Number(s.bidStep||1)} ر.س</p>${(s.currentItemId||lot)?`<div class="special-admin-note"><b>المفتوح الآن:</b> ${opened} — السعر ${Number(s.currentPrice||0).toLocaleString('ar-SA')} ر.س — ${esc(s.latestBidderName||'لا توجد مزايدة')}</div>`:''}${mode==='prepared'?`<div class="actions">${s.status==='live'?itemButtons:''}</div>`:''}${(s.currentItemId||lot)?`<div class="actions"><button class="gold-action" onclick="liveCloseItem('${s.id}',true)">بيع وإغلاق القطعة</button><button class="ghost" onclick="liveCloseItem('${s.id}',false)">إغلاق دون بيع</button></div>`:''}<div class="actions"><button onclick="editLiveSession('${s.id}')">تعديل</button><a class="gold-action" style="text-decoration:none" href="/live-studio?session=${encodeURIComponent(s.id)}" target="_blank">📹 فتح استوديو الكاميرا</a><button class="gold-action" onclick="liveControl('${s.id}','start')">بدء الجلسة</button><button onclick="liveControl('${s.id}','end')">إنهاء وأرشفة</button><a class="public-link" href="/live-auction" target="_blank">واجهة العملاء</a></div></article>`;
}
async function renderLiveAuctions(){
 if(!$('liveSessions'))return;
 const [lr,items,media]=await Promise.all([api('/api/live-auctions/admin'),all(),api('/api/live-media/status').catch(()=>({configured:false}))]);
 if($('liveMediaStatus')){$('liveMediaStatus').className='live-media-status '+(media.configured?'ok':'warn');$('liveMediaStatus').textContent=media.configured?'✓ خدمة الفيديو الحي جاهزة. الكاميرا والصوت سينتقلان للمشاهدين دون تسجيل.':'⚠ خدمة الفيديو لم تُربط بعد؛ جلسات المزاد تعمل لكن الكاميرا تحتاج إعداد LiveKit.'}
 $('liveItemIds').innerHTML=items.map(i=>`<option value="${esc(i.id)}">${esc(item_title(i))} — ${esc(i.location||'المستودع')}</option>`).join('');
 const sessions=lr.sessions||[], active=sessions.filter(s=>['scheduled','live'].includes(s.status)), archived=sessions.filter(s=>!['scheduled','live'].includes(s.status)).sort((a,b)=>String(b.endedAt||b.updated||'').localeCompare(String(a.endedAt||a.updated||'')));
 const groups={}; archived.forEach(s=>{const d=liveSessionDate(s);(groups[d]||(groups[d]=[])).push(s)});
 const archiveHtml=Object.entries(groups).map(([date,rows])=>`<details class="panel" style="margin-top:10px"><summary style="cursor:pointer;font-weight:900">📁 أرشيف ${esc(date)} — ${rows.length} جلسة</summary><div class="participants-list" style="margin-top:10px">${rows.map(s=>liveSessionCard(s,items,true)).join('')}</div></details>`).join('');
 $('liveSessions').innerHTML=`<div class="auction-title-row"><h3>الجلسات النشطة (${active.length})</h3><span class="muted">الجلسة المنتهية تنتقل تلقائيًا للأرشيف حسب التاريخ.</span></div>${active.map(s=>liveSessionCard(s,items,false)).join('')||'<p>لا توجد جلسات نشطة.</p>'}${archiveHtml?`<div style="margin-top:18px"><h3>🗂️ أرشيف جلسات البث</h3>${archiveHtml}</div>`:''}`;
 window.__liveSessions=sessions;
}
function openLiveEditor(s={}){ $('liveSessionEditor').hidden=false; $('liveSessionId').value=s.id||''; $('liveTitle').value=s.title||''; $('liveStartAt').value=(s.startAt||'').slice(0,16); $('liveDescription').value=s.description||''; if($('liveBidStep')) $('liveBidStep').value=Number(s.bidStep||1); if($('liveMode')) $('liveMode').value=s.mode||((s.itemIds||[]).length?'prepared':'camera'); if($('liveMarketEnabled')) $('liveMarketEnabled').checked=!!s.marketEnabled; [...$('liveItemIds').options].forEach(o=>o.selected=(s.itemIds||[]).map(String).includes(String(o.value))); }
function editLiveSession(id){ openLiveEditor((window.__liveSessions||[]).find(x=>String(x.id)===String(id))||{}); }
async function liveControl(id,action,extra={}){ await api('/api/live-auctions/control',{method:'POST',body:JSON.stringify({id,action,...extra})}); await renderLiveAuctions(); }
async function liveOpenItem(id,itemId){const price=prompt('سعر بداية هذا المقتنى في البث','0');if(price===null)return;await liveControl(id,'open-item',{itemId,price:Number(price||0)});}
async function liveCloseItem(id,sold){if(sold&&!confirm('اعتماد البيع لآخر مزايد وإنشاء طلب تلقائي؟'))return;await liveControl(id,'close-item',{sold});}
window.liveOpenItem=liveOpenItem; window.liveCloseItem=liveCloseItem; window.editLiveSession=editLiveSession; window.liveControl=liveControl;
$('liveAddSession')?.addEventListener('click',async()=>{await renderLiveAuctions();openLiveEditor({mode:'camera'});}); $('cancelLiveEditor')?.addEventListener('click',()=>$('liveSessionEditor').hidden=true); $('saveLiveSession')?.addEventListener('click',async()=>{const itemIds=[...$('liveItemIds').selectedOptions].map(o=>o.value); await api('/api/live-auctions/save',{method:'POST',body:JSON.stringify({id:$('liveSessionId').value,title:$('liveTitle').value,startAt:$('liveStartAt').value,description:$('liveDescription').value,bidStep:Number($('liveBidStep')?.value||1),mode:$('liveMode')?.value||'camera',marketEnabled:!!$('liveMarketEnabled')?.checked,itemIds})}); $('liveSessionEditor').hidden=true; await renderLiveAuctions();});
document.querySelectorAll('[data-v="live-auctions"],.dashboard-go[data-go="live-auctions"]').forEach(b=>b.addEventListener('click',renderLiveAuctions));
