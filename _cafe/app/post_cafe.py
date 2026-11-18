# -*- coding: utf-8 -*-
"""
네이버 카페 자동 글쓰기 (전용 크롬 창(9222)에 연결, 클립과 같은 창 사용)
  py post_cafe.py <글폴더>          -> 확인 모드: 게시판·제목·본문·태그까지 넣고 '등록'은 사람이 누름
  py post_cafe.py <글폴더> --auto   -> 자동 모드: '등록'까지 누름
  --board 게시판이름  -> 이 게시판에 올림 (없으면 post.json 의 board, 그다음 cafe_config.json boards 첫 번째)
설정: C:\\autowin\\cafe_config.json (카페 주소, 게시판 이름)
글폴더 안 post.json: {"title": "...", "body": ["문단1", "문단2", ...], "tags": ["..", ".."]}
단계마다 글폴더\\_log 에 화면 사진과 버튼 목록을 남깁니다.
"""
import json, os, re, sys, time, urllib.request
from playwright.sync_api import sync_playwright

BASE = r"C:\autowin"
ACCOUNT = "naver_main"


def load_json(p):
    return json.load(open(p, encoding="utf-8"))


def window_alive(port):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2)
        return True
    except Exception:
        return False


class Log:
    def __init__(self, job):
        self.dir = os.path.join(job, "_log")
        os.makedirs(self.dir, exist_ok=True)
        for f in os.listdir(self.dir):
            try:
                os.remove(os.path.join(self.dir, f))
            except Exception:
                pass
        self.n = 0
        self.txt = open(os.path.join(self.dir, "log.txt"), "w", encoding="utf-8")

    def say(self, msg):
        print(msg)
        self.txt.write(msg + "\n")
        self.txt.flush()

    def snap(self, page, name):
        self.n += 1
        base = os.path.join(self.dir, f"step{self.n:02d}_{name}")
        try:
            page.screenshot(path=base + ".png")
        except Exception as e:
            self.say(f"  (사진 실패: {e})")
        try:
            lines = []
            for fr in page.frames:
                try:
                    lines.append(fr.evaluate("""() => {
                      const out = ['URL: ' + location.href];
                      document.querySelectorAll('button, a, [role=button], [role=option], li, input, textarea, [contenteditable=true]')
                        .forEach(e => {
                          const r = e.getBoundingClientRect();
                          if (r.width === 0 && r.height === 0) return;
                          const t = (e.innerText || e.value || e.placeholder || e.getAttribute('aria-label') || '').trim().replace(/\\s+/g,' ').slice(0,60);
                          if (!t) return;
                          out.push(`${e.tagName.toLowerCase()} | ${t} | class=${(e.className||'').toString().slice(0,50)}`);
                        });
                      return out.join('\\n');
                    }"""))
                except Exception:
                    pass
            open(base + ".txt", "w", encoding="utf-8").write("\n\n".join(lines))
        except Exception as e:
            self.say(f"  (목록 실패: {e})")


def visible(loc):
    try:
        for i in range(loc.count()):
            el = loc.nth(i)
            if el.is_visible():
                return el
    except Exception:
        pass
    return None


