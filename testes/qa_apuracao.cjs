// Isolated synthetic browser checks. No login, external navigation or inference.
const {chromium}=require('playwright');
const fs=require('node:fs/promises');
const path=require('node:path');
const assert=require('node:assert/strict');
const editor=require('./editor_notas.cjs');
const [origin,output,phase,chrome]=process.argv.slice(2);
(async()=>{
  const browser=await chromium.launch({headless:true,...(chrome?{executablePath:chrome}:{})});
  const page=await browser.newPage({viewport:{width:1440,height:1100},acceptDownloads:true});
  const errors=[],checks=[],external=[],missing=[];const push=checks.push.bind(checks);checks.push=(...items)=>{console.log(items.join('\n'));return push(...items);};page.on('pageerror',e=>{errors.push(e.stack||e.message);console.log('PAGEERROR',e.stack||e.message);});
  page.on('request',r=>{if(!r.url().startsWith(origin)&&!r.url().startsWith('blob:'))external.push(r.url());});
  page.on('response',r=>{if(r.url().includes('/vendor/')&&r.status()!==200)missing.push(r.url());});
  async function saved(){await page.locator('#apuracao-status').filter({hasText:'Nota salva.'}).waitFor();await page.locator('#apuracao-salvar:enabled').waitFor();}
  async function add(){await page.locator('#apuracao-adicionar-salvar:enabled').waitFor();await page.click('#apuracao-adicionar-salvar');await page.locator('#apuracao-adicionar-dialogo').waitFor({state:'hidden'});await page.click('#ver-apuracao');await page.locator('#area-apuracao:not([hidden])').waitFor();}
  async function selectText(locator,text){await locator.evaluate((el,text)=>{const walker=document.createTreeWalker(el,NodeFilter.SHOW_TEXT);while(walker.nextNode()){const node=walker.currentNode,index=node.textContent.indexOf(text);if(index>=0){const range=document.createRange();range.setStart(node,index);range.setEnd(node,index+text.length);const selection=getSelection();selection.removeAllRanges();selection.addRange(range);return;}}throw Error('Selection missing');},text);}
  try{
    await page.goto(origin);
    await page.click('#ver-apuracao');await page.locator('#contexto-caso option[value="alpha"]').waitFor({state:'attached'});await page.selectOption('#contexto-caso','alpha');await page.locator('#apuracao-nova:enabled').waitFor();
    if(phase==='reinicio'){
      assert.equal(await page.locator('#apuracao-notas button').count(),2);
      await page.locator('#apuracao-notas button').filter({hasText:'Nota da repórter'}).click();
      assert.match(await page.locator('#apuracao-texto').inputValue(),/valor 12\./);
      assert.equal(await page.locator('#apuracao-fontes .notebook-source').count(),2);
      assert.match(await page.locator('#apuracao-fontes').innerText(),/página PDF 1/);
      checks.push('Servidor sintético encerrado e reiniciado: notas e referências reaparecem do disco.');
    }else{
      await page.click('#apuracao-nova');await page.fill('#apuracao-nota-titulo','Nota da repórter');
      await editor.write(page,'# Hipótese\n\n**Negrito** e *itálico*\n- item\n> citação\n[link](https://example.org)\n<script>window.NOTA_INJETADA=true</script>');
      assert.equal(await page.locator('#apuracao-previa strong').textContent(),'Negrito');assert.equal(await page.locator('#apuracao-previa em').textContent(),'itálico');
      assert.equal(await page.locator('#apuracao-previa script').count(),0);
      await page.click('#apuracao-salvar');await saved();
      await page.reload();await page.click('#ver-apuracao');await page.locator('#contexto-caso option[value="alpha"]').waitFor({state:'attached'});await page.selectOption('#contexto-caso','alpha');await page.locator('#apuracao-vditor .vditor-toolbar').waitFor();assert.match(await page.locator('#apuracao-texto').inputValue(),/Hipótese/);
      await editor.mode(page,'wysiwyg');assert.equal(await page.locator('#apuracao-vditor .vditor-wysiwyg strong').innerText(),'Negrito');await editor.mode(page,'ir');await page.locator('#apuracao-vditor .vditor-ir .vditor-reset').waitFor();await editor.mode(page,'sv');await page.click('#apuracao-salvar');await saved();
      checks.push('Criar, salvar, recarregar e reabrir nota; Vditor visual, instantâneo e Markdown preservam texto e formatação.');
      // Second tab conflict must preserve the local unsaved text.
      const second=await browser.newPage();await second.goto(origin);await second.click('#ver-apuracao');await second.locator('#contexto-caso option[value="alpha"]').waitFor({state:'attached'});await second.selectOption('#contexto-caso','alpha');await second.locator('#apuracao-vditor .vditor-toolbar').waitFor();await editor.write(second,'Versão salva na segunda janela.');await second.click('#apuracao-salvar');await second.locator('#apuracao-status').filter({hasText:'Nota salva.'}).waitFor();
      await editor.write(page,'Meu rascunho preservado.');await page.click('#apuracao-salvar');await page.locator('#apuracao-erro').filter({hasText:'outra janela'}).waitFor();assert.equal((await editor.read(page)).trim(),'Meu rascunho preservado.');
      page.once('dialog',d=>d.accept());await page.click('#apuracao-atualizar');await page.locator('#apuracao-vditor .vditor-toolbar').waitFor();await page.waitForFunction(()=>document.querySelector('#apuracao-texto').value.trim()==='Versão salva na segunda janela.');await second.close();
      checks.push('Conflito entre janelas é recusado e preserva o rascunho na tela.');
      await page.click('#ver-documentos');await page.click('#mesa-aba-pesquisa');if(!await page.locator('#acervo-escolha').evaluate(el=>el.open))await page.click('#acervo-escolha>summary');await page.selectOption('#rodada','R001');await page.selectOption('#geracao','v1');await page.locator('#buscar:enabled').waitFor();await page.fill('#consulta','declara');await page.click('#buscar');await page.locator('#resultados article').first().waitFor();
      const hit=page.locator('#resultados article').first();await selectText(hit.locator('pre').first(),'valor 12.');await hit.getByRole('button',{name:'Inserir em nota',exact:true}).click();
      assert.equal(await page.locator('#apuracao-adicionar-texto').innerText(),'valor 12.');await page.locator('#apuracao-destino option').nth(1).waitFor({state:'attached'});await page.selectOption('#apuracao-destino',{label:'Nota da repórter'});await add();
      assert.match(await page.locator('#apuracao-texto').inputValue(),/valor 12\./);assert.match(await page.locator('#apuracao-fontes').innerText(),/D001/);
      checks.push('Adicionar seleção documental exata a uma nota própria preserva texto, documento, linhas e vínculo ao original.');
      await page.click('#ver-achados');if(!await page.locator('#achados-versoes').evaluate(el=>el.open))await page.click('#achados-versoes>summary');await page.locator('#achados-revisao option[value="r2"]').waitFor({state:'attached'});await page.selectOption('#achados-revisao','r2');await page.selectOption('#achados-geracao','g2');await page.locator('#achados-inspecao .finding-detail').waitFor();
      const claim=page.locator('#achados-inspecao .finding-detail');await selectText(claim.locator('h3').first(),'A fonte declara');await claim.getByRole('button',{name:'Inserir em nota',exact:true}).first().click();await page.locator('#apuracao-destino option').nth(1).waitFor({state:'attached'});await page.selectOption('#apuracao-destino',{label:'Nota da repórter'});await add();
      assert.equal(await page.locator('#apuracao-fontes .notebook-source').count(),2);assert.match(await page.locator('#apuracao-fontes').innerText(),/página PDF 1/);
      await page.locator('#apuracao-fontes button').first().click();await page.locator('#original-dialogo[open]').waitFor();assert.match(await page.locator('#original-conteudo').innerText(),/A fonte declara/);await page.keyboard.press('Escape');
      checks.push('Adicionar achado da IA mantém a seleção e referências de todas as fontes, inclusive página PDF; original pode ser aberto.');
      // Per-evidence button opens a new note.
      await page.click('#ver-achados');await page.locator('#achados-inspecao .evidence').first().getByRole('button',{name:'Inserir em nota',exact:true}).click();await page.locator('#apuracao-adicionar-salvar:enabled').waitFor();await page.selectOption('#apuracao-destino','');await add();
      assert.equal(await page.locator('#apuracao-notas button').count(),2);
      await page.fill('#apuracao-nota-titulo','Evidência complementar');await page.click('#apuracao-salvar');await saved();
      await page.click('#apuracao-nova');await page.fill('#apuracao-nota-titulo','Excluir esta nota');await editor.write(page,'Não altera documentos.');await page.click('#apuracao-salvar');await saved();page.once('dialog',d=>d.accept());await page.click('#apuracao-excluir');await page.waitForFunction(()=>document.querySelectorAll('#apuracao-notas button').length===2);
      checks.push('Seleção de evidência individual cria outra nota; criar e excluir uma nota mantém as demais.');
      await page.locator('#apuracao-notas button').filter({hasText:'Nota da repórter'}).click();
      await editor.write(page,(await page.locator('#apuracao-texto').inputValue())+'\n\n# Texto da repórter\n**Negrito** e *itálico*.\n- Lista\n> Citação\n[link](https://example.org)\n\n'+('Parágrafo de teste com acentuação e referências. '.repeat(180)));
      assert.equal(await page.locator('#apuracao-exportar').isDisabled(),true);await page.click('#apuracao-salvar');await saved();
      for(const format of ['md','pdf','docx']){await page.selectOption('#apuracao-formato',format);const [file]=await Promise.all([page.waitForEvent('download'),page.click('#apuracao-exportar')]);await file.saveAs(path.join(output,'caderno_sintetico.'+format));const content=await fs.readFile(await file.path());assert.ok(content.length>100);if(format==='pdf')assert.equal(content.subarray(0,5).toString(),'%PDF-');if(format==='docx')assert.equal(content.subarray(0,2).toString(),'PK');if(format==='md')assert.match(content.toString(),/SHA-256:/);}
      checks.push('Exportar o caderno completo em Markdown, PDF e DOCX baixa arquivos reais com referências; rascunho exige salvar antes.');
      // Exercise actual rich-text input and formatting, then save without waiting for input callbacks.
      await page.click('#apuracao-nova');await page.fill('#apuracao-nota-titulo','Teste visual temporário');await editor.mode(page,'wysiwyg');
      const visual=page.locator('#apuracao-vditor .vditor-wysiwyg .vditor-reset');
      await visual.fill('Formatação pela barra');await visual.press('Control+A');await page.locator('#apuracao-vditor button[data-type="bold"]').click();
      await page.waitForFunction(()=>document.querySelector('#apuracao-texto').value.includes('**Formatação pela barra**'));
      await visual.fill('Último caractere á');await page.locator('#apuracao-form').evaluate(form=>form.requestSubmit());await saved();
      assert.match(await editor.read(page),/Último caractere á/);
      page.once('dialog',d=>d.accept());await page.click('#apuracao-excluir');await page.waitForFunction(()=>document.querySelectorAll('#apuracao-notas button').length===2);
      await page.locator('#apuracao-notas button').filter({hasText:'Nota da repórter'}).click();
      await editor.write(page,(await editor.read(page))+'\n\n```mermaid\ngraph TD; A-->B\n```\n');
      await editor.mode(page,'ir');await editor.mode(page,'sv');await page.waitForFunction(()=>[...document.querySelectorAll('#apuracao-vditor .vditor-preview pre')].some(pre=>pre.textContent.includes('graph TD')));
      await page.click('#apuracao-salvar');await saved();await editor.mode(page,'wysiwyg');
      checks.push('Digitação visual, botão Negrito e salvamento imediato preservam o último caractere; código de diagrama não exige renderizador externo.');
      await page.locator('#apuracao-notas button').filter({hasText:'Evidência complementar'}).click();await page.evaluate(()=>scrollTo({top:0,behavior:'instant'}));await page.screenshot({path:path.join(output,'apuracao-desktop.png'),fullPage:true});
      for(const width of [390,320,736,1440]){await page.setViewportSize({width,height:950});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'overflow '+width);if(width===390)await page.screenshot({path:path.join(output,'apuracao-mobile.png'),fullPage:true});}
      const fallback=await browser.newPage();
      await fallback.route('**/vendor/vditor/dist/js/lute/lute.min.js',route=>route.abort());
      await fallback.goto(origin+'/?area=apuracao&caso=alpha');
      await fallback.locator('#apuracao-editor-aviso:not([hidden])').waitFor();
      await fallback.locator('#apuracao-nova:enabled').waitFor();await fallback.click('#apuracao-nova');
      await fallback.fill('#apuracao-nota-titulo','Teste alternativo temporário');await fallback.fill('#apuracao-texto','Nota pelo campo alternativo.');
      await fallback.click('#apuracao-salvar');await fallback.locator('#apuracao-status').filter({hasText:'Nota salva.'}).waitFor();
      fallback.once('dialog',d=>d.accept());await fallback.click('#apuracao-excluir');await fallback.waitForFunction(()=>document.querySelectorAll('#apuracao-notas button').length===2);await fallback.close();
      checks.push('Falha simulada no Lute mostra aviso e campo Markdown; criar, salvar e excluir continuam funcionando.');
      await page.selectOption('#contexto-caso','beta');await page.waitForFunction(()=>document.querySelector('#apuracao-status').textContent.includes('0 nota'));assert.equal(await page.locator('#apuracao-notas button').count(),0);
      await page.selectOption('#contexto-caso','alpha');await page.waitForFunction(()=>document.querySelectorAll('#apuracao-notas button').length===2);assert.equal(await page.evaluate(()=>window.NOTA_INJETADA),undefined);
      checks.push('Casos isolados, HTML inerte e interface sem transbordamento de 320 a 1440 px.');
    }
    assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.deepEqual(missing,[]);await fs.writeFile(path.join(output,phase+'.json'),JSON.stringify({estado:'aprovado',checks,erros:errors,requisicoes_externas:external,recursos_ausentes:missing},null,2));console.log(JSON.stringify({phase,checks:checks.length,estado:'aprovado'}));
  }catch(error){await page.screenshot({path:path.join(output,'falha-'+phase+'.png'),fullPage:true});await fs.writeFile(path.join(output,'falha-'+phase+'.json'),JSON.stringify({erro:error.message,stack:error.stack,errors,checks,external,missing,notas:await page.locator('#apuracao-notas').innerText()},null,2));throw error;}
  finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1);});
