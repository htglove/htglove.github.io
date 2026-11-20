# -*- coding: utf-8 -*-
"""직원 전달용 묶음 만들기: C:\\autowin 의 지금 쓰는 최종 프로그램(블로그·클립·카페 전부)을
바탕화면 autowin_전달_날짜.zip 하나로 묶습니다.  실행: py C:\\autowin\\make_handoff.py
빼는 것: 네이버 로그인 정보(크롬 프로필), 기록·로그, 이미 올린 글, 백업, 큰 영상, API 키로 보이는 파일.
같이 만드는 것: 00_포함목록.txt (프로그램별 설명), 00_필요한설치.txt (pip 설치 명령), 00_빠진파일.txt
"""
import ast, os, sys, time, zipfile

BASE = r"C:\autowin"
OUT = os.path.join(os.path.expanduser("~"), "Desktop", "autowin_전달_" + time.strftime("%Y%m%d") + ".zip")
MAX_MB = 50
RAW_GUIDE = "https://raw.githubusercontent.com/htglove/htglove.github.io/main/_cafe/app/00_%EC%84%A4%EB%AA%85%EC%84%9C.html"
SKIP_DIRS = {"_삭제대기", "__pycache__", ".git", "_log", "venv", ".venv"}
SKIP_EXT = {".log", ".mp4", ".mov", ".avi", ".mkv", ".tmp", ".pyc"}
SKIP_FILES = {"cafe_log.txt", "_wake_set.txt", "cafe_rank.csv", "cafe_rank_요약.txt"}
SECRET_WORDS = ("key", "token", "secret", "password", "passwd", "credential", ".env", "cookie", "비번", "비밀번호")
DONE_MARKS = ("업로드완료.txt", "_실패.txt", "보류.txt")


def is_chrome_profile(d):
    return any(os.path.exists(os.path.join(d, f)) for f in ("Local State", "First Run")) or \
        os.path.isdir(os.path.join(d, "Default", "Network"))


def first_doc(path):
    try:
        src = open(path, encoding="utf-8", errors="ignore").read()
        doc = ast.get_docstring(ast.parse(src)) or ""
        return doc.strip().splitlines()[0] if doc.strip() else ""
    except Exception:
        return ""


def bat_desc(path):
    for enc in ("utf-8", "cp949"):
        try:
            lines = open(path, encoding=enc).read().splitlines()
            break
        except Exception:
            lines = []
    for ln in lines:
        s = ln.strip()
        if s.lower().startswith(("rem ", "::")):
            return s.split(" ", 1)[-1].lstrip(":").strip()
    run = [ln.strip() for ln in lines if ".py" in ln]
    return ("실행: " + run[0]) if run else ""


def imports(path):
    try:
        tree = ast.parse(open(path, encoding="utf-8", errors="ignore").read())
    except Exception:
        return set()
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module and not n.level:
            out.add(n.module.split(".")[0])
    return out


PIP = {"PIL": "pillow", "cv2": "opencv-python", "yaml": "pyyaml", "bs4": "beautifulsoup4",
       "dotenv": "python-dotenv", "win32api": "pywin32", "win32con": "pywin32", "win32gui": "pywin32",
       "sklearn": "scikit-learn", "fitz": "pymupdf", "docx": "python-docx", "pptx": "python-pptx"}


