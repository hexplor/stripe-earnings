#!/usr/bin/env python3
"""
Stripe Gross Volume - Argos GNOME Extension Script
Displays today's gross volume from Stripe in the Ubuntu top bar.
Refreshes every 5 minutes (configurable via filename).
"""

import json
import subprocess
import urllib.request
import urllib.error
from datetime import datetime


def get_api_key():
    try:
        result = subprocess.run(
            ["secret-tool", "lookup", "service", "stripe", "type", "api-key"],
            capture_output=True, text=True, timeout=5,
        )
        key = result.stdout.strip()
        return key if key else None
    except Exception:
        return None


GROSS_VOLUME_TYPES = {"charge", "payment"}


def fetch_gross_volume(api_key):
    """Fetch today's balance transactions and sum gross volume (charges + payments)."""
    today_start = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    totals = {}
    starting_after = None

    while True:
        url = (
            f"https://api.stripe.com/v1/balance_transactions"
            f"?created[gte]={today_start}&limit=100"
        )
        if starting_after:
            url += f"&starting_after={starting_after}"

        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {api_key}")

        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read().decode())

        for tx in data["data"]:
            if tx["type"] in GROSS_VOLUME_TYPES:
                cur = tx["currency"].upper()
                totals[cur] = totals.get(cur, 0) + tx["amount"]

        if not data["has_more"]:
            break
        starting_after = data["data"][-1]["id"]

    return totals


def format_amount(amount_minor, currency):
    """Format amount from minor units (e.g. cents) to display string."""
    amount = amount_minor / 100
    return f"{amount:,.2f} {currency}"


def main():
    api_key = get_api_key()
    if not api_key:
        print("\u26a0 Stripe")
        print("---")
        print("No API key in GNOME Keyring")
        print("Run in terminal: | font=monospace size=10")
        print("secret-tool store --label='Stripe API Key' service stripe type api-key | font=monospace size=10")
        return

    try:
        totals = fetch_gross_volume(api_key)

        if not totals:
            print("\U0001f4b0 0.00")
            print("---")
            print("No transactions today")
        else:
            # Main display - show primary (first/only) currency in top bar
            parts = [format_amount(amt, cur) for cur, amt in sorted(totals.items())]
            print(f"\U0001f4b0 {' | '.join(parts)}")
            print("---")
            print(f"Gross Volume \u2014 {datetime.now().strftime('%d.%m.%Y')} | size=12")
            for cur, amt in sorted(totals.items()):
                print(f"  {format_amount(amt, cur)} | size=11")

        print("---")
        print("Open Stripe Dashboard | href=https://dashboard.stripe.com")
        print("Refresh | refresh=true")

    except urllib.error.HTTPError as e:
        print("\u26a0 Stripe")
        print("---")
        print(f"HTTP Error {e.code}: {e.reason}")
    except Exception as e:
        print("\u26a0 Stripe")
        print("---")
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
