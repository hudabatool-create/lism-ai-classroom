"""Does the certificate the prompt now prescribes actually reach the device?

The snippet is lifted out of the prompt text rather than retyped here, so this
fails if the two ever drift apart. Tested inside an iframe, because that is
where a student meets it -- LISM serves the lesson in one.
"""
import asyncio
import io
import os
import re
import tempfile

from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
PROMPT = os.path.join(HERE, "lesson_deck_master_prompt.txt")
OUT = tempfile.mkdtemp(prefix="lism-cert-")

prompt = io.open(PROMPT, encoding="utf-8").read()
match = re.search(r"(  function saveCertificate\(\)\{.*?\n  \})", prompt, re.S)
assert match, "the saveCertificate snippet is no longer in the prompt"
snippet = match.group(1)
print("lifted the snippet out of the prompt:", len(snippet), "chars")

DECK = """<!DOCTYPE html><html lang="en" dir="ltr"><head><meta charset="utf-8"><style>
  body { font-family: system-ui; background: #0f172a; }
  #certificate { background: #fff; color: #1d2732; border: 10px double #8b6d3f;
                 padding: 30px; text-align: center; }
  #certificate h2 { color: #5b4527; }
</style></head><body>
  <div id="certificate">
    <h2>Certificate of Achievement &middot; Extension Challenge</h2>
    <p>Awarded to</p>
    <h1 id="who">Huda Batool</h1>
    <p>For completing the SOME pathway challenge task on Python Variables.</p>
  </div>
  <button id="save" onclick="saveCertificate()">Save my certificate</button>
<script>
const PROFILE = { lang: 'en', dir: 'ltr' };
var studentName = 'Huda Batool';
__SNIPPET__
</script></body></html>"""

HOST = """<!DOCTYPE html><html><body style="margin:0">
  <iframe id="lesson" src="deck.html" style="width:100%;height:600px;border:0"></iframe>
</body></html>"""

io.open(os.path.join(OUT, "deck.html"), "w", encoding="utf-8").write(
    DECK.replace("__SNIPPET__", snippet))
io.open(os.path.join(OUT, "host.html"), "w", encoding="utf-8").write(HOST)


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(accept_downloads=True)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)[:90]))

        await page.goto("file:///" + os.path.join(OUT, "host.html").replace("\\", "/"))
        await page.wait_for_timeout(700)

        frame = page.frames[1]
        async with page.expect_download(timeout=15000) as info:
            await frame.click("#save")
        download = await info.value

        saved = os.path.join(OUT, "cert-out.html")
        await download.save_as(saved)
        body = io.open(saved, encoding="utf-8").read()

        print()
        print("  suggested filename :", download.suggested_filename)
        print("  file size          :", len(body), "bytes")
        print("  keeps the student  :", "Huda Batool" in body)
        print("  keeps the wording  :", "Extension Challenge" in body)
        print("  keeps the styling  :", "double #8b6d3f" in body)
        print("  A4 landscape set   :", "size:A4 landscape" in body)
        print("  self-contained     :", "<script" not in body.lower())
        print("  JS errors          :", errors or "none")

        ok = (download.suggested_filename.endswith(".html")
              and "Huda Batool" in body
              and "double #8b6d3f" in body
              and "size:A4 landscape" in body
              and not errors)
        print()
        print("VERDICT:", "the certificate reaches the device" if ok else "FAILED")
        await browser.close()
        raise SystemExit(0 if ok else 1)


asyncio.run(main())
