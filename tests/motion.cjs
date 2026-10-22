'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {createController}=require('../frontend/motion.js');

class Events {
 constructor(){this.listeners=new Map();}
 addEventListener(name,fn){if(!this.listeners.has(name))this.listeners.set(name,new Set());this.listeners.get(name).add(fn);}
 removeEventListener(name,fn){this.listeners.get(name)?.delete(fn);}
 emit(name,extra={}){for(const fn of [...(this.listeners.get(name)||[])])fn({type:name,target:this,...extra});}
}

class Element extends Events {
 constructor(doc,tag='div',attrs={},text=''){
  super();this.ownerDocument=doc;this.tagName=tag.toUpperCase();this.nodeType=1;this.attributes=new Map(Object.entries(attrs));this.dataset={};
  for(const [name,value] of Object.entries(attrs))if(name.startsWith('data-'))this.dataset[name.slice(5).replace(/-([a-z])/g,(_,c)=>c.toUpperCase())]=value;
  this.children=[];this.parentElement=null;this.isConnected=true;this.hidden=false;this.style={};this.text=text;this.textWrites=0;this.attributeWrites=[];this.animations=[];
  const classes=new Set((attrs.class||'').split(/\s+/).filter(Boolean));this.classList={contains:v=>classes.has(v),add:(...v)=>v.forEach(x=>classes.add(x)),remove:(...v)=>v.forEach(x=>classes.delete(x)),toggle:(v,state)=>{if(state??!classes.has(v))classes.add(v);else classes.delete(v);return classes.has(v);}};
 }
 get textContent(){return this.text;}
 set textContent(value){this.textWrites++;this.text=String(value);}
 get parentNode(){return this.parentElement;}
 get id(){return this.getAttribute('id')||'';}
 get offsetParent(){return this.visible()?this.parentElement||this.ownerDocument.body:null;}
 get childNodes(){return this.children;}
 get firstElementChild(){return this.children[0]||null;}
 append(...nodes){for(const node of nodes){node.parentElement=this;this.children.push(node);}}
 getAttribute(name){return this.attributes.get(name)??null;}
 hasAttribute(name){return this.attributes.has(name);}
 setAttribute(name,value){this.attributeWrites.push([name,String(value)]);this.attributes.set(name,String(value));}
 removeAttribute(name){this.attributeWrites.push([name,null]);this.attributes.delete(name);}
 contains(node){return node===this||this.children.some(child=>child.contains(node));}
 visible(){return this.isConnected&&!this.hidden&&!this.parentElement?.closest('[hidden]')&&!this.closest('details:not([open])');}
 getBoundingClientRect(){return {x:0,y:0,top:0,left:0,right:800,bottom:this.visible()?200:0,width:800,height:this.visible()?200:0};}
 getClientRects(){return this.visible()?[this.getBoundingClientRect()]:[];}
 getTotalLength(){return 260;}
 getBBox(){return {x:Number(this.getAttribute('x')||0),y:Number(this.getAttribute('y')||0),width:Number(this.getAttribute('width')||100),height:Number(this.getAttribute('height')||100)};}
 matches(selector){
  return selector.split(',').some(part=>{
   part=part.trim();
   if(part==='*')return true;
   if(part.includes('>')){const [parent,child]=part.split('>').map(v=>v.trim());return this.matches(child)&&!!this.parentElement?.matches(parent);}
   if(part==='details:not([open])')return this.tagName==='DETAILS'&&!this.hasAttribute('open');
   const tag=part.match(/^[\w-]+/)?.[0];if(tag&&tag.toUpperCase()!==this.tagName)return false;
   const id=part.match(/#([\w-]+)/)?.[1];if(id&&id!==this.id)return false;
   for(const cls of part.matchAll(/\.([\w-]+)/g))if(!this.classList.contains(cls[1]))return false;
   for(const attr of part.matchAll(/\[([^\]=]+)(?:=["']?([^\]"']+)["']?)?\]/g)){
    if(attr[1]==='hidden'){if(!this.hidden)return false;}
    else if(!this.hasAttribute(attr[1])||(attr[2]!==undefined&&this.getAttribute(attr[1])!==attr[2]))return false;
   }
   return !!(tag||id||part.includes('.')||part.includes('['));
  });
 }
 closest(selector){for(let node=this;node;node=node.parentElement)if(node.matches(selector))return node;return null;}
 querySelectorAll(selector){const result=[];for(const child of this.children){if(child.matches(selector))result.push(child);result.push(...child.querySelectorAll(selector));}return result;}
 querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
 animate(frames,options){
  let resolve;const animation={frames,options,cancelled:false,finished:new Promise(done=>{resolve=done;}),cancel(){this.cancelled=true;resolve();},finish(){resolve();}};
  this.animations.push(animation);this.ownerDocument.animations.push({element:this,animation});return animation;
 }
}

