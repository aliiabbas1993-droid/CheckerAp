from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path("tie_capture")
OUT.mkdir(exist_ok=True)

URLS = [
    "https://sede.administracionespublicas.gob.es/pagina/index/directorio/icpplus",
    "https://sede.administracionespublicas.gob.es/icpplustiej/citar",
]

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"],
    )

    context = browser.new_context(
        locale="es-ES",
        timezone_id="Europe/Madrid",
    )

    for i, url in enumerate(URLS, start=1):
        page = context.new_page()

        print("\n" + "=" * 80)
        print(f"OPENING {url}")
        print("=" * 80)

        try:
            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            page.wait_for_timeout(5000)

            print("STATUS:", response.status if response else "NO RESPONSE")
            print("FINAL URL:", page.url)
            print("TITLE:", page.title())

            # Save HTML
            (OUT / f"page{i}.html").write_text(
                page.content(),
                encoding="utf-8",
            )

            # Save visible text
            (OUT / f"page{i}.txt").write_text(
                page.locator("body").inner_text(),
                encoding="utf-8",
            )

            # Screenshot
            page.screenshot(
                path=str(OUT / f"page{i}.png"),
                full_page=True,
            )

            # Frames
            frames = []
            for frame in page.frames:
                frames.append(
                    f"FRAME URL: {frame.url}"
                )

            (OUT / f"frames{i}.txt").write_text(
                "\n".join(frames),
                encoding="utf-8",
            )

            print("\nFRAMES:")
            for frame in frames:
                print(frame)

            # Links
            links = page.locator("a").all()
            link_lines = []

            for link in links:
                try:
                    text = (link.inner_text() or "").strip()
                    href = link.get_attribute("href")
                    if text or href:
                        link_lines.append(f"{text!r} -> {href!r}")
                except Exception:
                    pass

            (OUT / f"links{i}.txt").write_text(
                "\n".join(link_lines),
                encoding="utf-8",
            )

            # Forms
            forms = page.locator("form").all()
            form_lines = []

            for form in forms:
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

            print(f"\nCapture saved for page {i}")

        except Exception as e:
            print("ERROR:", repr(e))
            (OUT / f"error{i}.txt").write_text(
                repr(e),
                encoding="utf-8",
            )

        finally:
            page.close()

    browser.close()
