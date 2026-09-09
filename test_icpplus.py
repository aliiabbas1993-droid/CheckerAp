from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path("icpplus_test")
OUT.mkdir(exist_ok=True)

URLS = [
    "https://sede.administracionespublicas.gob.es/icpplus/citar",
    "https://sede.administracionespublicas.gob.es/icpplus/citar?p=8&locale=es",
    "https://icp.administracionelectronica.gob.es/icpplus/index.html",
]

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ],
    )

    context = browser.new_context(
        locale="es-ES",
        timezone_id="Europe/Madrid",
    )

    for i, url in enumerate(URLS, 1):
        page = context.new_page()

        print("\n" + "=" * 80)
        print(f"TEST {i}: {url}")
        print("=" * 80)

        try:
            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            page.wait_for_timeout(5000)

            status = response.status if response else None

            print("STATUS:", status)
            print("FINAL URL:", page.url)
            print("TITLE:", page.title())

            # Visible text
            text = page.locator("body").inner_text()

            print("\nPAGE TEXT:\n")
            print(text[:10000])

            # Save HTML
            (OUT / f"page{i}.html").write_text(
                page.content(),
                encoding="utf-8",
            )

            # Save text
            (OUT / f"page{i}.txt").write_text(
                text,
                encoding="utf-8",
            )

            # Screenshot
            page.screenshot(
                path=str(OUT / f"page{i}.png"),
                full_page=True,
            )

            # Save frame information
            frame_lines = []

            for frame in page.frames:
                frame_lines.append(
                    f"FRAME URL: {frame.url}"
                )

            (OUT / f"frames{i}.txt").write_text(
                "\n".join(frame_lines),
                encoding="utf-8",
            )

            print("\nFRAMES:")
            for line in frame_lines:
                print(line)

            # Save links
            link_lines = []

            for link in page.locator("a").all():
                try:
                    text_value = (link.inner_text() or "").strip()
                    href = link.get_attribute("href")

                    if text_value or href:
                        link_lines.append(
                            f"{text_value!r} -> {href!r}"
                        )
                except Exception:
                    pass

            (OUT / f"links{i}.txt").write_text(
                "\n".join(link_lines),
                encoding="utf-8",
            )

            # Save forms
            form_lines = []

            for form in page.locator("form").all():
                try:
                    form_lines.append(
                        f"FORM action={form.get_attribute('action')!r} "
                        f"method={form.get_attribute('method')!r}"
                    )
                except Exception:
                    pass

            (OUT / f"forms{i}.txt").write_text(
                "\n".join(form_lines),
                encoding="utf-8",
            )

            # Save selects
            select_lines = []

            selects = page.locator("select")

            for j in range(selects.count()):
                select = selects.nth(j)

                select_lines.append(
                    f"SELECT {j}\n"
                    f"id={select.get_attribute('id')}\n"
                    f"name={select.get_attribute('name')}\n"
                    f"options={select.locator('option').all_inner_texts()}\n"
                )

            (OUT / f"selects{i}.txt").write_text(
                "\n".join(select_lines),
                encoding="utf-8",
            )

            print(f"\nCapture {i} saved successfully.")

        except Exception as e:
            print("ERROR:", repr(e))

            (OUT / f"error{i}.txt").write_text(
                repr(e),
                encoding="utf-8",
            )

        finally:
            page.close()

    browser.close()
