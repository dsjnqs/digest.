"""
Daily Digest generator (v4).

Builds a 6-section daily digest — Word, Fact, Quote, Image, Trivia, and
History "of the Day" — and writes it to README.md for GitHub Pages.

v4 changes:
- Removed the 4 sections that weren't backed by a live API (Question,
  Tip, Discovery, Idea of the Day). Every remaining section pulls fresh
  content from a real external source each run.

Each section still shows a description and a "Source" link, and
failures show the real error message instead of a generic one.
"""

import html
import json
import urllib.error
import urllib.request
from datetime import date, datetime, timezone

OUTPUT_FILE = "README.md"
TIMEOUT = 15
UA = {"User-Agent": "DailyDigestBot/1.0 (GitHub Actions daily job; no contact configured)"}

TODAY = date.today()


def get_json(url, headers=None):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


# Each section function returns (content_markdown, source_name, source_url).

# ---------------------------------------------------------------------
# 1. Word of the Day
# ---------------------------------------------------------------------
def word_of_the_day():
    source_name = "Random Word API + Free Dictionary API"
    source_url = "https://dictionaryapi.dev/"
    try:
        word = get_json("https://random-word-api.herokuapp.com/word")[0]
        entries = get_json(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}")
        meaning = entries[0]["meanings"][0]
        part_of_speech = meaning.get("partOfSpeech", "")
        definition_obj = meaning["definitions"][0]
        definition = definition_obj.get("definition", "")
        example = definition_obj.get("example")
        text = f"**{word}** *({part_of_speech})* — {definition}"
        if example:
            text += f"\n> _\"{example}\"_"
        return text, source_name, source_url
    except Exception as exc:
        text = f"_Word lookup failed today._\n\n**Error:** `{exc}`"
        return text, source_name, source_url


# ---------------------------------------------------------------------
# 2. Fact of the Day
# ---------------------------------------------------------------------
def fact_of_the_day():
    source_name = "Useless Facts API"
    source_url = "https://uselessfacts.jsph.pl/"
    try:
        data = get_json("https://uselessfacts.jsph.pl/api/v2/facts/random?language=en")
        return data["text"], source_name, source_url
    except Exception as exc:
        text = f"_Fact lookup failed today._\n\n**Error:** `{exc}`"
        return text, source_name, source_url


# ---------------------------------------------------------------------
# 3. Quote of the Day
# ---------------------------------------------------------------------
def quote_of_the_day():
    source_name = "ZenQuotes API"
    source_url = "https://zenquotes.io/"
    try:
        data = get_json("https://zenquotes.io/api/today")[0]
        return f"\"{data['q']}\" — {data['a']}", source_name, source_url
    except Exception as exc:
        text = f"_Quote lookup failed today._\n\n**Error:** `{exc}`"
        return text, source_name, source_url


# ---------------------------------------------------------------------
# 4. Image of the Day — Wikipedia Picture of the Day (no API key needed)
# ---------------------------------------------------------------------
def image_of_the_day():
    source_name = "Wikipedia Picture of the Day (Wikimedia REST API)"
    source_url = "https://en.wikipedia.org/wiki/Main_Page"
    y, m, d = TODAY.strftime("%Y"), TODAY.strftime("%m"), TODAY.strftime("%d")
    feed_url = f"https://en.wikipedia.org/api/rest_v1/feed/featured/{y}/{m}/{d}"
    try:
        data = get_json(feed_url)
        img = data.get("image")
        if not img:
            raise ValueError("today's featured-content feed has no 'image' entry yet")

        raw_title = img.get("title", "Picture of the Day")
        title = raw_title.replace("File:", "").replace("_", " ")
        img_url = (img.get("image") or {}).get("source") or (img.get("thumbnail") or {}).get("source")
        if not img_url:
            raise ValueError("image entry had no usable image URL")
        description = (img.get("description") or {}).get("text", "")
        file_page = img.get("file_page")

        body = f"![{title}]({img_url})\n\n**{title}**\n\n{description}"
        if file_page:
            body += f"\n\n[View full details on Wikimedia Commons]({file_page})"
        return body, source_name, source_url
    except Exception as exc:
        text = f"_Couldn't reach Wikipedia's Picture of the Day feed today._\n\n**Error:** `{exc}`"
        return text, source_name, source_url


# ---------------------------------------------------------------------
# 5. Trivia of the Day
# ---------------------------------------------------------------------
def trivia_of_the_day():
    source_name = "Open Trivia Database"
    source_url = "https://opentdb.com/"
    try:
        data = get_json("https://opentdb.com/api.php?amount=1&type=multiple")
        q = data["results"][0]
        question = html.unescape(q["question"])
        correct = html.unescape(q["correct_answer"])
        category = html.unescape(q["category"])
        difficulty = q.get("difficulty", "").capitalize()
        text = f"**[{category} · {difficulty}]** {question}\n> Answer: ||{correct}||"
        return text, source_name, source_url
    except Exception as exc:
        text = f"_Trivia lookup failed today._\n\n**Error:** `{exc}`"
        return text, source_name, source_url


# ---------------------------------------------------------------------
# 6. History of the Day ("on this day" API)
# ---------------------------------------------------------------------
def history_of_the_day():
    source_name = "On This Day API (byabbe.se)"
    source_url = "https://byabbe.se/on-this-day/"
    month, day = TODAY.month, TODAY.day
    try:
        data = get_json(f"https://byabbe.se/on-this-day/{month}/{day}/events.json")
        events = data.get("events", [])
        if not events:
            raise ValueError("API returned no events for today's date")
        import random
        pick = random.Random(TODAY.isoformat()).choice(events)
        text = f"**{pick['year']}** — {pick['description']}"
        return text, source_name, source_url
    except Exception as exc:
        text = f"_History lookup failed today._\n\n**Error:** `{exc}`"
        return text, source_name, source_url


# ---------------------------------------------------------------------
# Assemble and write
# ---------------------------------------------------------------------
SECTIONS = [
    ("📖 Word of the Day", "A vocabulary word, expression, or piece of language worth learning.", word_of_the_day),
    ("💡 Fact of the Day", "Something true, interesting, or surprising.", fact_of_the_day),
    ("💬 Quote of the Day", "A quote — inspirational, funny, or philosophical.", quote_of_the_day),
    ("🌌 Image of the Day", "Wikipedia's Picture of the Day.", image_of_the_day),
    ("🧠 Trivia of the Day", "A quick knowledge challenge.", trivia_of_the_day),
    ("🕰️ History of the Day", "An event, person, or moment from history on this date.", history_of_the_day),
]


def main():
    lines = [
        f"# Daily Digest — {TODAY.isoformat()}",
        "",
        "_A daily digest, refreshed automatically once a day._",
        "",
    ]

    for title, description, func in SECTIONS:
        lines.append(f"## {title}")
        lines.append(f"_{description}_")
        lines.append("")
        try:
            content, source_name, source_url = func()
        except Exception as exc:  # last-resort safety net per section
            content, source_name, source_url = f"_Unavailable today: {exc}_", "N/A", None

        lines.append(content)
        lines.append("")
        if source_url:
            lines.append(f"**Source:** [{source_name}]({source_url})")
        else:
            lines.append(f"**Source:** {source_name}")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append(f"_Last updated: {datetime.now(timezone.utc).isoformat()} UTC_")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Wrote digest to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
    main()
