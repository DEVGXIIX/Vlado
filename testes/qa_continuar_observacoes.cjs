const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
const [origin,output,chrome]=process.argv.slice(2);
(async()=>{
  await fs.mkdir(output,{recursive:true});
  const browser=await chromium.launch({headless:true,...(chrome?{executablePath:chrome}:{})});
  const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
  const errors=[],checks=[];
  page.on('pageerror',e=>errors.push(e.message));
  const row=id=>page.locator('.finding-choice').filter({has:page.locator(`.finding-open[data-achado="${id}"]`)});
  async function count(value){await page.locator('#observacoes-contagem').filter({hasText:value?`${value} ${value===1?'observação selecionada':'observações selecionadas'}`:'Nenhuma observação'}).waitFor({state:'attached'});}
  async function findings(){
    await page.click('#ver-achados');
    await page.locator('#caso option[value="alpha"]').waitFor({state:'attached'});
    await page.selectOption('#caso','alpha'); await page.selectOption('#rodada','R001');
    await page.locator('#achados-revisao option[value="r2"]').waitFor({state:'attached'});
    await page.selectOption('#achados-revisao','r2'); await page.selectOption('#achados-geracao','g2');
    await page.locator('#achados-total').filter({hasText:'12 achado'}).waitFor();
  }
  try {
    await page.goto(origin); await findings();
    assert.equal(await row('A003').locator('.feedback-choice').count(),0,'Sem marcação salva não há seleção.');
    await row('A001').locator('input[type="checkbox"]').check(); await count(1);
    await page.click('#achados-proximo'); await row('A012').locator('input[type="checkbox"]').check(); await count(2);
    await page.click('#achados-anterior'); assert.equal(await row('A001').locator('input').isChecked(),true);
    await page.click('#achados-so-pendentes'); await page.locator('#achados-total').filter({hasText:'9 achado'}).waitFor(); await count(2);
    await page.click('#achados-so-pendentes'); await page.locator('#achados-total').filter({hasText:'12 achado'}).waitFor();
    checks.push('Seleção explícita de marcações salvas permanece entre páginas e filtros; observações não selecionadas ficam de fora.');
    await page.click('#observacoes-continuar'); await page.locator('#codex-observacoes:not([hidden])').waitFor();
    assert.equal(await page.locator('#codex-observacoes .feedback-item').count(),2);
    assert.match(await page.locator('#codex-observacoes').innerText(),/contrato inteiro/);
    assert.equal(await page.evaluate(()=>window.RETORNO_INJETADO),undefined);
    await page.locator('#codex-observacoes .feedback-item details').first().locator('summary').first().click();
    const download=page.waitForEvent('download');
    await page.locator('#codex-observacoes .feedback-source button').first().click();
    assert.match(await fs.readFile(await (await download).path(),'utf8'),/valor 12/);
    assert.equal(await page.locator('#codex-mensagens .codex-round').count(),0,'Prévia não inicia rodada.');
    await page.screenshot({path:path.join(output,'previa-desktop.png'),fullPage:true});
    for(const width of [390,320,736]){
      await page.setViewportSize({width,height:950});
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'overflow '+width);
      if(width===390)await page.screenshot({path:path.join(output,'previa-mobile.png'),fullPage:true});
    }
    await page.setViewportSize({width:1440,height:1000});
    checks.push('Prévia com fontes e download, HTML inerte e layout de 320 a 1440 px; nenhum envio automático.');
    await page.click('#codex-observacoes-remover'); assert.equal(await page.locator('#codex-observacoes').isHidden(),true);
    await page.click('#ver-achados'); await page.click('#observacoes-continuar');
    await page.locator('#codex-observacoes:not([hidden])').waitFor();
    await page.evaluate(async()=>{
      const scope={caso:'alpha',rodada:'R001',revisao:'r2',geracao_achados:'g2',achado_id:'A001'};
      const d=await api('achados-detalhe',scope);
      await api('achados-revisao-salvar',{...scope,achado_versao:d.achado.versao,registros_sha256:d.registros_sha256,
        anterior:d.achado.revisao_humana.evento_id,estado:'precisa_de_ajuste',observacao:'Contrato inteiro, com contexto revisto.'});
    });
    await page.click('#codex-enviar'); await page.locator('#codex-erro').filter({hasText:'marcação mudou'}).waitFor();
    assert.equal(await page.locator('#codex-observacoes').isVisible(),true);
    assert.equal(await page.locator('#codex-mensagens .codex-round').count(),0);
    await page.click('#ver-achados'); await page.click('#achados-buscar');
    await row('A001').locator('input').waitFor(); await count(1);
    await row('A001').locator('input').check(); await count(2);
    await page.click('#observacoes-continuar'); await page.locator('#codex-observacoes').filter({hasText:'contexto revisto'}).waitFor();
    checks.push('Retirar observações é explícito; mudança após prévia bloqueia o envio, preserva o rascunho e exige nova seleção.');
    await page.click('#codex-enviar');
    await page.locator('#codex-status').filter({hasText:'Execução concluída'}).waitFor({timeout:60000});
    assert.equal(await page.locator('#codex-observacoes').isHidden(),true);
    await count(0);
    assert.match(await page.locator('.feedback-history').innerText(),/2 observações/);
    await page.locator('.feedback-history>summary').click();
    assert.match(await page.locator('.feedback-history').innerText(),/Contrato inteiro, com contexto revisto/);
    await page.waitForFunction(()=>Boolean(document.querySelector('#codex-conversa').value));
    const chat=await page.locator('#codex-conversa').inputValue(); assert.ok(chat);
    await page.screenshot({path:path.join(output,'historico-desktop.png'),fullPage:true});
    await page.reload(); await page.click('#ver-codex');
    await page.locator('#codex-caso option[value="alpha"]').waitFor({state:'attached'});
    await page.selectOption('#codex-caso','alpha');
    await page.locator(`#codex-conversa option[value="${chat}"]`).waitFor({state:'attached'});
    await page.selectOption('#codex-conversa',chat);
    await page.locator('.feedback-history').waitFor(); await page.locator('.feedback-history>summary').click();
    assert.match(await page.locator('.feedback-history').innerText(),/Contrato inteiro, com contexto revisto/);
    checks.push('Envio conclui seis etapas, limpa a seleção e conserva as observações no histórico após recarga.');
    await findings(); await row('A001').locator('input').check(); await count(1);
    if(!await page.locator('#achados-versoes').evaluate(el=>el.open))await page.locator('#achados-versoes>summary').click();
    await page.selectOption('#achados-revisao','r1'); await count(0);
    if(!await page.locator('#acervo-escolha').evaluate(el=>el.open))await page.locator('#acervo-escolha>summary').click();
    await page.selectOption('#caso','beta'); await count(0);
    checks.push('Trocar revisão ou apuração limpa a seleção.');
    assert.deepEqual(errors,[]);
    await fs.writeFile(path.join(output,'resultado.json'),JSON.stringify({estado:'ok',natureza:'corpus sintético e app-server simulado; sem inferência real',checks,errors},null,2));
    console.log('QA observações: OK ('+checks.length+' verificações)');
  } catch(error){await page.screenshot({path:path.join(output,'falha.png'),fullPage:true}).catch(()=>{});throw error;}
  finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
