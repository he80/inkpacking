"""Smoke test: runs inkpacking.py against a matrix of parameter combos that
exercise every branch in effect() (all top/bottom schemes, finger slots,
mirrored flaps, independent top/bottom dust flap settings) and checks each
run exits cleanly and produces well-formed SVG with actual path geometry
in it.

This is what would have caught the extension silently breaking under
Inkscape 1.x / Python 3 in the first place -- run it locally with:

    pip install inkex
    python tests/run_variants.py

CI runs this on every push and PR (see .github/workflows/smoke-test.yml).
"""
import os
import subprocess
import sys
import tempfile

from lxml import etree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NS = {"svg": "http://www.w3.org/2000/svg"}

TEST_SVG = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:svg="http://www.w3.org/2000/svg"
     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
     width="210mm" height="297mm" viewBox="0 0 210 297" version="1.1" id="svg1">
  <g inkscape:groupmode="layer" id="layer1" inkscape:label="Layer 1"/>
</svg>
"""

BASE = dict(
    width=40, height=80, depth=30, unit="mm", **{"paper-thickness": 0.5},
    topscheme="rwlf", botscheme="rwlf",
    **{"tab-proportion": 14}, lockroundradius=18,
    clueflapsize=13, clueflapangle=12, clueflapside="false",
    tfal="true", bfal="true", hotmeltprop=0.6,
    fingergrepa="false", fingergrepb="false", fingergrepr=5,
    usetop="true",
    glueflapinoff=0, glueflapin45=2, glueflapinang=7,
    glueflapouoff=3, glueflapou45=3, glueflapouang=12,
    bglueflapinoff=0, bglueflapin45=2, bglueflapinang=7,
    bglueflapouoff=3, bglueflapou45=3, bglueflapouang=12,
    roto=0,
)


def variant(name, **overrides):
    d = dict(BASE)
    d.update(overrides)
    return name, d


VARIANTS = [
    variant("default"),
    variant("notop_nobottom", topscheme="notp", botscheme="nobt"),
    variant("flat_lockflap", topscheme="fwlf", botscheme="fwlf"),
    variant("flat_lockflap_altflap", topscheme="fwlf", botscheme="fwlf", tfal="false", bfal="false"),
    variant("hotmelt", topscheme="fwnf", botscheme="fwnf"),
    variant("hotmelt_altflap", topscheme="fwnf", botscheme="fwnf", tfal="false", bfal="false"),
    variant("fingergrep_a", fingergrepa="true"),
    variant("fingergrep_b", fingergrepb="true"),
    variant("fingergrep_ab", fingergrepa="true", fingergrepb="true"),
    variant("mirror_side_flap", clueflapside="true"),
    variant("independent_bottom_flaps", usetop="false",
            bglueflapinoff=1, bglueflapin45=4, bglueflapinang=15,
            bglueflapouoff=1, bglueflapou45=1, bglueflapouang=20),
    variant("tuck_lid", topscheme="tuck", botscheme="rwlf"),
    variant("tuck_lid_altflap", topscheme="tuck", botscheme="rwlf", tfal="false"),
    variant("autolock_bottom", topscheme="notp", botscheme="auto"),
    variant("autolock_bottom_altflap", topscheme="notp", botscheme="auto", bfal="false"),
    variant("fefco_0215", fefcostyle="fefco0215"),
    variant("fefco_0216", fefcostyle="fefco0216"),
    variant("fefco_0414", fefcostyle="fefco0414"),
    variant("fefco_0427", fefcostyle="fefco0427"),
]


def main():
    with tempfile.TemporaryDirectory() as tmp:
        test_svg = os.path.join(tmp, "test.svg")
        with open(test_svg, "w", encoding="utf-8") as f:
            f.write(TEST_SVG)

        ok = True
        for name, params in VARIANTS:
            args = [sys.executable, os.path.join(ROOT, "inkpacking.py")]
            for k, v in params.items():
                args.append(f"--{k}={v}")
            args.append(test_svg)
            proc = subprocess.run(args, capture_output=True, text=True)
            if proc.returncode != 0:
                print(f"[FAIL] {name}: exit {proc.returncode}\n{proc.stderr}")
                ok = False
                continue
            try:
                root = etree.fromstring(proc.stdout.encode("utf-8"))
            except etree.XMLSyntaxError as e:
                print(f"[FAIL] {name}: invalid XML output ({e})")
                ok = False
                continue
            paths = root.findall(".//svg:path", NS)
            if not paths:
                print(f"[FAIL] {name}: no <path> elements in output")
                ok = False
                continue
            print(f"[OK] {name}: {len(paths)} paths")

        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
