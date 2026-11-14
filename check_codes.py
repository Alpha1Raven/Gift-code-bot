
import os
import re
import json
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

WEBHOOK = os.environ["DISCORD_WEBHOOK_URL"]
STATE_FILE = Path("posted_codes.json")

SOURCES = [
    "https://www.pocketgamer.com/warline-sniper-strike/codes/",
    "https://game-go.wiki/warline/guides/gift-codes/",
]

# Recognize Warline's known code formats.
CODE_PATTERN = re.compile(
    r"\b(?:WARLINE[A-Z0-9]{2,15}|GUIDEMAKER|"
    r"HALLOW33N)\b",
    re.IGNORECASE,
)

HEADERS = {
    "User-Agent": "WarlineCodeMonitor/1.0"
}

def find_codes():
    found = {}

    for url in SOURCES:
        try:
            response = requests.get(
                url, headers=HEADERS, timeout=20
            )
            response.raise_for_status()

            soup = BeautifulSoup(
                response.text, "html.parser"
            )

            # Focus on article content where possible.
            article = (
                soup.find("article")
                or soup.find("main")
                or soup
            )

            # Exclude expired-code sections where
            # their headings can be identified.
            for heading in article.find_all(
                ["h2", "h3", "h4"]
            ):
                if "expired" in heading.get_text(
                    " ", strip=True
                ).lower():
                    for sibling in list(
                        heading.next_siblings
                    ):
                        if getattr(
                            sibling, "name", None
                        ) in ["h2", "h3", "h4"]:
                            break
                        if hasattr(sibling, "decompose"):
                            sibling.decompose()
                    heading.decompose()

            text = article.get_text(" ", strip=True)

            for code in CODE_PATTERN.findall(text):
                code = code.upper()
                found.setdefault(code, url)

            print(f"Checked {url}")

        except requests.RequestException as exc:
            print(f"Could not check {url}: {exc}")

        time.sleep(2)

    return found


def send_to_discord(code, source):
    payload = {
        "username": "Warline Gift Code Bot",
        "allowed_mentions": {"parse": []},
        "embeds": [{
            "title": "🎁 Warline Gift Code Found!",
            "description": (
                f"⚔️ **Potential new gift code:**\n"
                f"```{code}```\n"
                "📱 **How to redeem:**\n"
                "Profile → Gift Code → Exchange\n\n"
                "⚠️ Code validity is not guaranteed."
            ),
            "color": 5763719,
            "fields": [{
                "name": "🔎 Source",
                "value": f"[View source]({source})"
            }],
            "footer": {
                "text": "Warline Alliance • Automated Code Alerts"
            }
        }]
    }

    response = requests.post(
        WEBHOOK, json=payload, timeout=20
    )
    response.raise_for_status()


def main():
    found = find_codes()

    if not found:
        print("No candidate codes found.")
        return

    if STATE_FILE.exists():
        posted = set(json.loads(
            STATE_FILE.read_text()
        ))
    else:
        posted = set()

    new_codes = sorted(set(found) - posted)

    for code in new_codes:
        send_to_discord(code, found[code])
        posted.add(code)
        STATE_FILE.write_text(
            json.dumps(sorted(posted), indent=2)
        )
        print(f"Posted: {code}")

    print(f"Finished. {len(new_codes)} new codes.")


if __name__ == "__main__":
    main()
