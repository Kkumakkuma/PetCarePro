"""
영어 블로그 점검 (수동 진단용). **텔레그램으로 직접 발송하지 않는다.**

2026-08-21 쿠마님 지시로 이 스크립트의 cron 발송을 폐지했다.
알림은 아침 10시·저녁 22시 통합 브리핑 한 통으로만 받는다(2026-07-27 지시).
블로그 점검 신호는 EC2 briefing.service 가 매일 두 번 실어 보낸다.
이 파일은 workflow_dispatch 로 수동 실행해 자세히 들여다볼 때만 쓴다.

2026-05-23 v8 단일 블로그 전략: SmartMoneyDaily 1개만 활성(하루 1회 발행).
나머지 9개 블로그는 AdSense 재심사 위해 글 전부 _drafts 로 이동 + cron 제거되어
발행 중단 상태(=GitHub _posts 디렉토리 자체가 없어 404). 따라서 모니터 대상에서
제외한다. 각 블로그를 정예화해 부활시키면 ACTIVE_BLOGS 에 다시 추가할 것.

판정 기준 (2026-08-21 교체):
  기존에는 "최근 24h 자동발행 커밋" 개수로 발행량을 셌다. 커밋 메시지가
  "Auto-publish new" / "Add post:" 로 시작하는 것만 셌는데, 2026-08-19 쿠마님 지시로
  GPT 자동 집필을 중단하고 직접 집필 체제로 바꾸면서 커밋 메시지 형식이 달라졌다
  ("Add scheduled post for ...", "Rewrite ..."). 그래서 실제로는 매일 글이 올라가는데도
  매일 "24h 발행 0건" 오탐 경고가 나갔다(8/20 창에 커밋 2건이 있었으나 0건으로 집계).
  커밋 메시지에 의존하는 방식을 버리고, _posts 파일명 날짜만 본다.
    - 오늘(UTC) 날짜 글이 있는가        → 없으면 발행 끊김
    - 오늘 이후 예약 재고가 며칠치인가  → 3일 미만이면 보충 필요
  같은 블로그를 경고와 정상 목록에 동시에 넣던 자기모순도 함께 제거했다.
"""
import json
import os
import re
import urllib.request
from datetime import datetime, timezone

GH_USER = "smartmoneydaily"  # SMD 조직 이전(2026-08-02). 일시정지 9개 블로그는 여전히 Kkumakkuma 소유 - 부활 시 소유자 분기 필요

# v8 단일 블로그 집중 전략 (2026-05-23): SmartMoneyDaily 만 활성 발행.
# PAUSED_BLOGS 9개는 _drafts 이동 + auto-post cron 제거됨 → 점검하면 404 만 남.
# 정예화 거쳐 부활시킬 때 해당 블로그를 ACTIVE_BLOGS 로 옮긴다.
ACTIVE_BLOGS = ["smartmoneydaily.github.io"]
PAUSED_BLOGS = [
    "CarBuyingGuide", "CookingMadeEasy", "FitnessDailyTips", "HealthyLifeHub",
    "HomeFixGuide", "ParentingSimple", "PetCarePro",
    "TechSimplified", "TravelBudgetPro",
]
BLOGS = ACTIVE_BLOGS

# 예약 재고가 이 일수 밑으로 떨어지면 보충 대상 (쿠마님 기준: 항상 3일치 유지)
MIN_BACKLOG_DAYS = 3


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


def check_blog(blog: str, today: str) -> dict:
    """_posts 파일명만으로 중복 검사 + 오늘 글 존재 여부 + 예약 재고 일수 산출.

    today: 'YYYY-MM-DD' (UTC). 파일명 날짜와 문자열 비교하므로 타임존 변환이 없다.
    """
    files = list_posts(blog)
    slug_count: dict[str, int] = {}
    for f in files:
        m = re.match(r"^(\d{4}-\d{2}-\d{2})-(.+)\.md$", f)
        if not m:
            continue
        slug = re.sub(r"-\d{1,3}$", "", m.group(2))  # -2,-3 접미사 무시
        slug_count[slug] = slug_count.get(slug, 0) + 1
    dup = {s: c for s, c in slug_count.items() if c > 1}

    # 파일명 날짜만으로 판정한다 — 커밋 메시지 형식에 의존하지 않는다.
    dates = sorted({
        m.group(1) for m in (re.match(r"^(\d{4}-\d{2}-\d{2})-", f) for f in files) if m
    })

    return {
        "blog": blog,
        "total": len(files),
        "has_today": today in dates,
        "backlog": len([d for d in dates if d > today]),
        "last_date": dates[-1] if dates else "-",
        "duplicates": dup,
    }


def issues_for(r: dict, today: str) -> list[str]:
    """블로그 한 곳의 문제 목록. 비어 있으면 정상."""
    out = []
    if r["duplicates"]:
        out.append(f"중복 {len(r['duplicates'])}건 {list(r['duplicates'].keys())[:2]}")
    if not r["has_today"]:
        out.append(f"오늘({today}) 글 없음, 마지막 {r['last_date']}")
    if r["backlog"] < MIN_BACKLOG_DAYS:
        out.append(f"예약 재고 {r['backlog']}일치 (기준 {MIN_BACKLOG_DAYS}일)")
    return out


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"블로그 점검 (UTC {today}) - 대상 {len(BLOGS)}개")

    bad = 0
    for b in BLOGS:
        try:
            r = check_blog(b, today)
        except Exception as e:
            print(f"  [에러] {b}: {e}")
            bad += 1
            continue
        problems = issues_for(r, today)
        if problems:
            bad += 1
            print(f"  [문제] {b}: " + " / ".join(problems))
        else:
            print(f"  [정상] {b}: 오늘 글 있음, 예약 재고 {r['backlog']}일치, 전체 {r['total']}편")

    print(f"문제 {bad}건")
    print("[텔레그램 발송 없음 - 알림은 아침/저녁 통합 브리핑 한 통으로만]")


if __name__ == "__main__":
    main()
