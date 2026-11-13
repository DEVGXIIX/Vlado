const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
const [origin,output,chrome,chat]=process.argv.slice(2);
(async()=>{
  await fs.mkdir(output,{recursive:true});
  const browser=await chromium.launch({headless:true,...(chrome?{executablePath:chrome}:{})});
  const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
  const errors=[],checks=[],assets=[],consoleErrors=[];page.on('pageerror',e=>errors.push(e.message));
  page.on('requestfailed',request=>assets.push({url:request.url(),erro:request.failure()?.errorText}));
  page.on('response',response=>{if(/\.js$/.test(response.url()))assets.push({url:response.url(),status:response.status(),tipo:response.headers()['content-type']});});
  page.on('console',message=>{if(message.type()==='error')consoleErrors.push(message.text());});
  async function open(){await page.click('#codex-continuar-documentos');await page.locator('#continuidade-dialogo[open]').waitFor();}
  async function prepared(){await page.locator('#continuidade-usar:not([disabled])').waitFor();}
  try{
    await page.goto(origin);
    for(let n=0;n<Number(process.env.APURACAO_QA_RECARREGAS||0);n++){
      await page.reload();assert.equal(await page.evaluate(()=>typeof window.continuarComCaderno),'function',`Scripts após recarga ${n+1}`);
    }
    await page.click('#ver-codex');
    await page.locator('#codex-caso option[value="alpha"]').waitFor({state:'attached'});await page.selectOption('#codex-caso','alpha');
    await page.locator(`#codex-conversa option[value="${chat}"]`).waitFor({state:'attached'});await page.selectOption('#codex-conversa',chat);
    await page.locator('#codex-status').filter({hasText:'Execução concluída'}).waitFor();
    await open();
    await page.setInputFiles('#continuidade-arquivos',{name:'assessoria.txt',mimeType:'text/plain',buffer:Buffer.from('Contrato adicional. Valor total 246. <script>window.CONTINUIDADE_INJETADA=true</script>')});
    await page.selectOption('#continuidade-natureza','sinteticos');await page.click('#continuidade-cadastrar');await prepared();
    assert.match(await page.locator('#continuidade-recibo').innerText(),/1 recebidos · 1 novos · 0 duplicados/);
    assert.match(await page.locator('#continuidade-previa').innerText(),/assessoria/);
    assert.equal(await page.locator('.codex-round').count(),1,'Cadastro não cria nova rodada.');
    await page.screenshot({path:path.join(output,'cadastro-desktop.png'),fullPage:true});
    await page.click('#continuidade-usar');await page.locator('#continuidade-dialogo').waitFor({state:'hidden'});
    await page.locator('#codex-corpus-novo:not([hidden])').waitFor();
    await page.click('#codex-corpus-retirar');assert.equal(await page.locator('#codex-corpus-novo').isHidden(),true);
    await open();await page.click('#continuidade-atualizar');await prepared();await page.click('#continuidade-usar');
    checks.push('Cadastro imediato com recibo e prévia, sem rodada; retirar da pergunta preserva os arquivos e permite selecioná-los novamente.');
    await page.evaluate(async()=>api('cadastrar',{caso:'alpha',natureza:'sinteticos',arquivos:[{nome:'outro.txt',base64:btoa('Documento posterior sem leitura na rodada de teste.')}]}));
    await page.click('#codex-enviar');await page.locator('#codex-erro').filter({hasText:'mudou desde a prévia'}).waitFor();
    assert.equal(await page.locator('.codex-round').count(),1);
    assert.equal(await page.locator('#codex-corpus-novo').isVisible(),true);
    await open();await page.click('#continuidade-atualizar');await prepared();
    assert.match(await page.locator('#continuidade-previa').innerText(),/2 documentos novos/);
    await page.click('#continuidade-usar');await page.click('#codex-enviar');
    await page.locator('#codex-status').filter({hasText:'Execução concluída'}).waitFor({timeout:60000});
    await page.locator('.corpus-comparison').waitFor();
    assert.equal(await page.locator('.codex-round').count(),2);
    const comparison=page.locator('.corpus-comparison');
    for(const title of ['Evidências novas','Conclusões alteradas','Pendências respondidas','Achados para nova conferência'])assert.match(await comparison.innerText(),new RegExp(title));
    assert.match(await comparison.innerText(),/123/);assert.match(await comparison.innerText(),/246/);
    assert.match(await comparison.innerText(),/sem leitura registrada/);
    assert.equal(await page.evaluate(()=>window.CONTINUIDADE_INJETADA),undefined);
    assert.equal(await page.locator('#codex-corpus-novo').isHidden(),true);
    const exported=page.waitForEvent('download');await comparison.getByRole('button',{name:'Exportar comparativo · JSON'}).click();
    const data=JSON.parse(await fs.readFile(await(await exported).path(),'utf8'));
    assert.equal(data.rodada_anterior,'R001');assert.equal(data.rodada_atual,'R002');
    assert.equal(data.corpus_anterior,'alpha_v1');assert.equal(data.corpus_atual,'alpha_v3');
    assert.equal(data.comparacoes[0].tipo,'alterada');assert.deepEqual(data.documentos_novos_sem_leitura_registrada,['D003']);
    checks.push('Mudança após prévia bloqueia envio; nova conferência conclui sete etapas na mesma conversa, com comparativo exportável e lacunas explícitas.');
    await page.screenshot({path:path.join(output,'comparativo-desktop.png'),fullPage:true});
    for(const width of [390,320,736,1440]){await page.setViewportSize({width,height:950});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'overflow '+width);if(width===390)await page.screenshot({path:path.join(output,'comparativo-mobile.png'),fullPage:true});}
    const review=comparison.locator('.comparison-section').filter({has:page.getByRole('heading',{name:'Achados para nova conferência',exact:true})});
    await review.getByRole('button',{name:'Ver achado e fontes'}).first().click();
    await page.locator('#achados-inspecao').filter({hasText:'246'}).waitFor();
    assert.match(await page.locator('#achados-inspecao').innerText(),/Pendente/);
    checks.push('Achado alterado abre fontes da nova rodada e começa Pendente; conferência antiga não é herdada. Desktop e celular sem transbordamento.');
    await page.reload();await page.click('#ver-codex');
    await page.locator('#codex-caso option[value="alpha"]').waitFor({state:'attached'});await page.selectOption('#codex-caso','alpha');
    await page.locator(`#codex-conversa option[value="${chat}"]`).waitFor({state:'attached'});await page.selectOption('#codex-conversa',chat);
    await page.locator('.corpus-comparison').waitFor();assert.equal(await page.locator('.codex-round').count(),2);
    checks.push('Histórico e comparativo persistem após recarga, mantendo as duas rodadas na mesma conversa.');
    assert.deepEqual(errors,[]);
    await fs.writeFile(path.join(output,'resultado.json'),JSON.stringify({estado:'ok',natureza:'documentos sintéticos e app-server simulado; sem inferência real',checks,errors},null,2));
    console.log('QA continuidade: OK ('+checks.length+' verificações)');
  }catch(error){await page.screenshot({path:path.join(output,'falha.png'),fullPage:true}).catch(()=>{});await fs.writeFile(path.join(output,'falha.json'),JSON.stringify({erro:String(error),errors,assets,consoleErrors},null,2));throw error;}
  finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
