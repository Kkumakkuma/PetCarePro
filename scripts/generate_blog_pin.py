"""영블용 자동 핀 이미지 생성 (Pillow, 1000x1500).

영블 글 발행 시 generate_post.py 후처리에서 호출:
  pin_path = generate_pin(title, category, slug, output_dir)

또는 기존 600+ 글에 일괄 적용도 같은 함수 호출.

각 영블의 niche별 컬러 팔레트 매핑됨. 105개 Gumroad 핀 만들 때 패턴 그대로 재활용.
"""
import os
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1000, 1500

# 이모지 제거 (Bahnschrift/Arial 폰트 못 그림)
EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FAFF"
    "\U00002600-\U000027BF"
    "]+",
    flags=re.UNICODE,
)

# Linux/Windows 폰트 경로 자동 폴백
FONT_CANDIDATES = {
    "bold": [
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ],
    "regular": [
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ],
}


def _font(kind: str, size: int):
    for path in FONT_CANDIDATES.get(kind, FONT_CANDIDATES["regular"]):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


# 영블 niche별 컬러 (105 Gumroad 핀과 같은 톤 — 시각 일관성)
BLOG_PALETTE = {
    "SmartMoneyDaily":   {"bg": "#0f5132", "accent": "#16a34a", "label": "PERSONAL FINANCE"},
    "HealthyLifeHub":    {"bg": "#0c4a6e", "accent": "#0891b2", "label": "HEALTH & WELLNESS"},
    "FitnessDailyTips":  {"bg": "#1e3a8a", "accent": "#2563eb", "label": "FITNESS"},
    "TechSimplified":    {"bg": "#4c1d95", "accent": "#7c3aed", "label": "TECH & DIGITAL"},
    "CookingMadeEasy":   {"bg": "#7f1d1d", "accent": "#dc2626", "label": "COOKING & RECIPES"},
    "HomeFixGuide":      {"bg": "#451a03", "accent": "#92400e", "label": "HOME & DIY"},
    "ParentingSimple":   {"bg": "#831843", "accent": "#db2777", "label": "PARENTING"},
    "PetCarePro":        {"bg": "#7c2d12", "accent": "#ea580c", "label": "PET CARE"},
    "TravelBudgetPro":   {"bg": "#134e4a", "accent": "#0d9488", "label": "TRAVEL"},
    "CarBuyingGuide":    {"bg": "#0f172a", "accent": "#475569", "label": "CAR & AUTO"},
}

# 카테고리(소문자) → 라벨 매핑 (선택. 블로그 이름 우선)
CATEGORY_LABEL = {
    "credit-score": "CREDIT TIPS",
    "saving-money": "SAVE MONEY",
    "investing": "INVESTING",
    "side-hustle": "SIDE HUSTLE",
    "passive-income": "PASSIVE INCOME",
    "retirement": "RETIREMENT",
    "frugal-living": "FRUGAL LIVING",
}

# 5가지 레이아웃 변형 (slug 해시로 고정 매핑 → 같은 글은 같은 레이아웃)
LAYOUT_VARIANTS = [
    {"top_pad": 110, "title_size": 86, "stripe": "top"},
    {"top_pad": 80, "title_size": 96, "stripe": "left"},
    {"top_pad": 140, "title_size": 78, "stripe": "bottom"},
    {"top_pad": 100, "title_size": 88, "stripe": "right"},
    {"top_pad": 90, "title_size": 92, "stripe": "diagonal"},
]


def _clean_title(text: str) -> str:
    text = EMOJI_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace("'", "'").replace("'", "'").replace(""", '"').replace(""", '"')
    return text


def _wrap_title(text: str, font, max_width: int, draw) -> list:
    words = text.split()
    lines = []
    cur = []
    for w in words:
        trial = " ".join(cur + [w])
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width:
            cur.append(w)
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines


