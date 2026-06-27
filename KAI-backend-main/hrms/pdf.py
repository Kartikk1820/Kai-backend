"""Salary / incentive slip PDF rendering.

Rendering uses Playwright (headless Chromium) so slips render with full CSS,
web fonts, and the exact KAI navy/gold theme. A minimal-PDF fallback is kept
so a missing browser never breaks the download endpoint.

One-time setup after `pip install -r requirements.txt`:
    playwright install --with-deps chromium
"""
import calendar
import datetime
import structlog

logger = structlog.get_logger(__name__)


SLIP_HTML = """
<!doctype html><html><head><meta charset="utf-8"><style>
  @page {{ size: A4; margin: 0; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #1a1a1a; background: white; }}
  .wrap {{ max-width: 794px; margin: 0 auto; padding: 44px 48px; }}

  .header {{ display: flex; justify-content: space-between; align-items: flex-start;
             padding-bottom: 20px; border-bottom: 3px solid #172c47; margin-bottom: 22px; }}
  .brand-name {{ font-size: 26px; font-weight: 800; color: #172c47; letter-spacing: 1.5px; }}
  .brand-sub {{ font-size: 10px; color: #9e7f43; text-transform: uppercase; letter-spacing: 2px; margin-top: 4px; }}
  .slip-title-block {{ text-align: right; }}
  .slip-title-block h1 {{ font-size: 14px; font-weight: 700; color: #172c47; text-transform: uppercase; letter-spacing: 1px; }}
  .slip-title-block p {{ font-size: 12px; color: #737373; margin-top: 5px; }}
  .status-chip {{ display: inline-block; margin-top: 8px; padding: 3px 12px; border-radius: 20px;
                  font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; }}
  .chip-sent {{ background: #d1fae5; color: #065f46; }}
  .chip-gen  {{ background: #dbeafe; color: #1e40af; }}

  .emp-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0;
               border: 1px solid #e0e0e0; border-radius: 6px; overflow: hidden; margin-bottom: 22px; }}
  .emp-cell {{ display: flex; justify-content: space-between; align-items: center;
               padding: 9px 16px; border-bottom: 1px solid #f0f0f0; font-size: 12.5px; }}
  .emp-cell:nth-child(odd) {{ background: #f8f9fb; border-right: 1px solid #e0e0e0; }}
  .emp-cell:last-child, .emp-cell:nth-last-child(2) {{ border-bottom: none; }}
  .emp-label {{ color: #737373; }}
  .emp-val {{ font-weight: 600; color: #1a1a1a; }}

  .pay-row-outer {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }}
  .pay-block {{ border: 1px solid #e0e0e0; border-radius: 6px; overflow: hidden; }}
  .pay-head {{ padding: 10px 16px; font-size: 11px; font-weight: 700;
               text-transform: uppercase; letter-spacing: 1px; color: white; }}
  .pay-head.earn {{ background: #172c47; }}
  .pay-head.deduct {{ background: #7f1d1d; }}
  .pay-line {{ display: flex; justify-content: space-between; padding: 9px 16px;
               font-size: 13px; border-bottom: 1px solid #f5f5f5; }}
  .pay-line:last-child {{ border-bottom: none; font-weight: 700; background: #f8f9fb; }}
  .pay-amt {{ font-variant-numeric: tabular-nums; }}

  .net-box {{ background: linear-gradient(135deg, #172c47 0%, #0d1f36 100%); color: white;
              border-radius: 8px; padding: 22px 28px;
              display: flex; justify-content: space-between; align-items: center; }}
  .net-label {{ font-size: 14px; opacity: .75; margin-bottom: 4px; }}
  .net-period {{ font-size: 11px; opacity: .5; }}
  .net-amount {{ font-size: 30px; font-weight: 800; color: #f0c96e; font-variant-numeric: tabular-nums; }}

  .footer {{ margin-top: 32px; display: flex; justify-content: space-between; align-items: flex-end;
             padding-top: 20px; border-top: 1px solid #e0e0e0; }}
  .footer-note {{ font-size: 10px; color: #a3a3a3; line-height: 1.6; }}
  .sig-line {{ width: 160px; border-top: 1px solid #aaa; padding-top: 6px;
               font-size: 10px; color: #737373; text-align: center; }}
</style></head><body>
<div class="wrap">
  <div class="header">
    <div>
      <div class="brand-name">KC PORTAL</div>
      <div class="brand-sub">Human Resource Management</div>
    </div>
    <div class="slip-title-block">
      <h1>{slip_type} Slip</h1>
      <p>Pay Period: {month_name} {year}</p>
      <span class="status-chip {status_class}">{status_label}</span>
    </div>
  </div>

  <div class="emp-grid">
    <div class="emp-cell"><span class="emp-label">Employee Name</span><span class="emp-val">{employee_name}</span></div>
    <div class="emp-cell"><span class="emp-label">Employee ID</span><span class="emp-val">EMP-{employee_id:04d}</span></div>
    <div class="emp-cell"><span class="emp-label">Entity</span><span class="emp-val">{entity}</span></div>
    <div class="emp-cell"><span class="emp-label">Pay Period</span><span class="emp-val">{month_name} {year}</span></div>
    <div class="emp-cell"><span class="emp-label">Email</span><span class="emp-val">{email}</span></div>
    <div class="emp-cell"><span class="emp-label">Generated On</span><span class="emp-val">{generated}</span></div>
  </div>

  <div class="pay-row-outer">
    <div class="pay-block">
      <div class="pay-head earn">Earnings</div>
      <div class="pay-line"><span>Base Salary</span><span class="pay-amt">&#8377; {base_salary}</span></div>
      <div class="pay-line"><span>Incentive / Bonus</span><span class="pay-amt">&#8377; {incentive_amount}</span></div>
      <div class="pay-line"><span>Gross Pay</span><span class="pay-amt">&#8377; {gross_pay}</span></div>
    </div>
    <div class="pay-block">
      <div class="pay-head deduct">Deductions</div>
      <div class="pay-line"><span>Advance Recovery</span><span class="pay-amt">&#8377; {advance_deduction}</span></div>
      <div class="pay-line"><span>Other Deductions</span><span class="pay-amt">&#8377; {other_deductions}</span></div>
      <div class="pay-line"><span>Total Deductions</span><span class="pay-amt">&#8377; {total_deductions}</span></div>
    </div>
  </div>

  <div class="net-box">
    <div>
      <div class="net-label">Net Pay</div>
      <div class="net-period">{month_name} {year}</div>
    </div>
    <div class="net-amount">&#8377; {net_amount}</div>
  </div>

  <div class="footer">
    <div class="footer-note">
      <div>Generated on {generated}</div>
      <div>This is a computer-generated document and does not require a physical signature.</div>
    </div>
    <div class="sig-line">Authorised Signatory</div>
  </div>
</div>
</body></html>
"""


