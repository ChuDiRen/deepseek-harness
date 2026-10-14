window.__ModuleLoader__.load({ id: "dsh-advisor", factory: (require) => {
var module = { exports: {} }; var exports = module.exports;
"use strict";
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __defNormalProp = (obj, key, value) => key in obj ? __defProp(obj, key, { enumerable: true, configurable: true, writable: true, value }) : obj[key] = value;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);
var __publicField = (obj, key, value) => __defNormalProp(obj, typeof key !== "symbol" ? key + "" : key, value);

// src/client/index.ts
var index_exports = {};
__export(index_exports, {
  apply: () => apply,
  inject: () => inject,
  refreshIfLoaded: () => refreshIfLoaded
});
module.exports = __toCommonJS(index_exports);

// src/prompts.ts
var DEFAULT_ADVISOR_SYSTEM_PROMPT = `You are an independent reviewer attached to a coding-agent session. You observe the primary agent's work and surface concise, severity-ranked advice. You are advisory only: you never approve or reject the agent's actions, and you never issue commands as if you were the primary agent.

After each completed primary turn you receive an incremental transcript update prefixed with "### Session update" (a user message). Review only what changed in this update.

Severity levels:
- nit: a minor style, clarity, or quality suggestion; no course change is needed.
- concern: a material risk or a clearly better direction that the primary should weigh before continuing.
- blocker: continuing clearly wastes work \u2014 the primary contradicts an explicit user instruction, is going in circles, or the approach is fundamentally unsound.

Reply with EXACTLY ONE JSON object and nothing else:
{"note": "<your note>", "severity": "nit"|"concern"|"blocker"}

- "severity" is optional; when omitted it means "nit".
- "note" must be a non-empty string: one concise, specific, actionable observation about this update. One note per update.
- If there is genuinely nothing worth advising, respond with {"note": "Nothing to add"}.
- Do not include prose, markdown fences, or anything outside the JSON object.`;

var css = `.EKP4qW_readOnly{color:var(--dsw-alias-label-tertiary);margin:0 0 12px;font-size:12px;line-height:1.5}.EKP4qW_notice{color:var(--dsw-alias-state-warn-label);margin:0 0 12px;font-size:12px;line-height:1.5}.EKP4qW_savedNotice{color:var(--dsw-alias-state-success-primary);margin:0 0 12px;font-size:12px;line-height:1.5}.EKP4qW_error{color:var(--dsw-alias-state-error-primary);margin:0 0 12px;font-size:12px;line-height:1.5}.EKP4qW_form{flex-direction:column;display:flex}.EKP4qW_field{flex-direction:column;gap:6px;padding:12px 0;display:flex}.EKP4qW_form>.EKP4qW_field+.EKP4qW_field{border-top:.5px solid var(--dsw-alias-border-l2)}.EKP4qW_fieldLabel{color:var(--dsw-alias-label-primary);font-size:13px;font-weight:500;line-height:1.5}.EKP4qW_input{box-sizing:border-box;border:.5px solid var(--dsw-alias-border-l4);border-radius:var(--dsw-radius-md);width:100%;height:34px;font:inherit;background:var(--dsw-alias-bg-layer-3);color:var(--dsw-alias-label-primary);padding:0 12px;font-size:13px;line-height:1.5}select.EKP4qW_input{cursor:pointer;max-width:240px}.EKP4qW_input:focus-visible{border-color:var(--dsw-alias-state-business-primary);outline:none}.EKP4qW_input::placeholder{color:var(--dsw-alias-label-dimmed)}.EKP4qW_input:disabled{color:var(--dsw-alias-label-tertiary);cursor:default}.EKP4qW_selectInput{appearance:none;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12' fill='none'%3E%3Cpath d='M3 4.5L6 7.5L9 4.5' stroke='%2381858C' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");background-position:right 12px center;background-repeat:no-repeat;background-size:12px 12px;padding-right:32px}.EKP4qW_textarea{box-sizing:border-box;border:.5px solid var(--dsw-alias-border-l4);border-radius:var(--dsw-radius-md);width:100%;min-height:96px;font:inherit;background:var(--dsw-alias-bg-layer-3);color:var(--dsw-alias-label-primary);resize:vertical;padding:8px 12px;font-size:13px;line-height:1.5}.EKP4qW_textarea:focus-visible{border-color:var(--dsw-alias-state-business-primary);outline:none}.EKP4qW_textarea::placeholder{color:var(--dsw-alias-label-dimmed)}.EKP4qW_textarea:disabled{color:var(--dsw-alias-label-tertiary);cursor:default}.EKP4qW_numberFields{border-top:.5px solid var(--dsw-alias-border-l2);grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;padding:12px 0;display:grid}.EKP4qW_numberFields .EKP4qW_field{padding:0}.EKP4qW_checkboxInput{width:auto;accent-color:var(--dsw-alias-state-business-primary);align-self:flex-start;margin:0}.EKP4qW_hint{color:var(--dsw-alias-label-tertiary);margin:0;font-size:12px;line-height:1.5}.EKP4qW_warnHint{color:var(--dsw-alias-state-warn-label);margin:0;font-size:12px;line-height:1.5}.EKP4qW_footer{align-items:center;gap:8px;padding-top:16px;display:flex}.EKP4qW_failed{min-width:0;color:var(--dsw-alias-label-error);flex:1;margin:0;font-size:12px;line-height:1.5}.EKP4qW_discard,.EKP4qW_save{appearance:none;border-radius:var(--dsw-radius-md);font:inherit;cursor:pointer;border:1px solid #0000;padding:5px 14px;font-size:13px;line-height:1.5}.EKP4qW_discard{border-color:var(--dsw-alias-border-l2);color:var(--dsw-alias-label-secondary);background:0 0}.EKP4qW_discard:hover:not(:disabled){color:var(--dsw-alias-label-primary);border-color:var(--dsw-alias-label-dimmed)}.EKP4qW_save{background:var(--dsw-alias-label-primary);color:var(--dsw-alias-bg-layer-3)}.EKP4qW_discard:disabled,.EKP4qW_save:disabled{opacity:.4;cursor:default}.EKP4qW_discard:focus-visible,.EKP4qW_save:focus-visible{outline:2px solid var(--dsw-alias-brand-primary);outline-offset:1px}`;
var tagId = "dsh-advisor/advisor-card.module.css";
if (typeof document !== "undefined" && document.querySelector("style[data-plugin-css=" + JSON.stringify(tagId) + "]") === null) {
  const tag = document.createElement("style");
  tag.dataset.plugin = "dsh-advisor";
  tag.dataset.pluginCss = tagId;
  tag.textContent = css;
  document.head.appendChild(tag);
}
var advisor_card_module_css_default = { "checkboxInput": "EKP4qW_checkboxInput", "discard": "EKP4qW_discard", "error": "EKP4qW_error", "failed": "EKP4qW_failed", "field": "EKP4qW_field", "fieldLabel": "EKP4qW_fieldLabel", "footer": "EKP4qW_footer", "form": "EKP4qW_form", "hint": "EKP4qW_hint", "input": "EKP4qW_input", "notice": "EKP4qW_notice", "numberFields": "EKP4qW_numberFields", "readOnly": "EKP4qW_readOnly", "save": "EKP4qW_save", "savedNotice": "EKP4qW_savedNotice", "selectInput": "EKP4qW_selectInput", "textarea": "EKP4qW_textarea", "warnHint": "EKP4qW_warnHint" };

// src/client/advisor-card.tsx
var import_jsx_runtime = require("react/jsx-runtime");
function failureCopy(failure, t) {
  switch (failure.kind) {
    case "gate":
      return void 0;
    case "message":
      return failure.message;
  }
}
function AdvisorCard(props) {
  const { controller, useSnapshot, t } = props;
  const state = useSnapshot((snapshot) => snapshot);
  if (state.status === "idle") void controller.load();
  if (state.status === "error") {
    return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
      state.applyState.kind === "saved" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", { className: advisor_card_module_css_default["savedNotice"], role: "status", children: t("saved") }) : null,
      /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", { className: advisor_card_module_css_default["error"], children: `${t("loadFailed")}: ${state.error ?? ""}` }),
      /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { className: advisor_card_module_css_default["footer"], children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", { type: "button", className: advisor_card_module_css_default["discard"], onClick: () => {
        void controller.load();
      }, children: t("retry") }) })
    ] });
  }
  const degraded = state.status === "ready" ? !state.advisorPresent : state.degraded;
  if (degraded) {
    return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
      state.applyState.kind === "saved" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", { className: advisor_card_module_css_default["savedNotice"], role: "status", children: t("saved") }) : null,
      /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", { className: advisor_card_module_css_default["notice"], role: "status", children: t("namespaceUnavailable") }),
      /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { className: advisor_card_module_css_default["footer"], children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", { type: "button", className: advisor_card_module_css_default["discard"], onClick: () => {
        void controller.load();
      }, children: t("retry") }) })
    ] });
  }
  const refreshHold = state.status === "loading" && state.advisorPresent === true;
  if (state.status !== "ready" && !refreshHold) {
    return null;
  }
  const { draft, providers, writable, applyState } = state;
  const providerEmpty = draft.provider === void 0;
  const modelEmpty = draft.model === void 0;
  const gateFailed = providerEmpty || modelEmpty;
  const saving = applyState.kind === "saving";
  const busy = !writable || saving || state.status === "loading";
  const selectedModels = draft.provider === void 0 ? [] : state.modelsByProvider[draft.provider] ?? [];
  const modelsEmpty = draft.provider !== void 0 && Object.hasOwn(state.modelsEmptyReason, draft.provider);
  const providerStale = draft.provider !== void 0 && !providers.some((option) => option.provider === draft.provider);
  const modelStale = !providerStale && draft.model !== void 0 && selectedModels.length > 0 && !selectedModels.some((option) => option.id === draft.model);
  const errorText = applyState.kind === "error" ? failureCopy(applyState.failure, t) : void 0;
  const saveDisabled = !state.dirty || gateFailed || saving || !writable;
  const discardDisabled = !state.dirty || saving;
  return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
    !writable ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", { className: advisor_card_module_css_default["readOnly"], role: "status", children: t("readOnly") }) : null,
    applyState.kind === "saved" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", { className: advisor_card_module_css_default["savedNotice"], role: "status", children: t("saved") }) : null,
    /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { className: advisor_card_module_css_default["form"], children: [
      /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { className: advisor_card_module_css_default["field"], children: [
        /* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", { htmlFor: "advisor-provider", className: advisor_card_module_css_default["fieldLabel"], children: t("provider") }),
        /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(
          "select",
          {
            id: "advisor-provider",
            "aria-label": t("provider"),
            className: `${advisor_card_module_css_default["input"]} ${advisor_card_module_css_default["selectInput"]}`,
            value: draft.provider ?? "",
            disabled: busy,
            onChange: (event) => {
              controller.setProvider(event.target.value);
            },
            children: [
              /* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", { value: "", children: t("providerPlaceholder") }),
              providers.map((option) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", { value: option.provider, children: option.displayName }, option.provider))
            ]
          }
        ),
        providers.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", { className: advisor_card_module_css_default["hint"], children: t("noProviders") }) : null,
        providerEmpty ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", { className: advisor_card_module_css_default["warnHint"], children: t("providerRequired") }) : null,
        providerStale ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", { className: advisor_card_module_css_default["hint"], children: t("staleProvider") }) : null
      ] }),
      /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { className: advisor_card_module_css_default["field"], children: [
        /* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", { htmlFor: "advisor-model", className: advisor_card_module_css_default["fieldLabel"], children: t("model") }),
        /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(
          "select",
          {
            id: "advisor-model",
            "aria-label": t("model"),
            className: `${advisor_card_module_css_default["input"]} ${advisor_card_module_css_default["selectInput"]}`,
            value: draft.model ?? "",
            disabled: busy || draft.provider === void 0 || selectedModels.length === 0,
            onChange: (event) => {
              controller.setModel(event.target.value);
            },
            children: [
              /* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", { value: "", children: t("modelPlaceholder") }),
              selectedModels.map((option) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", { value: option.id, children: option.name }, option.id))
            ]
          }
        ),
        modelsEmpty ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", { className: advisor_card_module_css_default["hint"], children: t("noModels") }) : null,
        modelStale ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", { className: advisor_card_module_css_default["hint"], children: t("staleModel") }) : null,
        !providerEmpty && modelEmpty ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", { className: advisor_card_module_css_default["warnHint"], children: t("modelRequired") }) : null
      ] }),
      /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { className: advisor_card_module_css_default["field"], children: [
        /* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", { htmlFor: "advisor-system-prompt", className: advisor_card_module_css_default["fieldLabel"], children: t("systemPrompt") }),
        /* @__PURE__ */ (0, import_jsx_runtime.jsx)(
          "textarea",
          {
            id: "advisor-system-prompt",
            "aria-label": t("systemPrompt"),
            placeholder: DEFAULT_ADVISOR_SYSTEM_PROMPT,
            className: advisor_card_module_css_default["textarea"],
            value: draft.systemPrompt,
            disabled: busy,
            onChange: (event) => {
              controller.setSystemPrompt(event.target.value);
            }
          }
        ),
        /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", { className: advisor_card_module_css_default["hint"], children: t("systemPromptHint") })
      ] }),
      /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { className: advisor_card_module_css_default["field"], children: [
        /* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", { htmlFor: "advisor-prose-fallback", className: advisor_card_module_css_default["fieldLabel"], children: t("proseFallback") }),
        /* @__PURE__ */ (0, import_jsx_runtime.jsx)(
          "input",
          {
            id: "advisor-prose-fallback",
            "aria-label": t("proseFallback"),
            className: advisor_card_module_css_default["checkboxInput"],
            type: "checkbox",
            checked: draft.proseFallback ?? false,
            disabled: busy,
            onChange: (event) => {
              controller.setProseFallback(event.target.checked);
            }
          }
        ),
        /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", { className: advisor_card_module_css_default["hint"], children: t("proseFallbackHint") })
      ] }),
      /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { className: advisor_card_module_css_default["numberFields"], children: [
        /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { className: advisor_card_module_css_default["field"], children: [
          /* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", { htmlFor: "advisor-immune-turns", className: advisor_card_module_css_default["fieldLabel"], children: t("immuneTurns") }),
          /* @__PURE__ */ (0, import_jsx_runtime.jsx)(
            "input",
            {
              id: "advisor-immune-turns",
              "aria-label": t("immuneTurns"),
              className: advisor_card_module_css_default["input"],
              type: "number",
              min: 0,
              step: 1,
              value: draft.immuneTurns ?? "",
              disabled: busy,
              onChange: (event) => {
                controller.setImmuneTurns(event.target.value === "" ? void 0 : Number(event.target.value));
              }
            }
          )
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { className: advisor_card_module_css_default["field"], children: [
          /* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", { htmlFor: "advisor-max-delta-messages", className: advisor_card_module_css_default["fieldLabel"], children: t("maxDeltaMessages") }),
          /* @__PURE__ */ (0, import_jsx_runtime.jsx)(
            "input",
            {
              id: "advisor-max-delta-messages",
              "aria-label": t("maxDeltaMessages"),
              className: advisor_card_module_css_default["input"],
              type: "number",
              min: 0,
              step: 1,
              value: draft.maxDeltaMessages ?? "",
              disabled: busy,
              onChange: (event) => {
                controller.setMaxDeltaMessages(event.target.value === "" ? void 0 : Number(event.target.value));
              }
            }
          )
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { className: advisor_card_module_css_default["field"], children: [
          /* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", { htmlFor: "advisor-max-tokens", className: advisor_card_module_css_default["fieldLabel"], children: t("maxTokens") }),
          /* @__PURE__ */ (0, import_jsx_runtime.jsx)(
            "input",
            {
              id: "advisor-max-tokens",
              "aria-label": t("maxTokens"),
              className: advisor_card_module_css_default["input"],
              type: "number",
              min: 128,
              max: 16384,
              step: 1,
              value: draft.maxTokens ?? "",
              disabled: busy,
              onChange: (event) => {
                controller.setMaxTokens(event.target.value === "" ? void 0 : Number(event.target.value));
              }
            }
          ),
          /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", { className: advisor_card_module_css_default["hint"], children: t("maxTokensHint") })
        ] })
      ] })
    ] }),
    /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { className: advisor_card_module_css_default["footer"], children: [
      errorText === void 0 ? null : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", { className: advisor_card_module_css_default["failed"], role: "status", children: errorText }),
      /* @__PURE__ */ (0, import_jsx_runtime.jsx)(
        "button",
        {
          type: "button",
          className: advisor_card_module_css_default["discard"],
          disabled: discardDisabled,
          onClick: () => {
            controller.discard();
          },
          children: t("discard")
        }
      ),
      /* @__PURE__ */ (0, import_jsx_runtime.jsx)(
        "button",
        {
          type: "button",
          className: advisor_card_module_css_default["save"],
          disabled: saveDisabled,
          onClick: () => {
            void controller.apply();
          },
          children: t(saving ? "saving" : "save")
        }
      )
    ] })
  ] });
}

