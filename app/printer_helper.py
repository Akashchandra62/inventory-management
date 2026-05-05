# ============================================================
# printer_helper.py  –  PDF Invoice Generator
# Layout matches reference HTML invoice (SMJ-style).
# ============================================================

import os
import tempfile
import traceback

from PyQt5.QtWidgets import QMessageBox, QFileDialog
from app.config import AppConfig
from app.utils import format_currency
from app.constants import LOGO_FILE, QR_FILE, CERTIFICATE_FILE


def _qt_render(text: str, font_pt: int = 9, dpi: int = 300):
    """
    Render text using Qt's shaping engine so complex scripts (Devanagari, etc.)
    form correct conjunct ligatures — identical to what the user sees in the UI.
    Returns (tmp_png_path, width_mm, height_mm) or None on failure.
    """
    try:
        from PyQt5.QtGui import QPixmap, QPainter, QFont, QFontMetrics, QColor
        from PyQt5.QtCore import Qt

        px_per_pt = dpi / 72.0
        font = QFont("Nirmala UI")
        font.setPixelSize(max(int(font_pt * px_per_pt), 1))

        fm = QFontMetrics(font)
        br = fm.boundingRect(text)
        w  = max(br.width() + 12, 1)
        h  = max(fm.height() + 6, 1)

        pix = QPixmap(w, h)
        pix.fill(Qt.transparent)

        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.setFont(font)
        painter.setPen(QColor(0, 0, 0))
        painter.drawText(6, fm.ascent() + 3, text)
        painter.end()

        fd, path = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        pix.save(path, 'PNG')

        w_mm = w / dpi * 25.4
        h_mm = h / dpi * 25.4
        return path, w_mm, h_mm
    except Exception:
        return None


