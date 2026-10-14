<template>
  <header class="site-header">
    <RouterLink to="/" class="site-brand">My Own Researcher<span class="brand-dot" aria-hidden="true">.</span></RouterLink>
    <nav class="site-navigation" :aria-label="t('interface.navigation')">
      <RouterLink to="/research" :class="{ active: inWorkspace }" :aria-current="inWorkspace ? 'page' : undefined">{{ t('interface.workspace') }}</RouterLink>
      <RouterLink to="/demo" :class="{ active: inDemo }" :aria-current="inDemo ? 'page' : undefined">{{ t('nav.demo') }}</RouterLink>
    </nav>
    <div class="site-utilities">
      <LanguageSwitcher />
      <button v-if="inWorkspace" type="button" class="site-settings" @click="settingsOpen = true">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M4 7h16M4 17h16"/><circle cx="9" cy="7" r="3" fill="currentColor"/><circle cx="15" cy="17" r="3" fill="currentColor"/></svg>
        {{ t('research.settings') }}
      </button>
    </div>
  </header>
  <ResearchSettingsPanel v-if="settingsOpen" @close="settingsOpen = false" />
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import LanguageSwitcher from './LanguageSwitcher.vue'
import ResearchSettingsPanel from './ResearchSettingsPanel.vue'
const { t } = useI18n()
const route = useRoute()
const settingsOpen = ref(false)
const inDemo = computed(() => route.path === '/demo')
const inWorkspace = computed(() => route.path !== '/' && !inDemo.value)
watch(() => route.path, () => { settingsOpen.value = false })
</script>

<style scoped>
.site-header { background: #171a16; color: #f7f8f2; min-height: 76px; padding: 12px max(32px, calc((100vw - 1200px) / 2)); display: flex; align-items: center; gap: 32px; font-family: var(--ui-font); }
.site-brand { color: inherit; text-decoration: none; font: 700 17px/1.3 var(--ui-mono); letter-spacing: -.045em; white-space: nowrap; margin-right: auto; }
.brand-dot { color: #fa8258; }
.site-navigation, .site-utilities { display: flex; align-items: center; gap: 8px; }
.site-navigation a { padding: 12px; min-height: 44px; color: #c9cec3; text-decoration: none; font-size: 13px; border-bottom: 2px solid transparent; }
.site-navigation a:hover { color: #fff; }
.site-navigation a.active { color: #fff; border-color: #fa8258; }
.site-utilities { padding-left: 24px; border-left: 1px solid #42483d; }
.site-settings { display: flex; align-items: center; gap: 8px; min-height: 40px; padding: 9px 12px; color: #f7f8f2; background: transparent; border: 1px solid #5b6254; border-radius: 3px; font: 500 12px/1.4 var(--ui-font); cursor: pointer; }
.site-settings:hover { background: #30362a; }
.site-header :deep(.switcher-trigger) { min-height: 40px; padding: 9px 12px; color: #f7f8f2; border-color: #5b6254; border-radius: 3px; font: 500 12px/1.4 var(--ui-font); }
.site-header :deep(.switcher-trigger:hover) { background: #30362a; }
@media (max-width: 760px) {
  .site-header { padding: 16px 22px 12px; gap: 12px; flex-wrap: wrap; }
  .site-brand { flex-basis: 100%; font-size: 16px; }
  .site-navigation { margin-right: auto; gap: 0; }
  .site-navigation a { padding: 10px 8px; font-size: 12px; }
  .site-utilities { border: 0; padding-left: 0; gap: 6px; }
  .site-settings { padding: 9px; font-size: 11px; }
  .site-settings svg { display: none; }
  .site-header :deep(.switcher-trigger) { padding: 9px; font-size: 11px; }
}
@media (max-width: 380px) { .site-header { padding-inline: 16px; gap: 8px; } .site-utilities { flex-wrap: wrap; } }
</style>