// src/client/advisor-session.tsx
var import_react = require("react");
var import_react_dom = require("react-dom");
var import_dsh_client_ui_primitives = require("@deepseek-ai/dsh-client-ui-primitives");

var css2 = "._8GvHZG_trigger{appearance:none;border:1px solid var(--dsw-alias-border-l2);font:inherit;color:var(--dsw-alias-label-secondary);cursor:pointer;white-space:nowrap;background:0 0;border-radius:999px;padding:3px 12px;font-size:13px;line-height:20px}._8GvHZG_trigger:hover{color:var(--dsw-alias-label-primary);border-color:var(--dsw-alias-label-dimmed)}._8GvHZG_trigger[aria-expanded=true]{color:var(--dsw-alias-label-primary);background:var(--dsw-alias-bg-layer-3);border-color:var(--dsw-alias-label-dimmed)}._8GvHZG_trigger:focus-visible{outline:2px solid var(--dsw-alias-brand-primary);outline-offset:1px}._8GvHZG_anchor{display:inline-flex}._8GvHZG_panel{z-index:100;border:1px solid var(--dsw-alias-border-l2);background:var(--dsw-alias-bg-layer-3);border-radius:12px;flex-direction:column;gap:10px;width:300px;padding:12px 14px;display:flex;position:fixed;box-shadow:0 8px 24px #0000002e}._8GvHZG_panelHeading{color:var(--dsw-alias-label-primary);margin:0;font-size:13px;font-weight:600;line-height:20px}._8GvHZG_routeLine{color:var(--dsw-alias-label-primary);overflow-wrap:anywhere;margin:0;font-size:13px;line-height:20px}._8GvHZG_sourceBadge{white-space:nowrap;background:var(--dsw-alias-bg-module-platform);color:var(--dsw-alias-label-secondary);border-radius:999px;margin-left:6px;padding:1px 8px;font-size:11px;font-weight:500;line-height:17px}._8GvHZG_mutedLine{color:var(--dsw-alias-label-tertiary);margin:0;font-size:12px;line-height:18px}._8GvHZG_notice{color:var(--dsw-alias-state-warn-label);margin:0;font-size:12px;line-height:18px}._8GvHZG_error{color:var(--dsw-alias-state-error-primary);margin:0;font-size:12px;line-height:18px}._8GvHZG_controls{border-top:1px solid var(--dsw-alias-border-l2);flex-direction:column;gap:8px;padding-top:8px;display:flex}._8GvHZG_selectRow{gap:8px;display:flex}._8GvHZG_select{appearance:auto;border:1px solid var(--dsw-alias-border-l2);background:var(--dsw-alias-bg-layer-2);min-width:0;color:var(--dsw-alias-label-primary);font:inherit;border-radius:8px;flex:1;padding:4px 6px;font-size:12px;line-height:18px}._8GvHZG_select:disabled{opacity:.4;cursor:default}._8GvHZG_select:focus-visible{outline:2px solid var(--dsw-alias-brand-primary);outline-offset:-1px}._8GvHZG_actions{justify-content:flex-end;align-items:center;gap:8px;display:flex}._8GvHZG_reset,._8GvHZG_pin{appearance:none;font:inherit;cursor:pointer;border:1px solid #0000;border-radius:8px;padding:4px 12px;font-size:12px;line-height:18px}._8GvHZG_reset{border-color:var(--dsw-alias-border-l2);color:var(--dsw-alias-label-secondary);background:0 0}._8GvHZG_reset:hover:not(:disabled){color:var(--dsw-alias-label-primary);border-color:var(--dsw-alias-label-dimmed)}._8GvHZG_pin{background:var(--dsw-alias-label-primary);color:var(--dsw-alias-bg-layer-3)}._8GvHZG_reset:disabled,._8GvHZG_pin:disabled{opacity:.4;cursor:default}._8GvHZG_reset:focus-visible,._8GvHZG_pin:focus-visible{outline:2px solid var(--dsw-alias-brand-primary);outline-offset:1px}";
var tagId2 = "dsh-advisor/advisor-session.module.css";
if (typeof document !== "undefined" && document.querySelector("style[data-plugin-css=" + JSON.stringify(tagId2) + "]") === null) {
  const tag = document.createElement("style");
  tag.dataset.plugin = "dsh-advisor";
  tag.dataset.pluginCss = tagId2;
  tag.textContent = css2;
  document.head.appendChild(tag);
}
var advisor_session_module_css_default = { "actions": "_8GvHZG_actions", "anchor": "_8GvHZG_anchor", "controls": "_8GvHZG_controls", "error": "_8GvHZG_error", "mutedLine": "_8GvHZG_mutedLine", "notice": "_8GvHZG_notice", "panel": "_8GvHZG_panel", "panelHeading": "_8GvHZG_panelHeading", "pin": "_8GvHZG_pin", "reset": "_8GvHZG_reset", "routeLine": "_8GvHZG_routeLine", "select": "_8GvHZG_select", "selectRow": "_8GvHZG_selectRow", "sourceBadge": "_8GvHZG_sourceBadge", "trigger": "_8GvHZG_trigger" };

