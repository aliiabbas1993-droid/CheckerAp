import os
import time
import logging
from typing import Dict, Any

import requests
from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================
# SECRETS
# ============================================================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
FULL_NAME = os.getenv("FULL_NAME")
NIE_NUMBER = os.getenv("NIE_NUMBER")
NATIONALITY = os.getenv("NATIONALITY")


# ============================================================
# CONFIGURATION
# ============================================================

BASE_URL = (
    "https://icp.administracionelectronica.gob.es/"
    "icpplustieb/index"
)

PROVINCIA = "Barcelona"
OFICINA = "Cualquier oficina"

TRAMITE_TEXT = (
    "POLICÍA-TOMA DE HUELLAS "
    "(EXPEDICIÓN DE TARJETA) INICIAL, "
    "RENOVACIÓN, DUPLICADO Y LEY 14/2013"
)

TIMEOUT_NAVIGATION = 90000
TIMEOUT_ELEMENT = 15000

# Don't hammer the site with repeated retries.
MAX_NAVIGATION_ATTEMPTS = 2
RETRY_DELAY_SECONDS = 10


NO_CITAS_PHRASES = [
    "no hay citas disponibles",
    "no existen citas",
    "agotado",
    "su sesión ha caducado",
    "no hay citas en este momento",
]

HAY_CITAS_PHRASES = [
    "seleccione cita",
    "seleccione fecha",
    "seleccione la hora",
    "citas disponibles",
    "pulse continuar para seleccionar cita",
]


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram_alert(message: str) -> None:
    """Send an alert through Telegram."""

    if not BOT_TOKEN or not CHAT_ID:
        logger.error("Telegram credentials are missing.")
        return

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            params={
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
            },
            timeout=15,
        )

        response.raise_for_status()
        logger.info("Telegram alert sent.")

    except requests.RequestException as exc:
        logger.error("Telegram error: %s", exc)


# ============================================================
# NAVIGATION
# ============================================================

def goto_page(page, url: str) -> bool:
    """
    Navigate conservatively.

    We use 'commit' rather than waiting for the entire page to
    reach DOMContentLoaded. Some government pages can be slow
    to finish loading.
    """

    for attempt in range(1, MAX_NAVIGATION_ATTEMPTS + 1):

        try:
            logger.info(
                "Opening page (attempt %s/%s)",
                attempt,
                MAX_NAVIGATION_ATTEMPTS,
            )

            page.goto(
                url,
                wait_until="commit",
                timeout=TIMEOUT_NAVIGATION,
            )

            logger.info("Initial response received.")
            return True

        except PlaywrightTimeoutError:
            logger.warning(
                "Navigation timed out on attempt %s.",
                attempt,
            )

        except Exception as exc:
            logger.warning(
                "Navigation failed on attempt %s: %s",
                attempt,
                exc,
            )

        if attempt < MAX_NAVIGATION_ATTEMPTS:
            logger.info(
                "Waiting %s seconds before retry...",
                RETRY_DELAY_SECONDS,
            )
            time.sleep(RETRY_DELAY_SECONDS)

    return False


# ============================================================
# SELECT HELPERS
# ============================================================

def select_option_by_label(
    page,
    selector: str,
    label: str,
) -> None:
    """
    Select an option using a specific select element.

    This fixes the previous incorrect usage of:
        page.select_option(..., has_text=...)
    """

    element = page.locator(selector)

    element.wait_for(
        state="visible",
        timeout=TIMEOUT_ELEMENT,
    )

    element.select_option(label=label)

    logger.info(
        "Selected '%s' from %s",
        label,
        selector,
    )


def select_option_from_any_select(
    page,
    label: str,
) -> None:
    """
    Find a select containing an option with the requested text.
    """

    selects = page.locator("select")
    count = selects.count()

    for index in range(count):

        select = selects.nth(index)

        try:
            options = select.locator("option")
            option_count = options.count()

            for option_index in range(option_count):

                option = options.nth(option_index)
                text = option.inner_text().strip()

                if text == label:
                    select.select_option(
                        value=option.get_attribute("value")
                    )

                    logger.info(
                        "Selected '%s'",
                        label,
                    )
                    return

        except Exception:
            continue

    raise RuntimeError(
        f"Could not find select option: {label}"
    )


# ============================================================
# PAGE STATUS
# ============================================================

def detect_appointment_status(page) -> Dict[str, Any]:
    """
    Inspect the current page for known appointment messages.
    """

    content = page.locator("body").inner_text().lower()

    for phrase in NO_CITAS_PHRASES:
        if phrase in content:
            return {
                "found": False,
                "message": "No appointments available.",
                "error": None,
            }

    for phrase in HAY_CITAS_PHRASES:
        if phrase in content:
            return {
                "found": True,
                "message": "Appointment availability detected.",
                "error": None,
            }

    return {
        "found": False,
        "message": "Page loaded, but appointment status is unclear.",
        "error": None,
    }


# ============================================================
# MAIN CHECK
# ============================================================

