"""
Daily Digest generator.

Builds a 10-section daily digest (Word, Fact, Quote, Question, Image,
Trivia, Tip, Discovery, History, Idea "of the Day") and writes it to
README.md so it can be published with GitHub Pages.

v3 changes:
- Image of the Day now uses Wikipedia's "Picture of the Day" via the
  Wikimedia REST API (https://en.wikipedia.org/api/rest_v1/feed/featured/...).
  No API key, no sign-up, no rate-limit headaches — it's a public,
  CDN-backed endpoint intended for exactly this kind of daily use.
  NASA's APOD is no longer used, so the NASA_API_KEY secret is no
  longer needed (safe to remove from your repo if you'd set it up).

Every section still shows a description and a "Source" link, and
failures show the real error message instead of a generic one.

Four sections (Question, Tip, Discovery, Idea) don't have good free
APIs, so they rotate through a curated list deterministically based
on today's date — stable across multiple runs on the same day, but
changes daily.
"""

import html
import json
import random
import urllib.error
import urllib.request
from datetime import date, datetime, timezone

OUTPUT_FILE = "README.md"
TIMEOUT = 15
UA = {"User-Agent": "DailyDigestBot/1.0 (GitHub Actions daily job; no contact configured)"}

TODAY = date.today()
DAY_SEED = random.Random(TODAY.isoformat())


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
        fallback = [
            ("serendipity", "noun", "the occurrence of finding pleasant things by chance"),
            ("ephemeral", "adjective", "lasting for a very short time"),
            ("mellifluous", "adjective", "sweet or musical; pleasant to hear"),
        ]
        w, p, d = DAY_SEED.choice(fallback)
        text = f"**{w}** *({p})* — {d}\n\n_(Live lookup failed: {exc} — showing a fallback word.)_"
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
        text = (
            "Honey never spoils — archaeologists have found 3,000-year-old edible "
            f"honey in Egyptian tombs.\n\n_(Live lookup failed: {exc} — showing a fallback fact.)_"
        )
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
        text = (
            "\"The only way to do great work is to love what you do.\" — Steve Jobs"
            f"\n\n_(Live lookup failed: {exc} — showing a fallback quote.)_"
        )
        return text, source_name, source_url


# ---------------------------------------------------------------------
# 4. Question of the Day (curated, rotates daily)
# ---------------------------------------------------------------------
QUESTIONS = [
    "What's a skill you'd love to master if time and money weren't an issue?",
    "What's the best piece of advice you've ever ignored?",
    "If you could instantly become an expert in one subject, what would it be?",
    "What's something you believed as a kid that you laugh about now?",
    "Who is someone that changed the way you see the world?",
    "What's a small thing that made you unreasonably happy recently?",
    "If you had an extra hour every day, what would you do with it?",
    "What's a place you've never been but feel drawn to?",
    "What does 'success' mean to you today, versus five years ago?",
    "What's a habit you're proud of building?",
    "What's a question you wish people asked you more often?",
    "What's something you learned the hard way?",
    "If you could send one sentence back to your younger self, what would it say?",
    "What's a book, film, or song that quietly changed you?",
    "What's something you're curious about but haven't looked into yet?",
    "What does an ideal ordinary day look like for you?",
    "What's a risk that turned out to be worth it?",
    "What's a tradition you want to start or keep alive?",
    "Who do you need to thank that you haven't yet?",
    "What's something you do differently than most people, and why?",
    "What would you attempt if you knew you couldn't fail?",
    "What's a compliment you received that you still remember?",
    "What's something you've changed your mind about recently?",
    "If your life had a theme song right now, what would it be?",
    "What's a small act of kindness you witnessed or received?",
    "What's a comfort zone you're ready to step out of?",
    "What does 'home' mean to you?",
    "What's something you want to be remembered for?",
    "What's a question you find yourself asking a lot lately?",
    "What's the most useful thing you've learned from a mistake?",
]