// src/client/advisor-session.tsx
var import_jsx_runtime2 = require("react/jsx-runtime");
var PANEL_GAP = 6;
var VIEWPORT_MARGIN = 12;
var MEASURE_STYLE = { visibility: "hidden", left: 0, top: 0 };
function AdvisorSessionAction(props) {
  const { controller, directory, useSnapshot, useRefreshSignal, useDirectory, t } = props;
  const state = useSnapshot((s) => s);
  const epoch = useRefreshSignal((s) => s.epoch);
  const directoryState = useDirectory((s) => s);
  const [open, setOpen] = (0, import_react.useState)(false);
  const rootRef = (0, import_react.useRef)(null);
  const triggerRef = (0, import_react.useRef)(null);
  const panelRef = (0, import_react.useRef)(null);
  const panelPosition = (0, import_dsh_client_ui_primitives.useAnchoredPosition)({
    open,
    anchorRef: rootRef,
    panelRef,
    gap: PANEL_GAP,
    margin: VIEWPORT_MARGIN
  });
  (0, import_dsh_client_ui_primitives.useDismissOnOutsidePointer)(rootRef, open, setOpen, panelRef);
  const [provider, setProvider] = (0, import_react.useState)("");
  const [model, setModel] = (0, import_react.useState)("");
  const openAdvisor = () => {
    setOpen(true);
    controller.takeSignal(epoch);
    void controller.refresh();
    if (directoryState.status === "idle") void directory.load();
  };
  if (open && controller.takeSignal(epoch)) void controller.refresh();
  const snapshot = state.snapshot;
  const busy = state.pending;
  const pinned = snapshot?.modelSource === "session";
  let body;
  if (state.unavailable) {
    body = /* @__PURE__ */ (0, import_jsx_runtime2.jsx)("p", { className: advisor_session_module_css_default.notice, role: "status", children: t("sessionUnavailable") });
  } else if (snapshot === null) {
    body = /* @__PURE__ */ (0, import_jsx_runtime2.jsx)("p", { className: advisor_session_module_css_default.mutedLine, role: "status", children: t("sessionLoading") });
  } else {
    const pair = snapshot.effectiveModel !== void 0 ? `${snapshot.effectiveModel.provider}/${snapshot.effectiveModel.model}` : void 0;
    body = /* @__PURE__ */ (0, import_jsx_runtime2.jsxs)(import_jsx_runtime2.Fragment, { children: [
      snapshot.enabled ? null : /* @__PURE__ */ (0, import_jsx_runtime2.jsx)("p", { className: advisor_session_module_css_default.notice, children: t("sessionAdvisorOff") }),
      snapshot.disabledReason !== void 0 ? /* @__PURE__ */ (0, import_jsx_runtime2.jsx)("p", { className: advisor_session_module_css_default.notice, children: t("sessionGateBlocked", { reason: snapshot.disabledReason }) }) : null,
      /* @__PURE__ */ (0, import_jsx_runtime2.jsxs)("p", { className: advisor_session_module_css_default.routeLine, children: [
        pair === void 0 ? t("sessionNoPair") : pair,
        pair !== void 0 && snapshot.modelSource !== void 0 ? /* @__PURE__ */ (0, import_jsx_runtime2.jsx)("span", { className: advisor_session_module_css_default.sourceBadge, children: t(snapshot.modelSource === "session" ? "sessionSourceSession" : "sessionSourceGlobal") }) : null
      ] }),
      /* @__PURE__ */ (0, import_jsx_runtime2.jsx)("p", { className: advisor_session_module_css_default.mutedLine, children: t("sessionLifetime") }),
      state.error !== null ? /* @__PURE__ */ (0, import_jsx_runtime2.jsx)("p", { className: advisor_session_module_css_default.error, role: "status", children: state.error }) : null,
      /* @__PURE__ */ (0, import_jsx_runtime2.jsxs)("div", { className: advisor_session_module_css_default.controls, children: [
        /* @__PURE__ */ (0, import_jsx_runtime2.jsxs)("div", { className: advisor_session_module_css_default.selectRow, children: [
          /* @__PURE__ */ (0, import_jsx_runtime2.jsxs)(
            "select",
            {
              "aria-label": t("provider"),
              className: advisor_session_module_css_default.select,
              value: provider,
              disabled: busy,
              onChange: (event) => {
                const next = event.target.value;
                setProvider(next);
                setModel("");
                if (next !== "") void directory.ensureModels(next);
              },
              children: [
                /* @__PURE__ */ (0, import_jsx_runtime2.jsx)("option", { value: "", children: t("providerPlaceholder") }),
                directoryState.providers.map((option) => /* @__PURE__ */ (0, import_jsx_runtime2.jsx)("option", { value: option.provider, children: option.displayName }, option.provider))
              ]
            }
          ),
          /* @__PURE__ */ (0, import_jsx_runtime2.jsxs)(
            "select",
            {
              "aria-label": t("model"),
              className: advisor_session_module_css_default.select,
              value: model,
              disabled: busy || provider === "" || (directoryState.modelsByProvider[provider]?.length ?? 0) === 0,
              onChange: (event) => {
                setModel(event.target.value);
              },
              children: [
                /* @__PURE__ */ (0, import_jsx_runtime2.jsx)("option", { value: "", children: t("modelPlaceholder") }),
                (directoryState.modelsByProvider[provider] ?? []).map((option) => /* @__PURE__ */ (0, import_jsx_runtime2.jsx)("option", { value: option.id, children: option.name }, option.id))
              ]
            }
          )
        ] }),
        provider !== "" && (directoryState.modelsByProvider[provider]?.length ?? 0) === 0 ? /* @__PURE__ */ (0, import_jsx_runtime2.jsx)("p", { className: advisor_session_module_css_default.mutedLine, children: t("noModels") }) : null,
        /* @__PURE__ */ (0, import_jsx_runtime2.jsxs)("div", { className: advisor_session_module_css_default.actions, children: [
          /* @__PURE__ */ (0, import_jsx_runtime2.jsx)(
            "button",
            {
              type: "button",
              className: advisor_session_module_css_default.reset,
              disabled: busy || !pinned,
              onClick: () => {
                void controller.resetSessionModel();
              },
              children: t("sessionReset")
            }
          ),
          /* @__PURE__ */ (0, import_jsx_runtime2.jsx)(
            "button",
            {
              type: "button",
              className: advisor_session_module_css_default.pin,
              disabled: busy || provider === "" || model === "",
              onClick: () => {
                void controller.setSessionModel(provider, model);
              },
              children: busy ? t("sessionPending") : t("sessionPinAction")
            }
          )
        ] })
      ] })
    ] });
  }
  return /* @__PURE__ */ (0, import_jsx_runtime2.jsxs)(
    "div",
    {
      ref: rootRef,
      className: advisor_session_module_css_default.anchor,
      onKeyDown: (event) => {
        if (open && event.key === "Escape") {
          event.preventDefault();
          setOpen(false);
          triggerRef.current?.focus();
        }
      },
      children: [
        /* @__PURE__ */ (0, import_jsx_runtime2.jsx)(
          "button",
          {
            ref: triggerRef,
            type: "button",
            className: advisor_session_module_css_default.trigger,
            "aria-expanded": open,
            "aria-haspopup": "dialog",
            "aria-label": t(open ? "sessionCollapse" : "sessionExpand"),
            onClick: () => {
              if (open) setOpen(false);
              else openAdvisor();
            },
            children: t("sessionTrigger")
          }
        ),
        open ? (0, import_react_dom.createPortal)(
          /* @__PURE__ */ (0, import_jsx_runtime2.jsxs)(
            "div",
            {
              ref: panelRef,
              className: advisor_session_module_css_default.panel,
              style: panelPosition ?? MEASURE_STYLE,
              role: "dialog",
              "aria-label": t("sessionModelHeading"),
              children: [
                /* @__PURE__ */ (0, import_jsx_runtime2.jsx)("p", { className: advisor_session_module_css_default.panelHeading, children: t("sessionModelHeading") }),
                directoryState.providers.length === 0 && directoryState.status === "ready" && !state.unavailable ? /* @__PURE__ */ (0, import_jsx_runtime2.jsx)("p", { className: advisor_session_module_css_default.mutedLine, children: t("noProviders") }) : null,
                body
              ]
            }
          ),
          document.body
        ) : null
      ]
    }
  );
}

