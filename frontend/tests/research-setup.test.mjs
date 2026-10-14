import test from 'node:test'
import assert from 'node:assert/strict'
import { validateSetup, startIntent, reviewLocation, tokenRange } from '../src/utils/researchSetup.js'

const chosen={provider:'codex',model:null,concurrency:2,depth:'quick',platform:'reddit'}
test('invalid concurrency and empty custom model cannot start',()=>{
  assert.equal(validateSetup(chosen),null)
  assert.equal(validateSetup({...chosen,concurrency:9}),'concurrency')
  assert.equal(validateSetup({...chosen,concurrency:2.5}),'concurrency')
  assert.equal(validateSetup({...chosen,model:'   '}),'model')
})
test('lost start responses retain the original key and payload on retry',()=>{
  const records=new Map();const storage={getItem:k=>records.get(k),setItem:(k,v)=>records.set(k,v)}
  const first=startIntent(storage,'draft-a',{settings:chosen},()=> 'one-key')
  const retry=startIntent(storage,'draft-a',{settings:{...chosen,model:'changed'}},()=> 'second-key')
  assert.equal(retry.key,'one-key')
  assert.deepEqual(retry.payload,first.payload)
})
test('legacy browser starts route to review with their exact IDs',()=>{
  assert.deepEqual(reviewLocation({code:'review_required',review:{project_id:'proj_a',simulation_id:'sim_b'}}),
    {name:'ResearchReview',query:{project_id:'proj_a',simulation_id:'sim_b'}})
  assert.deepEqual(reviewLocation({code:'run_active',run_id:'run_a'}),{name:'ResearchRun',params:{runId:'run_a'}})
  assert.equal(reviewLocation({error:'other'}),null)
})
test('token range exposes both bounds without pretending to be a bill',()=>{
  assert.equal(tokenRange({lower:160000,upper:450000},'en'),'160K–450K')
  assert.equal(tokenRange(null,'en'),'—')
})
