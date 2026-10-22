/* Presentation only: never interpolate, replace or delay real financial values. */
(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.RangeLabMotion=factory().createController(root);})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 function createController(win){
  const doc=win.document,media=win.matchMedia?.('(prefers-reduced-motion: reduce)')||{matches:false};
  const ease='cubic-bezier(.22,1,.36,1)',values=new Map(),consumed=new WeakSet(),entries=new WeakSet();
  const active=new Set(),playing=new WeakMap(),pending=new Map(),roots=new Set(),observers=[],dirty=new Set();
  let frame=null,lastPanel=null,destroyed=false;
  const raf=win.requestAnimationFrame?.bind(win)||((fn)=>win.setTimeout(fn,16));
  const caf=win.cancelAnimationFrame?.bind(win)||win.clearTimeout?.bind(win);
  const numericSelector='[data-motion-number],.metric-value,.big-number,.strategy-return';
  const chartSelector='[data-motion-line],[data-motion-area],[data-motion-bar],.bar-fill,.cost-line>span,.range-fill';
  const select=(root,selector)=>[...(root?.matches?.(selector)?[root]:[]),...Array.from(root?.querySelectorAll?.(selector)||[])];
  const reduced=()=>media.matches||doc?.hidden||destroyed;
  function shown(el){
   if(!el||el.isConnected===false||el.closest?.('[hidden]')||el.closest?.('details:not([open])'))return false;
   const box=el.getBoundingClientRect?.();
   return !box||box.width>0&&box.height>0;
  }
  function inView(el){
   const box=el.getBoundingClientRect?.(),height=win.innerHeight||doc?.documentElement?.clientHeight;
   return !box||!height||box.bottom>0&&box.top<height;
  }
  function remove(record){active.delete(record);if(playing.get(record.el)===record)playing.delete(record.el);}
  function stop(record){try{record.animation.cancel();}catch{}remove(record);}
  function play(el,keyframes,options){
   if(reduced()||!shown(el)||typeof el.animate!=='function')return;
   if(playing.has(el))stop(playing.get(el));
   try{
    const animation=el.animate(keyframes,{easing:ease,fill:'none',...options}),record={el,animation};
    active.add(record);playing.set(el,record);
    if(animation.finished?.then)animation.finished.then(()=>remove(record),()=>remove(record));
    else animation.onfinish=()=>remove(record);
   }catch{} // A missing/unsupported animation feature must never hide data.
  }
  const intersection=typeof win.IntersectionObserver==='function'?new win.IntersectionObserver(records=>{
   for(const record of records)if(record.isIntersecting){
    const action=pending.get(record.target);
    if(action&&shown(record.target)){pending.delete(record.target);intersection.unobserve(record.target);action();}
   }
  },{threshold:.05}):null;
  function queue(el,action){
   if(!el||el.isConnected===false||destroyed)return;
   if(reduced()){pending.delete(el);intersection?.unobserve(el);action();return;}
   if(!shown(el)||intersection&&!inView(el)){
    pending.set(el,action);intersection?.observe(el);return;
   }
   pending.delete(el);intersection?.unobserve(el);action();
  }
  function remember(key,value){
   values.delete(key);values.set(key,value);
   if(values.size>512)values.delete(values.keys().next().value);
  }
  function number(el,key,value){
   const signature=String(value??el?.textContent??'').replace(/\s+/g,' ').trim();
   if(!/[0-9]/.test(signature))return;
   el?.classList?.add('rl-motion-number');
   if(values.get(key)===signature)return;
   queue(el,()=>{
    if(values.get(key)===signature)return;
    const updated=values.has(key);remember(key,signature);
    play(el,updated?[{backgroundColor:'rgba(124,58,237,.13)'},{backgroundColor:'transparent'}]:[{opacity:.65},{opacity:1}],
     {duration:updated?420:340,id:updated?'rl-number-update':'rl-number-enter'});
   });
  }
  function chart(root){
   for(const el of select(root,chartSelector)){
    if(consumed.has(el))continue;
    queue(el,()=>{
     if(consumed.has(el))return;consumed.add(el);
     let frames=[{opacity:.35},{opacity:1}],duration=420,id='rl-chart-fade';
     if(el.matches?.('[data-motion-line]')){
      // Keep HODL dashes and path gaps exactly as rendered by the chart.
      const dashed=el.getAttribute?.('stroke-dasharray');
      let length=0;try{length=el.getTotalLength?.()||0;}catch{}
      if((!dashed||dashed==='none')&&Number.isFinite(length)&&length>0){
       frames=[{strokeDasharray:`${length} ${length}`,strokeDashoffset:length},{strokeDasharray:`${length} ${length}`,strokeDashoffset:0}];
       duration=620;id='rl-chart-line';
      }
     }else if(el.matches?.('[data-motion-bar]')){
      const origin=Number(el.getAttribute?.('data-motion-origin-y'));
      if(Number.isFinite(origin))frames=[{transform:`translateY(${origin}px) scaleY(0) translateY(${-origin}px)`,transformOrigin:'0px 0px'},{transform:'none',transformOrigin:'0px 0px'}];
      duration=500;id='rl-chart-bar';
     }else if(!el.matches?.('[data-motion-area]')){
      frames=[{transform:'scaleX(0)',transformOrigin:'left center'},{transform:'none',transformOrigin:'left center'}];
      duration=500;id='rl-chart-bar';
     }
     play(el,frames,{duration,id});
    });
   }
  }
  function keyFor(el){
   if(el.getAttribute?.('data-motion-key'))return el.getAttribute('data-motion-key');
   if(el.id)return el.id;
   const card=el.closest?.('.metric-card,.stat-card,.range-quad>div')||el.parentElement;
   const label=card?.querySelector?.('.label')?.textContent||el.className||'value';
   const region=el.closest?.('[id]')?.id||'page';
   return region+':'+label;
  }
  function prune(){
   for(const record of active)if(record.el.isConnected===false||!shown(record.el))stop(record);
   for(const [el] of pending)if(el.isConnected===false){pending.delete(el);intersection?.unobserve(el);}
  }
  function scan(root){
   if(!root||destroyed)return;prune();
   for(const el of select(root,numericSelector))number(el,keyFor(el),el.getAttribute?.('data-motion-value')??el.textContent);
   chart(root);
  }
  function enter(root){
   const blocks=Array.from(root?.children||[]).flatMap(el=>el.matches?.('.grid3,.grid4,.grid6')?Array.from(el.children||[]):[el]);
   let index=0;
   for(const el of blocks){
    if(el.hidden||el.matches?.('.tab-panel,.loading-state')||entries.has(el))continue;
    const delay=Math.min(index++*35,140);entries.add(el);
    queue(el,()=>play(el,el.matches?.('.workspace-grid')?[{opacity:.7},{opacity:1}]:[{opacity:.7,transform:'translateY(7px)'},{opacity:1,transform:'none'}],{duration:280,delay,id:'rl-page-enter'}));
   }
   scan(root);
  }
  function tab(panel){
   if(lastPanel===panel){scan(panel);return;}
   if(lastPanel)for(const record of active)if(record.el===lastPanel||lastPanel.contains?.(record.el))stop(record);
   lastPanel=panel;
   if(panel)queue(panel,()=>play(panel,[{opacity:.65,transform:'translateY(5px)'},{opacity:1,transform:'none'}],{duration:200,id:'rl-tab-enter'}));
   scan(panel);
  }
  function schedule(root){
   if(!root||destroyed)return;dirty.add(root);
   if(frame!==null)return;
   frame=raf(()=>{frame=null;const batch=[...dirty];dirty.clear();for(const item of batch)if(item.isConnected!==false)scan(item);});
  }
  function observe(root){
   if(!root||roots.has(root)||destroyed)return;roots.add(root);
   if(typeof win.MutationObserver==='function'){
    const observer=new win.MutationObserver(records=>{
     let removed=false;
     for(const record of records){
      if(record.target.closest?.('.chart-tooltip'))continue;
      if(record.type==='attributes'){schedule(record.target);continue;}
      if(record.removedNodes?.length)removed=true;
      if(record.target.matches?.(numericSelector))schedule(record.target);
      for(const node of record.addedNodes||[])if(node.nodeType===1&&(node.matches?.(numericSelector+','+chartSelector)||node.querySelector?.(numericSelector+','+chartSelector)))schedule(node);
     }
     if(removed)prune();
    });
    observer.observe(root,{childList:true,subtree:true,attributes:true,attributeFilter:['hidden','open']});observers.push(observer);
   }
   scan(root);
  }
  function cancel(){
   if(frame!==null){caf?.(frame);frame=null;}dirty.clear();pending.clear();intersection?.disconnect();
   for(const record of [...active])stop(record);
  }
  const onReduce=()=>{if(media.matches)cancel();};
  const onVisibility=()=>{if(doc?.hidden)cancel();else for(const root of roots)scan(root);};
  const onPageShow=event=>{if(event.persisted)for(const root of roots)scan(root);};
  media.addEventListener?.('change',onReduce);if(!media.addEventListener)media.addListener?.(onReduce);
  doc?.addEventListener?.('visibilitychange',onVisibility);
  win.addEventListener?.('pagehide',cancel);win.addEventListener?.('pageshow',onPageShow);
  function destroy(){
   cancel();destroyed=true;for(const observer of observers)observer.disconnect();roots.clear();
   media.removeEventListener?.('change',onReduce);if(!media.removeEventListener)media.removeListener?.(onReduce);
   doc?.removeEventListener?.('visibilitychange',onVisibility);
   win.removeEventListener?.('pagehide',cancel);win.removeEventListener?.('pageshow',onPageShow);
  }
  return {number,chart,scan,tab,enter,observe,cancel,destroy};
 }
 return {createController};
});
