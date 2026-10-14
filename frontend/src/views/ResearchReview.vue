<template>
  <div class="research-page"><ResearchNav /><main class="research-main">
    <div class="research-breadcrumb"><RouterLink to="/research">01 {{ t('research.sources') }}</RouterLink><span>→</span><strong>02 {{ t('research.review') }}</strong><span>→ 03 {{ t('research.research') }}</span></div>
    <header class="research-heading"><div><span class="eyebrow accent">{{ t('research.ready') }}</span><h1>{{ t('research.title') }}</h1><p>{{ t('research.subtitle') }}</p></div><span class="step-number" aria-hidden="true">02</span></header>
    <p v-if="loading" class="research-loading" role="status">{{ t('research.checking') }}</p>
    <div v-if="source && metadata" class="review-grid">
      <aside class="source-summary"><span class="eyebrow">{{ t('research.yourResearch') }}</span><h2>{{ source.question }}</h2>
        <ul class="source-files"><li v-for="(file, index) in source.files" :key="index"><span aria-hidden="true">↳</span> {{ file.filename }}</li></ul>
        <span class="eyebrow">{{ t('research.throughReport') }}</span><ol class="stage-list"><li v-for="stage in ['analysis','graph','preparation','simulation','memory','report']" :key="stage">{{ t(`research.stages.${stage}`) }}</li></ol>
        <p class="form-help">{{ t('research.controlHelp') }}</p><RouterLink class="back-link" to="/research">← {{ t('research.back') }}</RouterLink>
      </aside>
      <section :aria-label="t('interface.runSettings')"><h2 class="run-settings-heading">{{ t('interface.runSettings') }}</h2><fieldset class="settings-lock" :disabled="starting || uncertain">
        <ResearchSettingsForm v-model="chosen" :metadata="metadata" /><label class="remember-setting"><input type="checkbox" v-model="remember" /> {{ t('research.remember') }}</label>
      </fieldset>
      <div class="estimate-block" aria-live="polite"><div class="label-line"><span class="eyebrow">{{ t('research.estimated') }}</span><span v-if="estimate" class="workload-label">{{ t(`research.labels.${estimate.label}`) }}</span></div>
        <p class="token-range">{{ estimating ? '…' : tokenRange(estimate, locale) }} <span>{{ t('research.tokens') }}</span></p><p class="form-help">{{ t('research.estimateHelp') }}</p>
        <details v-if="estimate"><summary>{{ t('research.estimateDetails') }}</summary><p>{{ t('research.preliminary') }}</p><dl class="estimate-stages"><template v-for="(range, stage) in estimate.stages" :key="stage"><dt>{{ t(`research.estimateStages.${stage}`) }}</dt><dd>{{ tokenRange({lower: range[0], upper: range[1]}, locale) }}</dd></template></dl><p>{{ t('research.assumptions', { agents: estimate.assumptions.agents.join('–'), rounds: estimate.assumptions.rounds.join('–'), platforms: estimate.assumptions.platforms }) }}</p><p>{{ t('research.thresholds') }}</p><p>{{ t('research.reasoningUnknown') }} · {{ estimate.version }}</p></details>
      </div>
      <p v-if="uncertain" class="research-notice" role="status">{{ t('research.startUncertain') }}</p>
      <p v-if="error" class="research-error" role="alert">{{ error }}</p>
      <button class="primary-action start-research" :disabled="!canStart" @click="start">{{ t(starting ? 'research.starting' : uncertain ? 'research.retryStart' : 'research.start') }} <span aria-hidden="true">↗</span></button><p class="action-help">{{ t('research.startHelp') }}</p>
      </section>
    </div>
    <p v-if="error && (!source || !metadata)" class="research-error" role="alert">{{ error }} <RouterLink to="/research">{{ t('research.back') }}</RouterLink></p>
  </main></div>