// src/client/advisor-store.ts
var import_dsh_client_store = require("@deepseek-ai/dsh-client-store");
function defaultDraft() {
  return { systemPrompt: "", immuneTurns: 3, maxDeltaMessages: 60 };
}
function stringField(value) {
  return typeof value === "string" && value.trim().length > 0 ? value : void 0;
}
function numberField(value, fallback) {
  return typeof value === "number" && Number.isFinite(value) ? Math.max(0, Math.floor(value)) : fallback;
}
function draftOfConfig(config) {
  return {
    provider: stringField(config?.provider),
    model: stringField(config?.model),
    systemPrompt: typeof config?.systemPrompt === "string" ? config.systemPrompt : "",
    immuneTurns: numberField(config?.immuneTurns, 3),
    maxDeltaMessages: numberField(config?.maxDeltaMessages, 60),
    // The scalar fields show the effective values: the gateway returns the
    // resolved config, so the wire carries both keys whenever the resolver
    // defined them (the schema defaults fill 768/false on the normal path);
    // these fallbacks cover the containment wires whose raw entry omitted
    // the keys (the gateway's S1 fallback mirrors the raw source verbatim).
    maxTokens: numberField(config?.maxTokens, 768),
    proseFallback: typeof config?.proseFallback === "boolean" ? config.proseFallback : false
  };
}
function gateFailure(draft) {
  if (draft.provider === void 0) return "provider";
  if (draft.model === void 0) return "model";
  return void 0;
}
var AdvisorSettingsStore = class {
  /**
   * @param remote - the client Remote assembly face (llm/settings/session
   *   namespaces) for the provider/model directory (the advisor namespace is
   *   NOT on that wire).
   * @param rpc - the connection's generic RPC caller for the host gateway
   *   channel (`/api`), injected from the connection handle.
   */
  constructor(remote, rpc, schema) {
    __publicField(this, "remote", remote);
    __publicField(this, "rpc", rpc);
    __publicField(this, "schema", schema);
    /** The snapshot the card renders from (uSES-safe store). */
    __publicField(this, "store", (0, import_dsh_client_store.createSnapshotStore)({
      status: "idle",
      error: null,
      writable: false,
      providers: [],
      modelsByProvider: {},
      modelsEmptyReason: {},
      namespaces: {},
      advisorPresent: false,
      // qc1 S-2: the degraded latch defaults false — a first mount / healthy
      // card is never degraded, so a healthy first load renders nothing (the
      // latch only flips on a settled degraded ready state).
      degraded: false,
      // KD-U2: dirty derives from the patch diff against the seed
      // (recomputeDirty below — patchFor non-empty), recomputed on
      // load/mutation/discard/apply; the store default is clean.
      dirty: false,
      draft: defaultDraft(),
      applyState: { kind: "idle" }
    }));
    /** Latest load wins; an older response never overwrites a newer one. */
    __publicField(this, "generation", 0);
    /** Host-scoped model catalog; cached only on success (a transient failure stays uncached and is refetched). */
    __publicField(this, "catalog");
    /** In-flight host-scoped catalog fetch; one promise shared across providers. */
    __publicField(this, "catalogPromise");
    /**
     * Bumped by every successful load(): an in-flight catalog fetch started
     * before a bump is stale (the connection/reset invalidation that triggered
     * the reload happened mid-fetch) and caches nothing (qc1 W-1 / qc3 S-1).
     */
    __publicField(this, "catalogGeneration", 0);
    /** In-flight model resolutions (one per provider). */
    __publicField(this, "inflightModels", /* @__PURE__ */ new Set());
    /** The draft is seeded once (first load); refreshes never clobber edits. */
    __publicField(this, "draftSeeded", false);
    /** The resolved advisor config at the last get/apply (patch diff baseline). */
    __publicField(this, "seed", defaultDraft());
  }
  /** Profile-declared models (the provider's `models` directory), when the profile has one. */
  profileModels(profile) {
    const models = this.schema.getPath(profile, ["models"]);
    if (!Array.isArray(models)) return void 0;
    return models.flatMap((entry) => {
      if (typeof entry !== "object" || entry === null) return [];
      const model = entry;
      if (typeof model.id !== "string" || model.id.length === 0) return [];
      return [{
        id: model.id,
        name: typeof model.name === "string" ? model.name : model.id,
        ...typeof model.description === "string" ? { description: model.description } : {}
      }];
    });
  }
  /**
   * Refresh the whole page snapshot: the provider directory and the settings
   * namespaces in parallel, then the advisor config over the gateway channel,
   * then the provider join and the draft seed. A provider-directory failure
   * keeps the last good rows and surfaces the error; an `advisor.get` failure
   * is NOT a page error (KD-G5 — the card shows the config-channel notice,
   * the provider directory stays usable). The draft is seeded only on the
   * first load — pushed refreshes never discard in-progress edits (mirror the
   * ProviderEditor draft lifetime).
   * @returns nothing; the snapshot carries the outcome.
   */
  async load() {
    const generation = ++this.generation;
    this.store.update((s) => {
      s.status = "loading";
      s.error = null;
    });
    let providers;
    let writable;
    let views;
    try {
      const [providersResult, settingsResult] = await Promise.all([
        this.remote.llm.listConfigurableProviders(),
        this.remote.settings.describe()
      ]);
      if (!providersResult.ok) throw new Error(providersResult.error.message);
      if (!settingsResult.ok) throw new Error(settingsResult.error.message);
      providers = providersResult.value;
      writable = settingsResult.value.writable;
      views = settingsResult.value.namespaces;
    } catch (error) {
      if (generation !== this.generation) return;
      this.store.update((s) => {
        s.status = "error";
        s.error = error instanceof Error ? error.message : String(error);
      });
      return;
    }
    if (generation !== this.generation) return;
    let config;
    try {
      const getResult = await this.rpc.call("/api", "advisor/get", { args: {} });
      if (getResult.ok) {
        config = getResult.value.config;
      }
    } catch {
    }
    if (generation !== this.generation) return;
    const namespaces = Object.fromEntries(
      views.map((view) => [view.ns, view])
    );
    const options = [];
    for (const entry of providers) {
      const namespace = namespaces[entry.settingsNs];
      const configured = namespace !== void 0 && (entry.settingsPath.length === 0 || this.schema.getPath(namespace.value, entry.settingsPath) !== void 0);
      if (!configured) continue;
      options.push({
        provider: entry.provider,
        displayName: entry.displayName,
        settingsNs: entry.settingsNs,
        settingsPath: entry.settingsPath,
        configured
      });
    }
    this.seed = draftOfConfig(config);
    if (!this.draftSeeded && config !== void 0) {
      this.store.update((s) => {
        s.draft = this.seed;
      });
      this.draftSeeded = true;
    }
    this.catalogGeneration += 1;
    this.catalog = void 0;
    this.catalogPromise = void 0;
    this.inflightModels.clear();
    this.store.update((s) => {
      s.status = "ready";
      s.error = null;
      s.writable = writable;
      s.providers = options;
      s.namespaces = namespaces;
      s.advisorPresent = config !== void 0;
      s.degraded = config === void 0;
      s.modelsByProvider = {};
      s.modelsEmptyReason = {};
      if (config !== void 0) s.dirty = this.recomputeDirty(s.draft);
    });
    const selected = this.seed.provider;
    if (selected !== void 0 && options.some((option) => option.provider === selected)) {
      void this.ensureModels(selected);
    }
  }
  /**
   * Resolve the model options for one provider (KD-S2): profile-declared
   * `models` win; otherwise the `session.modelCatalog` group for that
   * provider; neither → empty options + a reason. The host-scoped catalog is
   * fetched at most once (concurrent first resolutions share one in-flight
   * fetch) and cached only on success. No-op for unconfigured providers.
   * @param provider - provider route id.
   * @returns nothing; the snapshot carries the outcome.
   */
  async ensureModels(provider) {
    if (this.inflightModels.has(provider)) return;
    const state = this.store.getSnapshot();
    if (Object.hasOwn(state.modelsByProvider, provider) || Object.hasOwn(state.modelsEmptyReason, provider)) return;
    const option = state.providers.find((candidate) => candidate.provider === provider);
    if (option === void 0) return;
    const namespace = state.namespaces[option.settingsNs];
    const profile = namespace !== void 0 ? this.schema.getPath(namespace.value, option.settingsPath) : void 0;
    const declared = this.profileModels(profile);
    if (declared !== void 0) {
      this.store.update((s) => {
        if (declared.length > 0) {
          s.modelsByProvider = { ...s.modelsByProvider, [provider]: declared };
        } else {
          s.modelsEmptyReason = { ...s.modelsEmptyReason, [provider]: "profile-empty" };
        }
      });
      return;
    }
    this.inflightModels.add(provider);
    try {
      let group;
      for (; ; ) {
        if (this.catalog === void 0) {
          if (this.catalogPromise === void 0) {
            const fetch = this.fetchCatalog();
            const tracked = fetch.finally(() => {
              if (this.catalogPromise === tracked) this.catalogPromise = void 0;
            });
            this.catalogPromise = tracked;
          }
          const generation = this.catalogGeneration;
          await this.catalogPromise;
          if (generation !== this.catalogGeneration) continue;
        }
        group = this.catalog?.find((candidate) => candidate.id === provider);
        break;
      }
      const options = group?.models ?? [];
      this.store.update((s) => {
        if (options.length > 0) {
          s.modelsByProvider = { ...s.modelsByProvider, [provider]: options };
        } else {
          const reason = group === void 0 ? "unavailable" : "catalog-empty";
          s.modelsEmptyReason = { ...s.modelsEmptyReason, [provider]: reason };
        }
      });
    } finally {
      this.inflightModels.delete(provider);
    }
  }
  /**
   * Fetch the host-scoped model catalog. A failure (wire rejection or throw)
   * leaves the cache empty so the next resolution refetches — a transient
   * failure is never sticky for the store lifetime. A fetch started before a
   * load() bumped `catalogGeneration` is stale (the invalidation that caused
   * the reload happened mid-fetch) and caches nothing.
   */
  async fetchCatalog() {
    const generation = this.catalogGeneration;
    try {
      const response = await this.remote.session.modelCatalog();
      if (generation !== this.catalogGeneration) return;
      this.catalog = response.ok ? response.value.groups : void 0;
    } catch {
      if (generation === this.catalogGeneration) this.catalog = void 0;
    }
  }
  /** Set or clear the provider ('' clears); switches invalidate the chosen model. */
  setProvider(provider) {
    const trimmed = provider.trim();
    this.store.update((s) => {
      const draft = s.draft;
      const withoutProvider = trimmed.length === 0 ? this.schema.deletePath(draft, ["provider"]) : this.schema.setPath(draft, ["provider"], trimmed);
      s.draft = this.schema.deletePath(withoutProvider, ["model"]);
      s.applyState = { kind: "idle" };
      s.dirty = this.recomputeDirty(s.draft);
    });
    if (trimmed.length > 0) void this.ensureModels(trimmed);
  }
  /** Set or clear the model ('' clears). */
  setModel(model) {
    const trimmed = model.trim();
    if (trimmed.length === 0) this.clearField("model");
    else this.setField("model", trimmed);
  }
  /** Set the system prompt override. */
  setSystemPrompt(prompt) {
    this.setField("systemPrompt", prompt);
  }
  /** Set the immune-turns cooldown (int ≥ 0; non-numeric input keeps the current value; undefined clears → omitted from patch). */
  setImmuneTurns(value) {
    if (value === void 0) {
      this.clearField("immuneTurns");
      return;
    }
    this.setField("immuneTurns", this.clampInt(value, this.store.getSnapshot().draft.immuneTurns ?? 0));
  }
  /** Set the delta-message window (int ≥ 0; non-numeric input keeps the current value; undefined clears → omitted from patch). */
  setMaxDeltaMessages(value) {
    if (value === void 0) {
      this.clearField("maxDeltaMessages");
      return;
    }
    this.setField("maxDeltaMessages", this.clampInt(value, this.store.getSnapshot().draft.maxDeltaMessages ?? 0));
  }
  /**
   * Set the advisor token budget (KD-I1, issue #102: int clamped into
   * 128..16384 — the schema bounds; non-numeric input keeps the current
   * value; undefined clears → omitted from patch).
   */
  setMaxTokens(value) {
    if (value === void 0) {
      this.clearField("maxTokens");
      return;
    }
    this.setField("maxTokens", this.clampInt(value, this.store.getSnapshot().draft.maxTokens ?? 768, 128, 16384));
  }
  /** Set the opt-in prose fallback (KD-I2, issue #102). */
  setProseFallback(value) {
    this.setField("proseFallback", value);
  }
  /**
   * Refuse in a read-only environment (store-side defense-in-depth for the
   * W-1 invariant — a write must never be issued when the UI declares the
   * settings service read-only), then validate the draft (KD-S4 gate) and
   * write the changed keys as a config patch through the gateway channel
   * (`/api/advisor/set`). Any failure (business rejection or transport)
   * surfaces the message failure and keeps the form for retry — the gateway
   * merge has no revision guard, so the old settings-conflict branch is
   * replaced by plain error handling (KD-G3). Nothing to write → the apply
   * reports saved without a call.
   * @returns nothing; the apply state carries the outcome.
   */
  async apply() {
    const state = this.store.getSnapshot();
    if (!state.writable) {
      this.store.update((s) => {
        s.applyState = {
          kind: "error",
          failure: { kind: "message", message: "advisor: settings service is read-only \u2014 configuration cannot be written" }
        };
      });
      return;
    }
    const gate = gateFailure(state.draft);
    if (gate !== void 0) {
      this.store.update((s) => {
        s.applyState = { kind: "error", failure: { kind: "gate", reason: gate } };
      });
      return;
    }
    const patch = this.patchFor(state.draft);
    if (Object.keys(patch).length === 0) {
      this.store.update((s) => {
        s.applyState = { kind: "saved" };
        s.dirty = this.recomputeDirty(s.draft);
      });
      return;
    }
    this.store.update((s) => {
      s.applyState = { kind: "saving" };
    });
    try {
      const result = await this.rpc.call("/api", "advisor/set", { args: { patch } });
      if (!result.ok) {
        this.store.update((s) => {
          s.applyState = { kind: "error", failure: { kind: "message", message: result.error.message } };
        });
        return;
      }
      this.seed = draftOfConfig(result.value.config);
      this.store.update((s) => {
        s.applyState = { kind: "saved" };
        s.dirty = this.recomputeDirty(s.draft);
      });
      await this.load();
    } catch (error) {
      this.store.update((s) => {
        s.applyState = {
          kind: "error",
          failure: { kind: "message", message: error instanceof Error ? error.message : String(error) }
        };
      });
    }
  }
  /**
   * Drop the current draft edits and rewind the form to the last-known host
   * config (the seed from the last get/apply). The card chrome mirrors the
   * upstream plugin cards' Save/Discard pair (KD-4): unlike the upstream
   * staged CardForm, this store's edits mutate the draft in place, so discard
   * rewinds the draft instead of dropping a staging layer. Pure client-side
   * revert — no gateway write (the host stays the single fact source; a
   * follow-up apply diffs against the restored seed and sends nothing).
   *
   * Invariant (qc3 N-2): a mid-apply discard is UNGUARDED at the store level
   * BY DESIGN — the UI disables Discard while a save is in flight
   * (`disabled={busy}` on the card, `busy = !writable || saving`), so the
   * interleaving cannot occur from the UI and no behavior guard is added
   * here. A programmatic mid-apply discard would only rewind the draft before
   * the in-flight apply adopts the returned config as the new seed — the
   * host write is unaffected.
   */
  discard() {
    this.store.update((s) => {
      s.draft = this.seed;
      s.applyState = { kind: "idle" };
      s.dirty = this.recomputeDirty(s.draft);
    });
  }
  /**
   * The minimal config patch making the effective config match the draft —
   * only keys whose value differs from the last-read seed are sent, so a
   * stale read never clobbers concurrent changes to untouched keys and base
   * (plugin-row) values stay in place. A cleared provider/model the seed pins
   * becomes an explicit `''` override (the gateway merge cannot express an
   * unset, and the resolver treats '' as absent); a cleared number field is
   * omitted (the stored value stays unchanged).
   */
  patchFor(draft) {
    const patch = {};
    const always = ["systemPrompt", "immuneTurns", "maxDeltaMessages", "maxTokens", "proseFallback"];
    for (const key of always) {
      const next = draft[key];
      if (next === void 0) continue;
      if (JSON.stringify(this.seed[key]) !== JSON.stringify(next)) {
        patch[key] = next;
      }
    }
    for (const key of ["provider", "model"]) {
      const next = draft[key];
      if (next !== void 0) {
        if (JSON.stringify(this.seed[key]) !== JSON.stringify(next)) {
          patch[key] = next;
        }
      } else if (this.seed[key] !== void 0) {
        patch[key] = "";
      }
    }
    return patch;
  }
  /**
   * The dirty derivation (KD-U2, plan dsh-advisor-plugin-config-card-ux task
   * 2): the draft holds edits a save would write iff the minimal patch
   * against the current seed is non-empty. Takes the DRAFT being mutated and
   * reads `this.seed` — it must be called INSIDE the same `store.update`
   * callback that mutates the draft/seed, never via a snapshot read + second
   * write (the frozen-snapshot write would be dropped by the snapshot store).
   */
  recomputeDirty(draft) {
    return Object.keys(this.patchFor(draft)).length > 0;
  }
  /** Edit one always-present draft field via the settings schema path writer. */
  setField(key, value) {
    this.store.update((s) => {
      s.draft = this.schema.setPath(s.draft, [key], value);
      s.applyState = { kind: "idle" };
      s.dirty = this.recomputeDirty(s.draft);
    });
  }
  /** Remove one optional draft field via the settings schema path writer. */
  clearField(key) {
    this.store.update((s) => {
      s.draft = this.schema.deletePath(s.draft, [key]);
      s.applyState = { kind: "idle" };
      s.dirty = this.recomputeDirty(s.draft);
    });
  }
  /** A bounded integer clamp (int ≥ min, ≤ max); a non-finite input keeps the fallback. */
  clampInt(value, fallback, min = 0, max = Number.MAX_SAFE_INTEGER) {
    return Number.isFinite(value) ? Math.min(max, Math.max(min, Math.floor(value))) : fallback;
  }
};
function refreshIfLoaded(controller) {
  if (controller.store.getSnapshot().status === "idle") return;
  void controller.load();
}
var AdvisorSessionModelController = class {
  constructor(sessionId, rpc) {
    __publicField(this, "rpc", rpc);
    __publicField(this, "sessionId");
    /** The snapshot the menu renders from (uSES-safe store). */
    __publicField(this, "store", (0, import_dsh_client_store.createSnapshotStore)({
      phase: "idle",
      snapshot: null,
      error: null,
      unavailable: false,
      pending: false
    }));
    /** Fence token: a newer op makes every older settle stale. */
    __publicField(this, "requestSeq", 0);
    /** Last consumed refresh-signal epoch (reconnect / focus bumps). */
    __publicField(this, "lastSignal");
    this.sessionId = sessionId;
  }
  /**
   * Record the refresh-signal epoch and report whether it is NEW. The open
   * handler always refetches and merely marks the signal current; the render
   * watcher calls this while open and refetches only on a true return (a
   * reconnect/focus bump). Idempotent per epoch, so a re-render never
   * double-fetches.
   */
  takeSignal(epoch) {
    if (this.lastSignal === epoch) return false;
    this.lastSignal = epoch;
    return true;
  }
  /**
   * Fetch the authoritative snapshot (`/api/advisor/getSession`). Called on
   * menu open and on every refresh signal while open. A stale settle (a newer
   * op superseded this fetch) touches nothing. An `advisor/unavailable` /
   * `advisor/session-unknown` tag or a transport failure latches
   * `unavailable` (writes stay off until a later successful refresh); other
   * tagged outcomes leave the surface usable with the error shown.
   */
  async refresh() {
    const seq = ++this.requestSeq;
    this.store.update((s) => {
      s.phase = "loading";
      s.pending = false;
      s.error = null;
    });
    let payload;
    let transport;
    try {
      const result = await this.rpc.call("/api", "advisor/getSession", { args: { sessionId: this.sessionId } });
      if (seq !== this.requestSeq) return;
      if (result.ok) payload = result.value;
      else transport = result.error.message;
    } catch (error) {
      if (seq !== this.requestSeq) return;
      transport = error instanceof Error ? error.message : String(error);
    }
    this.applyOutcome(payload, transport, seq);
  }
  /**
   * Pin the atomic `{provider, model}` pair for THIS session
   * (`/api/advisor/setSessionModel`, selection = the pair). Refuses outright
   * while `unavailable` (store-side defense-in-depth — an unavailable menu
   * must never issue a write, and must never fall back to the global
   * `advisor/set` channel). The host validates the pair through the same
   * rules as the `/advisor model set` command face.
   */
  async setSessionModel(provider, model) {
    await this.write({ provider, model });
  }
  /**
   * Drop the session pin and re-inherit the CURRENT global defaults
   * (`selection: null`). Never touches the enable override; reset to a
   * missing global pair still succeeds — the returned snapshot reports the
   * gate-blocked/no-call state, which the menu renders truthfully.
   */
  async resetSessionModel() {
    await this.write(null);
  }
  /** Shared write path (both arms ride the same endpoint + fence + outcome mapping). */
  async write(selection) {
    if (this.store.getSnapshot().unavailable) {
      this.store.update((s) => {
        s.error = "advisor: the session control surface is unavailable \u2014 writes are not offered";
      });
      return;
    }
    const seq = ++this.requestSeq;
    this.store.update((s) => {
      s.pending = true;
      s.error = null;
    });
    let payload;
    let transport;
    try {
      const result = await this.rpc.call("/api", "advisor/setSessionModel", {
        args: { sessionId: this.sessionId, selection }
      });
      if (seq !== this.requestSeq) return;
      if (result.ok) payload = result.value;
      else transport = result.error.message;
    } catch (error) {
      if (seq !== this.requestSeq) return;
      transport = error instanceof Error ? error.message : String(error);
    }
    this.applyOutcome(payload, transport, seq);
  }
  /**
   * Commit one settled outcome. Guards (seq checked by the callers before
   * reaching here): tagged `advisor/unavailable` / `advisor/session-unknown`
   * and transport failures latch `unavailable` (no writes offered, last good
   * snapshot kept for context); other tagged outcomes keep the surface usable
   * and surface the message (the host left the previous selection untouched);
   * a snapshot commits as the new authoritative state.
   */
  applyOutcome(payload, transport, seq) {
    if (seq !== this.requestSeq) return;
    const tagged = payload?.error;
    if (transport !== void 0 || tagged?.tag === "advisor/unavailable" || tagged?.tag === "advisor/session-unknown") {
      this.store.update((s) => {
        s.phase = "ready";
        s.unavailable = true;
        s.pending = false;
        s.error = transport ?? tagged?.message ?? "advisor: the session control surface is unavailable";
      });
      return;
    }
    if (tagged !== void 0) {
      this.store.update((s) => {
        s.phase = "ready";
        s.pending = false;
        s.error = tagged.message;
      });
      return;
    }
    const snapshot = payload?.snapshot;
    if (snapshot === void 0) {
      this.store.update((s) => {
        s.phase = "ready";
        s.unavailable = true;
        s.pending = false;
        s.error = "advisor: the session endpoint returned no snapshot";
      });
      return;
    }
    this.store.update((s) => {
      s.phase = "ready";
      s.snapshot = snapshot;
      s.unavailable = false;
      s.pending = false;
      s.error = null;
    });
  }
};

