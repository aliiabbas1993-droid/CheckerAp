import os
import time
import random
import logging
from typing import Dict
import requests
from playwright.sync_api import sync_playwright

# ✅ Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

# ✅ Base Configuration
BASE_URL = "https://icp.administracionelectronica.gob.es/icpplustieb/index"
PROVINCIA = "Barcelona"
OFICINA = "Cualquier oficina"
TRAMITE_TEXT = "POLICÍA-TOMA DE HUELLAS (EXPEDICIÓN DE TARJETA) INICIAL, RENOVACIÓN, DUPLICADO Y LEY 14/2013"

# ✅ Delay Constants (in seconds)
DELAY_SHORT = (0.5, 1.5)
DELAY_MEDIUM = (1, 2)
DELAY_LONG = (2, 4)
DELAY_EXTRA_LONG = (3, 5)

# ✅ Timeout Constants (in milliseconds)
TIMEOUT_SHORT = 5000
TIMEOUT_MEDIUM = 10000
TIMEOUT_LONG = 30000

# ✅ Messages to check for no appointments
NO_CITAS_PHRASES = [
    "no hay citas disponibles",
    "no existen citas",
    "agotado",
    "su sesión ha caducado",
    "no hay citas en este momento"
]

# ✅ Messages to check for available appointments
HAY_CITAS_PHRASES = [
    "seleccione cita",
    "seleccione fecha",
    "seleccione la hora",
    "citas disponibles",
    "elige una oficina",
    "pulse continuar para seleccionar cita",
    "siguiente"
]


def send_telegram_alert(message: str) -> None:
    """Send alert message via Telegram bot"""
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            params={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"},
            timeout=15
        )
        logger.info("✅ Telegram alert sent")
    except requests.RequestException as e:
        logger.error(f"❌ Telegram error: {e}")