def find(page, selectors=(), texts=(), exact=False, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        for fr in page.frames:
            for s in selectors:
                el = visible(fr.locator(s))
                if el:
                    return el
            for t in texts:
                el = visible(fr.get_by_text(t, exact=exact))
                if el:
                    return el
        time.sleep(0.5)
    return None


def upload_image(page, path, log):
    """스마트에디터 '사진' 버튼으로 이미지 1장 올리기. 성공하면 True"""
    before = 0
    for fr in page.frames:
        try:
            before += fr.locator(".se-content img, .se-component.se-image").count()
        except Exception:
            pass
    btn = find(page, selectors=["button.se-image-toolbar-button", "button[data-name='image']",
                                "button[data-log='dot.img']"], texts=["사진"], exact=True, timeout=5)
    if not btn:
        log.say("   (사진 버튼을 못 찾음)")
        return False
    with page.expect_file_chooser(timeout=10000) as fc:
        btn.click()
    fc.value.set_files(path)
    end = time.time() + 40
    while time.time() < end:
        now = 0
        for fr in page.frames:
            try:
                now += fr.locator(".se-content img, .se-component.se-image").count()
            except Exception:
                pass
        if now > before:
            time.sleep(2)
            return True
        time.sleep(1)
    log.say("   (사진 올리기 시간 초과)")
    return False


def caret_to_end(page):
    """본문 맨 끝 문단 끝으로 커서 이동 (사진 뒤에 글을 이어 쓰기 위해)"""
    for fr in page.frames:
        try:
            paras = fr.locator(".se-content .se-text-paragraph")
            n = paras.count()
            if not n:
                continue
            last = paras.nth(n - 1)
            comps = fr.locator(".se-content .se-component")
            last_comp_is_image = False
            if comps.count():
                cls = comps.nth(comps.count() - 1).get_attribute("class") or ""
                last_comp_is_image = "se-image" in cls
            if last_comp_is_image:
                comps.nth(comps.count() - 1).click()
                time.sleep(0.4)
                page.keyboard.press("Enter")
            else:
                last.click()
                page.keyboard.press("End")
            time.sleep(0.4)
            return
        except Exception:
            continue


def club_id(page):
    pats = [r"/cafes/(\d+)", r"clubid=(\d+)", r"g_sClubId\s*=\s*[\"'](\d+)", r"\"cafeId\"\s*:\s*(\d+)", r"clubId[\"']?\s*[:=]\s*[\"']?(\d+)"]
    srcs = [page.url]
    for fr in page.frames:
        try:
            srcs.append(fr.url)
            srcs.append(fr.content())
        except Exception:
            pass
    for s in srcs:
        for p in pats:
            m = re.search(p, s, re.I)
            if m:
                return m.group(1)
    return None


def main():
    if len(sys.argv) < 2:
        raise SystemExit("사용법: py post_cafe.py <글폴더> [--auto]")
    job = os.path.abspath(sys.argv[1])
    auto = "--auto" in sys.argv
    cfg = load_json(os.path.join(BASE, "cafe_config.json"))
    post = load_json(os.path.join(job, "post.json"))
    port = load_json(os.path.join(BASE, "windows.json"))[ACCOUNT]["port"]
    if not window_alive(port):
        raise SystemExit(f"[오류] 전용 창(번호 {port})이 안 떠 있습니다. 2_open_window.bat 를 먼저 실행해 주세요.")

    log = Log(job)
    with sync_playwright() as pw:
        br = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        ctx = br.contexts[0]
        page = ctx.new_page()
        try:
            log.say("[프로그램 v3 · 사진 지원]")
            log.say("1) 카페 열기: " + cfg["cafe_url"])
            page.goto(cfg["cafe_url"], wait_until="domcontentloaded")
            time.sleep(4)
            log.snap(page, "cafe_home")
            if find(page, texts=["로그인"], exact=True, timeout=1) and not find(page, texts=["로그아웃", "내정보"], timeout=1):
                log.say("[오류] 전용 창 네이버 로그인이 풀렸습니다. 전용 창에서 다시 로그인해 주세요.")
                return 2

            cid = club_id(page)
            log.say(f"   카페 번호: {cid}")
            if cid:
                page.goto(f"https://cafe.naver.com/ca-fe/cafes/{cid}/articles/write?boardType=L", wait_until="domcontentloaded")
            else:
                btn = find(page, texts=["카페 글쓰기", "글쓰기"], timeout=8)
                if not btn:
                    if find(page, texts=["카페 가입하기", "가입하기"], timeout=1):
                        log.say("[오류] 전용 창 계정이 이 카페 회원이 아닙니다. 가입 후 다시 실행해 주세요.")
                    else:
                        log.say("[오류] 글쓰기 버튼을 못 찾았습니다. _log 폴더를 Claude에게 보여 주세요.")
                    return 2
                try:
                    with ctx.expect_page(timeout=8000) as np:
                        btn.click()
                    page.close()
                    page = np.value
                except Exception:
                    pass
            time.sleep(5)
            log.say("2) 글쓰기 화면: " + page.url)
            log.snap(page, "write")
            if find(page, texts=["카페 가입하기", "가입 후", "글쓰기 권한"], timeout=1):
                log.say("[오류] 이 계정으로는 글쓰기 권한이 없습니다(미가입 또는 등급 부족).")
                return 2

            # 3) 게시판 선택
            board = ""
            if "--board" in sys.argv:
                board = sys.argv[sys.argv.index("--board") + 1]
            board = (board or post.get("board") or (cfg.get("boards") or [""])[0] or "").strip()
            sel = find(page, texts=["게시판을 선택해 주세요", "게시판을 선택해주세요", "게시판 선택"], timeout=10)
            if sel:
                sel.click()
                time.sleep(1.5)
                log.snap(page, "board_list")
            if not board:
                log.say("[멈춤] cafe_config.json 의 boards(게시판 이름 목록)가 비어 있습니다. "
                        "_log 의 board_list 사진/목록을 Claude에게 보여 주세요.")
                return 3
            opt = find(page, texts=[board], exact=True, timeout=5) or find(page, texts=[board], timeout=3)
            if not opt:
                log.say(f"[오류] 게시판 '{board}' 을(를) 목록에서 못 찾았습니다.")
                return 2
            opt.click()
            log.say(f"3) 게시판 선택: {board}")
            time.sleep(1)

            # 4) 제목
            t = find(page, selectors=["textarea[placeholder*='제목']", "input[placeholder*='제목']", "textarea.textarea_input"], timeout=10)
            if not t:
                log.say("[오류] 제목 칸을 못 찾았습니다.")
                log.snap(page, "no_title")
                return 2
            t.click()
            t.fill(post["title"])
            log.say("4) 제목: " + post["title"])

            # 5) 본문
            ed = find(page, selectors=[".se-content", ".se-component-content", "[contenteditable=true]"],
                      texts=["내용을 입력하세요"], timeout=10)
            if not ed:
                log.say("[오류] 본문 칸을 못 찾았습니다.")
                log.snap(page, "no_body")
                return 2
            ed.click()
            time.sleep(0.5)
            items = post["body"]
            n_img = 0
            for i, para in enumerate(items):
                if isinstance(para, dict) and para.get("image"):
                    img = os.path.join(job, para["image"])
                    if os.path.exists(img):
                        try:
                            if upload_image(page, img, log):
                                n_img += 1
                                log.snap(page, f"img{n_img}")
                        except Exception as e:
                            log.say(f"   사진 실패 (건너뜀): {str(e).splitlines()[0]}")
                        caret_to_end(page)
                    continue
                for j, line in enumerate(para.split("\n")):
                    if j:
                        page.keyboard.press("Shift+Enter")
                    page.keyboard.insert_text(line)
                    time.sleep(0.2)
                page.keyboard.press("Enter")
                if i < len(items) - 1:
                    page.keyboard.press("Enter")
                time.sleep(0.3)
            log.say(f"   사진 {n_img}장 올림")
            log.say(f"5) 본문 {sum(1 for x in items if isinstance(x, str))}문단 입력")

            # 6) 태그 (띄어쓰기 없이, 매번 칸을 새로 찾음 / 실패해도 계속)
            tags = [t.lstrip("#").replace(" ", "") for t in post.get("tags", [])][:10]
            done_tags = []
            for tg in tags:
                try:
                    ti = find(page, selectors=["input[placeholder*='태그']", "input.tag_input", "[class*='tag'] input"], timeout=4)
                    if not ti:
                        log.say("6) 태그 칸 없음 (건너뜀)")
                        break
                    ti.evaluate("e => { e.scrollIntoView({block: 'center'}); e.focus(); }", timeout=5000)
                    time.sleep(0.3)
                    page.keyboard.type(tg, delay=40)
                    page.keyboard.press("Enter")
                    time.sleep(0.6)
                    done_tags.append(tg)
                except Exception as e:
                    log.say(f"   태그 '{tg}' 실패 (건너뜀): {str(e).splitlines()[0]}")
            log.say("6) 태그: " + ", ".join(done_tags))
            page.keyboard.press("Escape")
            log.snap(page, "filled")

            if not auto:
                log.say("[확인 모드] 내용을 확인하고 직접 '등록'을 눌러 주세요. 창은 열어 둡니다.")
                return 0

            reg = find(page, selectors=["a.BaseButton:has-text('등록')", "button:has-text('등록')"], texts=["등록"], exact=True, timeout=8)
            if not reg:
                log.say("[오류] 등록 버튼을 못 찾았습니다.")
                return 2
            reg.click()
            time.sleep(6)
            log.snap(page, "after_submit")
            if "write" in page.url:
                log.say("[오류] 등록 후에도 글쓰기 화면입니다. 사진을 확인해 주세요.")
                return 2
            log.say("7) 등록 완료: " + page.url)
            from urllib.parse import unquote
            u = unquote(unquote(page.url))
            m = re.search(r"articleid=(\d+)", u, re.I) or re.search(r"articles/(\d+)", u) or re.search(r"/(\d+)(?:\?|$)", u)
            done = {"url": page.url, "article_id": m.group(1) if m else "", "board": board,
                    "keyword": post.get("keyword") or (post.get("tags") or [""])[0],
                    "title": post["title"], "posted_at": time.strftime("%Y-%m-%d %H:%M")}
            json.dump(done, open(os.path.join(job, "업로드완료.txt"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            page.close()
            return 0
        except Exception as e:
            log.say(f"[오류] {e}")
            try:
                log.snap(page, "error")
            except Exception:
                pass
            return 2


if __name__ == "__main__":
    sys.exit(main() or 0)