def generate_pin(title: str, blog_name: str, category: str, output_path: str) -> str:
    """영블 글 → 1000x1500 핀 이미지 생성. output_path에 PNG 저장 후 같은 path 반환."""
    pal = BLOG_PALETTE.get(blog_name, BLOG_PALETTE["SmartMoneyDaily"])
    label = CATEGORY_LABEL.get((category or "").lower(), pal["label"])

    # slug 해시로 레이아웃 고정 (같은 글 = 같은 디자인)
    h = sum(ord(c) for c in (title + blog_name)) % len(LAYOUT_VARIANTS)
    var = LAYOUT_VARIANTS[h]

    img = Image.new("RGB", (WIDTH, HEIGHT), "#ffffff")
    draw = ImageDraw.Draw(img)

    band_h = 280
    draw.rectangle([0, 0, WIDTH, band_h], fill=pal["bg"])

    if var["stripe"] == "top":
        draw.rectangle([0, band_h, WIDTH, band_h + 12], fill=pal["accent"])
    elif var["stripe"] == "left":
        draw.rectangle([0, band_h, 18, HEIGHT - 200], fill=pal["accent"])
    elif var["stripe"] == "right":
        draw.rectangle([WIDTH - 18, band_h, WIDTH, HEIGHT - 200], fill=pal["accent"])
    elif var["stripe"] == "bottom":
        draw.rectangle([0, HEIGHT - 220, WIDTH, HEIGHT - 208], fill=pal["accent"])
    else:
        draw.polygon(
            [(0, band_h), (220, band_h), (140, band_h + 90), (0, band_h + 90)],
            fill=pal["accent"],
        )

    label_font = _font("bold", 32)
    bbox = draw.textbbox((0, 0), label, font=label_font)
    lw = bbox[2] - bbox[0]
    draw.text(((WIDTH - lw) // 2, 70), label, font=label_font, fill="#ffffff")

    brand_mini_font = _font("regular", 24)
    brand_mini = f"kkumakkuma.github.io / {blog_name}"
    bbox = draw.textbbox((0, 0), brand_mini, font=brand_mini_font)
    bmw = bbox[2] - bbox[0]
    draw.text(
        ((WIDTH - bmw) // 2, 130),
        brand_mini,
        font=brand_mini_font,
        fill="#cccccc",
    )

    # Title
    clean = _clean_title(title)
    title_size = var["title_size"]
    title_font = _font("bold", title_size)
    max_w = WIDTH - 120
    lines = _wrap_title(clean, title_font, max_w, draw)
    # 줄 너무 많으면 폰트 축소
    while len(lines) > 6 and title_size > 50:
        title_size -= 6
        title_font = _font("bold", title_size)
        lines = _wrap_title(clean, title_font, max_w, draw)

    line_h = title_size + 16
    total_h = line_h * len(lines)
    y0 = band_h + var["top_pad"]
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=title_font)
        lw = bbox[2] - bbox[0]
        x = (WIDTH - lw) // 2
        draw.text((x, y0 + i * line_h), line, font=title_font, fill="#1a1a1a")

    # Footer brand bar
    footer_h = 110
    draw.rectangle([0, HEIGHT - footer_h, WIDTH, HEIGHT], fill=pal["bg"])
    footer_font = _font("bold", 36)
    footer_text = "kkumakkuma.github.io"
    bbox = draw.textbbox((0, 0), footer_text, font=footer_font)
    fw = bbox[2] - bbox[0]
    draw.text(
        ((WIDTH - fw) // 2, HEIGHT - footer_h + 32),
        footer_text,
        font=footer_font,
        fill="#ffffff",
    )

    Path(os.path.dirname(output_path)).mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG", optimize=True)
    return output_path


if __name__ == "__main__":
    # 테스트
    out = generate_pin(
        "How to Save Money Fast in 2026 — 7 Simple Steps That Actually Work",
        "SmartMoneyDaily",
        "saving-money",
        "test_pin.png",
    )
    print(f"테스트 핀 생성: {out}")
