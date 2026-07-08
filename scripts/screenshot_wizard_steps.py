"""截图 wizard 各步骤 - 用 URL query"""
import time, subprocess
for step, name in [(0, "step1"), (1, "step2"), (2, "step3"), (3, "step4"), (4, "step5")]:
    out = f"/tmp/v2_wizard_{name}.png"
    cmd = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless=new", "--disable-gpu", "--no-sandbox",
        "--window-size=1280,900",
        "--virtual-time-budget=15000",
        f"--screenshot={out}",
        f"http://localhost:5174/wizard/?step={step}"
    ]
    subprocess.run(cmd, capture_output=True, timeout=20)
    print(f"step {step+1}: {out}")
    time.sleep(2)
