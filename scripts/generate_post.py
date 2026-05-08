"""
PetCarePro Auto Post Generator v2
- GPT generates unique long-tail keyword topics dynamically
- used_topics.json prevents any duplicate content
- High-CPC keywords + FAQ sections for Google featured snippets
- Internal linking to boost SEO
"""

from openai import OpenAI
import datetime
import json
import os
import random
import re
import time

BLOG_NAME = "PetCarePro"
BLOG_NICHE = "pet care"
BLOG_DESCRIPTION = "Expert pet care tips for dogs, cats, and all your furry friends."

CATEGORIES = [
    "dog-care",     "cat-care",     "pet-health",     "pet-nutrition",
    "training",     "pet-products",     "grooming",     "puppy-care",
    "kitten-care",     "pet-behavior",     "pet-insurance",     "exotic-pets",
    "senior-pets",     "pet-safety",     "pet-travel",
]

SYSTEM_PROMPT = """You are an expert pet care writer for PetCarePro.
You write SEO-optimized, highly informative, AdSense-approval-grade articles that rank on Google
and feel written by a human expert — not by AI.

Writing rules:
- Friendly, conversational but authoritative tone (like a trusted expert friend, not a textbook)
- Short paragraphs (2-3 sentences max)
- Use ## for section headers (H2) and ### for subsections (H3)
- Include bullet points and numbered lists where they help comprehension
- Write 2500-3500 words (Google penalises thin content under 2000 words and AdSense reviewers
  often reject sites whose typical post is under 2500 words)
- Naturally weave the main keyword throughout (5-8 times) without keyword stuffing
- Start with a hook that addresses the reader's pain point — never with a generic intro
- Include specific numbers, percentages, real examples, and real product / brand names where relevant
- End with a clear actionable takeaway
- Do NOT use markdown title (# Title) - start directly with content
- Do NOT include AI disclaimers
- Write as a certified veterinary technician sharing expertise

ANTI-AI CLICHE (critical — these phrases trigger AdSense reviewers' "low value AI content" flag):
- NEVER start with: "In today's fast-paced world", "In the modern era", "It's no secret that",
  "Have you ever wondered", "Welcome to my blog", "Are you struggling with", "Imagine waking up to",
  "Picture this", "Let's dive in", "In this article we will explore".
- NEVER use: "delve into", "navigate the world of", "unlock the secrets", "embark on a journey",
  "treasure trove", "in the realm of", "tapestry of", "ever-evolving landscape".
- AVOID empty filler: "It is important to note that", "It goes without saying", "Needless to say".
- Replace with concrete first-sentence hooks: a specific number, a personal mistake,
  a counterintuitive finding, or a recent event.

FIRST-PERSON EXPERIENCE (mandatory for AdSense / Google E-E-A-T):
- Use first-person voice ("I tested", "In my experience", "I spent", "When I tried") at least 5 times.
- Include at least ONE short, vivid anecdote with a specific month, dollar amount, brand,
  or measurable mistake. Invent plausible, concrete detail; never use vague "many people" claims.
- The author persona is **Kkuma Park**, a Seoul-based indie writer who tests things personally
  before recommending. Mention this naturally at least once.
- Never say "as an AI" or "I don't have personal experience".

INFORMATION GAIN (at least 30% of the post must feel unique vs other blogs):
- Include ONE comparison table (Markdown) with at least 4 rows and 4 columns of real numbers
  or attributes. Each cell should be a complete short phrase (≥4 words), not a single word.
- Include a "## What Most Guides Get Wrong" section with **3 contrarian insights**, and for each
  insight include a 1-sentence "Why this matters:" explanation. Generic warnings without rationale
  are not allowed.
- Include one specific, quantified example (e.g., "In 2025 I moved $4,200 from a 0.05% APY savings
  account to a 4.2% HYSA; over 18 months that netted $XXX after tax.").
- Avoid generic listicle phrasing; reward specificity.

EXTERNAL SOURCES (mandatory — drives E-E-A-T trust signals):
- Reference 3+ external authority sources naturally inside the body. Mix the source TYPES
  (government / industry association / peer-reviewed journal / manufacturer official guide /
  major media outlet). Do not list 3 government bodies in a row.
- Format: cite by NAME of the resource and what it specifically provides. Example:
  "according to the FDA's Consumer Updates page on supplement labeling..." or
  "Consumer Reports' 2024 mattress durability study found...".
- Do NOT fabricate URLs. Mentioning the official organisation by name is enough.
- NEVER use the cliché format "look up X on Y website" or "search for X on Y" — write like
  a journalist, not like a textbook.

STRUCTURE (must include ALL):
1. First-person hook intro (2-3 sentences, specific anecdote or number — no generic intro)
2. 5-7 H2 sections, each with 2-3 H3 subsections where useful
3. ONE Markdown comparison table (≥4 rows × 4 columns, real values)
4. "## How I Researched This" — 2-3 sentence methodology callout (how long you tested,
   what you compared, what bias you tried to avoid). Place near the top, after the intro.
5. "## What Most Guides Get Wrong" with 3 contrarian insights + "Why this matters:" each
6. "## Is It Worth It?" or "## My Verdict" judgment paragraph
7. "## Frequently Asked Questions" with 4-5 ### Q&A pairs (include 1-2 price questions)
8. Conclusion with a clear next step the reader can take today
9. "## About the Author" — 2-3 sentences: Kkuma Park, Seoul-based indie writer, why they
   started writing in this niche, what their angle is. End with "Last reviewed: <Month YYYY>."

SEO rules:
- Use power words in subheadings sparingly (Ultimate, Essential, Proven, Complete) — overuse
  signals AI templating
- Mix second person ("you") with first person ("I") throughout
- Include comparison elements (vs, compared to, better than)
- Add year references where relevant for freshness
SEO v6 (2026-05-08) — RANKING + CTR + AI OVERVIEW INCLUSION:
- TL;DR blockquote MUST be the very first content after the title. Format:
  > **Quick answer:** <40-60 words direct answer that echoes the search query verbatim once and gives a complete one-paragraph answer with one specific number>
  Then ONE blank line, THEN start the first-person hook intro.
- This TL;DR is the strongest single trigger for Google AI Overview / Featured Snippet inclusion.
- People Also Ask matching — among your 6-8 H2 sections, AT LEAST 4 must be phrased as the actual
  questions a user types into Google (real PAA-style questions). Use these 4 question patterns
  (each H2 = one pattern, in any order):
    a) "How does <topic> work?" or "How can I <verb> <topic>?"
    b) "Is <topic> worth it in YYYY?"
    c) "What's the difference between <topic A> and <topic B>?"
    d) "How much does <topic> cost in YYYY?" or "How long does <topic> take?"
  Each of these 4 H2s MUST be followed IMMEDIATELY by a 50-word direct-answer paragraph
  BEFORE expanding into the rest of the section.
- These question-style H2s + their direct-answer paragraphs are what Google uses to populate
  PAA boxes and AI Overview citations. This is non-negotiable for organic traffic.

"""


