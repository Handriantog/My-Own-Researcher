<template>
  <div class="research-page run-page">
    <ResearchNav />
    <main class="research-main run-progress">
      <div class="research-breadcrumb"><RouterLink to="/research">{{ t('interface.workspace') }}</RouterLink><span>→ {{ t('research.research') }}</span></div>
      <p v-if="!run && !error" role="status">{{ t('research.loadingRun') }}</p>
      <template v-if="run">
        <header class="run-heading">
          <div class="run-title">
            <div class="run-status-line"><span class="run-status" :class="{ working: live, failed: run.status === 'failed' || !!error }"><span aria-hidden="true"></span>{{ t(`research.statuses.${run.status}`) }}</span><span class="run-heartbeat" role="status">{{ error ? t('runProgress.reconnecting') : lastSync ? t('runProgress.lastChecked', { seconds: syncAge }) : t('runProgress.connecting') }}</span></div>
            <h1 :class="{ expanded: questionExpanded }">{{ run.source.question }}</h1>
            <button type="button" class="question-toggle" :aria-expanded="questionExpanded" @click="questionExpanded = !questionExpanded">{{ t(questionExpanded ? 'runProgress.collapseQuestion' : 'runProgress.fullQuestion') }}</button>
          </div>
          <div class="run-controls">
            <button v-if="active" class="secondary-action" :disabled="busy || run.stop_requested" @click="control('stop')">{{ t(run.stop_requested ? 'research.stopping' : 'research.stop') }}</button>
            <template v-else-if="['failed','interrupted','stopped'].includes(run.status)">
              <button v-if="run.status !== 'stopped'" class="secondary-action" :disabled="busy" @click="control('stop')">{{ t('research.stop') }}</button>
              <button class="primary-action" :disabled="busy" @click="control('resume')">{{ t(run.memory_recovery_required ? 'recovery.retryMemory' : run.simulation_restart_required ? 'research.restartContinue' : 'research.resume') }}</button>
              <button v-if="run.simulation_id && ['simulation','memory','report'].includes(run.stage)" class="secondary-action" :disabled="busy" @click="control('partial-report')">{{ t('research.partialReport') }}</button>
            </template>
            <RouterLink v-if="run.status === 'completed' && run.report_id" class="primary-action" :to="`/report/${run.report_id}`">{{ t('research.openReport') }} ↗</RouterLink>
          </div>
        </header>
        <p v-if="run.memory_recovery_required" class="research-notice">{{ t('recovery.memoryHint') }}</p>
        <p v-if="run.simulation_restart_required" class="research-notice">{{ t('research.restartSimulation') }}</p>
        <p v-if="run.error" class="research-error" role="alert">{{ t(`research.stages.${run.error.stage}`) }}: {{ run.error.message }}</p>

        <ol class="run-stage-strip" :aria-label="t('research.progress')">
          <li v-for="(stage, index) in stages" :key="stage" :class="{ done: isDone(stage), current: run.stage === stage && !isDone(stage), halted: run.stage === stage && !live && !isDone(stage) }" :aria-current="run.stage === stage && !isDone(stage) ? 'step' : undefined">
            <div class="run-stage-label"><span>{{ isDone(stage) ? '✓' : String(index + 1).padStart(2, '0') }}</span><h2>{{ t(`research.stages.${stage}`) }}</h2></div>
            <div class="stage-meter" role="progressbar" :aria-label="t(`research.stages.${stage}`)" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="progressFor(stage) ?? undefined" :aria-valuetext="stageLabel(stage)" :class="{ indeterminate: progressFor(stage) === null && live }"><span :style="{ width: progressFor(stage) === null ? '35%' : `${progressFor(stage)}%` }"></span></div>
            <span class="stage-caption">{{ stageLabel(stage) }}</span>
          </li>
        </ol>

        <div class="run-workspace-toolbar">
          <div class="run-view-switcher" role="group" :aria-label="t('runProgress.view')">
            <button v-for="mode in ['graph','split','activity']" :key="mode" type="button" :aria-pressed="viewMode === mode" :class="{ selected: viewMode === mode }" @click="viewMode = mode">{{ t(`runProgress.${mode}`) }}</button>
          </div>
          <span class="run-graph-counts">{{ t('runProgress.graphCounts', { nodes: graphData?.nodes?.length || 0, edges: graphData?.edges?.length || 0 }) }}</span>
          <RouterLink v-if="run.simulation_id" :to="`/simulation/${run.simulation_id}/start`">{{ t('research.viewSimulation') }} →</RouterLink>
        </div>
        <div class="run-live-workspace" :class="`view-${viewMode}`">
          <section v-if="viewMode !== 'activity'" class="run-graph-pane" :aria-label="t('runProgress.graph')">
            <GraphPanel :key="viewMode" :graph-data="graphData" :loading="detailBusy && !graphData" :current-phase="run.stage === 'graph' && live ? 1 : 2" :is-simulating="run.stage === 'simulation' && live" :empty-message="t(run.stage === 'analysis' ? 'runProgress.graphWaiting' : 'runProgress.graphEmpty')" @refresh="refreshDetails(true)" @toggle-maximize="viewMode = viewMode === 'graph' ? 'split' : 'graph'" />
          </section>
          <section v-if="viewMode !== 'graph'" class="run-activity-pane" :aria-label="t('runProgress.activity')">
            <header class="activity-heading"><div><span class="eyebrow">{{ t('runProgress.currentStep') }}</span><h2>{{ t(`research.stages.${run.stage}`) }}</h2></div><span class="activity-live" :class="{ active: live }">{{ t(live ? 'runProgress.live' : 'runProgress.saved') }}</span></header>
            <div class="activity-summary">
            <div class="current-activity" aria-live="polite"><p>{{ currentMessage }}</p><p v-if="detail.stage === 'preparation' && detail.preparation?.entities_count" class="activity-counter">{{ t('runProgress.profiles', { current: detail.preparation.profiles_count || 0, total: detail.preparation.entities_count }) }}</p><p v-if="detail.stage === 'simulation' && detail.simulation?.total_rounds" class="activity-counter">{{ t('research.rounds', { current: detail.simulation.current_round || 0, total: detail.simulation.total_rounds }) }} · {{ t('runProgress.actions', { count: detail.simulation.total_actions_count || 0 }) }}</p></div>
            <MemorySaveProgress v-if="run.stage === 'memory'" :progress="detail.memory" :now="clock" :active="active" />
            <p v-if="detailErrors.length" class="activity-error" role="status">{{ t('runProgress.detailError') }} {{ detailErrors.join(' · ') }} <button type="button" :disabled="detailBusy" @click="refreshDetails(true)">{{ t('research.retry') }}</button></p>
            </div>
            <div class="terminal-toolbar"><span>{{ t('runProgress.terminal') }}</span><label><input type="checkbox" v-model="followLogs" /> {{ t('runProgress.follow') }}</label></div>
            <div ref="terminal" class="run-terminal" role="log" :aria-label="t('runProgress.terminal')" aria-live="off" tabindex="0">
              <p v-if="!events.length" class="terminal-empty">{{ t('runProgress.waitingActivity') }}</p>
              <div v-for="event in events" :key="event.id" class="terminal-line" :class="event.kind"><time>{{ event.time }}</time><span>{{ event.message }}</span></div>
            </div>
            <p class="terminal-note">{{ t('runProgress.logNote') }}</p>
          </section>
        </div>

        <details class="run-settings-details"><summary>{{ t('research.runSettings') }} <span>{{ run.settings.provider }} · {{ t(`research.depths.${run.settings.depth}`) }} · {{ t('research.atOnce', { count: run.settings.concurrency }) }}</span></summary>
          <div class="run-settings-grid">
            <dl><dt>{{ t('research.provider') }}</dt><dd>{{ run.settings.provider }}</dd><dt>{{ t('research.model') }}</dt><dd>{{ run.settings.model || t('research.defaultModel') }}</dd><dt>{{ t('research.platform') }}</dt><dd>{{ run.settings.platform === 'parallel' ? t('research.both') : run.settings.platform }}</dd></dl>
            <div><span class="eyebrow">{{ t('research.estimated') }}</span><p class="token-range">{{ tokenRange(run.estimate, locale) }}</p><span v-if="run.estimate" class="workload-label">{{ t(`research.labels.${run.estimate.label}`) }} · {{ t(`research.${run.estimate.confidence}`) }}</span><p class="form-help">{{ t('research.originalEstimate') }}: {{ tokenRange(run.original_estimate, locale) }}</p></div>
            <div v-if="run.usage"><span class="eyebrow">{{ t('research.actualUsage') }}</span><p class="token-range">{{ run.usage.total_tokens === null ? t('research.unknown') : new Intl.NumberFormat(locale).format(run.usage.total_tokens) }}</p><p>{{ t(`research.coverage.${run.usage.coverage}`) }}</p><p class="form-help">{{ t('research.usageHelp', { reported: run.usage.reported_calls, calls: run.usage.calls }) }}</p><p class="form-help">{{ t('research.reasoningUnknown') }}</p></div>
          </div>
        </details>
      </template>
      <p v-if="error" class="research-error" role="alert">{{ error }} <button class="plain-button" @click="refresh">{{ t('research.retry') }}</button></p>
    </main>
  </div>
