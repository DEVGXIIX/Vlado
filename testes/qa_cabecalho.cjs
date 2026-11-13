'use strict';
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const [origin, output] = process.argv.slice(2);
const spriteRule = 'body>svg:has(>defs>symbol[id^="vditor-icon-"]){position:absolute;width:0;height:0;overflow:hidden;pointer-events:none}';

(async () => {
  const browser = await chromium.launch({headless:true, executablePath:chromium.executablePath()});
  const page = await browser.newPage({viewport:{width:1440,height:1000}});
  const result = {checks:[], layouts:[], errors:[]};
  page.on('pageerror', error => result.errors.push(error.message));
  const geometry = () => page.evaluate(() => {
    const sprite = document.getElementById('vditor-icon-comment').closest('svg');
    return {
      header:document.querySelector('.app-header').getBoundingClientRect().toJSON(),
      sprite:sprite.getBoundingClientRect().toJSON(),
      spritePosition:getComputedStyle(sprite).position,
      scroll:scrollY,
      overflow:document.documentElement.scrollWidth>innerWidth,
      theme:document.documentElement.dataset.theme
    };
  });
  try {
    // Reproduce with the same assets and CSP, removing only the fix being checked.
    const body = await fs.readFile(path.join(__dirname,'../interface/style.css'),'utf8');
    assert.ok(body.includes(spriteRule));
    await page.route('**/style.css', route => route.fulfill({
      status:200,contentType:'text/css; charset=utf-8',body:body.replace(spriteRule,'')
    }));
    const response = await page.goto(origin);
    assert.ok(response.headers()['content-security-policy'].includes("style-src 'self'"));
    assert.ok(!response.headers()['content-security-policy'].includes('unsafe-inline'));
    await page.locator('#area-inicio').waitFor({state:'visible'});
    await page.evaluate(() => document.fonts.ready);
    result.before = await geometry();
    assert.ok(result.before.header.y>=100);
    assert.equal(result.before.sprite.height,150);
    await page.screenshot({path:path.join(output,'antes.png')});
    result.checks.push('Espaço indevido reproduzido com a CSP real: sprite de 150 px no fluxo.');
    await page.unroute('**/style.css');
    await page.reload();
    await page.locator('#area-inicio').waitFor({state:'visible'});

    for (const width of [2301,1440,1024,768,390,320]) {
      await page.setViewportSize({width,height:900});
      for (const theme of ['dark','light']) {
        if (await page.locator('html').getAttribute('data-theme')!==theme) await page.click('#mesa-tema');
        await page.evaluate(() => scrollTo(0,0));
        const initial = await geometry();
        assert.ok(Math.abs(initial.header.y)<1,`Cabeçalho começa em ${initial.header.y}px: ${width}/${theme}`);
        assert.equal(initial.sprite.height,0);
        assert.equal(initial.sprite.width,0);
        assert.equal(initial.spritePosition,'absolute');
        assert.equal(initial.overflow,false);
        await page.evaluate(() => scrollTo(0,350));
        const scrolled = await geometry();
        assert.ok(scrolled.scroll>0);
        assert.ok(Math.abs(scrolled.header.y)<1,`Cabeçalho deslocado após rolagem: ${width}/${theme}`);
        result.layouts.push({width,theme,initial,scrolled});
        if (theme==='dark' && [1440,390].includes(width)) {
          await page.evaluate(() => scrollTo(0,0));
          await page.screenshot({path:path.join(output,`depois-${width}.png`)});
        }
      }
    }
    result.checks.push('Cabeçalho em y=0 antes e depois da rolagem, nos dois temas e em seis larguras; sem transbordamento.');

    await page.setViewportSize({width:1440,height:1000});
    await page.selectOption('#contexto-caso','alpha');
    await page.click('#ver-apuracao');
    await page.locator('#apuracao-nova:not([disabled])').waitFor();
    await page.click('#apuracao-nova');
    const iconReady = await page.waitForFunction(() => {
      const icon = document.querySelector('#apuracao-vditor button[data-type=bold] svg');
      if (!icon) return false;
      const box = icon.getBoundingClientRect();
      const use = icon.querySelector('use');
      return box.width>0 && box.height>0 && use && {
        width:box.width,height:box.height,reference:use.getAttribute('xlink:href') || use.getAttribute('href')
      };
    });
    result.editorIcon = await iconReady.jsonValue();
    assert.ok(result.editorIcon.reference);
    result.checks.push('Ícones do editor continuam visíveis, com definições preservadas.');
    assert.deepEqual(result.errors,[]);
    result.ok = true;
  } catch (error) {
    result.failure = error.stack;
    await page.screenshot({path:path.join(output,'falha.png')});
    throw error;
  } finally {
    await fs.writeFile(path.join(output,'resultado.json'),JSON.stringify(result,null,2));
    console.log(JSON.stringify({ok:result.ok,checks:result.checks,failure:result.failure}));
    await browser.close();
  }
})().catch(error => {console.error(error);process.exitCode=1;});