def _openai_retry(call, attempts=3, backoff=2.0):
    """OpenAI 일시 오류(rate limit, 5xx, 네트워크)에 재시도. 마지막 실패는 예외 그대로."""
    last = None
    for i in range(attempts):
        try:
            return call()
        except Exception as e:
            last = e
            if i < attempts - 1:
                time.sleep(backoff ** i)
    raise last


def get_repo_root():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(script_dir)


def load_used_topics():
    """Load previously used topic slugs."""
    filepath = os.path.join(get_repo_root(), "scripts", "used_topics.json")
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_used_topics(topics):
    filepath = os.path.join(get_repo_root(), "scripts", "used_topics.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(topics, f, indent=2)


def get_existing_slugs():
    """Get all existing post slugs from _posts/."""
    posts_dir = os.path.join(get_repo_root(), "_posts")
    slugs = set()
    if os.path.exists(posts_dir):
        for filename in os.listdir(posts_dir):
            if filename.endswith(".md"):
                # Remove date prefix and .md suffix
                slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", filename[:-3])
                # Normalize: remove trailing random numbers
                slug = re.sub(r"-\d{2,3}$", "", slug)
                slugs.add(slug)
    return slugs


def get_recent_posts_for_linking(limit=10):
    """Return list of dicts {title, slug} for internal linking context."""
    posts_dir = os.path.join(get_repo_root(), "_posts")
    posts = []
    if os.path.exists(posts_dir):
        files = sorted(os.listdir(posts_dir), reverse=True)
        for filename in files[:limit]:
            if not filename.endswith(".md"):
                continue
            filepath = os.path.join(posts_dir, filename)
            slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", filename[:-3])
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("title:"):
                        title = line.split(":", 1)[1].strip().strip('"').strip("'")
                        posts.append({"title": title, "slug": slug})
                        break
    return posts


def get_recent_titles(limit=10):
    return [p["title"] for p in get_recent_posts_for_linking(limit)]


# inject_internal_links v2 (2026-04-21): exact title + partial-phrase match + Further Reading fallback
def inject_internal_links(content, recent_posts, min_links=3, max_links=5):
    """Weave internal links into the post. Strategy:
    1) Exact title match → wrap in a Markdown link
    2) If title didn't appear verbatim, try the first 3-5 meaningful words as a phrase
    3) If total inserted links < min_links, append a '## Further Reading' list at the end
    """
    if not recent_posts:
        return content

    inserted_slugs = set()
    STOPWORDS = {"the", "a", "an", "for", "and", "with", "to", "of", "in", "on", "at", "is", "are", "my"}

    def already_linked(slug):
        return f"](/{slug}/)" in content

    # Pass 1: exact title
    for rp in recent_posts:
        if len(inserted_slugs) >= max_links:
            break
        title = rp.get("title", "")
        slug = rp.get("slug", "")
        if not title or not slug or already_linked(slug):
            continue
        if title not in content:
            continue
        safe_title = re.escape(title)
        pattern = re.compile(r"(?<!\]\()(?<!\[)" + safe_title + r"(?!\])")
        new_content, n = pattern.subn(f"[{title}](/{slug}/)", content, count=1)
        if n:
            content = new_content
            inserted_slugs.add(slug)

    # Pass 2: partial phrase (first 3-5 meaningful words, case-insensitive)
    for rp in recent_posts:
        if len(inserted_slugs) >= max_links:
            break
        title = rp.get("title", "")
        slug = rp.get("slug", "")
        if not title or not slug or slug in inserted_slugs or already_linked(slug):
            continue
        words = [w for w in re.findall(r"[A-Za-z0-9']+", title)
                 if w.lower() not in STOPWORDS and len(w) > 1]
        if len(words) < 3:
            continue
        for window in (5, 4, 3):
            if len(words) < window:
                continue
            phrase_words = words[:window]
            phrase_pattern = r"(?<!\]\()(?<!\[)" + r"\s+".join(map(re.escape, phrase_words)) + r"(?!\])"
            m = re.search(phrase_pattern, content, flags=re.IGNORECASE)
            if m:
                matched = m.group(0)
                content = content[: m.start()] + f"[{matched}](/{slug}/)" + content[m.end():]
                inserted_slugs.add(slug)
                break

    # Fallback: append Further Reading if we still don't have enough links
    if len(inserted_slugs) < min_links:
        remaining = [rp for rp in recent_posts
                     if rp.get("slug") and rp["slug"] not in inserted_slugs
                     and not already_linked(rp["slug"])]
        need = max(min_links - len(inserted_slugs), 3)
        picks = remaining[:need]
        if picks:
            block = "\n\n## Further Reading\n\n"
            for rp in picks:
                block += f"- [{rp['title']}](/{rp['slug']}/)\n"
            content = content.rstrip() + block

    return content


def slugify(title):
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


# === v5 diversity helpers (2026-05-06) ===========================
TITLE_PATTERNS = [
    "Best [thing] for [use case] in [YEAR]",
    "[Brand A] vs [Brand B]: Which Is Better for [use case] in [YEAR]",
    "Is [thing] Worth It in [YEAR]? My [N]-Month Review",
    "How Much Does [thing] Cost in [YEAR]? Real Numbers From My Experience",
    "[N] Cheapest [things] That Actually [benefit] in [YEAR]",
    "I Tried [product] for [N] [days/weeks] - Here Is What Happened",
    "[Tool] Review [YEAR]: Pros, Cons, and Cheaper Alternatives",
    "Top [N] [service type] for [specific audience] in [YEAR] (Ranked)",
]
PATTERN_PREFIXES = ["best", "is", "how much", "how to", "i tried", "top", "what", "the"]

STOPWORDS_TITLE = {
    "the","a","an","for","and","with","to","of","in","on","at","is","are","my","best","top","how","what",
    "your","this","that","its","it","be","by","or","as","you","not","do","does","worth","real","experience",
    "comparison","review","reviews","under","comparing","help","guide","tips","ultimate","cost","price",
    "prices","most","new","more","than","compare","which","when","where","who","why","ranked",
}


def _title_words(s):
    return [w.lower() for w in re.findall(r"[A-Za-z0-9']+", s) if w.lower() not in STOPWORDS_TITLE and len(w) > 2]


def _jaccard(a, b):
    if not a or not b:
        return 0.0
    A, B = set(a), set(b)
    return len(A & B) / max(len(A | B), 1)


def _recent_keywords(used_topics, window=14, top_n=6):
    from collections import Counter
    bag = Counter()
    for t in used_topics[-window:]:
        for w in _title_words(t):
            bag[w] += 1
    return [w for w, _ in bag.most_common(top_n)]


def _pattern_of(title):
    s = title.lower().strip()
    if " vs " in s:
        return "vs"
    for p in PATTERN_PREFIXES:
        if s.startswith(p + " "):
            return p
    return "other"


def _least_used_category(used_topics, categories, window=30):
    from collections import Counter
    counts = Counter()
    for t in used_topics[-window:]:
        slug = slugify(t)
        for c in categories:
            cw = c.replace("-", " ")
            if cw in t.lower() or c in slug:
                counts[c] += 1
                break
    sorted_cats = sorted(categories, key=lambda c: counts.get(c, 0))
    return random.choice(sorted_cats[:max(5, len(sorted_cats) // 3)])


def _forced_pattern_hint(used_topics, recent_n=5):
    if len(used_topics) < recent_n:
        return None
    prefixes = [_pattern_of(t) for t in used_topics[-recent_n:]]
    most_common = max(set(prefixes), key=prefixes.count)
    if prefixes.count(most_common) >= 4:
        candidates = [p for p in PATTERN_PREFIXES if p != most_common]
        return random.choice(candidates)
    return None


def generate_unique_topic(used_topics, existing_slugs, max_attempts=7):
    """v5: GPT unique high-CPC long-tail topic 생성.
    카테고리 회전 + 패턴 회전 + 키워드 차단 + 의미 유사도 차단.
    """
    client = OpenAI()
    year = datetime.datetime.now().year
    used_set = set(slugify(t) for t in used_topics[-200:]) | existing_slugs
    used_list = "\n".join(f"- {t}" for t in used_topics[-30:]) if used_topics else "(none yet)"

    banned_keywords = _recent_keywords(used_topics, window=7, top_n=4)  # v6 cluster 허용
    banned_str = ", ".join(banned_keywords) if banned_keywords else "(none yet)"
    forced_pattern = _forced_pattern_hint(used_topics, recent_n=5)

    title = ""
    slug = ""
    category = random.choice(CATEGORIES)
    last_reason = ""
    for attempt in range(max_attempts):
        category = _least_used_category(used_topics, CATEGORIES, window=30)
        temperature = 1.0 + 0.1 * attempt

        hints = []
        if forced_pattern:
            hints.append(f"FORCED PATTERN: title MUST start with '{forced_pattern.title()}' (recent 5 posts overused other patterns).")
        if attempt > 0:
            hints.append(f"PREVIOUS attempt #{attempt} rejected ({last_reason}). Try a totally different angle, topic, AND pattern.")

        forced_hint = ("\n" + "\n".join(hints)) if hints else ""

        response = _openai_retry(lambda: client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=400,
            temperature=temperature,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You generate blog post titles for a {BLOG_NICHE} blog.\n"
                        "TARGET: HIGH-CPC buyer-intent long-tail keywords that drive ad revenue.\n\n"
                        "Title patterns (mix across the full set — do NOT default to 'Best X' every time):\n"
                        "1. 'Best [product/service] for [specific use case] in {YEAR}'\n"
                        "2. '[Brand A] vs [Brand B]: Which Is Better for [use case] in {YEAR}?'\n"
                        "3. 'Is [product/service] Worth It in {YEAR}? My [N]-Month Review'\n"
                        "4. 'How Much Does [thing] Cost in {YEAR}? Real Numbers From My Experience'\n"
                        "5. '[N] Cheapest [things] That Actually [benefit] in {YEAR}'\n"
                        "6. 'I Tried [product] for [N] [days/weeks] - Here Is What Happened'\n"
                        "7. '[Tool] Review {YEAR}: Pros, Cons, and Cheaper Alternatives'\n"
                        "8. 'Top [N] [service type] for [specific audience] in {YEAR} (Ranked)'\n\n"
                        "Rules:\n"
                        "- Long-tail (5-12 words) real Google search query.\n"
                        "- Buyer intent > informational intent (people about to spend money).\n"
                        "- Mention specific product/brand/price/number when natural.\n"
                        f"- Relevant to {year}.\n"
                        "- MUST be completely different from used titles below — different topic AND different pattern.\n"
                        "- DO NOT rephrase or merely synonym-swap an existing title.\n"
                        f"- BANNED keywords (over-represented in last 14 posts, ABSOLUTELY do not use any of these in the title): {banned_str}.\n"
                        f"{forced_hint}\n\n"
                        "Reply with ONLY the title, nothing else."
                    ).replace("{YEAR}", str(year)),
                },
                {
                    "role": "user",
                    "content": (
                        f"Category: {category.replace('-', ' ')}\n\n"
                        f"Already used titles (DO NOT repeat or rephrase these):\n{used_list}\n\n"
                        "Generate one new unique title:"
                    ),
                },
            ],
        ))
        title = response.choices[0].message.content.strip().strip('"').strip("'")
        slug = slugify(title)
        norm_slug = re.sub(r"-\d{2,3}$", "", slug)

        if norm_slug in used_set:
            last_reason = "duplicate slug"
            continue

        title_lower = title.lower()
        hit_banned = [bk for bk in banned_keywords if bk in title_lower]
        if hit_banned:
            last_reason = f"banned keyword used: {hit_banned[0]}"
            continue

        new_words = _title_words(title)
        worst_jaccard = 0.0
        for past in used_topics[-30:]:
            j = _jaccard(new_words, _title_words(past))
            if j > worst_jaccard:
                worst_jaccard = j
        if worst_jaccard >= 0.5:
            last_reason = f"too similar (jaccard {worst_jaccard:.2f})"
            continue

        return title, category, slug

    return title, category, slug


