import os
import time
import random
import requests
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

# ⚠️ THESE VALUES ARE SET IN GITHUB SECRETS — DO NOT WRITE THEM HERE
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PROXY_SERVER = os.getenv("PROXY_SERVER")  # e.g. "http://user:pass@host:port"

# ✅ Exact URLs & text from YOUR pages
BASE_URL = "https://icp.administracionelectronica.gob.es/icpplustieb/index"
PROVINCIA = "Barcelona"
OFICINA = "Cualquier oficina"
TRAMITE_TEXT = "POLICÍA-TOMA DE HUELLAS (EXPEDICIÓN DE TARJETA) INICIAL, RENOVACIÓN, DUPLICADO Y LEY 14/2013"

def send_telegram_alert(message):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            params={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"},
            timeout=15
        )
        print("✅ Telegram alert sent")
    except Exception as e:
        print(f"❌ Telegram error: {e}")

def check_appointments():
    results = {"found": False, "message": "", "error": None}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"]
        )

        ctx_options = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "locale": "es-ES",
            "timezone_id": "Europe/Madrid",
            "extra_http_headers": {"Accept-Language": "es-ES,es;q=0.9,en;q=0.8"},
        }
        if PROXY_SERVER:
            ctx_options["proxy"] = {"server": PROXY_SERVER}
            print("🌐 Proxy enabled")

        context = browser.new_context(**ctx_options)
        page = context.new_page()
        stealth_sync(page)  # 🕵️ Full anti-detection

        # STEP 1: Select Province
        print("📍 Step 1/3 — Province...")
        page.goto(BASE_URL, timeout=60000, wait_until="domcontentloaded")
        time.sleep(random.uniform(2, 4))
        page.select_option('select', has_text=PROVINCIA, timeout=5000)
        time.sleep(random.uniform(1, 2))
        page.click("input[type='submit'][value='Aceptar']", timeout=5000)
        page.wait_for_load_state("networkidle", timeout=30000)
        time.sleep(random.uniform(2, 3))

        # STEP 2: Select Office & Procedure
        print("🏢 Step 2/3 — Office & Procedure...")
        try:
            page.select_option('select', has_text=OFICINA, timeout=5000)
            time.sleep(random.uniform(1, 2))
        except: pass
        page.select_option('select', has_text=TRAMITE_TEXT, timeout=5000)
        time.sleep(random.uniform(1, 2))
        page.click("input[type='submit'][value='Aceptar']", timeout=5000)
        page.wait_for_load_state("networkidle", timeout=30000)
        time.sleep(random.uniform(3, 5))

        # STEP 3: Check for Appointments
        print("🔍 Step 3/3 — Checking availability...")
        content = page.content().lower()

        no_citas = ["no hay citas disponibles", "no existen citas", "agotado", "caducado"]
        hay_citas = ["seleccione cita", "seleccione fecha", "seleccione la hora", "citas disponibles"]

        if any(phrase in content for phrase in no_citas):
            results["message"] = "❌ No appointments available"
        elif any(phrase in content for phrase in hay_citas):
            results["found"] = True
            results["message"] = f"""
🚀 <b>¡CITA DISPONIBLE!</b> 🎉

📍 Provincia: {PROVINCIA}
📋 Trámite: Toma de Huellas
🕐 Hora: {time.strftime('%d/%m/%Y %H:%M')}

👉 RESERVA AHORA:
{BASE_URL}
            """.strip()
        else:
            results["message"] = "⚠️ Status unclear — page loaded but text not matched"
            page.screenshot(path=f"debug_{time.strftime('%Y%m%d_%H%M')}.png")

        browser.close()
        return results

if __name__ == "__main__":
    print("=" * 50)
    print("🤖 CITA CHECKER STARTED — BARCELONA HUELLAS")
    print(f"🕐 Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    result = check_appointments()
    
    if result["error"]:
        print(f"❌ ERROR: {result['error']}")
        send_telegram_alert(f"⚠️ ERROR:\n{result['error']}")
    elif result["found"]:
        print("🎉 CITAS FOUND!!! ALERT SENT!")
        send_telegram_alert(result["message"])
    else:
        print(result["message"])
    
    print("✅ Check finished")