def question_of_the_day():
    idx = TODAY.timetuple().tm_yday % len(QUESTIONS)
    return QUESTIONS[idx], "Curated list (rotates daily by date)", None


# ---------------------------------------------------------------------
# 5. Image of the Day — Wikipedia Picture of the Day (no API key needed)
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
# 6. Trivia of the Day
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
        text = (
            "**[Geography · Easy]** What is the smallest country in the world?\n"
            f"> Answer: ||Vatican City||\n\n_(Live lookup failed: {exc} — showing a fallback question.)_"
        )
        return text, source_name, source_url


# ---------------------------------------------------------------------
# 7. Tip of the Day (curated, rotates daily)
# ---------------------------------------------------------------------
TIPS = [
    "Write tomorrow's top 3 priorities before you finish work today — you'll start faster and calmer.",
    "When learning something new, teach it to someone (even an imaginary someone) — it exposes gaps fast.",
    "Keep a 'done' list, not just a to-do list. It's a fast antidote to feeling unproductive.",
    "Batch small errands and messages instead of reacting to each one as it appears.",
    "Before agreeing to something, ask 'what would I have to say no to, to say yes to this?'",
    "Drink a glass of water before your morning coffee — most 'tiredness' is mild dehydration.",
    "Use the 2-minute rule: if a task takes under 2 minutes, do it now instead of queueing it.",
    "When stuck on a problem, explain it out loud (or in writing) as if to a beginner.",
    "Keep your workspace ready to use — friction at the start kills more momentum than difficulty does.",
    "Default to 'send' — most drafts (emails, messages, ideas) are better shipped imperfect than polished never.",
    "Schedule breaks like meetings — they're easier to protect when they're on the calendar.",
    "When overwhelmed, write down everything in your head, then pick just one item to start.",
    "Say the actual next physical action out loud — 'plan trip' becomes 'open maps app.'",
    "Review your calendar the night before, not the morning of.",
    "Keep one running list of ideas so you're not trying to hold onto them all mentally.",
    "Ask 'what does done look like?' before starting any task — it prevents scope creep.",
    "Set a timer for focused work instead of committing to 'work until it's finished.'",
    "Replace 'I don't have time' with 'it's not a priority' and see how that feels — it's often more honest.",
    "Put your phone in another room while doing deep work — proximity alone pulls attention.",
    "When giving feedback, lead with what's working before what needs to change.",
]


def tip_of_the_day():
    idx = TODAY.timetuple().tm_yday % len(TIPS)
    return TIPS[idx], "Curated list (rotates daily by date)", None


# ---------------------------------------------------------------------
# 8. Discovery of the Day (curated, rotates daily)
# ---------------------------------------------------------------------
DISCOVERIES = [
    "Octopuses have three hearts and blue, copper-based blood instead of iron-based red blood.",
    "There's a shape called a 'gömböc' — a 3D object with only one stable and one unstable equilibrium point, meaning it always rights itself.",
    "Bananas are botanically berries, but strawberries are not.",
    "The Great Wall of China is not actually visible from space with the naked eye — a persistent myth.",
    "Some trees communicate and share resources through underground fungal networks nicknamed the 'wood wide web.'",
    "A day on Venus is longer than its year — it rotates so slowly that one day exceeds one orbit around the Sun.",
    "The word 'quarantine' comes from the Italian 'quaranta giorni,' meaning 'forty days.'",
    "Wombat droppings are cube-shaped, which keeps them from rolling away and helps mark territory.",
    "There are more possible chess games than atoms in the observable universe.",
    "The Eiffel Tower grows about 15 cm taller in summer due to thermal expansion of the iron.",
    "Sharks existed before trees — sharks are roughly 400 million years old, trees around 350 million.",
    "Your brain uses about 20% of your body's total energy despite being roughly 2% of your body weight.",
    "A group of flamingos is called a 'flamboyance.'",
    "The inventor of the frisbee, Walter Morrison, was cremated and made into memorial frisbees.",
    "Antarctica is technically the world's largest desert, defined by low precipitation, not heat.",
    "Some species of jellyfish, like Turritopsis dohrnii, can revert to an earlier stage of life, making them biologically 'immortal.'",
    "Scotland's national animal is the unicorn.",
    "The shortest war in recorded history lasted about 38 minutes (Britain vs. Zanzibar, 1896).",
    "Hot water can freeze faster than cold water under certain conditions — a real, still-debated phenomenon called the Mpemba effect.",
    "A single bolt of lightning contains enough energy to toast about 100,000 slices of bread.",
]