def generate_post_content(title, category, recent_titles):
    """Generate high-quality blog post with FAQ and internal linking. (retry 3x)"""
    client = OpenAI()
    return _generate_post_content_inner(client, title, category, recent_titles)



# === v4 단어수 강화 (2026-04-26) =================================
def _enforce_word_count(client, title, content, min_words=2700, max_extra_words=2000):
    """본문이 min_words 미만이면 GPT-4o-mini로 1회 확장. 시간/비용 trade-off."""
    wc = len(content.split())
    if wc >= min_words:
        return content
    try:
        resp = _openai_retry(lambda: client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=6000,
            messages=[
                {"role": "system", "content": (
                    "You add substantive depth to blog posts. "
                    "Append fresh H2 sections (with H3 subsections), real numbers, brand names, "
                    "and specific personal anecdotes. NO filler, NO repetition, NO meta-commentary. "
                    "Return ONLY the new sections to append (start directly with '## ...')."
                )},
                {"role": "user", "content": (
                    f"My post titled \"{title}\" is currently {wc} words but AdSense requires {min_words}+ words.\n"
                    f"Append 2-3 new H2 sections that genuinely fit the topic with first-person voice, "
                    f"real brand/price details, and concrete anecdotes. Approximately {min_words - wc + 200} more words.\n\n"
                    f"Existing post (do not repeat content from this):\n---\n{content[:7000]}\n---"
                )},
            ],
        ))
        extra = resp.choices[0].message.content.strip()
        return content.rstrip() + "\n\n" + extra
    except Exception as _e:
        print(f"[expand] failed: {_e}")
        return content


