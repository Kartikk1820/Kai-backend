"""Salary / incentive slip PDF rendering — KQT template design.

Rendering uses Playwright (headless Chromium). A minimal-PDF fallback is kept
so a missing browser never breaks the download endpoint.

One-time setup after `pip install -r requirements.txt`:
    playwright install --with-deps chromium
"""
import calendar
import datetime
import structlog

from .utils import amount_to_words_inr

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Colours (from KQT_Payslip_Template.docx)
# ---------------------------------------------------------------------------
_DARK_BLUE   = '#043AA7'   # header bar, section headers, gross/total row
_MID_BLUE    = '#2CA0ED'   # NET PAY box
_TITLE_BLUE  = '#3270DF'   # title band
_ROW_LIGHT   = '#EBF4FE'   # label cells, employee details rows
_ROW_ALT     = '#F5F5F5'   # alternating earnings/deductions rows
_LOP_YELLOW  = '#FFF8E1'   # LOP calculation note box

SLIP_HTML = """\
<!doctype html><html><head><meta charset="utf-8"><style>
@page {{ size: A4; margin: 0; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: Arial, Helvetica, sans-serif; font-size: 11px;
        color: #1a1a1a; background: white; }}
.wrap {{ max-width: 794px; margin: 0 auto; padding: 28px 36px; }}

/* ── Header ── */
.hdr {{ display: flex; align-items: flex-start; gap: 16px;
        border-bottom: 3px solid {dark_blue}; padding-bottom: 12px; margin-bottom: 10px; }}
.hdr-logo {{ width: 56px; height: 56px; border: 1px solid #ccc;
              display: flex; align-items: center; justify-content: center;
              font-size: 9px; color: #888; flex-shrink: 0; }}
.hdr-text {{ flex: 1; }}
.hdr-company {{ font-size: 15px; font-weight: 700; color: {dark_blue}; }}
.hdr-address {{ font-size: 9.5px; color: #555; margin-top: 3px; line-height: 1.5; }}

/* ── Title band ── */
.title-band {{ background: {title_blue}; color: white; text-align: center;
               padding: 9px 0; margin-bottom: 12px; }}
.title-band h1 {{ font-size: 13px; font-weight: 700; letter-spacing: 1.5px;
                   text-transform: uppercase; }}
.title-band p  {{ font-size: 10px; margin-top: 2px; opacity: .9; }}

/* ── Section heading ── */
.sec-head {{ font-size: 11px; font-weight: 700; color: {dark_blue};
             border-bottom: 1.5px solid {dark_blue};
             padding-bottom: 3px; margin: 12px 0 6px; text-transform: uppercase;
             letter-spacing: .5px; }}

/* ── 4-col detail table (Employee Details / Attendance) ── */
.dtbl {{ width: 100%; border-collapse: collapse; margin-bottom: 4px; }}
.dtbl td {{ padding: 5px 8px; font-size: 10.5px; border: 1px solid #d0d8e8; }}
.dtbl .lbl {{ background: {row_light}; font-weight: 600; color: #333; width: 20%; }}
.dtbl .val {{ background: #fff; width: 30%; }}

/* ── Salary particulars (4-col side-by-side) ── */
.stbl {{ width: 100%; border-collapse: collapse; margin-bottom: 4px; }}
.stbl td {{ padding: 5px 8px; font-size: 10.5px; border: 1px solid #d0d8e8; }}
.stbl .shdr {{ background: {dark_blue}; color: white; font-weight: 700;
               font-size: 11px; text-transform: uppercase; letter-spacing: .5px; }}
.stbl .slbl {{ width: 27%; }}
.stbl .samt {{ width: 23%; text-align: right; font-variant-numeric: tabular-nums; }}
.stbl .srow-alt {{ background: {row_alt}; }}
.stbl .srow-even {{ background: #fff; }}
.stbl .stotal {{ background: {dark_blue}; color: white; font-weight: 700; }}
.stbl .stotal .samt {{ color: #ffe082; }}
.zero {{ color: #b0b0b0; }}

/* ── Net Pay band ── */
.net-band {{ display: flex; margin: 10px 0 8px; border: 1px solid #d0d8e8; }}
.net-words {{ flex: 1; background: {row_light}; padding: 10px 12px;
              font-size: 10.5px; line-height: 1.6; }}
.net-words strong {{ font-size: 11px; color: {dark_blue}; }}
.net-box {{ background: {mid_blue}; color: white; padding: 10px 18px;
            min-width: 160px; display: flex; flex-direction: column;
            align-items: center; justify-content: center; text-align: center; }}
.net-box .nl {{ font-size: 11px; font-weight: 700; opacity: .9;
                text-transform: uppercase; letter-spacing: .5px; }}
.net-box .na {{ font-size: 18px; font-weight: 800;
                font-variant-numeric: tabular-nums; margin-top: 4px; }}

/* ── LOP note box ── */
.lop-box {{ background: {lop_yellow}; border: 1px solid #e0c87a;
            padding: 9px 12px; font-size: 10px; line-height: 1.7; }}
.lop-box strong {{ color: {dark_blue}; }}

/* ── Footer ── */
.footer {{ margin-top: 18px; border-top: 1px solid #ccc;
           padding-top: 10px; display: flex; justify-content: space-between; }}
.footer-note {{ font-size: 9px; color: #888; line-height: 1.7; }}
.sig-line {{ width: 140px; border-top: 1px solid #aaa; padding-top: 5px;
              font-size: 9.5px; color: #555; text-align: center; }}
</style></head><body>
<div class="wrap">

  <!-- Header -->
  <div class="hdr">
    <div class="hdr-logo">Logo</div>
    <div class="hdr-text">
      <div class="hdr-company">{company_name}</div>
      <div class="hdr-address">{company_address}<br>{company_cin}</div>
    </div>
  </div>

  <!-- Title band -->
  <div class="title-band">
    <h1>Payslip / Salary Statement</h1>
    <p>For the Month of {month_name} {year}</p>
  </div>

  <!-- Employee Details -->
  <div class="sec-head">Employee Details</div>
  <table class="dtbl">
    <tr>
      <td class="lbl">Employee Name</td><td class="val">{employee_name}</td>
      <td class="lbl">Employee ID</td><td class="val">EMP-{employee_id:04d}</td>
    </tr>
    <tr>
      <td class="lbl">Designation</td><td class="val">{designation}</td>
      <td class="lbl">Department</td><td class="val">{department}</td>
    </tr>
    <tr>
      <td class="lbl">Date of Joining</td><td class="val">{date_of_joining}</td>
      <td class="lbl">Pay Period</td><td class="val">{month_name} {year}</td>
    </tr>
    <tr>
      <td class="lbl">Bank Name</td><td class="val">{bank_name}</td>
      <td class="lbl">Account No.</td><td class="val">{account_no}</td>
    </tr>
    <tr>
      <td class="lbl">PAN Number</td><td class="val">{pan_number}</td>
      <td class="lbl">UAN Number</td><td class="val">{uan_number}</td>
    </tr>
    <tr>
      <td class="lbl">Working Days</td><td class="val">{total_working_days}</td>
      <td class="lbl">Days Paid For</td><td class="val">{days_paid_for}</td>
    </tr>
  </table>

  <!-- Attendance & Leave Details -->
  <div class="sec-head">Attendance &amp; Leave Details</div>
  <table class="dtbl">
    <tr>
      <td class="lbl">Total Working Days</td><td class="val">{total_working_days}</td>
      <td class="lbl">Paid Leave Availed</td><td class="val">{paid_leave_days}</td>
    </tr>
    <tr>
      <td class="lbl">Days Present</td><td class="val">{days_present}</td>
      <td class="lbl">Loss of Pay (LOP) Days</td><td class="val">{lop_days}</td>
    </tr>
    <tr>
      <td class="lbl">Weekly Offs</td><td class="val">{weekly_offs}</td>
      <td class="lbl">Public Holidays</td><td class="val">{public_holidays}</td>
    </tr>
  </table>

  <!-- Salary Particulars -->
  <div class="sec-head">Salary Particulars</div>
  <table class="stbl">
    <tr>
      <td class="shdr slbl">Earnings</td>
      <td class="shdr samt">Amount (&#8377;)</td>
      <td class="shdr slbl">Deductions</td>
      <td class="shdr samt">Amount (&#8377;)</td>
    </tr>
    {salary_rows}
    <tr>
      <td class="stotal slbl">Gross Earnings</td>
      <td class="stotal samt">&#8377; {gross_earnings}</td>
      <td class="stotal slbl">Total Deductions</td>
      <td class="stotal samt">&#8377; {total_deductions}</td>
    </tr>
  </table>

  <!-- Net Pay -->
  <div class="net-band">
    <div class="net-words">
      <strong>Net Pay in Words:</strong><br>
      {net_pay_words} Only
    </div>
    <div class="net-box">
      <div class="nl">Net Pay</div>
      <div class="na">&#8377; {net_amount}</div>
    </div>
  </div>

  {lop_note}

  <!-- Footer -->
  <div class="footer">
    <div class="footer-note">
      Generated on {generated}<br>
      This is a computer-generated document and does not require a physical signature.
    </div>
    <div class="sig-line">Authorised Signatory</div>
  </div>

</div></body></html>
"""