def discovery_of_the_day():
    idx = TODAY.timetuple().tm_yday % len(DISCOVERIES)
    return DISCOVERIES[idx], "Curated list (rotates daily by date)", None


# ---------------------------------------------------------------------
# 9. History of the Day ("on this day" API)
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
        pick = DAY_SEED.choice(events)
        text = f"**{pick['year']}** — {pick['description']}"
        return text, source_name, source_url
    except Exception as exc:
        text = (
            "On this day in history, countless events shaped the world."
            f"\n\n_(Live lookup failed: {exc} — check back tomorrow.)_"
        )
        return text, source_name, source_url


# ---------------------------------------------------------------------
# 10. Idea of the Day (curated, rotates daily)
# ---------------------------------------------------------------------
IDEAS = [
    "What if your notes app could ask you questions instead of just storing answers?",
    "A 'reverse bucket list' — things you're glad you didn't do.",
    "Design a city block where every building has to share something (a roof, a wall, a resource) with its neighbor.",
    "A subscription box that sends you ingredients for a skill, not a meal.",
    "What if streetlights dimmed or brightened based on how many people were nearby?",
    "A 'slow news' digest that only reports stories once they're a week old, once the noise has settled.",
    "Imagine furniture that's rated by how well it ages, not just how it looks new.",
    "A tip jar for good ideas in meetings, not just good service.",
    "What if your calendar showed energy levels, not just time blocks?",
    "A library where you can borrow experiences (a lesson, a walk, a skill swap) instead of just books.",
    "Redesign the 'like' button to instead ask 'what did this make you think of?'",
    "A city planning rule: every new building must also improve one public space nearby.",
    "What if apologies had a required 'what I'll do differently' field?",
    "A game where the goal is to make the other player's next move easier, not harder.",
    "Imagine a resume that lists what you're curious about, not just what you've done.",
]


def idea_of_the_day():
    idx = TODAY.timetuple().tm_yday % len(IDEAS)
    return IDEAS[idx], "Curated list (rotates daily by date)", None


# ---------------------------------------------------------------------
# Assemble and write
# ---------------------------------------------------------------------
SECTIONS = [
    ("📖 Word of the Day", "A vocabulary word, expression, or piece of language worth learning.", word_of_the_day),
    ("💡 Fact of the Day", "Something true, interesting, or surprising.", fact_of_the_day),
    ("💬 Quote of the Day", "A quote — inspirational, funny, or philosophical.", quote_of_the_day),
    ("❓ Question of the Day", "A prompt for reflection, conversation, or curiosity.", question_of_the_day),
    ("🌌 Image of the Day", "Wikipedia's Picture of the Day.", image_of_the_day),
    ("🧠 Trivia of the Day", "A quick knowledge challenge.", trivia_of_the_day),
    ("✅ Tip of the Day", "Practical advice or a small life hack.", tip_of_the_day),
    ("🔎 Discovery of the Day", "Something new to learn or explore.", discovery_of_the_day),
    ("🕰️ History of the Day", "An event, person, or moment from history on this date.", history_of_the_day),
    ("✨ Idea of the Day", "A thought, concept, possibility, or creative spark.", idea_of_the_day),
]


def main():
    lines = [
        f"# Daily Digest — {TODAY.isoformat()}",
        "",
        "_A 10-part daily digest, refreshed automatically once a day._",
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
    main()    main()
