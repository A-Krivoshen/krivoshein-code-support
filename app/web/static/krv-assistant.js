/**
 * KRV AI Popup Assistant — vanilla embed (v=20260730p)
 * CSS injected as <style>. Theme: html[data-theme]. Lang: html[lang] / storage.
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
  var PROACTIVE_DISMISS_KEY = "krv_assistant_proactive_dismissed";
  var PROACTIVE_SHOWN_KEY = "krv_assistant_proactive_shown";
  var PROACTIVE_MS = 50000;
  var PROACTIVE_MS_MOBILE = 62000;
  var EMBEDDED_CSS = "/* KRV Web AI Assistant — clean technical UI (right-bottom)\n * Avoids landing mobile-cta-bar (~z-index 60, ~64px) via --krv-a-stack-bottom.\n */\n.krv-assistant {\n  --krv-a-bg: #ffffff;\n  --krv-a-bg-soft: #f8fafc;\n  --krv-a-bg-msg: #f1f5f9;\n  --krv-a-line: #e2e8f0;\n  --krv-a-ink: #0f172a;\n  --krv-a-mute: #64748b;\n  --krv-a-accent: #315fe8;\n  --krv-a-accent-h: #244ac2;\n  --krv-a-accent-soft: #eef4ff;\n  --krv-a-user: #315fe8;\n  --krv-a-shadow: 0 4px 6px -1px rgba(15, 23, 42, 0.06),\n    0 16px 40px -8px rgba(15, 23, 42, 0.18);\n  --krv-a-radius: 16px;\n  --krv-a-radius-sm: 10px;\n  /* Above page content & mobile CTA (60) / cookie (90); below rare system modals */\n  --krv-a-z: 120;\n  /* JS sets --krv-a-stack-bottom to clear fixed bottom bars; CSS fallback for mobile CTA */\n  --krv-a-stack-bottom: 16px;\n  --krv-a-edge: 16px;\n  --krv-a-gap: 10px;\n  --krv-a-bubble-size: 56px;\n  --krv-a-w: min(360px, calc(100vw - 24px));\n  --krv-a-h: min(\n    520px,\n    calc(\n      100dvh - var(--krv-a-stack-bottom) - env(safe-area-inset-bottom, 0px) -\n        var(--krv-a-bubble-size) - var(--krv-a-gap) - 16px\n    )\n  );\n\n  /* !important: landings force body children to position:relative in dark\n     (theme-i18n matrix stacking). Without this the widget ends up at page\n     bottom instead of floating in the viewport. */\n  position: fixed !important;\n  z-index: var(--krv-a-z) !important;\n  top: auto !important;\n  left: auto !important;\n  right: max(var(--krv-a-edge), env(safe-area-inset-right, 0px)) !important;\n  /* --krv-a-keyboard-inset: soft keyboard lift (JS / visualViewport) */\n  --krv-a-keyboard-inset: 0px;\n  bottom: calc(\n    var(--krv-a-stack-bottom) + env(safe-area-inset-bottom, 0px) +\n      var(--krv-a-keyboard-inset)\n  ) !important;\n  display: flex !important;\n  flex-direction: column;\n  align-items: flex-end;\n  gap: var(--krv-a-gap);\n  color: var(--krv-a-ink);\n  line-height: 1.45;\n  font-size: 14px;\n  font-family: Inter, system-ui, -apple-system, \"Segoe UI\", Roboto, Arial, sans-serif;\n  -webkit-font-smoothing: antialiased;\n  /* Don't trap page scroll when closed */\n  pointer-events: none;\n  max-width: calc(100vw - 16px);\n  transform: none !important;\n  filter: none !important;\n}\n\n/* Only interactive pieces receive clicks */\n.krv-assistant .krv-a-bubble,\n.krv-assistant .krv-a-panel,\n.krv-assistant .krv-a-tip {\n  pointer-events: auto;\n}\n\n.krv-assistant[data-side=\"left\"] {\n  left: max(var(--krv-a-edge), env(safe-area-inset-left, 0px)) !important;\n  right: auto !important;\n  align-items: flex-start;\n}\n\n/* Mobile: clear fixed .mobile-cta-bar (~64–90px + safe-area) before JS measures.\n * Prefer a generous fallback so bubble never sits on CTA buttons. */\n@media (max-width: 767.98px) {\n  .krv-assistant {\n    --krv-a-stack-bottom: 96px;\n    --krv-a-edge: 12px;\n    --krv-a-bubble-size: 52px;\n  }\n}\n\n/* Very small phones (SE / 320–375) — taller bar when labels wrap */\n@media (max-width: 380px) {\n  .krv-assistant {\n    --krv-a-stack-bottom: 104px;\n    --krv-a-edge: 10px;\n    --krv-a-bubble-size: 48px;\n    --krv-a-gap: 8px;\n  }\n}\n\n/* Desktop / tablet: no mobile bar */\n@media (min-width: 768px) {\n  .krv-assistant {\n    --krv-a-stack-bottom: 16px;\n    --krv-a-edge: 20px;\n    --krv-a-bubble-size: 56px;\n  }\n}\n\n/* When assistant panel is open on mobile, free the bottom for the chat panel */\n@media (max-width: 767.98px) {\n  body.krv-a-panel-open .mobile-cta-bar {\n    display: none !important;\n    pointer-events: none !important;\n    visibility: hidden !important;\n  }\n}\n\n.krv-assistant *,\n.krv-assistant *::before,\n.krv-assistant *::after {\n  box-sizing: border-box;\n}\n\n/* —— Bubble —— */\n.krv-assistant .krv-a-bubble {\n  width: var(--krv-a-bubble-size);\n  height: var(--krv-a-bubble-size);\n  flex: 0 0 auto;\n  border: 0;\n  border-radius: 50%;\n  cursor: pointer;\n  display: inline-flex;\n  align-items: center;\n  justify-content: center;\n  background: var(--krv-a-accent);\n  color: #fff;\n  box-shadow: 0 8px 24px rgba(49, 95, 232, 0.35);\n  transition: transform 0.15s ease, background 0.15s ease, box-shadow 0.15s ease;\n  padding: 0;\n}\n\n.krv-assistant .krv-a-bubble:hover {\n  background: var(--krv-a-accent-h);\n  transform: translateY(-1px);\n  box-shadow: 0 10px 28px rgba(49, 95, 232, 0.42);\n}\n\n.krv-assistant .krv-a-bubble:active {\n  transform: translateY(0);\n}\n\n.krv-assistant .krv-a-bubble:focus-visible {\n  outline: 2px solid var(--krv-a-accent);\n  outline-offset: 3px;\n}\n\n.krv-assistant .krv-a-bubble svg {\n  width: 24px;\n  height: 24px;\n  display: block;\n  fill: none;\n  stroke: currentColor;\n  stroke-width: 2;\n  stroke-linecap: round;\n  stroke-linejoin: round;\n}\n\n.krv-assistant.is-open .krv-a-bubble {\n  background: #1e293b;\n  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.2);\n}\n\n/* Soft proactive nudge */\n.krv-assistant .krv-a-nudge-wrap {\n  display: flex;\n  flex-direction: row;\n  align-items: flex-end;\n  gap: 8px;\n  pointer-events: none;\n}\n\n.krv-assistant[data-side=\"left\"] .krv-a-nudge-wrap {\n  flex-direction: row-reverse;\n}\n\n.krv-assistant .krv-a-tip {\n  display: none;\n  max-width: min(220px, calc(100vw - 88px));\n  padding: 8px 10px 8px 12px;\n  border-radius: 12px;\n  border: 1px solid var(--krv-a-line);\n  background: var(--krv-a-bg);\n  color: var(--krv-a-ink);\n  box-shadow: var(--krv-a-shadow);\n  font-size: 12.5px;\n  line-height: 1.35;\n  position: relative;\n  cursor: pointer;\n  text-align: left;\n  gap: 6px;\n  align-items: flex-start;\n}\n\n.krv-assistant.is-nudge .krv-a-tip {\n  display: inline-flex;\n  animation: krv-a-tip-in 0.28s ease;\n}\n\n.krv-assistant .krv-a-tip-text {\n  flex: 1 1 auto;\n  min-width: 0;\n}\n\n.krv-assistant .krv-a-tip-x {\n  flex: 0 0 auto;\n  border: 0;\n  background: transparent;\n  color: var(--krv-a-mute);\n  cursor: pointer;\n  font-size: 16px;\n  line-height: 1;\n  padding: 0 0 0 4px;\n  margin: -2px 0 0;\n}\n\n.krv-assistant .krv-a-tip-x:hover {\n  color: var(--krv-a-ink);\n}\n\n/* subtle pulse on bubble when nudging */\n.krv-assistant.is-nudge .krv-a-bubble {\n  box-shadow:\n    0 0 0 0 rgba(49, 95, 232, 0.45),\n    0 8px 24px rgba(49, 95, 232, 0.35);\n  animation: krv-a-pulse 1.8s ease-out infinite;\n}\n\n.krv-assistant.is-open.is-nudge .krv-a-bubble {\n  animation: none;\n}\n\n@keyframes krv-a-pulse {\n  0% {\n    box-shadow:\n      0 0 0 0 rgba(49, 95, 232, 0.4),\n      0 8px 24px rgba(49, 95, 232, 0.35);\n  }\n  70% {\n    box-shadow:\n      0 0 0 12px rgba(49, 95, 232, 0),\n      0 8px 24px rgba(49, 95, 232, 0.28);\n  }\n  100% {\n    box-shadow:\n      0 0 0 0 rgba(49, 95, 232, 0),\n      0 8px 24px rgba(49, 95, 232, 0.35);\n  }\n}\n\n@keyframes krv-a-tip-in {\n  from {\n    opacity: 0;\n    transform: translateY(6px) scale(0.96);\n  }\n  to {\n    opacity: 1;\n    transform: translateY(0) scale(1);\n  }\n}\n\n@media (max-width: 480px) {\n  .krv-assistant .krv-a-tip {\n    max-width: min(168px, calc(100vw - 78px));\n    font-size: 12px;\n    padding: 7px 8px 7px 10px;\n  }\n}\n\n@media (prefers-reduced-motion: reduce) {\n  .krv-assistant.is-nudge .krv-a-bubble {\n    animation: none;\n  }\n  .krv-assistant.is-nudge .krv-a-tip {\n    animation: none;\n  }\n}\n\n/* —— Panel —— */\n.krv-assistant .krv-a-panel {\n  display: none;\n  width: var(--krv-a-w);\n  height: var(--krv-a-h);\n  max-height: var(--krv-a-h);\n  max-width: 100%;\n  flex-direction: column;\n  background: var(--krv-a-bg);\n  border: 1px solid var(--krv-a-line);\n  border-radius: var(--krv-a-radius);\n  box-shadow: var(--krv-a-shadow);\n  overflow: hidden;\n  /* Keep panel inside viewport horizontally */\n  margin-right: 0;\n  margin-left: 0;\n}\n\n.krv-assistant.is-open .krv-a-panel {\n  display: flex;\n}\n\n/* When open on mobile, lock body scroll slightly less invasive: overscroll contain */\n.krv-assistant.is-open .krv-a-panel,\n.krv-assistant.is-open .krv-a-msgs {\n  overscroll-behavior: contain;\n}\n\n/* Header */\n.krv-assistant .krv-a-head {\n  flex: 0 0 auto;\n  display: flex;\n  align-items: flex-start;\n  justify-content: space-between;\n  gap: 10px;\n  padding: 12px 12px 10px;\n  background: var(--krv-a-bg);\n  border-bottom: 1px solid var(--krv-a-line);\n}\n\n.krv-assistant .krv-a-head-left {\n  display: flex;\n  align-items: center;\n  gap: 10px;\n  min-width: 0;\n}\n\n.krv-assistant .krv-a-avatar {\n  width: 32px;\n  height: 32px;\n  border-radius: 10px;\n  flex: 0 0 auto;\n  display: flex;\n  align-items: center;\n  justify-content: center;\n  background: var(--krv-a-accent-soft);\n  color: var(--krv-a-accent);\n  font-size: 13px;\n  font-weight: 700;\n  letter-spacing: -0.02em;\n}\n\n.krv-assistant .krv-a-titles {\n  min-width: 0;\n  flex: 1 1 auto;\n  padding-right: 4px;\n}\n\n.krv-assistant .krv-a-head-left {\n  min-width: 0;\n  flex: 1 1 auto;\n  overflow: hidden;\n}\n\n.krv-assistant .krv-a-close {\n  flex: 0 0 auto !important;\n}\n\n.krv-assistant .krv-a-head h2,\n.krv-assistant .krv-a-head .krv-a-title {\n  margin: 0 !important;\n  padding: 0 !important;\n  /* Full «Помощник Dr.Slon» / «Dr.Slon Assistant» must fit 360px head */\n  font-size: 12px !important;\n  font-weight: 650 !important;\n  letter-spacing: -0.015em !important;\n  color: var(--krv-a-ink) !important;\n  line-height: 1.25 !important;\n  white-space: nowrap !important;\n  overflow: visible !important;\n  text-overflow: clip !important;\n  max-width: none !important;\n  text-transform: none !important;\n  flex-shrink: 0 !important;\n}\n\n.krv-assistant .krv-a-head p,\n.krv-assistant .krv-a-head .krv-a-sub {\n  margin: 2px 0 0 !important;\n  padding: 0 !important;\n  font-size: 11px !important;\n  font-weight: 400 !important;\n  color: var(--krv-a-mute) !important;\n  line-height: 1.3 !important;\n  white-space: nowrap !important;\n  overflow: hidden !important;\n  text-overflow: ellipsis !important;\n  max-width: 100% !important;\n  text-transform: none !important;\n  display: block !important;\n}\n\n.krv-assistant .krv-a-close {\n  flex: 0 0 auto;\n  width: 32px;\n  height: 32px;\n  border: 0;\n  border-radius: 8px;\n  background: transparent;\n  color: var(--krv-a-mute);\n  cursor: pointer;\n  font-size: 20px;\n  line-height: 1;\n  display: inline-flex;\n  align-items: center;\n  justify-content: center;\n  padding: 0;\n}\n\n.krv-assistant .krv-a-close:hover {\n  background: var(--krv-a-bg-soft);\n  color: var(--krv-a-ink);\n}\n\n/* Messages */\n.krv-assistant .krv-a-msgs {\n  flex: 1 1 auto;\n  min-height: 0;\n  overflow-x: hidden;\n  overflow-y: auto;\n  padding: 12px 12px 8px;\n  display: flex;\n  flex-direction: column;\n  gap: 8px;\n  background: var(--krv-a-bg-soft);\n  -webkit-overflow-scrolling: touch;\n}\n\n.krv-assistant .krv-a-msg {\n  max-width: 88%;\n  padding: 9px 12px;\n  border-radius: 12px;\n  white-space: pre-wrap;\n  word-break: break-word;\n  font-size: 13px;\n  line-height: 1.45;\n}\n\n.krv-assistant .krv-a-msg.bot {\n  align-self: flex-start;\n  background: var(--krv-a-bg);\n  border: 1px solid var(--krv-a-line);\n  color: var(--krv-a-ink);\n  border-bottom-left-radius: 4px;\n}\n\n.krv-assistant .krv-a-msg.user {\n  align-self: flex-end;\n  background: var(--krv-a-user);\n  color: #fff;\n  border-bottom-right-radius: 4px;\n}\n\n.krv-assistant .krv-a-msg.sys {\n  align-self: center;\n  max-width: 100%;\n  background: transparent;\n  color: var(--krv-a-mute);\n  font-size: 11.5px;\n  padding: 2px 6px;\n  text-align: center;\n}\n\n.krv-assistant .krv-a-typing {\n  align-self: flex-start;\n  color: var(--krv-a-mute);\n  font-size: 12px;\n  padding: 2px 4px;\n}\n\n/* Quick replies */\n.krv-assistant .krv-a-quick {\n  flex: 0 0 auto;\n  display: flex;\n  flex-wrap: wrap;\n  gap: 6px;\n  padding: 8px 12px 0;\n  background: var(--krv-a-bg);\n}\n\n.krv-assistant .krv-a-quick:empty {\n  display: none;\n}\n\n.krv-assistant .krv-a-chip {\n  border: 1px solid var(--krv-a-line);\n  background: var(--krv-a-bg);\n  color: var(--krv-a-ink);\n  border-radius: 999px;\n  padding: 6px 11px;\n  font-size: 12px;\n  line-height: 1.2;\n  cursor: pointer;\n  transition: border-color 0.12s ease, background 0.12s ease, color 0.12s ease;\n}\n\n.krv-assistant .krv-a-chip:hover {\n  border-color: #93b0f5;\n  background: var(--krv-a-accent-soft);\n  color: var(--krv-a-accent);\n}\n\n/* Handoff links */\n.krv-assistant .krv-a-handoff {\n  flex: 0 0 auto;\n  display: flex;\n  flex-wrap: wrap;\n  gap: 6px;\n  padding: 8px 12px;\n  background: var(--krv-a-bg);\n  border-bottom: 1px solid var(--krv-a-line);\n}\n\n.krv-assistant .krv-a-handoff:empty {\n  display: none;\n  border-bottom: 0;\n  padding: 0;\n}\n\n.krv-assistant .krv-a-handoff a,\n.krv-assistant .krv-a-handoff button.krv-a-chip {\n  font-size: 11.5px;\n  color: var(--krv-a-accent);\n  text-decoration: none;\n  border: 1px solid var(--krv-a-line);\n  border-radius: 999px;\n  padding: 5px 10px;\n  background: var(--krv-a-bg-soft);\n  cursor: pointer;\n  font-family: inherit;\n  line-height: 1.2;\n}\n\n.krv-assistant .krv-a-handoff a:hover,\n.krv-assistant .krv-a-handoff button.krv-a-chip:hover {\n  border-color: #93b0f5;\n  background: var(--krv-a-accent-soft);\n}\n\n/* Lead form */\n.krv-assistant .krv-a-form {\n  display: none;\n  flex: 0 0 auto;\n  flex-direction: column;\n  gap: 8px;\n  padding: 10px 12px 12px;\n  border-top: 1px solid var(--krv-a-line);\n  background: var(--krv-a-bg);\n  max-height: 55%;\n  overflow-y: auto;\n  -webkit-overflow-scrolling: touch;\n  overscroll-behavior: contain;\n}\n\n.krv-assistant .krv-a-form.is-on {\n  display: flex;\n}\n\n/* —— Mobile open panel + lead form (class .is-lead from JS) —— */\n@media (max-width: 767.98px) {\n  /* Panel height tracks visual viewport (keyboard-safe).\n   * Root bottom already includes stack + keyboard-inset, so free\n   * height for (panel + gap + bubble) is vv - stack - safe. */\n  .krv-assistant.is-open .krv-a-panel {\n    height: min(\n      520px,\n      calc(\n        var(--krv-a-vv-h, 100dvh) - var(--krv-a-stack-bottom) -\n          env(safe-area-inset-bottom, 0px) - var(--krv-a-bubble-size) -\n          var(--krv-a-gap) - 12px\n      )\n    );\n    max-height: calc(\n      var(--krv-a-vv-h, 100dvh) - var(--krv-a-stack-bottom) -\n        env(safe-area-inset-bottom, 0px) - var(--krv-a-bubble-size) -\n        var(--krv-a-gap) - 12px\n    );\n    min-height: 0;\n  }\n\n  /* Chat mode: ensure msgs + composer + chips can scroll if needed */\n  .krv-assistant.is-open:not(.is-lead) .krv-a-panel {\n    overflow: hidden;\n  }\n\n  .krv-assistant.is-open:not(.is-lead) .krv-a-msgs {\n    flex: 1 1 auto;\n    min-height: 80px;\n  }\n\n  /* Lead mode: give the form almost the entire panel */\n  .krv-assistant.is-lead .krv-a-msgs {\n    display: none !important;\n  }\n\n  .krv-assistant.is-lead .krv-a-quick,\n  .krv-assistant.is-lead .krv-a-handoff {\n    display: none !important;\n  }\n\n  .krv-assistant.is-lead .krv-a-form.is-on {\n    flex: 1 1 auto;\n    min-height: 0;\n    max-height: none;\n    gap: 6px;\n    padding: 8px 10px 8px;\n    overflow-x: hidden;\n    overflow-y: auto;\n    -webkit-overflow-scrolling: touch;\n    overscroll-behavior: contain;\n  }\n\n  .krv-assistant.is-lead .krv-a-form.is-on .krv-a-form-title {\n    font-size: 12px;\n    margin-bottom: 0;\n    position: sticky;\n    top: 0;\n    z-index: 2;\n    background: var(--krv-a-bg);\n    padding-bottom: 4px;\n  }\n\n  .krv-assistant.is-lead .krv-a-form.is-on .krv-a-field > span {\n    font-size: 10.5px;\n  }\n\n  .krv-assistant.is-lead .krv-a-form.is-on input,\n  .krv-assistant.is-lead .krv-a-form.is-on textarea,\n  .krv-assistant.is-lead .krv-a-form.is-on select {\n    min-height: 36px;\n    padding: 7px 9px;\n    font-size: 16px; /* iOS: avoid focus zoom */\n  }\n\n  .krv-assistant.is-lead .krv-a-form.is-on textarea {\n    min-height: 44px;\n    max-height: 56px;\n  }\n\n  .krv-assistant.is-lead .krv-a-form.is-on .krv-a-field-row {\n    grid-template-columns: 1fr;\n    gap: 6px;\n  }\n\n  .krv-assistant.is-lead .krv-a-form.is-on .krv-a-form-actions {\n    position: sticky;\n    bottom: 0;\n    z-index: 3;\n    flex-shrink: 0;\n    margin-top: 6px;\n    padding-top: 8px;\n    padding-bottom: max(4px, env(safe-area-inset-bottom, 0px));\n    background: var(--krv-a-bg);\n    box-shadow: 0 -6px 12px -8px rgba(15, 23, 42, 0.18);\n    gap: 6px;\n  }\n\n  html[data-theme=\"dark\"] .krv-assistant.is-lead .krv-a-form.is-on .krv-a-form-actions,\n  .krv-assistant.krv-a-dark.is-lead .krv-a-form.is-on .krv-a-form-actions {\n    background: var(--krv-a-bg);\n    box-shadow: 0 -6px 12px -8px rgba(0, 0, 0, 0.45);\n  }\n\n  .krv-assistant.is-lead .krv-a-form.is-on .krv-a-btn {\n    min-height: 44px;\n    padding: 10px 12px;\n  }\n\n  /* Very short viewports (keyboard open or SE): tighter lead chrome */\n  @media (max-height: 520px) {\n    .krv-assistant.is-lead .krv-a-head {\n      padding: 8px 10px 6px;\n    }\n    .krv-assistant.is-lead .krv-a-form.is-on {\n      gap: 4px;\n      padding: 6px 8px;\n    }\n    .krv-assistant.is-lead .krv-a-form.is-on textarea {\n      min-height: 40px;\n      max-height: 48px;\n    }\n  }\n}\n\n.krv-assistant .krv-a-form-title {\n  margin: 0 0 2px;\n  font-size: 12.5px;\n  font-weight: 650;\n  color: var(--krv-a-ink);\n}\n\n.krv-assistant .krv-a-field {\n  display: flex;\n  flex-direction: column;\n  gap: 4px;\n  margin: 0;\n}\n\n.krv-assistant .krv-a-field > span {\n  font-size: 11px;\n  font-weight: 500;\n  color: var(--krv-a-mute);\n}\n\n.krv-assistant .krv-a-field-row {\n  display: grid;\n  grid-template-columns: 1fr 1fr;\n  gap: 8px;\n}\n\n.krv-assistant .krv-a-form input,\n.krv-assistant .krv-a-form textarea,\n.krv-assistant .krv-a-form select {\n  width: 100%;\n  margin: 0;\n  border: 1px solid var(--krv-a-line);\n  background: var(--krv-a-bg);\n  color: var(--krv-a-ink);\n  border-radius: var(--krv-a-radius-sm);\n  padding: 8px 10px;\n  font-size: 13px;\n  font-family: inherit;\n  line-height: 1.35;\n  min-height: 38px;\n  appearance: none;\n  -webkit-appearance: none;\n}\n\n.krv-assistant .krv-a-form textarea {\n  min-height: 64px;\n  max-height: 100px;\n  resize: vertical;\n}\n\n.krv-assistant .krv-a-form select {\n  background-image: url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2364748b' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E\");\n  background-repeat: no-repeat;\n  background-position: right 10px center;\n  padding-right: 28px;\n}\n\n.krv-assistant .krv-a-form input:focus,\n.krv-assistant .krv-a-form textarea:focus,\n.krv-assistant .krv-a-form select:focus {\n  outline: none;\n  border-color: var(--krv-a-accent);\n  box-shadow: 0 0 0 3px rgba(49, 95, 232, 0.15);\n}\n\n.krv-assistant .krv-a-form input::placeholder,\n.krv-assistant .krv-a-form textarea::placeholder {\n  color: #94a3b8;\n}\n\n.krv-assistant .krv-a-hp {\n  position: absolute !important;\n  left: -10000px !important;\n  width: 1px !important;\n  height: 1px !important;\n  overflow: hidden !important;\n  opacity: 0 !important;\n  pointer-events: none !important;\n}\n\n.krv-assistant .krv-a-form-actions {\n  display: flex;\n  gap: 8px;\n  margin-top: 2px;\n}\n\n.krv-assistant .krv-a-btn {\n  border: 0;\n  border-radius: var(--krv-a-radius-sm);\n  padding: 9px 12px;\n  font-size: 13px;\n  font-weight: 600;\n  font-family: inherit;\n  cursor: pointer;\n  line-height: 1.2;\n  min-height: 38px;\n}\n\n.krv-assistant .krv-a-btn.primary {\n  background: var(--krv-a-accent);\n  color: #fff;\n  flex: 1;\n}\n\n.krv-assistant .krv-a-btn.primary:hover {\n  background: var(--krv-a-accent-h);\n}\n\n.krv-assistant .krv-a-btn.ghost {\n  background: var(--krv-a-bg);\n  color: var(--krv-a-mute);\n  border: 1px solid var(--krv-a-line);\n  flex: 0 0 auto;\n  min-width: 88px;\n}\n\n.krv-assistant .krv-a-btn.ghost:hover {\n  color: var(--krv-a-ink);\n  background: var(--krv-a-bg-soft);\n}\n\n/* Composer */\n.krv-assistant .krv-a-composer {\n  flex: 0 0 auto;\n  display: flex;\n  align-items: flex-end;\n  gap: 8px;\n  padding: 10px 12px 12px;\n  border-top: 1px solid var(--krv-a-line);\n  background: var(--krv-a-bg);\n}\n\n.krv-assistant .krv-a-composer.is-hidden {\n  display: none;\n}\n\n.krv-assistant .krv-a-composer textarea {\n  flex: 1 1 auto;\n  width: 100%;\n  min-height: 40px;\n  max-height: 96px;\n  margin: 0;\n  border: 1px solid var(--krv-a-line);\n  background: var(--krv-a-bg-soft);\n  color: var(--krv-a-ink);\n  border-radius: 12px;\n  padding: 10px 12px;\n  font-size: 13px;\n  font-family: inherit;\n  line-height: 1.4;\n  resize: none;\n}\n\n.krv-assistant .krv-a-composer textarea:focus {\n  outline: none;\n  border-color: var(--krv-a-accent);\n  background: var(--krv-a-bg);\n  box-shadow: 0 0 0 3px rgba(49, 95, 232, 0.12);\n}\n\n.krv-assistant .krv-a-send {\n  flex: 0 0 auto;\n  width: 40px;\n  height: 40px;\n  border: 0;\n  border-radius: 12px;\n  background: var(--krv-a-accent);\n  color: #fff;\n  cursor: pointer;\n  display: inline-flex;\n  align-items: center;\n  justify-content: center;\n  padding: 0;\n  font-size: 16px;\n  font-weight: 600;\n  line-height: 1;\n}\n\n.krv-assistant .krv-a-send:hover {\n  background: var(--krv-a-accent-h);\n}\n\n.krv-assistant .krv-a-send:disabled {\n  opacity: 0.5;\n  cursor: not-allowed;\n}\n\n/* Mobile width/form */\n@media (max-width: 480px) {\n  .krv-assistant {\n    --krv-a-w: min(calc(100vw - 20px), 400px);\n    width: auto;\n    max-width: calc(100vw - 16px);\n  }\n\n  .krv-assistant .krv-a-field-row {\n    grid-template-columns: 1fr;\n  }\n\n  .krv-assistant .krv-a-bubble svg {\n    width: 22px;\n    height: 22px;\n  }\n}\n\n\n/* ========== Theme: dark (isolated from landing Tailwind) ==========\n * Triggers:\n *  - html[data-theme=\"dark\"] (landings + WP theme toggle)\n *  - .krv-assistant.krv-a-dark (JS class from prefers-color-scheme / classes)\n */\nhtml[data-theme=\"dark\"] .krv-assistant,\n.krv-assistant.krv-a-dark {\n  --krv-a-bg: #121a2b;\n  --krv-a-bg-soft: #0c1320;\n  --krv-a-bg-msg: #152238;\n  --krv-a-line: #3d5a9a;\n  --krv-a-ink: #e8eefc;\n  --krv-a-mute: #b6c4e0;\n  --krv-a-accent: #5b8cff;\n  --krv-a-accent-h: #7aa3ff;\n  --krv-a-accent-soft: #1a2744;\n  --krv-a-user: #315fe8;\n  --krv-a-shadow: 0 10px 32px rgba(0, 0, 0, 0.5);\n  color-scheme: dark;\n  color: var(--krv-a-ink) !important;\n}\n\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-panel,\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-head,\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-msgs,\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-quick,\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-handoff,\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-form,\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-composer,\n.krv-assistant.krv-a-dark .krv-a-panel,\n.krv-assistant.krv-a-dark .krv-a-head,\n.krv-assistant.krv-a-dark .krv-a-msgs,\n.krv-assistant.krv-a-dark .krv-a-quick,\n.krv-assistant.krv-a-dark .krv-a-handoff,\n.krv-assistant.krv-a-dark .krv-a-form,\n.krv-assistant.krv-a-dark .krv-a-composer {\n  background: var(--krv-a-bg) !important;\n  border-color: var(--krv-a-line) !important;\n  color: var(--krv-a-ink) !important;\n}\n\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-msgs,\n.krv-assistant.krv-a-dark .krv-a-msgs {\n  background: var(--krv-a-bg-soft) !important;\n}\n\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-head,\n.krv-assistant.krv-a-dark .krv-a-head {\n  border-bottom: 1px solid var(--krv-a-line) !important;\n}\n\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-handoff,\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-composer,\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-form,\n.krv-assistant.krv-a-dark .krv-a-handoff,\n.krv-assistant.krv-a-dark .krv-a-composer,\n.krv-assistant.krv-a-dark .krv-a-form {\n  border-top-color: var(--krv-a-line) !important;\n  border-bottom-color: var(--krv-a-line) !important;\n}\n\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-title,\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-head h2,\n.krv-assistant.krv-a-dark .krv-a-title,\n.krv-assistant.krv-a-dark .krv-a-head h2 {\n  color: #ffffff !important;\n}\n\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-sub,\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-head p,\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-typing,\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-msg.sys,\n.krv-assistant.krv-a-dark .krv-a-sub,\n.krv-assistant.krv-a-dark .krv-a-head p,\n.krv-assistant.krv-a-dark .krv-a-typing,\n.krv-assistant.krv-a-dark .krv-a-msg.sys {\n  color: var(--krv-a-mute) !important;\n}\n\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-avatar,\n.krv-assistant.krv-a-dark .krv-a-avatar {\n  background: var(--krv-a-accent-soft) !important;\n  color: var(--krv-a-accent) !important;\n}\n\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-close,\n.krv-assistant.krv-a-dark .krv-a-close {\n  color: var(--krv-a-mute) !important;\n  background: transparent !important;\n}\n\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-close:hover,\n.krv-assistant.krv-a-dark .krv-a-close:hover {\n  color: #fff !important;\n  background: #1a2744 !important;\n}\n\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-msg.bot,\n.krv-assistant.krv-a-dark .krv-a-msg.bot {\n  background: #152238 !important;\n  border: 1px solid var(--krv-a-line) !important;\n  color: var(--krv-a-ink) !important;\n}\n\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-msg.user,\n.krv-assistant.krv-a-dark .krv-a-msg.user {\n  background: #315fe8 !important;\n  color: #ffffff !important;\n  border-color: transparent !important;\n}\n\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-chip,\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-handoff a,\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-handoff button,\n.krv-assistant.krv-a-dark .krv-a-chip,\n.krv-assistant.krv-a-dark .krv-a-handoff a,\n.krv-assistant.krv-a-dark .krv-a-handoff button {\n  background: #152238 !important;\n  border: 1px solid var(--krv-a-line) !important;\n  color: var(--krv-a-ink) !important;\n}\n\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-chip:hover,\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-handoff a:hover,\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-handoff button:hover,\n.krv-assistant.krv-a-dark .krv-a-chip:hover,\n.krv-assistant.krv-a-dark .krv-a-handoff a:hover,\n.krv-assistant.krv-a-dark .krv-a-handoff button:hover {\n  background: #1a2744 !important;\n  border-color: #5b8cff !important;\n  color: #c7d7ff !important;\n}\n\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-form input,\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-form textarea,\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-form select,\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-composer textarea,\n.krv-assistant.krv-a-dark .krv-a-form input,\n.krv-assistant.krv-a-dark .krv-a-form textarea,\n.krv-assistant.krv-a-dark .krv-a-form select,\n.krv-assistant.krv-a-dark .krv-a-composer textarea {\n  background: #0c1320 !important;\n  border: 1px solid var(--krv-a-line) !important;\n  color: #e8eefc !important;\n}\n\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-form input::placeholder,\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-form textarea::placeholder,\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-composer textarea::placeholder,\n.krv-assistant.krv-a-dark .krv-a-form input::placeholder,\n.krv-assistant.krv-a-dark .krv-a-form textarea::placeholder,\n.krv-assistant.krv-a-dark .krv-a-composer textarea::placeholder {\n  color: #7a8aab !important;\n}\n\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-btn.ghost,\n.krv-assistant.krv-a-dark .krv-a-btn.ghost {\n  background: #152238 !important;\n  border: 1px solid var(--krv-a-line) !important;\n  color: var(--krv-a-mute) !important;\n}\n\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-btn.primary,\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-send,\n.krv-assistant.krv-a-dark .krv-a-btn.primary,\n.krv-assistant.krv-a-dark .krv-a-send {\n  background: #315fe8 !important;\n  color: #ffffff !important;\n  border-color: transparent !important;\n}\n\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-btn.primary:hover,\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-send:hover,\n.krv-assistant.krv-a-dark .krv-a-btn.primary:hover,\n.krv-assistant.krv-a-dark .krv-a-send:hover {\n  background: #244ac2 !important;\n}\n\n/* Bubble stays brand blue in dark (not muddy slate) */\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-bubble,\n.krv-assistant.krv-a-dark .krv-a-bubble {\n  background: #315fe8 !important;\n  color: #ffffff !important;\n  border: 0 !important;\n  box-shadow: 0 8px 24px rgba(49, 95, 232, 0.5) !important;\n}\n\nhtml[data-theme=\"dark\"] .krv-assistant.is-open .krv-a-bubble,\n.krv-assistant.krv-a-dark.is-open .krv-a-bubble {\n  background: #244ac2 !important;\n  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.4) !important;\n}\n\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-tip,\n.krv-assistant.krv-a-dark .krv-a-tip {\n  background: #152238 !important;\n  border: 1px solid var(--krv-a-line) !important;\n  color: var(--krv-a-ink) !important;\n}\n\nhtml[data-theme=\"dark\"] .krv-assistant .krv-a-tip-x,\n.krv-assistant.krv-a-dark .krv-a-tip-x {\n  color: var(--krv-a-mute) !important;\n}\n\n/* System dark only when site does not force light (vars fallback before JS class) */\n@media (prefers-color-scheme: dark) {\n  html:not([data-theme=\"light\"]) .krv-assistant:not(.krv-a-dark) {\n    --krv-a-bg: #121a2b;\n    --krv-a-bg-soft: #0c1320;\n    --krv-a-bg-msg: #152238;\n    --krv-a-line: #3d5a9a;\n    --krv-a-ink: #e8eefc;\n    --krv-a-mute: #b6c4e0;\n    --krv-a-accent: #5b8cff;\n    --krv-a-accent-h: #7aa3ff;\n    --krv-a-accent-soft: #1a2744;\n    --krv-a-user: #315fe8;\n    --krv-a-shadow: 0 10px 32px rgba(0, 0, 0, 0.5);\n    color-scheme: dark;\n  }\n}\n\n/* Smooth token switches when site toggles data-theme */\n.krv-assistant,\n.krv-assistant .krv-a-panel,\n.krv-assistant .krv-a-bubble,\n.krv-assistant .krv-a-tip,\n.krv-assistant .krv-a-msg,\n.krv-assistant .krv-a-chip,\n.krv-assistant .krv-a-form input,\n.krv-assistant .krv-a-form textarea,\n.krv-assistant .krv-a-form select,\n.krv-assistant .krv-a-composer textarea {\n  transition: background-color 0.18s ease, color 0.18s ease, border-color 0.18s ease,\n    box-shadow 0.18s ease;\n}\n\n/* Prefer reduced motion */\n@media (prefers-reduced-motion: reduce) {\n  .krv-assistant .krv-a-bubble {\n    transition: none;\n  }\n}\n";

  var I18N = {
    ru: {
      title: "Помощник Dr.Slon",
      subtitleDefault: "Услуги и заявки",
      openChat: "Открыть чат",
      close: "Закрыть",
      tipAria: "Нужна помощь?",
      tipClose: "Закрыть подсказку",
      tipDefault: "Нужна помощь?",
      placeholder: "Напишите вопрос…",
      send: "Отправить",
      formTitle: "Заявка",
      need: "Что нужно *",
      needPh: "Кратко опишите задачу",
      contact: "Контакт *",
      contactPh: "Telegram / телефон / email",
      budget: "Бюджет",
      budgetPh: "от 40 000 ₽",
      urgency: "Срочность",
      urgencyNormal: "Обычная",
      urgencySoon: "Срочно",
      urgencyUrgent: "Очень срочно",
      topic: "Тема",
      topicPh: "Боты / WordPress / …",
      submit: "Отправить",
      cancel: "Отмена",
      leadBtn: "Заявка",
      price: "Прайс",
      typing: "Печатает…",
      suggestLead: "Можно оставить заявку кнопкой ниже",
      offline:
        "Чат временно недоступен. Telegram: https://t.me/DrSlon",
      chatFail:
        "Не удалось ответить. Напишите в Telegram @DrSlon или на krivoshein.site/contacts/",
      leadFail:
        "Не удалось отправить заявку. Напишите @DrSlon или через форму контактов.",
      greetHub:
        "Здравствуйте! Я помощник Алексея Кривошеина (Dr.Slon): WordPress, VPS, боты, Директ, лендинги, AI-ready. Чем помочь?",
      greetDefault:
        "Здравствуйте! Я помощник Алексея Кривошеина. Могу рассказать об услугах и помочь с заявкой.",
      tips: {
        bots: "Есть вопросы по ботам?",
        vps: "Нужна помощь с сервером?",
        wordpress: "Помочь с WordPress?",
        direct: "Вопросы по Директу?",
        landing: "Нужен лендинг?",
        "ai-ready": "Подготовить сайт к AI?",
        hub: "Нужна помощь?",
        general: "Нужна помощь?",
      },
      greets: {
        bots:
          "Здравствуйте! Я помощник Алексея Кривошеина. Здесь — чат-боты MAX и Telegram: заявки, CRM, уведомления, сценарии. Могу сориентировать по формату и цене «от», или помочь оставить заявку.",
        vps:
          "Здравствуйте! Помогу с VPS: Linux, Nginx, Docker, SSL, firewall, перенос. Настройка под ключ — от 10 000 ₽. Что нужно настроить?",
        wordpress:
          "Здравствуйте! Здесь — поддержка и доработка WordPress: обновления, бэкапы, безопасность, правки. Техподдержка — от 20 000 ₽/мес. Чем помочь?",
        direct:
          "Здравствуйте! Консультации, аудит, настройка и ведение Яндекс.Директ. Аудит — от 10 000 ₽. Что интересует?",
        landing:
          "Здравствуйте! Лендинги под ключ: визитка от 25 000 ₽, с SEO и блоками — от 45 000 ₽. Расскажите задачу — подскажу формат.",
        "ai-ready":
          "Здравствуйте! Подготовка сайта к нейропоиску и AI-агентам: Start / Pro / Bot-ready. Без обещаний «топ-1» — только честная техника и контент.",
        hub: null,
        general: null,
      },
      quick: {
        bots: ["Сколько стоит бот?", "Какие сроки?", "Оставить заявку", "Другие услуги"],
        vps: ["Настройка VPS", "Сколько стоит?", "Оставить заявку", "Другие услуги"],
        wordpress: ["Техподдержка", "Доработка сайта", "Оставить заявку", "Другие услуги"],
        direct: ["Аудит", "Ведение", "Оставить заявку", "Другие услуги"],
        landing: ["Сколько стоит лендинг?", "Сроки", "Оставить заявку", "Другие услуги"],
        "ai-ready": ["Пакеты Start / Pro", "Bot-ready", "Оставить заявку", "Другие услуги"],
        hub: ["Прайс / услуги", "WordPress", "Оставить заявку", "Контакты"],
        general: ["Какие услуги?", "Оставить заявку", "Telegram", "Контакты"],
      },
      leaveLead: "Оставить заявку",
    },
    en: {
      title: "Dr.Slon Assistant",
      subtitleDefault: "Services & leads",
      openChat: "Open chat",
      close: "Close",
      tipAria: "Need help?",
      tipClose: "Dismiss tip",
      tipDefault: "Need help?",
      placeholder: "Type your question…",
      send: "Send",
      formTitle: "Lead form",
      need: "What do you need *",
      needPh: "Briefly describe the task",
      contact: "Contact *",
      contactPh: "Telegram / phone / email",
      budget: "Budget",
      budgetPh: "from 40,000 ₽",
      urgency: "Urgency",
      urgencyNormal: "Normal",
      urgencySoon: "Soon",
      urgencyUrgent: "Very urgent",
      topic: "Topic",
      topicPh: "Bots / WordPress / …",
      submit: "Send",
      cancel: "Cancel",
      leadBtn: "Lead",
      price: "Pricing",
      typing: "Typing…",
      suggestLead: "You can leave a lead with the button below",
      offline: "Chat is temporarily unavailable. Telegram: https://t.me/DrSlon",
      chatFail:
        "Could not reply. Message Telegram @DrSlon or krivoshein.site/contacts/",
      leadFail:
        "Could not send the lead. Message @DrSlon or use the contacts form.",
      greetHub:
        "Hi! I'm Alexey Krivoshein's assistant (Dr.Slon): WordPress, VPS, bots, Yandex Direct, landings, AI-ready. How can I help?",
      greetDefault:
        "Hi! I'm Alexey Krivoshein's assistant. I can outline services and help you leave a lead.",
      tips: {
        bots: "Questions about bots?",
        vps: "Need help with a server?",
        wordpress: "Help with WordPress?",
        direct: "Questions about Yandex Direct?",
        landing: "Need a landing page?",
        "ai-ready": "Prepare a site for AI?",
        hub: "Need help?",
        general: "Need help?",
      },
      greets: {
        bots:
          "Hi! Chatbots for MAX and Telegram: leads, CRM, notifications, support flows. I can outline format and “from” pricing, or help you leave a lead.",
        vps:
          "Hi! I can help with VPS: Linux, Nginx, Docker, SSL, firewall, migrations. Turnkey setup from 10,000 ₽. What do you need?",
        wordpress:
          "Hi! WordPress support and development: updates, backups, security, fixes. Maintenance from 20,000 ₽/mo. How can I help?",
        direct:
          "Hi! Yandex Direct consulting, audit, setup and management. Audit from 10,000 ₽. What are you looking for?",
        landing:
          "Hi! Turnkey landings: simple from 25,000 ₽, with SEO blocks from 45,000 ₽. Tell me the goal — I'll suggest a format.",
        "ai-ready":
          "Hi! Preparing sites for AI search and agents: Start / Pro / Bot-ready. No “#1 rank” promises — solid tech and content only.",
        hub: null,
        general: null,
      },
      quick: {
        bots: ["Bot pricing?", "Timeline?", "Leave a lead", "Other services"],
        vps: ["VPS setup", "Pricing?", "Leave a lead", "Other services"],
        wordpress: ["Maintenance", "Site fixes", "Leave a lead", "Other services"],
        direct: ["Audit", "Management", "Leave a lead", "Other services"],
        landing: ["Landing price?", "Timeline", "Leave a lead", "Other services"],
        "ai-ready": ["Start / Pro packs", "Bot-ready", "Leave a lead", "Other services"],
        hub: ["Pricing / services", "WordPress", "Leave a lead", "Contacts"],
        general: ["What services?", "Leave a lead", "Telegram", "Contacts"],
      },
      leaveLead: "Leave a lead",
    },
  };

  var currentLang = "ru";

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

  function t(key) {
    var pack = I18N[currentLang] || I18N.ru;
    if (pack[key] != null) return pack[key];
    return I18N.ru[key] != null ? I18N.ru[key] : key;
  }

  function detectLang() {
    try {
      var html = document.documentElement;
      var lang = (html.getAttribute("lang") || "").toLowerCase();
      if (lang.indexOf("en") === 0) return "en";
      if (lang.indexOf("ru") === 0) return "ru";
      if (html.getAttribute("data-lang") === "en") return "en";
      if (html.classList.contains("en") || html.classList.contains("lang-en"))
        return "en";
      var body = document.body;
      if (body) {
        if (body.getAttribute("data-lang") === "en") return "en";
        if (body.classList.contains("en") || body.classList.contains("lang-en"))
          return "en";
      }
      try {
        var stored = localStorage.getItem("krv_lang");
        if (stored === "en" || stored === "ru") return stored;
      } catch (e) {}
      var q = new URLSearchParams(location.search).get("lang");
      if (q === "en" || q === "ru") return q;
    } catch (e2) {}
    return "ru";
  }

  function siteKeyFromHost() {
    var host = (location.hostname || "").toLowerCase().replace(/^www\./, "");
    var map = {
      "bots.krivoshein.site": "bots",
      "vps.krivoshein.site": "vps",
      "wordpress.krivoshein.site": "wordpress",
      "direct.krivoshein.site": "direct",
      "landing.krivoshein.site": "landing",
      "ai-ready.krivoshein.site": "ai-ready",
      "krivoshein.site": "hub",
    };
    return map[host] || "general";
  }

  function localizedGreeting(siteKey) {
    var pack = I18N[currentLang] || I18N.ru;
    var g = pack.greets && pack.greets[siteKey];
    if (g) return g;
    if (siteKey === "hub") return pack.greetHub || pack.greetDefault;
    return pack.greetDefault;
  }

  function localizedQuick(siteKey) {
    var pack = I18N[currentLang] || I18N.ru;
    var q = pack.quick && pack.quick[siteKey];
    return q ? q.slice() : pack.quick.general.slice();
  }

  function proactiveHint() {
    var pack = I18N[currentLang] || I18N.ru;
    var key = siteKeyFromHost();
    return (pack.tips && pack.tips[key]) || pack.tipDefault;
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

  var _stackBusy = false;
  /* Clear air between bubble bottom and fixed CTA top (px). */
  var STACK_EXTRA_GAP = 20;
  var STACK_MOBILE_MIN = 96;
  var STACK_MOBILE_MIN_NARROW = 104;

  function updateStackOffset(root) {
    if (!root || _stackBusy) return;
    _stackBusy = true;
    try {
      var base = 16;
      var vh = window.innerHeight || document.documentElement.clientHeight || 0;
      var maxBottom = 0;
      var isMobile =
        window.matchMedia &&
        window.matchMedia("(max-width: 767.98px)").matches;
      var isNarrow =
        window.matchMedia &&
        window.matchMedia("(max-width: 380px)").matches;

      function consider(el, pad) {
        if (!isVisible(el)) return;
        // Never treat our own widget chrome as a bottom bar
        if (el.closest && el.closest(".krv-assistant")) return;
        var cs = window.getComputedStyle(el);
        if (cs.position !== "fixed" && cs.position !== "sticky") return;
        var r = el.getBoundingClientRect();
        if (r.bottom < vh - 2) return;
        if (r.top > vh - 8) return;
        var h = Math.ceil(r.height);
        var need = h + (pad != null ? pad : STACK_EXTRA_GAP);
        if (need > maxBottom) maxBottom = need;
      }

      document.querySelectorAll(".mobile-cta-bar").forEach(function (el) {
        consider(el, STACK_EXTRA_GAP);
      });
      document.querySelectorAll(".krv-cookie, #krv-cookie").forEach(function (el) {
        if (el.hasAttribute("hidden")) return;
        if (el.classList && el.classList.contains("is-hidden")) return;
        consider(el, 12);
      });

      if (isMobile) {
        var minStack = isNarrow ? STACK_MOBILE_MIN_NARROW : STACK_MOBILE_MIN;
        var bar = document.querySelector(".mobile-cta-bar");
        if (bar) {
          var d = window.getComputedStyle(bar).display;
          if (d !== "none") maxBottom = Math.max(maxBottom, minStack);
        } else if (
          document.body &&
          document.body.classList.contains("has-mobile-cta")
        ) {
          maxBottom = Math.max(maxBottom, minStack);
        } else if (maxBottom < 40) {
          /* no bar measured — keep desktop-ish base on mobile without CTA */
        }
      }

      var stack = Math.max(base, maxBottom);
      var cap = Math.max(16, Math.floor(vh * 0.4));
      if (stack > cap) stack = cap;
      var next = stack + "px";
      // Avoid style thrash: setting --var rewrites the style attr and used to
      // retrigger a body MutationObserver → infinite loop / frozen page.
      if (root.style.getPropertyValue("--krv-a-stack-bottom") !== next) {
        root.style.setProperty("--krv-a-stack-bottom", next);
      }
    } finally {
      _stackBusy = false;
    }
  }

  function isSiteDark() {
    try {
      var html = document.documentElement;
      var t = (html.getAttribute("data-theme") || "").toLowerCase();
      if (t === "dark") return true;
      if (t === "light") return false;
      if (html.classList.contains("dark") || html.classList.contains("theme-dark"))
        return true;
      if (html.classList.contains("light") || html.classList.contains("theme-light"))
        return false;
      if (document.body) {
        if (document.body.classList.contains("dark")) return true;
        if (document.body.getAttribute("data-theme") === "dark") return true;
      }
      if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches)
        return true;
    } catch (e) {}
    return false;
  }

  function applyThemeClass(root) {
    if (!root) return;
    if (isSiteDark()) root.classList.add("krv-a-dark");
    else root.classList.remove("krv-a-dark");
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

  function formHtml() {
    return (
      '<p class="krv-a-form-title" data-i18n="formTitle"></p>' +
      '<label class="krv-a-field"><span data-i18n="need"></span>' +
      '<textarea name="need" rows="2" required maxlength="4000" data-i18n-ph="needPh"></textarea></label>' +
      '<label class="krv-a-field"><span data-i18n="contact"></span>' +
      '<input name="contact" required maxlength="300" data-i18n-ph="contactPh" autocomplete="tel"></label>' +
      '<div class="krv-a-field-row">' +
      '<label class="krv-a-field"><span data-i18n="budget"></span>' +
      '<input name="budget" maxlength="200" data-i18n-ph="budgetPh"></label>' +
      '<label class="krv-a-field"><span data-i18n="urgency"></span>' +
      '<select name="urgency">' +
      '<option value="normal" data-i18n="urgencyNormal"></option>' +
      '<option value="soon" data-i18n="urgencySoon"></option>' +
      '<option value="urgent" data-i18n="urgencyUrgent"></option>' +
      "</select></label></div>" +
      '<label class="krv-a-field"><span data-i18n="topic"></span>' +
      '<input name="topic" maxlength="200" data-i18n-ph="topicPh"></label>' +
      '<label class="krv-a-hp" aria-hidden="true">Site<input name="website" tabindex="-1" autocomplete="off"></label>' +
      '<div class="krv-a-form-actions">' +
      '<button type="submit" class="krv-a-btn primary" data-i18n="submit"></button>' +
      '<button type="button" class="krv-a-btn ghost" data-cancel-lead data-i18n="cancel"></button>' +
      "</div>"
    );
  }

  function applyI18n(ui) {
    if (!ui) return;
    currentLang = detectLang();
    ui.root.setAttribute("data-lang", currentLang);
    ui.h2.textContent = t("title");
    if (!ui.sub.dataset.locked) {
      ui.sub.textContent = t("subtitleDefault");
    }
    ui.bubble.setAttribute("aria-label", t("openChat"));
    ui.closeBtn.setAttribute("aria-label", t("close"));
    ui.tip.setAttribute("aria-label", t("tipAria"));
    ui.tipX.setAttribute("aria-label", t("tipClose"));
    ui.ta.placeholder = t("placeholder");
    ui.send.setAttribute("aria-label", t("send"));
    if (ui.tipText && !ui.root.classList.contains("is-nudge")) {
      ui.tipText.textContent = t("tipDefault");
    } else if (ui.tipText && ui.root.classList.contains("is-nudge")) {
      ui.tipText.textContent = proactiveHint();
    }
    ui.form.querySelectorAll("[data-i18n]").forEach(function (node) {
      var k = node.getAttribute("data-i18n");
      if (k) node.textContent = t(k);
    });
    ui.form.querySelectorAll("[data-i18n-ph]").forEach(function (node) {
      var k = node.getAttribute("data-i18n-ph");
      if (k) node.setAttribute("placeholder", t(k));
    });
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
    panel.setAttribute("aria-label", "Dr.Slon Assistant");

    var head = el("div", "krv-a-head");
    var headLeft = el("div", "krv-a-head-left");
    var avatar = el("div", "krv-a-avatar", "DS");
    var titles = el("div", "krv-a-titles");
    var h2 = el("div", "krv-a-title", "Dr.Slon Assistant");
    var sub = el("div", "krv-a-sub", "…");
    titles.appendChild(h2);
    titles.appendChild(sub);
    headLeft.appendChild(avatar);
    headLeft.appendChild(titles);
    var closeBtn = el("button", "krv-a-close", "×");
    closeBtn.type = "button";
    head.appendChild(headLeft);
    head.appendChild(closeBtn);

    var msgs = el("div", "krv-a-msgs");
    var quick = el("div", "krv-a-quick");
    var handoff = el("div", "krv-a-handoff");

    var form = el("form", "krv-a-form");
    form.innerHTML = formHtml();

    var composer = el("div", "krv-a-composer");
    var ta = el("textarea");
    ta.rows = 1;
    var send = el("button", "krv-a-send", "→");
    send.type = "button";
    composer.appendChild(ta);
    composer.appendChild(send);

    var bubble = el("button", "krv-a-bubble");
    bubble.type = "button";
    bubble.innerHTML = iconChat();

    var tip = el("button", "krv-a-tip");
    tip.type = "button";
    tip.setAttribute("hidden", "hidden");
    var tipText = el("span", "krv-a-tip-text", "");
    var tipX = el("span", "krv-a-tip-x", "×");
    tipX.setAttribute("role", "button");
    tipX.tabIndex = 0;
    tip.appendChild(tipText);
    tip.appendChild(tipX);

    var nudgeWrap = el("div", "krv-a-nudge-wrap");
    nudgeWrap.appendChild(tip);
    nudgeWrap.appendChild(bubble);

    panel.appendChild(head);
    panel.appendChild(msgs);
    panel.appendChild(quick);
    panel.appendChild(handoff);
    panel.appendChild(form);
    panel.appendChild(composer);
    wrap.appendChild(panel);
    wrap.appendChild(nudgeWrap);
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
      tip: tip,
      tipText: tipText,
      tipX: tipX,
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
      [h.contacts_url, h.contacts_label || (currentLang === "en" ? "Contacts" : "Контакты")],
      [h.price_url, t("price")],
    ];
    links.forEach(function (pair) {
      if (!pair[0]) return;
      var a = el("a", null, pair[1]);
      a.href = pair[0];
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      ui.handoff.appendChild(a);
    });
    var lead = el("button", "krv-a-chip", t("leadBtn"));
    lead.type = "button";
    lead.addEventListener("click", function () {
      showLeadForm(ui, true);
    });
    ui.handoff.appendChild(lead);
  }

  function showLeadForm(ui, on) {
    if (on) {
      ui.form.classList.add("is-on");
      ui.root.classList.add("is-lead");
      ui.composer.classList.add("is-hidden");
      ui.quick.style.display = "none";
      if (ui.handoff) ui.handoff.style.display = "none";
      // Scroll form to top so title + first fields are visible
      try {
        ui.form.scrollTop = 0;
        if (ui.msgs) ui.msgs.scrollTop = ui.msgs.scrollHeight;
      } catch (e) {}
      setTimeout(function () {
        try {
          ui.form.scrollTop = 0;
          var first = ui.form.querySelector(
            "textarea:not(.krv-a-hp), input:not(.krv-a-hp):not([type=hidden])"
          );
          if (first && isMobileViewport()) {
            first.focus({ preventScroll: true });
            // Keep focused field inside the scrollable form
            first.scrollIntoView({ block: "nearest", behavior: "smooth" });
          }
        } catch (e2) {}
      }, 60);
    } else {
      ui.form.classList.remove("is-on");
      ui.root.classList.remove("is-lead");
      ui.composer.classList.remove("is-hidden");
      ui.quick.style.display = "";
      if (ui.handoff) ui.handoff.style.display = "";
    }
    updateStackOffset(ui.root);
  }

  function isMobileViewport() {
    return (
      window.matchMedia &&
      window.matchMedia("(max-width: 767.98px)").matches
    );
  }

  /**
   * Hide landing .mobile-cta-bar while the chat panel is open on mobile,
   * so it does not cover the composer. Restore when panel closes / on desktop.
   */
  function syncMobileCtaBar(ui) {
    if (!document.body) return;
    var open = !!(ui && ui.root && ui.root.classList.contains("is-open"));
    var hide = open && isMobileViewport();
    if (hide) document.body.classList.add("krv-a-panel-open");
    else document.body.classList.remove("krv-a-panel-open");

    // Direct style fallback if body class is overridden by landing CSS
    try {
      document.querySelectorAll(".mobile-cta-bar").forEach(function (bar) {
        if (hide) {
          if (!bar.dataset.krvCtaPrevDisplay) {
            bar.dataset.krvCtaPrevDisplay = bar.style.display || "";
          }
          bar.style.setProperty("display", "none", "important");
        } else if (bar.dataset.krvCtaPrevDisplay != null) {
          var prev = bar.dataset.krvCtaPrevDisplay;
          bar.style.removeProperty("display");
          if (prev) bar.style.display = prev;
          delete bar.dataset.krvCtaPrevDisplay;
        }
      });
    } catch (e) {}

    if (ui && ui.root) updateStackOffset(ui.root);
  }

  function openPanel(ui, open) {
    if (open) ui.root.classList.add("is-open");
    else {
      ui.root.classList.remove("is-open");
      // Drop keyboard lift when fully closed
      try {
        ui.root.style.setProperty("--krv-a-keyboard-inset", "0px");
      } catch (e) {}
    }
    syncMobileCtaBar(ui);
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
        (data && (data.detail || data.message)) || "Error " + res.status;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return data;
  }

  function isProactiveDismissed() {
    try {
      return localStorage.getItem(PROACTIVE_DISMISS_KEY) === "1";
    } catch (e) {
      return false;
    }
  }

  function isProactiveShown() {
    try {
      return sessionStorage.getItem(PROACTIVE_SHOWN_KEY) === "1";
    } catch (e) {
      return false;
    }
  }

  function markProactiveShown() {
    try {
      sessionStorage.setItem(PROACTIVE_SHOWN_KEY, "1");
    } catch (e) {}
  }

  function markProactiveDismissed() {
    try {
      localStorage.setItem(PROACTIVE_DISMISS_KEY, "1");
      sessionStorage.setItem(PROACTIVE_SHOWN_KEY, "1");
    } catch (e) {}
  }

  function proactiveDelayMs() {
    var w = window.innerWidth || 1200;
    return w < 480 ? PROACTIVE_MS_MOBILE : PROACTIVE_MS;
  }

  function showNudge(ui, state) {
    if (!ui || !ui.root) return;
    if (state.proactiveDone || isProactiveDismissed() || isProactiveShown()) return;
    if (ui.root.classList.contains("is-open")) return;
    ui.tipText.textContent = proactiveHint();
    ui.tip.removeAttribute("hidden");
    ui.root.classList.add("is-nudge");
    state.nudgeVisible = true;
    markProactiveShown();
    state.proactiveDone = true;
  }

  function hideNudge(ui, state, dismissed) {
    if (!ui || !ui.root) return;
    ui.root.classList.remove("is-nudge");
    ui.tip.setAttribute("hidden", "hidden");
    state.nudgeVisible = false;
    if (dismissed) {
      markProactiveDismissed();
      state.proactiveDone = true;
    }
  }

  function setupProactive(ui, state) {
    if (isProactiveDismissed() || isProactiveShown()) {
      state.proactiveDone = true;
      return;
    }
    state.proactiveDone = false;
    state.nudgeVisible = false;
    state.idleTimer = null;
    state.lastScrollY = window.scrollY || window.pageYOffset || 0;

    function clearIdle() {
      if (state.idleTimer) {
        clearTimeout(state.idleTimer);
        state.idleTimer = null;
      }
    }

    function armIdle() {
      if (state.proactiveDone) return;
      if (ui.root.classList.contains("is-open")) return;
      clearIdle();
      state.idleTimer = setTimeout(function () {
        showNudge(ui, state);
      }, proactiveDelayMs());
    }

    function onActivity(ev) {
      if (state.proactiveDone && !state.nudgeVisible) return;
      if (ev && ev.type === "scroll") {
        var y = window.scrollY || window.pageYOffset || 0;
        var dy = Math.abs(y - state.lastScrollY);
        state.lastScrollY = y;
        if (dy < 2) return;
      }
      if (state.nudgeVisible) return;
      armIdle();
    }

    var opts = { passive: true, capture: true };
    ["mousemove", "mousedown", "click", "keydown", "touchstart", "touchmove", "wheel", "scroll"].forEach(
      function (type) {
        window.addEventListener(type, onActivity, opts);
      }
    );
    window.addEventListener(
      "focusin",
      function () {
        onActivity({ type: "focusin" });
      },
      true
    );

    setTimeout(armIdle, 800);
    state._armIdle = armIdle;
    state._clearIdle = clearIdle;
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
    state.siteKey = data.site_key || siteKeyFromHost();

    applyI18n(ui);
    ui.h2.textContent = t("title");
    ui.sub.textContent =
      currentLang === "en"
        ? data.site_label || t("subtitleDefault")
        : data.subtitle || data.site_label || t("subtitleDefault");
    ui.sub.dataset.locked = "1";

    if (!state.greeted) {
      var greet =
        currentLang === "en"
          ? localizedGreeting(state.siteKey)
          : data.greeting || localizedGreeting(state.siteKey);
      addMsg(ui, "bot", greet);
      state.greeted = true;
    }

    var quick =
      currentLang === "en"
        ? localizedQuick(state.siteKey)
        : data.quick_replies && data.quick_replies.length
          ? data.quick_replies
          : localizedQuick(state.siteKey);

    setQuick(ui, quick, function (label) {
      if (
        label === t("leaveLead") ||
        label === t("leadBtn") ||
        label === "Оставить заявку" ||
        label === "Leave a lead" ||
        label === "Заявка" ||
        label === "Lead"
      ) {
        showLeadForm(ui, true);
        return;
      }
      if (
        (label === "Telegram" || label.indexOf("Telegram") === 0) &&
        data.handoff &&
        data.handoff.telegram_url
      ) {
        window.open(data.handoff.telegram_url, "_blank", "noopener");
        return;
      }
      if (
        (label === "Контакты" || label === "Contacts") &&
        data.handoff &&
        data.handoff.contacts_url
      ) {
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
    var typing = el("div", "krv-a-typing", t("typing"));
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
      if (data.quick_replies && data.quick_replies.length && currentLang === "ru") {
        setQuick(ui, data.quick_replies, function (label) {
          if (label === t("leaveLead") || label === "Оставить заявку") {
            showLeadForm(ui, true);
            return;
          }
          sendMessage(ui, state, label);
        });
      }
      if (data.suggest_lead) {
        addMsg(ui, "sys", t("suggestLead"));
      }
    } catch (err) {
      typing.remove();
      addMsg(ui, "bot", t("chatFail"));
      console.warn("[krv-assistant]", err);
    } finally {
      state.busy = false;
      ui.send.disabled = false;
      ui.ta.focus();
    }
  }

  function urgencyLabelToApi(val) {
    // map select values to Russian API-friendly labels the backend already accepts
    if (val === "soon" || val === "Срочно" || val === "Soon") return "Срочно";
    if (val === "urgent" || val === "Очень срочно" || val === "Very urgent")
      return "Очень срочно";
    return "Обычная";
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
      urgency: urgencyLabelToApi(String(fd.get("urgency") || "normal")),
      contact: String(fd.get("contact") || ""),
      website: String(fd.get("website") || ""),
    };
    state.busy = true;
    try {
      var data = await api("/lead", payload);
      var leadMsg =
        (data && data.message) ||
        (currentLang === "en" ? "Lead sent." : "Заявка отправлена.");
      addMsg(ui, "bot", leadMsg);
      // Only close form on success; keep it open on rate-limit / soft errors
      if (!data || data.ok !== false) {
        showLeadForm(ui, false);
        formEl.reset();
      }
      if (data && data.handoff) setHandoff(ui, data.handoff);
    } catch (err) {
      var failText = (err && err.message) || t("leadFail");
      // Prefer human backend message if api() put it on Error
      if (failText && failText.indexOf("Error ") === 0) failText = t("leadFail");
      addMsg(ui, "bot", failText);
      console.warn("[krv-assistant]", err);
    } finally {
      state.busy = false;
    }
  }

  function openChat(ui, state) {
    updateStackOffset(ui.root);
    hideNudge(ui, state, false);
    if (state._clearIdle) state._clearIdle();
    state.proactiveDone = true;
    markProactiveShown();
    if (!ui.root.classList.contains("is-open")) {
      openPanel(ui, true);
    }
    if (!state.bootstrapped) {
      bootstrap(ui, state)
        .then(function () {
          state.bootstrapped = true;
        })
        .catch(function (err) {
          addMsg(ui, "bot", t("offline"));
          console.warn("[krv-assistant] bootstrap", err);
        });
    }
    setTimeout(function () {
      ui.ta.focus();
    }, 40);
  }

  function bind(ui, state) {
    ui.bubble.addEventListener("click", function () {
      if (ui.root.classList.contains("is-open")) {
        openPanel(ui, false);
        return;
      }
      openChat(ui, state);
    });
    ui.tip.addEventListener("click", function (e) {
      if (
        e.target === ui.tipX ||
        (e.target && e.target.classList && e.target.classList.contains("krv-a-tip-x"))
      ) {
        return;
      }
      openChat(ui, state);
    });
    ui.tipX.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      hideNudge(ui, state, true);
      if (state._clearIdle) state._clearIdle();
    });
    ui.tipX.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        e.stopPropagation();
        hideNudge(ui, state, true);
        if (state._clearIdle) state._clearIdle();
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

  function watchLangAndTheme(ui, state) {
    var html = document.documentElement;
    var lastLang = detectLang();
    var lastDark = isSiteDark();

    function refresh() {
      var lang = detectLang();
      var dark = isSiteDark();
      if (lang !== lastLang) {
        lastLang = lang;
        applyI18n(ui);
        if (state.bootstrapped) {
          ui.h2.textContent = t("title");
          if (state.handoff) setHandoff(ui, state.handoff);
          var sk = state.siteKey || siteKeyFromHost();
          setQuick(ui, localizedQuick(sk), function (label) {
            if (label === t("leaveLead") || label === t("leadBtn")) {
              showLeadForm(ui, true);
              return;
            }
            sendMessage(ui, state, label);
          });
        }
      }
      if (dark !== lastDark) {
        lastDark = dark;
        applyThemeClass(ui.root);
      } else {
        applyThemeClass(ui.root);
      }
    }

    applyThemeClass(ui.root);

    if (typeof MutationObserver !== "undefined") {
      var mo = new MutationObserver(refresh);
      mo.observe(html, {
        attributes: true,
        attributeFilter: ["lang", "data-theme", "data-lang", "class"],
      });
      if (document.body) {
        mo.observe(document.body, {
          attributes: true,
          attributeFilter: ["data-lang", "class", "data-theme"],
        });
      }
    }
    if (window.matchMedia) {
      try {
        var mql = window.matchMedia("(prefers-color-scheme: dark)");
        var onScheme = function () {
          applyThemeClass(ui.root);
        };
        if (mql.addEventListener) mql.addEventListener("change", onScheme);
        else if (mql.addListener) mql.addListener(onScheme);
      } catch (e) {}
    }
    // periodic light poll for SPA-like lang / theme switches
    setInterval(refresh, 1500);
  }

  function init() {
    loadCss();
    currentLang = detectLang();
    var ui = createUI();
    applyI18n(ui);
    applyThemeClass(ui.root);
    var state = {
      sessionId: getSession(),
      bootstrapped: false,
      greeted: false,
      busy: false,
      handoff: null,
      siteKey: siteKeyFromHost(),
    };
    bind(ui, state);
    setupProactive(ui, state);
    watchLangAndTheme(ui, state);
    updateStackOffset(ui.root);
    syncMobileCtaBar(ui);

    // Track visual viewport (mobile keyboard): shrink panel + lift above keyboard
    function syncVisualViewport() {
      try {
        var layoutH = window.innerHeight || document.documentElement.clientHeight || 0;
        var vv = window.visualViewport;
        var h = layoutH;
        var inset = 0;
        if (vv && vv.height) {
          h = vv.height;
          // Distance from layout bottom to visual viewport bottom ≈ keyboard
          inset = Math.round(layoutH - vv.height - (vv.offsetTop || 0));
          if (inset < 72) inset = 0; // ignore tiny browser chrome jitter
          // Cap so we never push the panel off-screen
          if (inset > layoutH * 0.55) inset = Math.round(layoutH * 0.55);
        }
        ui.root.style.setProperty("--krv-a-vv-h", Math.round(h) + "px");
        ui.root.style.setProperty(
          "--krv-a-keyboard-inset",
          Math.max(0, inset) + "px"
        );
      } catch (e) {}
    }
    syncVisualViewport();
    if (window.visualViewport) {
      window.visualViewport.addEventListener("resize", syncVisualViewport, {
        passive: true,
      });
      window.visualViewport.addEventListener("scroll", syncVisualViewport, {
        passive: true,
      });
    }

    // Keep focused form field visible above the keyboard inside the form scroller
    ui.form.addEventListener(
      "focusin",
      function (e) {
        var t = e.target;
        if (!t || !ui.root.classList.contains("is-lead")) return;
        if (!/^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName)) return;
        if (t.classList && t.classList.contains("krv-a-hp")) return;
        setTimeout(function () {
          try {
            syncVisualViewport();
            t.scrollIntoView({ block: "center", behavior: "smooth" });
          } catch (err) {}
        }, 180);
      },
      true
    );

    var onResize = function () {
      syncVisualViewport();
      syncMobileCtaBar(ui);
      updateStackOffset(ui.root);
    };
    window.addEventListener("resize", onResize, { passive: true });
    window.addEventListener("orientationchange", onResize, { passive: true });
    // Watch for late-mounted mobile CTA only — never observe style attrs
    // (our own --krv-a-stack-bottom writes would infinite-loop the page).
    if (typeof MutationObserver !== "undefined" && document.body) {
      var stackTimer = null;
      var mo = new MutationObserver(function (records) {
        var relevant = false;
        for (var i = 0; i < records.length; i++) {
          var rec = records[i];
          var t = rec.target;
          if (t && t.closest && t.closest(".krv-assistant")) continue;
          if (rec.type === "childList") {
            relevant = true;
            break;
          }
          if (rec.type === "attributes") {
            var name = rec.attributeName;
            if (name === "class" || name === "hidden") {
              relevant = true;
              break;
            }
          }
        }
        if (!relevant) return;
        if (stackTimer) clearTimeout(stackTimer);
        stackTimer = setTimeout(function () {
          updateStackOffset(ui.root);
        }, 80);
      });
      mo.observe(document.body, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ["class", "hidden"],
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
