const percent = value => typeof value === 'number' && Number.isFinite(value) ? Math.max(0, Math.min(100, Math.round(value))) : null

export function stageProgress(stage, run, detail) {
  if (run.completed_stages?.includes(stage)) return 100
  if (run.stage !== stage) return 0
  if (detail.stage !== stage) return null
  if (stage === 'graph') return percent(detail.task?.progress)
  if (stage === 'preparation') return percent(detail.preparation?.progress)
  if (stage === 'report') return percent(detail.report?.progress)
  if (stage === 'memory') return percent(detail.memory?.percent)
  if (stage === 'simulation' && detail.simulation?.total_rounds > 0) {
    return percent((detail.simulation.current_round || 0) / detail.simulation.total_rounds * 100)
  }
  return null
}

// Observation is deliberately separate from the components that start or resume
// work. Only GET requests are available here; visiting a run cannot launch work.
export function createRunObserver(client, now = Date.now) {
  let cache = null
  return {
    async read(run, { forceGraph = false } = {}) {
      if (cache?.id !== run.run_id) cache = { id: run.run_id, graph: null, graphAt: -Infinity, graphId: null, reportLine: 0, memory: null, memoryAt: -Infinity, memoryError: null }
      const owner = cache
      const result = { stage: run.stage, graph: owner.graph, errors: [] }
      const get = async (url, options = {}) => (await client.get(url, { timeout: 8000, ...options })).data
      const capture = async operation => {
        try { await operation() } catch (error) { result.errors.push(error.message) }
      }
      const jobs = []
      if (run.project_id) jobs.push(capture(async () => {
        const project = await get(`/api/graph/project/${run.project_id}`)
        if (cache !== owner) return
        result.project = project
        const reads = []
        if (run.stage === 'graph' && project.graph_build_task_id) reads.push(capture(async () => {
          result.task = await get(`/api/graph/task/${project.graph_build_task_id}`)
        }))
        if (project.graph_id && (forceGraph || project.graph_id !== owner.graphId || now() - owner.graphAt >= 10000)) reads.push(capture(async () => {
          const graph = await get(`/api/graph/data/${project.graph_id}`)
          if (cache !== owner) return
          // Keep the same object while unchanged, so the graph doesn't reset on every poll.
          if (JSON.stringify(graph) !== JSON.stringify(owner.graph)) owner.graph = graph
          owner.graphId = project.graph_id
          owner.graphAt = now()
          result.graph = owner.graph
        }))
        await Promise.all(reads)
      }))
      if (run.stage === 'preparation' && run.simulation_id) {
        jobs.push(capture(async () => {
          const state = await get(`/api/simulation/${run.simulation_id}`)
          const progress = run.stage_progress || {}
          result.preparation = { ...state, progress: ['processing', 'ready', 'not_started', 'completed'].includes(progress.status) ? percent(progress.progress) : null, message: progress.message }
        }))
        jobs.push(capture(async () => { result.config = await get(`/api/simulation/${run.simulation_id}/config/realtime`) }))
      }
      if (['simulation', 'memory'].includes(run.stage) && run.simulation_id) {
        jobs.push(capture(async () => { result.simulation = await get(`/api/simulation/${run.simulation_id}/run-status`) }))
        jobs.push(capture(async () => { result.actions = (await get(`/api/simulation/${run.simulation_id}/actions`, { params: { limit: 40 } })).actions || [] }))
      }
      if (run.stage === 'memory' && run.simulation_id) jobs.push((async () => {
        if (forceGraph || now() - owner.memoryAt >= 5000) {
          owner.memoryAt = now()
          try {
            const progress = await get(`/api/simulation/${run.simulation_id}/memory-progress`)
            if (cache !== owner) return
            owner.memory = progress
            owner.memoryError = null
          } catch (error) { owner.memoryError = error.message }
        }
        result.memory = owner.memory
        if (owner.memoryError) result.errors.push(owner.memoryError)
      })())
      if (run.report_id) {
        jobs.push(capture(async () => { result.report = await get(`/api/report/${run.report_id}/progress`) }))
        jobs.push(capture(async () => {
          const log = await get(`/api/report/${run.report_id}/console-log`, { params: { from_line: owner.reportLine } })
          result.reportLogs = log.logs || []
          if (cache === owner) owner.reportLine = log.total_lines || owner.reportLine
        }))
      }
      await Promise.all(jobs)
      return result
    },
  }
}
