#!/usr/bin/env python3
"""Validate a rendered page before publishing it.

Usage:
    check.py <page.html>              # static checks only (no browser needed)
    check.py <page.html> --browser    # also measure layout in headless Chrome

Static checks:
  - tag balance
  - every var(--token) is defined on the BARE :root (the classic unreadable-artifact bug
    is a color defined only inside a media or [data-theme] block)
  - no literal colors outside the token blocks
  - no external resource loads, no <script>, no doctype/html/head/body wrapper
  - a <title> is present, and the file is under the artifact size ceiling

Browser checks (needs Google Chrome):
  - documentElement.scrollWidth == viewport at several widths, i.e. no horizontal
    page scroll; wide code must scroll inside its own container instead

Exits 1 if any check fails.
"""
import re, sys, os, json, html, subprocess, argparse, tempfile
from html.parser import HTMLParser

VOID = {"br", "hr", "img", "input", "meta", "link", "source", "col", "area",
        "base", "wbr", "embed", "track", "param"}
MAX_BYTES = 16 * 1024 * 1024
CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome", "chromium", "chromium-browser",
]


class Balance(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.errors = [], []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append((tag, self.getpos()))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append(f"stray </{tag}> at {self.getpos()}")
            return
        if self.stack[-1][0] == tag:
            self.stack.pop()
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                self.errors.append(
                    f"</{tag}> at {self.getpos()} left unclosed: {[t for t, _ in self.stack[i+1:]]}")
                del self.stack[i:]
                return
        self.errors.append(f"stray </{tag}> at {self.getpos()}")


def find_chrome():
    for c in CHROME_CANDIDATES:
        if os.path.exists(c):
            return c
        from shutil import which
        if which(c):
            return which(c)
    return None


def static_checks(path):
    src = open(path).read()
    fails = []

    b = Balance()
    b.feed(src)
    if b.stack:
        b.errors.append(f"never closed: {[t for t, _ in b.stack][:10]}")
    if b.errors:
        fails.append(("tag balance", b.errors[:10]))
    print(f"size:            {len(src)/1024:.0f} KB" + ("  OVER LIMIT" if len(src) > MAX_BYTES else ""))
    if len(src) > MAX_BYTES:
        fails.append(("size", [f"{len(src)} bytes exceeds 16MB"]))
    print(f"tag errors:      {len(b.errors)}")

    m = re.search(r"<style>(.*?)</style>", src, re.S)
    if not m:
        fails.append(("style", ["no <style> block found"]))
    else:
        style = m.group(1)
        rm = re.search(r":root\s*\{(.*?)\}", style, re.S)
        root_tokens = set(re.findall(r"(--[\w-]+)\s*:", rm.group(1))) if rm else set()
        used = set(re.findall(r"var\((--[\w-]+)", style))
        missing = used - root_tokens
        print(f"tokens on :root: {len(root_tokens)}; referenced: {len(used)}; undefined: {len(missing)}")
        if missing:
            fails.append(("theme tokens", [f"var({t}) never defined on bare :root" for t in sorted(missing)]))

        lits = []
        for prop, val in re.findall(r"(?:^|;|\{)\s*(background|color|border[\w-]*|box-shadow|fill|stroke)\s*:\s*([^;}]+)", style):
            if "var(" in val:
                continue
            if re.search(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(", val):
                lits.append(f"{prop}: {val.strip()}")
        print(f"literal colors:  {len(lits)}")
        if lits:
            fails.append(("literal colors", lits[:10]))

        flat = re.sub(r"\s+", "", style)
        if not re.search(r"body\{[^}]*background:var\(--", flat):
            fails.append(("body background", ["body must set background from a token, or it "
                                              "borrows the host theme's ground"]))
        for probe in ['[data-theme="dark"]', "prefers-color-scheme:dark", '[data-theme="light"]']:
            if probe.replace(" ", "") not in flat:
                fails.append(("theme coverage", [f"missing {probe} block"]))

    if re.search(r"<(!doctype|html|head|body)\b", src, re.I):
        fails.append(("wrapper", ["file must contain page content only, no doctype/html/head/body"]))
    if re.search(r"<script\b", src, re.I):
        fails.append(("script", ["artifact CSP blocks scripts; the page must be static"]))
    ext = re.findall(r'(?:\bsrc|\bhref)\s*=\s*"(https?://[^"]+)"', src)
    css_ext = re.findall(r'@import|url\(\s*["\']?https?://', src)
    print(f"external loads:  {len(css_ext)} (anchors to {len(set(ext))} URLs are fine)")
    if css_ext:
        fails.append(("external resources", ["CSP blocks external CSS/fonts/images"]))
    if not re.search(r"<title>.*?</title>", src, re.S):
        fails.append(("title", ["no <title> element"]))
    return fails


PROBE = """
<script>
window.addEventListener('load', function () {
  var vw = document.documentElement.clientWidth;
  var out = {viewport: vw, docScrollWidth: document.documentElement.scrollWidth,
             bodyScrollWidth: document.body.scrollWidth, offenders: []};
  document.querySelectorAll('*').forEach(function (el) {
    var r = el.getBoundingClientRect();
    if (r.left + r.width > vw + 1) {
      var cs = getComputedStyle(el);
      if (cs.overflowX === 'auto' || cs.overflowX === 'scroll' || cs.overflowX === 'hidden') return;
      var p = el.parentElement, contained = false;
      while (p) {
        var pc = getComputedStyle(p).overflowX;
        if (pc === 'auto' || pc === 'scroll' || pc === 'hidden') { contained = true; break; }
        p = p.parentElement;
      }
      if (contained) return;
      out.offenders.push((el.tagName.toLowerCase() +
        (typeof el.className === 'string' && el.className
          ? '.' + el.className.trim().split(/\\s+/).join('.') : '')) +
        ' w=' + Math.round(r.width));
    }
  });
  out.offenders = out.offenders.slice(0, 10);
  var pre = document.createElement('pre');
  pre.id = 'probe-out';
  pre.textContent = JSON.stringify(out);
  document.body.insertBefore(pre, document.body.firstChild);
});
</script>
"""


def browser_checks(path, widths=(1280, 900, 500)):
    chrome = find_chrome()
    if not chrome:
        print("\nbrowser checks: SKIPPED (Chrome not found)")
        return []
    src = open(path).read()
    fails = []
    with tempfile.TemporaryDirectory() as td:
        probe_path = os.path.join(td, "probe.html")
        open(probe_path, "w").write(PROBE + src)
        print()
        for w in widths:
            r = subprocess.run(
                [chrome, "--headless", "--disable-gpu", f"--window-size={w},1200",
                 "--virtual-time-budget=6000", "--dump-dom", f"file://{probe_path}"],
                capture_output=True, text=True)
            m = re.search(r'<pre id="probe-out">(.*?)</pre>', r.stdout, re.S)
            if not m:
                print(f"  width {w}: probe did not run")
                continue
            d = json.loads(html.unescape(m.group(1)))
            # Chrome enforces a minimum window width; report what actually rendered
            ok = d["docScrollWidth"] <= d["viewport"] and not d["offenders"]
            print(f"  width {w} (rendered {d['viewport']}): "
                  f"scrollWidth={d['docScrollWidth']} {'OK' if ok else 'OVERFLOW'}")
            if not ok:
                fails.append((f"overflow @{w}", d["offenders"] or
                              [f"docScrollWidth {d['docScrollWidth']} > viewport {d['viewport']}"]))
    return fails


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("page")
    ap.add_argument("--browser", action="store_true", help="also run headless-Chrome layout checks")
    ap.add_argument("--screenshot-dir", help="write light/dark screenshots here")
    a = ap.parse_args()

    fails = static_checks(a.page)
    if a.browser:
        fails += browser_checks(a.page)
    if a.screenshot_dir:
        chrome = find_chrome()
        if chrome:
            os.makedirs(a.screenshot_dir, exist_ok=True)
            for label, extra in (("light", []), ("dark", ["--force-dark-mode",
                                                          "--enable-features=WebContentsForceDark"])):
                out = os.path.join(a.screenshot_dir, f"{label}.png")
                subprocess.run([chrome, "--headless", "--disable-gpu", "--hide-scrollbars",
                                "--window-size=1280,1700", f"--screenshot={out}",
                                "--virtual-time-budget=5000"] + extra +
                               [f"file://{os.path.abspath(a.page)}"], capture_output=True)
            print(f"\nscreenshots -> {a.screenshot_dir}/light.png, dark.png")

    if fails:
        print("\nFAILED:")
        for name, details in fails:
            print(f"  {name}:")
            for d in details:
                print(f"    - {d}")
        sys.exit(1)
    print("\nall checks passed")


if __name__ == "__main__":
    main()
