/* Saved-result rules, archive statistics and workbench replay stay separate. */
const test=require('node:test'),assert=require('node:assert/strict');
const view=require('../frontend/research-view.js');

const freeze=value=>{if(value&&typeof value==='object'){Object.values(value).forEach(freeze);Object.freeze(value);}return value;};
const plain=html=>html.replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim();
const code=html=>{
 const match=html.match(/<pre class="research-code">([\s\S]*?)<\/pre>/);assert.ok(match);
 return match[1].replace(/&#39;/g,"'").replace(/&quot;/g,'"').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&');
};
function evidenceFixture(){
 return {
  research_id:'a'.repeat(64),archive_version:'stage5-descriptive-research-v2',
  archive_profile:{fixed_half_width:.2,volatility_window_days:30},
  full_period:{pool_count:8,rows_count:40,optimizer_minus_fixed_medians:-.0498,
   strategies:[{id:'fixed',label:'Khoảng cố định lưu trữ',median:{excess_vs_hodl:.2124,fees:.2306,il:.0165,gas:.0006,rebalance_cost:0,rebalance_count:0},
    cost_from_independent_medians:.0017,median_paired_cost:.0006}],
   costs:{gas_min:.0006,gas_max:.0006,gas_percent_min:.06,gas_percent_max:.06,slippage_min:0,slippage_max:0,
    slippage_percent_min:0,slippage_percent_max:0,zero_rebalance_rows:40,max_abs_accounting_residual:3.8e-12}},
  gas_evidence:{rows:72,gain_zero_rows:72,extra_gas_zero_rows:72,break_even_defined_rows:0,informative:false,status:'no_rebalance_events',
   interpretation:'Lợi ích trước gas và gas tăng thêm đều bằng 0. Ngưỡng hòa vốn không xác định, không phải 0 USD.'},
  optimizer_window:{holding_days:30,mean_optimizer_minus_fixed:.0148,ci95_low:.0094,ci95_high:.0204,paired_pool_windows:88,
   time_windows:11,repetitions:999,circular_block_windows:2,status:'exploratory_model_conditional',not_confirmatory_OOS:true},
  claims:[{id:'H4',message:'Không phát sinh dời khoảng nên chưa kiểm tra được đánh đổi.'}],
  limitations:['Phí mô hình hóa; chưa xác nhận ngoài mẫu.'],
 };
}
function oldResult(){
 return {meta:{model_version:'rangelab-comparison-v1',run_id:'b'.repeat(64),effective_config:{half_width:.15,volatility_window_days:14,capital:50000,gas_usd:15}},
  strategies:[{id:'dynamic',label:'Tái cân bằng hàng tuần',rules:{rebalance:'weekly'}},{id:'vol_scaled',label:'Volatility rolling 14 ngày · cập nhật tuần'}]};
}

test('old comparison V1 without a mode remains weekly and keeps its saved labels',()=>{
 const result=freeze(oldResult());
 assert.equal(view.modeFor(result),'weekly');assert.equal(view.modeFor(undefined),'weekly');
 const saved=view.savedStrategy(result,'dynamic');
 assert.equal(saved.label,'Tái cân bằng hàng tuần');assert.match(saved.description,/hằng tuần/);
 assert.equal(saved.rules.rebalance,'weekly');
 // Choosing a research label for an edit form cannot rewrite the immutable saved result.
 assert.equal(view.strategyLabel('dynamic',{strategy_mode:'research'}),'Động khi ra ngoài khoảng');
 assert.deepEqual(view.savedStrategy(result,'dynamic'),saved);
 const html=view.resultConfiguration(result);
 assert.match(html,/rangelab-comparison-v1/);assert.match(html,/bản đã lưu cũ/);
 assert.match(html,/0,15 log/);assert.match(html,/14 ngày/);assert.doesNotMatch(html,/Quy tắc nghiên cứu/);
});

test('research and weekly volatility descriptions describe different executable rules',()=>{
 const research={strategy_mode:'research',volatility_window_days:30,half_width:.2};
 const weekly={strategy_mode:'weekly',volatility_window_days:14,half_width:.15};
 assert.match(view.strategyDescription('vol_scaled',research),/30 ngày trước entry; giữ nguyên/);
 assert.doesNotMatch(view.strategyDescription('vol_scaled',research),/hằng tuần/);
 assert.match(view.strategyDescription('vol_scaled',weekly),/14 ngày; cập nhật độ rộng và tâm khoảng hằng tuần/);
 assert.match(view.strategyDescription('dynamic',research),/sau khi giá ra ngoài khoảng/);
 assert.match(view.strategyDescription('dynamic',weekly),/hằng tuần/);
 assert.equal(view.modeFor({meta:{effective_config:research}}),'research');
 const html=view.profileTable({research:{config:research},weekly:{config:weekly}});
 for(const expected of ['0,20 log','0,15 log','30 ngày','14 ngày','Giữ độ rộng tính tại entry','Cập nhật độ rộng hằng tuần'])assert.ok(html.includes(expected),expected);
});

test('custom numeric settings cannot be presented as a matched research preset',()=>{
 const result=oldResult();result.meta.model_version='rangelab-comparison-v2';
 result.meta.effective_config={strategy_mode:'research',half_width:.21,volatility_window_days:30,capital:12345,gas_usd:15};
 result.meta.configuration_profile={id:'custom',label:'Tham số tùy chỉnh',matches_preset:false,description:'Khớp quy tắc và tham số'};
 const text=plain(view.resultConfiguration(result));
 assert.match(text,/Tham số tùy chỉnh/);assert.match(text,/không khớp trọn bộ cấu hình chuẩn/);
 assert.match(text,/0,21 log/);assert.match(text,/12\.345,00 USD/);
 assert.doesNotMatch(text,/Khớp quy tắc và tham số/);
});

test('evidence distinguishes percentage-point differences from percentage costs and cites its archive',()=>{
 const data=freeze(evidenceFixture()),html=view.evidence(data),text=plain(html);
 assert.match(text,/stage5-descriptive-research-v2/);assert.ok(text.includes('Research ID: '+'a'.repeat(64)));
 assert.ok(text.includes('-4,98 điểm %'),'full-period median difference must retain its negative sign and pp unit');
 assert.ok(text.includes('+1,48 điểm %'),'paired mean must use percentage points');
 assert.ok(text.includes('+0,94 điểm %'));assert.ok(text.includes('+2,04 điểm %'));
 assert.ok(text.includes('0,06%'),'raw gas .0006 is .06 percent of capital');
 assert.ok(!text.includes('6,00%'),'do not multiply the already-percent convenience fields a second time');
 assert.match(text,/88 cặp pool và cửa sổ; 11 cửa sổ thời gian/);
 assert.match(text,/999 lần lấy mẫu, khối 2 cửa sổ/);
 assert.match(text,/khác chân trời và cách tổng hợp/);
});

test('a degenerate gas archive does not turn an undefined threshold into zero USD',()=>{
 const html=view.evidence(freeze(evidenceFixture())),text=plain(html);
 assert.match(text,/Chưa đủ bằng chứng/);
 assert.match(text,/Ngưỡng hòa vốn không xác định, không phải 0 USD/);
 assert.doesNotMatch(html,/<h3>0(?:,00)?\s*USD<\/h3>/);
 assert.match(text,/40\/40 kết quả không dời khoảng/);
 assert.match(text,/Không phát sinh dời khoảng nên chưa kiểm tra được đánh đổi/);
});

test('independent-median residual is displayed separately from paired row cost',()=>{
 const data=freeze(evidenceFixture()),html=view.evidence(data),text=plain(html);
 assert.ok(text.includes('+0,17 điểm %'));assert.ok(text.includes('0,06%'));
 assert.match(text,/Phần dư từ các trung vị độc lập/);
 assert.match(text,/Trung vị chi phí ghép theo hàng/);
 assert.match(text,/Không dùng median\(phí\) − median\(IL\) − median\(ΔR\) để suy ra chi phí/);
 assert.match(text,/phí − IL − gas − trượt giá − ΔR trên từng hàng/);
 assert.equal(data.full_period.strategies[0].median_paired_cost,.0006);
 assert.equal(data.full_period.strategies[0].cost_from_independent_medians,.0017);
});

test('saved workbench reproduction fetches and resends the entire nested effective request',()=>{
 const runId='c'.repeat(64),record=freeze({config:{config:{pool:'weth-usdc-500',seed:42},rebalance_policy:'hedged',market_snapshot_id:'d'.repeat(64)},result:{meta:{run_id:runId}}});
 const html=view.reproduction(record),script=code(html),text=plain(html);
 assert.ok(script.includes('/api/v1/workbench/runs/'+runId));
 assert.match(script,/\$body = \$saved\.config \| ConvertTo-Json -Depth 20/);
 assert.match(script,/Invoke-RestMethod -Method Post -Uri 'http:\/\/127\.0\.0\.1:8000\/api\/v1\/workbench\/run'/);
 assert.match(script,/-Body \$body/);assert.match(script,/\$run\.meta\.run_id -eq \$saved\.result\.meta\.run_id/);
 assert.doesNotMatch(script,/\/api\/v1\/simulate/);
 assert.match(text,/config lồng bên trong/);assert.match(text,/Không chụp snapshot mới/);
 assert.match(text,/R_LP = \(V_inventory \+ F − G − C \+ H\) \/ K − 1/);
 assert.match(text,/ΔR = \(F − IL_loss − G − C \+ H\) \/ K/);
 assert.match(text,/Policy không phòng hộ có H = 0/);
});

test('the new workbench example also uses a nested body and sufficient JSON depth',()=>{
 const script=code(view.reproduction(null));
 assert.match(script,/config = @\{/);assert.match(script,/rebalance_policy = 'none'/);
 assert.match(script,/market_snapshot_id = \$null/);assert.match(script,/ConvertTo-Json -Depth 20/);
 assert.match(script,/\/api\/v1\/workbench\/run/);assert.doesNotMatch(script,/\/api\/v1\/simulate/);
});

test('text from archives and saved records is escaped before entering generated HTML',()=>{
 const attack='</pre><img src=x onerror="alert(1)"><script>bad()</script>&';
 const data=evidenceFixture();data.archive_version=attack;data.research_id=attack;
 data.full_period.strategies[0].label=attack;data.gas_evidence.interpretation=attack;
 data.claims=[{id:attack,message:attack}];data.limitations=[attack];
 const html=view.evidence(freeze(data));
 assert.ok(html.includes('&lt;img src=x onerror=&quot;alert(1)&quot;&gt;'));
 assert.ok(html.includes('&lt;script&gt;bad()&lt;/script&gt;&amp;'));
 assert.doesNotMatch(html,/<img\b|<script\b/);
 const reproduction=view.reproduction({result:{meta:{run_id:attack}}});
 assert.doesNotMatch(reproduction,/<img\b|<script\b/);
 assert.ok(reproduction.includes('&lt;/pre&gt;'));
 const result=oldResult();result.meta.run_id=attack;result.meta.model_version=attack;result.meta.configuration_profile={description:attack};
 assert.doesNotMatch(view.resultConfiguration(result),/<img\b|<script\b/);
});
