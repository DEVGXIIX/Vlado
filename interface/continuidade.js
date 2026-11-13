'use strict';
(() => {
  const dialog=$('continuidade-dialogo');
  let scope=null, preview=null, busy=false, sequence=0;
  function fail(message='') { $('continuidade-erro').textContent=message; $('continuidade-erro').hidden=!message; }
  function controls() {
    for(const control of $('continuidade-cadastro').elements) control.disabled=busy;
    $('continuidade-fechar').disabled=busy; $('continuidade-atualizar').disabled=busy;
    $('continuidade-usar').disabled=busy||!preview;
  }
  window.mostrarCorpusNovo=(target,data)=>{
    target.replaceChildren(element('p',`${Leitura.quantidade(data.documentos_novos.length,'documento novo','documentos novos')} · ${data.total_documentos} no total.`));
    const list=element('ul',undefined,'document-list');
    for(const doc of data.documentos_novos){
      const row=element('li',Leitura.nome(doc));
      for(const warning of Leitura.lacunas(doc)) row.append(element('p',warning,'notice'));
      list.append(row);
    }
    target.append(list,element('p',data.rodada_atual?'Versão incorporada nesta rodada. As conferências anteriores foram preservadas; os novos achados começam pendentes.':'O comparativo usará a última resposta concluída desta conversa. As conferências anteriores serão preservadas; os novos achados começarão pendentes.','small'),
      Leitura.tecnicos(`${data.corpus_anterior} → ${data.corpus_novo} · comparação com ${data.rodada_anterior}`));
  };
  async function refresh(version=sequence){
    preview=null; $('continuidade-previa').hidden=true; controls();
    const result=await api('codex-corpus-previa',scope);
    if(version!==sequence||!dialog.open) return;
    preview=result; window.mostrarCorpusNovo($('continuidade-documentos'),result);
    $('continuidade-previa').hidden=false; controls();
  }
  $('codex-continuar-documentos').addEventListener('click',()=>{
    const current=window.estadoConversa(); if(current.ocupada||!current.conversa)return;
    scope={caso:current.caso,conversa:current.conversa}; preview=null; ++sequence;
    $('continuidade-cadastro').reset(); $('continuidade-previa').hidden=true;
    $('continuidade-recibo').hidden=true; $('continuidade-recibo').replaceChildren();
    $('continuidade-status').textContent='O cadastro registra os arquivos antes da próxima pergunta; não inicia a análise.';
    fail(); controls(); dialog.showModal();
  });
  $('continuidade-fechar').addEventListener('click',()=>{if(!busy)dialog.close();});
  dialog.addEventListener('cancel',e=>{if(busy)e.preventDefault();});
  dialog.addEventListener('close',()=>{++sequence;scope=null;preview=null;});
  $('continuidade-atualizar').addEventListener('click',async()=>{
    if(busy||!scope)return;busy=true;controls();fail();
    try{await refresh();$('continuidade-status').textContent='Confira a versão antes de usá-la na próxima pergunta.';}
    catch(error){fail(error.message);}finally{busy=false;controls();}
  });
  $('continuidade-cadastro').addEventListener('submit',async event=>{
    event.preventDefault();if(busy||!scope)return;
    const files=[...$('continuidade-arquivos').files]; if(!files.length)return;
    if(files.reduce((n,f)=>n+f.size,0)>50*1024*1024){fail('O lote excede 50 MB. Divida os arquivos em lotes menores.');return;}
    busy=true;preview=null;controls();fail();$('continuidade-previa').hidden=true;
    $('continuidade-status').textContent='Cadastrando os arquivos e conferindo o recibo…';
    try{
      const arquivos=await Promise.all(files.map(encodeFile));
      const result=await api('codex-documentos-cadastrar',{...scope,arquivos,natureza:$('continuidade-natureza').value});
      if(result.recebidos!==files.length||result.arquivos.length!==files.length)throw new Error('Recibo incompleto; confira o cadastro antes de continuar.');
      const receipt=$('continuidade-recibo');receipt.replaceChildren(element('h3','Recibo do lote'),
        element('p',`${result.recebidos} recebidos · ${result.novos} novos · ${result.duplicados} duplicados.`));
      for(const file of result.arquivos){
        receipt.append(element('p',`${file.nome_recebido} · ${file.estado}`));
        if(file.extracao_pdf) receipt.append(element('p',`${file.extracao_pdf.paginas_com_texto} de ${file.extracao_pdf.paginas_pdf??'?'} páginas com texto. Estado: ${file.extracao_pdf.estado}.`,'small'));
      }
      receipt.append(Leitura.tecnicos(element('pre',JSON.stringify(result,null,2),'raw-briefing')));receipt.hidden=false;
      $('continuidade-arquivos').value='';$('continuidade-status').textContent='Lote cadastrado. A conversa ainda não mudou de versão.';
      try{await refresh();}catch(error){fail(error.message);}
    }catch(error){fail(error.message);$('continuidade-status').textContent='O recebimento não foi confirmado nesta tela. Confira os documentos cadastrados; reenvios identificam duplicatas.';}
    finally{busy=false;controls();}
  });
  $('continuidade-usar').addEventListener('click',()=>{
    if(busy||!preview)return;
    try{window.selecionarCorpusNovo(preview);dialog.close();}catch(error){fail(error.message);}
  });
  window.mostrarComparativo=(target,data,chat)=>{
    const scope={caso:data.caso_id,rodada:data.rodada_atual,revisao:data.revisao_atual,geracao:'g1'};
    target.append(element('h3','O que mudou com os novos documentos'),element('p',data.limitacao,'small'));
    function section(title){const block=element('section',undefined,'comparison-section');block.append(element('h4',title));target.append(block);return block;}
    function openClaim(claim){
      const button=element('button','Ver achado e fontes','secondary');button.type='button';
      button.addEventListener('click',()=>window.abrirAchadosDaRodada(scope,claim.id).catch(error=>{button.after(element('p',error.message,'notice'));}));
      return button;
    }
    const evidence=section('Evidências novas');
    if(!data.evidencias_novas.length)evidence.append(element('p','Nenhuma evidência dos novos documentos foi publicada como suporte nesta rodada.','small'));
    for(const item of data.evidencias_novas){
      const block=element('article',undefined,'feedback-item');
      block.append(element('p',Leitura.fonte({...item,...item.localizador})),element('blockquote',item.trecho||'Fonte visual: consulte o original.'));
      const source=element('a','Abrir fonte lida nesta rodada');source.href='#fonte-'+item.referencia_atual;
      source.addEventListener('click',event=>{event.preventDefault();const card=$('fonte-'+item.referencia_atual);if(card){$('codex-painel-fontes').open=true;card.open=true;card.scrollIntoView({block:'center'});card.querySelector('blockquote').focus();}});
      const original=element('button','Baixar original','secondary');original.type='button';
      original.addEventListener('click',async()=>{
        original.disabled=true;try{download(await api('codex-original',{conversa:chat,referencia:item.referencia_atual},true),item.original.split('/').pop());}
        catch(error){block.append(element('p',error.message,'notice'));}finally{original.disabled=false;}
      });block.append(source,original);evidence.append(block);
    }
    for(const [kind,title]of [['alterada','Conclusões alteradas'],['pendencia_respondida','Pendências respondidas'],['nova','Achados novos'],['mantida','Conclusões mantidas'],['nao_retomada','Achados não retomados']]){
      const block=section(title),entries=data.comparacoes.filter(e=>e.tipo===kind);
      if(!entries.length)block.append(element('p','Nenhum registro nesta categoria.','small'));
      for(const entry of entries){
        const card=element('article',undefined,'feedback-item');
        for(const claim of entry.anteriores)card.append(element('p',`Antes · ${claim.redacao}`),Leitura.tecnicos(`${data.rodada_anterior} · ${claim.id}@v${claim.versao}`));
        for(const claim of entry.atuais)card.append(element('p',`Agora · ${claim.redacao}`),element('p',`Suporte da IA: ${pretty(claim.suporte)}`,'small'),openClaim(claim));
        card.append(element('p',`Avaliação da IA: ${entry.justificativa}`,'small'));block.append(card);
      }
    }
    const review=section('Achados para nova conferência');
    review.append(element('p','Todos os achados da nova rodada começam pendentes. Estes se destacam por serem novos, alterados ou terem evidência de documento novo.','small'));
    if(!data.nova_conferencia.length)review.append(element('p','Nenhum achado destacado nesta rodada.','small'));
    for(const claim of data.nova_conferencia)review.append(element('p',claim.redacao),openClaim(claim));
    if(data.documentos_novos_sem_leitura_registrada.length)target.append(element('p',`Há documentos novos sem leitura registrada: ${data.documentos_novos_sem_leitura_registrada.map(id=>Leitura.nome(data.documentos_novos.find(d=>d.id===id))).join(', ')}. A comparação não cobre seu conteúdo.`,'notice'));
    const exportButton=element('button','Exportar comparativo · texto com referências','secondary');exportButton.type='button';
    exportButton.addEventListener('click',()=>window.exportarEditorial(data,`comparativo_${data.rodada_anterior}_${data.rodada_atual}`));
    const jsonButton=element('button','Dados técnicos · JSON','secondary');jsonButton.type='button';jsonButton.addEventListener('click',()=>window.exportarEditorial(data,`comparativo_${data.rodada_anterior}_${data.rodada_atual}`,'json'));target.append(jsonButton);
    target.append(exportButton,Leitura.tecnicos(element('pre',JSON.stringify(data,null,2),'raw-briefing')));
  };
})();
