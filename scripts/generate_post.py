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
You write SEO-optimized, highly informative articles that rank on Google.

Writing rules:
- Friendly, conversational but authoritative tone (like a trusted financial advisor friend)
- Short paragraphs (2-3 sentences max)
- Use ## for section headers (H2) and ### for subsections (H3)
- Include bullet points and numbered lists
- Write 2000-2800 words (deep content ranks better and holds reader longer for ad views)
- Naturally weave the main keyword throughout (5-8 times)
- Start with a hook that addresses the reader's pain point
- Include specific numbers, percentages, real examples, and real product / brand names where relevant
- End with a clear actionable takeaway
- Do NOT use markdown title (# Title) - start directly with content
- Do NOT include AI disclaimers
- Write as a certified veterinary technician sharing expertise

Commercial intent (critical - this is how the blog earns ad revenue):
- When the topic involves buying, choosing, or comparing products/services, mention REAL brands/products by name (3-8 mentions) and compare them honestly.
- Include a "Prices and where to look" style paragraph with realistic price ranges in USD.
- Include affiliate-friendly phrasing ("If you want to check current prices...") without inventing fake URLs.
- Include at least one "worth it?" judgment that addresses the reader's likely purchase hesitation.
- These buyer-intent signals drive higher CPC ad matching and therefore higher revenue per page.

FIRST-PERSON EXPERIENCE (critical for AdSense / Google E-E-A-T):
- Use first-person voice ("I tested", "In my experience", "I spent", "When I tried") at least 3 times.
- Include at least ONE short anecdote about a real-feeling personal situation (a specific month, specific dollar amount, specific mistake made). Invent plausible, concrete detail; avoid vague "many people" claims.
- Mention "the author" as Kkuma Park once naturally (e.g., "After 3 years of tracking my own spending, I learned ...").
- Never say "as an AI" or "I don't have personal experience".

INFORMATION GAIN (at least 30% of the post must feel unique vs other blogs):
- Include ONE comparison table (Markdown) with at least 3 rows and 3 columns of real numbers or attributes.
- Include a "What most guides get wrong" or "What others don't mention" section with 3 contrarian points.
- Include one specific, quantified example (e.g., "In 2025 I moved $4,200 from a 0.05% APY savings account to a 4.2% HYSA; over 18 months that netted $XXX after tax.").
- Avoid generic listicle phrasing; reward specificity.

STRUCTURE (must include ALL):
1. Intro hook (2-3 sentences, first-person pain point)
2. 4-6 H2 sections, each with 2-3 H3 subsections where useful
3. One Markdown comparison table
4. "What most guides get wrong" section with 3 contrarian insights
5. Frequently Asked Questions (## FAQ with 3-4 ### Q&A pairs)
6. Conclusion with clear next step

SEO rules:
- Use power words in subheadings (Ultimate, Essential, Proven, Complete)
- Mix second person ("you") with first person ("I") throughout
- Include comparison elements (vs, compared to, better than)
- Add year references where relevant for freshness
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


def get_recent_titles(limit=10):
    """Get recent post titles for internal linking context."""
    posts_dir = os.path.join(get_repo_root(), "_posts")
    titles = []
    if os.path.exists(posts_dir):
        files = sorted(os.listdir(posts_dir), reverse=True)
        for filename in files[:limit]:
            if filename.endswith(".md"):
                filepath = os.path.join(posts_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("title:"):
                            title = line.split(":", 1)[1].strip().strip('"')
                            titles.append(title)
                            break
    return titles


def slugify(title):
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def generate_unique_topic(used_topics, existing_slugs, max_attempts=5):
    """Ask GPT to generate a unique, high-CPC long-tail keyword topic. 재시도 강화."""
    client = OpenAI()
    year = datetime.datetime.now().year
    category = random.choice(CATEGORIES)
    used_set = set(slugify(t) for t in used_topics[-200:]) | existing_slugs

    used_list = "\n".join(f"- {t}" for t in used_topics[-50:]) if used_topics else "(none yet)"

    title = ""
    slug = ""
    for attempt in range(max_attempts):
        temperature = 1.0 + 0.1 * attempt   # 점점 다양성 ↑
        prompt_strength = "" if attempt == 0 else f" (PREVIOUS ATTEMPT WAS DUPLICATE — try a totally different angle. Attempt #{attempt + 1})"
        response = _openai_retry(lambda: client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=200,
            temperature=temperature,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You generate blog post titles for a {BLOG_NICHE} blog.\n"
                        "TARGET: HIGH-CPC buyer-intent long-tail keywords that drive ad revenue.\n\n"
                        "Preferred title patterns (pick one that fits):\n"
                        "- 'Best [product/service] for [specific use case] in {YEAR}'\n"
                        "- '[Brand A] vs [Brand B]: Which Is Better for [use case] in {YEAR}?'\n"
                        "- 'Is [product/service] Worth It in {YEAR}? My [N]-Month Review'\n"
                        "- 'How Much Does [thing] Cost in {YEAR}? Real Numbers From My Experience'\n"
                        "- '[N] Cheapest [things] That Actually [benefit] in {YEAR}'\n"
                        "- 'I Tried [product] for [N] [days/weeks] - Here Is What Happened'\n"
                        "- '[Tool] Review {YEAR}: Pros, Cons, and Cheaper Alternatives'\n"
                        "- 'Top [N] [service type] for [specific audience] in {YEAR} (Ranked)'\n\n"
                        "Rules:\n"
                        "- Long-tail (5-12 words) real Google search query\n"
                        "- Buyer intent > informational intent (people about to spend money)\n"
                        "- Mention specific product/brand/price/number when natural (drives CPC)\n"
                        f"- Relevant to {year}\n"
                        "- MUST be completely different from the used titles below\n"
                        "- DO NOT rephrase an existing title\n"
                        "- Avoid pure listicles without buyer intent (e.g., '10 tips for X' without a product angle)\n\n"
                        f"{prompt_strength}\n"
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
        if norm_slug not in used_set:
            break
        # 다른 카테고리로도 한 번 시도
        if attempt == 2:
            category = random.choice(CATEGORIES)

    return title, category, slug


def generate_post_content(title, category, recent_titles):
    """Generate high-quality blog post with FAQ and internal linking. (retry 3x)"""
    client = OpenAI()
    return _generate_post_content_inner(client, title, category, recent_titles)


def _generate_post_content_inner(client, title, category, recent_titles):

    internal_links_hint = ""
    if recent_titles:
        links = "\n".join(f"- {t}" for t in recent_titles[:5])
        internal_links_hint = (
            f"\n\nFor internal linking, naturally reference 1-2 of these related articles "
            f"where relevant (use the exact title in a mention like "
            f"'as we covered in [Article Title]'):\n{links}"
        )

    response = _openai_retry(lambda: client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=5000,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f'Write a comprehensive, ad-revenue-optimized blog post titled: "{title}"\n\n'
                    f"Category: {category.replace('-', ' ')}\n\n"
                    "Structure (follow ALL):\n"
                    "1. First-person hook intro (2-3 sentences, use I/me/my; mention a specific dollar amount or month)\n"
                    "2. 5-7 H2 sections; each section with 2-3 H3 subsections where useful\n"
                    "3. ONE Markdown comparison table with 4+ rows and 3+ columns (real values or realistic ranges)\n"
                    "4. At least 2 H2 sections that mention specific REAL brands/products/services by name and compare them honestly\n"
                    "5. A '## What Most Guides Get Wrong' section with 3 contrarian insights\n"
                    "6. A '## Is It Worth It?' or '## My Verdict' section addressing the reader's purchase hesitation\n"
                    "7. A '## Frequently Asked Questions' section with 4-5 ### Q&A pairs (include 1-2 price-related questions)\n"
                    "8. Conclusion with a clear next step the reader can take today\n\n"
                    "Commercial intent is the priority (this blog monetizes via Google AdSense; buyer-intent pages earn 3-10x more per view):\n"
                    "- Mention real products, brands, or services by name. Never invent fake brand names.\n"
                    "- Include realistic US dollar price ranges where relevant.\n"
                    "- Use buyer-intent phrases: 'is it worth it', 'cheaper alternative', 'best for X budget', 'before you buy'.\n"
                    "- Do NOT fabricate URLs. Say 'check current price on the brand's official site' instead.\n\n"
                    "First-person voice is mandatory: use 'I', 'my', 'in my experience' at least 4 times.\n"
                    "Author persona: Kkuma Park, an indie writer in Seoul who writes from personal testing.\n"
                    "Avoid generic 'many people' claims. Use specific numbers, months, dollar amounts.\n\n"
                    "Write 2000-2800 words. Longer is better for ranking and total ad impressions, but only if every paragraph pulls weight."
                    f"{internal_links_hint}"
                ),
            },
        ],
    ))

    return response.choices[0].message.content


def generate_meta_description(title):
    """Generate a unique, compelling meta description."""
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=100,
        messages=[
            {
                "role": "system",
                "content": (
                    "Write a compelling meta description for a blog post. "
                    "150-160 characters max. Include the main keyword. "
                    "Add a call-to-action. Reply with ONLY the description."
                ),
            },
            {"role": "user", "content": f"Title: {title}"},
        ],
    )
    desc = response.choices[0].message.content.strip().strip('"')
    return desc[:160]


def create_post():
    """Generate and save a new unique blog post."""
    used_topics = load_used_topics()
    existing_slugs = get_existing_slugs()
    recent_titles = get_recent_titles(10)

    title, category, slug = generate_unique_topic(used_topics, existing_slugs)
    print(f"Generating post: {title}")
    print(f"Category: {category}")

    content = generate_post_content(title, category, recent_titles)
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
