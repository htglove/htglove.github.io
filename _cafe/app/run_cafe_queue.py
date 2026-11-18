# -*- coding: utf-8 -*-
"""카페 글 매일 자동 실행 (cafe_config.json 의 시간대·개수 사용)
cafe_posts 안의 폴더를 이름 순서로, 아직 안 올린 것부터 하나씩 올립니다.
'_' 로 시작, '업로드완료.txt' 또는 '보류.txt' 가 있는 폴더는 건너뜀.
"""
import json, os, random, subprocess, sys, time
sys.path.insert(0, r"C:\autowin")
BASE = r"C:\autowin"
POSTS = os.path.join(BASE, "cafe_posts")
LOG = os.path.join(BASE, "cafe_log.txt")


def log(msg):
    line = time.strftime("%Y-%m-%d %H:%M ") + msg
    print(line)
    open(LOG, "a", encoding="utf-8").write(line + "\n")


def minutes(hhmm):
    h, m = map(int, hhmm.split(":"))
    return h * 60 + m


def pick_times(win, n, gap):
    if n <= 0:
        return []
    if win < gap * (n - 1):
        gap = win // max(n - 1, 1)
    free = max(win - gap * (n - 1), 0)
    base = sorted(random.randint(0, free) for _ in range(n))
    return [b + gap * i for i, b in enumerate(base)]


def next_job():
    if not os.path.isdir(POSTS):
        return None
    for d in sorted(os.listdir(POSTS)):
        p = os.path.join(POSTS, d)
        if (os.path.isdir(p) and not d.startswith("_")
                and os.path.exists(os.path.join(p, "post.json"))
                and not os.path.exists(os.path.join(p, "업로드완료.txt"))
                and not os.path.exists(os.path.join(p, "보류.txt"))
                and not os.path.exists(os.path.join(p, "_실패.txt"))):
            return d
    return None


def pick_board(cfg):
    """올린 글이 가장 적은 게시판부터 (게시판별 비교 시험용으로 고르게 돌림)"""
    boards = cfg.get("boards") or []
    if not boards:
        return ""
    cnt = {b: 0 for b in boards}
    for d in os.listdir(POSTS):
        f = os.path.join(POSTS, d, "업로드완료.txt")
        if os.path.exists(f):
            try:
                b = json.load(open(f, encoding="utf-8")).get("board")
                if b in cnt:
                    cnt[b] += 1
            except Exception:
                pass
    low = min(cnt.values())
    return random.choice([b for b in boards if cnt[b] == low])


BUSY = ("post_blog.py", "upload_clip.py", "make_clip.py", "make_voice_clip.py", "blog_stats.py", "keyword_research.py")


def busy():
    """블로그·클립 프로그램이 크롬창을 쓰는 중이면 True"""
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command",
                              "Get-CimInstance Win32_Process | Select-Object -ExpandProperty CommandLine"],
                             capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=60).stdout
        return any(b in out for b in BUSY)
    except Exception:
        return False


def wait_free(max_min=120):
    t0 = time.time()
    while busy() and time.time() - t0 < max_min * 60:
        log("다른 자동 작업(블로그·클립) 실행 중 → 3분 뒤 다시 확인")
        time.sleep(180)


def open_window():
    """전용 창이 없으면 띄움 (PC마다 이름이 달라서 둘 다 확인)"""
    import urllib.request
    try:
        urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=2)
        return
    except Exception:
        pass
    for b in ("2_open_window.bat", "2_네이버창_열기.bat"):
        p = os.path.join(BASE, b)
        if os.path.exists(p):
            subprocess.run(["cmd", "/c", p])
            time.sleep(8)
            return


def post_one(cfg):
    name = next_job()
    if name:
        wait_free()
    if not name:
        log("올릴 카페 글이 없습니다 (cafe_posts 비어 있음)")
        return False
    open_window()
    p = json.load(open(os.path.join(POSTS, name, "post.json"), encoding="utf-8"))
    board = p.get("board") or pick_board(cfg)
    log(f"시작: {name} -> 게시판 '{board}'")
    r = subprocess.run([sys.executable, os.path.join(BASE, "post_cafe.py"), os.path.join(POSTS, name), "--auto", "--board", board])
    if r.returncode:
        log(f"실패: {name} -> cafe_posts\\{name}\\_log 확인")
        open(os.path.join(POSTS, name, "_실패.txt"), "w", encoding="utf-8").write(str(r.returncode))
        return False   # 실패하면 그날은 멈춤 (같은 오류 반복 방지)
    log(f"완료: {name}")
    return True


def fix_schedule(cfg):
    """작업 스케줄러 시작 시각이 설정과 다르면 맞춤 (CafeAuto=시작 시각, CafeRank=순위 확인 시각)"""
    for tn, st in (("CafeAuto", cfg["window_start"]), ("CafeRank", cfg.get("rank_check_time", "12:10"))):
        try:
            xml = subprocess.run(["schtasks", "/query", "/tn", tn, "/xml"], capture_output=True,
                                 text=True, encoding="utf-16", errors="ignore").stdout
            if not xml:
                xml = subprocess.run(["schtasks", "/query", "/tn", tn, "/xml"], capture_output=True,
                                     text=True, encoding="utf-8", errors="ignore").stdout
            if f"T{st}:00" in xml or not xml:
                continue
            r = subprocess.run(["schtasks", "/change", "/tn", tn, "/st", st], capture_output=True, text=True)
            log(f"예약 시각 변경: {tn} -> {st} ({'성공' if r.returncode == 0 else '실패: 12_cafe_schedule.bat 를 관리자 권한으로 다시 실행해 주세요'})")
        except Exception as e:
            log(f"예약 시각 확인 실패: {e}")


def main():
    cfg = json.load(open(os.path.join(BASE, "cafe_config.json"), encoding="utf-8"))
    try:
        import cafe_sync
        upd = cafe_sync.update_app()
        if upd:
            log(f"프로그램 {upd}개 업데이트됨 → 새 버전으로 다시 시작")
            sys.exit(subprocess.run([sys.executable] + sys.argv).returncode)
        got = cafe_sync.sync()
        log(f"새 글 {got}개 받음")
    except Exception as e:
        log(f"새 글 받기 실패: {e}")
    cfg = json.load(open(os.path.join(BASE, "cafe_config.json"), encoding="utf-8"))
    fix_schedule(cfg)
    from datetime import datetime, timedelta
    now = datetime.now()
    ws = datetime.combine(now.date(), datetime.strptime(cfg["window_start"], "%H:%M").time())
    we = datetime.combine(now.date(), datetime.strptime(cfg["window_end"], "%H:%M").time())
    if we <= ws:
        we += timedelta(days=1)
    if now < ws:
        base, win = ws, (we - ws).seconds // 60
    elif now < we:
        base, win = now, max(int((we - now).total_seconds() // 60), 1)
    else:   # 시간대가 지났으면(예: 첫날) 지금부터 같은 길이로 진행
        base, win = now, (we - ws).seconds // 60
    start = base.timestamp()
    plan = pick_times(win, int(cfg.get("count", 3)), int(cfg.get("min_gap_minutes", 45)))
    log("오늘 카페 글 시각: " + ", ".join(time.strftime("%H:%M", time.localtime(start + m * 60)) for m in plan))
    for m in plan:
        while time.time() < start + m * 60:
            time.sleep(min(60, max(1, start + m * 60 - time.time())))
        if not post_one(cfg):
            break


if __name__ == "__main__":
    main()