// src/client/index.ts
var import_dsh_client_store2 = require("@deepseek-ai/dsh-client-store");

// src/client/locales.ts
var en = {
  loadFailed: "Loading advisor settings failed",
  retry: "Retry",
  provider: "Provider",
  providerPlaceholder: "Select a provider",
  providerRequired: "Provider is required.",
  model: "Model",
  modelPlaceholder: "Select a model",
  modelRequired: "Model is required.",
  noProviders: "No configured providers. Configure one on the Models page first.",
  noModels: "This provider has no available models. Configure models for it on the Models page.",
  staleProvider: "The stored provider is no longer configured. Reselect one or keep the stored value.",
  staleModel: "The stored model is no longer available for this provider. Reselect one or keep the stored value.",
  systemPrompt: "System prompt",
  systemPromptHint: "Leave empty to use the default system prompt",
  immuneTurns: "Immune turns",
  maxDeltaMessages: "Max delta messages",
  maxTokens: "Max tokens",
  maxTokensHint: "Token budget for one advisor review (128\u201316384, default 768). Raise it if a thinking model returns empty replies.",
  proseFallback: "Prose fallback",
  proseFallbackHint: "When no JSON frame is found, deliver the prose reply as a low-severity note \u2014 for models that answer in prose instead of JSON.",
  save: "Save",
  saving: "Saving\u2026",
  discard: "Discard",
  saved: "Advisor settings saved. New sessions pick them up immediately.",
  readOnly: "Settings are read-only in this environment.",
  namespaceUnavailable: "The advisor configuration channel is not available yet \u2014 the settings gateway is not ready on this host. Configure the advisor via the plugin config row \u2014 `- id: advisor` whose `config:` map sets `provider`/`model` (e.g. `config: { provider: \u2026, model: \u2026 }`) in `$DSH_HOME/profiles/<name>/cordis.patch.yml`. The advisor plugin runs fully from its plugin config row; the web settings form becomes available again on the next load once the gateway is reachable. Note: `/advisor` only toggles the advisor per session; it cannot supply provider/model.",
  // Session header action (B2): the control lives on the session header and
  // drives the live-session reviewer route only.
  sessionTrigger: "Advisor",
  sessionExpand: "Open the advisor controls for this session",
  sessionCollapse: "Close the advisor controls for this session",
  sessionLoading: "Loading\u2026",
  sessionModelHeading: "Reviewer model for this session",
  sessionSourceSession: "session override",
  sessionSourceGlobal: "global default",
  sessionNoPair: "No reviewer model \u2014 the global default has no provider/model.",
  sessionLifetime: "Lives for this session only \u2014 never persisted; cleared on dispose or restart. A new or forked session inherits the global defaults.",
  sessionAdvisorOff: "The advisor is off for this session.",
  sessionGateBlocked: "No model call can start: {reason}",
  sessionPinAction: "Pin this model",
  sessionPending: "Applying\u2026",
  sessionReset: "Use global default",
  sessionUnavailable: "The advisor session control surface is not available on this host. Use /advisor model in the session, or configure the global defaults on the Plugins page."
};
var zh = {
  loadFailed: "\u52A0\u8F7D\u987E\u95EE\u8BBE\u7F6E\u5931\u8D25",
  retry: "\u91CD\u8BD5",
  provider: "\u63D0\u4F9B\u5546",
  providerPlaceholder: "\u9009\u62E9\u63D0\u4F9B\u5546",
  providerRequired: "\u63D0\u4F9B\u5546\u4E0D\u80FD\u4E3A\u7A7A\u3002",
  model: "\u6A21\u578B",
  modelPlaceholder: "\u9009\u62E9\u6A21\u578B",
  modelRequired: "\u6A21\u578B\u4E0D\u80FD\u4E3A\u7A7A\u3002",
  noProviders: "\u6CA1\u6709\u5DF2\u914D\u7F6E\u7684\u63D0\u4F9B\u5546\u3002\u8BF7\u5148\u5728 Models \u9875\u9762\u914D\u7F6E\u3002",
  noModels: "\u8BE5\u63D0\u4F9B\u5546\u6CA1\u6709\u53EF\u7528\u6A21\u578B\u3002\u8BF7\u5230 Models \u9875\u9762\u4E3A\u5176\u914D\u7F6E\u6A21\u578B\u3002",
  staleProvider: "\u5B58\u50A8\u7684\u63D0\u4F9B\u5546\u5DF2\u4E0D\u5728\u914D\u7F6E\u4E2D\u3002\u8BF7\u91CD\u65B0\u9009\u62E9\uFF0C\u6216\u4FDD\u7559\u5B58\u50A8\u7684\u503C\u3002",
  staleModel: "\u5B58\u50A8\u7684\u6A21\u578B\u5728\u8BE5\u63D0\u4F9B\u5546\u4E0B\u5DF2\u4E0D\u53EF\u7528\u3002\u8BF7\u91CD\u65B0\u9009\u62E9\uFF0C\u6216\u4FDD\u7559\u5B58\u50A8\u7684\u503C\u3002",
  systemPrompt: "\u7CFB\u7EDF\u63D0\u793A\u8BCD",
  systemPromptHint: "\u7559\u7A7A\u5219\u4F7F\u7528\u9ED8\u8BA4\u7CFB\u7EDF\u63D0\u793A\u8BCD",
  immuneTurns: "\u514D\u75AB\u8F6E\u6B21",
  maxDeltaMessages: "\u6700\u5927\u589E\u91CF\u6D88\u606F\u6570",
  maxTokens: "\u6700\u5927 token \u6570",
  maxTokensHint: "\u5355\u6B21\u8BC4\u5BA1\u7684 token \u9884\u7B97\uFF08128\u201316384\uFF0C\u9ED8\u8BA4 768\uFF09\u3002\u601D\u8003\u578B\u6A21\u578B\u8FD4\u56DE\u7A7A\u56DE\u590D\u65F6\u8BF7\u8C03\u9AD8\u3002",
  proseFallback: "\u6563\u6587\u56DE\u9000",
  proseFallbackHint: "\u672A\u627E\u5230 JSON \u5E27\u65F6\uFF0C\u5C06\u6563\u6587\u56DE\u590D\u4F5C\u4E3A\u4F4E\u4E25\u91CD\u7EA7\u5EFA\u8BAE\u6295\u9012\u2014\u2014\u9002\u7528\u4E8E\u4EE5\u6563\u6587\u800C\u975E JSON \u4F5C\u7B54\u7684\u6A21\u578B\u3002",
  save: "\u4FDD\u5B58",
  saving: "\u4FDD\u5B58\u4E2D\u2026",
  discard: "\u653E\u5F03\u4FEE\u6539",
  saved: "\u987E\u95EE\u8BBE\u7F6E\u5DF2\u4FDD\u5B58\u3002\u65B0\u4F1A\u8BDD\u7ACB\u5373\u751F\u6548\u3002",
  readOnly: "\u5F53\u524D\u73AF\u5883\u4E2D\u7684\u8BBE\u7F6E\u4E3A\u53EA\u8BFB\u3002",
  namespaceUnavailable: "\u987E\u95EE\u914D\u7F6E\u901A\u9053\u6682\u4E0D\u53EF\u7528\u2014\u2014\u672C\u5BBF\u4E3B\u4E0A\u7684\u8BBE\u7F6E\u7F51\u5173\u5C1A\u672A\u5C31\u7EEA\u3002\u8BF7\u901A\u8FC7\u63D2\u4EF6\u914D\u7F6E\u884C\u914D\u7F6E\u987E\u95EE\u2014\u2014\u5728 `$DSH_HOME/profiles/<name>/cordis.patch.yml` \u4E2D\u5199 `- id: advisor`\uFF0C\u5176 `config:` \u6620\u5C04\u4E2D\u8BBE\u7F6E `provider`/`model`\uFF08\u4F8B\u5982 `config: { provider: \u2026, model: \u2026 }`\uFF09\u3002\u987E\u95EE\u63D2\u4EF6\u5B8C\u5168\u901A\u8FC7\u63D2\u4EF6\u914D\u7F6E\u884C\u8FD0\u884C\uFF1B\u7F51\u5173\u53EF\u7528\u540E\uFF0Cweb \u8BBE\u7F6E\u8868\u5355\u5C06\u5728\u4E0B\u6B21\u52A0\u8F7D\u65F6\u91CD\u65B0\u663E\u793A\u3002\u6CE8\u610F\uFF1A`/advisor` \u4EC5\u5207\u6362\u5F53\u524D\u4F1A\u8BDD\u7684\u987E\u95EE\u5F00\u5173\uFF0C\u65E0\u6CD5\u63D0\u4F9B provider/model\u3002",
  sessionTrigger: "\u987E\u95EE",
  sessionExpand: "\u6253\u5F00\u672C\u4F1A\u8BDD\u7684\u987E\u95EE\u63A7\u5236",
  sessionCollapse: "\u5173\u95ED\u672C\u4F1A\u8BDD\u7684\u987E\u95EE\u63A7\u5236",
  sessionLoading: "\u52A0\u8F7D\u4E2D\u2026",
  sessionModelHeading: "\u672C\u4F1A\u8BDD\u7684\u5BA1\u9605\u6A21\u578B",
  sessionSourceSession: "\u4F1A\u8BDD\u8986\u76D6",
  sessionSourceGlobal: "\u5168\u5C40\u9ED8\u8BA4",
  sessionNoPair: "\u6682\u65E0\u5BA1\u9605\u6A21\u578B\u2014\u2014\u5168\u5C40\u9ED8\u8BA4\u672A\u914D\u7F6E provider/model\u3002",
  sessionLifetime: "\u4EC5\u5728\u672C\u4F1A\u8BDD\u5185\u6709\u6548\u2014\u2014\u4ECE\u4E0D\u6301\u4E45\u5316\uFF1B\u4F1A\u8BDD\u9500\u6BC1\u6216\u91CD\u542F\u540E\u6E05\u9664\u3002\u65B0\u5EFA\u6216\u5206\u53C9\u7684\u4F1A\u8BDD\u7EE7\u627F\u5168\u5C40\u9ED8\u8BA4\u503C\u3002",
  sessionAdvisorOff: "\u672C\u4F1A\u8BDD\u7684\u987E\u95EE\u5DF2\u5173\u95ED\u3002",
  sessionGateBlocked: "\u65E0\u6CD5\u53D1\u8D77\u6A21\u578B\u8C03\u7528\uFF1A{reason}",
  sessionPinAction: "\u56FA\u5B9A\u6B64\u6A21\u578B",
  sessionPending: "\u5E94\u7528\u4E2D\u2026",
  sessionReset: "\u4F7F\u7528\u5168\u5C40\u9ED8\u8BA4",
  sessionUnavailable: "\u672C\u5BBF\u4E3B\u4E0A\u7684\u987E\u95EE\u4F1A\u8BDD\u63A7\u5236\u9762\u4E0D\u53EF\u7528\u3002\u8BF7\u5728\u4F1A\u8BDD\u4E2D\u4F7F\u7528 /advisor model\uFF0C\u6216\u5728 Plugins \u9875\u914D\u7F6E\u5168\u5C40\u9ED8\u8BA4\u503C\u3002"
};