# ── Amount in Words ──────────────────────────────────────────
def amount_in_words(amount: float) -> str:
    try:
        ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven',
                'Eight', 'Nine', 'Ten', 'Eleven', 'Twelve', 'Thirteen',
                'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
        tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty',
                'Sixty', 'Seventy', 'Eighty', 'Ninety']

        def words(n):
            if n == 0:          return ''
            elif n < 20:        return ones[n]
            elif n < 100:       return tens[n // 10] + (' ' + ones[n % 10] if n % 10 else '')
            elif n < 1000:      return ones[n // 100] + ' Hundred' + (' ' + words(n % 100) if n % 100 else '')
            elif n < 100000:    return words(n // 1000) + ' Thousand' + (' ' + words(n % 1000) if n % 1000 else '')
            elif n < 10000000:  return words(n // 100000) + ' Lakh' + (' ' + words(n % 100000) if n % 100000 else '')
            else:               return words(n // 10000000) + ' Crore' + (' ' + words(n % 10000000) if n % 10000000 else '')

        rupees = int(amount)
        paise  = round((amount - rupees) * 100)
        result = 'Rupees ' + words(rupees) if rupees else 'Rupees Zero'
        if paise:
            result += ' and ' + words(paise) + ' Paise'
        return (result + ' Only').strip()
    except Exception:
        return ''


# ── Public entry points ───────────────────────────────────────
def save_invoice_as_pdf(invoice: dict, parent=None):
    try:
        inv_num      = invoice.get("invoice_number", "invoice").replace("/", "-")
        default_name = f"Invoice_{inv_num}.pdf"
        path, _ = QFileDialog.getSaveFileName(
            parent, "Save Invoice as PDF", default_name, "PDF Files (*.pdf)"
        )
        if not path:
            return
        _generate_pdf(invoice, path)
        QMessageBox.information(parent, "Invoice Saved", f"Invoice saved as PDF:\n{path}")
        os.startfile(path)
    except Exception as e:
        traceback.print_exc()
        QMessageBox.critical(parent, "Error", f"Could not generate invoice:\n{str(e)}")


# ── Reusable box helpers ──────────────────────────────────────
def _make_initials_box(initials: str, size: float, bc):
    """Bordered box with shop initials — shown when no logo image exists."""
    from reportlab.platypus import Table, TableStyle, Paragraph
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    p = Paragraph(
        f'<b>{initials}</b><br/><font size="6">JEWELLERS</font>',
        ParagraphStyle('_ib', fontSize=14, fontName='Helvetica-Bold',
                       alignment=TA_CENTER, leading=17)
    )
    t = Table([[p]], colWidths=[size], rowHeights=[size])
    t.setStyle(TableStyle([
        ('BOX',           (0, 0), (-1, -1), 1.5, bc),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return t


def _make_bis_box(size: float, bc):
    """BIS HALLMARK CERTIFIED bordered box — right side of header."""
    from reportlab.platypus import Table, TableStyle, Paragraph
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    p = Paragraph(
        '<b>BIS<br/>HALLMARK<br/>CERTIFIED</b>',
        ParagraphStyle('_bb', fontSize=7, fontName='Helvetica-Bold',
                       alignment=TA_CENTER, leading=10)
    )
    t = Table([[p]], colWidths=[size], rowHeights=[size])
    t.setStyle(TableStyle([
        ('BOX',           (0, 0), (-1, -1), 1.5, bc),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return t


# ── Core PDF builder ─────────────────────────────────────────
def _generate_pdf(invoice: dict, path: str):
    _tmp_files = []   # temp PNGs rendered via Qt — cleaned up after build

    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle,
        Paragraph, Spacer, Image as RLImage, KeepInFrame
    )
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # Register Nirmala UI for Hindi / Devanagari rendering
    _HINDI_FONT      = 'Helvetica'
    _HINDI_FONT_BOLD = 'Helvetica-Bold'
    try:
        _nirmala_path = r'C:\Windows\Fonts\Nirmala.ttc'
        pdfmetrics.registerFont(TTFont('NirmalaUI',     _nirmala_path, subfontIndex=0))
        pdfmetrics.registerFont(TTFont('NirmalaUI-Bd',  _nirmala_path, subfontIndex=1))
        _HINDI_FONT      = 'NirmalaUI'
        _HINDI_FONT_BOLD = 'NirmalaUI-Bd'
    except Exception:
        pass   # fall back to Helvetica (Hindi won't render but won't crash)

    BLACK = colors.black
    LGRAY = colors.HexColor('#f5f5f5')   # table header bg
    DGRAY = colors.HexColor('#f0f0f0')   # net payable row bg
    MGRAY = colors.HexColor('#f9f9f9')   # totals row bg
    SUBT  = colors.HexColor('#e4e4e4')   # purity sub-total row bg (light gray)

    # Build a purity→metal-name lookup from the metals rate-card
    try:
        from services.metal_service import get_metals as _gm
        _metals_map = {m.get('purity', '').strip().upper(): m.get('name', '')
                       for m in _gm() if m.get('purity')}
    except Exception:
        _metals_map = {}

    def _metal_label(purity: str) -> str:
        """Return 'Gold 22Kt' style label, or just the purity if no match found."""
        metal = _metals_map.get(purity.strip().upper(), '')
        return f"{metal} {purity}".strip() if metal else purity

    # ── Shop data ─────────────────────────────────────────────
    shop         = AppConfig.shop()
    shop_name        = shop.get("shop_name",        "Jewellers")
    tagline          = shop.get("tagline",          "")
    address          = shop.get("address",          "")
    mobile           = shop.get("mobile",           "")
    mobile2          = shop.get("mobile2",          "")
    invoice_heading  = shop.get("invoice_heading",  "")
    gst_number   = shop.get("gst_number",   "")
    state        = shop.get("state",        "")
    state_code   = shop.get("state_code",   "")
    jurisdiction = shop.get("jurisdiction", "")
    bank_name    = shop.get("bank_name",    "")
    acc_name     = shop.get("account_name", "")
    acc_no       = shop.get("account_number", "")
    branch       = shop.get("bank_branch",  "")
    ifsc         = shop.get("ifsc_code",    "")
    terms_text   = shop.get("terms",        "")

    # ── Invoice data ──────────────────────────────────────────
    customer_name    = invoice.get("customer_name",    "")
    customer_address = invoice.get("customer_address", "")
    customer_mobile  = invoice.get("customer_mobile",  "")
    customer_gst     = invoice.get("customer_gst",     "")
    inv_number       = invoice.get("invoice_number",   "")
    inv_date         = invoice.get("date",             "")
    items            = invoice.get("items",            [])
    subtotal         = float(invoice.get("subtotal",   0))
    cgst_pct         = float(invoice.get("cgst_percent", 1.5))
    sgst_pct         = float(invoice.get("sgst_percent", 1.5))
    igst_pct         = float(invoice.get("igst_percent", 0))
    # Use stored tax amounts — never recompute, to ensure PDF matches saved record
    cgst_amt         = float(invoice.get("cgst_amount", round(subtotal * cgst_pct / 100, 2)))
    sgst_amt         = float(invoice.get("sgst_amount", round(subtotal * sgst_pct / 100, 2)))
    igst_amt         = float(invoice.get("igst_amount", round(subtotal * igst_pct / 100, 2)))
    amt_after_gst    = round(subtotal + cgst_amt + sgst_amt + igst_amt, 2)
    grand_total      = float(invoice.get("grand_total", amt_after_gst))
    round_off        = float(invoice.get("round_off", round(grand_total - amt_after_gst, 2)))
    cash_paid        = float(invoice.get("cash_paid",    0))
    upi_paid         = float(invoice.get("upi_paid",     0))
    card_paid        = float(invoice.get("card_paid",    0))
    cheque_paid      = float(invoice.get("cheque_paid",  0))
    old_purchase     = float(invoice.get("old_purchase", 0))
    advance_paid     = float(invoice.get("advance_paid", 0))
    notes            = invoice.get("notes",             "")

    # ── Page layout constants ──────────────────────────────────
    W, H   = A4
    margin = 10 * mm
    UW     = W - 2 * margin       # usable width ≈ 190 mm

    # ── Style factory (unique names avoid any caching clash) ──
    _n = [0]
    def _ps(size=8, bold=False, italic=False, align=TA_LEFT,
            color=BLACK, leading=None, fontName=None):
        _n[0] += 1
        if fontName:
            fn = fontName
        else:
            fn = ('Helvetica-Bold'    if bold   else
                  'Helvetica-Oblique' if italic else 'Helvetica')
        kw = dict(fontSize=size, fontName=fn,
                  alignment=align, textColor=color)
        if leading:
            kw['leading'] = leading
        return ParagraphStyle(f'_s{_n[0]}', **kw)

    def P(txt, size=8, bold=False, italic=False,
          align=TA_LEFT, color=BLACK, leading=None, fontName=None):
        return Paragraph(str(txt),
                         _ps(size=size, bold=bold, italic=italic,
                             align=align, color=color, leading=leading,
                             fontName=fontName))

    def TH(txt):
        """Table header cell."""
        return Paragraph(str(txt),
                         _ps(size=6, bold=True, align=TA_CENTER, leading=8))

    def TD(txt, bold=False, align=TA_CENTER, size=8):
        """Table data cell."""
        return Paragraph(str(txt),
                         _ps(size=size, bold=bold, align=align, leading=10))

    story = []

    # ── Watermark + outer border drawn on every page ──────────
    words_ = shop_name.split()
    initials = ''.join(w[0].upper() for w in words_[:3]) if words_ else 'JB'

    def on_page(c, doc):
        c.saveState()
        # outer border (2 mm inside page edge)
        c.setStrokeColor(BLACK)
        c.setLineWidth(1.5)
        c.rect(8 * mm, 8 * mm, W - 16 * mm, H - 16 * mm)
        # diagonal watermark
        c.setFont('Helvetica-Bold', 110)
        c.setFillColorRGB(0, 0, 0, 0.04)
        c.translate(W / 2, H / 2)
        c.rotate(35)
        c.drawCentredString(0, 0, initials)
        c.restoreState()

    # ══════════════════════════════════════════════════════════
    # 1. TOP BAR  — GSTIN | Mantra | Mobile
    # ══════════════════════════════════════════════════════════
    mob_str = f"Mobile No. :- {mobile}"
    if mobile2:
        mob_str += f"<br/>{mobile2}"

    # Render invoice heading via Qt so Devanagari conjuncts match the settings field exactly
    if invoice_heading.strip():
        _qt = _qt_render(invoice_heading.strip(), font_pt=9, dpi=300)
        if _qt:
            _tmp_files.append(_qt[0])
            heading_cell = RLImage(_qt[0], width=_qt[1] * mm, height=_qt[2] * mm)
        else:
            heading_cell = P(invoice_heading, size=9, align=TA_CENTER, fontName=_HINDI_FONT)
    else:
        heading_cell = P('', size=9)

    top_bar = Table(
        [[P(f"GSTIN :- {gst_number}", size=8),
          heading_cell,
          P(mob_str, size=8, align=TA_RIGHT)]],
        colWidths=[UW * 0.38, UW * 0.24, UW * 0.38]
    )
    top_bar.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING',   (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
        ('LINEBELOW',     (0, 0), (-1, -1), 0.5, BLACK),
    ]))
    story.append(top_bar)

    # ══════════════════════════════════════════════════════════
    # 2. HEADER  — Logo box | Shop info | BIS sticker
    # ══════════════════════════════════════════════════════════
    BOX_COL  = 26 * mm          # column width for left/right cells
    CTR_COL  = UW - 2 * BOX_COL

    # Left: logo image or initials box
    if os.path.exists(LOGO_FILE):
        try:
            left_hdr = RLImage(LOGO_FILE,
                               width=BOX_COL - 4 * mm,
                               height=BOX_COL - 4 * mm)
        except Exception:
            left_hdr = _make_initials_box(initials, BOX_COL - 4 * mm, BLACK)
    else:
        left_hdr = _make_initials_box(initials, BOX_COL - 4 * mm, BLACK)

    # Center: shop name, tagline, address
    # Pass as a list directly — table cell auto-sizes, no squashing
    center_items = [P(shop_name, size=20, bold=True, align=TA_CENTER,
                      leading=24)]
    if tagline:
        center_items += [Spacer(1, 2 * mm),
                         P(tagline, size=8, italic=True, align=TA_CENTER)]
    if address:
        center_items += [Spacer(1, 2 * mm),
                         P(address, size=8, align=TA_CENTER)]
    center_cell = center_items      # list of flowables — cell auto-sizes

    # Right: uploaded certificate/hallmark image, or BIS box as fallback
    if os.path.exists(CERTIFICATE_FILE):
        try:
            right_hdr = RLImage(CERTIFICATE_FILE,
                                width=BOX_COL - 4 * mm,
                                height=BOX_COL - 4 * mm)
        except Exception:
            right_hdr = _make_bis_box(BOX_COL - 4 * mm, BLACK)
    else:
        right_hdr = _make_bis_box(BOX_COL - 4 * mm, BLACK)

    header_tbl = Table(
        [[left_hdr, center_cell, right_hdr]],
        colWidths=[BOX_COL, CTR_COL, BOX_COL]
    )
    header_tbl.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',         (0, 0), (0,  -1), 'CENTER'),
        ('ALIGN',         (2, 0), (2,  -1), 'CENTER'),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING',   (0, 0), (-1, -1), 3),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 3),
        ('LINEBELOW',     (0, 0), (-1, -1), 0.5, BLACK),
    ]))
    story.append(header_tbl)

    # ══════════════════════════════════════════════════════════
    # 3. TAX INVOICE STRIP
    # ══════════════════════════════════════════════════════════
    tax_strip = Table(
        [[P("<u>T A X   I N V O I C E</u>",
            size=11, bold=True, align=TA_CENTER)]],
        colWidths=[UW]
    )
    tax_strip.setStyle(TableStyle([
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('LINEBELOW',     (0, 0), (-1, -1), 0.5, BLACK),
    ]))
    story.append(tax_strip)

    # ══════════════════════════════════════════════════════════
    # 4. CUSTOMER INFO  |  INVOICE META
    # ══════════════════════════════════════════════════════════
    CW = UW * 0.60      # customer column
    MW = UW - CW        # meta column

    cust_tbl = Table(
        [[P("<b>Name :-</b>",           size=8), P(customer_name,    size=8)],
         [P("<b>Address :-</b>",        size=8), P(customer_address, size=8)],
         [P("<b>Phone No.</b>",         size=8), P(customer_mobile,  size=8)],
         [P("<b>Customer GST NO:-</b>", size=8), P(customer_gst,     size=8)]],
        colWidths=[33 * mm, CW - 33 * mm]
    )
    cust_tbl.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING',   (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 2),
    ]))

    state_str = ""
    if state:
        state_str = f"State : {state}" + (f"  Code : {state_code}"
                                           if state_code else "")

    meta_tbl = Table(
        [[P("<b>INVOICE DATE :</b>", size=8), P(inv_date,        size=8, align=TA_RIGHT)],
         [P("<b>INVOICE NO. :-</b>", size=8), P(inv_number,      size=8, align=TA_RIGHT)],
         [P(f"<b>{state_str}</b>",   size=7), P("Original Copy", size=7,
                                                 italic=True, align=TA_RIGHT)]],
        colWidths=[MW * 0.55, MW * 0.45]
    )
    meta_tbl.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING',   (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
        ('LINEABOVE',     (0, 2), (-1,  2), 0.3, colors.HexColor('#cccccc')),
        ('TOPPADDING',    (0, 2), (-1,  2), 4),
    ]))

    info_tbl = Table([[cust_tbl, meta_tbl]], colWidths=[CW, MW])
    info_tbl.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('LINEBEFORE',    (1, 0), (1,  -1), 0.5, BLACK),
        ('LINEBELOW',     (0, 0), (-1, -1), 0.5, BLACK),
        ('TOPPADDING',    (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
    ]))
    story.append(info_tbl)

    # ══════════════════════════════════════════════════════════
    # 5. ITEMS TABLE  (11 columns, sum = 190 mm)
    #    Items are grouped by Metal (Gold, Silver, etc.).
    #    A "Gold Total" / "Silver Total" row is inserted after
    #    each metal group, always shown, with a gray background.
    # ══════════════════════════════════════════════════════════
    col_w = [8*mm, 12*mm, 30*mm, 16*mm, 12*mm, 12*mm, 8*mm,
             16*mm, 12*mm, 12*mm, 12*mm, 18*mm, 22*mm]

    hdr_texts = [
        'S.\nNo', 'Tag/\nRfid', 'Item\nName', 'Huid/\nRemarks',
        'Hsn\nCode', 'Purity\nKt/Ct', 'Pcs',
        'Gross Wt\n(in Gms)', 'Less\n(in Gms)', 'Nett Wt\n(in Gms)',
        'Rate\nPer Gm', 'Mk/Chrg\nPer Gm', 'Amount\n(INR)'
    ]

    def _item_metal_name(purity: str) -> str:
        """Return metal name (Gold/Silver/…) for a purity, falling back to purity itself."""
        metal = _metals_map.get(purity.strip().upper(), '')
        return metal if metal else purity

    # ── Group items by metal name (preserve insertion order) ──
    from collections import OrderedDict as _OD
    _metal_groups = _OD()
    for _it in items:
        _p  = (_it.get('purity') or 'Other').strip()
        _mn = _item_metal_name(_p)
        _metal_groups.setdefault(_mn, []).append(_it)

    metal_row_indices = []   # 0-based row indices of metal-total rows

    rows      = [[TH(h) for h in hdr_texts]]
    gross_tot = 0.0
    nett_tot  = 0.0
    serial_no = 0

    for metal_name, grp_items in _metal_groups.items():
        gw_grp = nw_grp = amt_grp = 0.0

        for it in grp_items:
            serial_no += 1
            gw      = float(it.get('weight',        0))
            lw      = float(it.get('less_weight',   0))
            nw      = round(gw - lw, 3)
            mk      = float(it.get('making_charge', 0))
            mk_pct  = float(it.get('making_pct',    0))
            amt     = float(it.get('total',         0))
            cat     = it.get('category', '')
            gross_tot += gw;  nett_tot  += nw
            gw_grp    += gw;  nw_grp    += nw;  amt_grp += amt
            mk_str = f"{mk_pct:.2f}%" if mk_pct > 0 else f"\u20b9{mk:,.2f}"

            name_p = Paragraph(
                f'<b>{it.get("name", "")}</b>'
                f'<br/><font size="6" color="#555555">{cat}</font>',
                _ps(size=7, bold=True, align=TA_LEFT, leading=9)
            )
            rows.append([
                TD(serial_no),
                TD(it.get('tag',  '')),
                name_p,
                TD(it.get('huid', '')),
                TD(it.get('hsn_code', '7113')),
                TD(it.get('purity', '')),
                TD(it.get('quantity', 1)),
                TD(f"{gw:.2f}"),
                TD(f"{lw:.2f}"),
                TD(f"{nw:.2f}"),
                TD(f"{float(it.get('rate', 0)):.0f}"),
                TD(mk_str),
                TD(f"{amt:,.2f}", bold=True),
            ])

        # Metal total row — always shown
        metal_lbl = Paragraph(
            f'<b>{metal_name} Total</b>',
            _ps(size=9, bold=True, align=TA_LEFT)
        )
        rows.append([
            metal_lbl,                                      # col 0 — spans 0-6
            TD(''), TD(''), TD(''), TD(''), TD(''), TD(''), # cols 1-6 (merged)
            TD(f'{gw_grp:.2f}',   bold=True),
            TD(''),
            TD(f'{nw_grp:.2f}',   bold=True),
            TD(''), TD(''),
            TD(f'{amt_grp:,.2f}', bold=True),
        ])
        metal_row_indices.append(len(rows) - 1)

    n_data_rows = len(rows) - 1          # header not counted
    n_blank     = max(5 - len(items), 2)
    empty_r     = [TD('') for _ in col_w]
    for _       in range(n_blank):
        rows.append(empty_r)

    # Grand totals row
    rows.append([
        TD(''), TD(''), TD(''), TD(''), TD(''), TD(''), TD(''),
        TD(f"{gross_tot:.2f}", bold=True),
        TD(''),
        TD(f"{nett_tot:.2f}",  bold=True),
        TD(''), TD(''),
        TD(f"{subtotal:,.2f}", bold=True),
    ])

    nr = len(rows)

    # ── Base table style ──────────────────────────────────────
    style_cmds = [
        ('BACKGROUND',    (0, 0),              (-1, 0),      LGRAY),
        ('FONTNAME',      (0, 0),              (-1, 0),      'Helvetica-Bold'),
        ('GRID',          (0, 0),              (-1, -1),     0.5, BLACK),
        ('ALIGN',         (0, 0),              (-1, -1),     'CENTER'),
        ('VALIGN',        (0, 0),              (-1, -1),     'MIDDLE'),
        ('TOPPADDING',    (0, 0),              (-1, -1),     0),
        ('BOTTOMPADDING', (0, 0),              (-1, -1),     0),
        # item-name column: left-aligned for all data rows
        ('ALIGN',         (2, 1),              (2, n_data_rows), 'LEFT'),
        ('LEFTPADDING',   (2, 1),              (2, n_data_rows), 4),
        # blank filler rows: thin height
        ('ROWHEIGHT',     (0, n_data_rows + 1), (-1, nr - 2), 15),
        # grand totals row
        ('BACKGROUND',    (0, -1),             (-1, -1),     MGRAY),
        ('FONTNAME',      (0, -1),             (-1, -1),     'Helvetica-Bold'),
    ]

    # ── Metal total row styling ────────────────────────────────
    for mri in metal_row_indices:
        style_cmds += [
            ('SPAN',        (0, mri), (6,  mri)),
            ('BACKGROUND',  (0, mri), (-1, mri), SUBT),
            ('FONTNAME',    (0, mri), (-1, mri), 'Helvetica-Bold'),
            ('LINEABOVE',   (0, mri), (-1, mri), 1.2, BLACK),
            ('LINEBELOW',   (0, mri), (-1, mri), 1.2, BLACK),
            ('ALIGN',       (0, mri), (0,  mri), 'LEFT'),
            ('LEFTPADDING', (0, mri), (0,  mri), 8),
            ('ROWHEIGHT',   (0, mri), (-1, mri), 20),
            ('VALIGN',      (0, mri), (-1, mri), 'MIDDLE'),
        ]

    items_tbl = Table(rows, colWidths=col_w, repeatRows=1)
    items_tbl.setStyle(TableStyle(style_cmds))
    story.append(items_tbl)

    # ══════════════════════════════════════════════════════════
    # 6. BOTTOM  — Payment/Words/Bank  |  Totals + Signature
    # ══════════════════════════════════════════════════════════
    LW = UW * 0.55      # left column  ≈ 104 mm
    RW = UW - LW        # right column ≈  86 mm

    # ── Left: Payment Detail ──────────────────────────────────
    total_paid = cash_paid + upi_paid + card_paid + cheque_paid + old_purchase + advance_paid
    if total_paid == 0:
        total_paid = grand_total

    def _pamt(val):
        """Right-aligned ₹ amount cell for payment rows."""
        return P(f"₹ {val:,.0f} /-", size=8, align=TA_RIGHT, fontName=_HINDI_FONT)

    pay_data = [[P("<b><u>Payment Detail :</u></b>", size=9), '']]
    if cash_paid > 0:
        pay_data.append([P("<b>Cash</b>", size=8), _pamt(cash_paid)])
    if upi_paid > 0:
        pay_data.append([P("<b>UPI</b>", size=8), _pamt(upi_paid)])
    if card_paid > 0:
        pay_data.append([P("<b>Card</b>", size=8), _pamt(card_paid)])
    if cheque_paid > 0:
        pay_data.append([P("<b>Cheque</b>", size=8), _pamt(cheque_paid)])
    if old_purchase > 0:
        pay_data.append([P("<b>Old Purchase (-)</b>", size=8), _pamt(old_purchase)])
    if advance_paid > 0:
        pay_data.append([P("<b>Advance (-)</b>", size=8), _pamt(advance_paid)])
    pay_data.append([P("<b>TOTAL PAYMENT -</b>", size=8),
                     P(f"₹ {total_paid:,.0f} /-", size=8, bold=True,
                       align=TA_RIGHT, fontName=_HINDI_FONT_BOLD)])

    pay_inner = Table(pay_data, colWidths=[LW * 0.58, LW * 0.42])
    pay_inner.setStyle(TableStyle([
        ('SPAN',          (0, 0), (-1, 0)),
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (1, 1), (1,  -1), 6),   # right margin on amount column
        ('ALIGN',         (1, 1), (1,  -1), 'RIGHT'),
    ]))

    # ── Left: Amount in Words ─────────────────────────────────
    words_para = Paragraph(
        f"<b><u>Amount In Word</u></b><br/>"
        f"Rupees: {amount_in_words(grand_total)}",
        _ps(size=8, leading=13)
    )

    # ── Left: Bank Detail ─────────────────────────────────────
    bank_parts = ["<b><u>Bank Detail :</u></b>"]
    if bank_name: bank_parts.append(f"Bank Name :- {bank_name}")
    if acc_name:  bank_parts.append(f"A/c Name  :- {acc_name}")
    if acc_no:    bank_parts.append(f"A/c No.   :- {acc_no}")
    if branch:    bank_parts.append(f"Branch {branch}")
    if ifsc:      bank_parts.append(f"IFSC      :- {ifsc}")
    bank_para = Paragraph('<br/>'.join(bank_parts), _ps(size=8, leading=12))

    if os.path.exists(QR_FILE):
        try:
            qr_img   = RLImage(QR_FILE, width=20 * mm, height=20 * mm)
            bank_cell = Table(
                [[bank_para, qr_img]],
                colWidths=[LW - 24 * mm, 24 * mm]
            )
            bank_cell.setStyle(TableStyle([
                ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
                ('ALIGN',         (1, 0), (1,  -1), 'CENTER'),
                ('TOPPADDING',    (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                ('LEFTPADDING',   (0, 0), (-1, -1), 0),
                ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
            ]))
        except Exception:
            bank_cell = bank_para
    else:
        bank_cell = bank_para

    left_bottom = Table(
        [[pay_inner], [words_para], [bank_cell]],
        colWidths=[LW]
    )
    left_bottom.setStyle(TableStyle([
        ('LINEBELOW',     (0, 0), (0, 0), 0.5, BLACK),
        ('LINEBELOW',     (0, 1), (0, 1), 0.5, BLACK),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING',   (0, 0), (-1, -1), 5),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 5),
    ]))

    # ── Right: Totals ─────────────────────────────────────────
    round_off_str = (f"- {abs(round_off):.2f}" if round_off < 0
                     else f"+ {round_off:.2f}"  if round_off > 0
                     else "0.00")

    def srow(lbl, val, bold=False):
        sz = 9 if bold else 8
        return [P(lbl, size=sz, bold=bold, align=TA_LEFT),
                P(':',  size=sz, bold=bold, align=TA_CENTER),
                P(val,  size=sz, bold=bold, align=TA_RIGHT)]

    sig_p = Paragraph(
        "________________________<br/>Customer's Signature",
        _ps(size=7, align=TA_CENTER, leading=11)
    )

    sum_rows = [
        srow('Gross Amount',          f"{subtotal:,.2f}"),
        srow(f'CGST @ {cgst_pct}%',  f"{cgst_amt:.2f}"),
        srow(f'SGST @ {sgst_pct}%',  f"{sgst_amt:.2f}"),
        srow('Amt After GST',          f"{amt_after_gst:.2f}"),
        srow('Round Off',              round_off_str),
        srow('Net Payable',            f"{grand_total:,.2f}", bold=True),
        [sig_p, '', ''],
    ]

    r1, r2, r3 = RW * 0.48, RW * 0.06, RW * 0.46
    right_bottom = Table(sum_rows, colWidths=[r1, r2, r3])
    right_bottom.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING',   (0, 0), (-1, -1), 3),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 2),
        # value column: minimal right padding so numbers don't get clipped
        ('RIGHTPADDING',  (2, 0), (2, -1), 4),
        ('LINEBELOW',     (0, 0), (-1,  4), 0.5, BLACK),
        # Net Payable row (index 5) — gray bg, thick top border
        ('BACKGROUND',    (0, 5), (-1,  5), DGRAY),
        ('LINEABOVE',     (0, 5), (-1,  5), 1.5, BLACK),
        ('LINEBELOW',     (0, 5), (-1,  5), 0.5, BLACK),
        # Signature row (index 6) — spanned, centered
        ('SPAN',          (0, 6), (-1,  6)),
        ('LINEABOVE',     (0, 6), (-1,  6), 0.5, BLACK),
        ('ALIGN',         (0, 6), (-1,  6), 'CENTER'),
        ('TOPPADDING',    (0, 6), (-1,  6), 10),
        ('BOTTOMPADDING', (0, 6), (-1,  6), 6),
    ]))

    # ── Combine left + right ──────────────────────────────────
    bottom_tbl = Table([[left_bottom, right_bottom]], colWidths=[LW, RW])
    bottom_tbl.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('LINEBEFORE',    (1, 0), (1,  -1), 0.5, BLACK),
        ('LINEABOVE',     (0, 0), (-1,  0), 0.5, BLACK),
        ('TOPPADDING',    (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
    ]))
    story.append(bottom_tbl)

    # ══════════════════════════════════════════════════════════
    # 7. TERMS & CONDITIONS
    # ══════════════════════════════════════════════════════════
    if terms_text.strip():
        terms_hdr = Table(
            [[P("<b><u>Terms &amp; Condition of Sale</u></b>", size=9)]],
            colWidths=[UW]
        )
        terms_hdr.setStyle(TableStyle([
            ('LINEABOVE',     (0, 0), (-1, -1), 0.5, BLACK),
            ('TOPPADDING',    (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING',   (0, 0), (-1, -1), 5),
        ]))
        story.append(terms_hdr)

        term_rows = []
        for j, line in enumerate(terms_text.split('\n'), 1):
            if line.strip():
                term_rows.append([P(f"{j}.", size=8, align=TA_RIGHT),
                                   P(line.strip(), size=8, fontName=_HINDI_FONT)])
        if term_rows:
            tl = Table(term_rows, colWidths=[8 * mm, UW - 10 * mm])
            tl.setStyle(TableStyle([
                ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING',    (0, 0), (-1, -1), 1),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                ('LEFTPADDING',   (0, 0), (-1, -1), 5),
                ('RIGHTPADDING',  (0, 0), (-1, -1), 2),
            ]))
            story.append(tl)
        story.append(Spacer(1, 2 * mm))

    if notes.strip():
        notes_tbl = Table(
            [[P(f"<b>Notes:</b> {notes}", size=8)]],
            colWidths=[UW]
        )
        notes_tbl.setStyle(TableStyle([
            ('LINEABOVE',     (0, 0), (-1, -1), 0.5, BLACK),
            ('TOPPADDING',    (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING',   (0, 0), (-1, -1), 5),
        ]))
        story.append(notes_tbl)

    # ══════════════════════════════════════════════════════════
    # 8. FOOTER
    # ══════════════════════════════════════════════════════════
    jur = f"SUBJECT TO {jurisdiction.upper()} JURISDICTION" if jurisdiction else ""
    footer_tbl = Table(
        [[P(jur, size=7, bold=True),
          P("NOTE :- FOR ANY TYPE OF EXCHANGE OR SALE THE BILL IS COMPULSORY",
            size=7, bold=True, align=TA_CENTER),
          P("Sign &amp; Seal", size=7, bold=True, align=TA_RIGHT)]],
        colWidths=[UW * 0.30, UW * 0.50, UW * 0.20]
    )
    footer_tbl.setStyle(TableStyle([
        ('LINEABOVE',     (0, 0), (-1, -1), 1.5, BLACK),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING',   (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(footer_tbl)

    # ── Build PDF ─────────────────────────────────────────────
    doc = SimpleDocTemplate(
        path, pagesize=A4,
        rightMargin=margin, leftMargin=margin,
        topMargin=margin,   bottomMargin=margin
    )
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)

    # Remove temporary Qt-rendered PNG files
    for _f in _tmp_files:
        try:
            os.remove(_f)
        except Exception:
            pass


# ── Print via Qt (preview or direct) ─────────────────────────
def print_invoice(invoice: dict, parent=None, preview=True):
    try:
        from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog, QPrintDialog
        from PyQt5.QtGui import QTextDocument
        from PyQt5.QtCore import QSizeF

        html = _build_html_preview(invoice)
        doc  = QTextDocument()
        doc.setHtml(html)
        doc.setPageSize(QSizeF(595, 842))

        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageSize(QPrinter.A4)

        if preview:
            dialog = QPrintPreviewDialog(printer, parent)
            dialog.setWindowTitle("Invoice Print Preview")
            dialog.paintRequested.connect(doc.print)
            dialog.exec()
        else:
            dialog = QPrintDialog(printer, parent)
            if dialog.exec() == QPrintDialog.Accepted:
                doc.print(printer)

    except Exception:
        traceback.print_exc()
        reply = QMessageBox.question(
            parent, "Printer Not Available",
            "Could not open print dialog.\nSave as PDF instead?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            save_invoice_as_pdf(invoice, parent)


def _build_html_preview(invoice: dict) -> str:
    """Minimal HTML for Qt print preview — mirrors the reference layout."""
    from collections import OrderedDict as _OD
    shop     = AppConfig.shop()
    items    = invoice.get("items", [])
    subtotal = float(invoice.get("subtotal",   0))
    cgst_pct = float(invoice.get("cgst_percent", 1.5))
    sgst_pct = float(invoice.get("sgst_percent", 1.5))
    igst_pct = float(invoice.get("igst_percent", 0))
    cgst_amt = float(invoice.get("cgst_amount", round(subtotal * cgst_pct / 100, 2)))
    sgst_amt = float(invoice.get("sgst_amount", round(subtotal * sgst_pct / 100, 2)))
    igst_amt = float(invoice.get("igst_amount", round(subtotal * igst_pct / 100, 2)))
    grand    = float(invoice.get("grand_total", subtotal + cgst_amt + sgst_amt + igst_amt))
    round_off = float(invoice.get("round_off", round(grand - (subtotal + cgst_amt + sgst_amt + igst_amt), 2)))
    _cash_h  = float(invoice.get("cash_paid",    0))
    _upi_h   = float(invoice.get("upi_paid",     0))
    _card_h  = float(invoice.get("card_paid",    0))
    _chq_h   = float(invoice.get("cheque_paid",  0))
    _op_h    = float(invoice.get("old_purchase", 0))
    _adv_h   = float(invoice.get("advance_paid", 0))
    _tp_h    = _cash_h + _upi_h + _card_h + _chq_h + _op_h + _adv_h
    total_paid_html = _tp_h if _tp_h > 0 else grand

    # Build purity → metal-name lookup
    try:
        from services.metal_service import get_metals as _gm2
        _mmap = {m.get('purity','').strip().upper(): m.get('name','')
                 for m in _gm2() if m.get('purity')}
    except Exception:
        _mmap = {}

    def _mlabel(purity):
        metal = _mmap.get(purity.strip().upper(), '')
        return f"{metal} {purity}".strip() if metal else purity

    def _item_metal(purity: str) -> str:
        metal = _mmap.get(purity.strip().upper(), '')
        return metal if metal else purity

    # Group items by metal name
    _grps = _OD()
    for _it in items:
        _p  = (_it.get('purity') or 'Other').strip()
        _mn = _item_metal(_p)
        _grps.setdefault(_mn, []).append(_it)

    rows_html = ""
    serial = 0
    for metal_name, grp_items in _grps.items():
        gw_grp = nw_grp = amt_grp = 0.0
        for it in grp_items:
            gw  = float(it.get('weight', 0))
            lw  = float(it.get('less_weight', 0))
            nw  = round(gw - lw, 3)
            mk     = float(it.get('making_charge', 0))
            mk_pct = float(it.get('making_pct',    0))
            mk_s   = f"{mk_pct:.2f}%" if mk_pct > 0 else f"₹{mk:,.2f}"
            gw_grp += gw; nw_grp += nw; amt_grp += float(it.get('total', 0))
            serial += 1
            rows_html += (
                f"<tr>"
                f"<td>{serial}</td>"
                f"<td>{it.get('tag','')}</td>"
                f"<td style='text-align:left'><b>{it.get('name','')}</b>"
                f"<br/><small style='color:#555'>{it.get('category','')}</small></td>"
                f"<td>{it.get('huid','')}</td>"
                f"<td>{it.get('hsn_code','7113')}</td>"
                f"<td>{it.get('purity','')}</td>"
                f"<td>{it.get('quantity','')}</td>"
                f"<td>{gw:.2f}</td><td>{lw:.2f}</td><td>{nw:.2f}</td>"
                f"<td>{float(it.get('rate',0)):.0f}</td>"
                f"<td>{mk_s}</td>"
                f"<td><b>{float(it.get('total',0)):,.2f}</b></td>"
                f"</tr>"
            )
        # Metal total row — always shown
        rows_html += (
            f"<tr style='background:#e4e4e4;font-weight:bold;'>"
            f"<td colspan='7' style='text-align:left;padding-left:8px;'>"
            f"{metal_name} Total</td>"
            f"<td>{gw_grp:.2f}</td>"
            f"<td></td>"
            f"<td>{nw_grp:.2f}</td>"
            f"<td></td><td></td>"
            f"<td>{amt_grp:,.2f}</td>"
            f"</tr>"
        )

    r_off = (f"- {abs(round_off):.2f}" if round_off < 0
             else f"+ {round_off:.2f}" if round_off > 0 else "0.00")

    mob = shop.get('mobile', '')
    mob2 = shop.get('mobile2', '')
    mob_str = mob + (f" / {mob2}" if mob2 else "")

    return f"""<!DOCTYPE html><html><head>
<meta charset="UTF-8"/>
<style>
  *{{margin:0;padding:0;box-sizing:border-box;}}
  body{{font-family:Arial,sans-serif;font-size:11px;background:#fff;padding:8px;}}
  .invoice{{border:1.5px solid #000;width:100%;}}
  .top-bar{{display:flex;justify-content:space-between;padding:3px 8px;
            border-bottom:1px solid #000;font-size:10px;}}
  .header{{display:flex;align-items:center;padding:6px 8px;
           border-bottom:1px solid #000;gap:6px;}}
  .logo-box{{width:70px;height:70px;border:1.5px solid #000;display:flex;
             flex-direction:column;align-items:center;justify-content:center;
             font-weight:900;font-size:22px;}}
  .shop-ctr{{flex:1;text-align:center;}}
  .shop-name{{font-size:26px;font-weight:900;}}
  .shop-tag{{font-size:10px;font-style:italic;}}
  .bis-box{{width:70px;height:70px;border:1.5px solid #000;display:flex;
            flex-direction:column;align-items:center;justify-content:center;
            font-size:8px;font-weight:700;text-align:center;}}
  .tax-strip{{text-align:center;font-weight:700;font-size:12px;letter-spacing:3px;
              padding:4px;border-bottom:1px solid #000;text-decoration:underline;}}
  .info-row{{display:flex;border-bottom:1px solid #000;}}
  .customer{{flex:1;padding:4px 8px;font-size:11px;}}
  .inv-meta{{width:220px;border-left:1px solid #000;padding:4px 8px;font-size:11px;}}
  .customer .r,.inv-meta .r{{display:flex;justify-content:space-between;margin-bottom:2px;}}
  table{{width:100%;border-collapse:collapse;font-size:10px;}}
  th{{border:1px solid #000;padding:3px;text-align:center;background:#f5f5f5;
      font-size:9px;}}
  td{{border:1px solid #000;padding:3px;text-align:center;}}
  .bottom{{display:flex;border-top:1px solid #000;}}
  .left-bot{{flex:1;border-right:1px solid #000;}}
  .pay-box,.words-box,.bank-box{{padding:5px 8px;border-bottom:1px solid #000;}}
  .bank-box{{border-bottom:none;}}
  .right-bot{{width:220px;font-size:11px;}}
  .srow{{display:flex;justify-content:space-between;padding:3px 8px;
         border-bottom:1px solid #000;}}
  .srow.net{{font-weight:700;font-size:12px;background:#f0f0f0;
             border-top:2px solid #000;}}
  .sig{{padding:8px;text-align:center;font-size:10px;border-top:1px solid #000;}}
  .terms{{border-top:1px solid #000;padding:5px 8px;font-size:10px;}}
  .footer{{border-top:2px solid #000;padding:3px 8px;display:flex;
           justify-content:space-between;font-size:9px;font-weight:600;}}
</style></head><body>
<div class="invoice">
  <div class="top-bar">
    <span>GSTIN :- {shop.get('gst_number','')}</span>
    <span>&#x936;&#x94d;&#x930;&#x940; &#x917;&#x923;&#x947;&#x936;&#x93e;&#x92f; &#x928;&#x92e;&#x903;</span>
    <span>Mobile :- {mob_str}</span>
  </div>
  <div class="header">
    <div class="logo-box" style="font-size:18px"><b>{shop.get('shop_name','')[:3].upper()}</b>
      <div style="font-size:7px">JEWELLERS</div></div>
    <div class="shop-ctr">
      <div class="shop-name">{shop.get('shop_name','')}</div>
      <div class="shop-tag">{shop.get('tagline','')}</div>
      <div style="font-size:10px">{shop.get('address','')}</div>
    </div>
    <div class="bis-box">BIS<br/>HALLMARK<br/>CERTIFIED</div>
  </div>
  <div class="tax-strip">T A X &nbsp; I N V O I C E</div>
  <div class="info-row">
    <div class="customer">
      <div class="r"><span><b>Name :-</b></span><span>{invoice.get('customer_name','')}</span></div>
      <div class="r"><span><b>Address :-</b></span><span>{invoice.get('customer_address','')}</span></div>
      <div class="r"><span><b>Phone No.</b></span><span>{invoice.get('customer_mobile','')}</span></div>
      <div class="r"><span><b>Customer GST :-</b></span><span>{invoice.get('customer_gst','')}</span></div>
    </div>
    <div class="inv-meta">
      <div class="r"><span><b>INVOICE DATE :</b></span><span>{invoice.get('date','')}</span></div>
      <div class="r"><span><b>INVOICE NO. :-</b></span><span>{invoice.get('invoice_number','')}</span></div>
      <div class="r" style="font-size:10px;margin-top:4px;border-top:1px solid #ccc;padding-top:3px">
        <span><b>{shop.get('state','')}</b></span>
        <span style="font-style:italic;color:#555">Original Copy</span>
      </div>
    </div>
  </div>
  <table>
    <thead><tr>
      <th>S.No</th><th>Tag/Rfid</th><th style="text-align:left">Item Name</th>
      <th>Huid/Remarks</th><th>Hsn</th><th>Purity</th><th>Pcs</th>
      <th>Gross Wt</th><th>Less</th><th>Nett Wt</th>
      <th>Rate</th><th>Mk/Chrg</th><th>Amount</th>
    </tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
  <div class="bottom">
    <div class="left-bot">
      <div class="pay-box">
        <div><u><b>Payment Detail :</b></u></div>
        {f'<div style="display:flex;justify-content:space-between"><b>Cash</b><span style="padding-right:6px">&#x20B9; {_cash_h:,.0f} /-</span></div>' if _cash_h > 0 else ""}
        {f'<div style="display:flex;justify-content:space-between"><b>UPI</b><span style="padding-right:6px">&#x20B9; {_upi_h:,.0f} /-</span></div>' if _upi_h > 0 else ""}
        {f'<div style="display:flex;justify-content:space-between"><b>Card</b><span style="padding-right:6px">&#x20B9; {_card_h:,.0f} /-</span></div>' if _card_h > 0 else ""}
        {f'<div style="display:flex;justify-content:space-between"><b>Cheque</b><span style="padding-right:6px">&#x20B9; {_chq_h:,.0f} /-</span></div>' if _chq_h > 0 else ""}
        {f'<div style="display:flex;justify-content:space-between"><b>Old Purchase (-)</b><span style="padding-right:6px">&#x20B9; {_op_h:,.0f} /-</span></div>' if _op_h > 0 else ""}
        {f'<div style="display:flex;justify-content:space-between"><b>Advance (-)</b><span style="padding-right:6px">&#x20B9; {_adv_h:,.0f} /-</span></div>' if _adv_h > 0 else ""}
        <div style="display:flex;justify-content:space-between">
          <b>TOTAL PAYMENT -</b><span style="padding-right:6px"><b>&#x20B9; {total_paid_html:,.0f} /-</b></span>
        </div>
      </div>
      <div class="words-box">
        <div><u><b>Amount In Word</b></u></div>
        <div><i>Rupees: {amount_in_words(grand)}</i></div>
      </div>
      <div class="bank-box">
        <div><u><b>Bank Detail :</b></u></div>
        <div>Bank Name :- {shop.get('bank_name','')}</div>
        <div>A/c No. :- {shop.get('account_number','')}</div>
        <div>IFSC :- {shop.get('ifsc_code','')}</div>
      </div>
    </div>
    <div class="right-bot">
      <div class="srow"><span>Gross Amount</span><span>{subtotal:,.2f}</span></div>
      <div class="srow"><span>CGST @ {cgst_pct}%</span><span>{cgst_amt:.2f}</span></div>
      <div class="srow"><span>SGST @ {sgst_pct}%</span><span>{sgst_amt:.2f}</span></div>
      <div class="srow"><span>Amt After GST</span><span>{subtotal+cgst_amt+sgst_amt:.2f}</span></div>
      <div class="srow"><span>Round Off</span><span>{r_off}</span></div>
      <div class="srow net"><span>Net Payable</span><span>{grand:,.2f}</span></div>
      <div class="sig">________________________<br/>Customer's Signature</div>
    </div>
  </div>
  <div class="terms"><b><u>Terms &amp; Condition of Sale</u></b><br/>
    {shop.get('terms','').replace(chr(10),'<br/>')}
  </div>
  <div class="footer">
    <span>SUBJECT TO {shop.get('jurisdiction','').upper()} JURISDICTION</span>
    <span>NOTE :- FOR ANY TYPE OF EXCHANGE OR SALE THE BILL IS COMPULSORY</span>
    <span>Sign &amp; Seal</span>
  </div>
</div>
</body></html>"""
