"""
PetCarePro - Gumroad Promotional Post Generator v2
- Dynamic unique titles (no more fixed "How a X Can Transform Your Y Game")
- Each promo post takes a different angle/problem
- Tracks used promo titles to prevent duplicates
"""

from openai import OpenAI
import datetime
import json
import os
import random
import re

BLOG_NAME = "PetCarePro"
BLOG_NICHE = "pet care"
STORE_URL = "https://smarttemplatesell.gumroad.com/l"

PROMO_PRODUCTS = [
    {
        "name": "Pet Health Tracker",
        "price": "$5.99",
        "slug": "pet-health",
        "desc": "Track your pet's health, vet visits, and medications in one place.",
        "keywords": ["pet health", "vet visits", "pet medication", "health tracking"],
    },
    {
        "name": "Pet Care Schedule",
        "price": "$5.99",
        "slug": "pet-schedule",
        "desc": "Never miss a feeding, walk, or grooming session with our pet care scheduler.",
        "keywords": ["pet schedule", "feeding routine", "pet grooming", "daily pet care"],
    },
]

PROMO_SYSTEM_PROMPT = """You are an expert pet care writer.
Write a helpful, SEO-optimized blog post that naturally recommends a Notion template.

Rules:
- Write 1000-1500 words
- Start with a real, specific problem the reader faces
- Provide 4-5 genuine, actionable tips
- Naturally introduce the template as one solution (not the only one)
- Include the product link with natural anchor text
- Use ## headers and bullet points
- Include a FAQ section with 2-3 questions
- Conversational, helpful tone - NOT salesy
- Do NOT mention AI or being AI-generated
- The post must stand on its own as valuable content even without the product mention
"""


def slugify(title):
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def get_repo_root():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(script_dir)


def load_used_promo_titles():
    filepath = os.path.join(get_repo_root(), "scripts", "used_promo_titles.json")
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_used_promo_titles(titles):
    filepath = os.path.join(get_repo_root(), "scripts", "used_promo_titles.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(titles, f, indent=2)


def should_write_promo():
    posts_dir = os.path.join(get_repo_root(), "_posts")
    if not os.path.exists(posts_dir):
        return False
    post_count = len([f for f in os.listdir(posts_dir) if f.endswith(".md")])
    return post_count > 0 and post_count % 5 == 0


def generate_promo_title(product, used_titles):
    """Generate a unique, SEO-friendly title that naturally fits the product."""
    client = OpenAI()
    year = datetime.datetime.now().year

    used_list = "\n".join(f"- {t}" for t in used_titles[-20:]) if used_titles else "(none)"

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=100,
        temperature=1.0,
        messages=[
            {
                "role": "system",
                "content": (
                    f"Generate ONE blog post title for a {BLOG_NICHE} blog. "
                    f"The post will naturally mention a {product['name']} template. "
                    "The title should focus on solving a REAL PROBLEM, not on the product.\n\n"
                    "Requirements:\n"
                    "- Long-tail SEO keyword (6-12 words)\n"
                    f"- Related to: {', '.join(product['keywords'])}\n"
                    "- Problem-focused, not product-focused\n"
                    f"- Relevant to {year}\n"
                    "- MUST be different from used titles below\n"
                    "Reply with ONLY the title."
                ),
            },
            {
                "role": "user",
                "content": f"Used titles:\n{used_list}\n\nGenerate:",
            },
        ],
    )

    return response.choices[0].message.content.strip().strip('"').strip("'")


def create_promo_post():
    product = random.choice(PROMO_PRODUCTS)
    product_url = f"{STORE_URL}/{product['slug']}"

    used_titles = load_used_promo_titles()
    title = generate_promo_title(product, used_titles)

    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=4000,
        messages=[
            {"role": "system", "content": PROMO_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f'Write a blog post titled: "{title}"\n\n'
                    f"Product to mention naturally: {product['name']} ({product['price']})\n"
                    f"Description: {product['desc']}\n"
                    f"Link: {product_url}\n\n"
                    "The post should solve a real problem. Mention the template as ONE of several solutions. "
                    "Include the link with natural anchor text. Add a FAQ section."
                ),
            },
        ],
    )

    post_content = response.choices[0].message.content
    today = datetime.datetime.now()
    date_str = today.strftime("%Y-%m-%d")
    slug = slugify(title)
    filename = f"{date_str}-{slug}.md"

    posts_dir = os.path.join(get_repo_root(), "_posts")
    os.makedirs(posts_dir, exist_ok=True)
    filepath = os.path.join(posts_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write("layout: post\n")
        f.write(f'title: "{title}"\n')
        f.write(f"date: {today.strftime('%Y-%m-%d %H:%M:%S')} +0000\n")
        f.write("categories: [product-review]\n")
        f.write(f'description: "{product["desc"]}"\n')
        f.write(f"tags: [product-review, {BLOG_NICHE.replace(' ', '-')}]\n")
        f.write("---\n\n")
        f.write(post_content)

    # Track used title
    used_titles.append(title)
    save_used_promo_titles(used_titles)

    print(f"Promo post saved: {filepath}")
    return filepath, filename


if __name__ == "__main__":
    filepath, filename = create_promo_post()
    print(f"Done! Promo post: {filename}")
