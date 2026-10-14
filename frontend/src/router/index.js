import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Process from '../views/MainView.vue'
import SimulationView from '../views/SimulationView.vue'
import SimulationRunView from '../views/SimulationRunView.vue'
import ReportView from '../views/ReportView.vue'
import InteractionView from '../views/InteractionView.vue'

const routes = [
  { path: '/research', name: 'Workspace', component: () => import('../views/Workspace.vue') },
  { path: '/research/review', name: 'ResearchReview', component: () => import('../views/ResearchReview.vue') },
  { path: '/research/runs/:runId', name: 'ResearchRun', component: () => import('../views/ResearchRun.vue') },
  {
    path: '/demo',
    name: 'Demo',
    component: () => import('../views/DemoView.vue')
  },
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/process/:projectId',
    name: 'Process',
    component: Process,
    props: true
  },
  {
    path: '/simulation/:simulationId',
    name: 'Simulation',
    component: SimulationView,
    props: true
  },
  {
    path: '/simulation/:simulationId/start',
    name: 'SimulationRun',
    component: SimulationRunView,
    props: true
  },
  {
    path: '/report/:reportId',
    name: 'Report',
    component: ReportView,
    props: true
  },
  {
    path: '/interaction/:reportId',
    name: 'Interaction',
    component: InteractionView,
    props: true
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.path === '/' && to.hash === '#how-it-works') return { el: '#how-it-works' }
    if (to.path !== from.path) return { top: 0 }
  }
})

// Preserve bookmarks and links from older versions of the homepage.
router.beforeEach(to => {
  if (to.path === '/' && to.hash === '#research') {
    return { path: '/research', query: to.query, replace: true }
  }
})

export default router
