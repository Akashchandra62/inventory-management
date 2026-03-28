# ============================================================
# printer_helper.py - PDF Invoice Generator
# Everything fetched from AppConfig / uploaded assets.
# Nothing is hardcoded.
# ============================================================

import os
import traceback

from PyQt6.QtWidgets import QMessageBox, QFileDialog
from app.config import AppConfig
from app.utils import format_currency
from app.constants import LOGO_FILE, QR_FILE


# ── Amount in Words ──────────────────────────────────────────
def amount_in_words(amount: float) -> str:
    try:
        ones = [
            '', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven',
            'Eight', 'Nine', 'Ten', 'Eleven', 'Twelve', 'Thirteen',
            'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen'
        ]
        tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty',
                'Sixty', 'Seventy', 'Eighty', 'Ninety']

        def words(n):
            if n == 0:
                return ''
            elif n < 20:
                return ones[n]
            elif n < 100:
                return tens[n // 10] + (' ' + ones[n % 10] if n % 10 else '')
            elif n < 1000:
                return ones[n // 100] + ' Hundred' + (' ' + words(n % 100) if n % 100 else '')
            elif n < 100000:
                return words(n // 1000) + ' Thousand' + (' ' + words(n % 1000) if n % 1000 else '')
            elif n < 10000000:
                return words(n // 100000) + ' Lakh' + (' ' + words(n % 100000) if n % 100000 else '')
            else:
                return words(n // 10000000) + ' Crore' + (' ' + words(n % 10000000) if n % 10000000 else '')

        rupees = int(amount)
        paise  = round((amount - rupees) * 100)
        result = 'Rupees ' + words(rupees) if rupees else 'Rupees Zero'
        if paise:
            result += ' and ' + words(paise) + ' Paise'
        return (result + ' Only').strip()
    except Exception:
        return ''


# ── Main PDF Generator ────────────────────────────────────────
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


def _generate_pdf(invoice: dict, path: str):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle,
        Paragraph, Spacer, HRFlowable, Image as RLImage
    )
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

    # ── All data from AppConfig (settings) ───────────────────
    shop = AppConfig.shop()

    shop_name    = shop.get("shop_name", "")
    tagline      = shop.get("tagline", "")
    address      = shop.get("address", "")
    mobile       = shop.get("mobile", "")
    mobile2      = shop.get("mobile2", "")
    state        = shop.get("state", "")
    jurisdiction = shop.get("jurisdiction", "")
    bank_name    = shop.get("bank_name", "")
    acc_name     = shop.get("account_name", "")
    acc_no       = shop.get("account_number", "")
    branch       = shop.get("bank_branch", "")
    ifsc         = shop.get("ifsc_code", "")
    terms_text   = shop.get("terms", "")

    # ── Invoice data ─────────────────────────────────────────
    customer_name    = invoice.get("customer_name", "")
    customer_address = invoice.get("customer_address", "")
    customer_mobile  = invoice.get("customer_mobile", "")
    customer_gst     = invoice.get("customer_gst", "")
    inv_number       = invoice.get("invoice_number", "")
    inv_date         = invoice.get("date", "")
    items            = invoice.get("items", [])
    subtotal         = float(invoice.get("subtotal", 0))
    cgst_pct         = float(invoice.get("cgst_percent", 1.5))
    sgst_pct         = float(invoice.get("sgst_percent", 1.5))
    cgst_amt         = round(subtotal * cgst_pct / 100, 2)
    sgst_amt         = round(subtotal * sgst_pct / 100, 2)
    amt_after_gst    = round(subtotal + cgst_amt + sgst_amt, 2)
    grand_total      = float(invoice.get("grand_total", amt_after_gst))
    cash_paid        = float(invoice.get("cash_paid", 0))
    due_amount       = float(invoice.get("due_amount", 0))
    due_date         = invoice.get("due_date", "")
    notes            = invoice.get("notes", "")

    # ── Page setup ───────────────────────────────────────────
    W = 190 * mm

    doc = SimpleDocTemplate(
        path, pagesize=A4,
        rightMargin=10*mm, leftMargin=10*mm,
        topMargin=8*mm, bottomMargin=8*mm
    )

    # ── Style helpers ─────────────────────────────────────────
    def S(name, **kw):
        return ParagraphStyle(name, **kw)

    s_ganesh   = S('g',  fontSize=8,  alignment=TA_CENTER, textColor=colors.HexColor('#8B0000'))
    s_shopname = S('sn', fontSize=20, alignment=TA_CENTER, fontName='Helvetica-Bold',
                   textColor=colors.HexColor('#8B0000'), spaceAfter=0, spaceBefore=0)
    s_tagline  = S('tl', fontSize=9,  alignment=TA_CENTER, fontName='Helvetica-Oblique', spaceAfter=0)
    s_address  = S('ad', fontSize=8,  alignment=TA_CENTER, spaceAfter=0)
    s_mobile   = S('mb', fontSize=8,  alignment=TA_CENTER, fontName='Helvetica-Bold', spaceAfter=0)
    s_tax_inv  = S('ti', fontSize=11, alignment=TA_CENTER, fontName='Helvetica-Bold',
                   spaceBefore=2, spaceAfter=2)
    s_normal   = S('nm', fontSize=8)
    s_bold     = S('bd', fontSize=8,  fontName='Helvetica-Bold')
    s_right    = S('rt', fontSize=8,  alignment=TA_RIGHT)
    s_bold_r   = S('br', fontSize=8,  fontName='Helvetica-Bold', alignment=TA_RIGHT)
    s_italic   = S('it', fontSize=8,  fontName='Helvetica-Oblique')
    s_footer   = S('ft', fontSize=7,  alignment=TA_CENTER, textColor=colors.grey)
    s_section  = S('sc', fontSize=8,  fontName='Helvetica-Bold')
    s_terms    = S('tm', fontSize=7,  leading=10)

    def cell(txt, bold=False, align=TA_CENTER, size=7):
        fn = 'Helvetica-Bold' if bold else 'Helvetica'
        return Paragraph(str(txt), S('c', fontSize=size, alignment=align, fontName=fn, leading=9))

    story = []

    # ── HEADER: each element added one by one — NO overlap possible ──
    if os.path.exists(LOGO_FILE):
        try:
            logo_tbl = Table([[RLImage(LOGO_FILE, width=20*mm, height=20*mm)]], colWidths=[W])
            logo_tbl.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
            story.append(logo_tbl)
        except Exception:
            pass

    story.append(Paragraph("|| श्री गणेशाय नमः ||", s_ganesh))
    story.append(Spacer(1, 1*mm))
    story.append(Paragraph(shop_name, s_shopname))
    story.append(Spacer(1, 1*mm))
    if tagline:
        story.append(Paragraph(tagline, s_tagline))
        story.append(Spacer(1, 1*mm))
    if address:
        story.append(Paragraph(address, s_address))
        story.append(Spacer(1, 1*mm))

    mob_line = f"Mobile No.: {mobile}"
    if mobile2:
        mob_line += f"  &nbsp;&nbsp;  {mobile2}"
    story.append(Paragraph(mob_line, s_mobile))
    story.append(Spacer(1, 2*mm))
    story.append(HRFlowable(width=W, thickness=1.5, color=colors.black, spaceAfter=2))
    story.append(Paragraph("TAX INVOICE", s_tax_inv))
    story.append(HRFlowable(width=W, thickness=0.5, color=colors.black, spaceAfter=3))

    # ── CUSTOMER + INVOICE META ───────────────────────────────
    meta = [
        [Paragraph(f"<b>Name :</b> {customer_name}", s_normal),
         Paragraph(f"<b>Invoice Date :</b> {inv_date}", s_normal)],
        [Paragraph(f"<b>Address :</b> {customer_address}", s_normal),
         Paragraph(f"<b>Invoice No. :</b> {inv_number}", s_normal)],
        [Paragraph(f"<b>Phone No. :</b> {customer_mobile}", s_normal),
         Paragraph(f"<b>State :</b> {state}", s_normal)],
        [Paragraph(f"<b>Customer GST No. :</b> {customer_gst}", s_normal),
         Paragraph("Original Copy", s_bold_r)],
    ]
    meta_tbl = Table(meta, colWidths=[W * 0.55, W * 0.45])
    meta_tbl.setStyle(TableStyle([
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(meta_tbl)
    story.append(HRFlowable(width=W, thickness=0.5, color=colors.black, spaceBefore=3, spaceAfter=3))

    # ── ITEMS TABLE ───────────────────────────────────────────
    col_headers = [
        'S.No', 'Particulars /\nItem', 'HSN\nCode', 'Purity\nKt/Ct',
        'Pcs /\nQty', 'Gross Wt.\n(In Gm)', 'Less Wt.\n(In Gm)',
        'Nett Wt.\n(In Gm)', 'Rate\nPer Gm.', 'Mk/Oth.Chrg.\nPer Gm./Pcs.',
        'Amount\n(INR)'
    ]
    col_w = [8*mm, 32*mm, 13*mm, 12*mm, 9*mm, 16*mm, 15*mm, 15*mm, 14*mm, 22*mm, 18*mm]

    rows      = [[cell(h, bold=True) for h in col_headers]]
    gross_tot = 0.0
    nett_tot  = 0.0

    for i, item in enumerate(items, 1):
        gross_wt = float(item.get('weight', 0))
        less_wt  = float(item.get('less_weight', 0))
        nett_wt  = round(gross_wt - less_wt, 3)
        rate     = float(item.get('rate', 0))
        making   = float(item.get('making_charge', 0))
        amt      = float(item.get('total', 0))

        gross_tot += gross_wt
        nett_tot  += nett_wt

        making_str = f"{making:.2f}%" if making <= 100 else f"Rs{making:.2f}"

        rows.append([
            cell(i),
            cell(item.get('name', ''), align=TA_LEFT),
            cell(item.get('hsn_code', '7113')),
            cell(item.get('purity', '')),
            cell(item.get('quantity', 1)),
            cell(f"{gross_wt:.3f}"),
            cell(f"{less_wt:.3f}"),
            cell(f"{nett_wt:.3f}"),
            cell(f"{rate:.0f}"),
            cell(making_str),
            cell(f"{amt:.2f}"),
        ])

    # 2 empty rows for spacing
    empty_row = [cell('') for _ in col_headers]
    rows.append(empty_row)
    rows.append(empty_row)

    # Totals row
    rows.append([
        cell(''), cell('', bold=True), cell(''), cell(''), cell(''),
        cell(f"{gross_tot:.3f}", bold=True),
        cell(''),
        cell(f"{nett_tot:.3f}", bold=True),
        cell(''), cell(''),
        cell(f"{subtotal:.2f}", bold=True),
    ])

    items_tbl = Table(rows, colWidths=col_w, repeatRows=1)
    items_tbl.setStyle(TableStyle([
        ('BACKGROUND',     (0, 0),  (-1, 0),  colors.HexColor('#e8e8e8')),
        ('TEXTCOLOR',      (0, 0),  (-1, 0),  colors.black),
        ('ALIGN',          (0, 0),  (-1, -1), 'CENTER'),
        ('VALIGN',         (0, 0),  (-1, -1), 'MIDDLE'),
        ('FONTSIZE',       (0, 0),  (-1, -1), 7),
        ('GRID',           (0, 0),  (-1, -1), 0.4, colors.black),
        ('TOPPADDING',     (0, 0),  (-1, -1), 2),
        ('BOTTOMPADDING',  (0, 0),  (-1, -1), 2),
        ('ROWBACKGROUNDS', (0, 1),  (-1, -2), [colors.white, colors.HexColor('#fffef0')]),
        ('BACKGROUND',     (0, -1), (-1, -1), colors.HexColor('#f0f0f0')),
        ('FONTNAME',       (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    story.append(items_tbl)
    story.append(Spacer(1, 3*mm))

    # ── PAYMENT + TOTALS ─────────────────────────────────────
    pay_rows = [
        [Paragraph('<b>Payment Detail :</b>', s_section), ''],
        [Paragraph('Cash Payment',    s_normal), Paragraph(f'{cash_paid:.2f} /-',           S('pr',  fontSize=8, alignment=TA_RIGHT))],
        [Paragraph('Total Payment -', s_normal), Paragraph(f'{cash_paid:.2f} /-',           S('pr2', fontSize=8, alignment=TA_RIGHT))],
        [Paragraph('Due & Due date',  s_normal), Paragraph(f'{due_amount:.2f}  {due_date}', S('pr3', fontSize=8, alignment=TA_RIGHT))],
    ]
    pay_tbl = Table(pay_rows, colWidths=[35*mm, 30*mm])
    pay_tbl.setStyle(TableStyle([
        ('SPAN',          (0, 0), (1, 0)),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('FONTSIZE',      (0, 0), (-1, -1), 8),
        ('ALIGN',         (1, 1), (1, -1),  'RIGHT'),
    ]))

    totals_rows = [
        [Paragraph('Gross Amount',       s_normal), Paragraph(f': {subtotal:.2f}',      s_normal)],
        [Paragraph(f'CGST@ {cgst_pct}%', s_normal), Paragraph(f': {cgst_amt:.2f}',     s_normal)],
        [Paragraph(f'SGST@ {sgst_pct}%', s_normal), Paragraph(f': {sgst_amt:.2f}',     s_normal)],
        [Paragraph('Amt After GST',       s_normal), Paragraph(f': {amt_after_gst:.2f}', s_normal)],
        [Paragraph('Net Payable',         s_bold),   Paragraph(f': {grand_total:.2f}',   s_bold)],
        [Paragraph('Dues',                s_normal), Paragraph(f': {due_amount:.2f}',    s_normal)],
    ]
    totals_tbl = Table(totals_rows, colWidths=[28*mm, 24*mm])
    totals_tbl.setStyle(TableStyle([
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('FONTSIZE',      (0, 0), (-1, -1), 8),
        ('LINEABOVE',     (0, 4), (-1, 4),  0.5, colors.black),
    ]))

    bottom_tbl = Table([[pay_tbl, totals_tbl]], colWidths=[95*mm, 95*mm])
    bottom_tbl.setStyle(TableStyle([
        ('VALIGN',     (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(bottom_tbl)
    story.append(HRFlowable(width=W, thickness=0.5, color=colors.black, spaceBefore=3, spaceAfter=3))

    # ── AMOUNT IN WORDS ───────────────────────────────────────
    story.append(Paragraph("<b>Amount In Word</b>", s_section))
    story.append(Paragraph(amount_in_words(grand_total), s_italic))
    story.append(HRFlowable(width=W, thickness=0.5, color=colors.black, spaceBefore=3, spaceAfter=3))

    # ── BANK DETAILS + QR + CUSTOMER SIGNATURE ───────────────
    bank_lines = (
        f"<b>Bank Details :</b><br/>"
        f"Bank Name :- {bank_name}<br/>"
        f"A/c Name :- {acc_name}<br/>"
        f"A/c No. :- {acc_no}<br/>"
        f"Branch {branch}<br/>"
        f"IFSC :- {ifsc}"
    )

    if os.path.exists(QR_FILE):
        try:
            qr_cell = [RLImage(QR_FILE, width=30*mm, height=30*mm)]
        except Exception:
            qr_cell = [Paragraph("", s_normal)]
    else:
        qr_cell = [Paragraph("", s_normal)]

    bank_sig = [[
        Paragraph(bank_lines, s_normal),
        qr_cell,
        Paragraph("Customer's Signature", s_right)
    ]]
    bank_tbl = Table(bank_sig, colWidths=[W * 0.45, 35*mm, W * 0.30])
    bank_tbl.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (0, 0),   'TOP'),
        ('VALIGN',        (1, 0), (1, 0),   'MIDDLE'),
        ('VALIGN',        (2, 0), (2, 0),   'BOTTOM'),
        ('ALIGN',         (1, 0), (1, 0),   'CENTER'),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(bank_tbl)
    story.append(HRFlowable(width=W, thickness=0.5, color=colors.black, spaceBefore=3, spaceAfter=3))

    # ── TERMS & CONDITIONS ────────────────────────────────────
    if terms_text.strip():
        story.append(Paragraph("<b>Terms & Condition of Sale</b>", s_section))
        for line in terms_text.split('\n'):
            if line.strip():
                story.append(Paragraph(line.strip(), s_terms))
        story.append(Spacer(1, 3*mm))

    if notes.strip():
        story.append(Paragraph(f"<b>Notes:</b> {notes}", s_normal))
        story.append(Spacer(1, 2*mm))

    # ── FOOTER ───────────────────────────────────────────────
    story.append(HRFlowable(width=W, thickness=0.5, color=colors.grey, spaceAfter=2))
    if jurisdiction:
        story.append(Paragraph(f"SUBJECT TO {jurisdiction.upper()} JURISDICTION", s_footer))
    story.append(Paragraph("NOTE :- FOR ANY TYPE OF EXCHANGE OR SALE THE BILL IS COMPULSORY.", s_footer))
    story.append(Spacer(1, 4*mm))

    sign_tbl = Table([['', Paragraph("Sign & Seal", S('ss', fontSize=8, alignment=TA_RIGHT, fontName='Helvetica-Bold'))]], colWidths=[W * 0.7, W * 0.3])
    story.append(sign_tbl)

    doc.build(story)


# ── Print via Qt (fallback to PDF) ───────────────────────────
def print_invoice(invoice: dict, parent=None, preview=True):
    try:
        from PyQt6.QtPrintSupport import QPrinter, QPrintPreviewDialog, QPrintDialog
        from PyQt6.QtGui import QTextDocument, QPageSize
        from PyQt6.QtCore import QSizeF

        html = _build_html_preview(invoice)
        doc  = QTextDocument()
        doc.setHtml(html)
        doc.setPageSize(QSizeF(595, 842))

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))

        if preview:
            dialog = QPrintPreviewDialog(printer, parent)
            dialog.setWindowTitle("Invoice Print Preview")
            dialog.paintRequested.connect(doc.print)
            dialog.exec()
        else:
            dialog = QPrintDialog(printer, parent)
            if dialog.exec() == QPrintDialog.DialogCode.Accepted:
                doc.print(printer)

    except Exception:
        traceback.print_exc()
        reply = QMessageBox.question(
            parent, "Printer Not Available",
            "Could not open print dialog.\nSave as PDF instead?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            save_invoice_as_pdf(invoice, parent)


def _build_html_preview(invoice: dict) -> str:
    shop  = AppConfig.shop()
    items = invoice.get("items", [])
    rows  = ""
    for i, item in enumerate(items, 1):
        rows += (
            f"<tr>"
            f"<td>{i}</td><td>{item.get('name','')}</td>"
            f"<td>{item.get('purity','')}</td>"
            f"<td>{item.get('quantity','')}</td>"
            f"<td>{item.get('weight','')}</td>"
            f"<td>{item.get('less_weight',0)}</td>"
            f"<td>{format_currency(item.get('rate',0))}</td>"
            f"<td>{format_currency(item.get('making_charge',0))}</td>"
            f"<td><b>{format_currency(item.get('total',0))}</b></td>"
            f"</tr>"
        )
    subtotal = invoice.get('subtotal', 0)
    cgst_pct = invoice.get('cgst_percent', 1.5)
    sgst_pct = invoice.get('sgst_percent', 1.5)
    cgst_amt = round(subtotal * cgst_pct / 100, 2)
    sgst_amt = round(subtotal * sgst_pct / 100, 2)
    grand    = invoice.get('grand_total', 0)

    return f"""<html><body style="font-family:Arial;font-size:11px;margin:20px">
    <h2 style="text-align:center;color:#8B0000">{shop.get('shop_name','')}</h2>
    <p style="text-align:center">{shop.get('tagline','')}</p>
    <p style="text-align:center">{shop.get('address','')} | {shop.get('mobile','')}</p>
    <h3 style="text-align:center">TAX INVOICE</h3>
    <p><b>Invoice No:</b> {invoice.get('invoice_number','')} &nbsp;&nbsp;
       <b>Date:</b> {invoice.get('date','')}</p>
    <p><b>Customer:</b> {invoice.get('customer_name','')} &nbsp;&nbsp;
       <b>Mobile:</b> {invoice.get('customer_mobile','')}</p>
    <table width="100%" border="1" cellspacing="0" cellpadding="4">
    <tr style="background:#e8e8e8;color:black">
        <th>#</th><th>Item</th><th>Purity</th><th>Qty</th>
        <th>Gross Wt</th><th>Less Wt</th><th>Rate</th><th>Making</th><th>Amount</th>
    </tr>{rows}
    </table>
    <br>
    <p style="text-align:right">Gross Amount: {format_currency(subtotal)}</p>
    <p style="text-align:right">CGST @{cgst_pct}%: {format_currency(cgst_amt)}</p>
    <p style="text-align:right">SGST @{sgst_pct}%: {format_currency(sgst_amt)}</p>
    <p style="text-align:right"><b>Net Payable: {format_currency(grand)}</b></p>
    <p><i>{amount_in_words(grand)}</i></p>
    </body></html>"""