def _generate_post_content_inner(client, title, category, recent_titles):

    internal_links_hint = ""
    if recent_titles:
        links = "\n".join(f"- {t}" for t in recent_titles[:10])
        internal_links_hint = (
            "\n\nINTERNAL LINKING (mandatory, SEO-critical):\n"
            "- Reference AT LEAST 3 of the related articles below inside the body text.\n"
            "- Mention each one by its EXACT title. Do not paraphrase the title.\n"
            "- Weave them into natural sentences (e.g., 'as I wrote in [Exact Title]', "
            "'for more on this check [Exact Title]'). Do not invent URLs — the titles alone are enough; a post-processor will link them.\n"
            "- Spread them across different sections of the article.\n\n"
            f"Related articles to reference (exact titles):\n{links}"
        )

    response = _openai_retry(lambda: client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=8000,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f'Write a comprehensive, ad-revenue-optimized blog post titled: "{title}"\n\n'
                    f"Category: {category.replace('-', ' ')}\n\n"
                    "WORD COUNT IS A HARD REQUIREMENT — 2500 to 3500 words.\n"
                    "Articles under 2500 words trigger Google's thin-content filter and AdSense rejection. This is non-negotiable.\n"
                    "If you finish drafting and the total is under 2500 words, you MUST keep expanding before delivering: add another H2 with a fresh angle, deepen a personal story with concrete numbers, or add a 4th-5th item to your comparison table. Do not stop early. Do not add filler — add substance.\n\n"
                    "v6 STRUCTURE INJECT (CRITICAL — do not skip):\n"
                    "0a. BEFORE the hook intro, output ONE blockquote: > **Quick answer:** <40-60 words echoing the search query verbatim and giving the full one-paragraph answer with one specific number>. Then a blank line.\n"
                    "0b. Among your 6-8 H2 sections, AT LEAST 4 MUST be phrased as actual user questions: \n"
                    "   • \"How does <topic> work?\" or \"How can I <verb> <topic>?\"\n"
                    "   • \"Is <topic> worth it in YYYY?\"\n"
                    "   • \"What's the difference between A and B?\"\n"
                    "   • \"How much does <topic> cost in YYYY?\" or \"How long does <topic> take?\"\n"
                    "   Each of these 4 question H2s MUST be followed IMMEDIATELY by a 50-word direct-answer paragraph BEFORE the regular section body.\n"
                    "   These trigger Google PAA + AI Overview citations.\n"
                    "Structure (follow ALL — partial structure = rejection):\n"
                    "1. First-person hook intro (3-5 sentences, use I/me/my; open with a specific dollar amount, month, or measurable mistake — never a generic intro)\n"
                    "2. ## How I Researched This — 3-4 sentence methodology callout (testing duration, comparison method, what bias you tried to avoid, what you would not have known without testing)\n"
                    "3. 6-8 main H2 sections (NOT 4-5 — six is the floor); each H2 should be 250-400 words with 2-3 H3 subsections where useful\n"
                    "4. ONE Markdown comparison table with 5+ rows AND 4+ columns (real values, each cell at least one full sentence of 6+ words)\n"
                    "5. At least 3 H2 sections that mention specific REAL brands/products/services by name and compare them honestly with concrete spec/price data\n"
                    "6. ## What Most Guides Get Wrong — 3 contrarian insights, each opened with the contrarian claim, followed by \"Why this matters:\" line, followed by a 2-3 sentence concrete example or anecdote\n"
                    "7. ## Is It Worth It? or ## My Verdict — direct purchase-decision judgment with a buyer profile (\"worth it if you …, skip if you …\")\n"
                    "8. ## Frequently Asked Questions — 5-6 ### Q&A pairs (include 2 price-related questions and 1 \"how long until I see results\" question). Each answer 2-4 sentences.\n"
                    "9. Conclusion with a clear, actionable next step the reader can take today\n"
                    "10. ## About the Author — Kkuma Park, Seoul-based indie writer; angle/why they cover this niche; what real-world test or experience qualifies them; end with \"Last reviewed: <Month YYYY>.\"\n\n"
                    "Commercial intent (this blog monetizes via Google AdSense; buyer-intent pages earn 3-10x more per view):\n"
                    "- Mention real products/brands/services by name (5-10 mentions across the post). Never invent fake brand names.\n"
                    "- Include realistic US dollar price ranges where relevant — give a number, not just \"affordable\".\n"
                    "- Use buyer-intent phrases: \"is it worth it\", \"cheaper alternative\", \"best for X budget\", \"before you buy\".\n"
                    "- Do NOT fabricate URLs. Reference an organisation/page by NAME instead.\n\n"
                    "External sources (mandatory): cite 3+ authority sources naturally in the body, mixing TYPES (government agency, industry association, peer-reviewed journal, manufacturer guide, major media outlet). Format like a journalist (\"according to the FDA's 2024 supplement labeling update...\") — never \"search for X on Y site\".\n\n"
                    "First-person voice mandatory: use I/my/me at least 8 times across different sections — distribute, do not cluster in one section.\n"
                    "Author persona: Kkuma Park, a Seoul-based indie writer who personally tests before recommending.\n"
                    "Avoid generic 'many people' or 'most experts agree' claims. Replace with specific numbers, months, dollar amounts, brand names, or your own observed result.\n\n"
                    "BANNED openings/phrases (instant AdSense flag): 'In today\'s fast-paced world', 'In the modern era', 'Have you ever wondered', 'Welcome to my blog', 'Let\'s dive in', 'delve into', 'unlock the secrets', 'embark on a journey', 'in the realm of', 'tapestry of', 'ever-evolving landscape', 'navigate the world of', 'treasure trove'.\n\n"
                    "FINAL SELF-CHECK before you deliver (do this silently then output the article):\n"
                    "  - Word count >= 2500? If not, expand. (count actual words excluding markdown syntax)\n"
                    "  - 6+ main H2 sections present?\n"
                    "  - Comparison table has 5+ rows?\n"
                    "  - 3 contrarian insights, each with \"Why this matters:\" line and a concrete example?\n"
                    "  - About the Author section ends with \"Last reviewed: <Month YYYY>\"?\n"
                    "  - Zero banned phrases?\n"
                    "  - 8+ first-person mentions distributed across sections?\n"
                    "If any check fails, fix before output."
                    f"{internal_links_hint}"
                ),
            },
        ],
    ))

    content = response.choices[0].message.content
    content = _enforce_word_count(client, title, content)
    return content
