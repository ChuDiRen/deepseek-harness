/** Locale bundles for the bigbear toolkit's settings page. */

import type { SettingsFormLabels } from '@deepseek-ai/dsh-client-ui-primitives'

/** Locale keys the page renders. */
export type BigbearSettingsLocaleKey =
  | 'title' | 'description'
  | 'toolkitDir' | 'toolkitDirHint'
  | 'gatewayApiKey' | 'gatewayApiKeyHint'
  | 'gatewayBaseUrl' | 'gatewayBaseUrlHint'
  | 'runnerModel' | 'runnerModelHint'
  | 'webModel' | 'webModelHint'
  | 'androidModel' | 'androidModelHint'
  | 'visionModel' | 'visionModelHint'
  | 'overridden' | 'reset' | 'readOnly' | 'unavailable'
  | 'save' | 'saving' | 'saveFailed' | 'invalidValue'

/** English copy. */
export const en: Record<BigbearSettingsLocaleKey, string> = {
  title: 'Bigbear toolkit',
  description: 'Gateway values the toolkit CLIs read from the environment, ahead of any project .env file.',
  toolkitDir: 'Toolkit directory',
  toolkitDirHint: 'Leave blank to use the repository copy at extensions/bigbear-toolkit.',
  gatewayApiKey: 'Gateway API key',
  gatewayApiKeyHint: 'Shared key for the runner, web, Android, and vision CLIs. Stored in the profile patch.',
  gatewayBaseUrl: 'Gateway base URL',
  gatewayBaseUrlHint: 'OpenAI-compatible endpoint, for example http://192.168.1.6:13000/v1.',
  runnerModel: 'Runner model',
  runnerModelHint: 'AGENT_AI_MODEL for bigbear-test-runner plan execution.',
  webModel: 'Web vision model',
  webModelHint: 'WEB_AUTOMATION_AI_MODEL for bigbear-web-cli element location.',
  androidModel: 'Android vision model',
  androidModelHint: 'ANDROID_AI_MODEL for bigbear-android-cli element location.',
  visionModel: 'Capture vision model',
  visionModelHint: 'VISION_MODEL for record-tool screenshot analysis.',
  overridden: 'Overridden',
  reset: 'Reset to default',
  readOnly: 'This deployment stores settings read-only.',
  unavailable: 'This plugin is not loaded, so it cannot be configured right now.',
  save: 'Save',
  saving: 'Saving…',
  saveFailed: 'The deployment did not accept these values; they were left for you to correct.',
  invalidValue: 'Enter text, or leave blank to use the default.',
}

/** Simplified Chinese copy. */
export const zh: Record<BigbearSettingsLocaleKey, string> = {
  title: '大熊工具箱',
  description: '工具箱 CLI 从环境变量读取的网关配置，优先于任何项目 .env 文件。',
  toolkitDir: '工具箱目录',
  toolkitDirHint: '留空使用仓库内 extensions/bigbear-toolkit。',
  gatewayApiKey: '网关 API Key',
  gatewayApiKeyHint: 'runner、Web、安卓、视觉四组 CLI 共用的密钥，保存在 profile 补丁里。',
  gatewayBaseUrl: '网关 Base URL',
  gatewayBaseUrlHint: 'OpenAI 兼容接口地址，例如 http://192.168.1.6:13000/v1。',
  runnerModel: 'Runner 模型',
  runnerModelHint: 'bigbear-test-runner 执行计划用的 AGENT_AI_MODEL。',
  webModel: 'Web 视觉模型',
  webModelHint: 'bigbear-web-cli 元素定位用的 WEB_AUTOMATION_AI_MODEL。',
  androidModel: '安卓视觉模型',
  androidModelHint: 'bigbear-android-cli 元素定位用的 ANDROID_AI_MODEL。',
  visionModel: '采集视觉模型',
  visionModelHint: '录制工具截图分析用的 VISION_MODEL。',
  overridden: '已覆盖',
  reset: '恢复默认',
  readOnly: '本部署的设置为只读。',
  unavailable: '该插件当前未加载，暂时无法配置。',
  save: '保存',
  saving: '保存中…',
  saveFailed: '本部署没有接受这些值，已保留供你修改。',
  invalidValue: '请填写文本；留空表示使用默认值。',
}

/**
 * The form frame's copy, read from this page's dictionary.
 * @param t - the page's locale reader.
 * @returns the labels the shared settings form renders.
 */
export function formLabels(t: (key: BigbearSettingsLocaleKey) => string): SettingsFormLabels {
  return {
    unavailable: t('unavailable'),
    readOnly: t('readOnly'),
    saveFailed: t('saveFailed'),
    save: t('save'),
    saving: t('saving'),
  }
}