def check_appointments() -> Dict[str, Any]:

    result = {
        "found": False,
        "message": "",
        "error": None,
    }

    with sync_playwright() as playwright:

        browser = playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        context = browser.new_context(
            viewport={
                "width": 1280,
                "height": 900,
            },
            locale="es-ES",
            timezone_id="Europe/Madrid",
        )

        page = context.new_page()

        try:

            # ------------------------------------------------
            # STEP 1 — OPEN SITE
            # ------------------------------------------------

            logger.info("STEP 1 — Opening government website.")

            if not goto_page(page, BASE_URL):
                result["error"] = (
                    "Government website could not be reached "
                    "after the allowed attempts."
                )
                return result

            time.sleep(3)

            # ------------------------------------------------
            # STEP 2 — PROVINCE
            # ------------------------------------------------

            logger.info("STEP 2 — Selecting province.")

            select_option_from_any_select(
                page,
                PROVINCIA,
            )

            time.sleep(1)

            page.locator(
                "input[type='submit'][value='Aceptar']"
            ).first.click(
                timeout=TIMEOUT_ELEMENT
            )

            time.sleep(3)

            # ------------------------------------------------
            # STEP 3 — OFFICE / PROCEDURE
            # ------------------------------------------------

            logger.info(
                "STEP 3 — Selecting office and procedure."
            )

            # Office may not always be required.
            try:
                select_option_from_any_select(
                    page,
                    OFICINA,
                )
            except Exception as exc:
                logger.info(
                    "Office selection skipped: %s",
                    exc,
                )

            select_option_from_any_select(
                page,
                TRAMITE_TEXT,
            )

            time.sleep(1)

            page.locator(
                "input[type='submit'][value='Aceptar']"
            ).first.click(
                timeout=TIMEOUT_ELEMENT
            )

            time.sleep(3)

            # ------------------------------------------------
            # STEP 4 — CONTINUE WITHOUT CL@VE
            # ------------------------------------------------

            logger.info(
                "STEP 4 — Looking for 'Continuar sin clave'."
            )

            continue_button = page.locator(
                "input[type='submit'][value='Continuar sin clave']"
            )

            if continue_button.count() > 0:
                continue_button.first.click(
                    timeout=TIMEOUT_ELEMENT
                )
                time.sleep(3)

            else:
                logger.info(
                    "'Continuar sin clave' not present."
                )

            # ------------------------------------------------
            # STEP 5 — PERSONAL DATA
            # ------------------------------------------------

            logger.info(
                "STEP 5 — Entering personal information."
            )

            # Document type
            try:
                page.locator(
                    'select[name="tipoDocumento"]'
                ).select_option(
                    label="N.I.E"
                )
            except Exception:
                page.locator(
                    "select#tipoDocumento"
                ).select_option(
                    label="N.I.E"
                )

            # NIE
            nie = page.locator(
                'input[name="numeroDocumento"]'
            )

            if nie.count() == 0:
                nie = page.locator(
                    "input#numeroDocumento"
                )

            nie.fill(NIE_NUMBER)

            # Name
            name = page.locator(
                'input[name="nombre"]'
            )

            if name.count() == 0:
                name = page.locator(
                    "input#nombre"
                )

            name.fill(FULL_NAME)

            # Nationality
            try:
                page.locator(
                    'select[name="nacionalidad"]'
                ).select_option(
                    label=NATIONALITY
                )
            except Exception:
                page.locator(
                    "select#nacionalidad"
                ).select_option(
                    label=NATIONALITY
                )

            time.sleep(1)

            page.locator(
                "input[type='submit'][value='Aceptar']"
            ).first.click(
                timeout=TIMEOUT_ELEMENT
            )

            time.sleep(5)

            # ------------------------------------------------
            # STEP 6 — CHECK RESULT
            # ------------------------------------------------

            logger.info(
                "STEP 6 — Checking appointment availability."
            )

            result.update(
                detect_appointment_status(page)
            )

            if result["found"]:

                result["message"] = f"""
🚀 <b>¡CITA DISPONIBLE!</b> 🎉

📍 Provincia: {PROVINCIA}
📋 Trámite: Toma de Huellas
🕐 Detectado: {time.strftime('%d/%m/%Y %H:%M')}

👉 ¡VE A RESERVAR AHORA!
{BASE_URL}
""".strip()

            elif result["message"]:
                logger.info(result["message"])

            return result

        except Exception as exc:

            result["error"] = (
                f"Unexpected error during check: {exc}"
            )

            logger.exception(
                "Unexpected checker error."
            )

            # Save diagnostic screenshot.
            try:
                filename = (
                    f"debug_{time.strftime('%Y%m%d_%H%M%S')}.png"
                )

                page.screenshot(
                    path=filename,
                    full_page=True,
                )

                logger.info(
                    "Diagnostic screenshot saved: %s",
                    filename,
                )

            except Exception as screenshot_error:
                logger.warning(
                    "Could not save screenshot: %s",
                    screenshot_error,
                )

            return result

        finally:

            browser.close()
            logger.info("Browser closed.")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    logger.info("=" * 60)
    logger.info(
        "CITA CHECKER STARTED — BARCELONA HUELLAS"
    )
    logger.info(
        "Time: %s",
        time.strftime("%Y-%m-%d %H:%M:%S"),
    )
    logger.info("=" * 60)

    result = check_appointments()

    if result["error"]:

        logger.error(
            "ERROR: %s",
            result["error"],
        )

        send_telegram_alert(
            f"⚠️ <b>Checker error</b>\n\n"
            f"{result['error']}"
        )

    elif result["found"]:

        logger.info(
            "🎉 APPOINTMENT FOUND!"
        )

        send_telegram_alert(
            result["message"]
        )

    else:

        logger.info(
            result["message"]
        )

    logger.info("Check finished.")
