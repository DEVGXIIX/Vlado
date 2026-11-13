'use strict';
// Shared editorial context. Internal selectors remain as adapters for each module.
(() => {
  const caseSelects = ['caso','codex-caso','apuracao-caso','caderno-caso','diligencias-caso','gerenciar-caso'];
  const routeIds = ['documentos-aba','rodada','geracao','achados-revisao','achados-geracao','codex-conversa','consulta','modo','documento','pagina','limite',
    'achados-texto','achados-documento','achados-natureza','achados-suporte','achados-humana','achados-destino','achados-briefing','achados-marcacao','achados-limite',
    'caderno-texto','diligencias-texto','diligencias-estado-filtro','diligencias-responsavel-filtro'];
  let current = '', area = 'inicio', restoring = false, revision = 0;
  const desktop = matchMedia('(min-width: 1051px)');
  const pageOffsets = {documentos:0, achados:0, caderno:0};
  let restoredOffset = 0;
  window.restaurandoMesa = () => desktop.matches && restoring;
  window.paginaRestauradaMesa = name => desktop.matches && restoring && area === name ? restoredOffset : 0;
  window.registrarPaginaMesa = (name, offset) => {
    if (!desktop.matches) return;
    pageOffsets[name] = offset;
    writeRoute();
    window.dispatchEvent(new CustomEvent('mesa-consulta', {detail:{area:name}}));
  };
  const defaults = Object.fromEntries(routeIds.map(id=>[id,$(id).value]));
  const notice = message => { $('experiencia-status').textContent = message; };
  window.contextoCaso = () => current;
  function adapt(id, value) {
    const select = $(id);
    if (value && ![...select.options].some(o => o.value === value)) {
      select.append(new Option(cases.find(c => c.id === value)?.titulo || value, value));
    }
    select.value = value;
  }
  function canSwitch() {
    if(cadastroBusy){notice('Aguarde o recibo deste envio antes de trocar de apuração.');return false;}
    if (window.estadoConversa?.().ocupada) {
      notice('Aguarde a execução ou reconecte o acompanhamento antes de trocar de apuração.'); return false;
    }
    return window.prepararTrocaApuracao?.() !== false;
  }
  window.definirContextoCaso = (value, {force = false} = {}) => {
    if (value === current) return true;
    if (!force && !canSwitch()) return false;
    current = value;
    for (const name of Object.keys(pageOffsets)) pageOffsets[name] = 0;
    adapt('contexto-caso', value);
    for (const id of caseSelects) {
      if ($(id).value !== value) { adapt(id,value); $(id).dispatchEvent(new Event('change')); }
    }
    // Upload destination follows the desk; starting a new case is always explicit.
    adapt('cadastro-caso', value); toggleNewCase();
    try { localStorage.setItem('mesa-apuracao', value); } catch {}
    notice(value ? `Apuração: ${cases.find(c => c.id === value)?.titulo || value}.` : 'Escolha uma apuração ou comece uma nova.');
    writeRoute(); return true;
  };
  $('contexto-caso').addEventListener('change', () => {
    const value = $('contexto-caso').value;
    if (!window.definirContextoCaso(value)) $('contexto-caso').value = current;
  });
  for (const id of caseSelects) {
    $(id).closest('label')?.classList.add('context-adapter');
    $(id).addEventListener('change', () => {
      // Programmatic navigation to a cited case must also update the shared context.
      if ($(id).value !== current) window.definirContextoCaso($(id).value);
    });
  }
  function routeFor(target = area) {
    const url = new URL(location.href); url.search = '';
    if (desktop.matches) url.hash = '';
    url.searchParams.set('area',target);
    if (current) url.searchParams.set('caso',current);
    for (const id of routeIds) {
      const relevant = id.startsWith('achados-') ? target === 'achados'
        : id.startsWith('codex-') ? target === 'codex'
        : id.startsWith('caderno-') ? target === 'caderno'
        : id.startsWith('diligencias-') ? target === 'diligencias'
        : ['rodada','geracao'].includes(id) ? ['documentos','achados'].includes(target) : target === 'documentos';
      if (relevant && $(id).value) url.searchParams.set(id,$(id).value);
    }
    if (desktop.matches && pageOffsets[target]) url.searchParams.set('deslocamento',pageOffsets[target]);
    return url;
  }
  window.enderecoAreaMesa = routeFor;
  function writeRoute(replace = false) {
    if (restoring) return;
    const url = routeFor();
    if (url.href !== location.href) history[replace ? 'replaceState' : 'pushState']({},'',url);
    window.dispatchEvent(new Event('mesa-rota-alterada'));
  }
  const originalArea = showArea;
  showArea = name => {
    if (!$('area-' + name)) name = 'inicio';
    area = name;
    originalArea(name);
    $('caderno-abas').hidden = !['apuracao','caderno'].includes(name);
    $('caderno-aba-notas').setAttribute('aria-pressed',String(name === 'apuracao'));
    $('caderno-aba-trechos').setAttribute('aria-pressed',String(name === 'caderno'));
    if (name === 'caderno') $('ver-apuracao').setAttribute('aria-pressed','true');
    $('area-titulo').tabIndex = -1; $('area-titulo').focus({preventScroll:true});
    writeRoute();
  };
  $('caderno-aba-notas').addEventListener('click',()=>showArea('apuracao'));
  $('caderno-aba-trechos').addEventListener('click',()=>showArea('caderno'));
  $('achados-texto').closest('label').after($('achados-documento').closest('label'));
  $('inicio-nova').addEventListener('click',()=>{
    showArea('cadastro'); $('cadastro-caso').value=''; toggleNewCase(); $('cadastro-titulo-input').focus();
  });
  $('inicio-adicionar').addEventListener('click',()=>{showArea('cadastro');$('cadastro-arquivos').focus();});
  $('inicio-retomar').addEventListener('click',()=>{
    if (!current) { notice('Escolha a apuração que deseja retomar.'); $('contexto-caso').focus(); }
    else showArea('codex');
  });
  $('cadastro-perguntar').addEventListener('click',()=>{
    const caseId = $('cadastro-perguntar').dataset.caso;
    if (!window.definirContextoCaso(caseId)) return;
    $('codex-recibo-alerta').replaceChildren(element('summary','Recibo dos documentos enviados · confira as limitações antes de perguntar'),$('cadastro-recibo').cloneNode(true));
    // Avoid duplicated DOM IDs when preserving the receipt alongside the question.
    for (const child of $('codex-recibo-alerta').querySelectorAll('[id]')) child.removeAttribute('id');
    $('codex-recibo-alerta').hidden=false; showArea('codex'); window.abrirComposicaoMesa?.(); $('codex-pergunta').focus();
  });
  for (const id of routeIds) $(id).addEventListener('change',()=>writeRoute());
  for (const form of ['pesquisa','achados-form','caderno-pesquisa','diligencias-filtros']) $(form).addEventListener('submit',()=>writeRoute());
  async function waitFor(test) {
    const start = Date.now();
    while (!test()) { if (Date.now()-start > 8000) throw new Error('A seleção salva ainda não está disponível. Confira a versão antes de continuar.'); await new Promise(r=>setTimeout(r,40)); }
  }
  async function restore() {
    const ticket = ++revision, params = new URL(location.href).searchParams;
    restoring = true;
    try {
      const value = params.get('caso') || '';
      if (value && !cases.some(c=>c.id===value)) throw new Error('A apuração deste endereço não está disponível. Nenhuma outra foi selecionada.');
      if (!window.definirContextoCaso(value)) { restoring=false; writeRoute(true); return; }
      const target = params.get('area') || 'inicio';
      const offset = Number(params.get('deslocamento') || 0);
      restoredOffset = desktop.matches && Number.isSafeInteger(offset) && offset >= 0 ? offset : 0;
      showArea(target);
      for (const id of routeIds) {
        if (ticket !== revision) return;
        const value = params.get(id);
        if (value === null) {
          if (id === 'documentos-aba') {
            $(id).value = target === 'documentos' && ['consulta','rodada','geracao'].some(key=>params.has(key)) ? 'pesquisa' : defaults[id];
            $(id).dispatchEvent(new Event('change'));
            continue;
          }
          if (!['rodada','geracao','achados-revisao','achados-geracao','codex-conversa'].includes(id)) $(id).value = defaults[id];
          continue;
        }
        const select = $(id);
        if (desktop.matches && id === 'achados-documento') {
          if (value && ![...select.options].some(o=>o.value===value)) select.append(new Option(value,value));
        } else if (select.tagName === 'SELECT') await waitFor(()=>!select.disabled && [...select.options].some(o=>o.value===value));
        if (ticket !== revision) return;
        select.value=value; select.dispatchEvent(new Event('change'));
      }
      if (target==='documentos' && params.has('consulta')) {
        await waitFor(()=>!$('buscar').disabled); $('pesquisa').requestSubmit();
      }
      if (target==='achados' && params.has('achados-geracao')) {
        if (desktop.matches) await searchFindings({...findingScope(), filtros:findingFilters(), limite:Number($('achados-limite').value), deslocamento:restoredOffset});
        else {await waitFor(()=>!$('achados-buscar').disabled); $('achados-form').requestSubmit();}
      }
      if(target==='caderno' && (params.has('caderno-texto') || restoredOffset)) {
        await waitFor(()=>!$('caderno-buscar').disabled); $('caderno-pesquisa').requestSubmit();
      }
      if(target==='diligencias' && ['diligencias-texto','diligencias-estado-filtro','diligencias-responsavel-filtro'].some(id=>params.has(id))) {
        $('diligencias-filtros').requestSubmit();
      }
    } catch (failure) { notice(failure.message); }
    finally { if(ticket===revision) {restoring=false;if (desktop.matches) writeRoute(true);} }
  }
  let initialized = false;
  window.addEventListener('catalogo-carregado',()=>{
    $('contexto-caso').replaceChildren(new Option('Escolha uma apuração',''),...cases.map(c=>new Option(c.titulo,c.id)));
    adapt('contexto-caso',current);
    if (!initialized) {
      initialized=true;
      if (!new URL(location.href).searchParams.has('area')) {
        let saved=''; try { saved=localStorage.getItem('mesa-apuracao') || ''; } catch {}
        if(cases.some(c=>c.id===saved)) window.definirContextoCaso(saved);
        showArea('inicio');
      } else restore();
    } else if(current && !cases.some(c=>c.id===current)) {
      window.definirContextoCaso('',{force:true});
    }
  });
  window.addEventListener('popstate',restore);
  if (catalogLoaded) window.dispatchEvent(new Event('catalogo-carregado'));
  // In a narrow viewport the detail is a dedicated screen; the list position survives.
  const back=element('button','Voltar à lista de achados','secondary'); back.type='button';
  back.id='achados-voltar-lista'; $('achados-inspecao').before(back); back.hidden=true;
  let returnTo=null;
  $('achados-resultados').addEventListener('click',event=>{
    if(!event.target.closest('.finding-open') || !matchMedia('(max-width: 900px)').matches)return;
    returnTo=event.target.closest('.finding-open'); $('mesa-achados').classList.add('detail-open'); back.hidden=false;
    const heading=$('achados-inspecao').querySelector('h3'); if(heading){heading.tabIndex=-1;heading.focus();}
  });
  back.addEventListener('click',()=>{
    $('mesa-achados').classList.remove('detail-open');back.hidden=true;returnTo?.focus();
  });
  // Discard checks cover close, Escape and page reload; saved programmatic closes remain allowed.
  for(const [dialogId,formIds]of [['revisao-dialogo',['revisao-form']],['caderno-dialogo',['caderno-form']],['diligencias-dialogo',['diligencias-form']],['diligencias-resposta-dialogo',['diligencias-upload','diligencias-resposta-form']]]) {
    const dialog=$(dialogId); let dirty=false;
    for(const formId of formIds) {
      $(formId).addEventListener('input',()=>{dirty=true;}); $(formId).addEventListener('change',()=>{dirty=true;});
    }
    const close=dialog.querySelector('.section-heading button');
    const check=()=>!dirty || window.confirm('Há texto ou alterações não salvas. Descartar e fechar?');
    close.addEventListener('click',event=>{if(!check()){event.preventDefault();event.stopImmediatePropagation();}},true);
    dialog.addEventListener('cancel',event=>{if(!check())event.preventDefault();},true);
    dialog.addEventListener('close',()=>{dirty=false;});
    window.addEventListener('beforeunload',event=>{if(dialog.open&&dirty){event.preventDefault();event.returnValue='';}});
  }
})();

