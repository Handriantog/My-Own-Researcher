<template>
  <div class="research-page"><ResearchNav /><main class="research-main run-progress">
    <div class="research-breadcrumb"><RouterLink to="/">{{ t('research.home') }}</RouterLink><span>→ 03 {{ t('research.research') }}</span></div>
    <p v-if="!run && !error" role="status">{{ t('research.loadingRun') }}</p>
    <template v-if="run">
      <header class="research-heading"><div><span class="eyebrow accent" role="status">{{ t(`research.statuses.${run.status}`) }}</span><h1>{{ run.source.question }}</h1><p>{{ t('research.backgroundHelp') }}</p></div></header>
      <div class="progress-grid"><section :aria-label="t('research.progress')"><ol class="run-stages"><li v-for="(stage, index) in stages" :key="stage" :class="{ done: run.completed_stages.includes(stage), current: run.stage === stage && run.status !== 'completed' }"><span class="stage-index">{{ run.completed_stages.includes(stage) ? '✓' : String(index + 1).padStart(2, '0') }}</span><div><h2>{{ t(`research.stages.${stage}`) }}</h2><span v-if="run.stage === stage" class="form-help">{{ t(`research.statuses.${run.status}`) }}<template v-if="stage === 'simulation' && run.stage_progress?.total_rounds"> · {{ t('research.rounds', { current: run.stage_progress.current_round || 0, total: run.stage_progress.total_rounds }) }}</template></span></div></li></ol>
        <div class="run-controls"><button v-if="active" class="secondary-action" :disabled="busy || run.stop_requested" @click="control('stop')">{{ t(run.stop_requested ? 'research.stopping' : 'research.stop') }}</button>
          <template v-else-if="['failed','interrupted','stopped'].includes(run.status)"><button v-if="run.status !== 'stopped'" class="secondary-action" :disabled="busy" @click="control('stop')">{{ t('research.stop') }}</button><p v-if="run.simulation_restart_required" class="research-notice">{{ t('research.restartSimulation') }}</p><button class="primary-action" :disabled="busy" @click="control('resume')">{{ t(run.simulation_restart_required ? 'research.restartContinue' : 'research.resume') }}</button><button v-if="run.simulation_id && ['simulation','memory','report'].includes(run.stage)" class="secondary-action" :disabled="busy" @click="control('partial-report')">{{ t('research.partialReport') }}</button></template>
          <RouterLink v-if="run.status === 'completed' && run.report_id" class="primary-action" :to="`/report/${run.report_id}`">{{ t('research.openReport') }} ↗</RouterLink>
          <RouterLink v-if="run.simulation_id" class="back-link" :to="`/simulation/${run.simulation_id}/start`">{{ t('research.viewSimulation') }} →</RouterLink>
        </div>
      </section><aside class="run-summary"><span class="eyebrow">{{ t('research.runSettings') }}</span><dl><dt>{{ t('research.provider') }}</dt><dd>{{ run.settings.provider }}</dd><dt>{{ t('research.model') }}</dt><dd>{{ run.settings.model || t('research.defaultModel') }}</dd><dt>{{ t('research.parallel') }}</dt><dd>{{ t('research.atOnce', { count: run.settings.concurrency }) }}</dd><dt>{{ t('research.depth') }}</dt><dd>{{ t(`research.depths.${run.settings.depth}`) }}</dd><dt>{{ t('research.platform') }}</dt><dd>{{ run.settings.platform === 'parallel' ? t('research.both') : run.settings.platform }}</dd></dl>
        <div class="estimate-block"><span class="eyebrow">{{ t('research.estimated') }}</span><p class="token-range">{{ tokenRange(run.estimate, locale) }}</p><span class="workload-label">{{ t(`research.labels.${run.estimate.label}`) }} · {{ t(`research.${run.estimate.confidence}`) }}</span><p class="form-help">{{ t('research.originalEstimate') }}: {{ tokenRange(run.original_estimate, locale) }}</p></div>
        <div class="usage-block" aria-live="polite"><span class="eyebrow">{{ t('research.actualUsage') }}</span><p class="token-range">{{ run.usage.total_tokens === null ? t('research.unknown') : new Intl.NumberFormat(locale).format(run.usage.total_tokens) }}</p><p>{{ t(`research.coverage.${run.usage.coverage}`) }}</p><p class="form-help">{{ t('research.usageHelp', { reported: run.usage.reported_calls, calls: run.usage.calls }) }}</p><p class="form-help">{{ t('research.reasoningUnknown') }}</p></div>
      </aside></div>
      <p v-if="run.error" class="research-error" role="alert">{{ t(`research.stages.${run.error.stage}`) }}: {{ run.error.message }}</p>
    </template>
    <p v-if="error" class="research-error" role="alert">{{ error }} <button class="plain-button" @click="refresh">{{ t('research.retry') }}</button></p>
  </main></div>
</template>
<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import ResearchNav from '../components/ResearchNav.vue'
import { getResearch, controlResearch } from '../api/research'
import { tokenRange } from '../utils/researchSetup'
const { t, locale } = useI18n(), route = useRoute()
const run = ref(null), error = ref(''), busy = ref(false)
const stages = ['analysis','graph','preparation','simulation','memory','report']
const active = computed(() => ['running','queued','stopping'].includes(run.value?.status))
let timer, disposed = false
async function refresh() {
  clearTimeout(timer)
  try { const result = await getResearch(route.params.runId); if (!disposed) { run.value = result.data; error.value = '' } } catch (e) { if (!disposed) error.value = e.message }
  finally { if (!disposed && (!run.value || active.value || error.value)) timer = setTimeout(refresh, 2000) }
}
async function control(action) { busy.value = true; error.value = ''; try { run.value = (await controlResearch(route.params.runId, action)).data; await refresh() } catch (e) { error.value = e.message } finally { busy.value = false } }
onMounted(refresh); onUnmounted(() => { disposed = true; clearTimeout(timer) })
</script>