function environment({reduced=false,hidden=false,intersection=false,mutations=false}={}){
 const document=new Events();document.hidden=hidden;document.animations=[];document.documentElement=new Element(document,'html');document.body=new Element(document,'body');document.documentElement.append(document.body);
 document.querySelectorAll=selector=>document.documentElement.querySelectorAll(selector);document.querySelector=selector=>document.documentElement.querySelector(selector);document.contains=node=>document.documentElement.contains(node);
 const media=new Events();media.matches=reduced;media.addListener=fn=>media.addEventListener('change',fn);media.removeListener=fn=>media.removeEventListener('change',fn);
 const frames=new Map();let next=0;
 const win=new Events();Object.assign(win,{document,matchMedia:()=>media,requestAnimationFrame:fn=>{const id=++next;frames.set(id,fn);return id;},cancelAnimationFrame:id=>frames.delete(id),getComputedStyle:el=>({display:el.visible()?'block':'none',visibility:'visible',opacity:'1',transform:'none'}),setTimeout,clearTimeout});
 const intersections=[],observers=[];
 if(intersection){win.innerHeight=600;win.IntersectionObserver=class {
  constructor(callback){this.callback=callback;this.observed=new Set();this.disconnected=false;intersections.push(this);}
  observe(el){this.observed.add(el);this.disconnected=false;}
  unobserve(el){this.observed.delete(el);}
  disconnect(){this.observed.clear();this.disconnected=true;}
  emit(records){this.callback(records);}
 };}
 if(mutations)win.MutationObserver=class {
  constructor(callback){this.callback=callback;this.disconnected=false;observers.push(this);}
  observe(root,options){this.root=root;this.options=options;}
  disconnect(){this.disconnected=true;}
  emit(records){if(!this.disconnected)this.callback(records);}
 };
 const flush=()=>{for(let i=0;frames.size&&i<20;i++){const pending=[...frames];frames.clear();for(const [,fn] of pending)fn(i*16);}};
 const el=(tag='div',attrs={},text='')=>new Element(document,tag,attrs,text);
 const mount=node=>{document.body.append(node);return node;};
 return {win,document,media,el,mount,flush,frames,intersections,observers,all:()=>document.animations};
}

test('real numeric values are emphasized once per key and keep exact text and accessible labels',()=>{
 const env=environment(),motion=createController(env.win),first=env.mount(env.el('strong',{'aria-label':'Giá 2.465,6800 USDC'},'2.465,6800 USDC'));
 motion.number(first,'pool:weth-usdc:price',2465.68);env.flush();const initial=env.all().length;assert.ok(initial>0);
 motion.number(first,'pool:weth-usdc:price',2465.68);env.flush();assert.equal(env.all().length,initial);
 const replacement=env.mount(env.el('strong',{'aria-label':'Giá 2.465,6800 USDC'},'2.465,6800 USDC'));
 motion.number(replacement,'pool:weth-usdc:price',2465.68);env.flush();assert.equal(env.all().length,initial,'DOM replacement from polling must not imply changed data');
 replacement.text='2.465,6900 USDC';motion.number(replacement,'pool:weth-usdc:price',2465.69);env.flush();assert.ok(env.all().length>initial);
 assert.equal(first.textContent,'2.465,6800 USDC');assert.equal(replacement.textContent,'2.465,6900 USDC');
 assert.equal(first.textWrites+replacement.textWrites,0);assert.deepEqual(first.attributeWrites,[]);assert.deepEqual(replacement.attributeWrites,[]);motion.destroy();
});

