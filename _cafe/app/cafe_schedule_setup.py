# -*- coding: utf-8 -*-
import json, subprocess
cfg = json.load(open(r"C:\autowin\cafe_config.json", encoding="utf-8"))
st = cfg["window_start"]
r = subprocess.run(["schtasks", "/create", "/tn", "CafeAuto", "/tr", r'py "C:\autowin\run_cafe_queue.py"',
                    "/sc", "daily", "/st", st, "/rl", "HIGHEST", "/f"])
r2 = subprocess.run(["schtasks", "/create", "/tn", "CafeRank", "/tr", r'py "C:\autowin\cafe_rank_check.py"',
                     "/sc", "daily", "/st", cfg.get("rank_check_time", "19:20"), "/rl", "HIGHEST", "/f"])
if r.returncode == 0 and r2.returncode == 0:
    print(f"\n ===== SCHEDULE OK : 매일 {st} ~ {cfg['window_end']} 사이 랜덤으로 {cfg['count']}개 =====")
    print(f" 노출 순위 확인: 매일 {cfg.get('rank_check_time', '19:20')} (결과: C:\\autowin\\cafe_rank.csv, cafe_rank_요약.txt)")
    print(" 작업 스케줄러 > CafeAuto, CafeRank > 조건 탭에서 '작업을 실행하기 위해 절전 모드 해제'도 체크해 주세요.")
else:
    print(" SCHEDULE FAILED - 이 화면을 Claude에게 보여 주세요")