def check_appointments() -> Dict[str, any]:
    """Check for available appointments on the Spanish administration website"""
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
            logger.info("🌐 Proxy enabled")

        context = browser.new_context(**ctx_options)
        page = context.new_page()
        
        # ✅ Apply stealth — works with the correct function name now!
        stealth_sync(page)

        try:
            # ==================================================
            # STEP 1: Select Province
            # ==================================================
            logger.info("📍 Step 1/5 — Province...")
            page.goto(BASE_URL, timeout=TIMEOUT_LONG, wait_until="domcontentloaded")
            time.sleep(random.uniform(*DELAY_MEDIUM))
            page.select_option('select', has_text=PROVINCIA, timeout=TIMEOUT_SHORT)
            time.sleep(random.uniform(*DELAY_MEDIUM))
            page.click("input[type='submit'][value='Aceptar']", timeout=TIMEOUT_SHORT)
            page.wait_for_load_state("networkidle", timeout=TIMEOUT_LONG)
            time.sleep(random.uniform(*DELAY_LONG))

            # ==================================================
            # STEP 2: Select Office & Trámite
            # ==================================================
            logger.info("🏢 Step 2/5 — Office & Procedure...")
            try:
                page.select_option('select', has_text=OFICINA, timeout=TIMEOUT_SHORT)
                time.sleep(random.uniform(*DELAY_MEDIUM))
            except (TimeoutError, Exception) as e:
                logger.warning(f"⚠️ Office selection failed (continuing): {e}")
            
            page.select_option('select', has_text=TRAMITE_TEXT, timeout=TIMEOUT_SHORT)
            time.sleep(random.uniform(*DELAY_MEDIUM))
            page.click("input[type='submit'][value='Aceptar']", timeout=TIMEOUT_SHORT)
            page.wait_for_load_state("networkidle", timeout=TIMEOUT_LONG)
            time.sleep(random.uniform(*DELAY_LONG))

            # ==================================================
            # STEP 3: Click "Continuar sin clave" ✅
            # ==================================================
            logger.info("📄 Step 3/5 — Clicking 'Continuar sin clave'...")
            try:
                page.click("input[type='submit'][value='Continuar sin clave']", timeout=TIMEOUT_MEDIUM)
                page.wait_for_load_state("networkidle", timeout=TIMEOUT_LONG)
                time.sleep(random.uniform(*DELAY_LONG))
            except (TimeoutError, Exception) as e:
                logger.warning(f"⚠️ 'Continuar sin clave' not found, trying alternatives: {e}")
                try:
                    page.click("input[type='submit'][value='Entrar']", timeout=TIMEOUT_SHORT)
                    page.wait_for_load_state("networkidle", timeout=TIMEOUT_LONG)
                except (TimeoutError, Exception):
                    try:
                        page.click("button:has-text('Continuar sin clave')", timeout=TIMEOUT_SHORT)
                    except (TimeoutError, Exception) as e2:
                        logger.warning(f"⚠️ No terms button found — may have been skipped: {e2}")

            # ==================================================
            # STEP 4: PERSONAL DATA — NIE, Name, Nationality
            # ==================================================
            logger.info("👤 Step 4/5 — Entering personal data...")
            
            # Select Document Type = NIE
            try:
                page.select_option('select[name="tipoDocumento"]', label="N.I.E", timeout=TIMEOUT_SHORT)
                time.sleep(random.uniform(*DELAY_SHORT))
            except (TimeoutError, Exception):
                try:
                    page.select_option('select#tipoDocumento', label="N.I.E", timeout=TIMEOUT_SHORT)
                except (TimeoutError, Exception) as e:
                    results["error"] = f"Document type select failed: {e}"
                    logger.error(results["error"])
                    browser.close()
                    return results

            # Enter NIE Number
            try:
                nie_input = page.locator('input[name="numeroDocumento"]')
                nie_input.fill(NIE_NUMBER)
                time.sleep(random.uniform(*DELAY_SHORT))
            except (TimeoutError, Exception):
                try:
                    page.fill('input#numeroDocumento', NIE_NUMBER)
                except (TimeoutError, Exception) as e:
                    results["error"] = f"NIE input failed: {e}"
                    logger.error(results["error"])
                    browser.close()
                    return results

            # Enter Full Name
            try:
                name_input = page.locator('input[name="nombre"]')
                name_input.fill(FULL_NAME)
                time.sleep(random.uniform(*DELAY_SHORT))
            except (TimeoutError, Exception):
                try:
                    page.fill('input#nombre', FULL_NAME)
                except (TimeoutError, Exception) as e:
                    results["error"] = f"Name input failed: {e}"
                    logger.error(results["error"])
                    browser.close()
                    return results

            # Select Nationality
            try:
                page.select_option('select[name="nacionalidad"]', label=NATIONALITY, timeout=TIMEOUT_SHORT)
                time.sleep(random.uniform(*DELAY_MEDIUM))
            except (TimeoutError, Exception):
                try:
                    page.select_option('select#nacionalidad', label=NATIONALITY, timeout=TIMEOUT_SHORT)
                except (TimeoutError, Exception) as e:
                    results["error"] = f"Nationality select failed: {e}"
                    logger.error(results["error"])
                    browser.close()
                    return results

            # Submit Personal Data → Goes ALL the way to availability page! ✅
            try:
                page.click("input[type='submit'][value='Aceptar']", timeout=TIMEOUT_SHORT)
                page.wait_for_load_state("networkidle", timeout=TIMEOUT_LONG)
                time.sleep(random.uniform(*DELAY_EXTRA_LONG))
            except (TimeoutError, Exception) as e:
                results["error"] = f"Submit personal data failed: {e}"
                logger.error(results["error"])
                browser.close()
                return results

            # ==================================================
            # STEP 5: Check for Appointments — Availability Page! 🎯
            # ==================================================
            logger.info("🔍 Step 5/5 — Checking availability page...")
            content = page.content().lower()

            if any(phrase in content for phrase in NO_CITAS_PHRASES):
                results["message"] = "❌ No appointments available"
            elif any(phrase in content for phrase in HAY_CITAS_PHRASES):
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
                debug_filename = f"debug_{time.strftime('%Y%m%d_%H%M')}.png"
                page.screenshot(path=debug_filename)
                logger.warning(f"Screenshot saved to {debug_filename}")

        except Exception as e:
            results["error"] = f"Unexpected error during check: {e}"
            logger.error(results["error"])
        finally:
            browser.close()
            logger.info("🔒 Browser closed")

        return results


# ============================================================
# MAIN EXECUTION
# ============================================================
if __name__ == "__main__":
    logger.info("=" * 55)
    logger.info("🤖 CITA CHECKER STARTED — BARCELONA HUELLAS")
    logger.info(f"👤 NIE: {NIE_NUMBER} | Name: {FULL_NAME}")
    logger.info(f"🕐 Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 55)
    
    result = check_appointments()
    
    if result["error"]:
        logger.error(f"❌ ERROR: {result['error']}")
        send_telegram_alert(f"⚠️ ERROR:\n{result['error']}")
    elif result["found"]:
        logger.info("🎉 CITAS FOUND!!! ALERT SENT!")
        send_telegram_alert(result["message"])
    else:
        logger.info(result["message"])
    
    logger.info("✅ Check finished")
