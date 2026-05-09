"""영블용 자동 핀 이미지 생성 v2 (Pexels 사진 배경 + 다크 오버레이 + typography).

v1(2026-05-08): 단색 배경 + 텍스트만 → 시각적으로 심심함 (쿠마님 2026-05-09 지적)
v2(2026-05-09): Pexels portrait 사진 배경 + 그라디언트 오버레이 + 카테고리 컬러 라벨
              + 큰 제목 typography. fallback으로 단색 배경(사진 못 가져왔을 때).
"""
import os
import re
import urllib.request
import urllib.parse
import io
import random
import hashlib
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

WIDTH, HEIGHT = 1000, 1500
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")

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


# 영블 niche별 컬러 + Pexels 검색 키워드
BLOG_PALETTE = {
    "SmartMoneyDaily":   {"accent": "#16a34a", "label": "PERSONAL FINANCE",  "kw": "money saving cash budget"},
    "HealthyLifeHub":    {"accent": "#0891b2", "label": "HEALTH & WELLNESS", "kw": "wellness healthy lifestyle"},
    "FitnessDailyTips":  {"accent": "#2563eb", "label": "FITNESS",           "kw": "fitness workout gym"},
    "TechSimplified":    {"accent": "#7c3aed", "label": "TECH & DIGITAL",    "kw": "technology gadget laptop"},
    "CookingMadeEasy":   {"accent": "#dc2626", "label": "COOKING & RECIPES", "kw": "cooking food kitchen"},
    "HomeFixGuide":      {"accent": "#d97706", "label": "HOME & DIY",        "kw": "home interior cozy"},
    "ParentingSimple":   {"accent": "#db2777", "label": "PARENTING",         "kw": "family children kids"},
    "PetCarePro":        {"accent": "#ea580c", "label": "PET CARE",          "kw": "dog cat pet"},
    "TravelBudgetPro":   {"accent": "#0d9488", "label": "TRAVEL",            "kw": "travel destination scenic"},
    "CarBuyingGuide":    {"accent": "#475569", "label": "CAR & AUTO",        "kw": "car automobile road"},
}

# 카테고리별 보강 키워드 (없으면 niche 기본만 사용)
CATEGORY_KEYWORDS = {
    "credit-score": "credit card",
    "saving-money": "piggy bank coins",
    "investing": "stock chart",
    "side-hustle": "laptop work",
    "passive-income": "money tree",
    "retirement": "elderly couple",
    "frugal-living": "thrift simple",
    "budgeting": "calculator notebook",
    "stress-management": "meditation calm",
    "nutrition": "salad healthy",
    "weight-loss": "fitness scale",
    "yoga": "yoga pose",
    "skincare": "skincare beauty",
    "smartphones": "smartphone modern",
    "ai-tools": "artificial intelligence",
    "productivity": "desk workspace",
    "recipes": "delicious dish",
    "meal-prep": "meal prep containers",
    "diy-repair": "tools workshop",
    "interior": "modern interior",
    "baby-care": "baby cute",
    "education": "study books",
    "dog-care": "happy dog",
    "cat-care": "cute cat",
    "vacation": "vacation beach",
    "hostel": "backpack travel",
    "ev": "electric car charging",
    "used-car": "used car lot",
}

CATEGORY_LABEL = {
    "credit-score": "CREDIT TIPS",
    "saving-money": "SAVE MONEY",
    "investing": "INVESTING",
    "side-hustle": "SIDE HUSTLE",
    "passive-income": "PASSIVE INCOME",
    "retirement": "RETIREMENT",
    "frugal-living": "FRUGAL LIVING",
    "budgeting": "BUDGETING",
    "product-review": "REVIEW",
}

# 사진 못 가져왔을 때 단색 fallback 배경
FALLBACK_BG = {
    "SmartMoneyDaily":   "#0f5132",
    "HealthyLifeHub":    "#0c4a6e",
    "FitnessDailyTips":  "#1e3a8a",
    "TechSimplified":    "#4c1d95",
    "CookingMadeEasy":   "#7f1d1d",
    "HomeFixGuide":      "#451a03",
    "ParentingSimple":   "#831843",
    "PetCarePro":        "#7c2d12",
    "TravelBudgetPro":   "#134e4a",
    "CarBuyingGuide":    "#0f172a",
}


def _clean_title(text: str) -> str:
    text = EMOJI_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
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


def _fetch_pexels_photo(query: str, seed: str) -> Image.Image:
    """Pexels 검색 → portrait 사진 1장 다운로드 → PIL Image 반환. 실패 시 None."""
    if not PEXELS_API_KEY:
        return None
    try:
        url = (
            f"https://api.pexels.com/v1/search"
            f"?query={urllib.parse.quote(query)}"
            f"&orientation=portrait&size=large&per_page=15"
        )
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": PEXELS_API_KEY,
                "User-Agent": "Mozilla/5.0 (compatible; AutoPinBot/1.0)",
            },
        )
        resp = urllib.request.urlopen(req, timeout=20)
        import json as _json
        data = _json.loads(resp.read())
        photos = data.get("photos", [])
        if not photos:
            return None
        # seed로 고정 선택 (같은 글 = 같은 사진)
        idx = int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(photos)
        photo_url = photos[idx]["src"].get("portrait") or photos[idx]["src"].get("large")
        if not photo_url:
            return None
        img_req = urllib.request.Request(
            photo_url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; AutoPinBot/1.0)"},
        )
        img_resp = urllib.request.urlopen(img_req, timeout=20)
        img = Image.open(io.BytesIO(img_resp.read())).convert("RGB")
        return img
    except Exception as e:
        print(f"  [pexels] fail: {e}")
        return None


