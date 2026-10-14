<template>
  <div class="site-page workspace-page">
    <SiteHeader />
    <main class="site-main workspace-main">
      <header class="workspace-heading"><div><p class="ui-eyebrow">{{ t('interface.workspace') }}</p><h1>{{ t('workspace.title') }}</h1><p>{{ t('workspace.description') }}</p></div>
        <RouterLink v-if="lastResearchRun" :to="`/research/runs/${lastResearchRun}`" class="ui-button ui-button-secondary">{{ t('workspace.continue') }} <span aria-hidden="true">→</span></RouterLink>
      </header>
      <div class="workspace-grid">
        <section class="source-card" aria-labelledby="sources-title">
          <div class="source-card-heading"><h2 id="sources-title">{{ t('workspace.newResearch') }}</h2><span>{{ t('workspace.step') }}</span></div>
          <form @submit.prevent="review">
            <label class="field-label" for="research-files"><span>01</span>{{ t('workspace.sources') }}</label>
            <div class="source-drop" :class="{ dragging: isDragOver }" @dragover.prevent="isDragOver = true" @dragleave.prevent="isDragOver = false" @drop.prevent="dropFiles">
              <span class="upload-symbol" aria-hidden="true">↑</span>
              <strong>{{ t('workspace.drop') }}</strong>
              <span class="upload-help" id="file-formats">{{ t('workspace.formats') }}</span>
              <label class="ui-button ui-button-secondary browse-label" for="research-files">{{ t('workspace.browse') }}</label>
              <input id="research-files" type="file" accept=".pdf,.md,.txt" multiple aria-describedby="file-formats" @change="selectFiles" />
            </div>
            <p v-if="rejectedNames" class="upload-error" role="alert">{{ t('workspace.invalidFiles', { names: rejectedNames }) }}</p>
            <ul v-if="files.length" class="selected-files" :aria-label="t('workspace.sources')"><li v-for="(file, index) in files" :key="index"><span class="file-extension">{{ file.name.split('.').pop().toUpperCase() }}</span><span class="selected-name">{{ file.name }}</span><button type="button" class="remove-file" :aria-label="t('workspace.removeFile', { name: file.name })" @click="files.splice(index, 1)">×</button></li></ul>
            <label class="field-label question-label" for="research-question"><span>02</span>{{ t('workspace.question') }}</label>
            <textarea id="research-question" v-model="question" rows="4" :placeholder="t('workspace.placeholder')" aria-describedby="question-help" required></textarea>
            <p id="question-help" class="field-help">{{ t('workspace.questionHelp') }}</p>
            <div class="source-submit"><button type="submit" class="ui-button ui-button-primary" :disabled="!canSubmit">{{ t('workspace.review') }} <span aria-hidden="true">→</span></button><p>{{ canSubmit ? t('workspace.reviewHelp') : t('workspace.requiredHelp') }}</p></div>
          </form>
        </section>
        <aside class="workspace-sidebar">
          <details class="workspace-status" :open="system !== null && !systemReady">
            <summary><span class="status-light" :class="{ ready: systemReady, unavailable: system !== null && !systemReady }" aria-hidden="true"></span><span>{{ system === null ? t('workspace.checking') : systemReady ? t('workspace.ready') : t('workspace.unavailable') }}</span><span class="status-chevron" aria-hidden="true">⌄</span></summary>
            <div class="status-details"><p>{{ t('workspace.ai') }} <strong>{{ system?.llm_provider || '—' }}</strong></p><p>{{ t('workspace.graph') }} <strong>{{ system?.graph_provider || '—' }}</strong></p><p class="status-explanation">{{ systemReady ? t('workspace.readyHelp') : t('workspace.unavailableHelp') }}</p><a href="https://github.com/Handriantog/My-Own-Researcher#install-and-run" target="_blank" rel="noopener noreferrer" class="ui-text-link">{{ t('workspace.setupHelp') }} ↗</a></div>
          </details>
          <HistoryDatabase />
          <div class="workspace-demo"><span class="ui-eyebrow">{{ t('workspace.firstTime') }}</span><h2>{{ t('workspace.demoTitle') }}</h2><p>{{ t('workspace.demoDescription') }}</p><RouterLink to="/demo" class="ui-text-link">{{ t('landing.demo') }} <span aria-hidden="true">→</span></RouterLink></div>
        </aside>
      </div>
    </main>
    <SiteFooter />
  </div>
