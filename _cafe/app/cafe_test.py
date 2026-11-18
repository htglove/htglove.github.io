# -*- coding: utf-8 -*-
"""카페 글쓰기 시험 실행: 아직 안 올린 첫 글을 '확인 모드'로 채웁니다 (등록은 직접)"""
import os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.dirname(os.path.abspath(__file__))
POSTS = os.path.join(BASE, "cafe_posts")
print("작업 폴더:", BASE)
if os.path.normcase(BASE) != os.path.normcase(r"C:\autowin"):
    print("[오류] 파일들이 C:\\autowin 바로 아래에 있어야 합니다. 지금 위치:", BASE)
    print("       이 폴더 안의 파일을 모두 C:\\autowin 으로 옮긴 뒤 다시 실행해 주세요.")
    sys.exit(1)
if not os.path.isdir(POSTS):
    print("[오류] cafe_posts 폴더가 없습니다:", POSTS)
    print("       압축을 풀 때 하위 폴더가 생겼는지 확인하고, 파일들을 C:\\autowin 바로 아래로 옮겨 주세요.")
    sys.exit(1)
try:
    import cafe_sync
    if cafe_sync.update_app():
        print("프로그램이 업데이트됐습니다. 새 버전으로 다시 실행합니다.")
        sys.exit(subprocess.run([sys.executable] + sys.argv).returncode)
    cafe_sync.sync()
except Exception as e:
    print("[업데이트·새 글 받기 실패]", e)
import run_cafe_queue as q
name = q.next_job()
if not name:
    print("[오류] 올릴 글이 없습니다.")
    sys.exit(1)
print("시험할 글:", name)
q.open_window()
args = [sys.executable, os.path.join(BASE, "post_cafe.py"), os.path.join(POSTS, name)]
if "--auto" in sys.argv:
    cfg = q.json.load(open(os.path.join(BASE, "cafe_config.json"), encoding="utf-8"))
    args += ["--auto", "--board", q.pick_board(cfg)]
    print("[자동 등록 모드] 등록까지 누르고 기록을 남깁니다.")
r = subprocess.run(args)
print("\n끝났습니다. (결과 코드", r.returncode, ") 기록:", os.path.join(POSTS, name, "_log"))
