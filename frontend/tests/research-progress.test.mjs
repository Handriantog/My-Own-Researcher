import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import vm from 'node:vm'
import { createRunObserver, stageProgress } from '../src/utils/researchProgress.js'

function runPage(mocks = {}) {
  const setup = readFileSync(new URL('../src/views/ResearchRun.vue', import.meta.url), 'utf8')
    .match(/<script setup>([\s\S]*?)<\/script>/)[1]
    .replace(/^import[^\n]+$/gm, '')
  const timers = new Map()
  let timerId = 0
  const context = vm.createContext({
    ref: value => ({ value }), computed: getter => ({ get value() { return getter() } }),
    watch() {}, onMounted() {}, onUnmounted() {}, nextTick: fn => fn?.(),
    useI18n: () => ({ t: key => key, locale: { value: 'en' } }),
    useRoute: () => ({ params: { runId: 'run_a' } }),
    setTimeout: fn => { timers.set(++timerId, fn); return timerId },
    clearTimeout: id => timers.delete(id), setInterval() {}, clearInterval() {},
    service: { async get() { throw Error('Unexpected request') } },
    createRunObserver, stageProgress, ...mocks,
  })
  vm.runInContext(`${setup}\nglobalThis.subject = { run, detail, detailErrors, graphData, refresh, refreshDetails, control };`, context)
  return { ...context.subject, timers }
}
const settle = () => new Promise(resolve => setImmediate(resolve))
const state = status => ({ run_id: 'run_a', stage: 'graph', status, completed_stages: ['analysis'] })

test('a temporary detail failure preserves the last measured progress with an error indicator', async () => {
  let reads = 0
  const page = runPage({ createRunObserver: () => ({ async read() {
    return ++reads === 1
      ? { stage: 'simulation', simulation: { current_round: 7, total_rounds: 12 }, errors: [], graph: null }
      : { stage: 'simulation', errors: ['Request timeout'], graph: null }
  } }) })
  page.run.value = { ...state('running'), stage: 'simulation' }
  await page.refreshDetails()
  await page.refreshDetails()
  assert.equal(page.detail.value.simulation?.current_round, 7)
  assert.match(page.detailErrors.value.join(' '), /timeout/)
})

test('resume invalidates an older status read and queues a fresh poll', async () => {
  let release, reads = 0
  const page = runPage({
    getResearch: async () => ++reads === 1 ? new Promise(resolve => { release = resolve }) : { data: state('running') },
    controlResearch: async () => ({ data: state('running') }),
  })
  page.run.value = state('failed')
  const old = page.refresh()
  await page.control('resume')
  assert.equal(page.run.value.status, 'running')
  release({ data: state('failed') })
  await old; await settle()
  assert.equal(page.run.value.status, 'running')
  assert.equal(reads, 2)
  assert.equal(page.timers.size, 1, 'Resumed work continues polling')
})

test('a terminal transition fetches the final graph even within the refresh throttle', async () => {
  let status = 'running', graphReads = 0
  const page = runPage({
    getResearch: async () => ({ data: { ...state(status), project_id: 'proj_a' } }),
    service: { async get(url) {
      if (url.endsWith('/project/proj_a')) return { data: { graph_id: 'graph_a' } }
      if (url.endsWith('/data/graph_a')) return { data: { nodes: Array.from({ length: ++graphReads }, (_, i) => ({ uuid: String(i) })), edges: [] } }
      throw Error(`Unexpected endpoint: ${url}`)
    } },
  })
  await page.refresh(); await settle()
  status = 'completed'
  await page.refresh(); await settle()
  assert.equal(page.graphData.value.nodes.length, 2)
  assert.equal(page.timers.size, 0)
})

test('a terminal transition during a detail read gets a final snapshot before going idle', async () => {
  let release
  const reads = []
  const page = runPage({ createRunObserver: () => ({ async read(run, options) {
    reads.push({ run, options })
    const value = { stage: run.stage, graph: null, errors: [] }
    if (reads.length === 1) return new Promise(resolve => { release = () => resolve(value) })
    return value
  } }) })
  page.run.value = state('running')
  const pending = page.refreshDetails()
  page.run.value = state('completed')
  await page.refreshDetails(true)
  release(); await pending; await settle()
  assert.equal(reads.length, 2)
  assert.equal(reads[1].run.status, 'completed')
  assert.equal(reads[1].options.forceGraph, true)
})

async function subject() {
  const file = new URL('../src/utils/researchProgress.js', import.meta.url)
  assert.ok(existsSync(file), 'Run progress must expose live observation without launching work')
  return import(file)
}

