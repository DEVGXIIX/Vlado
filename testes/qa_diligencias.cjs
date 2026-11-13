const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
const [origin,output,chrome,chat]=process.argv.slice(2);
(async()=>{
  await fs.mkdir(output,{recursive:true});
  const browser=await chromium.launch({headless:true,...(chrome?{executablePath:chrome}:{})});
  const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
  const errors=[],checks=[];page.on('pageerror',error=>errors.push(error.message));
  const entry=()=>page.locator('.diligence-entry').filter({has:page.getByRole('heading',{name:'Solicitar ordem bancária',exact:true})});
  async function listed(count){await page.waitForFunction(n=>document.querySelectorAll('#diligencias-resultados .diligence-entry').length===n,count);}
  try{
    await page.goto(origin);await page.click('#ver-achados');
    await page.locator('#caso option[value="alpha"]').waitFor({state:'attached'});await page.selectOption('#caso','alpha');await page.selectOption('#rodada','R001');
    await page.locator('#achados-revisao option[value="r3_sintese"]').waitFor({state:'attached'});await page.selectOption('#achados-revisao','r3_sintese');
    await page.locator('#achados-geracao option[value="g1"]').waitFor({state:'attached'});await page.selectOption('#achados-geracao','g1');
    await page.locator('.finding-open').first().click();
    await page.locator('#achados-inspecao').getByRole('button',{name:'Ver briefing e referências'}).click();
    await page.locator('#achados-briefing-painel .briefing-text button').first().click();
    await page.locator('#achados-detalhe-painel').getByRole('button',{name:'Criar diligência',exact:true}).click();
    await page.fill('#diligencias-acao','Solicitar ordem bancária');await page.fill('#diligencias-responsavel','Repórter A');await page.fill('#diligencias-autor','Editora A');await page.fill('#diligencias-prazo','2026-12-10');
    await page.click('#diligencias-salvar');await page.locator('#diligencias-dialogo').waitFor({state:'hidden'});await listed(1);
    assert.match(await entry().innerText(),/Origem: achado da IA/);assert.match(await entry().innerText(),/solicitar/i);
    checks.push('Criação a partir de uma referência do briefing preserva o achado e sua versão; responsável e prazo são declarados.');
    await entry().getByRole('button',{name:'Assumir / atualizar'}).click();await page.fill('#diligencias-responsavel','Repórter B');await page.selectOption('#diligencias-estado','aguardando_resposta');await page.fill('#diligencias-autor','Repórter B');await page.fill('#diligencias-observacao','Solicitação enviada pelo jornalista fora da Mesa.');await page.click('#diligencias-salvar');await page.locator('#diligencias-dialogo').waitFor({state:'hidden'});
    await entry().getByText('Responsável declarado: Repórter B',{exact:false}).first().waitFor();
    await entry().getByText('Histórico de responsáveis e estados',{exact:true}).click();assert.match(await entry().innerText(),/Repórter A/);assert.match(await entry().innerText(),/Repórter B/);
    await page.fill('#diligencias-responsavel-filtro','Outra pessoa');await page.click('#diligencias-buscar');await listed(0);await page.fill('#diligencias-responsavel-filtro','');await page.click('#diligencias-buscar');await listed(1);
    checks.push('Atribuição, estado, prazo e justificativa têm histórico; filtros mostram apenas os responsáveis selecionados.');
    await entry().getByRole('button',{name:'Anexar resposta',exact:true}).click();await page.locator('#diligencias-vincular:not([disabled])').waitFor();
    await page.setInputFiles('#diligencias-arquivos',{name:'resposta_assessoria.txt',mimeType:'text/plain',buffer:Buffer.from('Contrato adicional. Valor total 246. Resposta da assessoria em material sintético.')});
    await page.click('#diligencias-cadastrar');await page.locator('#diligencias-recibo').filter({hasText:'1 recebidos'}).waitFor();await page.locator('#diligencias-vincular:not([disabled])').waitFor();
    assert.equal(await page.locator('#diligencias-documentos input:checked').count(),1);
    await page.fill('#diligencias-resposta-autor','Editora C');await page.fill('#diligencias-resposta-nota','RESPOSTA_DILIGENCIA_BROWSER: conferir a declaração e o alcance. <script>window.DILIGENCIA_INJETADA=true</script>');await page.click('#diligencias-vincular');await page.locator('#diligencias-resposta-dialogo').waitFor({state:'hidden'});
    await entry().getByRole('heading',{name:'Resposta recebida',exact:true}).waitFor();assert.equal(await page.evaluate(()=>window.DILIGENCIA_INJETADA),undefined);
    const [downloaded]=await Promise.all([page.waitForEvent('download'),entry().getByRole('button',{name:/^Baixar resposta/i}).click()]);assert.match(await fs.readFile(await downloaded.path(),'utf8'),/246/);
    checks.push('Resposta é cadastrada com recibo antes do vínculo, pode ser baixada e marca recebimento sem concluir automaticamente a diligência; HTML permanece inerte.');
    await page.selectOption('#diligencias-conversa',chat);await entry().getByRole('button',{name:'Retomar esta questão'}).click();await page.locator('#diligencias-erro').filter({hasText:'Continuar com novos documentos'}).waitFor();
    await page.check('#diligencias-incorporar');await entry().getByRole('button',{name:'Retomar esta questão'}).click();
    await page.locator('#codex-diligencias:not([hidden])').waitFor();await page.locator('#codex-corpus-novo:not([hidden])').waitFor();assert.match(await page.locator('#codex-diligencias').innerText(),/RESPOSTA_DILIGENCIA_BROWSER/);
    await page.click('#codex-diligencias-retirar');assert.equal(await page.locator('#codex-diligencias').isHidden(),true);
    await page.click('#ver-diligencias');await listed(1);await entry().getByRole('button',{name:'Retomar esta questão'}).click();await page.locator('#codex-diligencias:not([hidden])').waitFor();
    await page.click('#codex-enviar');await page.waitForFunction(()=>document.querySelectorAll('.codex-round').length===2,null,{timeout:90000});await page.locator('#codex-status').filter({hasText:'Execução concluída'}).waitFor({timeout:90000});assert.equal(await page.locator('.codex-round').count(),2);
    await page.locator('.feedback-history>summary').filter({hasText:'Diligências humanas'}).click();assert.match(await page.locator('.feedback-history').filter({hasText:'Diligências humanas'}).innerText(),/Solicitar ordem bancária/);
    checks.push('Retomada exige adoção explícita da nova versão; prévia pode ser retirada; pergunta executa sete etapas simuladas na mesma conversa com recibo e histórico.');
    await page.click('#ver-diligencias');await listed(1);await page.screenshot({path:path.join(output,'diligencias-desktop.png'),fullPage:true});
    for(const width of [390,320,736,1440]){await page.setViewportSize({width,height:950});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'overflow '+width);if(width===390)await page.screenshot({path:path.join(output,'diligencias-mobile.png'),fullPage:true});}
    await page.reload();await page.click('#ver-diligencias');await page.locator('#diligencias-caso option[value="alpha"]').waitFor({state:'attached'});await page.selectOption('#diligencias-caso','alpha');await listed(1);assert.match(await entry().innerText(),/Resposta recebida/);
    await page.selectOption('#diligencias-caso','beta');await page.locator('#diligencias-status').filter({hasText:'Nenhuma diligência'}).waitFor();await listed(0);
    checks.push('Histórico e respostas persistem após recarga, isolados por apuração, com layout de 320 a 1440 px.');
    await page.click('#ver-caderno');await page.locator('#caderno-caso option[value="alpha"]').waitFor({state:'attached'});await page.selectOption('#caderno-caso','alpha');await page.locator('#caderno-novo:not([disabled])').waitFor();await page.click('#caderno-novo');await page.locator('#caderno-salvar:not([disabled])').waitFor();
    await page.fill('#caderno-trecho','Valor 123.');await page.fill('#caderno-localizador','Linha 1');await page.fill('#caderno-autor','Repórter D');await page.click('#caderno-salvar');await page.locator('#caderno-dialogo').waitFor({state:'hidden'});
    await page.locator('#caderno-resultados').getByRole('button',{name:'Criar diligência'}).click();await page.fill('#diligencias-acao','Conferir escopo do valor');await page.fill('#diligencias-responsavel','Repórter D');await page.fill('#diligencias-autor','Repórter D');await page.click('#diligencias-salvar');await page.locator('#diligencias-dialogo').waitFor({state:'hidden'});await listed(2);
    checks.push('Registro do caderno também pode originar diligência com autoria humana preservada.');
    assert.deepEqual(errors,[]);await fs.writeFile(path.join(output,'resultado.json'),JSON.stringify({estado:'ok',natureza:'fontes e ações humanas sintéticas; runtime simulado, sem inferência real ou envio de solicitações',checks,errors},null,2));console.log('QA diligências: OK ('+checks.length+' verificações)');
  }catch(error){await page.screenshot({path:path.join(output,'falha.png'),fullPage:true}).catch(()=>{});await fs.writeFile(path.join(output,'falha.json'),JSON.stringify({erro:String(error),errors},null,2));throw error;}
  finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
