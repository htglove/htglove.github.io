# -*- coding: utf-8 -*-
"""블로그 상위 글 수집(blog_top_posts.py)을 시크릿 모드 검색으로 바꾸는 자동 패치 (한 번만)
- 로그인된 전용 창 대신, 같은 크롬 안의 '새 시크릿 컨텍스트'(쿠키·로그인·기록 없음)에서 네이버를 검색하게 함
- 원본은 C:\\autowin\\_backup\\blog_top_posts_시크릿전.py 로 보관. 패턴이 예상과 다르면 고치지 않고 기록만 남김
"""
import os, re, shutil, time, py_compile

BASE = r"C:\autowin"
TARGET = os.path.join(BASE, "blog_top_posts.py")
FLAG = os.path.join(BASE, "_incognito_patched.txt")
BACKUP_DIR = os.path.join(BASE, "_backup")
MARK = "# 시크릿 모드 자동 패치"


def run(log=print):
    if not os.path.exists(TARGET):
        return
    src = open(TARGET, encoding="utf-8", errors="ignore").read()
    if MARK in src or "new_context(" in src:
        if not os.path.exists(FLAG):
            open(FLAG, "w", encoding="utf-8").write("이미 시크릿 모드")
        return
    if os.path.exists(FLAG) and open(FLAG, encoding="utf-8").read().startswith("실패"):
        return  # 한 번 실패하면 반복 시도하지 않음
    new = src
    # 1) br.contexts[0].new_page()  →  br.new_context().new_page()
    new, n1 = re.subn(r"(\w+)\.contexts\[0\]\.new_page\(\)", r"\1.new_context().new_page()  " + MARK, new)
    # 2) ctx = br.contexts[0]  →  ctx = br.new_context()   (ctx.pages 를 쓰지 않을 때만)
    m = re.findall(r"^(\s*)(\w+)\s*=\s*(\w+)\.contexts\[0\]\s*$", new, flags=re.M)
    n2 = 0
    if len(m) == 1:
        ind, ctx, br = m[0]
        if not re.search(rf"\b{ctx}\.pages\b", new):
            new = re.sub(rf"^{re.escape(ind)}{ctx}\s*=\s*{br}\.contexts\[0\]\s*$",
                         f"{ind}{ctx} = {br}.new_context()  {MARK}", new, count=1, flags=re.M)
            n2 = 1
    if n1 + n2 == 0:
        open(FLAG, "w", encoding="utf-8").write("실패: blog_top_posts.py 에서 바꿀 부분(contexts[0])을 못 찾음 — 직접 수정 필요\n")
        log("시크릿 모드 패치 못 함: blog_top_posts.py 구조가 예상과 다름 (직접 수정 필요)")
        return
    os.makedirs(BACKUP_DIR, exist_ok=True)
    bak = os.path.join(BACKUP_DIR, "blog_top_posts_시크릿전.py")
    shutil.copy2(TARGET, bak)
    tmp = TARGET + ".new"
    open(tmp, "w", encoding="utf-8").write(new)
    try:
        py_compile.compile(tmp, doraise=True)
    except Exception as e:
        os.remove(tmp)
        open(FLAG, "w", encoding="utf-8").write(f"실패: 고친 파일 검사 오류 {e}\n")
        log("시크릿 모드 패치 취소(검사 오류) — 원본 그대로")
        return
    os.replace(tmp, TARGET)
    open(FLAG, "w", encoding="utf-8").write(time.strftime("%Y-%m-%d %H:%M") + f" 완료 ({n1 + n2}곳). 원본: {bak}\n")
    log(f"블로그 상위 글 수집을 시크릿 모드로 변경 ({n1 + n2}곳, 원본 _backup 에 보관)")


if __name__ == "__main__":
    run()
