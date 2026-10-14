<template>
  <div class="site-page landing-page">
    <SiteHeader />
    <main class="site-main">
      <section class="welcome-hero" aria-labelledby="welcome-title">
        <div class="welcome-copy">
          <p class="ui-eyebrow"><span class="eyebrow-dot" aria-hidden="true"></span>{{ t('landing.eyebrow') }}</p>
          <h1 id="welcome-title">{{ t('landing.title') }}<br><em>{{ t('landing.titleAccent') }}</em></h1>
          <p class="welcome-description">{{ t('landing.description') }}</p>
          <div class="welcome-actions">
            <RouterLink to="/research" class="ui-button ui-button-primary">{{ t('landing.start') }} <span aria-hidden="true">→</span></RouterLink>
            <RouterLink to="/demo" class="ui-button ui-button-secondary">{{ t('landing.demo') }}</RouterLink>
          </div>
          <p class="welcome-note">{{ t('landing.note') }}</p>
          <a href="#how-it-works" class="how-link">{{ t('landing.how') }} <span aria-hidden="true">↓</span></a>
        </div>
        <RouterLink to="/demo" class="example-preview" :aria-label="t('landing.previewLink')">
          <div class="preview-top"><span>LOOPLUNCH</span><span>{{ t('landing.savedExample') }}</span></div>
          <div class="preview-question"><span class="ui-eyebrow">{{ t('landing.questionLabel') }}</span><h2>{{ t('landing.exampleQuestion') }}</h2></div>
          <div class="perspective-map" aria-hidden="true">
            <svg viewBox="0 0 420 128" preserveAspectRatio="none"><path d="M210 31V67M210 67H66V101M210 67H354V101M210 67V101" /></svg>
            <span class="map-center">LoopLunch</span>
            <div class="map-people"><span>{{ t('landing.founder') }}</span><span>{{ t('landing.customers') }}</span><span>{{ t('landing.operations') }}</span></div>
          </div>
          <div class="preview-findings"><span class="ui-eyebrow">{{ t('landing.reportPreview') }}</span>
            <p><span>01</span>{{ t('landing.finding1') }}</p><p><span>02</span>{{ t('landing.finding2') }}</p><p><span>03</span>{{ t('landing.finding3') }}</p>
          </div>
          <div class="preview-bottom"><span>{{ t('landing.exampleNote') }}</span><span class="preview-arrow" aria-hidden="true">↗</span></div>
        </RouterLink>
      </section>
      <section id="how-it-works" class="how-section" aria-labelledby="how-title">
        <div class="how-heading"><p class="ui-eyebrow">{{ t('landing.how') }}</p><h2 id="how-title">{{ t('landing.howTitle') }}</h2></div>
        <div class="how-grid">
          <article v-for="step in [1, 2, 3]" :key="step"><span class="how-number">0{{ step }}</span><h3>{{ t(`landing.step${step}Title`) }}</h3><p>{{ t(`landing.step${step}Description`) }}</p></article>
        </div>
      </section>
    </main>
    <SiteFooter />
  </div>
