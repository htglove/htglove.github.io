# -*- coding: utf-8 -*-
"""카페 글 노출 순위 확인 (게시판별 비교용)
올린 지 1·3·7일째 되는 글을 네이버에서 키워드로 검색해,
  - 통합검색 첫 화면에 우리 카페 글이 나오는지 / 몇 번째 카페 글인지
  - 카페 탭에서 몇 위인지(1~30위)
를 cafe_rank.csv 에 쌓고, 게시판별 노출률을 cafe_rank_요약.txt 로 정리합니다.
  py cafe_rank_check.py          -> 1·3·7일째 글만
  py cafe_rank_check.py --all    -> 올린 글 전부 지금 확인
"""
import csv, json, os, re, sys, time, urllib.parse, urllib.request
from datetime import datetime
from playwright.sync_api import sync_playwright

BASE = r"C:\autowin"
POSTS = os.path.join(BASE, "cafe_posts")
CSV = os.path.join(BASE, "cafe_rank.csv")
SUMMARY = os.path.join(BASE, "cafe_rank_요약.txt")
CHECK_DAYS = (1, 3, 7)


def cafe_slug():
    cfg = json.load(open(os.path.join(BASE, "cafe_config.json"), encoding="utf-8"))
    return cfg["cafe_url"].rstrip("/").split("/")[-1].lower()


def posted():
    out = []
    for d in sorted(os.listdir(POSTS)):
        f = os.path.join(POSTS, d, "업로드완료.txt")
        if not os.path.exists(f):
            continue
        try:
            j = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        j["folder"] = d
        if not j.get("article_id"):
            from urllib.parse import unquote
            u = unquote(unquote(j.get("url", "")))
            m = re.search(r"articleid=(\d+)", u, re.I) or re.search(r"articles/(\d+)", u)
            j["article_id"] = m.group(1) if m else ""
        out.append(j)
    return out


def cafe_links(page):
    """화면에 보이는 순서대로 카페 글 링크 목록"""
    return page.evaluate("""() => {
      const seen = new Set(), out = [];
      document.querySelectorAll('a[href*="cafe.naver.com"]').forEach(a => {
        const h = a.href;
        if (!/cafe\\.naver\\.com\\/(ca-fe\\/cafes\\/\\d+\\/articles\\/\\d+|[A-Za-z0-9_]+\\/\\d+)/.test(h)) return;
        const key = h.split('?')[0];
        if (seen.has(key)) return;
        seen.add(key);
        out.push({href: h, text: (a.innerText || '').trim().slice(0, 80)});
      });
      return out;
    }""")


def find_rank(links, slug, aid, title):
    for i, l in enumerate(links, 1):
        h = l["href"].lower()
        if aid and (f"/{slug}/{aid}" in h or f"/articles/{aid}" in h):
            return i
        if title and title[:15] in l["text"]:
            return i
    return 0


def main():
    slug = cafe_slug()
    allmode = "--all" in sys.argv
    today = datetime.now().date()
    todo = []
    for p in posted():
        try:
            day = (today - datetime.strptime(p["posted_at"][:10], "%Y-%m-%d").date()).days
        except Exception:
            continue
        if allmode or day in CHECK_DAYS:
            p["day"] = day
            todo.append(p)
    if not todo:
        print("오늘 확인할 글이 없습니다.")
        summarize()
        return
    try:
        sys.path.insert(0, BASE)
        import run_cafe_queue
        run_cafe_queue.wait_free(90)
    except Exception:
        pass
    port = json.load(open(os.path.join(BASE, "windows.json"), encoding="utf-8"))["naver_main"]["port"]
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2)
    except Exception:
        os.system(f'cmd /c "{os.path.join(BASE, "2_open_window.bat")}"')
        time.sleep(8)
    new = not os.path.exists(CSV)
    w = csv.writer(open(CSV, "a", newline="", encoding="utf-8-sig"))
    if new:
        w.writerow(["확인일", "올린지(일)", "게시판", "키워드", "제목", "통합검색_카페글순위", "카페탭_순위", "글주소"])
    with sync_playwright() as pw:
        br = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        page = br.contexts[0].new_page()
        try:
            for p in todo:
                q = urllib.parse.quote(p["keyword"])
                page.goto(f"https://search.naver.com/search.naver?query={q}", wait_until="domcontentloaded")
                time.sleep(3)
                r1 = find_rank(cafe_links(page), slug, p.get("article_id"), p.get("title"))
                r2 = 0
                for start in (1, 11, 21):
                    page.goto(f"https://search.naver.com/search.naver?where=article&query={q}&start={start}",
                              wait_until="domcontentloaded")
                    time.sleep(3)
                    r = find_rank(cafe_links(page), slug, p.get("article_id"), p.get("title"))
                    if r:
                        r2 = r + start - 1
                        break
                w.writerow([today.isoformat(), p["day"], p.get("board"), p["keyword"], p.get("title"),
                            r1 or "-", r2 or "-", p.get("url")])
                print(f"{p['keyword']} [{p.get('board')}] 통합 {r1 or '-'} / 카페탭 {r2 or '-'}")
                time.sleep(5)
        finally:
            page.close()
    summarize()


def summarize():
    if not os.path.exists(CSV):
        return
    rows = list(csv.DictReader(open(CSV, encoding="utf-8-sig")))
    lines = ["게시판별 노출 비교 (" + datetime.now().strftime("%Y-%m-%d %H:%M") + ")", ""]
    for d in CHECK_DAYS:
        sub = [r for r in rows if r["올린지(일)"] == str(d)]
        if not sub:
            continue
        lines.append(f"[올린 지 {d}일째]")
        boards = sorted({r["게시판"] for r in sub})
        for b in boards:
            rs = [r for r in sub if r["게시판"] == b]
            top = sum(1 for r in rs if r["통합검색_카페글순위"] != "-")
            tab = [int(r["카페탭_순위"]) for r in rs if r["카페탭_순위"] != "-"]
            tab10 = sum(1 for t in tab if t <= 10)
            avg = f"{sum(tab)/len(tab):.1f}위" if tab else "-"
            lines.append(f"  {b}: 글 {len(rs)}개 | 통합검색 노출 {top}개 | 카페탭 10위 안 {tab10}개 | 카페탭 평균 {avg}")
        lines.append("")
    open(SUMMARY, "w", encoding="utf-8").write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
