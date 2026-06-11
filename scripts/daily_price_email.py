#!/usr/bin/env python3
"""
Daily market outlook email: USD/IDR exchange rate + gold price.
Runs via GitHub Actions every day at 23:00 UTC (06:00 WIB).
"""

import os
import smtplib
import requests
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo


def fetch_usd_idr():
    resp = requests.get("https://open.er-api.com/v6/latest/USD", timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data["rates"]["IDR"]


def fetch_gold_price():
    """Return (current_price_usd, prev_close_usd) for gold futures (GC=F)."""
    url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; DailyPriceBot/1.0)"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    meta = resp.json()["chart"]["result"][0]["meta"]
    return meta["regularMarketPrice"], meta["chartPreviousClose"]


def fmt_idr(value):
    return f"Rp {value:,.0f}"


def fmt_usd(value):
    return f"${value:,.2f}"


def change_badge(current, prev):
    if not prev:
        return ""
    pct = (current - prev) / prev * 100
    sign = "+" if pct >= 0 else ""
    color = "#22c55e" if pct >= 0 else "#ef4444"
    return (
        f'<span style="color:{color};font-weight:700;font-size:15px;">'
        f"{sign}{pct:.2f}%</span>"
    )


def build_html(usd_idr, gold_usd, gold_prev):
    wib = ZoneInfo("Asia/Jakarta")
    now = datetime.now(wib)
    date_str = now.strftime("%A, %d %B %Y")
    time_str = now.strftime("%H:%M WIB")

    gold_idr = gold_usd * usd_idr if gold_usd and usd_idr else None
    gold_change_html = change_badge(gold_usd, gold_prev) if gold_usd and gold_prev else "—"

    usd_idr_display = fmt_idr(usd_idr) if usd_idr else "N/A"
    gold_usd_display = fmt_usd(gold_usd) if gold_usd else "N/A"
    gold_idr_display = fmt_idr(gold_idr) if gold_idr else "N/A"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Daily Market Outlook</title>
</head>
<body style="margin:0;padding:0;background:#f5f5f4;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">
<div style="max-width:560px;margin:40px auto;background:#ffffff;border-radius:14px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.09);">

  <!-- Header -->
  <div style="background:#1a1a1a;padding:28px 32px 24px;">
    <p style="margin:0;color:#737373;font-size:11px;letter-spacing:0.12em;text-transform:uppercase;font-weight:600;">Daily Market Outlook</p>
    <h1 style="margin:8px 0 0;color:#ffffff;font-size:22px;font-weight:700;letter-spacing:-0.02em;">{date_str}</h1>
    <p style="margin:6px 0 0;color:#525252;font-size:13px;">Prices as of {time_str}</p>
  </div>

  <!-- USD/IDR -->
  <div style="padding:28px 32px 0;">
    <p style="margin:0 0 10px;font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#737373;">USD / IDR Exchange Rate</p>
    <div style="background:#fafaf8;border:1px solid #e5e2dd;border-radius:10px;padding:22px 24px;">
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td>
            <p style="margin:0;font-size:13px;color:#737373;font-weight:500;">1 USD equals</p>
            <p style="margin:6px 0 0;font-size:32px;font-weight:700;color:#1a1a1a;letter-spacing:-0.03em;font-family:'Courier New',Courier,monospace;">{usd_idr_display}</p>
          </td>
          <td style="text-align:right;vertical-align:top;">
            <span style="display:inline-block;background:#1a1a1a;color:#ffffff;font-size:11px;font-weight:600;padding:4px 10px;border-radius:20px;letter-spacing:0.05em;">IDR</span>
          </td>
        </tr>
      </table>
    </div>
  </div>

  <!-- Gold -->
  <div style="padding:20px 32px 0;">
    <p style="margin:0 0 10px;font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#737373;">Gold Price (XAU — per Troy Oz)</p>
    <div style="background:#fafaf8;border:1px solid #e5e2dd;border-radius:10px;padding:22px 24px;">

      <!-- USD row -->
      <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:18px;">
        <tr>
          <td>
            <p style="margin:0;font-size:13px;color:#737373;font-weight:500;">Price in USD</p>
            <p style="margin:6px 0 0;font-size:32px;font-weight:700;color:#1a1a1a;letter-spacing:-0.03em;font-family:'Courier New',Courier,monospace;">{gold_usd_display}</p>
          </td>
          <td style="text-align:right;vertical-align:middle;">
            <p style="margin:0;font-size:11px;color:#a3a3a3;margin-bottom:4px;">vs prev. close</p>
            {gold_change_html}
          </td>
        </tr>
      </table>

      <!-- IDR row -->
      <div style="border-top:1px solid #e5e2dd;padding-top:16px;">
        <p style="margin:0;font-size:13px;color:#737373;font-weight:500;">Price in IDR</p>
        <p style="margin:6px 0 0;font-size:26px;font-weight:700;color:#1a1a1a;letter-spacing:-0.02em;font-family:'Courier New',Courier,monospace;">{gold_idr_display}</p>
      </div>
    </div>
  </div>

  <!-- Footer -->
  <div style="padding:24px 32px 28px;margin-top:20px;border-top:1px solid #e5e2dd;">
    <p style="margin:0;font-size:12px;color:#a3a3a3;line-height:1.6;">
      Sources: Open Exchange Rates (USD/IDR) &amp; Yahoo Finance (Gold futures GC=F).<br>
      Market data may be delayed up to 15–20 minutes. Automated daily briefing.
    </p>
  </div>

</div>
</body>
</html>"""


def main():
    sender = os.environ["GMAIL_USER"]
    app_password = os.environ["GMAIL_APP_PASSWORD"]
    recipient = os.environ.get("RECIPIENT_EMAIL", "soegeng.wibowo@gmail.com")

    print("Fetching USD/IDR rate...")
    usd_idr = fetch_usd_idr()
    print(f"  USD/IDR = {usd_idr:,.0f}")

    print("Fetching gold price...")
    gold_usd, gold_prev = fetch_gold_price()
    print(f"  Gold = ${gold_usd:,.2f} (prev close ${gold_prev:,.2f})")

    wib = ZoneInfo("Asia/Jakarta")
    subject = f"Daily Market Outlook — {datetime.now(wib).strftime('%d %b %Y')}"
    html_body = build_html(usd_idr, gold_usd, gold_prev)

    print(f"Sending email to {recipient}...")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Market Outlook <{sender}>"
    msg["To"] = recipient
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, app_password)
        server.sendmail(sender, recipient, msg.as_string())

    print("Done.")


if __name__ == "__main__":
    main()