// src/client/index.ts
var NS = "settings.advisor";
var BUNDLE_NAME = "dsh-advisor";
var inject = ["slots", "locale", "connection", "settingsSchema", "remote", "remote.llm", "remote.settings", "remote.session"];
function apply(ctx) {
  ctx.effect(() => ctx.locale.register(NS, { zh, en }), "advisor: copy dictionaries");
  const connection = ctx.get("connection");
  const controller = new AdvisorSettingsStore(ctx.remote, connection.rpc, ctx.settingsSchema);
  const refreshSignal = (0, import_dsh_client_store2.createSnapshotStore)({ epoch: 0 });
  ctx.effect(() => {
    let pending = false;
    const refresh = () => {
      if (pending) return;
      pending = true;
      queueMicrotask(() => {
        pending = false;
        refreshIfLoaded(controller);
        refreshSignal.update((signal) => {
          signal.epoch += 1;
        });
      });
    };
    const disposers = [ctx.on("connection/reset", refresh)];
    disposers.push(ctx.remote.$on("settings/document-updated", refresh));
    disposers.push(ctx.remote.$on("llm/adapters-updated", refresh));
    const onFocus = () => {
      refresh();
    };
    window.addEventListener("focus", onFocus);
    return () => {
      window.removeEventListener("focus", onFocus);
      for (const dispose of disposers) dispose();
    };
  }, "advisor: pushed invalidations");
  ctx.slots.inject("plugins.bundle.config", function* () {
    yield ctx.slots.register({
      name: "plugins.bundle.config",
      // Keyed slot: the key is the bundle package name the page dispatches
      // (`entryKey = pkg.name` in ui-plugin-manager's PackageDetail). Keyed
      // entries declare no `id`/`order` — there is one entry per bundle page.
      key: BUNDLE_NAME,
      locale: NS,
      // Hooks compartment: the renderer binds `hooks.snapshot` to the
      // component's `useSnapshot` selector hook (the old web-react
      // bindSnapshotSelector call is gone with that package).
      inject: () => ({ controller, hooks: { snapshot: controller.store } })
    }, AdvisorCard);
  });
  ctx.slots.inject("conversation.session.header.actions", function* () {
    yield ctx.slots.register({
      name: "conversation.session.header.actions",
      // List slot: one cell per `id` — this bundle contributes exactly one
      // action; default order keeps registration sequencing.
      id: BUNDLE_NAME,
      locale: NS,
      inject: (sessionId) => {
        const sessionController = new AdvisorSessionModelController(sessionId, connection.rpc);
        return {
          sessionId,
          controller: sessionController,
          // READ-only directory reuse: provider/model options come from the
          // global card's store; the session surface never writes through it.
          directory: controller,
          hooks: {
            snapshot: sessionController.store,
            refreshSignal,
            directory: controller.store
          }
        };
      }
    }, AdvisorSessionAction);
  });
}
return module.exports; } });