def _fmt(value) -> str:
    return f"{float(value):,.2f}"


def _fmt_days(value) -> str:
    f = float(value)
    return str(int(f)) if f == int(f) else f"{f:.1f}"


def _earn_row(label, value, row_class) -> str:
    cls = f'{row_class} zero' if float(value) == 0 else row_class
    return (
        f'<td class="slbl {cls}">{label}</td>'
        f'<td class="samt {cls}">&#8377; {_fmt(value)}</td>'
    )


def _ded_row(label, value, row_class) -> str:
    cls = f'{row_class} zero' if float(value) == 0 else row_class
    return (
        f'<td class="slbl {cls}">{label}</td>'
        f'<td class="samt {cls}">&#8377; {_fmt(value)}</td>'
    )


def _build_salary_rows(record) -> str:
    """Build the paired earnings|deductions rows of the salary particulars table.

    Earnings: 7 lines (Basic, HRA, Special, Conveyance, Medical, Performance Bonus, Other)
    Deductions: 5 lines (PT, TDS, LOP, Advance Recovery, Other)
    Earnings has more rows — pad deductions side with empty cells.
    """
    earn_items = [
        ('Basic Salary', record.basic_salary),
        ('House Rent Allowance (HRA)', record.hra),
        ('Special Allowance', record.special_allowance),
        ('Conveyance Allowance', record.conveyance_allowance),
        ('Medical Allowance', record.medical_allowance),
        ('Performance Bonus', record.performance_bonus),
        ('Other Allowance', record.other_allowance),
    ]
    lop_label = (f"Loss of Pay (LOP) Deduction"
                 f" ({_fmt_days(record.lop_days)} day{'s' if float(record.lop_days) != 1 else ''})")
    ded_items = [
        ('Professional Tax (PT)', record.professional_tax),
        ('Tax Deducted at Source (TDS)', record.tds_deduction),
        (lop_label, record.lop_deduction),
        ('Advance Recovery', record.advance_recovery),
        ('Other Deduction (if any)', record.other_deductions),
    ]

    # Incentive slip: only show the incentive_amount row
    if record.slip_type == 'incentive':
        earn_items = [('Incentive / Bonus', record.incentive_amount)]
        ded_items = []

    rows = []
    max_len = max(len(earn_items), len(ded_items))
    for i in range(max_len):
        row_class = 'srow-alt' if i % 2 == 0 else 'srow-even'
        ecells = _earn_row(*earn_items[i], row_class) if i < len(earn_items) else (
            f'<td class="slbl {row_class}"></td><td class="samt {row_class}"></td>'
        )
        dcells = _ded_row(*ded_items[i], row_class) if i < len(ded_items) else (
            f'<td class="slbl {row_class}"></td><td class="samt {row_class}"></td>'
        )
        rows.append(f'<tr>{ecells}{dcells}</tr>')
    return '\n    '.join(rows)


