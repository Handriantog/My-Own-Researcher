<template><nav class="research-nav"><RouterLink to="/" class="research-brand">My Own Researcher</RouterLink><div><LanguageSwitcher /><button class="nav-settings" @click="settingsOpen = true">{{ t('research.settings') }}</button></div></nav><ResearchSettingsPanel v-if="settingsOpen" @close="settingsOpen = false" /></template>
<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import LanguageSwitcher from './LanguageSwitcher.vue'
import ResearchSettingsPanel from './ResearchSettingsPanel.vue'
const { t } = useI18n(); const settingsOpen = ref(false)
</script>
