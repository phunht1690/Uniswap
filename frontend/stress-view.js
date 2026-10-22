/* Shared browser/Node presenter: the selected stress response owns the main chart. */
(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.RangeLabStress=factory();})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const presets=[[-10,1.1,1.2],[-30,1.5,2],[30,1.4,1.8],[0,2.2,1.3],[-5,1,5.3]];
 const labels=['Giá −10%','Giá −30%','Giá +30%','Dao động 2,2×','Phí mạng 5,3×'];
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const money=v=>Number(v).toLocaleString('vi-VN',{minimumFractionDigits:2,maximumFractionDigits:2})+' USD';
 const number=v=>Number(v).toLocaleString('vi-VN',{maximumFractionDigits:1});
 function describe(s){return `Giá cuối kỳ ${s.price_shock_pct>=0?'+':''}${number(s.price_shock_pct)}% · Dao động ${number(s.volatility_multiplier)}× · Phí mạng ${number(s.gas_multiplier)}×`;}
 function createLoader(send,runId){
  let references=null;
  return async request=>{
   // Fixed reference scenarios are calculated once for this immutable saved run.
   const selected=send({...request,run_id:runId});
   if(!references)references=Promise.all(presets.map(([price_shock_pct,volatility_multiplier,gas_multiplier])=>send({run_id:runId,price_shock_pct,volatility_multiplier,gas_multiplier}))).catch(error=>{references=null;throw error;});
   const [current,referenceResult]=await Promise.all([selected,references.then(value=>({value}),error=>({error}))]);
   // Reference comparisons are optional: their failure must not hide a valid selected result.
   return {current,references:referenceResult.value||null,referenceError:referenceResult.error?.message||null};
  };
 }
 function svgChart(results,names,capital,current=false){
  const W=current?760:1000,H=300,L=90,R=20,T=35,B=45;
  const values=results.flatMap(r=>[r.metrics.lp_value,r.metrics.hodl_value]);
  const low=Math.min(0,...values),high=Math.max(capital,...values,1)*1.1,span=high-low;
  const y=v=>T+(high-v)/span*(H-T-B),zero=y(0),step=(W-L-R)/results.length;
  let svg=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${current?'Tài sản cuối kỳ của kịch bản vừa chạy':'So sánh năm kịch bản mẫu cố định'}">`;
  for(let i=0;i<5;i++){const v=low+span*i/4;svg+=`<line x1="${L}" x2="${W-R}" y1="${y(v)}" y2="${y(v)}" stroke="#e6e2f1"/><text x="${L-10}" y="${y(v)+4}" text-anchor="end">${esc(number(v))}</text>`;}
  results.forEach((r,i)=>{
   const center=L+step*(i+.5),bw=Math.min(current?110:32,step*.24),gap=current?16:5;
   [[-bw-gap/2,r.metrics.lp_value,'#630ed4','Cung cấp thanh khoản (LP)'],[gap/2,r.metrics.hodl_value,'#94a3b8','Giữ token (HODL)']].forEach(([offset,v,color,label])=>{
    svg+=`<rect data-series="${label.startsWith('Cung')?'lp':'hodl'}" data-value="${v}" x="${center+offset}" y="${Math.min(zero,y(v))}" width="${bw}" height="${Math.abs(zero-y(v))}" rx="3" fill="${color}"><title>${esc(names[i]+' · '+label+': '+money(v))}</title></rect>`;
    if(current)svg+=`<text x="${center+offset+bw/2}" y="${Math.min(zero,y(v))-10}" text-anchor="middle">${esc(money(v))}</text>`;
   });
   svg+=`<text x="${center}" y="${H-15}" text-anchor="middle">${esc(names[i])}</text>`;
  });
  return svg+'</svg><div class="chart-legend"><span><span class="legend-dot" style="background:#630ed4"></span>Cung cấp thanh khoản (LP)</span><span><span class="legend-dot" style="background:#94a3b8"></span>Giữ nguyên token (HODL)</span></div>';
 }
 function current(result,capital){
  const m=result.metrics;
  return `<div class="chart-stats mono" data-stress-scenario="${esc(JSON.stringify(result.scenario))}">${esc(describe(result.scenario))}</div>`+svgChart([result],['Kịch bản vừa chạy · USD'],capital,true)+`<div class="note gap-top"><b>LP ${m.lp_value>=m.hodl_value?'cao hơn':'thấp hơn'} giữ token ${money(Math.abs(m.lp_value-m.hodl_value))}.</b> Phí mạng trong kịch bản: ${money(m.gas*capital)}. Cột bắt đầu từ 0; thay đổi chi phí nhỏ có thể khó thấy, hãy đối chiếu số tiền trên cột.</div>`;
 }
 function reference(results,capital){
  return svgChart(results,labels,capital)+`<div class="table-wrap gap-top"><table><thead><tr><th>Kịch bản mẫu</th><th class="num">LP cuối kỳ</th><th class="num">Giữ token cuối kỳ</th></tr></thead><tbody>${results.map((r,i)=>`<tr><td>${labels[i]}</td><td class="num">${money(r.metrics.lp_value)}</td><td class="num">${money(r.metrics.hodl_value)}</td></tr>`).join('')}</tbody></table></div>`;
 }
 return {createLoader,current,reference,describe};
});
