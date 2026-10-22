/* Keep the supplied five shells and design tokens; compile all assets locally. */
const fs=require('fs'),path=require('path'),cp=require('child_process'),cheerio=require('cheerio'),crypto=require('crypto');
const dest=path.resolve(__dirname,'../dashboard/rangelab');fs.mkdirSync(path.join(dest,'assets'),{recursive:true});
const source=fs.readFileSync(path.join(__dirname,'templates/overview.html'),'utf8');
// Parse the template's object literal as data; never execute supplied scripts.
const literal=cheerio.load(source)('#tailwind-config').text().trim().replace(/^tailwind\.config\s*=\s*/,'').replace(/;\s*$/,'').replace(/([{,])\s*([A-Za-z_][\w-]*)\s*:/g,'$1"$2":');
const config={...JSON.parse(literal),content:[path.join(__dirname,'templates/*.html'),path.join(__dirname,'app.js')],plugins:[]};
// Content identity invalidates browser caches when locally installed assets change.
const assetVersion=crypto.createHash('sha256').update(['app.js','motion.js','stress-view.js','guide.js','glossary.js','app.css','motion.css','tailwind-input.css','package-lock.json',...fs.readdirSync(path.join(__dirname,'templates')).filter(name=>name.endsWith('.html')).sort().map(name=>'templates/'+name)].map(name=>fs.readFileSync(path.join(__dirname,name),'utf8')).join('\n')).digest('hex').slice(0,16);
// Serialize plugin separately (functions cannot be JSON serialized).
fs.writeFileSync(path.join(__dirname,'tailwind.config.cjs'),'module.exports='+JSON.stringify({...config,plugins:[]},null,2)+';module.exports.plugins=[require("@tailwindcss/forms")];\n');
const labels={'overview':'Tổng quan','lp-optimizer':'Tìm khoảng giá LP','optimization-results':'Kết quả tối ưu hóa','strategy-backtesting':'Thử chiến lược trong quá khứ','risk-and-research':'Kiểm tra rủi ro & dữ liệu'};
for(const [page,label] of Object.entries(labels)){
 const $=cheerio.load(fs.readFileSync(path.join(__dirname,'templates',page+'.html'),'utf8'));
 $('script,head link,head style').remove();$('title').remove();
 $('head').append(`<title>${label} · RangeLab</title><meta name="description" content="Uniswap LP Optimizer - nghiên cứu thanh khoản Uniswap v3 với dữ liệu quan sát, mô phỏng và historical replay."/><link rel="icon" href="/dashboard/rangelab/assets/favicon.svg"/><link rel="stylesheet" href="/dashboard/rangelab/assets/tailwind.css?v=${assetVersion}"/><link rel="stylesheet" href="/dashboard/rangelab/assets/fonts/material.css"/><link rel="stylesheet" href="/dashboard/rangelab/assets/app.css?v=${assetVersion}"/><link rel="stylesheet" href="/dashboard/rangelab/assets/motion.css?v=${assetVersion}"/><script defer src="/dashboard/rangelab/assets/motion.js?v=${assetVersion}"></script><script defer src="/dashboard/rangelab/assets/stress-view.js?v=${assetVersion}"></script><script defer src="/dashboard/rangelab/assets/guide.js?v=${assetVersion}"></script><script defer src="/dashboard/rangelab/assets/glossary.js?v=${assetVersion}"></script><script defer src="/dashboard/rangelab/assets/app.js?v=${assetVersion}"></script>`);
 $('*').each((i,e)=>{for(const key of Object.keys(e.attribs||{}))if(key.startsWith('on'))$(e).removeAttr(key);});
 $('body').attr('data-page',page);
 $('[data-path]').each((i,e)=>{const link=$(e),key=link.attr('data-path');link.attr('href','/'+key);if(labels[key])link.children('span').not('.material-symbols-outlined').last().text(labels[key]);});
 $('aside').attr('id','sidebar');
 $('aside span').filter((i,e)=>$(e).text().trim()==='60 fps').attr('id','api-state').text('API…');
 $('aside span').filter((i,e)=>$(e).text().trim()==='Mô phỏng đang hoạt động').text('Bộ mô phỏng');
 $('aside>div').last().prepend('<a id="news-shortcut" class="news-shortcut" href="/risk-and-research?tab=news"><span class="material-symbols-outlined">newspaper</span><span>Tin tức & cộng đồng</span></a>');
 $('header').html(`<div class="header-title"><button id="menu-toggle" class="icon-btn" type="button" aria-label="Mở menu" aria-expanded="false"><span class="material-symbols-outlined">menu</span></button><span class="material-symbols-outlined">domain</span><span>RangeLab</span><span>›</span><b>${label}</b></div><div class="header-tools"><span id="header-pool" class="badge mono">Đang tải cặp thanh khoản</span><span id="header-asof" class="badge">Ngày dữ liệu</span><span class="badge teal">● Lịch sử & Mô phỏng</span><button id="glossary-btn" class="btn small" type="button"><span class="material-symbols-outlined">help</span>Thuật ngữ</button><button id="workspace-info" class="btn small info-button" aria-label="Thông tin và hướng dẫn sử dụng dashboard" title="Thông tin và hướng dẫn sử dụng" type="button"><span class="material-symbols-outlined">info</span><span>Thông tin</span></button></div>`);
 $('main').attr('id','main').html('<section id="market-live-panel" class="card live-panel" aria-label="Thị trường đang theo dõi"></section><div id="page-content" class="page-stack" aria-busy="true"><section class="card loading-state"><span class="spinner"></span><h1>Đang mở RangeLab</h1><p>Đọc danh sách pool và dữ liệu quan sát…</p></section></div><div id="page-error" class="error-box" role="alert" hidden></div>');
 $('footer').html('<div class="footer-inner"><span>△ Công cụ mô phỏng nghiên cứu — không phải lời khuyên đầu tư.</span><span id="footer-meta" class="mono">RPC · GeckoTerminal · DefiLlama</span></div>');
 $('body').append('<div id="toast" role="status" hidden></div><dialog id="modal"><div class="modal-head"><h2 id="modal-title"></h2><button id="modal-close" class="icon-btn" aria-label="Đóng" type="button">✕</button></div><div id="modal-body"></div></dialog>');
 $('.material-symbols-outlined').attr('aria-hidden','true');
 fs.writeFileSync(path.join(dest,page+'.html'),$.html());
}
for(const name of ['app.js','motion.js','stress-view.js','guide.js','glossary.js','app.css','motion.css'])fs.copyFileSync(path.join(__dirname,name),path.join(dest,'assets',name));
fs.writeFileSync(path.join(dest,'assets/favicon.svg'),'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40"><rect width="40" height="40" rx="10" fill="#7c3aed"/><path d="M15 9h10m-7 0v10l-7 12h18l-7-12V9M15 25h10" stroke="white" stroke-width="2" fill="none"/></svg>');
cp.execFileSync(process.execPath,[require.resolve('tailwindcss/lib/cli.js'),'-c',path.join(__dirname,'tailwind.config.cjs'),'-i',path.join(__dirname,'tailwind-input.css'),'-o',path.join(dest,'assets/tailwind.css'),'--minify'],{stdio:'inherit'});
console.log('Built 5 RangeLab pages with local assets.');
