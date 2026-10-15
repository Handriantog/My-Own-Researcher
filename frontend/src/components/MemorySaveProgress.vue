<template>
  <div class="memory-save-progress">
    <template v-if="progress?.total">
      <div class="memory-save-summary"><strong>{{ t('runProgress.memoryBatches', { current: progress.completed, total: progress.total }) }}</strong><span v-if="progress.percent !== null">{{ progress.percent }}%</span></div>
      <div class="stage-meter memory-save-meter" role="progressbar" :aria-label="t('research.stages.memory')" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="progress.percent ?? undefined" :aria-valuetext="t('runProgress.memoryBatches', { current: progress.completed, total: progress.total })"><span :style="{ width: progress.percent === null ? '0%' : `${progress.percent}%` }"></span></div>
      <p class="memory-save-counts">{{ t('runProgress.memoryQueue', { processing: progress.processing, queued: progress.queued }) }}<span v-if="progress.failed"> · {{ t('runProgress.memoryFailed', { count: progress.failed }) }}</span><span v-if="progress.unknown"> · {{ t('runProgress.memoryUnknown', { count: progress.unknown }) }}</span></p>
      <p v-if="progress.error" class="memory-save-error" role="status">{{ progress.error }}</p>
      <p v-else-if="progress.completed === progress.total && active">{{ t('runProgress.memoryFinalizing') }}</p>
      <p class="memory-save-timing"><span v-if="progress.started_at">{{ t('runProgress.memoryElapsed', { duration: duration((active ? now / 1000 : progress.checked_at) - progress.started_at) }) }}</span><span v-if="progress.completed_ai_calls !== null"> · {{ t('runProgress.memoryCalls', { count: progress.completed_ai_calls }) }}</span></p>
      <p v-if="progress.last_activity_at" class="memory-save-timing">{{ t('runProgress.memoryActivity', { duration: duration(now / 1000 - progress.last_activity_at) }) }}</p>
    </template>
    <p v-else class="memory-save-timing">{{ t('runProgress.memoryPreparing') }}</p>
    <p class="memory-save-explanation">{{ t('runProgress.memoryExplanation') }}</p>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
defineProps({ progress: Object, now: Number, active: Boolean })
function duration(value) {
  const seconds = Math.max(0, Math.floor(value))
  return seconds < 60 ? t('runProgress.seconds', { count: seconds }) : t('runProgress.minutes', { count: Math.floor(seconds / 60) })
}
</script>

<style scoped>
.memory-save-progress { margin-top: 14px; padding-top: 14px; border-top: 1px solid var(--line, #dce0d6); font-size: 13px; }
.memory-save-summary { display: flex; justify-content: space-between; gap: 12px; font-variant-numeric: tabular-nums; }
.memory-save-meter { margin: 10px 0; height: 6px; }
.memory-save-progress p { margin: 7px 0 0; line-height: 1.5; }
.memory-save-counts { font-variant-numeric: tabular-nums; }
.memory-save-timing, .memory-save-explanation { color: var(--muted, #697267); font-size: 12px; }
.memory-save-explanation { padding-top: 5px; }
.memory-save-error { color: #a43e32; }
</style>
