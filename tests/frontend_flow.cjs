const assert=require('node:assert/strict');
const {createHarness,response,apiPool,apiResult}=require('./frontend_harness.cjs');
(async()=>{
  const requests=[],pending=[];let broken=false,hold=false,infeasible=false,copied='',backtestMode='error';
  const app=createHarness(process.argv[2],{protocol:'http:',clipboard:{writeText:async text=>{copied=text;}},fetchImpl:async(url,options)=>{
    requests.push({url,options});
    if(url==='/api/v1/pools')return response({pools:[apiPool()],data_kind:'observed_snapshot'});
    if(url.startsWith('/api/v1/backtest/')){
      if(backtestMode==='error')return response({detail:'Thiếu TVL lịch sử.'},400);
      return response({status:backtestMode==='infeasible'?'infeasible':'ok',returns_unit:'fraction_of_initial_capital',
        equity_curve:backtestMode==='infeasible'?[]:[{timestamp:'2025-11-22T00:00:00Z',lp:-.0003,hodl:0},{timestamp:'2026-10-20T00:00:00Z',lp:.07,hodl:.02}],
        summary:{net:.07,excess_vs_hodl:.05,fees:.09,il:.03,gas:.01,rebalance_cost:0,active_share:.8,rebalance_count:2},
        meta:{run_id:'c'.repeat(64),data_kind:'historical_replay_modelled_fees',effective_start:'2025-11-22',effective_end:'2026-10-20',partial_period:true,assumptions:{concentration:3}}});
    }
    if(url==='/api/v1/research/status')return response({research_id:'d'.repeat(64),status:{pool_count:8,panel_rows:440,panel_time_windows:11},files:[{name:'regressions.csv',kind:'csv'},{name:'equity_curves.png',kind:'png'},{name:'../secret',kind:'json'}]});
    if(broken)throw new Error('Failed to fetch');
    const config=JSON.parse(options.body);if(hold)return new Promise(resolve=>pending.push({resolve,config}));
    return response(apiResult(config,{infeasible}));
  }});await app.settle();
  assert.match(app.elements.get('modeLabel').textContent,/dữ liệu quan sát/);assert.equal(app.elements.get('kEx').textContent,'+12.3%');assert.equal(app.elements.get('kAct').textContent,'33.3%');
  assert.match(app.elements.get('tickCaption').textContent,/block 123/);assert.doesNotMatch(app.elements.get('tickCaption').textContent,/Gaussian/);
  app.click('copyConfig');await app.settle();assert.equal(JSON.parse(copied).run_id,'a'.repeat(64));assert.equal(JSON.parse(copied).config.calibration_asof,'2026-10-20T15:10:00Z');
  const count=()=>requests.filter(request=>request.url==='/api/v1/simulate').length,initial=count();
  app.input('hor',70);app.input('hor',75);app.input('hor',80);await app.advance(299);assert.equal(count(),initial);await app.advance(1);assert.equal(count(),initial+1);
  assert.equal(JSON.parse(requests.filter(request=>request.url==='/api/v1/simulate').at(-1).options.body).horizon_days,80);
  hold=true;app.input('hor',90);await app.advance(300);app.input('hor',100);await app.advance(300);
  pending[1].resolve(response(apiResult(pending[1].config,{excess:.222})));await app.settle();pending[0].resolve(response(apiResult(pending[0].config,{excess:.999})));await app.settle();assert.equal(app.elements.get('kEx').textContent,'+22.2%');
  hold=false;broken=true;app.input('gas',20);await app.advance(300);assert.match(app.elements.get('modeLabel').textContent,/JavaScript/);assert.match(app.elements.get('apiStageStatus').textContent,/Failed to fetch/);
  assert.equal(JSON.parse(app.elements.get('configText').value).engine,'javascript_offline');assert.doesNotMatch(app.elements.get('dataAsOf').textContent,/2026/);
  broken=false;app.click('apiStageRetry');await app.settle();assert.match(app.elements.get('modeLabel').textContent,/dữ liệu quan sát/);
  infeasible=true;app.input('risk',.15);await app.advance(300);assert.match(app.elements.get('kRange').textContent,/Không có range khả thi/);assert.equal(app.elements.get('kNet').textContent,'—');assert.match(app.elements.get('cPnl').innerHTML,/Không có range/);
  app.click('tabBacktest');app.click('loadBacktest');await app.settle();assert.match(app.elements.get('btStatus').textContent,/Thiếu TVL/);assert.equal(app.elements.get('backtestChart').innerHTML,'');
  assert.ok(requests.some(request=>request.url.includes('/backtest/weth-usdc-500?start=2025-10-22&end=2026-10-20&strategy=fixed')));
  backtestMode='ok';app.click('loadBacktest');await app.settle();assert.match(app.elements.get('backtestChart').innerHTML,/<svg/);assert.match(app.elements.get('btStatus').textContent,/ước tính.*TVL/);assert.match(app.elements.get('btStatus').textContent,/giới hạn/);
  assert.equal(app.elements.get('downloadBacktestCsv').hidden,false);assert.match(app.elements.get('downloadBacktestCsv').href,/c{64}\/curve.csv/);assert.match(app.elements.get('backtestSummary').innerHTML,/\+7.0%/);
  app.input('gas',25);assert.equal(app.elements.get('backtestChart').innerHTML,'');assert.equal(app.elements.get('downloadBacktestCsv').hidden,true);await app.advance(300);
  backtestMode='infeasible';app.click('loadBacktest');await app.settle();assert.match(app.elements.get('btStatus').textContent,/Không có range khả thi/);assert.equal(app.elements.get('backtestChart').innerHTML,'');
  app.click('loadResearch');await app.settle();assert.match(app.elements.get('researchStatus').textContent,/8 pool.*440/);assert.match(app.elements.get('researchFiles').innerHTML,/regressions.csv/);assert.doesNotMatch(app.elements.get('researchFiles').innerHTML,/secret/);
  const calls=requests.length;app.input('cap',0);await app.advance(300);assert.equal(requests.length,calls);assert.match(app.elements.get('calculationStatus').textContent,/Vốn USD/);
  const savedConfig={pool:'weth-usdc-500',capital:60000,horizon_days:220,vol_annual:.345,gas_usd:56,risk_max_exit_prob:.35,min_rebalance_gap_days:9,price_model:'garch',n_paths:40,seed:123,path_index:12,max_rebalances:20,rebalance_slippage_bps:4,min_half_width:.02,max_half_width:.8,calibration_asof:'2026-10-20T15:10:00Z',bootstrap_mean_block_days:15};
  let restoredPost;
  const restored=createHarness(process.argv[2],{protocol:'http:',hash:'#run='+'b'.repeat(64),fetchImpl:async(url,options)=>{
    if(url.startsWith('/api/v1/runs/'))return response({config:savedConfig,result:apiResult(savedConfig)});
    if(url==='/api/v1/pools')return response({pools:[apiPool()],data_kind:'observed_snapshot'});
    restoredPost=JSON.parse(options.body);return response(apiResult(restoredPost));
  }});await restored.settle();
  assert.deepEqual(restoredPost,savedConfig);assert.equal(restored.elements.get('hor').value,220);assert.equal(restored.elements.get('hor').max,220);
  assert.equal(restored.elements.get('priceModel').value,'garch');assert.match(restored.elements.get('restoreStatus').textContent,/Đã nạp cấu hình/);
  assert.ok(restored.elements.get('risk').options.some(option=>option.value==='0.35'));assert.ok(restored.elements.get('reb').options.some(option=>option.value==='9'));
  const beforeInvalid=restoredPost;restored.input('savedRunId','invalid');restored.click('loadSavedRun');await restored.settle();assert.equal(restoredPost,beforeInvalid);assert.match(restored.elements.get('restoreStatus').textContent,/64 ký tự/);
  console.log('PASS: API/debounce/stale responses, fallback, copy/restore, historical replay labels and charts, costs, infeasibility, downloads and research manifest.');
})().catch(error=>{console.error(error);process.exitCode=1;});
