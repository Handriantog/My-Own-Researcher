<template>
  <dialog ref="dialog" class="settings-dialog" aria-labelledby="settings-title" @close="emit('close')" @click="outside">
    <div class="settings-panel"><header><div><span class="eyebrow">{{ t('research.defaults') }}</span><h1 id="settings-title">{{ t('research.settings') }}</h1></div><button type="button" class="plain-button" @click="dialog.close()" :aria-label="t('research.close')">✕</button></header>
      <p class="form-help">{{ t('research.defaultsHelp') }}</p>
      <p v-if="loading" role="status">{{ t('research.checking') }}</p>
      <ResearchSettingsForm v-if="metadata" v-model="chosen" :metadata="metadata" id="defaults" />
      <p v-if="error" class="research-error" role="alert">{{ error }}</p><p v-if="saved" role="status">{{ t('research.saved') }}</p>
      <button class="primary-action" :disabled="loading || saving || !metadata || !!validateSetup(chosen)" @click="save">{{ t(saving ? 'research.saving' : 'research.saveDefaults') }}</button>
    </div>
  </dialog>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { getSettings, saveSettings } from '../api/research'
import { validateSetup } from '../utils/researchSetup'
import ResearchSettingsForm from './ResearchSettingsForm.vue'
const emit = defineEmits(['close'])
const { t } = useI18n()
const dialog = ref(null), metadata = ref(null), chosen = ref({}), loading = ref(true), saving = ref(false), error = ref(''), saved = ref(false)
onMounted(async () => { dialog.value.showModal(); try { metadata.value = (await getSettings()).data; chosen.value = { ...metadata.value.defaults } } catch (e) { error.value = e.message } finally { loading.value = false } })
function outside(event) { if (event.target === dialog.value) { const r = dialog.value.getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.value.close() } }
async function save() { saving.value = true; error.value = ''; try { await saveSettings(chosen.value); saved.value = true } catch (e) { error.value = e.message } finally { saving.value = false } }
</script>
