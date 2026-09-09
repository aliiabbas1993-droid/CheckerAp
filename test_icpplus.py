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

            text = page.locator("body").inner_text()

            print("\nPAGE TEXT:\n")
            print(text[:10000])

            (OUT / f"page{i}.html").write_text(
                page.content(),
                encoding="utf-8",
            )

            (OUT / f"page{i}.txt").write_text(
                text,
                encoding="utf-8",
            )

            page.screenshot(
                path=str(OUT / f"page{i}.png"),
                full_page=True,
            )

            selects = page.locator("select")
            select_info = []

            for j in range(await selects.count()):
                s = selects.nth(j)

                select_info.append(
                    f"""
SELECT {j}
id={await s.get_attribute("id")}
name={await s.get_attribute("name")}
options={await s.locator("option").all_inner_texts()}
"""
                )

            (OUT / f"selects{i}.txt").write_text(
                "\n".join(select_info),
                encoding="utf-8",
            )

        except Exception as e:
            print("ERROR:", repr(e))

            (OUT / f"error{i}.txt").write_text(
                repr(e),
                encoding="utf-8",
            )

        finally:
            page.close()

    browser.close()
