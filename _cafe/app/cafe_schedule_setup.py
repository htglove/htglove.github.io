# -*- coding: utf-8 -*-
"""카페 예약 작업 등록 (관리자 권한 필요: 12_cafe_schedule.bat 를 오른쪽 클릭 → 관리자 권한으로 실행)
- 파이썬 전체 경로로 등록 (작업 스케줄러가 py 를 못 찾는 문제 방지)
- 절전 모드 해제 + 놓친 작업 바로 실행 설정 포함"""
import json, os, subprocess, sys
BASE = r"C:\autowin"
try:
    sys.path.insert(0, BASE)
    import cafe_sync
    cafe_sync.update_app()
except Exception as e:
    print("업데이트 확인 실패:", e)
cfg = json.load(open(os.path.join(BASE, "cafe_config.json"), encoding="utf-8"))
py = sys.executable
if py.lower().endswith("pythonw.exe"):
    py = py[:-11] + "python.exe"
print("파이썬 위치:", py)


def register(name, script, at):
    ps = f"""
$a = New-ScheduledTaskAction -Execute '{py}' -Argument '"{os.path.join(BASE, script)}"' -WorkingDirectory '{BASE}'
$t = New-ScheduledTaskTrigger -Daily -At '{at}'
$s = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 6)
$p = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\\$env:USERNAME" -LogonType Interactive -RunLevel Highest
Register-ScheduledTask -TaskName '{name}' -Action $a -Trigger $t -Settings $s -Principal $p -Force | Out-Null
"""
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                       capture_output=True, text=True, encoding="utf-8", errors="ignore")
    print(f" {name}: {'성공' if r.returncode == 0 else '실패'}")
    if r.returncode:
        print(r.stderr[:500])
    return r.returncode == 0


ok1 = register("CafeAuto", "run_cafe_queue.py", cfg["window_start"])
ok2 = register("CafeRank", "cafe_rank_check.py", cfg.get("rank_check_time", "12:10"))
if ok1 and ok2:
    open(os.path.join(BASE, "_wake_set.txt"), "w").write("ok")
    print(f"\n ===== SCHEDULE OK : 매일 {cfg['window_start']} ~ {cfg['window_end']} 사이 랜덤으로 {cfg['count']}개 =====")
    print(f" 노출 순위 확인: 매일 {cfg.get('rank_check_time', '12:10')}")
    print(" 절전 모드 해제 · 놓친 작업 바로 실행: 켜짐")
else:
    print("\n SCHEDULE FAILED - 이 화면을 Claude에게 보여 주세요")
