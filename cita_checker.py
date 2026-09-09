import os
import time
import random
import requests
from playwright.sync_api import sync_playwright

# ✅ FINAL FIX — Correct import name for ALL versions!
try:
    # Newer versions use just "stealth"
    from playwright_stealth import stealth as stealth_sync
except ImportError:
    try:
        # Older version
        from playwright_stealth import stealth_sync
    except ImportError:
        # Alternative name
        from playwright_stealth import sync_stealth as stealth_sync

# ⚠️ ALL SET IN GITHUB SECRETS — NEVER WRITE HERE!
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PROXY_SERVER = os.getenv("PROXY_SERVER")
FULL_NAME = os.getenv("FULL_NAME")
NIE_NUMBER = os.getenv("NIE_NUMBER")
NATIONALITY = os.getenv("NATIONALITY")

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
        
        # ✅ Apply stealth — works with the correct function name now!
        stealth_sync(page)

        # ==================================================
        # STEP 1: Select Province
        # ==================================================
        print("📍 Step 1/5 — Province...")
        page.goto(BASE_URL, timeout=60000, wait_until="domcontentloaded")
        time.sleep(random.uniform(2, 4))
        page.select_option('select', has_text=PROVINCIA, timeout=5000)
        time.sleep(random.uniform(1, 2))
        page.click("input[type='submit'][value='Aceptar']", timeout=5000)
        page.wait_for_load_state("networkidle", timeout=30000)
        time.sleep(random.uniform(2, 3))

        # ==================================================
        # STEP 2: Select Office & Trámite
        # ==================================================
        print("🏢 Step 2/5 — Office & Procedure...")
        try:
            page.select_option('select', has_text=OFICINA, timeout=5000)
            time.sleep(random.uniform(1, 2))
        except: pass
        page.select_option('select', has_text=TRAMITE_TEXT, timeout=5000)
        time.sleep(random.uniform(1, 2))
        page.click("input[type='submit'][value='Aceptar']", timeout=5000)
        page.wait_for_load_state("networkidle", timeout=30000)
        time.sleep(random.uniform(2, 3))

        # ==================================================
        # STEP 3: Click "Continuar sin clave" ✅
        # ==================================================
        print("📄 Step 3/5 — Clicking 'Continuar sin clave'...")
        try:
            page.click("input[type='submit'][value='Continuar sin clave']", timeout=10000)
            page.wait_for_load_state("networkidle", timeout=30000)
            time.sleep(random.uniform(2, 4))
        except Exception as e:
            print(f"⚠️ 'Continuar sin clave' not found, trying alternatives: {e}")
            try:
                page.click("input[type='submit'][value='Entrar']", timeout=5000)
                page.wait_for_load_state("networkidle", timeout=30000)
            except:
                try:
                    page.click("button:has-text('Continuar sin clave')", timeout=5000)
                except Exception as e2:
                    print(f"⚠️ No terms button found — may have been skipped: {e2}")

        # ==================================================
        # STEP 4: PERSONAL DATA — NIE, Name, Nationality
        # ==================================================
        print("👤 Step 4/5 — Entering personal data...")
        
        # Select Document Type = NIE
        try:
            page.select_option('select[name="tipoDocumento"]', label="N.I.E", timeout=5000)
            time.sleep(random.uniform(0.5, 1.5))
        except:
            try:
                page.select_option('select#tipoDocumento', label="N.I.E", timeout=5000)
            except Exception as e:
                results["error"] = f"Document type select failed: {e}"
                browser.close()
                return results

        # Enter NIE Number
        try:
            nie_input = page.locator('input[name="numeroDocumento"]')
            nie_input.fill(NIE_NUMBER)
            time.sleep(random.uniform(0.5, 1))
        except:
            try:
                page.fill('input#numeroDocumento', NIE_NUMBER)
            except Exception as e:
                results["error"] = f"NIE input failed: {e}"
                browser.close()
                return results

        # Enter Full Name
        try:
            name_input = page.locator('input[name="nombre"]')
            name_input.fill(FULL_NAME)
            time.sleep(random.uniform(0.5, 1))
        except:
            try:
                page.fill('input#nombre', FULL_NAME)
            except Exception as e:
                results["error"] = f"Name input failed: {e}"
                browser.close()
                return results

        # Select Nationality
        try:
            page.select_option('select[name="nacionalidad"]', label=NATIONALITY, timeout=5000)
            time.sleep(random.uniform(1, 2))
        except:
            try:
                page.select_option('select#nacionalidad', label=NATIONALITY, timeout=5000)
            except Exception as e:
                results["error"] = f"Nationality select failed: {e}"
                browser.close()
                return results

        # Submit Personal Data → Goes ALL the way to availability page! ✅
        try:
            page.click("input[type='submit'][value='Aceptar']", timeout=5000)
            page.wait_for_load_state("networkidle", timeout=30000)
            time.sleep(random.uniform(3, 5))
        except Exception as e:
            results["error"] = f"Submit personal data failed: {e}"
            browser.close()
            return results

        # ==================================================
        # STEP 5: Check for Appointments — Availability Page! 🎯
        # ==================================================
        print("🔍 Step 5/5 — Checking availability page...")
        content = page.content().lower()

        no_citas = [
            "no hay citas disponibles",
            "no existen citas",
            "agotado",
            "su sesión ha caducado",
            "no hay citas en este momento"
        ]
        hay_citas = [
            "seleccione cita",
            "seleccione fecha",
            "seleccione la hora",
            "citas disponibles",
            "elige una oficina",
            "pulse continuar para seleccionar cita",
            "siguiente"
        ]

        if any(phrase in content for phrase in no_citas):
            results["message"] = "❌ No appointments available"
        elif any(phrase in content for phrase in hay_citas):
            results["found"] = True
            results["message"] = f"""
🚀 <b>¡CITA DISPONIBLE!</b> 🎉

📍 Provincia: {PROVINCIA}
📋 Trámite: Toma de Huellas
👤 NIE: {NIE_NUMBER}
🕐 Hora: {time.strftime('%d/%m/%Y %H:%M')}

👉 ¡VE A RESERVAR AHORA!
{BASE_URL}
            """.strip()
        else:
            results["message"] = "⚠️ Page loaded — status unclear"
            page.screenshot(path=f"debug_{time.strftime('%Y%m%d_%H%M')}.png")

        browser.close()
        return results

# ---------------- MAIN ----------------
if __name__ == "__main__":
    print("=" * 55)
    print("🤖 CITA CHECKER STARTED — BARCELONA HUELLAS")
    print(f"👤 NIE: {NIE_NUMBER} | Name: {FULL_NAME}")
    print(f"🕐 Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)
    
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