def _build_lop_note(record) -> str:
    if float(record.lop_days) == 0:
        return ''
    wd = record.total_working_days or 1
    per_day = float(record.basic_salary) / wd if wd else 0
    return (
        f'<div class="lop-box">'
        f'<strong>LOP (Loss of Pay) Calculation Note</strong><br>'
        f'LOP Deduction Formula: LOP Amount = (Gross Monthly Salary &divide; Total Working Days) &times; LOP Days<br>'
        f'LOP Days for this month: {_fmt_days(record.lop_days)}'
        f'&nbsp;&nbsp;|&nbsp;&nbsp;Per-Day Rate: &#8377; {per_day:,.2f}'
        f'&nbsp;&nbsp;|&nbsp;&nbsp;Total LOP Deduction: &#8377; {_fmt(record.lop_deduction)}'
        f'</div>'
    )


def _get_bank_info(employee):
    acct = employee.bank_accounts.filter(is_active=True).first()
    if acct:
        return acct.bank_name, acct.account_number
    return '—', '—'


def build_slip_html(record) -> str:
    emp = record.employee
    bank_name, account_no = _get_bank_info(emp)

    doj = emp.date_of_joining.strftime('%d/%m/%Y') if emp.date_of_joining else '—'
    pan = emp.pan_number or '—'
    uan = (emp.uan_number if (emp.uan_number and getattr(emp, 'is_pf_applicable', False))
           else 'N/A (PF not applicable)')
    designation = emp.sub_position or '—'
    department = emp.department.name if (hasattr(emp, 'department') and emp.department_id) else '—'

    # For incentive slips the attendance block is not meaningful — use zeros shown
    days_paid = _fmt_days(record.days_paid_for) if record.slip_type == 'salary' else '—'
    att_fields = {
        'total_working_days': record.total_working_days if record.slip_type == 'salary' else '—',
        'days_present': _fmt_days(record.days_present) if record.slip_type == 'salary' else '—',
        'paid_leave_days': _fmt_days(record.paid_leave_days) if record.slip_type == 'salary' else '—',
        'weekly_offs': record.weekly_offs if record.slip_type == 'salary' else '—',
        'public_holidays': record.public_holidays if record.slip_type == 'salary' else '—',
        'lop_days': _fmt_days(record.lop_days) if record.slip_type == 'salary' else '—',
    }

    return SLIP_HTML.format(
        dark_blue=_DARK_BLUE,
        mid_blue=_MID_BLUE,
        title_blue=_TITLE_BLUE,
        row_light=_ROW_LIGHT,
        row_alt=_ROW_ALT,
        lop_yellow=_LOP_YELLOW,
        company_name='Kaushik Quantum Technologies Pvt. Ltd.',
        company_address='315, Khera Delhi – 110082, India',
        company_cin='CIN: U62090DL2024PTC436525',
        employee_name=(f"{emp.first_name} {emp.last_name}".strip() or emp.email),
        employee_id=emp.id,
        designation=designation,
        department=department,
        date_of_joining=doj,
        month_name=calendar.month_name[record.month],
        year=record.year,
        bank_name=bank_name,
        account_no=account_no,
        pan_number=pan,
        uan_number=uan,
        days_paid_for=days_paid,
        **att_fields,
        salary_rows=_build_salary_rows(record),
        gross_earnings=_fmt(record.gross_earnings),
        total_deductions=_fmt(record.total_deductions),
        net_pay_words=amount_to_words_inr(record.net_amount),
        net_amount=_fmt(record.net_amount),
        lop_note=_build_lop_note(record),
        generated=datetime.date.today().strftime('%d %b %Y'),
    )


