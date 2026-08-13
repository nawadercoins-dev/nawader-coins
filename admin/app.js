const DB = "khazina_db",
  STORE = "items";
let db,
  frontImg = "",
  backImg = "",
  frontImageRemoved = false,
  backImageRemoved = false,
  promptInstall,
  isSaving = false,
  mediaPicking = false;
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
  if (!r.ok || j?.ok === false)
    throw new Error(j?.error || "تعذر الاتصال بقاعدة البيانات المشتركة");
  return j || {};
}
async function all() {
  return (await api("/api/items")).items || [];
}
async function put(x) {
  return api("/api/item", {
    method: "POST",
    body: JSON.stringify({ item: x }),
  });
}
async function del(id) {
  return api("/api/item/" + encodeURIComponent(id), { method: "DELETE" });
}
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
function serialValues() {
  return [...document.querySelectorAll(".serial-input")]
    .map((x) => x.value.trim())
    .filter(Boolean);
}
function renderSerialFields(values) {
  let q = Math.max(1, n("quantity") || 1),
    old = Array.isArray(values)
      ? values
      : [...document.querySelectorAll(".serial-input")].map((x) => x.value),
    fields = Array.from(
      { length: q },
      (_, i) =>
        `<label>القطعة ${i + 1}<input class="serial-input" data-i="${i}" value="${esc(old[i] || "")}" placeholder="الرقم التسلسلي"><small class="muted serial-analysis">${esc(serial(old[i] || ""))}</small></label>`,
    ).join("");
  $("serialFields").innerHTML =
    q > 3
      ? `<details ${q <= 5 ? "open" : ""}><summary>إدخال ${q} أرقام تسلسلية — اضغط للفتح أو الإغلاق</summary><div class="serial-fields-inner">${fields}</div></details>`
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
function updateGradingUI() {
  if ($("gradingFields")) $("gradingFields").hidden = !$("isGraded").checked;
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

function show(vw) {
  document
    .querySelectorAll(".view")
    .forEach((x) => x.classList.toggle("active", x.id === vw));
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
  return `<article class="item auction-item">${i.frontImg ? `<div class="auction-card-image"><img src="${i.frontImg}" onclick="openAdminAuctionImages('${i.id}',0)" title="اضغط لفتح عارض الصور" style="cursor:zoom-in"><span class="auction-state ${ended ? "ended" : "live"}">${ended ? "منتهي" : "نشط"}</span></div>` : '<div class="auction-card-image no-photo">لا توجد صورة</div>'}<div class="auction-card-body"><div class="auction-card-title"><h3>${esc(i.country)} — ${esc(i.denomination)}</h3><span class="approval-chip ${i.auctionApproved ? "ok" : "pending"}">${i.auctionApproved ? "✓ معتمد" : "بانتظار الاعتماد"}</span></div><p class="auction-clock ${ended ? "ended" : ""}" data-end="${esc(i.auctionEnd || "")}">${esc(left || "بدون وقت انتهاء")}</p><div class="auction-admin-metrics"><div><span>السعر الحالي</span><b>${money(i.auctionCurrentPrice || 0)}</b></div><div><span>سعر الفتح</span><b>${money(i.auctionOpeningPrice || i.auctionStartPrice || 0)}</b></div><div><span>قيمة الزيادة</span><b>${money(i.auctionBidStep || 1)}</b></div><div class="private-metric"><span>حد البيع • إدارة فقط</span><b>${money(i.auctionTargetPrice || Number(i.auctionStartPrice || 0) + 1)}</b></div></div><p class="round-chip">الجولة ${Number(i.auctionRound || 1)}</p><div class="actions auction-actions"><button onclick="detail('${i.id}')">عرض</button><button class="ghost" onclick="editItem('${i.id}')">✎ تعديل</button>${ended ? `<button class="gold-action" onclick="openRelaunch('${i.id}')">♻ إعادة المزاد</button>` : ""}<a class="public-link" href="/auction#${i.id}" target="_blank">مشاركة</a></div><div class="bid-list" id="bids-${i.id}" data-round="${Number(i.auctionRound || 1)}"></div></div></article>`;
}

function endedReserveReached(i) {
  return (
    Number(i.auctionCurrentPrice || 0) >=
    Number(i.auctionTargetPrice || Number(i.auctionStartPrice || 0) + 1)
  );
}
function endedAuctionCard(i) {
  let reached = endedReserveReached(i),
    sold = reached && Number(i.auctionCurrentPrice || 0) > 0;
  return `<article class="item auction-item ended-admin-card ${sold ? "sold-ended" : ""}">${i.frontImg ? `<div class="auction-card-image"><img src="${i.frontImg}" onclick="detail('${i.id}')"><span class="auction-state ${sold ? "sold" : "ended"}">${sold ? "✓ تم البيع / فائز" : "انتهى دون بيع"}</span></div>` : '<div class="auction-card-image no-photo">لا توجد صورة</div>'}<div class="auction-card-body"><div class="auction-card-title"><h3>${esc(i.country)} — ${esc(i.denomination)}</h3><span class="approval-chip ${sold ? "ok" : "pending"}">${sold ? "🏆 مزاد ناجح" : "دون حد البيع"}</span></div><p class="ended-date">انتهى: ${esc(i.auctionEnd || "—")}</p><div class="auction-admin-metrics"><div><span>آخر سعر</span><b>${money(i.auctionCurrentPrice || 0)}</b></div><div><span>سعر الفتح السابق</span><b>${money(i.auctionOpeningPrice || i.auctionStartPrice || 0)}</b></div><div><span>الزيادة السابقة</span><b>${money(i.auctionBidStep || 1)}</b></div><div class="private-metric"><span>حد البيع السابق</span><b>${money(i.auctionTargetPrice || Number(i.auctionStartPrice || 0) + 1)}</b></div></div>${sold ? '<p class="sold-order-note">✓ مزاد ناجح — ينشأ طلب الفائز تلقائيًا في الطلبات والشحن.</p>' : ""}<p class="round-chip">الجولة المنتهية ${Number(i.auctionRound || 1)}</p><div class="actions auction-actions"><button onclick="detail('${i.id}')">عرض السجل</button><button class="ghost" onclick="editItem('${i.id}')">✎ تعديل المقتنى</button><button class="gold-action" onclick="openRelaunch('${i.id}')">♻ إعادة إدراج</button></div></div></article>`;
}
async function renderEndedAuctions(a) {
  a = a || (await all());
  let q = (
      document.getElementById("endedAuctionSearch")?.value || ""
    ).toLowerCase(),
    f = document.getElementById("endedAuctionFilter")?.value || "all";
  let ended = a.filter(
    (i) => i.forAuction && auctionText(i.auctionEnd) === "انتهى المزاد",
  );
  let reached = ended.filter(endedReserveReached),
    below = ended.filter((i) => !endedReserveReached(i));
  if ($("endedPageCount")) $("endedPageCount").textContent = ended.length;
  if ($("endedReachedTarget"))
    $("endedReachedTarget").textContent = reached.length;
  if ($("endedBelowTarget")) $("endedBelowTarget").textContent = below.length;
  if ($("endedAuctionsBadge")) {
    $("endedAuctionsBadge").textContent = ended.length;
    $("endedAuctionsBadge").hidden = !ended.length;
  }
  let rows = ended.filter(
    (i) =>
      (f === "all" ||
        (f === "reached" && endedReserveReached(i)) ||
        (f === "below" && !endedReserveReached(i))) &&
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
  const photo = i.frontImg
    ? `<img src="${esc(i.frontImg)}" alt="${esc(`${i.country || ""} ${i.denomination || ""}`)}" loading="lazy">`
    : '<div class="record-no-photo" aria-label="لا توجد صورة"><span>🖼️</span><b>لا توجد صورة</b></div>';
  return `<article class="item record-card">${photo}<div class="record-card-body"><h3>${esc(i.country)} — ${esc(i.denomination)}</h3><div class="record-strips record-strips-v403"><div><span>الفئة</span><b>${esc(i.denomination || "—")}</b></div><div><span>حالة الحفظ</span><b>${esc(i.condition || "—")}</b></div><div class="quantity-stack"><span>الكميات</span><b><em>الكمية الأصلية</em><strong>${Number(i.quantity || 0)}</strong></b><b><em>المباعة</em><strong>${Number(i.soldQuantity || 0)}</strong></b><b><em>المتبقية</em><strong>${remain}</strong></b></div><div class="display-status"><span>حالة العرض</span><b><em>السوق العام</em><strong class="state ${marketState === "نشط" ? "on" : marketState === "غير نشط" ? "off" : "neutral"}">${marketState}</strong></b><b><em>المزاد</em><strong class="state ${auctionState === "نشط" || auctionState.includes("فائز") ? "on" : auctionState === "غير نشط" || auctionState.includes("دون بيع") ? "off" : "neutral"}">${auctionState}</strong></b></div><div><span>موقع التخزين</span><b>${esc(loc(i))}</b></div></div><div class="actions record-actions"><button onclick="detail('${i.id}')">عرض</button><button class="ghost" onclick="editItem('${i.id}')">تعديل</button><button class="danger" onclick="removeItem('${i.id}')">حذف</button></div></div></article>`;
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
        i.soldQuantity,
        (i.serials || []).join(","),
        i.forAuction,
        i.auctionEnd,
        i.forMarket,
        i.marketApproved,
        i.marketSalePrice,
        i.marketUnitPrice,
        i.marketQuantity,
        i.ownerName,
        i.ownerPhone,
        i.purchase,
        i.shipping,
        i.other,
        i.expectedPrice,
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
  return (
    i.marketOfferType === "set" || i.offerType === "set" || i.isSet === true
  );
}
function setSizeClass(i) {
  let p = Number(i.marketSetPieces || i.setPieces || i.quantity || 0);
  return p <= 3 ? "mini" : p <= 5 ? "small" : p <= 10 ? "medium" : "large";
}
function classMatch(i, f, sf) {
  if (f === "graded" && !i.isGraded) return false;
  if (f === "ungraded" && (i.isGraded || isSet(i))) return false;
  if (f === "sets" && !isSet(i)) return false;
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
window.removeItem = async (id) => {
  if (confirm("حذف السجل؟")) {
    try {
      await del(id);
      await refresh(true);
      toast("تم حذف المقتنى.");
    } catch (error) {
      alert("تعذر حذف المقتنى: " + (error?.message || "خطأ غير معروف"));
    }
  }
};
window.detail = async (id) => {
  let i = (await all()).find((x) => x.id === id),
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
      ["الكمية", i.quantity],
      ["المباعة", i.soldQuantity || 0],
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
        "اعتماد المزاد",
        i.forAuction ? (i.auctionApproved ? "معتمد" : "غير معتمد") : "—",
      ],
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
async function renderParticipants() {
  try {
    let r = await api("/api/participants");
    let a = r.participants || [];
    let archived = r.archive || [];
    if ($("pendingParticipantsCount"))
      $("pendingParticipantsCount").textContent = r.pending || 0;
    if ($("participantsTotalCount"))
      $("participantsTotalCount").textContent = r.total || a.length;
    if ($("participantsArchiveCount"))
      $("participantsArchiveCount").textContent = r.archived || archived.length;
    $("participantsList").innerHTML =
      a
        .map(
          (x) =>
            `<div class="participant ${x.approved ? "approved" : "pending"}"><b>${esc(x.name || "")}</b> — ${esc(x.phone || "")}<br><span class="muted">${x.approved && x.verified ? "✅ موثق ومعتمد" : x.approved ? "✅ معتمد إداريًا" : "⏳ بانتظار التحقق/الاعتماد"}</span><br><small class="muted">رمز المشاركة: ${esc(x.id || "")} ${x.created ? "— الطلب: " + new Date(x.created).toLocaleString("ar-SA") : ""}</small><div class="actions"><button onclick="participantSet('${x.id}',true,true)">✅ اعتماد مباشر بدون رمز</button><button class="danger" onclick="participantSet('${x.id}',false,false)">${x.approved ? "إلغاء الاعتماد ونقل للأرشيف" : "رفض ونقل للأرشيف"}</button></div></div>`,
        )
        .join("") || "<p>لا توجد طلبات مشاركة.</p>";
    if ($("participantsArchiveList"))
      $("participantsArchiveList").innerHTML =
        archived
          .map(
            (x) =>
              `<div class="participant archived"><b>${esc(x.name || "")}</b> — ${esc(x.phone || "")}<br><span class="muted">🗄️ ${esc(x.archiveReason || "مؤرشف")}</span><br><small class="muted">رمز المشاركة: ${esc(x.id || "")} ${x.archivedAt ? "— الأرشفة: " + new Date(x.archivedAt).toLocaleString("ar-SA") : ""}</small><div class="actions"><button onclick="participantRestore('${x.id}',false)">↩️ استعادة إلى الانتظار</button><button onclick="participantRestore('${x.id}',true)">✅ استعادة واعتماد</button><button class="danger" onclick="participantDeleteForever('${x.id}')">🗑️ حذف نهائي</button></div></div>`,
          )
          .join("") || "<p>لا يوجد مشاركون في الأرشيف.</p>";
    await refreshParticipantBadge();
  } catch (e) {
    $("participantsList").innerHTML = "<p>تعذر تحميل المشاركين.</p>";
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
window.participantSet = async (id, approved, direct = false) => {
  await api("/api/participant/approve", {
    method: "POST",
    body: JSON.stringify({ id, approved, direct }),
  });
  await renderParticipants();
};
window.participantRestore = async (id, approve = false) => {
  await api("/api/participant/restore", {
    method: "POST",
    body: JSON.stringify({ id, approve }),
  });
  await renderParticipants();
};
window.participantDeleteForever = async (id) => {
  if (!confirm("حذف هذا العميل نهائيًا؟ لا يمكن التراجع عن هذا الإجراء."))
    return;
  await api("/api/participant/delete", {
    method: "POST",
    body: JSON.stringify({ id }),
  });
  await renderParticipants();
};
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
                (b) => `<p>${money(b.amount)} — ${esc(b.bidderName || "")}</p>`,
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
      if (["country", "denomination", "year"].includes(k) && $(k) && !v(k))
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
            if (["country", "denomination", "year"].includes(k) && $(k))
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
  let i = (await all()).find((x) => x.id === id);
  Object.keys(i).forEach((k) => {
    if ($(k) && !["front", "back", "year"].includes(k)) $(k).value = i[k] ?? "";
  });
  if ($("issueEdition")) $("issueEdition").value = i.issueEdition || "";
  if ($("issueEditionOther"))
    $("issueEditionOther").value = i.issueEditionOther || "";
  updateEditionUI();
  fillYearFields(i.year, i.yearFrom, i.yearTo);
  if ($("isGraded")) $("isGraded").checked = !!i.isGraded;
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
  if ($("forMarket")) $("forMarket").checked = !!i.forMarket;
  if ($("marketApproved")) $("marketApproved").checked = !!i.marketApproved;
  if ($("marketPartialAllowed"))
    $("marketPartialAllowed").checked = !!i.marketPartialAllowed;
  if ($("marketNegotiationEnabled"))
    $("marketNegotiationEnabled").checked = !!i.marketNegotiationEnabled;
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
  renderSerialFields(i.serials || [i.serial || ""]);
  updateAuctionUI();
  updateMarketUI();
  show("add");
  window.scrollTo({ top: 0, behavior: "smooth" });
};
$("close").onclick = () => $("dlg").close();
$("quantity").oninput = () => renderSerialFields();
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
if ($("issueEdition")) $("issueEdition").onchange = updateEditionUI;
if ($("yearMode")) $("yearMode").onchange = updateYearUI;
if ($("isGraded")) $("isGraded").onchange = updateGradingUI;
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
    let id = v("id") || newId(),
      old = (await all()).find((x) => x.id === id);
    let year = composedYear();
    $("year").value = year;
    let wantsAuction = $("forAuction").checked,
      wantsMarket = !!$("forMarket")?.checked,
      auctionPublish = wantsAuction && $("auctionApproved").checked,
      marketPublish = wantsMarket && !!$("marketApproved")?.checked;
    if (auctionPublish) {
      let end = v("auctionEnd");
      if (!end)
        throw new Error(
          "اعتماد المزاد للنشر يتطلب تحديد تاريخ ووقت انتهاء المزاد",
        );
      let endMs = new Date(end).getTime();
      if (!Number.isFinite(endMs) || endMs <= Date.now())
        throw new Error("موعد انتهاء المزاد يجب أن يكون في المستقبل");
    }
    if (marketPublish) {
      if (n("marketSalePrice") <= 0)
        throw new Error("اعتماد العرض في السوق يتطلب سعر بيع أكبر من صفر");
      if ((n("marketQuantity") || 0) < 1)
        throw new Error("الكمية المعروضة في السوق يجب أن تكون 1 على الأقل");
    }
    let payload = {
      id,
      country: v("country"),
      denomination: v("denomination"),
      issueEdition: v("issueEdition"),
      issueEditionOther: v("issueEditionOther"),
      year,
      yearFrom: v("yearFrom"),
      yearTo: $("yearMode").value === "range" ? v("yearTo") : "",
      yearMode: v("yearMode"),
      isGraded: $("isGraded").checked,
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
      quantity: n("quantity") || 1,
      soldQuantity: Math.min(
        n("quantity") || 1,
        Math.max(0, n("soldQuantity")),
      ),
      serials: serialValues(),
      serial: serialValues()[0] || "",
      serialType: serial(serialValues()[0] || ""),
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
      forAuction: wantsAuction,
      auctionEnd: wantsAuction ? v("auctionEnd") : "",
      auctionStartPrice: n("auctionStartPrice"),
      auctionOpeningPrice: n("auctionOpeningPrice"),
      auctionBidStep: n("auctionBidStep") || 1,
      auctionTargetPrice: n("auctionTargetPrice"),
      auctionCurrentPrice: n("auctionCurrentPrice"),
      auctionApproved: auctionPublish,
      negotiationEnabled: wantsAuction && $("negotiationEnabled").checked,
      negotiationPercent: n("negotiationPercent") || 5,
      forMarket: wantsMarket,
      marketApproved: marketPublish,
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
      purchase: n("purchase"),
      shipping: n("shipping"),
      other: n("other"),
      expectedPrice: n("expectedPrice"),
      notes: v("notes"),
      updated: Date.now(),
    };
    if (
      payload.specialNumberEnabled &&
      (!Array.isArray(payload.specialNumberTypes) ||
        !payload.specialNumberTypes.length)
    )
      throw new Error(
        "اختر التصنيف: متكرر أو متسلسل أو متطابق أو نادر أو أخطاء نادرة",
      );
    let savedResult = await put(payload);
    if (
      savedResult?.verified !== true ||
      String(savedResult?.saved?.id || "") !== String(id)
    )
      throw new Error("أعاد الخادم نتيجة غير مؤكدة للحفظ؛ بقي النموذج كما هو");
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
    if (auctionPublish) {
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
  let f = $("form");
  if (f && typeof f.reset === "function") f.reset();
  $("id").value = "";
  $("year").value = "";
  $("quantity").value = 1;
  $("soldQuantity").value = 0;
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
  document
    .querySelectorAll(".special-number-type")
    .forEach((x) => (x.checked = false));
  if ($("specialNumberReason")) $("specialNumberReason").value = "";
  if ($("specialNumberFields")) $("specialNumberFields").hidden = true;
  if ($("forMarket")) $("forMarket").checked = false;
  if ($("marketApproved")) $("marketApproved").checked = false;
  if ($("marketOfferType")) $("marketOfferType").value = "single";
  if ($("marketPriceUnit")) $("marketPriceUnit").value = "piece";
  if ($("marketQuantity")) $("marketQuantity").value = "1";
  if ($("marketSetPieces")) $("marketSetPieces").value = "1";
  if ($("marketSetSize")) $("marketSetSize").value = "mini";
  if ($("marketNegotiationPercent")) $("marketNegotiationPercent").value = "5";
  if ($("marketNegotiationEnabled"))
    $("marketNegotiationEnabled").checked = false;
  if ($("marketPartialAllowed")) $("marketPartialAllowed").checked = false;
  updateEditionUI();
  updateYearUI();
  updateGradingUI();
  updateAuctionUI();
  updateMarketUI();
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

// V2.1 إعادة المزاد: جولة مستقلة تحفظ سجل الجولة السابقة ولا تخلط مزايداتها بالجولة الجديدة.
function localDateTimeValue(d) {
  let z = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}T${z(d.getHours())}:${z(d.getMinutes())}`;
}
window.openRelaunch = async (id) => {
  let i = (await all()).find((x) => x.id === id);
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
  return `<article class="item market-admin-card">${i.frontImg ? `<button type="button" class="market-image-button" onclick='openCoinLightbox(${JSON.stringify(imgs)},0,${JSON.stringify(title)})' title="فتح عارض الصور"><img src="${i.frontImg}" alt="${esc(title)}"><span class="market-image-hint">⛶ تكبير الصور</span></button>` : '<div class="market-image-button market-no-photo">لا توجد صورة</div>'}<div class="market-admin-body"><h3>${esc(title)}</h3><p class="market-status-row"><span class="badge market-badge">${marketTypeLabel(i.marketOfferType)}</span> <span class="approval-chip ${i.marketApproved ? "ok" : "bad"}">${i.marketApproved ? "نشط" : "غير نشط"}</span></p><div class="market-admin-metrics"><b>سعر ${ul}: ${money(price)}</b><span>المتاح ${left} من ${qty} ${i.marketOfferType === "set" ? "طقم" : i.marketOfferType === "bundle" ? "حزمة" : "وحدة"}</span>${i.marketSetPieces ? `<span>داخل الوحدة ${Number(i.marketSetPieces)} قطعة/ورقة</span>` : ""}</div><p class="market-negotiation">${i.marketNegotiationEnabled ? `التفاوض حتى ${Number(i.marketNegotiationPercent || 0)}%` : "سعر ثابت"}</p><div class="actions market-admin-actions">${imgs.length ? `<button class="ghost" onclick='openCoinLightbox(${JSON.stringify(imgs)},0,${JSON.stringify(title)})'>⛶ الصور</button>` : ""}<button onclick="editItem('${i.id}')">تعديل</button><a class="public-link" href="/market#${i.id}" target="_blank">عرض في السوق</a></div></div></article>`;
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
async function renderMarketAdmin(items) {
  if (!$("marketAdminItems")) return;
  let a = Array.isArray(items) ? items : await all(),
    m = a.filter((i) => i.forMarket),
    map = Object.fromEntries(a.map((i) => [String(i.id), i]));
  $("marketPublishedCount").textContent = m.filter(
    (i) => i.marketApproved,
  ).length;
  $("marketAdminItems").innerHTML =
    m
      .filter((i) => classMatch(i, marketFilter, marketSetFilter))
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
      await api("/api/settings", {
        method: "POST",
        body: JSON.stringify({
          buyerFeePercent: Number($("settingsBuyerFee").value || 0),
          charityProfitPercent: Number($("settingsCharity").value || 0),
          auctionEntryFee: Number($("settingsEntryFee").value || 0),
          entryFeeEnabled: !!$("settingsEntryEnabled").checked,
          platformName: $("platformName").value.trim() || "نوادر العملات",
          adminEmail: $("adminEmail").value.trim(),
          ocrTesseractPath: $("ocrTesseractPath")
            ? $("ocrTesseractPath").value.trim()
            : "",
        }),
      });
      st.textContent = "✅ تم حفظ الإعدادات.";
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
          return `<article class="notification-row ${x.read ? "" : "unread"}"><span class="notification-icon">${notificationIcon(x.category)}</span><div><b>${esc(x.title)}</b><p>${esc(x.message)}</p><small>${fmtDate(x.created)}</small></div><div class="actions notification-actions">${approval ? `<button type="button" onclick="approveParticipantFromNotification('${esc(x.participantId)}',true)">✅ اعتماد مباشر</button><button type="button" class="danger" onclick="approveParticipantFromNotification('${esc(x.participantId)}',false)">❌ رفض/إلغاء</button><button type="button" class="ghost" onclick="openParticipantsFromNotification()">عرض المشاركين</button>` : x.actionUrl ? `<a href="${esc(x.actionUrl)}" class="ghost button-link">فتح</a>` : ""}</div></article>`;
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
window.approveParticipantFromNotification = async (id, approved) => {
  try {
    if (!approved && !confirm("هل تريد رفض/إلغاء اعتماد هذا الحساب؟")) return;
    await api("/api/participant/approve", {
      method: "POST",
      body: JSON.stringify({ id, approved, direct: approved }),
    });
    await renderAdminNotifications();
    await refreshParticipantBadge();
    alert(
      approved
        ? "✅ تم اعتماد الحساب مباشرة وأصبح بإمكانه المشاركة."
        : "تم رفض/إلغاء اعتماد الحساب.",
    );
  } catch (e) {
    alert("تعذر تنفيذ الاعتماد: " + e.message);
  }
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
          return `<article class="permission-row"><div class="permission-user"><b>${esc(x.name || "مشارك")}</b><span>${esc(x.phone || "")}</span><small>${x.verified ? "موثق" : "غير موثق"} • ${x.approved ? "معتمد" : "غير معتمد"}</small></div><div class="permission-options">${permissionCheck(x.id, "sellerEndedAuctions", p.sellerEndedAuctions)}${permissionCheck(x.id, "sellerMarket", p.sellerMarket)}${permissionCheck(x.id, "marketSupervision", p.marketSupervision)}${permissionCheck(x.id, "auctionSupervision", p.auctionSupervision)}${permissionCheck(x.id, "ordersView", p.ordersView)}${permissionCheck(x.id, "ordersManage", p.ordersManage)}</div><button type="button" class="save-permissions" data-pid="${esc(x.id)}">حفظ الصلاحيات</button></article>`;
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
  if (vw === "permissions") await renderPermissions();
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
  return (
    b +
    `<button class="ghost" onclick="orderStatus('${o.id}','stalled')">متعثر</button><button class="ghost" onclick="orderStatus('${o.id}','returned')">مرتجع</button><button class="danger" onclick="orderStatus('${o.id}','cancelled')">ملغي</button>`
  );
}
function orderCard(o) {
  let imgs = (o.items || []).flatMap((x) => x.images || []).filter(Boolean);
  let itemHtml = (o.items || [])
    .map(
      (x) =>
        `<div class="order-item">${(x.images || [])[0] ? `<img class="order-thumb" style="width:96px;height:72px;max-width:96px;max-height:72px;object-fit:contain" src="${esc((x.images || [])[0])}" onclick='openCoinLightbox(${JSON.stringify(x.images || [])},0,${JSON.stringify(x.title || "")})'>` : ""}<div><b>${esc(x.title || "مقتنى")}</b><div>الكمية: ${Number(x.quantity || 1)} • ${money(x.total || 0)}</div><div class="storage-path">${esc(storageText(x.storage || {}))}</div></div></div>`,
    )
    .join("");
  return `<article class="order-card ${o.archived ? "archived-order" : ""}"><div class="order-head"><div><h3>${esc(o.orderNumber || o.id)}</h3><small>${new Date(o.created).toLocaleString("ar-SA")}</small></div><div><span class="source-chip">${o.source === "auction" ? "مزاد" : "السوق العام"}</span> <span class="order-status">${ORDER_LABELS[o.status] || esc(o.status)}</span></div></div><div class="order-body"><div class="order-grid"><div class="order-info"><span>العميل</span><b>${esc(o.customerName || "—")}</b><br>${esc(o.customerPhone || "")}</div><div class="order-info"><span>السداد</span><b>${o.paymentStatus === "paid" ? "تم السداد" : "غير مسدد"}</b></div><div class="order-info"><span>الإجمالي</span><b>${money(o.total || 0)}</b></div><div class="order-info"><span>الشحن</span><b>${esc(o.shippingCompany || "لم يسجل")}</b><br>${esc(o.trackingNumber || "")}</div></div>${itemHtml}<div class="order-shipping-fields"><input id="shipco-${o.id}" value="${esc(o.shippingCompany || "")}" placeholder="شركة الشحن"><input id="track-${o.id}" value="${esc(o.trackingNumber || "")}" placeholder="رقم التتبع"></div><div class="order-actions"><button class="ghost" onclick="saveShipping('${o.id}')">حفظ الشحن والتتبع</button>${orderNextButtons(o)}<button class="ghost" onclick="printOrder('${o.id}')">🖨 طباعة ملخص/فاتورة</button></div></div></article>`;
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
window.saveShipping = async (id) => {
  try {
    await api("/api/order/shipping", {
      method: "POST",
      body: JSON.stringify({
        id,
        shippingCompany: $("shipco-" + id)?.value || "",
        trackingNumber: $("track-" + id)?.value || "",
      }),
    });
    await renderOrders();
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
// Make record images open lightbox without disturbing existing buttons
setInterval(
  () =>
    document.querySelectorAll(".record-card img").forEach((img) => {
      if (img.dataset.lbready) return;
      img.dataset.lbready = "1";
      img.style.cursor = "zoom-in";
      img.addEventListener("click", (e) => {
        e.stopPropagation();
        openCoinLightbox([img.src], 0, "صورة المقتنى");
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

// V4.0.11 — customer collectible approval workflow
function collectibleApprovalStatus(s) {
  return s === "approved"
    ? "معتمد"
    : s === "needs_changes"
      ? "يحتاج استكمال"
      : s === "rejected"
        ? "مرفوض"
        : "قيد المراجعة";
}
async function renderCollectibleApprovals() {
  if (!$("collectibleApprovalsList")) return;
  try {
    let r = await api("/api/collectible-submissions/admin"),
      rows = r.submissions || [];
    $("collectiblePendingCount").textContent = r.pending || 0;
    $("collectibleNeedsCount").textContent = r.needsChanges || 0;
    $("collectibleTotalCount").textContent = rows.length;
    let badge = $("collectibleApprovalsBadge");
    if (badge) {
      let n = (r.pending || 0) + (r.needsChanges || 0);
      badge.textContent = n;
      badge.hidden = !n;
    }
    $("collectibleApprovalsList").innerHTML =
      rows
        .map(
          (x) =>
            `<article class="collectible-approval-card"><div class="collectible-approval-images">${x.frontImage ? `<img src="${x.frontImage}" onclick='openCoinLightbox([${JSON.stringify(x.frontImage)},${JSON.stringify(x.backImage || "")}].filter(Boolean),0,${JSON.stringify((x.country || "") + " — " + (x.denomination || ""))})'>` : ""}${x.backImage ? `<img src="${x.backImage}" onclick='openCoinLightbox([${JSON.stringify(x.frontImage || "")},${JSON.stringify(x.backImage)}].filter(Boolean),${x.frontImage ? 1 : 0},${JSON.stringify((x.country || "") + " — " + (x.denomination || ""))})'>` : ""}</div><div class="collectible-approval-info"><h3>${esc(x.country)} — ${esc(x.denomination)}</h3><div><b>${esc(x.participantName || "عميل")}</b> — ${esc(x.participantPhone || "")}</div><div class="collectible-meta"><span>${esc(x.year || "بدون سنة")}</span><span>${esc(x.condition || "—")}</span>${x.serial ? `<span>رقم: ${esc(x.serial)}</span>` : ""}<span>الرغبة: ${x.desiredDestination === "market" ? "السوق" : x.desiredDestination === "auction" ? "المزاد" : "المقتنيات"}</span><span class="collectible-state ${esc(x.status)}">${collectibleApprovalStatus(x.status)}</span></div>${x.notes ? `<p>${esc(x.notes)}</p>` : ""}${x.itemId ? `<p><b>أضيف للسجل:</b> ${esc(x.itemId)}</p>` : ""}<textarea id="cap-note-${esc(x.id)}" class="collectible-admin-note" placeholder="ملاحظة للعميل عند طلب الاستكمال أو الرفض">${esc(x.adminNote || "")}</textarea><div class="collectible-actions"><button class="approve" onclick="setCollectibleApproval('${esc(x.id)}','approved')" ${x.status === "approved" ? "disabled" : ""}>✓ اعتماد وإضافة للسجل</button><button class="changes" onclick="setCollectibleApproval('${esc(x.id)}','needs_changes')">✎ طلب استكمال</button><button class="reject" onclick="setCollectibleApproval('${esc(x.id)}','rejected')">رفض</button></div><small>${x.created ? new Date(x.created).toLocaleString("ar-SA") : ""}</small></div></article>`,
        )
        .join("") ||
      '<p class="muted">لا توجد طلبات اعتماد مقتنيات حتى الآن.</p>';
  } catch (e) {
    $("collectibleApprovalsList").textContent =
      "تعذر تحميل طلبات الاعتماد: " + e.message;
  }
}
window.setCollectibleApproval = async (id, status) => {
  try {
    let note = $("cap-note-" + id)?.value || "";
    if (
      status === "rejected" &&
      !note.trim() &&
      !confirm("لم تكتب سبب الرفض. هل تريد المتابعة؟")
    )
      return;
    await api("/api/collectible-submissions/status", {
      method: "POST",
      body: JSON.stringify({ id, status, note }),
    });
    await renderCollectibleApprovals();
    await renderAdminNotifications();
    await refresh(true);
  } catch (e) {
    alert(e.message);
  }
};
if ($("refreshCollectibleApprovals"))
  $("refreshCollectibleApprovals").onclick = renderCollectibleApprovals;
document
  .querySelectorAll(
    'nav button[data-v="collectible-approvals"],.dashboard-go[data-go="collectible-approvals"]',
  )
  .forEach((b) => b.addEventListener("click", renderCollectibleApprovals));
setTimeout(renderCollectibleApprovals, 600);

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
