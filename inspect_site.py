import asyncio
from pathlib import Path

from playwright.async_api import async_playwright


URL = (
    "https://citaprevia.administracionelectronica.gob.es/"
    "icpplus/citar"
)

OUTPUT_DIR = Path("site_capture")


async def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        print("Launching Chromium...")

        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        context = await browser.new_context(
            viewport={
                "width": 1920,
                "height": 1080,
            },
            locale="es-ES",
            timezone_id="Europe/Madrid",
            extra_http_headers={
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
            },
        )

        page = await context.new_page()

        page.set_default_timeout(60000)

        try:
            print()
            print("=" * 70)
            print("OPENING CURRENT GOVERNMENT APPOINTMENT SITE")
            print("=" * 70)
            print(URL)
            print()

            response = await page.goto(
                URL,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            print("Navigation completed.")
            print(f"HTTP status: {response.status if response else 'UNKNOWN'}")
            print(f"Final URL: {page.url}")
            print(f"Title: {await page.title()}")

            # Give JavaScript a little time to finish rendering.
            await page.wait_for_timeout(5000)

            # --------------------------------------------------
            # SAVE COMPLETE HTML
            # --------------------------------------------------

            html = await page.content()

            html_path = OUTPUT_DIR / "page.html"
            html_path.write_text(
                html,
                encoding="utf-8",
            )

            print(f"HTML saved: {html_path}")
            print(f"HTML size: {len(html):,} characters")

            # --------------------------------------------------
            # SAVE VISIBLE TEXT
            # --------------------------------------------------

            try:
                body_text = await page.locator("body").inner_text()

                text_path = OUTPUT_DIR / "page.txt"
                text_path.write_text(
                    body_text,
                    encoding="utf-8",
                )

                print(f"Text saved: {text_path}")

            except Exception as exc:
                print(f"Could not save body text: {exc}")

            # --------------------------------------------------
            # SAVE SCREENSHOT
            # --------------------------------------------------

            screenshot_path = OUTPUT_DIR / "page.png"

            await page.screenshot(
                path=str(screenshot_path),
                full_page=True,
            )

            print(f"Screenshot saved: {screenshot_path}")

            # --------------------------------------------------
            # EXTRACT SELECT ELEMENTS
            # --------------------------------------------------

            selects = await page.locator("select").evaluate_all(
                """
                elements => elements.map(el => ({
                    id: el.id,
                    name: el.name,
                    value: el.value,
                    title: el.getAttribute("title"),
                    options: Array.from(el.options).map(o => ({
                        text: o.textContent.trim(),
                        value: o.value
                    }))
                }))
                """
            )

            select_path = OUTPUT_DIR / "selects.txt"

            with select_path.open(
                "w",
                encoding="utf-8",
            ) as f:
                for index, select in enumerate(selects, 1):
                    f.write("=" * 70 + "\\n")
                    f.write(f"SELECT #{index}\\n")
                    f.write("=" * 70 + "\\n")
                    f.write(f"ID: {select['id']}\\n")
                    f.write(f"NAME: {select['name']}\\n")
                    f.write(f"VALUE: {select['value']}\\n")
                    f.write(f"TITLE: {select['title']}\\n")
                    f.write("\\nOPTIONS:\\n")

                    for option in select["options"]:
                        f.write(
                            f"  VALUE={option['value']!r} "
                            f"TEXT={option['text']!r}\\n"
                        )

                    f.write("\\n")

            print(f"Select information saved: {select_path}")

            # --------------------------------------------------
            # EXTRACT INPUTS
            # --------------------------------------------------

            inputs = await page.locator(
                "input"
            ).evaluate_all(
                """
                elements => elements.map(el => ({
                    id: el.id,
                    name: el.name,
                    type: el.type,
                    value: el.value,
                    placeholder: el.placeholder,
                    required: el.required
                }))
                """
            )

            input_path = OUTPUT_DIR / "inputs.txt"

            with input_path.open(
                "w",
                encoding="utf-8",
            ) as f:
                for index, item in enumerate(inputs, 1):
                    f.write(
                        f"{index}. "
                        f"ID={item['id']!r} "
                        f"NAME={item['name']!r} "
                        f"TYPE={item['type']!r} "
                        f"VALUE={item['value']!r} "
                        f"PLACEHOLDER={item['placeholder']!r} "
                        f"REQUIRED={item['required']!r}\\n"
                    )

            print(f"Input information saved: {input_path}")

            # --------------------------------------------------
            # EXTRACT BUTTONS
            # --------------------------------------------------

            buttons = await page.locator(
                "button, input[type='button'], "
                "input[type='submit'], a"
            ).evaluate_all(
                """
                elements => elements.map(el => ({
                    tag: el.tagName,
                    id: el.id,
                    name: el.name,
                    type: el.type || "",
                    text: el.innerText || el.value || "",
                    href: el.href || ""
                }))
                """
            )

            button_path = OUTPUT_DIR / "buttons.txt"

            with button_path.open(
                "w",
                encoding="utf-8",
            ) as f:
                for index, button in enumerate(buttons, 1):
                    text = " ".join(
                        button["text"].split()
                    )

                    f.write(
                        f"{index}. "
                        f"TAG={button['tag']!r} "
                        f"ID={button['id']!r} "
                        f"NAME={button['name']!r} "
                        f"TYPE={button['type']!r} "
                        f"TEXT={text!r} "
                        f"HREF={button['href']!r}\\n"
                    )

            print(f"Button information saved: {button_path}")

            # --------------------------------------------------
            # PRINT USEFUL INFORMATION TO GITHUB LOG
            # --------------------------------------------------

            print()
            print("=" * 70)
            print("PAGE INFORMATION")
            print("=" * 70)

            print(f"Final URL: {page.url}")
            print(f"Title: {await page.title()}")
            print(f"Selects found: {len(selects)}")
            print(f"Inputs found: {len(inputs)}")
            print(f"Buttons/links found: {len(buttons)}")

            print()
            print("Visible page text:")
            print("-" * 70)

            visible_text = await page.locator("body").inner_text()

            print(visible_text[:10000])

            print()
            print("=" * 70)
            print("CAPTURE COMPLETE")
            print("=" * 70)

        except Exception as exc:
            print()
            print("=" * 70)
            print("ERROR")
            print("=" * 70)
            print(repr(exc))

            # Save whatever HTML exists even if navigation fails.
            try:
                html = await page.content()

                error_html = OUTPUT_DIR / "error_page.html"

                error_html.write_text(
                    html,
                    encoding="utf-8",
                )

                print(
                    f"Partial HTML saved: {error_html}"
                )

            except Exception:
                pass

            raise

        finally:
            await context.close()
            await browser.close()

            print("Browser closed.")


if __name__ == "__main__":
    asyncio.run(main())