def render_slip_pdf(record) -> bytes:
    html = build_slip_html(record)
    try:
        return _render_with_playwright(html)
    except Exception as exc:  # pragma: no cover
        logger.warning('slip_pdf_playwright_failed', error=str(exc),
                       hint="Run: playwright install --with-deps chromium")
        text = (f"KAI {record.get_slip_type_display()} Slip - "
                f"{record.month}/{record.year} - Net {record.net_amount}")
        return _minimal_pdf(text)


def _render_with_playwright(html: str) -> bytes:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(args=['--no-sandbox', '--disable-dev-shm-usage'])
        try:
            page = browser.new_page()
            page.set_content(html, wait_until='networkidle')
            pdf_bytes = page.pdf(format='A4', print_background=True,
                                 margin={'top': '0', 'bottom': '0', 'left': '0', 'right': '0'})
        finally:
            browser.close()
    return pdf_bytes


def _minimal_pdf(text: str) -> bytes:
    text = text.replace('(', '').replace(')', '')
    content = f"BT /F1 14 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = b"%PDF-1.4\n"
    offsets = []
    for i, o in enumerate(objs, 1):
        offsets.append(len(pdf))
        pdf += b"%d 0 obj\n%s\nendobj\n" % (i, o)
    xref = len(pdf)
    pdf += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offsets:
        pdf += b"%010d 00000 n \n" % off
    pdf += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (len(objs) + 1, xref)
    return pdf
