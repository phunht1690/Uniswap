/* Archive evidence and current strategy rules are deliberately kept distinct. */
(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.RangeLabResearch=factory();})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const num=(value,d=2)=>value==null||!Number.isFinite(Number(value))?'—':Number(value).toLocaleString('vi-VN',{minimumFractionDigits:d,maximumFractionDigits:d});
 const pct=value=>value==null?'—':num(value*100)+'%';
 const pp=value=>value==null?'—':(value>=0?'+':'')+num(value*100)+' điểm %';
 const labels={full:'Toàn dải',fixed:'Khoảng cố định',vol_scaled:'Theo biến động',dynamic:'Khoảng động',optimizer:'Tối ưu tại thời điểm mở',hodl:'Giữ token HODL'};
 const table=(headers,rows)=>`<div class="table-wrap"><table><thead><tr>${headers.map(h=>`<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map(cell=>`<td>${cell}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
 function modeFor(result){return result?.meta?.strategy_mode||result?.meta?.effective_config?.strategy_mode||'weekly';}
 function strategyDescription(id,config={}){
  const research=config.strategy_mode==='research',window=config.volatility_window_days??14;
  return {full:'Giữ vị thế toàn dải đến cuối kỳ.',fixed:`Giữ nửa độ rộng w = ${num(config.half_width??.15)} log; không dời khoảng.`,
   vol_scaled:research?`Tính độ rộng từ biến động ${window} ngày trước entry; giữ nguyên đến cuối kỳ.`:`Biến động trễ ${window} ngày; cập nhật độ rộng và tâm khoảng hằng tuần.`,
   dynamic:research?'Giữ độ rộng lúc mở; chỉ xét dời tâm sau khi giá ra ngoài khoảng.':'Giữ độ rộng lúc mở; xét dời tâm hằng tuần.',
   optimizer:'Chọn độ rộng bằng mô phỏng trước entry; không dùng giá tương lai để chọn.',hodl:'Giữ số token ban đầu, không tính phí giao dịch LP.'}[id]||'';
 }
 function strategyLabel(id,config={}){
  const research=config.strategy_mode==='research';
  if(id==='dynamic')return research?'Động khi ra ngoài khoảng':'Động hằng tuần';
  if(id==='vol_scaled')return research?'Theo biến động lúc mở':'Theo biến động cập nhật tuần';
  return labels[id]||id;
 }
 function savedStrategy(result,id){
  const row=result?.strategies?.find(s=>s.id===id),config={...result?.meta?.effective_config,strategy_mode:modeFor(result)};
  return {label:row?.label||strategyLabel(id,config),description:strategyDescription(id,config),rules:row?.rules||result?.meta?.strategy_rules?.[id]};
 }
 function profileTable(presets){
  return table(['Thông số','Nghiên cứu lưu trữ','Biến thể hằng tuần'],[
   ['Khoảng cố định',`w = ${num(presets.research.config.half_width)} log`,`w = ${num(presets.weekly.config.half_width)} log`],
   ['Cửa sổ biến động',`${presets.research.config.volatility_window_days} ngày`,`${presets.weekly.config.volatility_window_days} ngày`],
   ['Khoảng động','Dời tâm khi ra ngoài khoảng','Dời tâm hằng tuần'],
   ['Theo biến động','Giữ độ rộng tính tại entry','Cập nhật độ rộng hằng tuần']
  ]);
 }
 function resultConfiguration(result){
  const c=result.meta.effective_config,mode=modeFor(result),legacy=!c.strategy_mode,assessment=result.meta.configuration_profile;
  const custom=assessment?.matches_preset===false,title=custom?'Tham số tùy chỉnh':assessment?.label||(mode==='research'?'Quy tắc nghiên cứu':'Quy tắc hằng tuần');
  return `<div class="row between wrap"><h3>Cấu hình của kết quả đang hiển thị</h3><span class="badge ${!custom&&mode==='research'?'teal':''}">${esc(title)}${legacy?' · bản đã lưu cũ':''}</span></div><p class="small-text">Khoảng cố định w = <b>${num(c.half_width)} log</b> · cửa sổ biến động <b>${c.volatility_window_days} ngày</b> · vốn <b>${num(c.capital)} USD</b> · gas <b>${num(c.gas_usd)} USD/đơn vị</b>. Quy tắc khoảng động: <b>${mode==='research'?'khi ra ngoài khoảng':'hằng tuần'}</b>. ${esc(custom?'Các tham số không khớp trọn bộ cấu hình chuẩn.':assessment?.description||'Kết quả giữ nguyên quy tắc và đầu vào của lần chạy đã lưu.')}</p><div class="code-line">${esc(result.meta.model_version)} · ${esc(result.meta.run_id)}</div><a class="news-external" href="/api/v1/backtests/comparisons/${esc(result.meta.run_id)}" target="_blank" rel="noopener">Xem cấu hình đầy đủ và kết quả JSON</a>`;
 }
 function evidence(data){
  const full=data.full_period,gas=data.gas_evidence,window=data.optimizer_window,cost=full.costs,profile=data.archive_profile;
  const strategyRows=full.strategies.map(s=>[esc(s.label||labels[s.id]||s.id),pct(s.median.excess_vs_hodl),pct(s.median.fees),pct(s.median.il),pct(s.median.gas),pct(s.median.rebalance_cost),esc(s.median.rebalance_count)]);
  const medianRows=full.strategies.map(s=>[esc(s.label||labels[s.id]||s.id),pp(s.cost_from_independent_medians),pct(s.median_paired_cost)]);
  return `<div class="row between wrap"><div><h2>Nghiên cứu lưu trữ và quy tắc đang chạy</h2><p class="small-text">Các số dưới đây được đọc từ tệp nghiên cứu đã kiểm tra hash; chúng giữ nguyên kỳ dữ liệu và cách tổng hợp của nghiên cứu.</p></div><a class="btn small" href="/api/v1/research/reconciliation" target="_blank" rel="noopener">Xem dữ liệu đối chiếu JSON</a></div>
   <p class="small-text"><b>${esc(data.archive_version)}</b> · ${full.pool_count} pool · ${full.rows_count} kết quả toàn kỳ · w cố định ${num(profile.fixed_half_width)} · biến động ${profile.volatility_window_days} ngày. Khoảng động dời khi ra ngoài; chiến lược theo biến động giữ độ rộng tại entry.</p>
   <div class="grid3"><section class="note"><div class="label">TOÀN KỲ THEO POOL</div><h3>${pp(full.optimizer_minus_fixed_medians)}</h3><p class="small-text">Trung vị ΔR optimizer trừ trung vị ΔR fixed. Khác đại lượng trung bình ghép cặp theo cửa sổ bên cạnh.</p></section><section class="note"><div class="label">CỬA SỔ GHÉP CẶP ${window.holding_days} NGÀY</div><h3>${pp(window.mean_optimizer_minus_fixed)}</h3><p class="small-text">Trung bình optimizer − fixed; CI thăm dò 95% từ ${pp(window.ci95_low)} đến ${pp(window.ci95_high)}. ${window.paired_pool_windows} cặp pool và cửa sổ; ${window.time_windows} cửa sổ thời gian. Đây là chênh lệch ΔR, không phải lợi nhuận bảo đảm.</p></section><section class="note"><div class="label">ĐÁNH ĐỔI GAS H4</div><h3>${gas.informative?'Xem phạm vi phát sinh tái cân bằng':'Chưa đủ bằng chứng'}</h3><p class="small-text">${esc(gas.interpretation)}</p></section></div>
   <p class="small-text gap-top">Hai kết quả optimizer đo khác chân trời và cách tổng hợp, nên có thể trái dấu mà không mâu thuẫn. Bootstrap dùng ${window.repetitions} lần lấy mẫu, khối ${window.circular_block_windows} cửa sổ; chưa xác nhận hiệu quả ngoài mẫu hoặc nhân quả.</p>
   <details class="details"><summary>Chênh lệch LP với HODL và chi phí thực trong từng kết quả</summary><div>${table(['Chiến lược','Trung vị ΔR','Trung vị phí','Trung vị IL dương','Gas','Trượt giá','Số lần dời'],strategyRows)}<p class="small-text gap-top">Chi phí lấy trực tiếp từ từng hàng: gas ${pct(cost.gas_min)} đến ${pct(cost.gas_max)} vốn; trượt giá ${pct(cost.slippage_min)} đến ${pct(cost.slippage_max)}. ${cost.zero_rebalance_rows}/${full.rows_count} kết quả không dời khoảng. Sai số phân rã lớn nhất ${num(cost.max_abs_accounting_residual,12)} theo tỷ lệ vốn.</p>${table(['Chiến lược','Phần dư từ các trung vị độc lập','Trung vị chi phí ghép theo hàng'],medianRows)}<p class="small-text gap-top">Không dùng median(phí) − median(IL) − median(ΔR) để suy ra chi phí: các trung vị có thể đến từ những hàng khác nhau. Kiểm tra đúng là phí − IL − gas − trượt giá − ΔR trên từng hàng.</p></div></details>
   <details class="details"><summary>Phạm vi bằng chứng và điều kiện tái lập</summary><div class="stack">${data.claims.map(claim=>`<p class="small-text"><b>${esc(claim.id)}:</b> ${esc(claim.message)}</p>`).join('')}<p class="small-text">${data.limitations.map(esc).join(' ')}</p><p class="tiny mono break-all">Research ID: ${esc(data.research_id)}</p></div></details>
   <div class="row wrap gap-top"><a class="btn primary" href="/strategy-backtesting?profile=research">Chạy theo cấu hình nghiên cứu</a><a class="btn" href="/strategy-backtesting?profile=weekly">Thử biến thể hằng tuần</a></div>`;
 }
 function reproduction(record){
  const id=record?.result?.meta?.run_id;
  const code=id?`$saved = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/v1/workbench/runs/${id}'\n$body = $saved.config | ConvertTo-Json -Depth 20\n$run = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/v1/workbench/run' -ContentType 'application/json' -Body $body\n$run.meta.run_id -eq $saved.result.meta.run_id`:`$body = @{\n  config = @{ pool = 'weth-usdc-500'; capital = 50000; horizon_days = 30; n_paths = 300; seed = 42; price_model = 'gbm'; vol_annual = 0.65 }\n  rebalance_policy = 'none'\n  volume_daily_override_usd = $null\n  market_snapshot_id = $null\n} | ConvertTo-Json -Depth 20\n$run = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/v1/workbench/run' -ContentType 'application/json' -Body $body`;
  return `<h2>Tái lập đúng phiên bản và công thức</h2><p class="small-text">Giao diện tối ưu hóa dùng <b>/api/v1/workbench/run</b>; yêu cầu có đối tượng <b>config</b> lồng bên trong. API /simulate thuộc engine cũ và không thay thế lần chạy workbench, backtest hay toàn bộ nghiên cứu.</p>${table(['Lớp kết quả','API','Phiên bản'],[['Engine gốc giữ tương thích','POST /simulate','stage4-observed-inputs-v2'],['Mô phỏng trên giao diện','POST /workbench/run','rangelab-workbench-v3'],['So sánh quá khứ','POST /backtests/compare','Phiên bản ghi trong kết quả'],['Nghiên cứu lưu trữ','GET /research/reconciliation','Phiên bản và research ID của archive']])}<details class="details"><summary>${id?'Lệnh tái lập đúng kết quả đang xem':'Ví dụ tạo một lần chạy workbench'}</summary><pre class="research-code">${esc(code)}</pre><p class="small-text">Gửi lại nguyên cấu hình hiệu lực đã lưu; giữ cùng dữ liệu, snapshot và môi trường. Không chụp snapshot mới khi mục tiêu là tái lập cùng run. Ví dụ này không tự tái lập báo cáo 8 pool hoặc kết quả backtest.</p></details><p class="small-text gap-top">Với K là vốn, F là phí, G là gas, C là ma sát và H là PnL phòng hộ: <b>R_LP = (V_inventory + F − G − C + H) / K − 1</b>. Nếu IL_loss = V_HODL − V_inventory là phần thiếu hụt dương thì <b>ΔR = (F − IL_loss − G − C + H) / K</b>. Policy không phòng hộ có H = 0; không trừ IL thêm lần nữa khỏi V_inventory.</p>`;
 }
 return {modeFor,strategyLabel,strategyDescription,savedStrategy,profileTable,resultConfiguration,evidence,reproduction};
});
