"""截图 SvelteKit 欢迎页"""
import time, subprocess
for name, w, h in [("1280x800", 1280, 800), ("375x812", 375, 812)]:
    out = f"/tmp/v2_welcome_{name}.png"
    cmd = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless=new", "--disable-gpu", "--no-sandbox",
        f"--window-size={w},{h}",
        "--virtual-time-budget=8000",
        f"--screenshot={out}",
        "http://localhost:5173/"
    ]
    subprocess.run(cmd, capture_output=True, timeout=20)
    print(f"{name}: done")