def main():
    if not os.path.isdir(BASE):
        sys.exit("[오류] C:\\autowin 폴더가 없습니다.")
    keep, skipped, local_mods, pyfiles = [], [], set(), []
    for root, dirs, files in os.walk(BASE):
        rel_root = os.path.relpath(root, BASE)
        for d in list(dirs):
            full = os.path.join(root, d)
            if d in SKIP_DIRS or is_chrome_profile(full):
                dirs.remove(d)
                skipped.append((os.path.relpath(full, BASE) + "\\", "로그인정보·기록 폴더" if d not in SKIP_DIRS else "기록·임시"))
        # 이미 올린(또는 실패·보류) 카페 글 폴더는 통째로 뺌
        # 이미 올린(또는 실패·보류) 카페 글은 post.json 과 표시 파일만 넣음 → 새 PC가 같은 글을 다시 올리지 않게
        if os.path.basename(os.path.dirname(root)) == "cafe_posts" and any(m in files for m in DONE_MARKS):
            keep += [os.path.join(rel_root, f) for f in files if f == "post.json" or f in DONE_MARKS]
            dirs.clear()
            continue
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, BASE)
            low = f.lower()
            if f == os.path.basename(OUT) or low.endswith(".zip"):
                skipped.append((rel, "압축파일"))
            elif f in SKIP_FILES or os.path.splitext(low)[1] in SKIP_EXT or "이전본" in f or "_log" in rel.split(os.sep):
                skipped.append((rel, "기록·백업·영상"))
            elif any(w in low for w in SECRET_WORDS):
                skipped.append((rel, "API 키·비밀번호로 보임 → 따로 전달"))
            elif os.path.getsize(full) > MAX_MB * 1024 * 1024:
                skipped.append((rel, f"{MAX_MB}MB 넘음"))
            else:
                keep.append(rel)
                if low.endswith(".py"):
                    pyfiles.append(rel)
                    local_mods.add(os.path.splitext(f)[0])

    std = set(getattr(sys, "stdlib_module_names", ())) | {"__future__"}
    need = set()
    for rel in pyfiles:
        need |= imports(os.path.join(BASE, rel))
    need = sorted(PIP.get(m, m) for m in need - std - local_mods)

    lines = ["autowin 포함 목록 (" + time.strftime("%Y-%m-%d %H:%M") + ")", "", "[실행 파일 .bat]"]
    for rel in sorted(keep):
        if rel.lower().endswith(".bat"):
            lines.append(f"  {rel}  —  {bat_desc(os.path.join(BASE, rel))}")
    lines += ["", "[프로그램 .py]"]
    for rel in sorted(pyfiles):
        lines.append(f"  {rel}  —  {first_doc(os.path.join(BASE, rel))}")
    lines += ["", "[설정 .json]"] + [f"  {r}" for r in sorted(keep) if r.lower().endswith(".json") and os.sep not in r]
    listing = "\n".join(lines) + "\n"
    req = ("새 PC에서 명령 프롬프트(cmd)를 열고 아래 한 줄을 붙여 넣으세요.\n\n"
           "py -m pip install " + " ".join(need) + "\n\n"
           "playwright 가 들어 있으면 이어서 이것도 한 번:\npy -m playwright install chromium\n")
    miss = "넣지 않은 파일·폴더 (필요하면 따로 전달)\n\n" + "\n".join(f"  {r}  ({why})" for r, why in skipped) + "\n"

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in keep:
            z.write(os.path.join(BASE, rel), "autowin/" + rel.replace(os.sep, "/"))
        z.writestr("autowin/00_포함목록.txt", listing)
        z.writestr("autowin/00_필요한설치.txt", req)
        z.writestr("autowin/00_빠진파일.txt", miss)
        if "00_설명서.html" not in keep:
            try:
                import urllib.request, urllib.parse
                url = RAW_GUIDE + "?t=" + str(int(time.time()))
                z.writestr("autowin/00_설명서.html", urllib.request.urlopen(url, timeout=30).read())
            except Exception as e:
                print("[알림] 설명서를 GitHub에서 못 받았습니다:", e)
    print(f"\n완료: {OUT}")
    print(f"  넣은 파일 {len(keep)}개, 뺀 것 {len(skipped)}개 (00_빠진파일.txt 참고)")
    print(f"  필요한 설치: {' '.join(need) or '(없음)'}")
    secrets = [r for r, why in skipped if "API" in why]
    if secrets:
        print("\n[확인] 아래는 키·비밀번호로 보여 뺐습니다. 직원에게 필요하면 메신저 등으로 따로 주세요:")
        for r in secrets:
            print("   ", r)
    input("\n엔터를 누르면 닫힙니다.")


if __name__ == "__main__":
    main()
