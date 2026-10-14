<template>
  <div class="language-switcher" ref="switcherRef" @keydown.esc.stop="closeAndFocus">
    <button ref="trigger" type="button" class="switcher-trigger" :aria-expanded="open" aria-haspopup="true" :aria-label="`${t('interface.language')}: ${currentLabel}`" @click="open = !open" @keydown.down.prevent="openAndFocus">
      {{ currentLabel }}<span class="caret" aria-hidden="true">{{ open ? '▴' : '▾' }}</span>
    </button>
    <ul v-if="open" class="switcher-dropdown" :aria-label="t('interface.language')">
      <li v-for="loc in availableLocales" :key="loc.key"><button type="button" class="switcher-option" :class="{ active: loc.key === locale }" :aria-pressed="loc.key === locale" :lang="loc.key" @click="switchLocale(loc.key)">{{ loc.label }}<span v-if="loc.key === locale" aria-hidden="true">✓</span></button></li>
    </ul>
  </div>
</template>
<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { availableLocales } from '@/i18n/index.js'
const { locale, t } = useI18n()
const open = ref(false), switcherRef = ref(null), trigger = ref(null)
const currentLabel = computed(() => availableLocales.find(l => l.key === locale.value)?.label || locale.value)
function closeAndFocus() { open.value = false; trigger.value?.focus() }
async function openAndFocus() { open.value = true; await nextTick(); switcherRef.value?.querySelector('.switcher-option')?.focus() }
function switchLocale(key) { locale.value = key; localStorage.setItem('locale', key); document.documentElement.lang = key; closeAndFocus() }
function onOutside(event) { if (!switcherRef.value?.contains(event.target)) open.value = false }
onMounted(() => { document.addEventListener('click', onOutside); document.addEventListener('focusin', onOutside); document.documentElement.lang = locale.value })
onUnmounted(() => { document.removeEventListener('click', onOutside); document.removeEventListener('focusin', onOutside) })
</script>
<style scoped>
.language-switcher { position: relative; display: inline-block; font-family: var(--ui-font, system-ui); }.switcher-trigger { min-height: 40px; padding: 9px 12px; background: transparent; color: #333; border: 1px solid #aeb3a6; border-radius: 3px; font: 500 12px/1.4 var(--ui-font, system-ui); cursor: pointer; display: flex; align-items: center; gap: 8px; }.switcher-trigger:hover { background: #f0f2ea; }.caret { font-size: 10px; }.switcher-dropdown { position: absolute; top: 100%; right: 0; margin-top: 8px; background: #fffefa; border: 1px solid #dcded5; border-radius: 3px; list-style: none; padding: 6px; min-width: 155px; z-index: 1000; box-shadow: 0 8px 24px #171a1620; }.switcher-option { width: 100%; display: flex; align-items: center; justify-content: space-between; gap: 18px; text-align: left; padding: 10px; min-height: 40px; background: transparent; border: 0; border-radius: 2px; color: #333; font: 12px var(--ui-font, system-ui); cursor: pointer; white-space: nowrap; }.switcher-option:hover,.switcher-option:focus-visible { background: #eeefe7; }.switcher-option.active { color: #a73516; }.switcher-trigger:focus-visible,.switcher-option:focus-visible { outline: 3px solid #d76532; outline-offset: 2px; }
</style>
