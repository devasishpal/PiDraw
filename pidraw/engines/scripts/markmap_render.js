const path = require('path');
const fs = require('fs');
const { execSync } = require('child_process');

const globalDir = path.join(process.env.APPDATA || '', 'npm', 'node_modules');
const { chromium } = require(path.join(globalDir, 'playwright'));

async function main() {
  const inputFile = path.resolve(process.argv[2]);
  const outputFile = path.resolve(process.argv[3]);
  const tmpHtml = path.join(path.dirname(outputFile), '_mmap_render.html');

  // Generate offline HTML with markmap (assets inlined)
  execSync(`markmap "${inputFile}" -o "${tmpHtml}" --no-open --offline`, { stdio: 'pipe' });

  // Launch headless Chromium and open the HTML
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1200, height: 800 } });
  await page.goto('file://' + tmpHtml.replace(/\\/g, '/'));

  // Wait for D3/markmap JS to render SVG elements inside #mindmap
  await page.waitForFunction(() => {
    const el = document.getElementById('mindmap');
    return el && el.querySelectorAll('path, text, g, circle').length > 5;
  }, { timeout: 15000 });

  const svg = await page.evaluate(() => {
    const el = document.getElementById('mindmap');
    return el ? el.outerHTML : '';
  });
  await browser.close();
  try { fs.unlinkSync(tmpHtml); } catch {}

  if (!svg || svg.length < 200) throw new Error('No SVG content rendered');
  fs.writeFileSync(outputFile, svg, 'utf-8');
}

main().catch(e => { console.error(e.message); process.exit(1); });