</template>
<script setup>
import { useI18n } from 'vue-i18n'
import SiteHeader from '../components/SiteHeader.vue'
import SiteFooter from '../components/SiteFooter.vue'
const { t } = useI18n()
</script>
<style scoped>
.welcome-hero { display: grid; grid-template-columns: 1.1fr 1fr; align-items: center; gap: 78px; padding: 25px 0 76px; }
.welcome-copy .ui-eyebrow { display: flex; gap: 10px; align-items: center; }.eyebrow-dot { width: 6px; height: 6px; background: var(--ui-accent); }
h1 { font-size: clamp(40px, 4.5vw, 63px); line-height: 1.08; font-weight: 500; letter-spacing: -.06em; margin: 26px 0; }h1 em { color: var(--ui-accent); font-style: normal; }
.welcome-description { max-width: 490px; font: 16px/1.85 system-ui, sans-serif; color: var(--ui-muted); }
.welcome-actions { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 32px; }.welcome-actions .ui-button { min-height: 50px; padding-inline: 24px; }
.welcome-note { color: var(--ui-muted); font-size: 11px; margin-top: 15px; }.how-link { display: inline-flex; align-items: center; gap: 16px; color: var(--ui-ink); text-decoration: none; font-size: 12px; margin-top: 34px; }.how-link:hover { color: var(--ui-accent); }
.example-preview { display: block; color: inherit; text-decoration: none; background: #edf0e6; border: 1px solid #d9dece; border-radius: 4px; box-shadow: 0 12px 36px #242a1710; transition: border-color .2s; }.example-preview:hover { border-color: #8b947c; }
.preview-top { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px; padding: 18px 26px; border-bottom: 1px solid #d4dbc8; font: 10px/1.5 var(--ui-mono); letter-spacing: .06em; color: #626e54; }.preview-top span:first-child { font-weight: 700; color: #333d2b; }
.preview-question { padding: 25px 28px 0; }.preview-question .ui-eyebrow { font-size: 9px; }h2 { font-size: 30px; letter-spacing: -.04em; line-height: 1.2; font-weight: 500; }.preview-question h2 { max-width: 340px; margin-top: 10px; }
.perspective-map { height: 130px; position: relative; margin: 6px 28px 22px; display: flex; align-items: center; flex-direction: column; justify-content: space-between; padding: 15px 0 0; }.perspective-map svg { position: absolute; inset: 0; width: 100%; height: 100%; }.perspective-map path { fill: none; stroke: #9ba68b; stroke-width: 1; }.map-center,.map-people span { position: relative; font-size: 10px; border: 1px solid #bfc8b0; background: #f7f8f2; border-radius: 3px; padding: 8px 12px; }.map-center { background: #303c27; color: white; border-color: #303c27; }.map-people { display: flex; width: 100%; justify-content: space-between; gap: 6px; }.map-people span { width: 30%; text-align: center; padding: 8px 4px; }
.preview-findings { margin: 0 18px; padding: 20px; background: #fffefa; border: 1px solid #dde2d4; box-shadow: 0 3px 8px #303c2705; }.preview-findings .ui-eyebrow { display: block; font-size: 9px; margin-bottom: 12px; }.preview-findings p { display: flex; align-items: baseline; gap: 12px; font-size: 12px; padding-block: 5px; }.preview-findings p span { font: 10px var(--ui-mono); color: #929b86; }
.preview-bottom { padding: 16px 26px; display: flex; align-items: center; justify-content: space-between; gap: 16px; font-size: 10px; color: #626e54; }.preview-arrow { font-size: 24px; color: var(--ui-accent); }
.how-section { border-top: 1px solid var(--ui-line); padding-top: 34px; scroll-margin-top: 24px; }.how-heading { display: flex; justify-content: space-between; gap: 24px; align-items: center; margin-bottom: 30px; }.how-heading h2 { font-size: 25px; }.how-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 32px; }.how-grid article { position: relative; padding-left: 44px; }.how-grid article + article { border-left: 1px solid var(--ui-line); padding-left: 60px; }.how-number { position: absolute; left: 0; top: 4px; color: var(--ui-accent); font: 11px var(--ui-mono); }.how-grid article + article .how-number { left: 20px; }.how-grid h3 { font-size: 17px; font-weight: 500; margin-bottom: 10px; }.how-grid p { font: 13px/1.7 system-ui, sans-serif; color: var(--ui-muted); }
@media (max-width: 950px) { .welcome-hero { gap: 40px; } h1 { font-size: 46px; }.how-heading { align-items: flex-start; flex-direction: column; gap: 10px; } }
@media (max-width: 700px) { .welcome-hero { grid-template-columns: 1fr; gap: 40px; padding: 6px 0 42px; }h1 { font-size: clamp(40px, 9vw, 56px); }.welcome-description { font-size: 15px; }.welcome-actions { margin-top: 26px; }.how-link { margin-top: 24px; }.example-preview { max-width: 520px; width: 100%; }.how-grid { grid-template-columns: 1fr; gap: 26px; }.how-grid article + article { border: 0; padding-left: 44px; }.how-grid article + article .how-number { left: 0; }.preview-question h2 { font-size: 27px; } }
</style>
