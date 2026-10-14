<template>
  <div class="run-settings-form">
    <div class="provider-row">
      <span class="provider-mark" aria-hidden="true">{{ metadata.provider.name?.[0] || 'AI' }}</span>
      <div><span class="eyebrow">{{ t('research.provider') }}</span><h2>{{ metadata.provider.name || metadata.provider.id }}</h2>
        <p>{{ t(metadata.provider.installed === false ? 'research.notInstalled' : 'research.connectionManaged') }}</p></div>
      <span class="connection" :class="metadata.provider.connection">{{ t(`research.connection.${metadata.provider.connection}`) }}</span>
    </div>
    <p v-if="metadata.provider.connection === 'unknown'" class="form-help">{{ t('research.unknownHelp') }}</p>
    <div class="setting-row">
      <label :for="`${id}-model`">{{ t('research.model') }}</label>
      <select :id="`${id}-model`" :value="modelChoice" @change="selectModel($event.target.value)">
        <option value="">{{ t('research.defaultModel') }}</option>
        <option v-for="model in metadata.provider.models" :key="model.id" :value="model.id">{{ model.name }}{{ model.source === 'configured' ? ` · ${t('research.configured')}` : '' }}</option>
        <option value="__custom">{{ t('research.customModel') }}</option>
      </select>
      <template v-if="modelChoice === '__custom'">
        <label class="custom-label" :for="`${id}-custom`">{{ t('research.modelId') }}</label>
        <input :id="`${id}-custom`" type="text" :value="modelValue.model || ''" maxlength="200" autocomplete="off" @input="update('model', $event.target.value)" :placeholder="t('research.modelPlaceholder')" />
      </template>
      <p class="form-help">{{ t(metadata.provider.discovery === 'available' ? 'research.modelsDiscovered' : 'research.modelsUnknown') }}</p>
    </div>
    <div class="setting-row">
      <div class="label-line"><label :for="`${id}-parallel`">{{ t('research.parallel') }}</label><output :for="`${id}-parallel`">{{ t('research.atOnce', { count: modelValue.concurrency }) }}</output></div>
      <input :id="`${id}-parallel`" type="range" min="1" max="8" step="1" :value="modelValue.concurrency" :aria-describedby="`${id}-parallel-help`" @input="update('concurrency', Number($event.target.value))" />
      <div class="range-labels"><span>{{ t('research.sequential') }}</span><span>{{ t('research.moreParallel') }}</span></div>
      <p :id="`${id}-parallel-help`" class="form-help">{{ t('research.parallelHelp', { count: modelValue.concurrency }) }}</p>
    </div>
    <fieldset class="setting-row depth-field"><legend>{{ t('research.depth') }}</legend>
      <div class="depth-options"><label v-for="(percent, depth) in { quick: 25, moderate: 50, full: 100 }" :key="depth" :class="{ selected: modelValue.depth === depth }">
        <input type="radio" :name="`${id}-depth`" :value="depth" :checked="modelValue.depth === depth" @change="update('depth', depth)" />
        <strong>{{ t(`research.depths.${depth}`) }}</strong><span>{{ t('research.roundFraction', { percent }) }}</span>
      </label></div>
    </fieldset>
    <div class="setting-row"><label :for="`${id}-platform`">{{ t('research.platform') }}</label>
      <select :id="`${id}-platform`" :value="modelValue.platform" @change="update('platform', $event.target.value)"><option value="reddit">Reddit</option><option value="twitter">Twitter</option><option value="parallel">{{ t('research.both') }}</option></select>
    </div>
    <details class="graph-details"><summary>{{ t('research.graphDetails') }}</summary>
      <p>{{ metadata.graph.provider }} · {{ t(`research.connection.${metadata.graph.status === 'ready' ? 'connected' : metadata.graph.status === 'configured' ? 'configured' : metadata.graph.status === 'unavailable' ? 'unavailable' : 'unknown'}`) }}</p>
      <p v-if="metadata.graph.inference_provider">{{ t('research.graphInference') }}: {{ metadata.graph.inference_provider }} / {{ metadata.graph.inference_provider === modelValue.provider ? modelValue.model || t('research.defaultModel') : metadata.graph.model || t('research.defaultModel') }}</p>
      <p class="form-help">{{ t('research.graphHelp') }}</p>
    </details>
    <p v-if="metadata.graph.status === 'unavailable'" class="research-error" role="alert">{{ metadata.graph.error || t('research.graphUnavailable') }}</p>
  </div>
</template>
<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
const props = defineProps({ modelValue: { type: Object, required: true }, metadata: { type: Object, required: true }, id: { type: String, default: 'run' } })
const emit = defineEmits(['update:modelValue'])
const { t } = useI18n()
const custom = ref(false)
const modelChoice = computed(() => custom.value || (props.modelValue.model !== null && !props.metadata.provider.models?.some(m => m.id === props.modelValue.model)) ? '__custom' : props.modelValue.model || '')
function update(key, value) { emit('update:modelValue', { ...props.modelValue, [key]: value }) }
function selectModel(value) { custom.value = value === '__custom'; update('model', custom.value ? '' : value || null) }
</script>
