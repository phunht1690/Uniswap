const assert=require('node:assert/strict');
const {createHarness}=require('./frontend_harness.cjs');
(async()=>{
  const app=createHarness(process.argv[2]);await app.settle();
  for(const id of ['kRange','kAct','kNet','kEx'])assert.ok(app.elements.get(id).textContent&&!/NaN|Infinity/.test(app.elements.get(id).textContent),id);
  for(const id of ['cPnl','cSweep','cPath','cTick','tbl','stress'])assert.ok(app.elements.get(id).innerHTML.length>100&&!/NaN|Infinity/.test(app.elements.get(id).innerHTML),id);
  assert.match(app.elements.get('apiStageStatus').textContent,/Mở file cục bộ/);assert.match(app.elements.get('modeLabel').textContent,/Dữ liệu minh họa/);assert.equal(app.elements.get('apiStageDocs').hidden,true);
  const before=app.elements.get('cPnl').innerHTML;app.click('nextPath');await app.settle();assert.notEqual(app.elements.get('cPnl').innerHTML,before);
  app.input('vol',0);await app.advance(300);for(const id of ['cPnl','cPath','cSweep'])assert.ok(!/NaN|Infinity/.test(app.elements.get(id).innerHTML),id);
  app.click('copyConfig');await app.settle();assert.equal(app.elements.get('configDetails').open,true);assert.equal(app.elements.get('configText').selected,true);
  app.click('themeToggle');assert.equal(app.root.getAttribute('data-theme'),'dark');app.click('tabBacktest');assert.equal(app.elements.get('simulationPanel').hidden,true);
  app.click('loadBacktest');await app.settle();assert.equal(app.elements.get('backtestChart').innerHTML,'');
  console.log('PASS: file:// offline GBM, charts, path switching, zero volatility, copy fallback, theme/backtest state; zero network.');
})().catch(error=>{console.error(error);process.exitCode=1;});