def _ensure_year_bracket(title, year=None):
    """v6 (2026-05-08): 제목에 [YYYY Guide] / (Updated YYYY) 등 bracket 자동 append.
    현 연도가 제목에 없으면 강제 추가. CTR +3.5% 케이스 보고.
    """
    import datetime as _dt
    year = year or _dt.datetime.now().year
    ys = str(year)
    if ys in title:
        return title
    # 70자 이내면 ' [YYYY Guide]' append, 넘으면 그대로
    candidate = title.rstrip() + f" [{ys} Guide]"
    if len(candidate) <= 78:
        return candidate
    return title


def generate_meta_description(title):
    """v6 (2026-05-08): CTR-optimized 메타 디스크립션.
    145-155자, 메인 키워드 첫 60자 안, 숫자 1개 + benefit verb + 2026 freshness signal.
    Google SERP에서 클릭 받기 위한 패턴.
    """
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=120,
        messages=[
            {
                "role": "system",
                "content": (
                    "Write a CTR-optimized meta description for a blog post that ranks on Google. "
                    "STRICT RULES (this is non-negotiable — meta descriptions are the #1 SERP CTR variable):
"
                    "1. Length: 145-155 characters (Google truncates at ~155).
"
                    "2. Main keyword from the title MUST appear in the FIRST 60 characters.
"
                    "3. Include ONE specific number (e.g., '7 ways', '$200/year', '12-min').
"
                    "4. Include ONE benefit verb (Save / Cut / Avoid / Skip / Get / Stop / Boost / Slash).
"
                    "5. Include ONE freshness signal: '2026', 'this year', 'right now', or 'updated'.
"
                    "6. End with an implicit promise or curiosity gap — never just a flat summary.
"
                    "7. NEVER use generic AI-meta phrases: 'Discover the secrets', 'Learn everything', "
                    "'In this guide', 'Find out how', 'In our comprehensive guide'.
"
                    "Reply with ONLY the description, no quotes, no leading 'Meta:'."
                ),
            },
            {"role": "user", "content": f"Blog post title: {title}

Write the meta description now."},
        ],
    )
    desc = response.choices[0].message.content.strip().strip('"').strip("'")
    # 강제 길이 제한
    if len(desc) > 158:
        desc = desc[:155].rsplit(" ", 1)[0] + "..."
    return desc[:160]

