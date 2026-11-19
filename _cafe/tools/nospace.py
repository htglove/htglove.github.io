# -*- coding: utf-8 -*-
"""모델명 띄어쓰기 붙이기 (사용자 규칙: 갤럭시 S26 → 갤럭시s26, 아이폰 17 → 아이폰17)
  python3 _cafe/tools/nospace.py _cafe/posts/<폴더> [...]   → post.json 의 keyword·title·body 문장을 고침
  index.json 의 같은 폴더 keyword 도 함께 고침"""
import json, os, re, sys
PAT = re.compile(r"(갤럭시|아이폰)\s*((?:[A-Za-z]\s*)?(?:플립|폴드)?\s*\d+[A-Za-z]?(?:\s*(?:울트라|플러스|프로\s*맥스|프로맥스|프로|엣지|FE|\+))?)")


def fix(s):
    s = PAT.sub(lambda m: m.group(1) + re.sub(r"\s+", "", m.group(2)).lower(), s)
    return s.replace("아이폰 에어", "아이폰에어").replace("갤럭시 Z", "갤럭시z")


def main(folders):
    idx_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "index.json")
    idx = json.load(open(idx_path, encoding="utf-8"))
    for d in folders:
        p = os.path.join(d, "post.json")
        j = json.load(open(p, encoding="utf-8"))
        j["keyword"] = fix(j["keyword"])
        j["title"] = fix(j["title"])
        j["body"] = [fix(x) if isinstance(x, str) else x for x in j["body"]]
        j["tags"] = [t.replace(" ", "").lower() if re.search(r"(갤럭시|아이폰)", t) else t for t in j.get("tags", [])]
        json.dump(j, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        name = os.path.basename(os.path.normpath(d))
        for x in idx["posts"]:
            if x["folder"] == name:
                x["keyword"] = j["keyword"]
                if x.get("model"):
                    x["model"] = fix(x["model"])
        print(name, "→", j["keyword"], "|", j["title"])
    json.dump(idx, open(idx_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main(sys.argv[1:])
