"""PetCarePro Auto Post Generator"""

from openai import OpenAI
import datetime, os, random, re

TOPIC_POOLS = {
    "dog_care": [
        "How to Train Your Dog to Stop Barking",
        "{number} Signs Your Dog Is Happy and Healthy",
        "Best Dog Foods for {year}: Complete Guide",
        "How to Stop Your Dog from Pulling on the Leash",
        "How Often Should You Walk Your Dog",
        "{number} Human Foods That Are Toxic to Dogs",
        "How to Potty Train a Puppy Fast",
    ],
    "cat_care": [
        "Why Does My Cat Meow So Much at Night",
        "{number} Signs Your Cat Loves You",
        "Best Cat Foods for Indoor Cats in {year}",
        "How to Stop a Cat from Scratching Furniture",
        "How Often Should You Take Your Cat to the Vet",
        "{number} Things Your Cat Wants You to Know",
        "Indoor vs Outdoor Cats: Pros and Cons",
    ],
    "pet_health": [
        "{number} Signs Your Pet Needs to See a Vet Immediately",
        "How to Keep Your Pet's Teeth Clean",
        "Pet Allergies: Symptoms and Solutions",
        "How to Protect Your Pet from Fleas and Ticks in {year}",
        "Common Pet Illnesses and How to Prevent Them",
        "How Much Exercise Does Your Pet Really Need",
        "Pet Vaccination Guide: What You Need to Know in {year}",
    ],
    "pet_nutrition": [
        "Raw Food Diet for Dogs: Is It Worth It",
        "How to Choose the Best Pet Food in {year}",
        "{number} Healthy Homemade Dog Treat Recipes",
        "Grain-Free Pet Food: Good or Bad",
        "How Much Should You Feed Your Dog Based on Weight",
        "Best Supplements for Dogs and Cats in {year}",
        "Wet Food vs Dry Food: Which Is Better for Your Pet",
    ],
    "training": [
        "How to Teach Your Dog {number} Basic Commands",
        "Crate Training Guide for Puppies",
        "How to Socialize Your Dog with Other Dogs",
        "Clicker Training for Dogs: Complete Beginner Guide",
        "How to Stop Your Dog from Jumping on People",
        "{number} Dog Training Mistakes Owners Make",
        "How to Train Your Cat to Use a Litter Box",
    ],
    "pet_products": [
        "Best Dog Beds for {year}: Top {number} Picks",
        "Best Automatic Pet Feeders in {year}",
        "Best Pet Cameras to Watch Your Pet While Away",
        "Best Dog Harnesses Compared {year}",
        "Best Cat Trees and Towers for {year}",
        "Best Pet Insurance Companies in {year}",
        "Best Interactive Dog Toys to Keep Them Busy",
    ],
}

SYSTEM_PROMPT = """You are an expert pet care writer for a blog called PetCarePro.
Write SEO-optimized, informative articles about pet care.

Rules:
- Friendly, warm tone like talking to a fellow pet lover
- Short paragraphs (2-3 sentences max)
- Practical, actionable advice
- Use headers (##) to break up sections
- Include bullet points and numbered lists
- Write between 1200-1800 words
- Naturally include the main keyword 3-5 times
- Include specific product recommendations where relevant
- End with a clear takeaway
- Do NOT include AI disclaimers
- Write as an experienced veterinary journalist
- Do NOT use markdown title (# Title) - just start with the content
"""

def pick_topic():
    year = datetime.datetime.now().year
    number = random.choice([3, 5, 7, 10])
    category = random.choice(list(TOPIC_POOLS.keys()))
    title_template = random.choice(TOPIC_POOLS[category])
    return title_template.format(year=year, number=number), category

def generate_post_content(title, category):
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini", max_tokens=4000,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Write a blog post: \"{title}\"\nCategory: {category.replace('_', ' ')}\n1200-1800 words, ## headers, SEO-friendly."},
        ],
    )
    return response.choices[0].message.content

def slugify(title):
    slug = re.sub(r'[^a-z0-9\s-]', '', title.lower())
    return re.sub(r'[\s-]+', '-', slug).strip('-')

def get_repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_existing_titles():
    posts_dir = os.path.join(get_repo_root(), '_posts')
    titles = set()
    if os.path.exists(posts_dir):
        for f in os.listdir(posts_dir):
            if f.endswith('.md'): titles.add(f[11:-3])
    return titles

def create_post():
    existing = get_existing_titles()
    for _ in range(10):
        title, category = pick_topic()
        slug = slugify(title)
        if slug not in existing: break
    else:
        title, category = pick_topic()
        slug = slugify(title) + f"-{random.randint(100,999)}"
    print(f"Generating: {title}")
    content = generate_post_content(title, category)
    today = datetime.datetime.now()
    filename = f"{today.strftime('%Y-%m-%d')}-{slug}.md"
    posts_dir = os.path.join(get_repo_root(), '_posts')
    os.makedirs(posts_dir, exist_ok=True)
    filepath = os.path.join(posts_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"""---\nlayout: post\ntitle: \"{title}\"\ndate: {today.strftime('%Y-%m-%d %H:%M:%S')} +0000\ncategories: [{category.replace('_','-')}]\ndescription: \"{title} - Expert pet care tips and advice.\"\n---\n\n{content}\n""")
    print(f"Saved: {filepath}")
    return filepath, filename

if __name__ == '__main__':
    filepath, filename = create_post()
    print(f"Done! {filename}")

if __name__ == '__main__':
    # Every 5th post: generate a Gumroad promo post
    from promo_post import should_write_promo, create_promo_post
    if should_write_promo():
        print("Generating promotional post...")
        filepath, filename = create_promo_post()
    else:
        filepath, filename = create_post()
    print(f"Done! Post generated: {filename}")