</template>
<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import ResearchNav from '../components/ResearchNav.vue'
import GraphPanel from '../components/GraphPanel.vue'
import MemorySaveProgress from '../components/MemorySaveProgress.vue'
import service from '../api/index'
import { getResearch, controlResearch } from '../api/research'
import { tokenRange } from '../utils/researchSetup'
import { createRunObserver, stageProgress } from '../utils/researchProgress'

const { t, locale } = useI18n(), route = useRoute()
const run = ref(null), error = ref(''), busy = ref(false), viewMode = ref('split'), questionExpanded = ref(false)
const detail = ref({}), graphData = ref(null), detailErrors = ref([]), detailBusy = ref(false)
const events = ref([]), terminal = ref(null), followLogs = ref(true), lastSync = ref(0), clock = ref(Date.now())
const stages = ['analysis','graph','preparation','simulation','memory','report']
const active = computed(() => ['running','queued','stopping'].includes(run.value?.status))
const live = computed(() => active.value && !error.value && syncAge.value < 15)
const syncAge = computed(() => Math.max(0, Math.floor((clock.value - lastSync.value) / 1000)))
const isDone = stage => run.value?.completed_stages.includes(stage)
const progressFor = stage => stageProgress(stage, run.value, detail.value)
const currentMessage = computed(() => {
  if (!run.value) return ''
  if (run.value.status === 'completed') return t('runProgress.complete')
  if (run.value.error) return run.value.error.message
  if (['stopped', 'interrupted', 'stopping'].includes(run.value.status)) return t(`research.statuses.${run.value.status}`)
  if (detail.value.stage === run.value.stage) {
    const message = detail.value.task?.message || detail.value.preparation?.message || detail.value.report?.message
    if (message) return message
  }
  return t(`runProgress.hints.${run.value.stage}`)
})
function stageLabel(stage) {
  if (isDone(stage)) return t('runProgress.done')
  if (run.value.stage !== stage) return t('runProgress.waiting')
  if (!active.value) return t(`research.statuses.${run.value.status}`)
  const progress = progressFor(stage)
  return progress === null ? t('runProgress.working') : `${progress}%`
}
let timer, heartbeat, disposed = false, generation = 0, controlEpoch = 0, refreshing = false, refreshQueued = false, forceGraphQueued = false, observer = createRunObserver(service)
let seen = new Set(), lastState = '', lastDetailMessage = ''
function addEvent(message, key, kind = '', timestamp) {
  if (!message || seen.has(key)) return
  seen.add(key)
  if (seen.size > 1200) seen = new Set([...seen].slice(-600))
  const date = timestamp ? new Date(timestamp) : new Date()
  events.value.push({ id: key, message, kind, time: Number.isNaN(date.getTime()) ? '—' : date.toLocaleTimeString(locale.value, { hour12: false }) })
  events.value = events.value.slice(-200)
  if (followLogs.value) nextTick(() => { if (terminal.value) terminal.value.scrollTop = terminal.value.scrollHeight })
}
function recordRun(next) {
  const state = `${next.stage}:${next.status}`
  if (state !== lastState) {
    addEvent(`${t(`research.stages.${next.stage}`)} · ${t(`research.statuses.${next.status}`)}`, `state:${state}:${Date.now()}`)
    lastState = state
  }
  if (next.error) addEvent(next.error.message, `error:${next.error.stage}:${next.error.message}`, 'error')
}
async function refreshDetails(forceGraph = false) {
  if (!run.value || disposed) return
  if (detailBusy.value) { forceGraphQueued ||= forceGraph; return }
  const ticket = generation, epoch = controlEpoch, snapshot = run.value, reader = observer
  forceGraph ||= forceGraphQueued
  forceGraphQueued = false
  detailBusy.value = true
  try {
    const value = await reader.read(snapshot, { forceGraph })
    if (disposed || ticket !== generation || epoch !== controlEpoch) return
    graphData.value = value.graph
    detailErrors.value = value.errors
    if (run.value.stage !== value.stage) return
    detail.value = detail.value.stage === value.stage ? { ...detail.value, ...value } : value
    const message = value.task?.message || value.preparation?.message || value.report?.message
    if (message && message !== lastDetailMessage) { addEvent(message, `detail:${snapshot.stage}:${message}`); lastDetailMessage = message }
    if (value.memory?.total) {
      const m = value.memory
      addEvent(t('runProgress.memoryBatches', { current: m.completed, total: m.total }), `memory:${m.started_at}:${m.completed}:${m.total}`)
    }
    if (value.graph) addEvent(t('runProgress.graphCounts', { nodes: value.graph.nodes?.length || 0, edges: value.graph.edges?.length || 0 }), `graph:${value.graph.nodes?.length}:${value.graph.edges?.length}`)
    if (value.preparation?.entities_count) addEvent(t('runProgress.profiles', { current: value.preparation.profiles_count || 0, total: value.preparation.entities_count }), `profiles:${value.preparation.profiles_count}`)
    for (const action of [...(value.actions || [])].reverse()) {
      const content = action.action_args?.content || action.action_args?.text || ''
      addEvent(`${action.agent_name} · ${(action.action_type || 'ACTION').replaceAll('_', ' ')}${content ? `: ${content}` : ''}`, `action:${action.platform}:${action.timestamp}:${action.agent_id}:${action.action_type}`, '', action.timestamp)
    }
    for (const line of value.reportLogs || []) addEvent(line, `report:${line}`)
  } finally {
    if (ticket === generation) {
      detailBusy.value = false
      // A terminal transition may stop the status poll while an older detail read
      // is in flight. Fetch the new stage's final snapshot before going idle.
      if (!disposed && (forceGraphQueued || epoch !== controlEpoch || run.value.stage !== snapshot.stage || run.value.status !== snapshot.status)) void refreshDetails(true)
    }
  }
}
async function refresh() {
  if (disposed) return
  if (refreshing || busy.value) { refreshQueued = true; return }
  refreshQueued = false
  clearTimeout(timer)
  const ticket = generation, epoch = controlEpoch, id = route.params.runId
  refreshing = true
  try {
    const result = await getResearch(id)
    if (disposed || ticket !== generation || epoch !== controlEpoch) return
    const previous = run.value
    run.value = result.data; error.value = ''; lastSync.value = Date.now(); clock.value = Date.now()
    recordRun(result.data)
    void refreshDetails(!!previous && (previous.stage !== run.value.stage || previous.status !== run.value.status))
  } catch (e) { if (!disposed && ticket === generation && epoch === controlEpoch) error.value = e.message }
  finally {
    if (ticket === generation) {
      refreshing = false
      if (!disposed && !busy.value) {
        if (refreshQueued) void refresh()
        else if (!run.value || active.value || error.value) timer = setTimeout(refresh, 2000)
      }
    }
  }
}
async function control(action) {
  if (busy.value) return
  controlEpoch++; clearTimeout(timer)
  busy.value = true; error.value = ''
  const ticket = generation
  try {
    const result = await controlResearch(route.params.runId, action)
    if (disposed || ticket !== generation) return
    run.value = result.data
    recordRun(result.data)
  } catch (e) { if (!disposed && ticket === generation) error.value = e.message }
  finally {
    if (!disposed && ticket === generation) {
      busy.value = false
      void refreshDetails(true)
      await refresh()
    }
  }
}
watch(() => route.params.runId, () => {
  generation++; clearTimeout(timer); observer = createRunObserver(service)
  run.value = null; detail.value = {}; graphData.value = null; detailErrors.value = []; events.value = []
  error.value = ''; lastSync.value = 0; detailBusy.value = false; refreshing = false; busy.value = false; refreshQueued = false; forceGraphQueued = false
  seen = new Set(); lastState = ''; lastDetailMessage = ''
  void refresh()
})
watch(followLogs, value => { if (value) nextTick(() => { if (terminal.value) terminal.value.scrollTop = terminal.value.scrollHeight }) })
onMounted(() => { void refresh(); heartbeat = setInterval(() => { clock.value = Date.now() }, 1000) })
onUnmounted(() => { disposed = true; generation++; clearTimeout(timer); clearInterval(heartbeat) })
</script>
<style src="../assets/researchProgress.css"></style>
