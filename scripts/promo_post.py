"""
PetCarePro - Gumroad Promotional Post Generator
Generates SEO-optimized promotional articles for Notion templates.
"""

from openai import OpenAI
import datetime
import os
import random
import re

NICHE = "pet care"
STORE_URL = "https://smarttemplatesell.gumroad.com/l"
PROMO_PRODUCTS = [
    {"name": "Pet Health Tracker", "price": "$5.99", "slug": "pet-health", "desc": "Track vet visits, vaccinations, medications, and complete health history."},
    {"name": "Pet Care Schedule", "price": "$5.99", "slug": "pet-schedule", "desc": "Never miss a feeding, walk, or grooming session."},
]

PROMO_SYSTEM_PROMPT = """You are an expert pet care writer.
Write a helpful, informative blog post that naturally recommends a Notion template product.
The post should provide genuine value and advice, then naturally introduce the template as a helpful tool.

Rules:
- Write 800-1200 words
- Start with a real problem the reader faces
- Provide 3-5 genuine tips or solutions
- Naturally mention the Notion template as one of the solutions
- Include the product link naturally in context
- Do NOT make it sound like a pure advertisement
- Use ## headers and bullet points
- Conversational, helpful tone
- Do NOT mention AI or being AI-generated
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


def should_write_promo():
    posts_dir = os.path.join(get_repo_root(), "_posts")
    if not os.path.exists(posts_dir):
        return False
    post_count = len([f for f in os.listdir(posts_dir) if f.endswith(".md")])
    return post_count > 0 and post_count % 5 == 0


def create_promo_post():
    product = random.choice(PROMO_PRODUCTS)
    product_url = STORE_URL + "/" + product["slug"]
    niche_title = NICHE.title()

    client = OpenAI()
    prompt = (
        "Write a helpful blog post that naturally recommends this product:\n"
        "Product: " + product["name"] + " (" + product["price"] + ")\n"
        "Description: " + product["desc"] + "\n"
        "Link: " + product_url + "\n\n"
        "The post should solve a real problem and mention the template as a helpful tool. "
        "Include the link naturally with markdown anchor text."
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=3000,
        messages=[
            {"role": "system", "content": PROMO_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )

    post_content = response.choices[0].message.content
    title = "How a " + product["name"] + " Can Transform Your " + niche_title + " Game"

    today = datetime.datetime.now()
    date_str = today.strftime("%Y-%m-%d")
    slug = slugify(title)
    filename = date_str + "-" + slug + ".md"

    posts_dir = os.path.join(get_repo_root(), "_posts")
    os.makedirs(posts_dir, exist_ok=True)
    filepath = os.path.join(posts_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write("layout: post\n")
        f.write('title: "' + title + '"\n')
        f.write("date: " + today.strftime("%Y-%m-%d %H:%M:%S") + " +0000\n")
        f.write("categories: [product-review]\n")
        f.write('description: "' + product["desc"] + '"\n')
        f.write("---\n\n")
        f.write(post_content)

    print("Promo post saved: " + filepath)
    return filepath, filename


if __name__ == "__main__":
    filepath, filename = create_promo_post()
    print("Done! Promo post: " + filename)
