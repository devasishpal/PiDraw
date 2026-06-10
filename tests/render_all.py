"""Render all diagram files in pidraw_test dir."""
import glob
import os
from pathlib import Path

from pidraw import render_file
from pidraw.backend.png import svg_to_png

out = Path(r"C:\Users\Alok\Desktop\pidraw_test")
os.chdir(str(out))

files = sorted(glob.glob("*.mmd") + glob.glob("*.puml") + glob.glob("*.dot") +
               glob.glob("*.d2") + glob.glob("*.txt") + glob.glob("*.md") +
               glob.glob("*.noml") + glob.glob("*.json") + glob.glob("*.dsl") +
               glob.glob("*.bpmn") + glob.glob("*.tex"))

print(f"Found {len(files)} diagram files\n")

for f in files:
    name = Path(f).stem
    try:
        result = render_file(str(out / f))
        svg = result.svg

        if not svg or len(svg) < 100:
            print(f"  {name}: SKIPPED (SVG too small: {len(svg) if svg else 0} chars)")
            continue

        svg_path = out / f"{name}.svg"
        png_path = out / f"{name}.png"
        svg_path.write_text(svg, encoding="utf-8")

        try:
            png = svg_to_png(svg, transparent=True, trim=True)
            png_path.write_bytes(png)
            png_ok = f"PNG {len(png)}b"
        except Exception:
            try:
                png = svg_to_png(svg, transparent=False, trim=False)
                png_path.write_bytes(png)
                png_ok = f"PNG (fallback) {len(png)}b"
            except Exception as e2:
                png_ok = f"PNG FAILED: {e2}"

        print(f"  {name:25s} SVG {len(svg):>5}b  {png_ok}")

    except Exception as e:
        print(f"  {name:25s} ERROR: {e}")
