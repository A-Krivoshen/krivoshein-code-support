/**
 * KRV AI Popup Assistant — vanilla embed (v=20260730c)
 * CSS is injected as <style> (no cross-origin stylesheet issues).
 */
(function () {
  "use strict";

  if (window.__krvAssistantLoaded) return;
  window.__krvAssistantLoaded = true;

  var script =
    document.currentScript ||
    (function () {
      var list = document.getElementsByTagName("script");
      return list[list.length - 1];
    })();

  var API =
    (script && script.getAttribute("data-api")) ||
    "https://support.krivoshein.site/api/v1";
  var SIDE = (script && script.getAttribute("data-side")) || "right";

  var STORAGE_KEY = "krv_assistant_session_v1";
  var EMBEDDED_CSS = "/* KRV Web AI Assistant \u2014 clean technical UI (right-bottom)\n * Avoids landing mobile-cta-bar (~z-index 60, ~64px) via --krv-a-stack-bottom.\n */\n.krv-assistant {\n  --krv-a-bg: #ffffff;\n  --krv-a-bg-soft: #f8fafc;\n  --krv-a-bg-msg: #f1f5f9;\n  --krv-a-line: #e2e8f0;\n  --krv-a-ink: #0f172a;\n  --krv-a-mute: #64748b;\n  --krv-a-accent: #315fe8;\n  --krv-a-accent-h: #244ac2;\n  --krv-a-accent-soft: #eef4ff;\n  --krv-a-user: #315fe8;\n  --krv-a-shadow: 0 4px 6px -1px rgba(15, 23, 42, 0.06),\n    0 16px 40px -8px rgba(15, 23, 42, 0.18);\n  --krv-a-radius: 16px;\n  --krv-a-radius-sm: 10px;\n  /* Above page content & mobile CTA (60) / cookie (90); below rare system modals */\n  --krv-a-z: 120;\n  /* JS sets --krv-a-stack-bottom to clear fixed bottom bars; CSS fallback for mobile CTA */\n  --krv-a-stack-bottom: 16px;\n  --krv-a-edge: 16px;\n  --krv-a-gap: 10px;\n  --krv-a-bubble-size: 56px;\n  --krv-a-w: min(360px, calc(100vw - 24px));\n  --krv-a-h: min(\n    520px,\n    calc(\n      100dvh - var(--krv-a-stack-bottom) - env(safe-area-inset-bottom, 0px) -\n        var(--krv-a-bubble-size) - var(--krv-a-gap) - 16px\n    )\n  );\n\n  position: fixed;\n  z-index: var(--krv-a-z);\n  right: max(var(--krv-a-edge), env(safe-area-inset-right, 0px));\n  bottom: calc(\n    var(--krv-a-stack-bottom) + env(safe-area-inset-bottom, 0px)\n  );\n  left: auto;\n  display: flex;\n  flex-direction: column;\n  align-items: flex-end;\n  gap: var(--krv-a-gap);\n  color: var(--krv-a-ink);\n  line-height: 1.45;\n  font-size: 14px;\n  font-family: Inter, system-ui, -apple-system, \"Segoe UI\", Roboto, Arial, sans-serif;\n  -webkit-font-smoothing: antialiased;\n  /* Don't trap page scroll when closed */\n  pointer-events: none;\n  max-width: calc(100vw - 16px);\n}\n\n/* Only interactive pieces receive clicks */\n.krv-assistant .krv-a-bubble,\n.krv-assistant .krv-a-panel {\n  pointer-events: auto;\n}\n\n.krv-assistant[data-side=\"left\"] {\n  left: max(var(--krv-a-edge), env(safe-area-inset-left, 0px));\n  right: auto;\n  align-items: flex-start;\n}\n\n/* Mobile: clear fixed .mobile-cta-bar (~64\u201372px) even before JS measures */\n@media (max-width: 767.98px) {\n  .krv-assistant {\n    --krv-a-stack-bottom: 76px;\n    --krv-a-edge: 12px;\n    --krv-a-bubble-size: 52px;\n  }\n}\n\n/* Very small phones (SE / 375) */\n@media (max-width: 380px) {\n  .krv-assistant {\n    --krv-a-stack-bottom: 80px;\n    --krv-a-edge: 10px;\n    --krv-a-bubble-size: 48px;\n    --krv-a-gap: 8px;\n  }\n}\n\n/* Desktop / tablet: no mobile bar */\n@media (min-width: 768px) {\n  .krv-assistant {\n    --krv-a-stack-bottom: 16px;\n    --krv-a-edge: 20px;\n    --krv-a-bubble-size: 56px;\n  }\n}\n\n.krv-assistant *,\n.krv-assistant *::before,\n.krv-assistant *::after {\n  box-sizing: border-box;\n}\n\n/* \u2014\u2014 Bubble \u2014\u2014 */\n.krv-assistant .krv-a-bubble {\n  width: var(--krv-a-bubble-size);\n  height: var(--krv-a-bubble-size);\n  flex: 0 0 auto;\n  border: 0;\n  border-radius: 50%;\n  cursor: pointer;\n  display: inline-flex;\n  align-items: center;\n  justify-content: center;\n  background: var(--krv-a-accent);\n  color: #fff;\n  box-shadow: 0 8px 24px rgba(49, 95, 232, 0.35);\n  transition: transform 0.15s ease, background 0.15s ease, box-shadow 0.15s ease;\n  padding: 0;\n}\n\n.krv-assistant .krv-a-bubble:hover {\n  background: var(--krv-a-accent-h);\n  transform: translateY(-1px);\n  box-shadow: 0 10px 28px rgba(49, 95, 232, 0.42);\n}\n\n.krv-assistant .krv-a-bubble:active {\n  transform: translateY(0);\n}\n\n.krv-assistant .krv-a-bubble:focus-visible {\n  outline: 2px solid var(--krv-a-accent);\n  outline-offset: 3px;\n}\n\n.krv-assistant .krv-a-bubble svg {\n  width: 24px;\n  height: 24px;\n  display: block;\n  fill: none;\n  stroke: currentColor;\n  stroke-width: 2;\n  stroke-linecap: round;\n  stroke-linejoin: round;\n}\n\n.krv-assistant.is-open .krv-a-bubble {\n  background: #1e293b;\n  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.2);\n}\n\n/* \u2014\u2014 Panel \u2014\u2014 */\n.krv-assistant .krv-a-panel {\n  display: none;\n  width: var(--krv-a-w);\n  height: var(--krv-a-h);\n  max-height: var(--krv-a-h);\n  max-width: 100%;\n  flex-direction: column;\n  background: var(--krv-a-bg);\n  border: 1px solid var(--krv-a-line);\n  border-radius: var(--krv-a-radius);\n  box-shadow: var(--krv-a-shadow);\n  overflow: hidden;\n  /* Keep panel inside viewport horizontally */\n  margin-right: 0;\n  margin-left: 0;\n}\n\n.krv-assistant.is-open .krv-a-panel {\n  display: flex;\n}\n\n/* When open on mobile, lock body scroll slightly less invasive: overscroll contain */\n.krv-assistant.is-open .krv-a-panel,\n.krv-assistant.is-open .krv-a-msgs {\n  overscroll-behavior: contain;\n}\n\n/* Header */\n.krv-assistant .krv-a-head {\n  flex: 0 0 auto;\n  display: flex;\n  align-items: center;\n  justify-content: space-between;\n  gap: 12px;\n  padding: 14px 14px 12px;\n  background: var(--krv-a-bg);\n  border-bottom: 1px solid var(--krv-a-line);\n}\n\n.krv-assistant .krv-a-head-left {\n  display: flex;\n  align-items: center;\n  gap: 10px;\n  min-width: 0;\n}\n\n.krv-assistant .krv-a-avatar {\n  width: 36px;\n  height: 36px;\n  border-radius: 10px;\n  flex: 0 0 auto;\n  display: flex;\n  align-items: center;\n  justify-content: center;\n  background: var(--krv-a-accent-soft);\n  color: var(--krv-a-accent);\n  font-size: 13px;\n  font-weight: 700;\n  letter-spacing: -0.02em;\n}\n\n.krv-assistant .krv-a-titles {\n  min-width: 0;\n}\n\n.krv-assistant .krv-a-head h2 {\n  margin: 0;\n  font-size: 14px;\n  font-weight: 650;\n  letter-spacing: -0.01em;\n  color: var(--krv-a-ink);\n  line-height: 1.25;\n  white-space: nowrap;\n  overflow: hidden;\n  text-overflow: ellipsis;\n}\n\n.krv-assistant .krv-a-head p {\n  margin: 2px 0 0;\n  font-size: 12px;\n  color: var(--krv-a-mute);\n  line-height: 1.3;\n  white-space: nowrap;\n  overflow: hidden;\n  text-overflow: ellipsis;\n}\n\n.krv-assistant .krv-a-close {\n  flex: 0 0 auto;\n  width: 32px;\n  height: 32px;\n  border: 0;\n  border-radius: 8px;\n  background: transparent;\n  color: var(--krv-a-mute);\n  cursor: pointer;\n  font-size: 20px;\n  line-height: 1;\n  display: inline-flex;\n  align-items: center;\n  justify-content: center;\n  padding: 0;\n}\n\n.krv-assistant .krv-a-close:hover {\n  background: var(--krv-a-bg-soft);\n  color: var(--krv-a-ink);\n}\n\n/* Messages */\n.krv-assistant .krv-a-msgs {\n  flex: 1 1 auto;\n  min-height: 0;\n  overflow-x: hidden;\n  overflow-y: auto;\n  padding: 12px 12px 8px;\n  display: flex;\n  flex-direction: column;\n  gap: 8px;\n  background: var(--krv-a-bg-soft);\n  -webkit-overflow-scrolling: touch;\n}\n\n.krv-assistant .krv-a-msg {\n  max-width: 88%;\n  padding: 9px 12px;\n  border-radius: 12px;\n  white-space: pre-wrap;\n  word-break: break-word;\n  font-size: 13px;\n  line-height: 1.45;\n}\n\n.krv-assistant .krv-a-msg.bot {\n  align-self: flex-start;\n  background: var(--krv-a-bg);\n  border: 1px solid var(--krv-a-line);\n  color: var(--krv-a-ink);\n  border-bottom-left-radius: 4px;\n}\n\n.krv-assistant .krv-a-msg.user {\n  align-self: flex-end;\n  background: var(--krv-a-user);\n  color: #fff;\n  border-bottom-right-radius: 4px;\n}\n\n.krv-assistant .krv-a-msg.sys {\n  align-self: center;\n  max-width: 100%;\n  background: transparent;\n  color: var(--krv-a-mute);\n  font-size: 11.5px;\n  padding: 2px 6px;\n  text-align: center;\n}\n\n.krv-assistant .krv-a-typing {\n  align-self: flex-start;\n  color: var(--krv-a-mute);\n  font-size: 12px;\n  padding: 2px 4px;\n}\n\n/* Quick replies */\n.krv-assistant .krv-a-quick {\n  flex: 0 0 auto;\n  display: flex;\n  flex-wrap: wrap;\n  gap: 6px;\n  padding: 8px 12px 0;\n  background: var(--krv-a-bg);\n}\n\n.krv-assistant .krv-a-quick:empty {\n  display: none;\n}\n\n.krv-assistant .krv-a-chip {\n  border: 1px solid var(--krv-a-line);\n  background: var(--krv-a-bg);\n  color: var(--krv-a-ink);\n  border-radius: 999px;\n  padding: 6px 11px;\n  font-size: 12px;\n  line-height: 1.2;\n  cursor: pointer;\n  transition: border-color 0.12s ease, background 0.12s ease, color 0.12s ease;\n}\n\n.krv-assistant .krv-a-chip:hover {\n  border-color: #93b0f5;\n  background: var(--krv-a-accent-soft);\n  color: var(--krv-a-accent);\n}\n\n/* Handoff links */\n.krv-assistant .krv-a-handoff {\n  flex: 0 0 auto;\n  display: flex;\n  flex-wrap: wrap;\n  gap: 6px;\n  padding: 8px 12px;\n  background: var(--krv-a-bg);\n  border-bottom: 1px solid var(--krv-a-line);\n}\n\n.krv-assistant .krv-a-handoff:empty {\n  display: none;\n  border-bottom: 0;\n  padding: 0;\n}\n\n.krv-assistant .krv-a-handoff a,\n.krv-assistant .krv-a-handoff button.krv-a-chip {\n  font-size: 11.5px;\n  color: var(--krv-a-accent);\n  text-decoration: none;\n  border: 1px solid var(--krv-a-line);\n  border-radius: 999px;\n  padding: 5px 10px;\n  background: var(--krv-a-bg-soft);\n  cursor: pointer;\n  font-family: inherit;\n  line-height: 1.2;\n}\n\n.krv-assistant .krv-a-handoff a:hover,\n.krv-assistant .krv-a-handoff button.krv-a-chip:hover {\n  border-color: #93b0f5;\n  background: var(--krv-a-accent-soft);\n}\n\n/* Lead form */\n.krv-assistant .krv-a-form {\n  display: none;\n  flex: 0 0 auto;\n  flex-direction: column;\n  gap: 8px;\n  padding: 10px 12px 12px;\n  border-top: 1px solid var(--krv-a-line);\n  background: var(--krv-a-bg);\n  max-height: 55%;\n  overflow-y: auto;\n}\n\n.krv-assistant .krv-a-form.is-on {\n  display: flex;\n}\n\n.krv-assistant .krv-a-form-title {\n  margin: 0 0 2px;\n  font-size: 12.5px;\n  font-weight: 650;\n  color: var(--krv-a-ink);\n}\n\n.krv-assistant .krv-a-field {\n  display: flex;\n  flex-direction: column;\n  gap: 4px;\n  margin: 0;\n}\n\n.krv-assistant .krv-a-field > span {\n  font-size: 11px;\n  font-weight: 500;\n  color: var(--krv-a-mute);\n}\n\n.krv-assistant .krv-a-field-row {\n  display: grid;\n  grid-template-columns: 1fr 1fr;\n  gap: 8px;\n}\n\n.krv-assistant .krv-a-form input,\n.krv-assistant .krv-a-form textarea,\n.krv-assistant .krv-a-form select {\n  width: 100%;\n  margin: 0;\n  border: 1px solid var(--krv-a-line);\n  background: var(--krv-a-bg);\n  color: var(--krv-a-ink);\n  border-radius: var(--krv-a-radius-sm);\n  padding: 8px 10px;\n  font-size: 13px;\n  font-family: inherit;\n  line-height: 1.35;\n  min-height: 38px;\n  appearance: none;\n  -webkit-appearance: none;\n}\n\n.krv-assistant .krv-a-form textarea {\n  min-height: 64px;\n  max-height: 100px;\n  resize: vertical;\n}\n\n.krv-assistant .krv-a-form select {\n  background-image: url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2364748b' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E\");\n  background-repeat: no-repeat;\n  background-position: right 10px center;\n  padding-right: 28px;\n}\n\n.krv-assistant .krv-a-form input:focus,\n.krv-assistant .krv-a-form textarea:focus,\n.krv-assistant .krv-a-form select:focus {\n  outline: none;\n  border-color: var(--krv-a-accent);\n  box-shadow: 0 0 0 3px rgba(49, 95, 232, 0.15);\n}\n\n.krv-assistant .krv-a-form input::placeholder,\n.krv-assistant .krv-a-form textarea::placeholder {\n  color: #94a3b8;\n}\n\n.krv-assistant .krv-a-hp {\n  position: absolute !important;\n  left: -10000px !important;\n  width: 1px !important;\n  height: 1px !important;\n  overflow: hidden !important;\n  opacity: 0 !important;\n  pointer-events: none !important;\n}\n\n.krv-assistant .krv-a-form-actions {\n  display: flex;\n  gap: 8px;\n  margin-top: 2px;\n}\n\n.krv-assistant .krv-a-btn {\n  border: 0;\n  border-radius: var(--krv-a-radius-sm);\n  padding: 9px 12px;\n  font-size: 13px;\n  font-weight: 600;\n  font-family: inherit;\n  cursor: pointer;\n  line-height: 1.2;\n  min-height: 38px;\n}\n\n.krv-assistant .krv-a-btn.primary {\n  background: var(--krv-a-accent);\n  color: #fff;\n  flex: 1;\n}\n\n.krv-assistant .krv-a-btn.primary:hover {\n  background: var(--krv-a-accent-h);\n}\n\n.krv-assistant .krv-a-btn.ghost {\n  background: var(--krv-a-bg);\n  color: var(--krv-a-mute);\n  border: 1px solid var(--krv-a-line);\n  flex: 0 0 auto;\n  min-width: 88px;\n}\n\n.krv-assistant .krv-a-btn.ghost:hover {\n  color: var(--krv-a-ink);\n  background: var(--krv-a-bg-soft);\n}\n\n/* Composer */\n.krv-assistant .krv-a-composer {\n  flex: 0 0 auto;\n  display: flex;\n  align-items: flex-end;\n  gap: 8px;\n  padding: 10px 12px 12px;\n  border-top: 1px solid var(--krv-a-line);\n  background: var(--krv-a-bg);\n}\n\n.krv-assistant .krv-a-composer.is-hidden {\n  display: none;\n}\n\n.krv-assistant .krv-a-composer textarea {\n  flex: 1 1 auto;\n  width: 100%;\n  min-height: 40px;\n  max-height: 96px;\n  margin: 0;\n  border: 1px solid var(--krv-a-line);\n  background: var(--krv-a-bg-soft);\n  color: var(--krv-a-ink);\n  border-radius: 12px;\n  padding: 10px 12px;\n  font-size: 13px;\n  font-family: inherit;\n  line-height: 1.4;\n  resize: none;\n}\n\n.krv-assistant .krv-a-composer textarea:focus {\n  outline: none;\n  border-color: var(--krv-a-accent);\n  background: var(--krv-a-bg);\n  box-shadow: 0 0 0 3px rgba(49, 95, 232, 0.12);\n}\n\n.krv-assistant .krv-a-send {\n  flex: 0 0 auto;\n  width: 40px;\n  height: 40px;\n  border: 0;\n  border-radius: 12px;\n  background: var(--krv-a-accent);\n  color: #fff;\n  cursor: pointer;\n  display: inline-flex;\n  align-items: center;\n  justify-content: center;\n  padding: 0;\n  font-size: 16px;\n  font-weight: 600;\n  line-height: 1;\n}\n\n.krv-assistant .krv-a-send:hover {\n  background: var(--krv-a-accent-h);\n}\n\n.krv-assistant .krv-a-send:disabled {\n  opacity: 0.5;\n  cursor: not-allowed;\n}\n\n/* Mobile width/form */\n@media (max-width: 480px) {\n  .krv-assistant {\n    --krv-a-w: min(calc(100vw - 20px), 400px);\n    width: auto;\n    max-width: calc(100vw - 16px);\n  }\n\n  .krv-assistant .krv-a-field-row {\n    grid-template-columns: 1fr;\n  }\n\n  .krv-assistant .krv-a-bubble svg {\n    width: 22px;\n    height: 22px;\n  }\n}\n\n/* Prefer reduced motion */\n@media (prefers-reduced-motion: reduce) {\n  .krv-assistant .krv-a-bubble {\n    transition: none;\n  }\n}\n";

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function loadCss() {
    if (document.getElementById("krv-assistant-css")) return;
    var style = document.createElement("style");
    style.id = "krv-assistant-css";
    style.type = "text/css";
    style.appendChild(document.createTextNode(EMBEDDED_CSS));
    document.head.appendChild(style);
  }

  function isVisible(el) {
    if (!el) return false;
    var cs = window.getComputedStyle(el);
    if (cs.display === "none" || cs.visibility === "hidden" || cs.opacity === "0") {
      return false;
    }
    var r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  }

  function updateStackOffset(root) {
    if (!root) return;
    var base = 16;
    var vh = window.innerHeight || document.documentElement.clientHeight || 0;
    var maxBottom = 0;

    function consider(el, pad) {
      if (!isVisible(el)) return;
      var cs = window.getComputedStyle(el);
      if (cs.position !== "fixed" && cs.position !== "sticky") return;
      var r = el.getBoundingClientRect();
      if (r.bottom < vh - 2) return;
      if (r.top > vh - 8) return;
      var h = Math.ceil(r.height);
      if (h > maxBottom) maxBottom = h + (pad || 10);
    }

    document.querySelectorAll(".mobile-cta-bar").forEach(function (el) {
      consider(el, 12);
    });
    document.querySelectorAll(".krv-cookie, #krv-cookie").forEach(function (el) {
      if (el.hasAttribute("hidden")) return;
      if (el.classList && el.classList.contains("is-hidden")) return;
      consider(el, 10);
    });

    if (maxBottom < 40 && window.matchMedia && window.matchMedia("(max-width: 767.98px)").matches) {
      var bar = document.querySelector(".mobile-cta-bar");
      if (bar) {
        var d = window.getComputedStyle(bar).display;
        if (d !== "none") maxBottom = Math.max(maxBottom, 76);
      } else if (document.body && document.body.classList.contains("has-mobile-cta")) {
        maxBottom = Math.max(maxBottom, 76);
      }
    }

    var stack = Math.max(base, maxBottom);
    var cap = Math.max(16, Math.floor(vh * 0.35));
    if (stack > cap) stack = cap;
    root.style.setProperty("--krv-a-stack-bottom", stack + "px");
  }


  function getSession() {
    try {
      return localStorage.getItem(STORAGE_KEY) || "";
    } catch (e) {
      return "";
    }
  }

  function setSession(id) {
    try {
      localStorage.setItem(STORAGE_KEY, id);
    } catch (e) {}
  }

  function hostPath() {
    return { host: location.hostname, path: location.pathname || "/" };
  }

  function iconChat() {
    return (
      '<svg viewBox="0 0 24 24" aria-hidden="true">' +
      '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>' +
      "</svg>"
    );
  }

  function createUI() {
    var wrap = document.createElement("div");
    wrap.className = "krv-assistant";
    wrap.setAttribute("data-side", SIDE === "left" ? "left" : "right");
    wrap.setAttribute("aria-live", "polite");
    wrap.setAttribute("role", "region");
    wrap.setAttribute("aria-label", "AI assistant");

    var panel = el("div", "krv-a-panel");
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", "Помощник Dr.Slon");

    var head = el("div", "krv-a-head");
    var headLeft = el("div", "krv-a-head-left");
    var avatar = el("div", "krv-a-avatar", "DS");
    var titles = el("div", "krv-a-titles");
    var h2 = el("h2", null, "Помощник Dr.Slon");
    var sub = el("p", null, "Загрузка…");
    titles.appendChild(h2);
    titles.appendChild(sub);
    headLeft.appendChild(avatar);
    headLeft.appendChild(titles);
    var closeBtn = el("button", "krv-a-close", "×");
    closeBtn.type = "button";
    closeBtn.setAttribute("aria-label", "Закрыть");
    head.appendChild(headLeft);
    head.appendChild(closeBtn);

    var msgs = el("div", "krv-a-msgs");
    var quick = el("div", "krv-a-quick");
    var handoff = el("div", "krv-a-handoff");

    var form = el("form", "krv-a-form");
    form.innerHTML =
      '<p class="krv-a-form-title">Заявка</p>' +
      '<label class="krv-a-field"><span>Что нужно *</span>' +
      '<textarea name="need" rows="2" required maxlength="4000" placeholder="Кратко опишите задачу"></textarea></label>' +
      '<label class="krv-a-field"><span>Контакт *</span>' +
      '<input name="contact" required maxlength="300" placeholder="Telegram / телефон / email" autocomplete="tel"></label>' +
      '<div class="krv-a-field-row">' +
      '<label class="krv-a-field"><span>Бюджет</span>' +
      '<input name="budget" maxlength="200" placeholder="от 40 000 ₽"></label>' +
      '<label class="krv-a-field"><span>Срочность</span>' +
      '<select name="urgency">' +
      '<option>Обычная</option><option>Срочно</option><option>Очень срочно</option>' +
      "</select></label></div>" +
      '<label class="krv-a-field"><span>Тема</span>' +
      '<input name="topic" maxlength="200" placeholder="Боты / WordPress / …"></label>' +
      '<label class="krv-a-hp" aria-hidden="true">Сайт<input name="website" tabindex="-1" autocomplete="off"></label>' +
      '<div class="krv-a-form-actions">' +
      '<button type="submit" class="krv-a-btn primary">Отправить</button>' +
      '<button type="button" class="krv-a-btn ghost" data-cancel-lead>Отмена</button>' +
      "</div>";

    var composer = el("div", "krv-a-composer");
    var ta = el("textarea");
    ta.rows = 1;
    ta.placeholder = "Напишите вопрос…";
    ta.setAttribute("aria-label", "Сообщение");
    var send = el("button", "krv-a-send", "→");
    send.type = "button";
    send.setAttribute("aria-label", "Отправить");
    composer.appendChild(ta);
    composer.appendChild(send);

    var bubble = el("button", "krv-a-bubble");
    bubble.type = "button";
    bubble.setAttribute("aria-label", "Открыть чат");
    bubble.innerHTML = iconChat();

    panel.appendChild(head);
    panel.appendChild(msgs);
    panel.appendChild(quick);
    panel.appendChild(handoff);
    panel.appendChild(form);
    panel.appendChild(composer);
    wrap.appendChild(panel);
    wrap.appendChild(bubble);
    document.body.appendChild(wrap);

    return {
      root: wrap,
      panel: panel,
      h2: h2,
      sub: sub,
      msgs: msgs,
      quick: quick,
      handoff: handoff,
      form: form,
      composer: composer,
      ta: ta,
      send: send,
      bubble: bubble,
      closeBtn: closeBtn,
    };
  }

  function addMsg(ui, role, text) {
    var m = el("div", "krv-a-msg " + role, text);
    ui.msgs.appendChild(m);
    ui.msgs.scrollTop = ui.msgs.scrollHeight;
    return m;
  }

  function setQuick(ui, items, onPick) {
    ui.quick.innerHTML = "";
    (items || []).forEach(function (label) {
      var b = el("button", "krv-a-chip", label);
      b.type = "button";
      b.addEventListener("click", function () {
        onPick(label);
      });
      ui.quick.appendChild(b);
    });
  }

  function setHandoff(ui, h) {
    ui.handoff.innerHTML = "";
    if (!h) return;
    var links = [
      [h.telegram_url, h.telegram_label || "Telegram"],
      [h.max_url, h.max_label || "MAX"],
      [h.contacts_url, h.contacts_label || "Контакты"],
      [h.price_url, "Прайс"],
    ];
    links.forEach(function (pair) {
      if (!pair[0]) return;
      var a = el("a", null, pair[1]);
      a.href = pair[0];
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      ui.handoff.appendChild(a);
    });
    var lead = el("button", "krv-a-chip", "Заявка");
    lead.type = "button";
    lead.addEventListener("click", function () {
      showLeadForm(ui, true);
    });
    ui.handoff.appendChild(lead);
  }

  function showLeadForm(ui, on) {
    if (on) {
      ui.form.classList.add("is-on");
      ui.composer.classList.add("is-hidden");
      ui.quick.style.display = "none";
    } else {
      ui.form.classList.remove("is-on");
      ui.composer.classList.remove("is-hidden");
      ui.quick.style.display = "";
    }
  }

  function openPanel(ui, open) {
    if (open) ui.root.classList.add("is-open");
    else ui.root.classList.remove("is-open");
  }

  async function api(path, body) {
    var res = await fetch(API + path, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body),
      credentials: "omit",
      mode: "cors",
    });
    var data = null;
    try {
      data = await res.json();
    } catch (e) {
      data = null;
    }
    if (!res.ok) {
      var detail =
        (data && (data.detail || data.message)) || "Ошибка " + res.status;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return data;
  }

  async function bootstrap(ui, state) {
    var hp = hostPath();
    var data = await api("/bootstrap", {
      host: hp.host,
      path: hp.path,
      session_id: state.sessionId || null,
    });
    state.sessionId = data.session_id;
    setSession(data.session_id);
    state.handoff = data.handoff;
    ui.h2.textContent = data.title || "Помощник Dr.Slon";
    ui.sub.textContent = data.subtitle || data.site_label || "";
    if (!state.greeted) {
      addMsg(ui, "bot", data.greeting || "Здравствуйте!");
      state.greeted = true;
    }
    setQuick(ui, data.quick_replies || [], function (label) {
      if (label === "Оставить заявку" || label === "Заявка") {
        showLeadForm(ui, true);
        return;
      }
      if (label === "Telegram" && data.handoff && data.handoff.telegram_url) {
        window.open(data.handoff.telegram_url, "_blank", "noopener");
        return;
      }
      if (label === "Контакты" && data.handoff && data.handoff.contacts_url) {
        window.open(data.handoff.contacts_url, "_blank", "noopener");
        return;
      }
      sendMessage(ui, state, label);
    });
    setHandoff(ui, data.handoff);
  }

  async function sendMessage(ui, state, text) {
    text = (text || "").trim();
    if (!text || state.busy) return;
    state.busy = true;
    ui.send.disabled = true;
    addMsg(ui, "user", text);
    ui.ta.value = "";
    var typing = el("div", "krv-a-typing", "Печатает…");
    ui.msgs.appendChild(typing);
    ui.msgs.scrollTop = ui.msgs.scrollHeight;

    try {
      var hp = hostPath();
      var data = await api("/chat", {
        session_id: state.sessionId,
        host: hp.host,
        path: hp.path,
        message: text,
        website: "",
      });
      typing.remove();
      addMsg(ui, "bot", data.reply || "…");
      if (data.quick_replies && data.quick_replies.length) {
        setQuick(ui, data.quick_replies, function (label) {
          if (label === "Оставить заявку" || label === "Заявка") {
            showLeadForm(ui, true);
            return;
          }
          sendMessage(ui, state, label);
        });
      }
      if (data.suggest_lead) {
        addMsg(ui, "sys", "Можно оставить заявку кнопкой ниже");
      }
    } catch (err) {
      typing.remove();
      addMsg(
        ui,
        "bot",
        "Не удалось ответить. Напишите в Telegram @DrSlon или на krivoshein.site/contacts/"
      );
      console.warn("[krv-assistant]", err);
    } finally {
      state.busy = false;
      ui.send.disabled = false;
      ui.ta.focus();
    }
  }

  async function submitLead(ui, state, formEl) {
    if (state.busy) return;
    var fd = new FormData(formEl);
    var payload = {
      session_id: state.sessionId,
      host: hostPath().host,
      path: hostPath().path,
      topic: String(fd.get("topic") || ""),
      need: String(fd.get("need") || ""),
      budget: String(fd.get("budget") || ""),
      urgency: String(fd.get("urgency") || "Обычная"),
      contact: String(fd.get("contact") || ""),
      website: String(fd.get("website") || ""),
    };
    state.busy = true;
    try {
      var data = await api("/lead", payload);
      addMsg(ui, "bot", data.message || "Заявка отправлена.");
      showLeadForm(ui, false);
      formEl.reset();
      if (data.handoff) setHandoff(ui, data.handoff);
    } catch (err) {
      addMsg(
        ui,
        "bot",
        "Не удалось отправить заявку. Напишите @DrSlon или через форму контактов."
      );
      console.warn("[krv-assistant]", err);
    } finally {
      state.busy = false;
    }
  }

  function bind(ui, state) {
    ui.bubble.addEventListener("click", function () {
      updateStackOffset(ui.root);
      var open = !ui.root.classList.contains("is-open");
      openPanel(ui, open);
      if (open && !state.bootstrapped) {
        bootstrap(ui, state)
          .then(function () {
            state.bootstrapped = true;
          })
          .catch(function (err) {
            addMsg(
              ui,
              "bot",
              "Чат временно недоступен. Telegram: https://t.me/DrSlon"
            );
            console.warn("[krv-assistant] bootstrap", err);
          });
      }
      if (open) {
        setTimeout(function () {
          ui.ta.focus();
        }, 40);
      }
    });
    ui.closeBtn.addEventListener("click", function () {
      openPanel(ui, false);
    });
    ui.send.addEventListener("click", function () {
      sendMessage(ui, state, ui.ta.value);
    });
    ui.ta.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage(ui, state, ui.ta.value);
      }
    });
    ui.form.addEventListener("submit", function (e) {
      e.preventDefault();
      submitLead(ui, state, ui.form);
    });
    var cancel = ui.form.querySelector("[data-cancel-lead]");
    if (cancel) {
      cancel.addEventListener("click", function () {
        showLeadForm(ui, false);
      });
    }
  }

  function init() {
    loadCss();
    var ui = createUI();
    var state = {
      sessionId: getSession(),
      bootstrapped: false,
      greeted: false,
      busy: false,
      handoff: null,
    };
    bind(ui, state);
    updateStackOffset(ui.root);
    var onResize = function () {
      updateStackOffset(ui.root);
    };
    window.addEventListener("resize", onResize, { passive: true });
    window.addEventListener("orientationchange", onResize, { passive: true });
    if (typeof MutationObserver !== "undefined" && document.body) {
      var mo = new MutationObserver(function () {
        updateStackOffset(ui.root);
      });
      mo.observe(document.body, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ["class", "hidden", "style"],
      });
      setTimeout(function () {
        try {
          mo.disconnect();
        } catch (e) {}
      }, 15000);
    }
    setTimeout(function () {
      updateStackOffset(ui.root);
    }, 400);
    setTimeout(function () {
      updateStackOffset(ui.root);
    }, 1200);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
