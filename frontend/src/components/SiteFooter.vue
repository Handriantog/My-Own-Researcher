<template>
  <footer class="site-footer">
    <span>My Own Researcher <span class="footer-version">/ v0.1</span></span>
    <nav :aria-label="t('interface.resources')">
      <a href="https://github.com/Handriantog/My-Own-Researcher/blob/main/docs/agent-providers.md" target="_blank" rel="noopener noreferrer">{{ t('interface.connectAI') }} ↗</a>
      <a href="https://github.com/Handriantog/My-Own-Researcher/blob/main/docs/agent-mcp.md" target="_blank" rel="noopener noreferrer">{{ t('interface.connectAgent') }} ↗</a>
      <a href="https://github.com/Handriantog/My-Own-Researcher" target="_blank" rel="noopener noreferrer">GitHub ↗</a>
    </nav>
  </footer>
</template>
<script setup>
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
</script>
<style scoped>
.site-footer { max-width: 1200px; margin: 0 auto; padding: 28px 0 32px; border-top: 1px solid var(--ui-line); display: flex; justify-content: space-between; align-items: center; gap: 24px; font: 12px/1.6 var(--ui-font); color: var(--ui-muted); }
.footer-version { opacity: .7; margin-left: 8px; }.site-footer nav { display: flex; flex-wrap: wrap; gap: 22px; }.site-footer a { color: inherit; text-decoration: none; }.site-footer a:hover { color: var(--ui-accent); text-decoration: underline; text-underline-offset: 4px; }
@media (max-width: 1280px) { .site-footer { margin-inline: 40px; } }
@media (max-width: 700px) { .site-footer { margin-inline: 22px; align-items: flex-start; flex-direction: column; gap: 14px; }.site-footer nav { gap: 12px 20px; } }
</style>
