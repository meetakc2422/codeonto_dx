"""Picture cards for WhatsApp image alerts: a clean Codeonto-branded PNG listing the outlets (and items) behind an
alert, drawn as HTML and screenshotted with Playwright's Chromium (already installed for the collector logins).
A card shows up to MAX_ROWS rows, then "+N more on the dashboard"."""

import base64
import html
from pathlib import Path

from .common import log

ROOT = Path(__file__).resolve().parent.parent.parent
LOGO = ROOT / "frontend" / "assets" / "logo-full.png"
MAX_ROWS = 12
THEMES = {
    "offline": {"accent": "#e5484d", "soft": "#fff1f1", "tag": "OUTLETS OFFLINE"},
    "oos": {"accent": "#f5a524", "soft": "#fff8eb", "tag": "ITEMS OUT OF STOCK"},
}


def _logo() -> str:
    try:
        return "data:image/png;base64," + base64.b64encode(LOGO.read_bytes()).decode()
    except OSError:
        return ""


def _page(kind: str, title: str, subtitle: str, rows: list[tuple[str, str, str]]) -> str:
    """rows: (outlet, detail, right-hand note)."""
    t, e = THEMES[kind], html.escape
    shown, rest = rows[:MAX_ROWS], len(rows) - MAX_ROWS
    logo = _logo()
    items = "".join(f"""<div class="row"><div class="dot"></div><div class="txt"><b>{e(o)}</b><span>{e(d)}</span></div><em>{e(n)}</em></div>"""
                    for o, d, n in shown)
    more = f'<div class="more">+{rest} more on the Codeonto dashboard</div>' if rest > 0 else ""
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
      * {{ box-sizing: border-box; margin: 0; }}
      body {{ width: 1080px; font-family: Inter, -apple-system, "Segoe UI", Roboto, Arial, sans-serif; background: #f4f6fa; padding: 36px; color: #0b1229; }}
      .card {{ background: #fff; border-radius: 26px; overflow: hidden; box-shadow: 0 8px 30px rgba(11,18,41,.08); }}
      .head {{ background: #0b1229; color: #fff; padding: 30px 36px; display: flex; justify-content: space-between; align-items: center; }}
      .head img {{ height: 38px; filter: brightness(0) invert(1); }}
      .tag {{ font-size: 15px; font-weight: 700; letter-spacing: .12em; padding: 8px 14px; border-radius: 999px; background: {t['accent']}; }}
      .title {{ padding: 30px 36px 6px; font-size: 40px; font-weight: 800; }}
      .sub {{ padding: 0 36px 24px; font-size: 21px; color: #64748b; }}
      .list {{ padding: 0 24px 18px; }}
      .row {{ display: flex; align-items: center; gap: 16px; padding: 16px 14px; border-top: 1px solid #eef1f5; }}
      .dot {{ width: 14px; height: 14px; border-radius: 50%; background: {t['accent']}; flex: none; }}
      .txt {{ display: flex; flex-direction: column; gap: 4px; min-width: 0; flex: 1; }}
      .txt b {{ font-size: 23px; }}
      .txt span {{ font-size: 19px; color: #475569; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }}
      em {{ font-style: normal; font-size: 18px; font-weight: 600; color: {t['accent']}; background: {t['soft']}; padding: 6px 12px; border-radius: 10px; white-space: nowrap; }}
      .more {{ margin: 6px 14px 0; padding: 14px; text-align: center; font-size: 19px; color: #64748b; background: #f8fafc; border-radius: 12px; }}
      .foot {{ padding: 18px 36px 26px; font-size: 17px; color: #94a3b8; }}
    </style></head><body><div class="card">
      <div class="head">{f'<img src="{logo}">' if logo else '<b style="font-size:28px">Codeonto</b>'}<span class="tag">{t['tag']}</span></div>
      <div class="title">{e(title)}</div><div class="sub">{e(subtitle)}</div>
      <div class="list">{items}{more}</div>
      <div class="foot">Codeonto · live monitoring · open the dashboard for details</div>
    </div></body></html>"""


def render(kind: str, title: str, subtitle: str, rows: list[tuple[str, str, str]]) -> bytes | None:
    """PNG bytes, or None if the card can't be drawn (the caller then sends the text template)."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page(viewport={"width": 1080, "height": 800}, device_scale_factor=1)
                page.set_content(_page(kind, title, subtitle, rows), wait_until="load")
                return page.locator(".card").screenshot(type="png")
            finally:
                browser.close()
    except Exception as e:
        log.warning("alert card not drawn (%s); sending text instead", e)
        return None
