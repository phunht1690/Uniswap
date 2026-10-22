const test=require('node:test'),assert=require('node:assert/strict');
const view=require('../frontend/stress-view.js');
const response=(scenario,lp,hodl,gas=30)=>({scenario,metrics:{lp_value:lp,hodl_value:hodl,gas:gas/10000}});

test('selected shock and gas responses update the main chart; fixed presets stay cached',async()=>{
 const calls=[],runId='a'.repeat(64);
 const requests=[{price_shock_pct:-20,volatility_multiplier:1.7,gas_multiplier:2.1},{price_shock_pct:-20,volatility_multiplier:1.7,gas_multiplier:4.1},{price_shock_pct:40,volatility_multiplier:1.7,gas_multiplier:4.1}];
 const snapshots=[{lp:8912.34,hodl:9000,gas:63},{lp:8852.34,hodl:9000,gas:123},{lp:11920.55,hodl:12000,gas:123}];
 const load=view.createLoader(async request=>{
  calls.push({...request});
  const i=requests.findIndex(r=>Object.entries(r).every(([k,v])=>request[k]===v));
  const x=i<0?{lp:8000,hodl:8500,gas:30}:snapshots[i];return response(request,x.lp,x.hodl,x.gas);
 },runId);
 let fixed=null,previous='';
 for(let i=0;i<requests.length;i++){
  const result=await load(requests[i]);assert.deepEqual(result.current.scenario,{...requests[i],run_id:runId});
  const html=view.current(result.current,10000);assert.ok(html.includes(`data-value="${snapshots[i].lp}"`));assert.ok(html.includes(`data-value="${snapshots[i].hodl}"`));assert.notEqual(html,previous);
  const reference=view.reference(result.references,10000);if(fixed!==null)assert.equal(reference,fixed);fixed=reference;previous=html;
 }
 assert.equal(calls.length,8); // three selected requests plus five reference requests, once.
 assert.equal(calls.filter(r=>r.price_shock_pct===-30&&r.volatility_multiplier===1.5&&r.gas_multiplier===2).length,1);
});

test('failed references cannot block the selected graph and can be retried',async()=>{
 let fail=true;const load=view.createLoader(async req=>{if(req.price_shock_pct===30&&fail){fail=false;throw Error('offline');}return response(req,9000,8500);},'b'.repeat(64));
 const req={price_shock_pct:-25,volatility_multiplier:1,gas_multiplier:1};
 const first=await load(req);assert.equal(first.references,null);assert.equal(first.referenceError,'offline');assert.ok(view.current(first.current,10000).includes('data-value="9000"'));
 const result=await load(req);assert.equal(result.references.length,5);assert.equal(result.current.scenario.price_shock_pct,-25);assert.equal(req.run_id,undefined);
});

test('a flat model response stays flat; signed wealth uses a zero baseline',()=>{
 const a=response({price_shock_pct:0,volatility_multiplier:1,gas_multiplier:0},10000,10000,0),b=response({...a.scenario,gas_multiplier:4},10000,10000,0);
 const extract=html=>[...html.matchAll(/data-value="([^"]+)"/g)].map(m=>Number(m[1]));
 assert.deepEqual(extract(view.current(a,10000)),extract(view.current(b,10000)));
 const signed=view.current(response(a.scenario,-100,10000),10000);assert.ok(!/NaN|Infinity/.test(signed));assert.ok(signed.includes('data-value="-100"'));
});