// The original is fetched by the existing hash/scope-validated endpoints.
window.abrirOriginal = async (blob, name, page = 1, reference = '') => {
  const dialog=$('original-dialogo'), body=$('original-conteudo');
  window.fecharOriginal?.();
  const pdf = /\.pdf$/i.test(name) || blob.type === 'application/pdf';
  const imageFile = /\.(png|jpe?g|gif|webp)$/i.test(name);
  const safeImageType = {'png':'image/png','jpg':'image/jpeg','jpeg':'image/jpeg','gif':'image/gif','webp':'image/webp'}[name.split('.').pop().toLowerCase()];
  const url = URL.createObjectURL(pdf ? new Blob([blob],{type:'application/pdf'}) : imageFile ? new Blob([blob],{type:safeImageType}) : blob);
  $('original-titulo').textContent=name;
  $('original-referencia').textContent=reference;
  $('original-referencia').hidden=!reference;
  $('original-localizacao').textContent=pdf ? `Página física ${Number(page)||1} do PDF. Confira tabelas e elementos visuais no original.` : 'Original preservado. Confira o localizador indicado na fonte.';
  body.replaceChildren();
  if(pdf) { const frame=element('iframe');frame.title=`Original: ${name}`;frame.src=url+'#page='+Math.max(1,Number(page)||1);body.append(frame); }
  else if(imageFile) { const img=element('img');img.src=url;img.alt=`Original: ${name}`;body.append(img); }
  else if(/\.(txt|md|csv|tsv|json)$/i.test(name)) body.append(element('pre',await blob.text()));
  else body.append(element('p','Este formato precisa de um aplicativo compatível. Baixe o original para conferir.'));
  $('original-baixar').onclick=()=>download(blob,name);
  window.fecharOriginal=()=>{URL.revokeObjectURL(url);body.replaceChildren();};
  if(!dialog.open)dialog.showModal();
};
$('original-fechar').addEventListener('click',()=>$('original-dialogo').close());
$('original-dialogo').addEventListener('close',()=>window.fecharOriginal?.());

