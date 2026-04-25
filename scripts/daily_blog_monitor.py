"""
영어 블로그 10개 일일 점검 → 텔레그램 알림.
GitHub Actions cron으로 매일 1회 실행 (UTC 기준 cron 지연 무관).

윈도우: 실행 시각 기준 최근 24시간 자동발행 커밋 카운트.
auto-post.yml이 4시간 cron이므로 정상이면 블로그당 4~6건/일.

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


def list_recent_commits(blog: str, since_iso: str) -> list[dict]:
    """GitHub API로 since 시각 이후 main 커밋 목록 (자동발행 커밋만 카운트)."""
    url = (
        f"https://api.github.com/repos/{GH_USER}/{blog}/commits"
        f"?sha=main&since={since_iso}&per_page=100"
    )
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    gh_token = os.environ.get("GITHUB_TOKEN")
    if gh_token:
        req.add_header("Authorization", f"Bearer {gh_token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def check_blog(blog: str, since_iso: str) -> dict:
    """전체 _posts 스캔으로 중복 검사 + 최근 24h 자동발행 커밋 카운트로 발행량 산출."""
    files = list_posts(blog)
    slug_count: dict[str, int] = {}
    for f in files:
        m = re.match(r"^(\d{4}-\d{2}-\d{2})-(.+)\.md$", f)
        if not m:
            continue
        slug = re.sub(r"-\d{1,3}$", "", m.group(2))  # -2,-3 접미사 무시
        slug_count[slug] = slug_count.get(slug, 0) + 1
    dup = {s: c for s, c in slug_count.items() if c > 1}

    commits = list_recent_commits(blog, since_iso)
    # 자동발행 커밋만 카운트 ("Auto-publish new article|recipe ..." 형식)
    recent = sum(
        1 for c in commits
        if c.get("commit", {}).get("message", "").startswith("Auto-publish new")
    )
    return {
        "blog": blog,
        "total": len(files),
        "recent": recent,
        "duplicates": dup,
    }


def main():
    # 최근 24시간 윈도우 (cron 지연/실행시각 무관하게 안정)
    now_utc = datetime.now(timezone.utc)
    since_dt = now_utc - timedelta(hours=24)
    since_iso = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    now_str = now_utc.strftime("%Y-%m-%d %H:%M")
    since_str = since_dt.strftime("%Y-%m-%d %H:%M")

    results = []
    errors = []
    for b in BLOGS:
        try:
            results.append(check_blog(b, since_iso))
        except Exception as e:
            errors.append(f"{b}: {e}")

    problems = []
    summary_ok = []
    low_volume = []  # 24h 발행 0~1건 블로그 (cron 1회/4h이므로 정상은 4~6건)
    for r in results:
        if r["duplicates"]:
            problems.append(
                f"⚠ {r['blog']}: 중복 {len(r['duplicates'])}건 → {list(r['duplicates'].keys())[:2]}"
            )
        else:
            summary_ok.append(f"{r['blog']}({r['recent']})")
        if r["recent"] <= 1:
            low_volume.append(f"{r['blog']}({r['recent']}건)")

    recent_total = sum(r["recent"] for r in results)
    header = f"최근 24h (UTC {since_str} ~ {now_str}) 자동발행: {recent_total}건"

    if problems or errors or low_volume:
        msg = f"📊 블로그 점검\n{header}\n\n"
        if problems:
            msg += "\n".join(problems) + "\n\n"
        if low_volume:
            msg += f"⚠ 24h 발행 부족 (1건 이하): {', '.join(low_volume)}\n\n"
        if errors:
            msg += "에러:\n" + "\n".join(errors) + "\n\n"
        if summary_ok:
            msg += f"나머지 정상: {', '.join(summary_ok)}"
    else:
        msg = (
            f"✅ 블로그 10개 정상 · 중복 0\n"
            f"{header}\n"
            + "\n".join(f"- {r['blog']}: {r['recent']}건" for r in results)
        )

    print(msg)
    send_telegram(msg)


if __name__ == "__main__":
    main()