test('hidden, disconnected, background and reduced-motion values stay readable without animation',()=>{
 for(const reason of ['hidden','disconnected','background','reduced']){
  const env=environment({hidden:reason==='background',reduced:reason==='reduced'}),motion=createController(env.win),root=env.mount(env.el()),value=env.el('div',{'aria-label':'Tài sản cuối kỳ'},'−1.234,56 USD');root.append(value);
  if(reason==='hidden')root.hidden=true;if(reason==='disconnected'){root.isConnected=false;value.isConnected=false;}
  motion.number(value,'value:'+reason,-1234.56);motion.enter(root);env.flush();assert.equal(env.all().length,0,reason);
  assert.equal(value.textContent,'−1.234,56 USD');assert.equal(value.textWrites,0);assert.equal(value.getAttribute('aria-label'),'Tài sản cuối kỳ');motion.destroy();
 }
});

test('changing the reduced-motion preference cancels active work and prevents queued playback',()=>{
 const env=environment(),motion=createController(env.win),value=env.mount(env.el('strong',{},'10.000 USD'));
 motion.number(value,'capital',10000);env.flush();assert.ok(env.all().length>0);
 const active=env.all().map(item=>item.animation);motion.number(value,'capital',10001);
 env.media.matches=true;env.media.emit('change',{matches:true});env.flush();assert.ok(active.every(animation=>animation.cancelled));
 const total=env.all().length;motion.number(value,'capital',10002);motion.enter(value);env.flush();assert.equal(env.all().length,total);
 assert.equal(value.textContent,'10.000 USD');assert.equal(value.textWrites,0);motion.destroy();
});

test('missing Web Animations API degrades to immediately readable final content',()=>{
 const env=environment(),motion=createController(env.win),root=env.mount(env.el()),value=env.el('div',{'class':'metric-value','aria-label':'Tỷ lệ âm'},'−2,50%');root.append(value);value.animate=undefined;root.animate=undefined;
 assert.doesNotThrow(()=>{motion.number(value,'return',-.025);motion.enter(root);motion.scan(root);motion.tab(root);env.flush();});
 assert.equal(env.all().length,0);assert.equal(value.textContent,'−2,50%');assert.equal(value.textWrites,0);assert.equal(value.getAttribute('aria-label'),'Tỷ lệ âm');assert.notEqual(value.style.opacity,'0');assert.notEqual(root.style.opacity,'0');motion.destroy();
});

test('chart animation touches marked data and bars while preserving axes, hit targets and dashed series',()=>{
 const env=environment(),motion=createController(env.win),root=env.mount(env.el('div',{'class':'chart'})),svg=env.el('svg');root.append(svg);
 const solid=env.el('path',{'data-motion-line':'','d':'M0,100L100,0','stroke':'#630ed4','fill':'none'}),dashed=env.el('path',{'data-motion-line':'','d':'M0,50L100,25','stroke':'#94a3b8','stroke-dasharray':'6 4','fill':'none'}),area=env.el('path',{'data-motion-area':'','d':'M0,100L100,0L100,100Z'}),column=env.el('rect',{'data-motion-bar':'','x':'10','y':'20','width':'20','height':'80','data-motion-origin-y':'100'});
 const axis=env.el('line',{'stroke-dasharray':'3 4'}),label=env.el('text',{},'10.000 USD'),crosshair=env.el('line',{'data-crosshair':'','visibility':'hidden'}),hit=env.el('rect',{'data-hit':'','fill':'transparent'}),band=env.el('rect',{'fill':'#bca5ed','opacity':'.15'});
 svg.append(solid,dashed,area,column,axis,label,crosshair,hit,band);
 const fill=env.el('div',{'class':'bar-fill'}),cost=env.el('div',{'class':'cost-line'}),costFill=env.el('span'),range=env.el('span',{'class':'range-fill'});cost.append(costFill);root.append(fill,cost,range);
 const marks=[solid,dashed,area,column,fill,costFill,range];motion.chart(root);env.flush();
 assert.ok(env.all().length>0);assert.ok(env.all().every(({element})=>marks.includes(element)),'chart chrome must remain stable');
 assert.ok(solid.animations.length>0);assert.ok(fill.animations.length>0);assert.ok(costFill.animations.length>0);assert.ok(range.animations.length>0);
 assert.ok(column.animations.length>0);assert.match(column.animations[0].frames[0].transform,/translateY\(100px\)/,'vertical bars must grow from their rendered baseline');
 assert.equal(dashed.getAttribute('stroke-dasharray'),'6 4');assert.equal(axis.getAttribute('stroke-dasharray'),'3 4');
 assert.ok(dashed.animations.every(animation=>animation.frames.every(frame=>!('strokeDasharray' in frame)&&!('strokeDashoffset' in frame))),'drawing must preserve the HODL dash pattern throughout playback');
 for(const el of [axis,label,crosshair,hit,band]){assert.equal(el.animations.length,0);assert.deepEqual(el.attributeWrites,[]);}
 assert.equal(label.textContent,'10.000 USD');assert.equal(label.textWrites,0);assert.equal(crosshair.getAttribute('visibility'),'hidden');motion.destroy();
});

