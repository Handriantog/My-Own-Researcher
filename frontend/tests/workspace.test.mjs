import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, existsSync } from 'node:fs'
import vm from 'node:vm'
import { createRouter, createMemoryHistory } from 'vue-router'

function router() {
  const source = readFileSync(new URL('../src/router/index.js', import.meta.url), 'utf8')
    .replace(/^import .*$/gm, '')
    .replace(/\(\) => import\('[^']+'\)/g, '({})')
    .replace('export default router', 'globalThis.subject = router')
  const context = vm.createContext({ createRouter, createWebHistory: createMemoryHistory,
    Home: {}, Process: {}, SimulationView: {}, SimulationRunView: {}, ReportView: {}, InteractionView: {} })
  vm.runInContext(source, context)
  return context.subject
}

test('welcome and workspace are distinct routes, and old research bookmarks retain their query', async () => {
  const r = router()
  assert.equal(r.resolve('/research').name, 'Workspace')
  await r.push('/?source=bookmark#research')
  assert.equal(r.currentRoute.value.path, '/research')
  assert.equal(r.currentRoute.value.query.source, 'bookmark')
  await r.push('/')
  assert.equal(r.currentRoute.value.name, 'Home')
  // Hash navigation within the homepage must also reach the workspace.
  await r.push('/#research')
  assert.equal(r.currentRoute.value.path, '/research')
})

function workspace(pending, navigate = () => {}) {
  const path = new URL('../src/views/Workspace.vue', import.meta.url)
  assert.ok(existsSync(path), 'A dedicated workspace must own research input')
  const unmounted = []
  const source = readFileSync(path, 'utf8').match(/<script setup>([\s\S]*?)<\/script>/)[1]
    .replace(/^import .*$/gm, '')
  const context = vm.createContext({
    ref: value => ({ value }), computed: getter => ({ get value() { return getter() } }),
    onMounted() {}, onUnmounted: fn => unmounted.push(fn),
    useI18n: () => ({ t: key => key }), useRouter: () => ({ push: navigate }),
    localStorage: { getItem: () => null },
    getPendingUpload: () => pending,
    setPendingUpload: (files, question) => { pending.files = files; pending.simulationRequirement = question },
    clearInterval() {}, setInterval() {},
  })
  vm.runInContext(`${source}\nglobalThis.subject = { files, question, addFiles, canSubmit, review, rejectedNames };`, context)
  return { ...context.subject, leave: () => unmounted.forEach(fn => fn()) }
}

test('unfinished sources and question survive navigation away from the workspace', () => {
  const pending = { files: [], simulationRequirement: '' }
  const c = workspace(pending)
  const file = { name: 'brief.pdf', size: 42 }
  c.addFiles([file])
  c.question.value = 'Which assumptions should we explore?'
  c.leave()
  const restored = workspace(pending)
  assert.equal(restored.files.value[0], file)
  assert.equal(restored.question.value, 'Which assumptions should we explore?')
  assert.equal(restored.canSubmit.value, true)
})

test('source validation explains rejected files and review hands off without launching research', () => {
  const pending = { files: [], simulationRequirement: '' }
  const locations = []
  const c = workspace(pending, location => locations.push(location))
  c.question.value = 'A question'
  c.addFiles([{ name: 'image.png' }])
  assert.equal(c.rejectedNames.value, 'image.png')
  c.review()
  assert.equal(locations.length, 0)
  const file = { name: 'NOTES.MD' }
  c.addFiles([file])
  c.review()
  assert.equal(locations.length, 1)
  assert.equal(locations[0].name, 'ResearchReview')
  assert.equal(pending.files[0], file)
  assert.equal(pending.simulationRequirement, 'A question')
})

test('history distinguishes a failed load from an empty collection and can retry', async () => {
  const source = readFileSync(new URL('../src/components/HistoryDatabase.vue', import.meta.url), 'utf8')
    .match(/<script setup>([\s\S]*?)<\/script>/)[1].replace(/^import .*$/gm, '')
  let unavailable = true
  const context = vm.createContext({
    ref: value => ({ value }), computed: getter => ({ get value() { return getter() } }), onMounted() {},
    useI18n: () => ({ t: key => key, locale: { value: 'en' } }),
    getSimulationHistory: async () => { if (unavailable) throw new Error('offline'); return { data: [] } },
  })
  vm.runInContext(`${source}\nglobalThis.subject = { loadHistory, error, loading, projects };`, context)
  const c = context.subject
  await c.loadHistory()
  assert.equal(c.error.value, true)
  assert.equal(c.loading.value, false)
  unavailable = false
  await c.loadHistory()
  assert.equal(c.error.value, false)
  assert.equal(c.projects.value.length, 0)
})
