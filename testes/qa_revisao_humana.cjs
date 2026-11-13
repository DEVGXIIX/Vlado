const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const [origin, output, chrome] = process.argv.slice(2);
(async () => {
  await fs.mkdir(output, {recursive:true});
  const browser = await chromium.launch({headless:true, ...(chrome ? {executablePath:chrome} : {})});
  const page = await browser.newPage({viewport:{width:1440,height:1000}, acceptDownloads:true});
  const errors = [], checks = [];
  page.on('pageerror', error => errors.push(error.message));
  async function scope(revision = 'r2', generation = 'g2') {
    if (!await page.locator('#achados-versoes').evaluate(el => el.open)) await page.locator('#achados-versoes>summary').click();
    await page.selectOption('#achados-revisao', revision);
    await page.selectOption('#achados-geracao', generation);
    await page.locator('#achados-total').filter({hasText:'12 achado'}).waitFor();
  }
  const row = id => page.locator('#achados-resultados .finding-choice').filter({has:page.locator(`.finding-open[data-achado="${id}"]`)});
  async function open(id) {
    await row(id).locator('.human-review-actions button').click();
    await page.locator('#revisao-dialogo[open]').waitFor();
    await page.locator('#revisao-salvar:not([disabled])').waitFor();
  }
  async function save(state, note, count) {
    await page.selectOption('#revisao-estado', state);
    await page.fill('#revisao-observacao', note);
    await page.click('#revisao-salvar');
    await page.locator('#revisao-dialogo').waitFor({state:'hidden'});
    await page.locator('#achados-progresso-texto').filter({hasText:`${count} de 12`}).waitFor();
    await page.locator('#achados-revisao-feedback').filter({hasText:'Marcação salva'}).waitFor();
  }
  try {
    await page.goto(origin); await page.click('#ver-achados');
    await page.locator('#caso option[value="alpha"]').waitFor({state:'attached'});
    await page.selectOption('#caso','alpha'); await page.selectOption('#rodada','R001');
    await page.locator('#achados-revisao option[value="r2"]').waitFor({state:'attached'});
    await scope();
    await page.locator('#achados-progresso-texto').filter({hasText:'0 de 12'}).waitFor();
    assert.equal(await page.locator('#achados-resultados .human-review-badge').count(),10);
    assert.equal(await row('A001').locator('.human-review-badge').innerText(),'Pendente');
    const originalText = await row('A001').locator('.claim-title').innerText();
    await open('A001');
    assert.equal(await page.locator('.review-evidence').count(),3);
    assert.match(await page.locator('#revisao-fontes').innerText(),/A fonte declara valor 12/);
    assert.match(await page.locator('#revisao-fontes').innerText(),/Outra versão declara valor 14/);
    assert.equal(await page.locator('#revisao-estado').inputValue(),'pendente');
    const download = page.waitForEvent('download');
    await page.locator('.review-evidence button').first().click();
    assert.match(await fs.readFile(await (await download).path(),'utf8'),/valor 12/);
    await page.screenshot({path:path.join(output,'conferir-desktop.png')});
    await save('precisa_de_ajuste','Valor correto, mas refere-se ao total do contrato.',1);
    assert.equal(await row('A001').locator('.claim-title').innerText(),originalText);
    assert.equal(await row('A001').locator('.human-review-badge').innerText(),'Precisa de ajuste');
    checks.push('Conferir abre trechos/contextos e original; salvar avaliação explícita preserva a afirmação da IA.');
    await open('A002');
    assert.equal(await page.locator('#revisao-estado option[value="conferida_no_original"]').evaluate(el=>el.disabled),true);
    await save('sem_suporte_suficiente','Sem evidência de pagamento.',2);
    await page.click('#achados-so-pendentes');
    await page.locator('#achados-total').filter({hasText:'10 achado'}).waitFor();
    assert.equal(await row('A001').count(),0);
    assert.equal(await row('A002').count(),0);
    await open('A003');
    await save('sem_suporte_suficiente','Não há fonte vinculada.',3);
    await page.locator('#achados-total').filter({hasText:'9 achado'}).waitFor();
    assert.equal(await row('A003').count(),0);
    assert.equal(await page.locator('#achados-so-pendentes').getAttribute('aria-pressed'),'true');
    checks.push('Só pendentes filtra a seleção inteira; achado revisado sai da lista e progresso permanece global.');
    await page.click('#achados-so-pendentes');
    await page.locator('#achados-total').filter({hasText:'12 achado'}).waitFor();
    await open('A001');
    assert.equal(await page.locator('#revisao-observacao').inputValue(),'Valor correto, mas refere-se ao total do contrato.');
    const note = '<script>window.INJETADO_REVISAO=true</script> Observação literal do teste.';
    await save('conferida_no_original', note,3);
    assert.equal(await page.evaluate(() => window.INJETADO_REVISAO),undefined);
    assert.equal(await row('A001').locator('.human-review-badge').innerText(),'Conferida no original');
    const exported = page.waitForEvent('download'); await page.click('#achados-exportar');
    const content = JSON.parse(await fs.readFile(await (await exported).path(),'utf8'));
    assert.equal(content.resultados.length,12);
    assert.equal(content.resultados[0].revisao_humana.observacao,note);
    assert.equal(content.resultados[0].revisao_humana.historico.length,2);
    assert.equal(content.resultados[0].redacao,originalText);
    assert.equal(content.resultados[0].conferencia_humana,'nao_realizada');
    checks.push('Exportação integral inclui quatro estados, observações e histórico separados; HTML da observação é inerte.');
    await open('A001');
    await page.route('**/api/achados-revisao-salvar', route => route.fulfill({status:400,contentType:'application/json',body:JSON.stringify({erro:'A marcação foi alterada em outra janela.'})}));
    await page.fill('#revisao-observacao','Rascunho que deve ser preservado.'); await page.click('#revisao-salvar');
    await page.locator('#revisao-erro').filter({hasText:'outra janela'}).waitFor();
    assert.equal(await page.locator('#revisao-observacao').inputValue(),'Rascunho que deve ser preservado.');
    await page.unroute('**/api/achados-revisao-salvar');
    await save('pendente','Revisitar a conferência.',2);
    checks.push('Falha ao salvar mantém o rascunho; retorno a Pendente atualiza progresso sem apagar histórico.');
    await page.reload(); await page.click('#ver-achados');
    await page.locator('#caso option[value="alpha"]').waitFor({state:'attached'});
    await page.selectOption('#caso','alpha'); await page.selectOption('#rodada','R001');
    await page.locator('#achados-revisao option[value="r2"]').waitFor({state:'attached'}); await scope();
    await page.locator('#achados-progresso-texto').filter({hasText:'2 de 12'}).waitFor();
    await open('A001');
    assert.equal(await page.locator('#revisao-observacao').inputValue(),'Revisitar a conferência.');
    for (const width of [390,320,736,1440]) {
      await page.setViewportSize({width,height:950});
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth<=innerWidth),true,'overflow page '+width);
      assert.equal(await page.locator('#revisao-dialogo').evaluate(el => el.scrollWidth<=el.clientWidth),true,'overflow dialog '+width);
      if (width===390) await page.screenshot({path:path.join(output,'conferir-mobile.png')});
    }
    await page.click('#revisao-fechar');
    await page.screenshot({path:path.join(output,'progresso-desktop.png'),fullPage:true});
    await scope('r1','g1');
    await page.locator('#achados-progresso-texto').filter({hasText:'0 de 12'}).waitFor();
    checks.push('Marcações persistem após recarga; outra revisão permanece pendente; desktop/celular sem transbordamento.');
    assert.deepEqual(errors,[]);
    await fs.writeFile(path.join(output,'resultado.json'),JSON.stringify({estado:'ok',natureza:'registros sintéticos, marcações explícitas de teste; sem inferência',checks,errors},null,2));
    console.log('QA revisão humana: OK ('+checks.length+' verificações)');
  } catch(error) {
    await page.screenshot({path:path.join(output,'falha.png'),fullPage:true}).catch(()=>{}); throw error;
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
