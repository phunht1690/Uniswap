const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Element {
  constructor(id,value=''){Object.assign(this,{id,value,textContent:'',innerHTML:'',className:'',hidden:false,disabled:false,dataset:{},attributes:{},listeners:{},options:[],open:false});}
  addEventListener(name,fn){(this.listeners[name]??=[]).push(fn);}
  dispatch(name,event={}){for(const fn of this.listeners[name]||[])fn({preventDefault(){},...event});if(this['on'+name])this['on'+name](event);}
  click(){if(!this.disabled)this.dispatch('click');}
  setAttribute(name,value){this.attributes[name]=String(value);}
  getAttribute(name){return this.attributes[name]??null;}
  replaceChildren(){this.options=[];this.value='';}
  add(option){this.options.push(option);if(this.value==='')this.value=option.value;}
  focus(){this.focused=true;}
  select(){this.selected=true;}
}
function createHarness(file,{protocol='file:',hash='',fetchImpl,clipboard}={}){
  const html=fs.readFileSync(file,'utf8'),elements=new Map();
  for(const match of html.matchAll(/<[A-Za-z][^>]*\bid="([^"]+)"[^>]*>/g)){const el=new Element(match[1],/\bvalue="([^"]*)"/.exec(match[0])?.[1]??'');el.hidden=/\bhidden(?:\s|>)/.test(match[0]);elements.set(el.id,el);}
  for(const match of html.matchAll(/<select[^>]*\bid="([^"]+)"[^>]*>([\s\S]*?)<\/select>/g)){
    const options=[...match[2].matchAll(/<option\b([^>]*)>([\s\S]*?)<\/option>/g)],selected=options.find(option=>/\bselected\b/.test(option[1]))||options[0];
    if(selected)elements.get(match[1]).value=/value="([^"]*)"/.exec(selected[1])[1];
    elements.get(match[1]).options=options.map(option=>({value:/value="([^"]*)"/.exec(option[1])[1]}));
  }
  elements.get('nPaths').value='10'; // UI contracts; numerical parity is tested independently.
  const root=new Element('root'),storage=new Map(),timers=new Map();let nextTimer=1,time=0;
  const context=vm.createContext({document:{getElementById:id=>{assert.ok(elements.has(id),'Missing DOM element '+id);return elements.get(id);},documentElement:root},
    Option:function(text,value){this.text=text;this.value=value;},location:{protocol,hash},window:{matchMedia:()=>({matches:false})},navigator:{clipboard},
    localStorage:{getItem:key=>storage.get(key)||null,setItem:(key,value)=>storage.set(key,value)},AbortController,URLSearchParams,console,
    setTimeout:(fn,delay)=>{const id=nextTimer++;timers.set(id,{fn,due:time+delay});return id;},clearTimeout:id=>timers.delete(id),
    fetch:fetchImpl||(()=>{throw new Error('Offline dashboard must not call network');})});
  for(const script of html.matchAll(/<script>([\s\S]*?)<\/script>/g))new vm.Script(script[1],{filename:file}).runInContext(context,{timeout:20000});
  const settle=async()=>{for(let i=0;i<40;i++)await Promise.resolve();};
  const advance=async ms=>{const end=time+ms;while(true){const due=[...timers].filter(([,timer])=>timer.due<=end).sort((a,b)=>a[1].due-b[1].due)[0];if(!due)break;time=due[1].due;timers.delete(due[0]);due[1].fn();await settle();}time=end;await settle();};
  return {elements,root,context,settle,advance,input:(id,value)=>{const el=elements.get(id);el.value=String(value);el.dispatch(id==='pool'?'change':'input');},click:id=>elements.get(id).click()};
}
function response(payload,status=200){return {ok:status>=200&&status<300,status,json:async()=>payload};}
function apiPool(){return {id:'weth-usdc-500',label:'WETH/USDC 0.05%',base:'WETH',quote:'USDC',p0:2468.5,fee_rate:.0005,fee_tier:500,tvl_usd:82e6,volume_24h_usd:40e6,
  vol_assumption_annual:.36,vol_realized_7d:.32,vol_realized_30d:.36,block_number:123,data_asof:'2026-10-20T15:00:00Z',history_start:'2025-10-22T00:00:00Z',history_end:'2026-10-20T00:00:00Z'};}
function apiResult(config,{excess=.123,infeasible=false,label}={}){
  const pool=apiPool(),metrics={half_width:.2,p_low:pool.p0*Math.exp(-.2),p_high:pool.p0*Math.exp(.2),active_share:.333,fees:.14,il:.01,gas:.007,net:.133,excess_vs_hodl:excess,q5:-.02,exit_prob:.2,rebalance_cost:0,rebalance_count:0,feasible:true};
  return {optimum:infeasible?null:metrics,sweep:[{...metrics,half_width:.1},{...metrics,half_width:.2}],
    strategies:['full','fixed','vol_scaled','dynamic',...(infeasible?[]:['optimizer'])].map(id=>({...metrics,id,label:label||id})),
    sample_paths:[Array.from({length:config.horizon_days+1},(_,i)=>pool.p0*(1+i/10000))],
    pnl_path:infeasible?[]:Array.from({length:config.horizon_days+1},(_,day)=>({day,lp:.133*day/config.horizon_days,hodl:.01*day/config.horizon_days})),
    stress:infeasible?[]:[{shock:-.3,lp_return:-.1,hodl_return:-.15,excess_vs_hodl:.05}],
    liquidity_ticks:[{tick:-10,price:2400,liquidity:1e8},{tick:0,price:2450,liquidity:1.1e8},{tick:10,price:2500,liquidity:1e8}],
    meta:{run_id:'a'.repeat(64),data_kind:'observed_snapshot',data_asof:pool.data_asof,messages:[],assumptions:{pool,effective_config:{...config,calibration_asof:'2026-10-20T15:10:00Z'},implemented_price_model:config.price_model,effective_vol_annual_for_width:config.vol_annual}}};
}
module.exports={createHarness,response,apiPool,apiResult};
