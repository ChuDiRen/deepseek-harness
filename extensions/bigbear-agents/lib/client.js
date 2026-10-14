window.__ModuleLoader__.load({
	id: "dsh-bigbear-agents",
	factory: (require) => {
		var module = { exports: {} };
		var exports = module.exports;
		Object.defineProperty(exports, Symbol.toStringTag, { value: "Module" });
		let _deepseek_ai_dsh_client_ui_primitives = require("@deepseek-ai/dsh-client-ui-primitives");
		let react_jsx_runtime = require("react/jsx-runtime");
		//#region src/client/locales.ts
		/** English copy. */
		const en = {
			title: "Bigbear toolkit",
			description: "Gateway values the toolkit CLIs read from the environment, ahead of any project .env file.",
			toolkitDir: "Toolkit directory",
			toolkitDirHint: "Leave blank to use the repository copy at extensions/bigbear-toolkit.",
			gatewayApiKey: "Gateway API key",
			gatewayApiKeyHint: "Shared key for the runner, web, Android, and vision CLIs. Stored in the profile patch.",
			gatewayBaseUrl: "Gateway base URL",
			gatewayBaseUrlHint: "OpenAI-compatible endpoint, for example http://192.168.1.6:13000/v1.",
			runnerModel: "Runner model",
			runnerModelHint: "AGENT_AI_MODEL for bigbear-test-runner plan execution.",
			webModel: "Web vision model",
			webModelHint: "WEB_AUTOMATION_AI_MODEL for bigbear-web-cli element location.",
			androidModel: "Android vision model",
			androidModelHint: "ANDROID_AI_MODEL for bigbear-android-cli element location.",
			visionModel: "Capture vision model",
			visionModelHint: "VISION_MODEL for record-tool screenshot analysis.",
			overridden: "Overridden",
			reset: "Reset to default",
			readOnly: "This deployment stores settings read-only.",
			unavailable: "This plugin is not loaded, so it cannot be configured right now.",
			save: "Save",
			saving: "Saving…",
			saveFailed: "The deployment did not accept these values; they were left for you to correct.",
			invalidValue: "Enter text, or leave blank to use the default."
		};
		/** Simplified Chinese copy. */
		const zh = {
			title: "大熊工具箱",
			description: "工具箱 CLI 从环境变量读取的网关配置，优先于任何项目 .env 文件。",
			toolkitDir: "工具箱目录",
			toolkitDirHint: "留空使用仓库内 extensions/bigbear-toolkit。",
			gatewayApiKey: "网关 API Key",
			gatewayApiKeyHint: "runner、Web、安卓、视觉四组 CLI 共用的密钥，保存在 profile 补丁里。",
			gatewayBaseUrl: "网关 Base URL",
			gatewayBaseUrlHint: "OpenAI 兼容接口地址，例如 http://192.168.1.6:13000/v1。",
			runnerModel: "Runner 模型",
			runnerModelHint: "bigbear-test-runner 执行计划用的 AGENT_AI_MODEL。",
			webModel: "Web 视觉模型",
			webModelHint: "bigbear-web-cli 元素定位用的 WEB_AUTOMATION_AI_MODEL。",
			androidModel: "安卓视觉模型",
			androidModelHint: "bigbear-android-cli 元素定位用的 ANDROID_AI_MODEL。",
			visionModel: "采集视觉模型",
			visionModelHint: "录制工具截图分析用的 VISION_MODEL。",
			overridden: "已覆盖",
			reset: "恢复默认",
			readOnly: "本部署的设置为只读。",
			unavailable: "该插件当前未加载，暂时无法配置。",
			save: "保存",
			saving: "保存中…",
			saveFailed: "本部署没有接受这些值，已保留供你修改。",
			invalidValue: "请填写文本；留空表示使用默认值。"
		};
		/**
		* The form frame's copy, read from this page's dictionary.
		* @param t - the page's locale reader.
		* @returns the labels the shared settings form renders.
		*/
		function formLabels(t) {
			return {
				unavailable: t("unavailable"),
				readOnly: t("readOnly"),
				saveFailed: t("saveFailed"),
				save: t("save"),
				saving: t("saving")
			};
		}
		//#endregion
		//#region src/client/BigbearCard.tsx
		/**
		* Render the bigbear one-liner or its settings form, as the Plugins page asks.
		* @param props - the view asked for, locale copy, the form snapshot, and its actions.
		* @returns the one-liner, or the form.
		*/
		function BigbearCard(props) {
			const { t } = props;
			const state = props.useBigbearCard((snapshot) => snapshot);
			if (props.view === "summary") return t("description");
			const disabled = !state.writable;
			const fields = [
				{
					id: "plugin-config-bigbear-toolkit-dir",
					label: t("toolkitDir"),
					hint: t("toolkitDirHint"),
					field: "toolkitDir"
				},
				{
					id: "plugin-config-bigbear-gateway-key",
					label: t("gatewayApiKey"),
					hint: t("gatewayApiKeyHint"),
					field: "gatewayApiKey"
				},
				{
					id: "plugin-config-bigbear-gateway-url",
					label: t("gatewayBaseUrl"),
					hint: t("gatewayBaseUrlHint"),
					field: "gatewayBaseUrl"
				},
				{
					id: "plugin-config-bigbear-runner-model",
					label: t("runnerModel"),
					hint: t("runnerModelHint"),
					field: "runnerModel"
				},
				{
					id: "plugin-config-bigbear-web-model",
					label: t("webModel"),
					hint: t("webModelHint"),
					field: "webModel"
				},
				{
					id: "plugin-config-bigbear-android-model",
					label: t("androidModel"),
					hint: t("androidModelHint"),
					field: "androidModel"
				},
				{
					id: "plugin-config-bigbear-vision-model",
					label: t("visionModel"),
					hint: t("visionModelHint"),
					field: "visionModel"
				}
			];
			return /* @__PURE__ */ (0, react_jsx_runtime.jsx)(_deepseek_ai_dsh_client_ui_primitives.SettingsForm, {
				labels: formLabels(t),
				state,
				onSave: props.save,
				onDiscard: props.discard,
				children: fields.map((field) => /* @__PURE__ */ (0, react_jsx_runtime.jsx)(_deepseek_ai_dsh_client_ui_primitives.SettingsValueField, {
					id: field.id,
					label: field.label,
					hint: field.hint,
					overriddenLabel: t("overridden"),
					resetLabel: t("reset"),
					invalidLabel: t("invalidValue"),
					disabled,
					...state[field.field],
					onEdit: (text) => {
						props.edit(field.field, text);
					},
					onReset: () => {
						props.resetField(field.field);
					}
				}, field.field))
			});
		}
		//#endregion
		//#region src/client/bigbear-card-controller.ts
		/** Profile entry id of the bigbear extension row. */
		const BIGBEAR_NS = "bigbear-agents";
		const FIELDS = [
			"toolkitDir",
			"gatewayApiKey",
			"gatewayBaseUrl",
			"runnerModel",
			"webModel",
			"androidModel",
			"visionModel"
		];
		/**
		* Bridges the extension entry's form onto the page's staged form. The served
		* schema nests gateway values under `gateway`; the page flattens them to one
		* card, so field names map onto config paths here.
		*/
		var BigbearCardController = class {
			form;
			store;
			/** @param scope - the shared configuration form of the bigbear extension entry. */
			constructor(scope) {
				this.form = new _deepseek_ai_dsh_client_ui_primitives.SettingsFormModel(scope, FIELDS.map((field) => (0, _deepseek_ai_dsh_client_ui_primitives.settingsTextField)(field)));
				this.store = this.form.bind(() => this.projection());
			}
			projection() {
				const shell = this.form.shell();
				const fields = Object.fromEntries(FIELDS.map((field) => [field, this.form.field(field)]));
				return {
					...shell,
					...fields
				};
			}
			/**
			* Build the face the page's slot registration injects.
			* @returns the page's snapshot and its form actions.
			*/
			inject() {
				return {
					hooks: { bigbearCard: this.store },
					...this.form.actions()
				};
			}
			/** Release the form subscription. */
			dispose() {
				this.form.dispose();
			}
		};
		//#endregion
		//#region src/client/index.ts
		/** Dictionary namespace owned by this plugin. */
		const NS = "settings.bigbear";
		/** Required services (cordis fiber inject). */
		const inject = [
			"slots",
			"locale",
			"configForms"
		];
		/**
		* Mount the bigbear settings page while the Host serves its namespace.
		* @param ctx - the browser plugin context.
		*/
		function apply(ctx) {
			const t = ctx.locale.bind(NS);
			ctx.effect(() => ctx.locale.register(NS, {
				zh,
				en
			}), "bigbear-agents: dictionaries");
			const card = new BigbearCardController(ctx.configForms.get(BIGBEAR_NS));
			ctx.effect(() => () => {
				card.dispose();
			}, "bigbear-agents: form subscriptions");
			ctx.effect(() => ctx.configForms.whileServed([BIGBEAR_NS], () => ctx.slots.inject("plugins.item", () => ctx.slots.register({
				name: "plugins.item",
				id: "bigbear",
				order: 45,
				label: () => t("title"),
				locale: NS,
				inject: () => card.inject()
			}, BigbearCard))), "bigbear-agents: page");
		}
		//#endregion
		exports.NS = NS;
		exports.apply = apply;
		exports.inject = inject;
		return module.exports;
	}
});

//# sourceMappingURL=client.js.map