test('stage bars use measured progress and never carry another stage percentage forward', async () => {
  const { stageProgress } = await subject()
  const run = { stage: 'graph', status: 'running', completed_stages: ['analysis'] }
  assert.equal(stageProgress('analysis', run, {}), 100)
  assert.equal(stageProgress('preparation', run, {}), 0)
  assert.equal(stageProgress('graph', run, {}), null)
  assert.equal(stageProgress('graph', run, { stage: 'graph', task: { progress: 73 } }), 73)
  assert.equal(stageProgress('graph', run, { stage: 'preparation', task: { progress: 100 } }), null)
  assert.equal(stageProgress('simulation', { ...run, stage: 'simulation' }, { stage: 'simulation', simulation: { current_round: 3, total_rounds: 12 } }), 25)
  assert.equal(stageProgress('memory', { ...run, stage: 'memory' }, { stage: 'memory', simulation: { current_round: 12, total_rounds: 12 } }), null)
  assert.equal(stageProgress('memory', { ...run, stage: 'memory' }, { stage: 'memory', memory: { percent: 25 } }), 25)
  assert.equal(stageProgress('memory', { ...run, stage: 'memory' }, { stage: 'memory', memory: { percent: null } }), null)
})

test('saving observation reads batch progress without writes and keeps it through a connection loss', async () => {
  let now = 0, failed = false, reads = 0
  const client = { async get(url) {
    if (url.endsWith('/memory-progress')) {
      reads++
      if (failed) throw Error('Graph temporarily unavailable')
      return { data: { total: 24, completed: 6, processing: 1, queued: 17, percent: 25 } }
    }
    if (url.endsWith('/run-status')) return { data: { simulation_completed: true } }
    if (url.endsWith('/actions')) return { data: { actions: [] } }
    throw Error(`Unexpected read: ${url}`)
  } }
  const observer = createRunObserver(client, () => now)
  const run = { run_id: 'run_a', stage: 'memory', simulation_id: 'sim_a' }
  assert.equal((await observer.read(run)).memory.completed, 6)
  now = 2000
  await observer.read(run)
  assert.equal(reads, 1, 'Batch reads are throttled independently from status polling')
  now = 6000; failed = true
  const result = await observer.read(run)
  assert.equal(result.memory.completed, 6)
  assert.match(result.errors.join(' '), /temporarily unavailable/)
})

test('observing a graph reads project, task and graph and retains data during a failed refresh', async () => {
  const { createRunObserver } = await subject()
  let clock = 0, failGraph = false
  const calls = []
  const graph = { nodes: [{ uuid: 'one' }], edges: [] }
  const client = { async get(url) {
    calls.push(url)
    if (url === '/api/graph/project/proj_a') return { data: { graph_id: 'graph_a', graph_build_task_id: 'task_a' } }
    if (url === '/api/graph/task/task_a') return { data: { progress: 73, message: '13/25 done' } }
    if (url === '/api/graph/data/graph_a') { if (failGraph) throw Error('Connection lost'); return { data: graph } }
    throw Error(`Unexpected endpoint: ${url}`)
  } }
  const observer = createRunObserver(client, () => clock)
  const run = { run_id: 'run_a', stage: 'graph', project_id: 'proj_a' }
  const first = await observer.read(run)
  assert.equal(first.task.progress, 73)
  assert.deepEqual(first.graph, graph)
  assert.deepEqual(first.errors, [])
  clock = 2000
  await observer.read(run)
  assert.equal(calls.filter(url => url.includes('/data/')).length, 1)
  clock = 11000; failGraph = true
  const failed = await observer.read(run)
  assert.deepEqual(failed.graph, graph)
  assert.match(failed.errors.join(' '), /Connection lost/)
  assert.equal(calls.some(url => /start|build|resume|prepare/.test(url)), false)
})

test('preparation and reporting observation uses GET endpoints and returns real activity', async () => {
  const { createRunObserver } = await subject()
  const routes = {
    '/api/simulation/sim_a': { profiles_count: 2, entities_count: 6 },
    '/api/simulation/sim_a/config/realtime': { generation_stage: 'generating_profiles' },
    '/api/report/report_a/progress': { progress: 45, message: 'Writing findings' },
    '/api/report/report_a/console-log': { logs: ['Found 3 relevant facts'], total_lines: 1 },
  }
  const client = { async get(url) { assert.ok(url in routes, `Unexpected endpoint: ${url}`); return { data: routes[url] } } }
  const observer = createRunObserver(client)
  const setup = await observer.read({ run_id: 'run_a', stage: 'preparation', simulation_id: 'sim_a', stage_progress: { status: 'processing', progress: 35 } })
  assert.equal(setup.preparation.profiles_count, 2)
  assert.equal(setup.preparation.progress, 35)
  const report = await observer.read({ run_id: 'run_a', stage: 'report', report_id: 'report_a' })
  assert.equal(report.report.progress, 45)
  assert.deepEqual(report.reportLogs, ['Found 3 relevant facts'])
})

test('switching runs cannot reuse another run graph or let a late response replace it', async () => {
  const { createRunObserver } = await subject()
  let release
  const client = { async get(url) {
    if (url.endsWith('/proj_old')) return new Promise(resolve => { release = resolve })
    throw Error(`Unexpected endpoint: ${url}`)
  } }
  const observer = createRunObserver(client)
  const old = observer.read({ run_id: 'old', stage: 'graph', project_id: 'proj_old' })
  const current = await observer.read({ run_id: 'new', stage: 'analysis' })
  release({ data: { graph_id: 'old_graph' } })
  await old
  const fresh = await observer.read({ run_id: 'new', stage: 'analysis' })
  assert.equal(current.graph, null)
  assert.equal(fresh.graph, null)
  assert.deepEqual(fresh.errors, [])
})