test('backgrounding or leaving the page cancels active animations',()=>{
 for(const event of ['visibilitychange','pagehide']){
  const env=environment(),motion=createController(env.win),value=env.mount(env.el('strong',{},'2,50%'));motion.number(value,'yield',.025);env.flush();assert.ok(env.all().length>0);
  if(event==='visibilitychange'){env.document.hidden=true;env.document.emit(event);}else env.win.emit(event);
  env.flush();assert.ok(env.all().every(({animation})=>animation.cancelled),event);assert.equal(value.textContent,'2,50%');motion.destroy();
 }
});

test('reduced-motion changes clear offscreen observer queues before delayed intersection callbacks',()=>{
 const env=environment({intersection:true}),motion=createController(env.win),value=env.mount(env.el('strong',{},'4.000 USD'));
 value.getBoundingClientRect=()=>({width:100,height:20,top:900,bottom:920,left:0,right:100});
 motion.number(value,'offscreen',4000);const observer=env.intersections[0];assert.equal(env.all().length,0);assert.ok(observer.observed.has(value));
 env.media.matches=true;env.media.emit('change',{matches:true});assert.ok(observer.disconnected);assert.equal(observer.observed.size,0);
 env.media.matches=false;env.media.emit('change',{matches:false});observer.emit([{target:value,isIntersecting:true}]);env.flush();assert.equal(env.all().length,0,'a stale observer callback must not resurrect canceled presentation work');
 assert.equal(value.textContent,'4.000 USD');assert.equal(value.textWrites,0);motion.destroy();
});

test('closed details defer chart effects until opened and pointer tooltip mutations remain quiet',()=>{
 const env=environment({mutations:true}),motion=createController(env.win),root=env.mount(env.el()),details=env.el('details'),line=env.el('path',{'data-motion-line':'','d':'M0,20L100,5'}),tooltip=env.el('div',{'class':'chart-tooltip'});details.append(line);root.append(details,tooltip);
 motion.observe(root);assert.equal(env.all().length,0);const observer=env.observers[0];
 const tipValue=env.el('span',{'class':'metric-value'},'2.500,12 USD');tooltip.append(tipValue);observer.emit([{type:'childList',target:tooltip,addedNodes:[tipValue],removedNodes:[]}]);env.flush();assert.equal(env.all().length,0,'moving the chart pointer must not trigger reveal animations');
 details.setAttribute('open','');observer.emit([{type:'attributes',target:details,attributeName:'open'}]);env.flush();assert.equal(line.animations.length,1,'the hidden reference chart must animate when the reader opens it');
 const count=env.all().length;observer.emit([{type:'attributes',target:details,attributeName:'open'}]);env.flush();assert.equal(env.all().length,count,'repeated scans must not replay an already drawn chart');
 motion.destroy();assert.ok(observer.disconnected);assert.equal(line.getAttribute('d'),'M0,20L100,5');assert.equal(tipValue.textWrites,0);
});