def _fmt(value) -> str:
    return f"{float(value):,.2f}"


def build_slip_html(record) -> str:
    gross = float(record.base_salary) + float(record.incentive_amount)
    total_deductions = float(record.advance_deduction) + float(record.other_deductions)
    return SLIP_HTML.format(
        slip_type=record.get_slip_type_display(),
        employee_name=(f"{record.employee.first_name} {record.employee.last_name}".strip()
                       or record.employee.email),
        email=record.employee.email,
        employee_id=record.employee_id,
        month_name=calendar.month_name[record.month],
        year=record.year,
        entity=record.entity or '—',
        base_salary=_fmt(record.base_salary),
        incentive_amount=_fmt(record.incentive_amount),
        gross_pay=_fmt(gross),
        advance_deduction=_fmt(record.advance_deduction),
        other_deductions=_fmt(record.other_deductions),
        total_deductions=_fmt(total_deductions),
        net_amount=_fmt(record.net_amount),
        status_label='Sent' if record.status == 'sent' else 'Generated',
        status_class='chip-sent' if record.status == 'sent' else 'chip-gen',
        generated=datetime.date.today().strftime('%d %b %Y'),
    )


def render_slip_pdf(record) -> bytes:
    """Render the slip to PDF bytes via headless Chromium (Playwright)."""
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
    """Synchronous Playwright render. Safe to call from a Django request thread."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(args=['--no-sandbox', '--disable-dev-shm-usage'])
        try:
            page = browser.new_page()
            # wait until network idle so web fonts load before printing
            page.set_content(html, wait_until='networkidle')
            pdf_bytes = page.pdf(format='A4', print_background=True,
                                 margin={'top': '0', 'bottom': '0', 'left': '0', 'right': '0'})
        finally:
            browser.close()
    return pdf_bytes


def _minimal_pdf(text: str) -> bytes:
    """Dependency-free valid PDF, used only if Chromium is unavailable."""
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