def _make_background(blog_name: str, category: str, title: str) -> Image.Image:
    """1000x1500 배경 이미지 생성. Pexels 사진 시도 → 실패 시 단색 fallback."""
    pal = BLOG_PALETTE.get(blog_name, BLOG_PALETTE["SmartMoneyDaily"])
    cat_kw = CATEGORY_KEYWORDS.get((category or "").lower(), "")
    query = f"{cat_kw} {pal['kw']}".strip() if cat_kw else pal["kw"]

    seed = title + blog_name
    photo = _fetch_pexels_photo(query, seed)

    if photo is not None:
        # cover-style resize + center crop to 1000x1500
        ratio = max(WIDTH / photo.width, HEIGHT / photo.height)
        new_w, new_h = int(photo.width * ratio), int(photo.height * ratio)
        photo = photo.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - WIDTH) // 2
        top = (new_h - HEIGHT) // 2
        bg = photo.crop((left, top, left + WIDTH, top + HEIGHT))
        # 살짝 블러로 텍스트 가독성
        bg = bg.filter(ImageFilter.GaussianBlur(radius=1))
        return bg

    # fallback: 단색
    return Image.new("RGB", (WIDTH, HEIGHT), FALLBACK_BG.get(blog_name, "#1f2937"))


def _apply_overlay(img: Image.Image) -> Image.Image:
    """배경 위 다크 그라디언트 오버레이 — 위→아래 점점 어두워짐. 텍스트 가독성 확보."""
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    # 위쪽: 30% 어둡게, 아래쪽: 75% 어둡게
    for y in range(HEIGHT):
        alpha = int(80 + (y / HEIGHT) * 130)  # 80 ~ 210
        draw.rectangle([0, y, WIDTH, y + 1], fill=(0, 0, 0, alpha))
    base = img.convert("RGBA")
    out = Image.alpha_composite(base, overlay)
    return out.convert("RGB")


def generate_pin(title: str, blog_name: str, category: str, output_path: str) -> str:
    """영블 글 → 1000x1500 핀 이미지 생성 (v2: Pexels 사진 배경)."""
    pal = BLOG_PALETTE.get(blog_name, BLOG_PALETTE["SmartMoneyDaily"])
    label = CATEGORY_LABEL.get((category or "").lower(), pal["label"])

    # 1. 배경 사진 + 오버레이
    bg = _make_background(blog_name, category, title)
    img = _apply_overlay(bg)
    draw = ImageDraw.Draw(img)

    # 2. 상단 카테고리 라벨 박스 (accent 컬러)
    label_font = _font("bold", 32)
    bbox = draw.textbbox((0, 0), label, font=label_font)
    lw, lh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    box_pad_x, box_pad_y = 28, 14
    box_w = lw + box_pad_x * 2
    box_h = lh + box_pad_y * 2
    box_x = (WIDTH - box_w) // 2
    box_y = 90
    draw.rectangle(
        [box_x, box_y, box_x + box_w, box_y + box_h],
        fill=pal["accent"],
    )
    draw.text(
        (box_x + box_pad_x, box_y + box_pad_y - 4),
        label,
        font=label_font,
        fill="#ffffff",
    )

    # 3. 중앙~하단 큰 제목
    clean = _clean_title(title)
    title_size = 88
    title_font = _font("bold", title_size)
    max_w = WIDTH - 100
    lines = _wrap_title(clean, title_font, max_w, draw)
    while len(lines) > 6 and title_size > 56:
        title_size -= 6
        title_font = _font("bold", title_size)
        lines = _wrap_title(clean, title_font, max_w, draw)

    line_h = title_size + 14
    total_h = line_h * len(lines)
    y0 = HEIGHT - 290 - total_h  # 하단에서 위로 290px 띄워서 시작 (footer 위)
    # 텍스트에 그림자 (가독성)
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=title_font)
        lw = bbox[2] - bbox[0]
        x = (WIDTH - lw) // 2
        y = y0 + i * line_h
        # 그림자
        draw.text((x + 3, y + 3), line, font=title_font, fill=(0, 0, 0, 200))
        # 본문
        draw.text((x, y), line, font=title_font, fill="#ffffff")

    # 4. accent 색 띠 (제목 위, 시각 강조)
    bar_y = y0 - 30
    bar_w = 80
    draw.rectangle(
        [(WIDTH - bar_w) // 2, bar_y, (WIDTH + bar_w) // 2, bar_y + 6],
        fill=pal["accent"],
    )

    # 5. 하단 브랜드 푸터
    brand_font = _font("regular", 28)
    brand_text = f"kkumakkuma.github.io / {blog_name}"
    bbox = draw.textbbox((0, 0), brand_text, font=brand_font)
    bw = bbox[2] - bbox[0]
    draw.text(
        ((WIDTH - bw) // 2, HEIGHT - 70),
        brand_text,
        font=brand_font,
        fill="#e5e7eb",
    )

    Path(os.path.dirname(output_path)).mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG", optimize=True)
    return output_path


if __name__ == "__main__":
    out = generate_pin(
        "How to Save Money Fast in 2026 — 7 Simple Steps That Actually Work",
        "SmartMoneyDaily",
        "saving-money",
        "test_pin_v2.png",
    )
    print(f"v2 테스트 핀 생성: {out}")