</template>
<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import service from '../api'
import SiteHeader from '../components/SiteHeader.vue'
import SiteFooter from '../components/SiteFooter.vue'
import HistoryDatabase from '../components/HistoryDatabase.vue'
import { getPendingUpload, setPendingUpload } from '../store/pendingUpload'
const { t } = useI18n()
const router = useRouter()
const pending = getPendingUpload()
const files = ref([...pending.files])
const question = ref(pending.simulationRequirement || '')
const rejectedNames = ref('')
const isDragOver = ref(false)
const savedRun = localStorage.getItem('lastResearchRun')
const lastResearchRun = /^run_[a-f0-9]{32}$/.test(savedRun || '') ? savedRun : null
const canSubmit = computed(() => files.value.length > 0 && question.value.trim().length > 0)
function addFiles(selected) {
  const accepted = [], rejected = []
  for (const file of selected) {
    if (/\.(pdf|md|txt)$/i.test(file.name)) accepted.push(file)
    else rejected.push(file.name)
  }
  files.value.push(...accepted)
  rejectedNames.value = rejected.join(', ')
}
function selectFiles(event) { addFiles(Array.from(event.target.files)); event.target.value = '' }
function dropFiles(event) { isDragOver.value = false; addFiles(Array.from(event.dataTransfer.files)) }
function persistDraft() { setPendingUpload([...files.value], question.value) }
function review() {
  if (!canSubmit.value) return
  persistDraft()
  router.push({ name: 'ResearchReview' })
}
const system = ref(null)
const systemReady = computed(() => ['ready', 'configured'].includes(system.value?.graph?.status))
let statusTimer
async function refreshStatus() {
  try { system.value = (await service.get('/api/system/status', { timeout: 8000 })).data }
  catch { system.value = { graph: { status: 'unavailable' } } }
}
onMounted(() => { refreshStatus(); statusTimer = setInterval(refreshStatus, 15000) })
onUnmounted(() => { clearInterval(statusTimer); persistDraft() })
</script>
<style scoped>
.workspace-main { padding-top: 38px; }.workspace-heading { display: flex; justify-content: space-between; align-items: center; gap: 24px; margin-bottom: 34px; }.workspace-heading h1 { font-size: clamp(30px, 3.6vw, 44px); line-height: 1.2; font-weight: 500; letter-spacing: -.045em; margin: 10px 0; }.workspace-heading p:not(.ui-eyebrow) { font-size: 14px; color: var(--ui-muted); }.workspace-heading .ui-button { flex-shrink: 0; }
.workspace-grid { display: grid; grid-template-columns: minmax(0, 1.65fr) minmax(280px, 1fr); gap: 38px; align-items: start; }.source-card { border: 1px solid var(--ui-line); border-radius: 4px; background: #fffefa; padding: 28px; }.source-card-heading { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 8px; padding-bottom: 23px; margin-bottom: 25px; border-bottom: 1px solid var(--ui-line); }.source-card h2 { font-size: 20px; font-weight: 500; letter-spacing: -.025em; }.source-card-heading>span { font: 10px var(--ui-mono); color: var(--ui-muted); }
.field-label { display: flex; gap: 12px; font-size: 13px; font-weight: 600; margin-bottom: 12px; }.field-label>span { color: var(--ui-accent); font: 11px var(--ui-mono); align-self: center; }.source-drop { position: relative; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; padding: 22px 16px; background: #f6f7f1; border: 1px dashed #b7bfac; border-radius: 3px; text-align: center; }.source-drop.dragging,.source-drop:focus-within { border-color: var(--ui-accent); background: #fff4ec; }.source-drop:focus-within { outline: 3px solid #d76532; outline-offset: 3px; }.upload-symbol { font-size: 26px; line-height: 1; color: #727f63; }.source-drop strong { font-size: 13px; font-weight: 500; }.upload-help { font-size: 10px; color: var(--ui-muted); }.browse-label { padding: 8px 16px; font-size: 12px; min-height: 38px; background: #fffefa; }.source-drop input { position: absolute; inset: 0; opacity: 0; width: 100%; height: 100%; cursor: pointer; }.selected-files { list-style: none; margin-top: 12px; }.selected-files li { display: flex; align-items: center; gap: 10px; padding: 6px 0; border-bottom: 1px solid #eceee5; }.file-extension { font: 9px var(--ui-mono); color: var(--ui-muted); min-width: 28px; }.selected-name { font-size: 12px; overflow-wrap: anywhere; flex: 1; }.remove-file { min-width: 36px; min-height: 36px; background: transparent; border: 0; color: var(--ui-muted); cursor: pointer; font-size: 20px; }.remove-file:hover { color: var(--ui-accent); }.upload-error { color: #9f3013; font-size: 12px; margin-top: 10px; overflow-wrap: anywhere; }
.question-label { margin-top: 26px; }textarea { width: 100%; padding: 14px; border: 1px solid #b7bfac; border-radius: 3px; background: #fff; font-size: 13px; line-height: 1.7; color: var(--ui-ink); resize: vertical; min-height: 122px; }textarea::placeholder { color: #767c6f; }.field-help { color: var(--ui-muted); font-size: 11px; margin-top: 8px; }.source-submit { border-top: 1px solid var(--ui-line); margin-top: 24px; padding-top: 20px; }.source-submit .ui-button { width: 100%; justify-content: space-between; }.source-submit p { text-align: center; font-size: 10px; color: var(--ui-muted); margin-top: 10px; }
.workspace-status { border: 1px solid var(--ui-line); border-radius: 3px; background: #f0f2e9; margin-bottom: 30px; }.workspace-status summary { display: flex; align-items: center; gap: 10px; font-size: 12px; padding: 15px 16px; list-style: none; cursor: pointer; }.workspace-status summary::-webkit-details-marker { display: none; }.status-light { width: 7px; height: 7px; border-radius: 50%; background: #8b917f; flex-shrink: 0; }.status-light.ready { background: #527249; }.status-light.unavailable { background: #bd3d19; }.status-chevron { margin-left: auto; }.status-details { border-top: 1px solid var(--ui-line); margin-inline: 16px; padding: 12px 0 16px; font-size: 11px; }.status-details>p:not(.status-explanation) { display: flex; justify-content: space-between; gap: 20px; margin-bottom: 5px; }.status-details strong { overflow-wrap: anywhere; }.status-explanation { color: var(--ui-muted); margin: 10px 0; }.status-details a { font-size: 11px; }.workspace-demo { border-top: 1px solid var(--ui-line); margin-top: 28px; padding-top: 24px; }.workspace-demo .ui-eyebrow { font-size: 9px; }.workspace-demo h2 { font-size: 18px; font-weight: 500; letter-spacing: -.025em; margin: 8px 0; }.workspace-demo p { font-size: 12px; color: var(--ui-muted); margin-bottom: 14px; }
@media (max-width: 900px) { .workspace-grid { gap: 26px; grid-template-columns: minmax(0, 1.4fr) minmax(240px, 1fr); }.source-card { padding: 22px; } }
@media (max-width: 700px) { .workspace-heading { align-items: flex-start; flex-direction: column; gap: 16px; }.workspace-grid { grid-template-columns: minmax(0, 1fr); gap: 32px; }.source-card { padding: 20px 18px; }.workspace-status { margin-bottom: 26px; }.workspace-main { padding-top: 28px; } }
</style>