// Markdown exports retain every field and exact reference; JSON stays available.
window.exportarEditorial = (data, name, format = 'md') => {
  if(format === 'json') { download(new Blob([JSON.stringify(data,null,2)],{type:'application/json;charset=utf-8'}),name+'.json'); return; }
  const lines=['# Registro da apuração','', 'Análise da IA e registros humanos devem ser conferidos nas fontes.',''];
  const safe = value => String(value ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
  const paragraph = value => {if(value)lines.push(safe(value),'');};
  const quote = value => {if(value)lines.push(...safe(value).split('\n').map(line=>'> '+line),'');};
  const scope=[data.caso_id || data.caso,data.rodada || data.rodada_atual,data.revisao || data.revisao_atual,data.geracao || data.geracao_achados].filter(Boolean).join(' / ');
  paragraph('Apuração e versão: '+scope);
  function source(item) {
    lines.push('### '+safe(Leitura.fonte(item)),'');quote(item.trecho);
    paragraph('Referência: '+[scope,item.documento_id,item.referencia || item.referencia_atual || item.id,Leitura.localizador(item)].filter(Boolean).join(' · '));
    paragraph('Original: '+(item.original || item.nome_documento || item.nome_recebido || 'Consulte o registro da fonte'));
    if(item.original_sha256)paragraph('SHA-256 do original: '+item.original_sha256);
    paragraph(item.contexto);paragraph(item.limitacoes);
  }
  if(Array.isArray(data.resultados) || Array.isArray(data.registros)) {
    const items=data.resultados || data.registros;
    paragraph(`${items.length} registro(s) nesta exportação.`);
    for(const [index,raw]of items.entries()) {
      const item=raw.registro || raw;
      lines.push('## '+safe(`${index+1}. ${item.redacao || item.titulo || Leitura.fonte(item)}`),'');
      if(item.redacao || item.titulo) {
        if(item.autor)paragraph('Autoria: '+item.autor);
        if(item.suporte)paragraph('Suporte avaliado pela IA: '+pretty(item.suporte));
        if(item.revisao_humana)paragraph('Conferência humana: '+pretty(item.revisao_humana.estado));
        paragraph(item.anotacao);paragraph(item.limitacoes);
        paragraph([item.id,item.versao?'versão '+item.versao:'',raw.sha256?'SHA-256 '+raw.sha256:''].filter(Boolean).join(' · '));
        for(const evidence of item.evidencias || item.fontes || []) source(evidence);
      } else source(item);
    }
    download(new Blob([lines.join('\n')],{type:'text/markdown;charset=utf-8'}),name+'.md');return;
  }
  if(Array.isArray(data.comparacoes)) {
    paragraph(data.limitacao);
    for(const comparison of data.comparacoes) {
      lines.push('## '+safe(pretty(comparison.tipo)),'');
      for(const previous of comparison.anteriores || [])paragraph('Antes: '+previous.redacao);
      for(const current of comparison.atuais || [])paragraph('Agora: '+current.redacao);
      paragraph('Avaliação da IA: '+comparison.justificativa);
    }
    lines.push('## Evidências novas','');
    for(const evidence of data.evidencias_novas || [])source(evidence);
    download(new Blob([lines.join('\n')],{type:'text/markdown;charset=utf-8'}),name+'.md');return;
  }
  function render(value,depth=0) {
    if(value===null||value===undefined)return 'Não informado';
    if(typeof value!=='object')return String(value);
    for(const [key,item]of Object.entries(value)) {
      if(item && typeof item==='object') {lines.push('', '#'.repeat(Math.min(6,depth+2))+' '+key.replaceAll('_',' '),''); render(item,depth+1);}
      else lines.push(`**${key.replaceAll('_',' ')}:** ${safe(item ?? 'Não informado')}`, '');
    }
    return '';
  }
  render(data);download(new Blob([lines.join('\n')],{type:'text/markdown;charset=utf-8'}),name+'.md');
};