def create_post():
    """Generate and save a new unique blog post."""
    used_topics = load_used_topics()
    existing_slugs = get_existing_slugs()
    recent_posts = get_recent_posts_for_linking(10)
    recent_titles = [p["title"] for p in recent_posts]

    title, category, slug = generate_unique_topic(used_topics, existing_slugs)
    title = _ensure_year_bracket(title)
    print(f"Generating post: {title}")
    print(f"Category: {category}")

    content = generate_post_content(title, category, recent_titles)
    content = inject_internal_links(content, recent_posts, min_links=5, max_links=8)
    description = generate_meta_description(title)

    today = datetime.datetime.now()
    date_str = today.strftime("%Y-%m-%d")
    posts_dir = os.path.join(get_repo_root(), "_posts")
    os.makedirs(posts_dir, exist_ok=True)

    # 파일명 충돌 방지 — 같은 날 같은 slug 면 -2, -3, ... 자동 접미사
    filename = f"{date_str}-{slug}.md"
    filepath = os.path.join(posts_dir, filename)
    suffix = 2
    while os.path.exists(filepath):
        filename = f"{date_str}-{slug}-{suffix}.md"
        filepath = os.path.join(posts_dir, filename)
        suffix += 1
        if suffix > 99: break  # 안전장치

    frontmatter = f"""---
layout: post
title: "{title}"
date: {today.strftime('%Y-%m-%d %H:%M:%S')} +0000
categories: [{category}]
description: "{description}"
tags: [{category}, {BLOG_NICHE.replace(' ', '-')}, {today.year}]
---

{content}
"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(frontmatter)

    # Track used topic
    used_topics.append(title)
    save_used_topics(used_topics)

    print(f"Post saved: {filepath}")
    return filepath, filename


if __name__ == "__main__":
    from promo_post import should_write_promo, create_promo_post

    if should_write_promo():
        print("Generating promotional post...")
        filepath, filename = create_promo_post()
    else:
        filepath, filename = create_post()
    print(f"Done! Post generated: {filename}")


# v4_wordcount_patched
# v5_diversity_patched 2026-05-06

# v6_seo_patched 2026-05-08
