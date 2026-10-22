"""Printable, Unicode research summaries generated from saved results."""
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,KeepTogether


def pdf_bytes(record,methodology=False):
    fontdir=Path(__file__).resolve().parents[2]/'dashboard/rangelab/assets/fonts'
    for name,file in [('RangeLab','Inter-Regular.ttf'),('RangeLab-Bold','Inter-Bold.ttf')]:
        if name not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont(name,str(fontdir/file)))
    pdfmetrics.registerFontFamily('RangeLab',normal='RangeLab',bold='RangeLab-Bold',italic='RangeLab',boldItalic='RangeLab-Bold')
    styles=getSampleStyleSheet()
    for key in styles.byName:styles[key].fontName='RangeLab'
    styles['Normal'].fontSize=9;styles['Normal'].leading=14;styles['Normal'].spaceAfter=8
    styles['Title'].fontName='RangeLab-Bold';styles['Title'].fontSize=23;styles['Title'].leading=29;styles['Title'].textColor=colors.HexColor('#630ed4')
    styles['Heading2'].fontName='RangeLab-Bold';styles['Heading2'].fontSize=13;styles['Heading2'].spaceBefore=14
    styles.add(ParagraphStyle(name='SmallLab',parent=styles['Normal'],fontSize=7,leading=11,textColor=colors.HexColor('#4a4455'),splitLongWords=True))
    def p(text,style='Normal'):return Paragraph(escape(str(text)),styles[style])
    result=record.result;meta=result['meta'];cfg=record.config.config;pool=meta['assumptions']['pool'];opt=result['optimum']
    buffer=BytesIO();doc=SimpleDocTemplate(buffer,pagesize=A4,rightMargin=42,leftMargin=42,topMargin=43,bottomMargin=44,title='RangeLab - '+('Phương pháp nghiên cứu' if methodology else 'Kết quả tối ưu hóa'),author='RangeLab Research Simulator')
    story=[p('RANGELAB / UNISWAP V3 RESEARCH','SmallLab'),p('Phương pháp nghiên cứu' if methodology else 'Kết quả tối ưu hóa LP','Title'),
        p(f"{pool['base']} / {pool['quote']}  |  Fee {pool['fee_tier']/10000:.2f}%  |  {cfg.horizon_days} ngày"),
        p('Kết quả mô phỏng theo giả định, phục vụ nghiên cứu. Không phải mức sinh lời được bảo đảm.'),
        p('Run ID: '+meta['run_id'],'SmallLab'),p('Data SHA256: '+meta['data_hash'],'SmallLab'),
        p('Snapshot: '+str(meta['data_asof'])+' | Model: '+meta['model_version'],'SmallLab')]
    def table(rows):
        data=[[p(x,'SmallLab') for x in row] for row in rows]
        t=Table(data,colWidths=[244,225],hAlign='LEFT',repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eaedff')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor('#ccc3d8')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#faf8ff')])]))
        story.append(t)
    if not methodology:
        story.append(p('Range và kết quả kỳ vọng','Heading2'))
        if opt:
            rows=[['Chỉ tiêu','Giá trị'],['Range liên tục (quote/base)',f"{opt['p_low']:,.8g} - {opt['p_high']:,.8g}"],
                ['Vốn / mô hình / số đường',f'{cfg.capital:,.2f} USD / {cfg.price_model} / {cfg.n_paths}'],['Phí / IL (USD)',f"{opt['fees']*cfg.capital:,.2f} / {opt['il']*cfg.capital:,.2f}"],
                ['Gas / ma sát (USD)',f"{opt['gas']*cfg.capital:,.2f} / {opt['rebalance_cost']*cfg.capital:,.2f}"],['Lợi nhuận ròng LP',f"{opt['net']:.3%}"],
                ['Chênh lệch so với HODL',f"{opt['excess_vs_hodl']:.3%}"],['Tỷ lệ ngày trong range / xác suất từng rời range',f"{opt['active_share']:.2%} / {opt['exit_prob']:.2%}"],
                ['Q5 / CVaR5 chênh lệch cuối kỳ',f"{opt['q5']:.3%} / {opt['cvar5']:.3%}"],['Policy / seed',record.config.rebalance_policy+' / '+str(cfg.seed)]]
            table(rows)
        else:story.append(p('Không có range khả thi trên lưới với giới hạn rủi ro hiện tại.'))
    story.append(p('Phương pháp và cách đọc kết quả','Heading2'))
    method_paragraphs=[
        'Range đối xứng theo log giá được đánh giá trên lưới 20 điểm. Mục tiêu là kỳ vọng chênh lệch tài sản cuối kỳ LP so với HODL, với ràng buộc xác suất từng rời range tại các mốc đóng cửa ngày. Lựa chọn trên mô phỏng không phải kiểm định ngoài mẫu.',
        'Với P trong range [a,b]: x = L(1/√P - 1/√b), y = L(√P - √a). Ngoài range, lượng token được chặn tại biên. Giá trị vị thế = xP + y. Benchmark giữ lượng token ban đầu 50:50 theo giá trị.',
        'Phí ngày = volume USD × fee rate × L_own/(L_own + L_background) × chỉ báo trong range. Forward dùng active-L quan sát đã chuẩn hóa tại snapshot và giữ cố định. Phí được giữ dưới dạng USD cash, không tái đầu tư.',
        'Chênh lệch so HODL = phí - IL - gas - ma sát + PnL phòng hộ (nếu có). IL đo chênh lệch HODL với giá trị inventory, tách riêng khỏi phí và chi phí. Hedging là delta hedge theo ngày, không có funding, borrow hoặc margin.',
        'Bootstrap ghép lợi nhuận và volume lịch sử; GARCH dùng hiệu chỉnh trước as-of; GBM dùng volatility giả định. Volume ghi đè là giả định cố định USD/ngày. Sensitivity dùng GBM và cùng seed; stress dùng log bridge có giá cuối kỳ cố định.',
        'Historical replay dùng giá và volume pool ngày, quote/USD tham chiếu và TVL trễ để xấp xỉ thanh khoản nền. Không có chuỗi active-L/fee-growth theo block để khẳng định phí LP thực hiện. Thông tin hiệu chỉnh chỉ lấy trước quyết định; vintage công bố TVL chưa được xác minh.',
        'Dữ liệu pool công khai hiện có khoảng một năm và có thể có khoảng trống theo pool. Giá tham chiếu dài hơn không thay được volume/liquidity pool còn thiếu. Chưa có tập pool 2022-2024 để khẳng định kiểm định OOS 2025-2026.',
        'Quote/USD giữ cố định trong forward, kể cả WETH. Quan sát theo ngày bỏ qua dao động nội ngày, MEV/JIT và market impact. Gas là giả định phẳng. Không áp ràng buộc khả năng thanh toán; chi phí lớn có thể làm tài sản mô phỏng âm. Lợi nhuận quy năm chỉ là phép ngoại suy.'
    ]
    if not methodology:
        method_paragraphs=[method_paragraphs[0],
            'Phí dùng volume pool và active-L snapshot, giữ cố định thanh khoản nền trong tương lai. Quote/USD không đổi, phí không tái đầu tư. Gas và ma sát là giả định người dùng. PnL hedge theo ngày được tách riêng nếu chọn phòng hộ.',
            'Giới hạn: quan sát ngày bỏ qua dao động nội ngày, funding và MEV/JIT. Không có ràng buộc khả năng thanh toán hoặc khẳng định OOS. Xem PDF phương pháp và JSON của run để có giả định đầy đủ.']
    for text in method_paragraphs:story.append(p(text))
    story.append(p('Tái lập và nguồn dữ liệu','Heading2'))
    provenance_rows=[['Tham số','Giá trị'],['Volatility hiệu lực / volume ngày trung bình',f"{result['effective_vol_annual']:.3%} / {result['mean_daily_volume_usd']:,.2f} USD"],
        ['Gas mỗi đơn vị / phí trượt giá',f'{cfg.gas_usd:,.2f} USD / {cfg.rebalance_slippage_bps:g} bps'],['Giới hạn xác suất / độ rộng min-max',f'{cfg.risk_max_exit_prob:.2%} / {cfg.min_half_width:g} - {cfg.max_half_width or "auto"} log'],
        ['Chain / địa chỉ pool',str(pool.get('chain_id',1))+' / '+str(pool['address'])],['Nguồn','Ethereum/Arbitrum RPC; GeckoTerminal; DefiLlama; Binance reference. Xem provenance trong JSON export.']]
    table(provenance_rows if methodology else [provenance_rows[0],provenance_rows[1],provenance_rows[2],provenance_rows[4]])
    story.append(p('Tài liệu giao thức: https://docs.uniswap.org/contracts/v3/reference/core/libraries/SqrtPriceMath','SmallLab'))
    def footer(canvas,document):
        canvas.saveState();canvas.setStrokeColor(colors.HexColor('#ccc3d8'));canvas.line(42,33,A4[0]-42,33);canvas.setFont('RangeLab',7);canvas.setFillColor(colors.HexColor('#4a4455'));canvas.drawString(42,21,'RangeLab Research Simulator | '+meta['run_id'][:16]);canvas.drawRightString(A4[0]-42,21,str(document.page));canvas.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return buffer.getvalue()