</template>
<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import ResearchNav from '../components/ResearchNav.vue'
import ResearchSettingsForm from '../components/ResearchSettingsForm.vue'
import { getSettings, saveSettings, createDraft, getDraft, getReviewProject, estimateResearch, startResearch } from '../api/research'
import { getPendingUpload, clearPendingUpload } from '../store/pendingUpload'
import { validateSetup, startIntent, tokenRange } from '../utils/researchSetup'
const { t, locale } = useI18n(); const route = useRoute(), router = useRouter()
const source = ref(null), metadata = ref(null), chosen = ref({}), estimate = ref(null), loading = ref(true), estimating = ref(false), starting = ref(false), uncertain = ref(false), remember = ref(true), error = ref('')
const scope = computed(() => source.value?.draft_id || source.value?.project_id)
const canStart = computed(() => !!metadata.value && !!source.value && !loading.value && !starting.value && !validateSetup(chosen.value) && (uncertain.value || (metadata.value.provider.connection !== 'unavailable' && metadata.value.graph.status !== 'unavailable' && !!estimate.value && !estimating.value)))
let estimateTimer, estimateSequence = 0, disposed = false
async function loadSource() {
  if (route.query.draft_id) return (await getDraft(route.query.draft_id)).data
  if (route.query.project_id) return (await getReviewProject(route.query.project_id)).data
  const pending = getPendingUpload()
  if (!pending.files.length) throw new Error(t('research.addSources'))
  const form = new FormData(); pending.files.forEach(file => form.append('files', file)); form.append('question', pending.simulationRequirement)
  const result = (await createDraft(form)).data
  await router.replace({ name: 'ResearchReview', query: { draft_id: result.draft_id } })
  return result
}
onMounted(async () => {
  try {
    const [data, info] = await Promise.all([loadSource(), getSettings()]); source.value = data; metadata.value = info.data
    if (data.run_id || data.research_run_id) {
      const runId = data.run_id || data.research_run_id
      localStorage.setItem('lastResearchRun', runId)
      await router.replace({ name:'ResearchRun', params:{ runId } })
      return
    }
    let saved = null; try { saved = JSON.parse(sessionStorage.getItem(`research-choice:${scope.value}`)) } catch { /* invalid local preference */ }
    chosen.value = saved?.provider === info.data.defaults.provider ? saved : { ...info.data.defaults }
    const intent = sessionStorage.getItem(`research-start:${scope.value}`)
    if (intent) { chosen.value = JSON.parse(intent).payload.settings; uncertain.value = true }
  } catch (e) { error.value = e.message } finally { loading.value = false; refreshEstimate() }
})
function refreshEstimate() {
  clearTimeout(estimateTimer)
  if (!source.value || !metadata.value || validateSetup(chosen.value)) return
  const sequence = ++estimateSequence; estimating.value = true
  estimateTimer = setTimeout(async () => {
    try {
      const result = await estimateResearch({ draft_id: source.value.draft_id, project_id: source.value.project_id, settings: chosen.value })
      if (!disposed && sequence === estimateSequence) { estimate.value = result.data; error.value = '' }
    } catch (e) { if (!disposed && sequence === estimateSequence) { estimate.value = null; error.value = e.message } }
    finally { if (!disposed && sequence === estimateSequence) estimating.value = false }
  }, 200)
}
watch(chosen, () => { if (scope.value) sessionStorage.setItem(`research-choice:${scope.value}`, JSON.stringify(chosen.value)); refreshEstimate() }, { deep: true })
onUnmounted(() => { disposed = true; clearTimeout(estimateTimer) })
async function start() {
  if (!canStart.value) return
  starting.value = true; error.value = ''
  try {
    if (remember.value && !uncertain.value) await saveSettings(chosen.value)
    const intent = startIntent(sessionStorage, scope.value, { draft_id: source.value.draft_id, project_id: source.value.project_id, simulation_id: route.query.simulation_id, settings: chosen.value })
    const result = await startResearch({ ...intent.payload, idempotency_key: intent.key })
    sessionStorage.removeItem(`research-start:${scope.value}`); localStorage.setItem('lastResearchRun', result.data.run_id); clearPendingUpload()
    await router.push({ name: 'ResearchRun', params: { runId: result.data.run_id } })
  } catch (e) {
    error.value = e.message; uncertain.value = uncertain.value || !e.response || e.response.status >= 500
    if (!uncertain.value) sessionStorage.removeItem(`research-start:${scope.value}`)
  } finally { starting.value = false }
}
</script>
