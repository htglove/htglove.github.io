# -*- coding: utf-8 -*-
"""새 카페 글 받아오기: GitHub 대기열(_cafe/index.json)에 있는데 PC에 없는 글 폴더를 내려받습니다.
run_cafe_queue.py 가 시작할 때 자동으로 실행합니다. (직접 실행: py cafe_sync.py)"""
import json, os, time, urllib.parse, urllib.request
BASE = r"C:\autowin"
POSTS = os.path.join(BASE, "cafe_posts")
RAW = "https://raw.githubusercontent.com/htglove/htglove.github.io/main/_cafe/"


def get(url):
    url = url + ("&" if "?" in url else "?") + "t=" + str(int(time.time()))
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read()


APP_FILES_DIR = "app/"


def update_app():
    """GitHub _cafe/app 의 프로그램 파일이 바뀌었으면 C:\\autowin 에 자동으로 교체"""
    import hashlib
    try:
        man = json.loads(get(RAW + APP_FILES_DIR + "manifest.json").decode("utf-8"))
    except Exception as e:
        print("[업데이트 확인 실패]", e)
        return 0
    n = 0
    for name, sha in man.get("files", {}).items():
        if "/" in name or "\\" in name or ".." in name or not (name.endswith(".py") or name == "cafe_config.json"):
            continue
        local = os.path.join(BASE, name)
        try:
            cur = hashlib.sha256(open(local, "rb").read()).hexdigest() if os.path.exists(local) else ""
        except Exception:
            cur = ""
        if cur == sha:
            continue
        try:
            data = get(RAW + APP_FILES_DIR + urllib.parse.quote(name))
            if hashlib.sha256(data).hexdigest() != sha:
                print("[업데이트 건너뜀] 내용 불일치:", name)
                continue
            open(local, "wb").write(data)
            n += 1
            print("업데이트:", name)
        except Exception as e:
            print("[업데이트 실패]", name, e)
    return n


def sync():
    try:
        idx = json.loads(get(RAW + "index.json").decode("utf-8"))
    except Exception as e:
        print("[받기 실패] 목록:", e)
        return 0
    os.makedirs(POSTS, exist_ok=True)
    n = 0
    for p in idx.get("posts", []):
        d = os.path.join(POSTS, p["folder"])
        if os.path.exists(os.path.join(d, "post.json")):
            continue
        try:
            os.makedirs(d, exist_ok=True)
            for f in p.get("files", ["post.json"]):
                data = get(RAW + "posts/" + urllib.parse.quote(p["folder"]) + "/" + urllib.parse.quote(f))
                open(os.path.join(d, f), "wb").write(data)
            n += 1
            print("받음:", p["folder"])
        except Exception as e:
            print("[받기 실패]", p["folder"], e)
            try:
                os.remove(os.path.join(d, "post.json"))
            except Exception:
                pass
    return n


if __name__ == "__main__":
    print("프로그램 업데이트", update_app(), "개")
    print("새 글", sync(), "개")
