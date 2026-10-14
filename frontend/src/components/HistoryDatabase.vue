<template>
  <section class="research-history" aria-labelledby="recent-title">
    <div class="history-heading"><h2 id="recent-title">{{ t('workspace.recent') }}</h2><span v-if="projects.length">{{ projects.length }}</span></div>
    <p v-if="loading" class="history-message" role="status">{{ t('workspace.loadingHistory') }}</p>
    <div v-else-if="error" class="history-message" role="alert"><p>{{ t('workspace.historyError') }}</p><button type="button" class="ui-button ui-button-secondary history-retry" @click="loadHistory">{{ t('research.retry') }}</button></div>
    <div v-else-if="!projects.length" class="history-empty"><span aria-hidden="true">↗</span><h3>{{ t('workspace.noHistory') }}</h3><p>{{ t('workspace.noHistoryHelp') }}</p></div>
    <template v-else>
      <ul class="history-list"><li v-for="project in visibleProjects" :key="project.simulation_id">
        <div class="history-meta"><time :datetime="project.created_at">{{ formatDate(project.created_at) }}</time><span>{{ project.total_rounds ? t('history.roundsProgress', { current: project.current_round || 0, total: project.total_rounds }) : t('history.notStarted') }}</span></div>
        <RouterLink :to="destination(project)" class="history-title" :title="project.simulation_requirement"><span class="history-question">{{ project.simulation_requirement || t('history.untitledSimulation') }}</span><span aria-hidden="true">↗</span></RouterLink>
        <p v-if="project.files?.length" class="history-source">{{ project.files.map(file => file.filename).join(', ') }}</p>
        <div class="history-links"><RouterLink v-if="project.project_id" :to="`/process/${project.project_id}`">{{ t('workspace.openGraph') }}</RouterLink><RouterLink v-if="project.simulation_id" :to="`/simulation/${project.simulation_id}`">{{ t('workspace.openSetup') }}</RouterLink><RouterLink v-if="project.report_id" :to="`/report/${project.report_id}`">{{ t('workspace.openReport') }}</RouterLink></div>
      </li></ul>
      <button v-if="projects.length > 3" type="button" class="history-toggle ui-text-link" :aria-expanded="expanded" @click="expanded = !expanded">{{ t(expanded ? 'workspace.showLess' : 'workspace.showAll') }}</button>
    </template>
  </section>
</template>
<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getSimulationHistory } from '../api/simulation'
const { t, locale } = useI18n()
const projects = ref([]), loading = ref(true), error = ref(false), expanded = ref(false)
const visibleProjects = computed(() => expanded.value ? projects.value : projects.value.slice(0, 3))
function destination(project) {
  if (project.report_id) return `/report/${project.report_id}`
  if (project.simulation_id) return `/simulation/${project.simulation_id}`
  return `/process/${project.project_id}`
}
function formatDate(value) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : new Intl.DateTimeFormat(locale.value, { month: 'short', day: 'numeric', year: 'numeric' }).format(date)
}
async function loadHistory() {
  loading.value = true
  error.value = false
  try { projects.value = (await getSimulationHistory(20)).data || [] }
  catch { error.value = true }
  finally { loading.value = false }
}
onMounted(loadHistory)
</script>
<style scoped>
.history-heading { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }.history-heading h2 { font-size: 18px; font-weight: 500; letter-spacing: -.03em; }.history-heading>span { font: 10px var(--ui-mono); color: var(--ui-muted); border: 1px solid var(--ui-line); padding: 3px 6px; border-radius: 3px; }
.history-list { list-style: none; }.history-list li { padding: 20px 0; border-bottom: 1px solid var(--ui-line); }.history-meta { display: flex; flex-wrap: wrap; gap: 8px; justify-content: space-between; font-size: 9px; color: var(--ui-muted); margin-bottom: 10px; }.history-title { display: flex; justify-content: space-between; gap: 12px; color: var(--ui-ink); font-size: 14px; line-height: 1.5; font-weight: 500; text-decoration: none; overflow-wrap: anywhere; }.history-title:hover { color: var(--ui-accent); }.history-question { display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 3; overflow: hidden; min-width: 0; }.history-title>span[aria-hidden] { color: var(--ui-accent); flex-shrink: 0; }.history-source { color: var(--ui-muted); font-size: 10px; margin-top: 8px; overflow-wrap: anywhere; }.history-links { display: flex; flex-wrap: wrap; gap: 16px; margin-top: 12px; }.history-links a { font-size: 10px; color: var(--ui-muted); text-underline-offset: 3px; }.history-links a:hover { color: var(--ui-accent); }.history-toggle { background: transparent; border: 0; padding: 15px 0; cursor: pointer; text-decoration: underline; }
.history-message { color: var(--ui-muted); font-size: 12px; padding: 20px 0; }.history-retry { margin-top: 12px; min-height: 38px; padding: 8px 14px; font-size: 12px; }.history-empty { border: 1px dashed var(--ui-line); padding: 25px 22px; margin-top: 20px; background: #f4f5ee; border-radius: 3px; }.history-empty>span { font-size: 22px; color: #8a947c; }.history-empty h3 { margin: 10px 0 6px; font-size: 14px; font-weight: 500; }.history-empty p { font-size: 12px; color: var(--ui-muted); }
</style>
