'use strict';
(() => {
  let state=null, noteId=null, dirty=false, busy=false, pending=null, sequence=0, saveAttempt=null, dialogSequence=0;
  const dialog=$('apuracao-adicionar-dialogo');
  const editor=new EditorNotas(changed);
  const uid=()=>crypto.randomUUID().replaceAll('-','');
  function error(message=''){$('apuracao-erro').textContent=message;$('apuracao-erro').hidden=!message;}
  function dialogError(message=''){$('apuracao-adicionar-erro').textContent=message;$('apuracao-adicionar-erro').hidden=!message;}
  function discard(){return !dirty||window.confirm('Há alterações não salvas. Descartar essas alterações?');}
  function controls(){
    const ready=!!state&&!busy;
    $('apuracao-caso').disabled=busy;
    $('apuracao-nova').disabled=!ready;
    $('apuracao-atualizar').disabled=busy;
    $('apuracao-exportar').disabled=!ready||dirty||!state.notas.length;
    for(const control of $('apuracao-form').elements)control.disabled=busy;
    editor.disabled(busy);
    $('apuracao-excluir').disabled=busy||!noteId;
    for(const button of $('apuracao-notas').querySelectorAll('button'))button.disabled=busy;
  }
  function preview(){Leitura.markdown($('apuracao-previa'),$('apuracao-texto').value);}
  function changed(){dirty=true;preview();controls();$('apuracao-status').textContent='Alterações não salvas.';}
  function sources(note){
    const target=$('apuracao-fontes');target.replaceChildren();
    if(!note?.fontes.length){target.append(element('p','Sem fonte anexada. Nota própria.','small'));return;}
    for(const [number,source]of note.fontes.entries()){
      const block=element('section',undefined,'notebook-source');
      block.append(element('h4',`Fonte ${number+1} · ${source.tipo==='ia'?'Seleção de achado da IA':'Pesquisa documental'}`),
        element('p',`${source.caso} / ${source.rodada}${source.achado_id?' / '+source.achado_id+' v'+source.achado_versao:''}`,'small'),element('blockquote',source.texto_selecionado));
      if(!source.documentos.length)block.append(element('p','Achado sem evidência documental vinculada.','small'));
      for(const [index,doc]of source.documentos.entries()){
        const button=element('button','Abrir fonte original','secondary');button.type='button';
        block.append(element('p',`${doc.nome_documento} (${doc.documento_id}) · ${doc.pagina_pdf?'página PDF '+doc.pagina_pdf+' · ':''}${doc.localizador}`));
        button.addEventListener('click',async()=>{button.disabled=true;try{await window.abrirOriginal(await api('apuracao-original',{caso:state.caso,nota_id:note.id,fonte_id:source.id,documento_indice:index},true),doc.nome_documento,doc.pagina_pdf);}catch(failure){error(failure.message);}finally{button.disabled=false;}});
        block.append(button);
      }
      target.append(block);
    }
  }
  function open(identifier){
    noteId=identifier;const note=state?.notas.find(n=>n.id===identifier);
    $('apuracao-editor').hidden=false;$('apuracao-nota-titulo').value=note?.titulo||'';$('apuracao-texto').value=note?.texto||'';
    editor.open(note?.texto||'');
    dirty=false;preview();sources(note);renderList();controls();
  }
  function renderList(){
    $('apuracao-notas').replaceChildren();
    for(const note of state?.notas||[]){const button=element('button',note.titulo,'secondary');button.type='button';button.dataset.nota=note.id;button.setAttribute('aria-current',String(note.id===noteId));button.addEventListener('click',()=>{if(discard())open(note.id);});$('apuracao-notas').append(button);}
  }
  function apply(result,selected=noteId){
    state=result;dirty=false;renderList();
    if(selected&&state.notas.some(n=>n.id===selected))open(selected);
    else if(state.notas.length)open(state.notas[0].id);
    else{noteId=null;$('apuracao-editor').hidden=true;}
    controls();$('apuracao-status').textContent=`${state.notas.length} nota(s) salva(s) · revisão ${state.revisao}.`;
  }
  async function load(caseId){
    const ticket=++sequence;busy=true;controls();error();
    try{const result=caseId?await api('apuracao-listar',{caso:caseId}):null;if(ticket!==sequence)return;
      if(result)apply(result);else{state=null;noteId=null;dirty=false;renderList();$('apuracao-editor').hidden=true;$('apuracao-status').textContent='Selecione uma apuração.';}}
    catch(failure){if(ticket===sequence){error(failure.message);state=null;renderList();$('apuracao-editor').hidden=true;}}
    finally{if(ticket===sequence){busy=false;controls();}}
  }
  async function catalog(){
    if(busy||dirty)return;
    try{const response=await fetch('/api/catalogo'),data=await response.json();if(!response.ok)throw new Error(data.erro||'Falha ao listar apurações.');
      const selected=window.contextoCaso?.() ?? ($('apuracao-caso').value||$('caso').value||$('codex-caso')?.value||'');
      $('apuracao-caso').replaceChildren(new Option('Selecione uma apuração',''),...data.casos.map(c=>new Option(c.titulo,c.id)));
      if(data.casos.some(c=>c.id===selected))$('apuracao-caso').value=selected;
      await load($('apuracao-caso').value);
    }catch(failure){error(failure.message);}
  }
  $('apuracao-caso').addEventListener('change',()=>{if(!discard()){$('apuracao-caso').value=state?.caso||'';return;}dirty=false;noteId=null;load($('apuracao-caso').value);});
  $('apuracao-atualizar').addEventListener('click',()=>{if(discard()){dirty=false;catalog();}});
  $('apuracao-nova').addEventListener('click',()=>{if(discard()){open(null);$('apuracao-nota-titulo').focus();}});
  $('apuracao-nota-titulo').addEventListener('input',changed);
  $('apuracao-form').addEventListener('submit',async event=>{
    event.preventDefault();if(busy||!state)return;editor.flush();busy=true;controls();error();
    const body={caso:state.caso,revisao:state.revisao,nota_id:noteId,titulo:$('apuracao-nota-titulo').value,texto:$('apuracao-texto').value};
    const key=JSON.stringify(body);if(saveAttempt?.key!==key)saveAttempt={key,id:uid()};
    try{const result=await api('apuracao-salvar',{...body,requisicao_id:saveAttempt.id});saveAttempt=null;apply(result,noteId||result.notas.at(-1).id);$('apuracao-status').textContent='Nota salva. Pode reabrir o caderno ou reiniciar o serviço.';}
    catch(failure){error(failure.message);}finally{busy=false;controls();}
  });
  $('apuracao-excluir').addEventListener('click',async()=>{
    if(busy||!noteId||!window.confirm('Excluir esta nota do caderno? As fontes serão preservadas.'))return;
    busy=true;controls();error();try{apply(await api('apuracao-excluir',{caso:state.caso,revisao:state.revisao,nota_id:noteId,requisicao_id:uid()}),null);}catch(failure){error(failure.message);}finally{busy=false;controls();}
  });
  $('apuracao-exportar').addEventListener('click',async()=>{
    if(busy||dirty||!state)return;busy=true;controls();error();const format=$('apuracao-formato').value;
    try{download(await api('apuracao-exportar',{caso:state.caso,formato:format},true),`caderno_${state.caso}.${format}`);$('apuracao-status').textContent='Caderno salvo exportado com as referências de cada nota.';}
    catch(failure){error(failure.message);}finally{busy=false;controls();}
  });
  window.botaoAdicionarApuracao=(scope,container,fallback)=>{
    const button=element('button','Inserir em nota','secondary');button.type='button';let selected='';
    const selection=()=>{const value=window.getSelection();return value&&!value.isCollapsed&&container?.contains(value.anchorNode)&&container.contains(value.focusNode)?value.toString():fallback;};
    // Capture before the button changes focus; keyboard activation also uses the current selection.
    button.addEventListener('pointerdown',()=>{selected=selection();});
    button.addEventListener('click',async event=>{
      if(busy)return;const text=event.detail?selected||selection():selection();
      const ticket=++dialogSequence;
      selected='';dialogError();pending=null;$('apuracao-adicionar-salvar').disabled=true;
      $('apuracao-adicionar-origem').textContent=`${scope.caso} / ${scope.rodada} · ${scope.tipo==='ia'?'Achado da IA':'Pesquisa documental'}`;$('apuracao-adicionar-texto').textContent=text;
      dialog.showModal();
      try{const saved=await api('apuracao-listar',{caso:scope.caso});if(!dialog.open||ticket!==dialogSequence)return;
        pending={scope:{...scope,texto:text},state:saved,requisicao:uid()};$('apuracao-destino').replaceChildren(new Option('Criar nova nota',''),...saved.notas.map(n=>new Option(n.titulo,n.id)));
        if(state?.caso===scope.caso&&noteId)$('apuracao-destino').value=noteId;
        $('apuracao-adicionar-salvar').disabled=false;
      }catch(failure){dialogError(failure.message);}
    });return button;
  };
  $('apuracao-adicionar-fechar').addEventListener('click',()=>{if(!busy)dialog.close();});
  dialog.addEventListener('close',()=>{++dialogSequence;pending=null;});
  dialog.addEventListener('cancel',event=>{if(busy)event.preventDefault();});
  $('apuracao-adicionar-form').addEventListener('submit',async event=>{
    event.preventDefault();if(!pending||busy)return;
    if(dirty){dialogError('Salve ou descarte a nota em edição na aba Apuração antes de adicionar a evidência.');return;}
    busy=true;controls();$('apuracao-adicionar-salvar').disabled=true;$('apuracao-adicionar-fechar').disabled=true;dialogError();
    const target=$('apuracao-destino').value;
    try{const result=await api('apuracao-adicionar',{caso:pending.scope.caso,revisao:pending.state.revisao,nota_id:target||null,origem:pending.scope,requisicao_id:pending.requisicao});
      const caseId=result.caso;dialog.close();if(![...$('apuracao-caso').options].some(o=>o.value===caseId))$('apuracao-caso').append(new Option(caseId,caseId));$('apuracao-caso').value=caseId;
      apply(result,target||result.notas.at(-1).id);$('experiencia-status').textContent='Trecho inserido na nota com suas referências. Continue aqui ou abra o Caderno.';
    }catch(failure){dialogError(failure.message);}finally{busy=false;controls();$('apuracao-adicionar-salvar').disabled=false;$('apuracao-adicionar-fechar').disabled=false;}
  });
  window.addEventListener('beforeunload',event=>{if(dirty){event.preventDefault();event.returnValue='';}});
  window.addEventListener('apuracao-abrir',catalog);
  window.addEventListener('acervo-alterado',()=>{if(!$('area-apuracao').hidden)catalog();});
  window.prepararTrocaApuracao=()=>{if(busy){$('experiencia-status').textContent='Aguarde o salvamento da nota.';return false;}if(!discard())return false;dirty=false;return true;};
  controls();
})();
