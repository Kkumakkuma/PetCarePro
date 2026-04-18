"""
영어 블로그 10개 일일 점검 → 텔레그램 알림.
GitHub Actions cron으로 매일 KST 18시 실행.

env:
  TELEGRAM_BOT_TOKEN — Telegram bot token
  TELEGRAM_CHAT_ID   — 알림 받을 chat id
"""
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

GH_USER = "Kkumakkuma"
BLOGS = [
    "CarBuyingGuide", "CookingMadeEasy", "FitnessDailyTips", "HealthyLifeHub",
    "HomeFixGuide", "ParentingSimple", "PetCarePro", "SmartMoneyDaily",
    "TechSimplified", "TravelBudgetPro",
]

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()


def send_telegram(text: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram secrets missing — skip"); print(text); return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": TELEGRAM_CHAT_ID, "text": text}).encode()
    try:
        urllib.request.urlopen(url, data, timeout=15)
    except Exception as e:
        print(f"Telegram send failed: {e}")


def list_posts(blog: str) -> list[str]:
    """GitHub API로 _posts 디렉토리 파일명 목록."""
    url = f"https://api.github.com/repos/{GH_USER}/{blog}/contents/_posts"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    # GitHub Actions 토큰이 있으면 사용 (rate limit ↑)
    gh_token = os.environ.get("GITHUB_TOKEN")
    if gh_token:
        req.add_header("Authorization", f"Bearer {gh_token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        items = json.load(r)
    return [it["name"] for it in items if isinstance(it, dict) and it.get("name", "").endswith(".md")]


def check_blog(blog: str, today: str, yesterday: str) -> dict:
    files = list_posts(blog)
    slug_count: dict[str, int] = {}
    today_count = 0
    yesterday_count = 0
    for f in files:
        m = re.match(r"^(\d{4}-\d{2}-\d{2})-(.+)\.md$", f)
        if not m:
            continue
        d, slug = m.group(1), re.sub(r"-\d{1,3}$", "", m.group(2))  # -2,-3 접미사 무시
        slug_count[slug] = slug_count.get(slug, 0) + 1
        if d == today:
            today_count += 1
        elif d == yesterday:
            yesterday_count += 1
    dup = {s: c for s, c in slug_count.items() if c > 1}
    return {
        "blog": blog,
        "total": len(files),
        "today": today_count,
        "yesterday": yesterday_count,
        "duplicates": dup,
    }


def main():
    # KST 기준 오늘/어제
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    today = now.date().isoformat()
    yesterday = (now.date() - timedelta(days=1)).isoformat()

    results = []
    errors = []
    for b in BLOGS:
        try:
            results.append(check_blog(b, today, yesterday))
        except Exception as e:
            errors.append(f"{b}: {e}")

    problems = []
    summary_ok = []
    for r in results:
        # 24시간 합 (오늘 + 어제) — KST 18시 점검이라 24h 범위
        recent = r["today"] + r["yesterday"]
        if r["duplicates"]:
            problems.append(f"⚠ {r['blog']}: 중복 {len(r['duplicates'])}건 → {list(r['duplicates'].keys())[:2]}")
        elif recent < 4:
            problems.append(f"⚠ {r['blog']}: 24h 발행 {recent}건 (누락 의심, 기대치 6)")
        else:
            summary_ok.append(f"{r['blog']}({recent})")

    if problems or errors:
        msg = f"📊 블로그 일일 점검 ({today})\n\n" + "\n".join(problems)
        if errors:
            msg += "\n\n에러:\n" + "\n".join(errors)
        if summary_ok:
            msg += f"\n\n나머지 정상: {', '.join(summary_ok)}"
    else:
        total_24h = sum(r["today"] + r["yesterday"] for r in results)
        msg = f"✅ 블로그 10개 모두 정상 ({today})\n중복 0, 24h 합계 {total_24h}건"

    print(msg)
    send_telegram(msg)


if __name__ == "__main__":
    main()
