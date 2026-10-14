export function validateSetup(value) {
  if (!Number.isInteger(value.concurrency) || value.concurrency < 1 || value.concurrency > 8) return 'concurrency'
  if (value.model !== null && (typeof value.model !== 'string' || !value.model.trim() || value.model.length > 200 || /[\x00-\x1f]/.test(value.model))) return 'model'
  if (!['quick', 'moderate', 'full'].includes(value.depth)) return 'depth'
  if (!['reddit', 'twitter', 'parallel'].includes(value.platform)) return 'platform'
  return null
}
export function startIntent(storage, scope, payload, uuid = () => crypto.randomUUID()) {
  const key = `research-start:${scope}`
  const saved = storage.getItem(key)
  if (saved) return JSON.parse(saved)
  const intent = { key: uuid(), payload: JSON.parse(JSON.stringify(payload)) }
  storage.setItem(key, JSON.stringify(intent))
  return intent
}
export function reviewLocation(data) {
  if (data?.code === 'run_active') return { name: 'ResearchRun', params: { runId: data.run_id } }
  if (data?.code !== 'review_required') return null
  return { name: 'ResearchReview', query: Object.fromEntries(Object.entries(data.review || {}).filter(([, value]) => value)) }
}
export function tokenRange(estimate, locale = 'en') {
  if (!estimate) return '—'
  const format = new Intl.NumberFormat(locale, { notation: 'compact', maximumFractionDigits: 1 })
  return `${format.format(estimate.lower)}–${format.format(estimate.upper)}`
}
