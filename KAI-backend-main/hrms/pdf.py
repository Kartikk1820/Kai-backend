"""Salary / incentive slip PDF rendering.

Rendering uses Playwright (headless Chromium) so slips render with full CSS,
web fonts, and the exact KAI navy/gold theme. A minimal-PDF fallback is kept
so a missing browser never breaks the download endpoint.

One-time setup after `pip install -r requirements.txt`:
    playwright install --with-deps chromium
"""
import datetime
import structlog

logger = structlog.get_logger(__name__)


SLIP_HTML = """
<!doctype html><html><head><meta charset="utf-8"><style>
  @page {{ size: A4; margin: 1.5cm; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: 'Manrope', 'Helvetica Neue', Arial, sans-serif; color: #1a1a1a; margin: 0; }}
  .header {{ border-bottom: 3px solid #9e7f43; padding-bottom: 12px; margin-bottom: 24px;
            display: flex; justify-content: space-between; align-items: flex-end; }}
  .brand {{ color: #172c47; font-size: 26px; font-weight: 800; letter-spacing: 1px; }}
  .title {{ color: #9e7f43; font-size: 13px; text-transform: uppercase; letter-spacing: 2px; font-weight: 700; }}
  .who {{ font-weight: 700; font-size: 15px; }}
  .meta {{ color: #737373; font-size: 12px; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 18px; }}
  td {{ padding: 9px 10px; border-bottom: 1px solid #e6e2d6; font-size: 13px; }}
  td.label {{ color: #737373; }}
  td.amt {{ text-align: right; font-variant-numeric: tabular-nums; }}
  tr.net td {{ background: #faf7f0; font-weight: 700; font-size: 15px; color: #172c47; border-bottom: none; }}
  .foot {{ margin-top: 40px; color: #a3a3a3; font-size: 11px; text-align: center; }}
</style></head><body>
  <div class="header">
    <div class="brand">KAI PORTAL</div>
    <div class="title">{slip_type} Slip</div>
  </div>
  <div class="who">{employee_name}</div>
  <div class="meta">Employee ID: {employee_id} &nbsp;·&nbsp; Period: {month}/{year} &nbsp;·&nbsp; Entity: {entity}</div>
  <table>
    <tr><td class="label">Base salary</td><td class="amt">{base_salary}</td></tr>
    <tr><td class="label">Incentive</td><td class="amt">{incentive_amount}</td></tr>
    <tr><td class="label">Advance recovery</td><td class="amt">- {advance_deduction}</td></tr>
    <tr><td class="label">Other deductions</td><td class="amt">- {other_deductions}</td></tr>
    <tr class="net"><td>Net amount</td><td class="amt">{net_amount}</td></tr>
  </table>
  <div class="foot">Generated on {generated} — This is a system-generated document.</div>
</body></html>
"""


def build_slip_html(record) -> str:
    return SLIP_HTML.format(
        slip_type=record.get_slip_type_display(),
        employee_name=(f"{record.employee.first_name} {record.employee.last_name}".strip()
                       or record.employee.email),
        employee_id=record.employee_id,
        month=record.month, year=record.year, entity=record.entity or '—',
        base_salary=record.base_salary, incentive_amount=record.incentive_amount,
        advance_deduction=record.advance_deduction, other_deductions=record.other_deductions,
        net_amount=record.net_amount,
        generated=datetime.date.today().isoformat(),
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
