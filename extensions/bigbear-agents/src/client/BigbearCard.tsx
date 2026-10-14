/** The bigbear toolkit's settings page: the gateway values every toolkit CLI reads. */

import type {} from '@deepseek-ai/dsh-client-ui-plugin-manager/client'
import { SettingsForm, SettingsValueField } from '@deepseek-ai/dsh-client-ui-primitives'
import type { InjectFace, PropsLocale, PropsRuntime } from '@deepseek-ai/dsh-client-ui-slots'
import { formLabels } from './locales.ts'
import type { BigbearCardFace } from './bigbear-card-controller.ts'

/** Props the renderer binds for the bigbear page. */
export type BigbearCardProps =
  PropsRuntime<'plugins.item'>
  & PropsLocale<'settings.bigbear'>
  & InjectFace<BigbearCardFace>

/** One text field of the card, bound through the shared settings form. */
interface FieldBinding {
  readonly id: string
  readonly label: string
  readonly hint: string
  readonly field: 'toolkitDir' | 'gatewayApiKey' | 'gatewayBaseUrl'
    | 'runnerModel' | 'webModel' | 'androidModel' | 'visionModel'
}

/**
 * Render the bigbear one-liner or its settings form, as the Plugins page asks.
 * @param props - the view asked for, locale copy, the form snapshot, and its actions.
 * @returns the one-liner, or the form.
 */
export function BigbearCard(props: BigbearCardProps) {
  const { t } = props
  const state = props.useBigbearCard(snapshot => snapshot)
  if (props.view === 'summary') return t('description')
  const disabled = !state.writable
  const fields: readonly FieldBinding[] = [
    { id: 'plugin-config-bigbear-toolkit-dir', label: t('toolkitDir'), hint: t('toolkitDirHint'), field: 'toolkitDir' },
    { id: 'plugin-config-bigbear-gateway-key', label: t('gatewayApiKey'), hint: t('gatewayApiKeyHint'), field: 'gatewayApiKey' },
    { id: 'plugin-config-bigbear-gateway-url', label: t('gatewayBaseUrl'), hint: t('gatewayBaseUrlHint'), field: 'gatewayBaseUrl' },
    { id: 'plugin-config-bigbear-runner-model', label: t('runnerModel'), hint: t('runnerModelHint'), field: 'runnerModel' },
    { id: 'plugin-config-bigbear-web-model', label: t('webModel'), hint: t('webModelHint'), field: 'webModel' },
    { id: 'plugin-config-bigbear-android-model', label: t('androidModel'), hint: t('androidModelHint'), field: 'androidModel' },
    { id: 'plugin-config-bigbear-vision-model', label: t('visionModel'), hint: t('visionModelHint'), field: 'visionModel' },
  ]
  return (
    <SettingsForm labels={formLabels(t)} state={state} onSave={props.save} onDiscard={props.discard}>
      {fields.map(field => (
        <SettingsValueField
          key={field.field}
          id={field.id}
          label={field.label}
          hint={field.hint}
          overriddenLabel={t('overridden')}
          resetLabel={t('reset')}
          invalidLabel={t('invalidValue')}
          disabled={disabled}
          {...state[field.field]}
          onEdit={(text: string) => { props.edit(field.field, text) }}
          onReset={() => { props.resetField(field.field) }}
        />
      ))}
    </SettingsForm>
  )
}
