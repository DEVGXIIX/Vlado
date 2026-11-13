'use strict';
(() => {
  let conversation = '', cursor = 0, view = 0, active = false, submitting = false, loginTimer;
  let inventoryVersion = 0, catalogVersion = 0, sourceMap = new Map(), messageMap = new Map();
  let currentStage = '';
  let currentGroup = null, currentRound = '', liveInventory = null, authenticated = null;
  let pendingFeedback = null;
  let pendingCorpus = null;
  let pendingNotebook = null;
  let pendingDiligences = null;
  const groups = new Map(), frozenInventories = new Map();
  const drafts = new Map(), approvalCards = new Map();
  let draftContext = {caso:'', conversa:''}, trackingFailed = false, trackingPending = false;
  const draftKey = context => JSON.stringify([context.caso, context.conversa]);
  function saveDraft() {
    if (!draftContext.caso) return;
    const text = $('codex-pergunta').value;
    if (text) drafts.set(draftKey(draftContext), text);
    else drafts.delete(draftKey(draftContext));
  }
  function switchDraft(caso, conversa) {
    saveDraft();
    draftContext = {caso, conversa};
    $('codex-pergunta').value = drafts.get(draftKey(draftContext)) || '';
    destination();
  }
  function destination() {
    const title = $('codex-caso').selectedOptions[0]?.textContent;
    const selected = [...$('codex-conversa').options].find(option => option.value === conversation);
    const chat = conversation ? selected?.dataset.titulo || selected?.textContent || conversation : 'Nova conversa';
    const message = draftContext.caso ? `Destino da pergunta: ${title || draftContext.caso} · ${chat}` : 'Escolha uma apuração para escrever a pergunta.';
    if ($('codex-destino').textContent !== message) $('codex-destino').textContent = message;
  }
  const stageLabels = {inventario:'Conferindo o acervo',plano:'Planejando',busca:'Buscando e lendo fontes',
    geracao_inicial:'Registrando a geração inicial',revisao:'Revisando o suporte',sintese:'Preparando a síntese',comparacao:'Comparando com a análise anterior'};
  const busyStates = new Set(['preparando','executando','aguardando_aprovacao','cancelando','publicando']);
  const names = {preparando:'Preparando snapshot e índice', executando:'Codex trabalhando',
    aguardando_aprovacao:'Aguardando sua resposta', cancelando:'Cancelamento solicitado',
    concluido:'Execução concluída', interrompido:'Execução interrompida · saídas parciais preservadas',
    erro:'Execução com erro · confira a mensagem', pronto:'Pronto'};
  names.publicando = 'Publicando e verificando os achados';
  names.incompleto = 'Fluxo incompleto · saídas preservadas, publicação final não confirmada';
  function fail(message = '') {
    $('codex-erro').textContent = message;
    $('codex-erro').hidden = !message;
  }
  function controls() {
    const blocked = active || submitting || trackingPending;
    $('codex-enviar').disabled = blocked || trackingFailed || !$('codex-caso').value;
    $('codex-pergunta').disabled = submitting || !$('codex-caso').value;
    $('codex-cancelar').disabled = !conversation || !(active || trackingFailed || trackingPending);
    $('codex-reconectar').hidden = !trackingFailed;
    $('codex-reconectar').disabled = trackingPending || submitting || !conversation;
    $('codex-reconectar').textContent = trackingPending ? 'Reconectando acompanhamento…' : 'Reconectar acompanhamento';
    $('codex-caso').disabled = blocked;
    $('codex-conversa').disabled = blocked;
    $('codex-nova').disabled = blocked;
    $('codex-atualizar').disabled = blocked;
    $('codex-excluir').disabled = blocked || trackingFailed || !conversation;
    $('codex-observacoes-remover').disabled = blocked || trackingFailed;
    $('codex-continuar-documentos').disabled = blocked || trackingFailed || !conversation;
    $('codex-corpus-retirar').disabled = blocked || trackingFailed;
    $('codex-caderno-retirar').disabled = blocked || trackingFailed;
    $('codex-diligencias-retirar').disabled = blocked || trackingFailed;
    destination();
  }
  function feedbackPreview() {
    $('codex-observacoes').hidden = !pendingFeedback;
    $('codex-observacoes-lista').replaceChildren();
    if (pendingFeedback) window.mostrarObservacoes($('codex-observacoes-lista'),
      pendingFeedback.preview.conteudo, pendingFeedback.request);
  }
  function corpusPreview() {
    $('codex-corpus-novo').hidden = !pendingCorpus;
    $('codex-corpus-previa').replaceChildren();
    if (pendingCorpus) window.mostrarCorpusNovo($('codex-corpus-previa'),pendingCorpus);
  }
  function notebookPreview(){
    $('codex-caderno').hidden=!pendingNotebook;$('codex-caderno-lista').replaceChildren();
    if(pendingNotebook)window.mostrarRegistrosCaderno($('codex-caderno-lista'),pendingNotebook.preview.conteudo);
  }
  function diligencePreview(){
    $('codex-diligencias').hidden=!pendingDiligences;$('codex-diligencias-lista').replaceChildren();
    if(pendingDiligences)window.mostrarDiligencias($('codex-diligencias-lista'),pendingDiligences.preview.conteudo);
  }
  window.estadoConversa = () => ({caso:$('codex-caso').value,conversa:conversation,ocupada:active||submitting||trackingPending||trackingFailed,
    atualizar_corpus:pendingCorpus?structuredClone(pendingCorpus.solicitacao):null});
  window.selecionarCorpusNovo = preview => {
    if (active||submitting||preview.conversa!==conversation||preview.caso_id!==$('codex-caso').value) throw new Error('A conversa mudou. Abra a continuação novamente.');
    pendingCorpus=structuredClone(preview);corpusPreview();
    if (!$('codex-pergunta').value.trim()) $('codex-pergunta').value='O que os novos documentos acrescentam ou alteram na apuração? Reexamine as pendências e compare com a análise anterior.';
    saveDraft();
    window.abrirComposicaoMesa?.();$('codex-form').scrollIntoView({block:'start'});$('codex-pergunta').focus();
  };
  window.abrirAchadosDaRodada = async (scope, identifier=null) => {
    await loadCatalog(); $('caso').value=scope.caso; $('caso').dispatchEvent(new Event('change'));
    $('rodada').value=scope.rodada; $('rodada').dispatchEvent(new Event('change'));
    showArea('achados'); await loadFindingsCatalog();
    $('achados-revisao').value=scope.revisao; $('achados-revisao').dispatchEvent(new Event('change'));
    const generations=[...$('achados-geracao').options].filter(option=>option.value);
    const generation=generations.find(option=>option.value===scope.geracao)?.value||generations[0]?.value;
    if(!generation)throw new Error('Não há índice disponível para esta revisão do achado.');
    $('achados-geracao').value=generation;
    const query={...findingScope(),filtros:{},limite:Number($('achados-limite').value),deslocamento:0};
    await searchFindings(query);
    if(identifier){const detail=await api('achados-detalhe',{...query,achado_id:identifier});selectFinding(detail.achado,query,findingEpoch,true);}
  };
  function state(value) {
    active = busyStates.has(value);
    $('codex-status').textContent = (names[value] || value) + (value === 'executando' && currentStage ? ' · ' + currentStage : '');
    if (value === 'concluido') {
      for (const group of new Set(groups.values())) group.updates.open = false;
      $('codex-andamento').open = false;
      $('codex-acervo').open = false;
    }
    controls();
  }
  function clear() {
    saveDraft();
    pendingFeedback = null; feedbackPreview();
    pendingCorpus = null; corpusPreview();
    pendingNotebook = null; notebookPreview();
    pendingDiligences = null; diligencePreview();
    ++view; conversation = ''; cursor = 0; active = false;
    trackingFailed = false; trackingPending = false; approvalCards.clear();
    switchDraft($('codex-caso').value, '');
    currentStage = '';
    currentGroup = null; currentRound = ''; groups.clear(); frozenInventories.clear();
    sourceMap.clear(); messageMap.clear();
    $('codex-conversa').value = '';
    for (const id of ['codex-mensagens','codex-fontes','codex-atividades','codex-aprovacoes']) $(id).replaceChildren();
    $('codex-aprovacoes').hidden = true;
    $('codex-versao-editorial').textContent='Nova conversa: os documentos atuais serão preservados ao enviar a pergunta.';
    if($('codex-recibo-alerta'))$('codex-recibo-alerta').hidden=true;
    $('codex-escopo').textContent = 'Nova conversa · o corpus será congelado após a pergunta.';
    fail(); state('pronto');
    $('codex-acervo').open = true;
    heading();
    limitations();
  }
  function heading() {
    destination();
    const selected = $('codex-caso').value;
    const title = selected ? $('codex-caso').selectedOptions[0]?.textContent : '';
    $('codex-acervo-resumo').textContent = title ? `${title} · conversas e documentos` : 'Escolher apuração e conversa';
    if (!$('area-codex').hidden) {
      $('area-titulo').textContent = title || 'Pergunte aos seus documentos.';
      $('area-descricao').textContent = title ? 'Perguntas, respostas e fontes desta apuração.' : 'Escolha uma apuração e abra uma conversa.';
    }
  }
  async function status() {
    clearTimeout(loginTimer);
    try {
      const data = await api('codex-status', {});
      $('codex-conta').textContent = data.autenticado ? 'Conectado ao ChatGPT' : 'Conecte sua conta ChatGPT';
      $('codex-conta').classList.toggle('connected', data.autenticado);
      if (authenticated !== data.autenticado || data.login_pendente) $('codex-conexao').open = !data.autenticado || data.login_pendente;
      authenticated = data.autenticado;
      $('codex-conexao-tecnica').replaceChildren(Leitura.tecnicos(`Codex: ${data.versao || 'versão não informada'} · Plano: ${data.plano || 'não informado'}`));
      $('codex-login').disabled = data.autenticado || data.login_pendente;
      $('codex-cancelar-login').hidden = !data.login_pendente;
      $('codex-login-alternativa').hidden = !data.login_pendente;
      $('codex-login-erro').textContent = data.erro_login || '';
      $('codex-login-erro').hidden = !data.erro_login;
      if (data.login_pendente) {
        $('codex-conta').textContent = 'Conclua o login no navegador';
        loginTimer = setTimeout(status, 3000);
      }
    } catch (error) { $('codex-conta').textContent = 'Codex indisponível.'; fail(error.message); }
  }
  async function catalogs() {
    const version = ++catalogVersion;
    try {
      const response = await fetch('/api/catalogo');
      const data = await response.json();
      if (!response.ok) throw new Error(data.erro || 'Falha ao listar casos.');
      if (version !== catalogVersion) return;
      const selected = window.contextoCaso?.() ?? $('codex-caso').value;
      $('codex-caso').replaceChildren(new Option('Selecione um caso', ''),
        ...data.casos.map(c => new Option(c.titulo, c.id)));
      if (data.casos.some(c => c.id === selected)) $('codex-caso').value = selected;
      else if (selected) clear();
      heading();
      controls();
    } catch (error) { if (version === catalogVersion) fail(error.message); }
  }
  async function conversations() {
    const caseId = $('codex-caso').value, version = ++inventoryVersion;
    if (!caseId) {
      $('codex-conversa').replaceChildren(new Option('Nova conversa', ''));
      $('codex-inventario').textContent = 'Escolha uma apuração para conferir seus documentos.';
      return;
    }
    try {
      const list = await api('codex-listar', {caso:caseId});
      if (version !== inventoryVersion || caseId !== $('codex-caso').value) return;
      heading();
      $('codex-conversa').replaceChildren(new Option('Nova conversa', ''),
        ...list.conversas.map(c => {
          const option = new Option(`${c.titulo} · ${names[c.estado] || c.estado}`, c.id);
          option.dataset.titulo = c.titulo;
          return option;
        }));
      if (list.conversas.some(c => c.id === conversation)) $('codex-conversa').value = conversation;
      else if (conversation && !active && !submitting) clear();
      destination();
      // A problem in the current inventory must not hide frozen conversations.
      const inventory = await api('inventario', {caso:caseId});
      if (version !== inventoryVersion || caseId !== $('codex-caso').value) return;
      liveInventory = inventory;
      const items = element('ul', undefined, 'document-list');
      for (const doc of inventory.documentos) {
        const entry = element('li', Leitura.nome(doc));
        if (doc.extracao_pdf) entry.append(element('p', `${doc.extracao_pdf.paginas_com_texto} de ${doc.extracao_pdf.paginas_pdf ?? '?'} páginas com texto`, 'small'));
        entry.append(Leitura.tecnicos(element('pre', JSON.stringify(doc, null, 2), 'raw-briefing')));
        items.append(entry);
      }
      $('codex-inventario').replaceChildren(element('p', Leitura.quantidade(inventory.total_documentos, 'documento')), items,
        Leitura.tecnicos(`Corpus: ${inventory.corpus_id} · Apuração: ${inventory.caso_id}`));
      limitations();
    } catch (error) { if (version === inventoryVersion) fail(error.message); }
  }
  function limitations() {
    const inventory = currentRound ? frozenInventories.get(currentRound)
      : liveInventory?.caso_id === $('codex-caso').value ? liveInventory : null;
    const messages = new Set();
    if (inventory?.indisponivel) messages.add(inventory.mensagem);
    for (const doc of inventory?.documentos || []) for (const warning of Leitura.lacunas(doc)) messages.add(`${Leitura.nome(doc)}: ${warning}`);
    let pending = 0;
    for (const record of messageMap.values()) if (record.final) pending += record.pending?.size || 0;
    if (pending) messages.add(`${pending} ${pending === 1 ? 'referência da resposta não foi recuperada' : 'referências das respostas não foram recuperadas'} na própria rodada. Confira as marcações “Fonte pendente”; essas citações não oferecem suporte verificável nesta tela.`);
    $('codex-limitacoes-lista').replaceChildren(...[...messages].map(message => element('li', message)));
    $('codex-limitacoes').hidden = !messages.size;
  }
  function group(question = '') {
    const root = element('section', undefined, 'codex-round'), user = element('article', undefined, 'codex-message codex-user');
    user.append(element('h3', 'Sua pergunta'), element('p', question, 'codex-text'));
    const answers = element('div', undefined, 'codex-answers'), actions = element('div', undefined, 'actions');
    const updates = element('details', undefined, 'codex-updates'); updates.open = true;
    const progress = element('div', undefined, 'codex-updates-body');
    progress.tabIndex = 0; progress.setAttribute('role', 'region');
    progress.setAttribute('aria-label', 'Atualizações de andamento do Codex');
    updates.append(element('summary', 'Atualizações de andamento'), progress);
    root.append(user, answers, actions, updates); $('codex-mensagens').append(root);
    currentGroup = {root, answers, actions, updates, progress};
    groups.set('pergunta-' + groups.size, currentGroup);
    return currentGroup;
  }
  function messageText(record) {
    record.pending = new Set();
    Leitura.markdown(record.body, record.text, reference => {
      const hit = sourceMap.get(reference);
      if (!hit || hit.rodada !== record.round) {
        record.pending.add(reference);
        const pending = element('span', 'Fonte pendente', 'codex-pendente');
        pending.title = 'Esta referência não foi recuperada nesta rodada.';
        return pending;
      }
      const link = element('a', Leitura.fonte(hit), 'source-citation');
      link.href = '#fonte-' + reference;
      link.addEventListener('click', event => {
        event.preventDefault();
        const card = document.getElementById('fonte-' + reference);
        if (card) { if($('codex-painel-fontes'))$('codex-painel-fontes').open=true; card.open = true; card.querySelector('blockquote').focus(); }
      });
      return link;
    });
    record.raw.textContent = JSON.stringify({...record.metadata, rodada:record.round, texto_preservado:record.text}, null, 2);
  }
  function agentMessage(id, text, delta = false, phase = '', round = '', metadata = {}) {
    let record = messageMap.get(id);
    const owner = record?.owner || groups.get(round) || currentGroup || group();
    const followUpdates = owner.progress.scrollHeight - owner.progress.clientHeight - owner.progress.scrollTop < 48;
    if (!record) {
      const card = element('article', undefined, 'panel codex-message');
      const label = element('h3', 'Codex · em andamento');
      const body = element('div', '', 'markdown-body'), raw = element('pre', '', 'raw-briefing');
      card.append(label, body, Leitura.tecnicos(raw)); owner.progress.append(card);
      record = {card, body, raw, label, owner, text:'', round, metadata:{}}; messageMap.set(id, record);
    }
    record.text = delta ? record.text + text : text;
    record.metadata = {...record.metadata, ...metadata};
    record.final = Boolean(metadata.publicada || phase === 'final_answer');
    record.label.textContent = record.final ? 'Resposta' : 'Atualização de andamento';
    if (record.final) { record.owner.answers.append(record.card); record.card.classList.add('codex-answer'); }
    messageText(record); limitations();
    if (!record.final && followUpdates) owner.progress.scrollTop = owner.progress.scrollHeight;
  }
  function source(hit, chatId) {
    if (sourceMap.has(hit.referencia)) return;
    const doc = frozenInventories.get(hit.rodada)?.documentos?.find(d => d.id === hit.documento_id);
    hit = {...hit, nome_documento:hit.nome_documento || doc?.nome_recebido || hit.original};
    sourceMap.set(hit.referencia, hit);
    const card = element('details', undefined, 'codex-source');
    card.id = 'fonte-' + hit.referencia; card.tabIndex = -1;
    const quote = element('blockquote', hit.trecho); quote.tabIndex = -1;
    card.append(element('summary', Leitura.fonte(hit)), quote);
    const button = element('button', 'Conferir original preservado', 'secondary');
    button.type = 'button';
    button.addEventListener('click', async () => {
      try {
        const blob = await api('codex-original', {conversa:chatId, referencia:hit.referencia}, true);
        await window.abrirOriginal(blob, hit.original.split('/').pop(), hit.pagina_pdf, hit.trecho);
      } catch (error) { fail(error.message); }
    });
    const notebook=element('button','Registrar trecho com fonte','secondary');notebook.type='button';
    const caseId=$('codex-caso').value;
    notebook.addEventListener('click',()=>window.abrirRegistroCaderno({caso:caseId,rodada:hit.rodada,
      documento_id:hit.documento_id,pagina_pdf:hit.pagina_pdf,
      localizador:Leitura.localizador(hit),
      trecho:window.trechoSelecionadoCaderno(quote,hit.trecho)}));
    card.append(button,notebook,Leitura.tecnicos(element('pre', JSON.stringify(hit, null, 2), 'raw-briefing')));
    $('codex-fontes').append(card);
    for (const record of messageMap.values()) messageText(record);
    limitations();
  }
  function event(event, chatId) {
    const data = event.dados;
    if (event.tipo === 'pergunta') {
      group(data.texto);
    } else if (event.tipo === 'observacoes_humanas') {
      const owner = currentGroup || group(), details = element('details',undefined,'feedback-history');
      details.append(element('summary', Leitura.quantidade(data.quantidade, 'observação humana anexada', 'observações humanas anexadas') + ' à pergunta'));
      const content = element('div');
      window.mostrarObservacoes(content, data, {caso:$('codex-caso').value,
        rodada:data.rodada_origem, revisao:data.revisao_origem});
      details.append(content); owner.root.insertBefore(details,owner.answers);
    } else if (event.tipo === 'diligencias_recebidas') {
      const owner=currentGroup||group(),details=element('details',undefined,'feedback-history');details.append(element('summary','Diligências humanas anexadas a esta pergunta'));
      const body=element('div');window.mostrarDiligencias(body,data);details.append(body);owner.root.insertBefore(details,owner.answers);
    } else if (event.tipo === 'contribuicoes_caderno') {
      const owner=currentGroup||group(),details=element('details',undefined,'feedback-history');
      details.append(element('summary',Leitura.quantidade(data.quantidade,'contribuição humana anexada','contribuições humanas anexadas')+' do caderno'));
      const content=element('div');window.mostrarRegistrosCaderno(content,data);details.append(content);owner.root.insertBefore(details,owner.answers);
    } else if (event.tipo === 'evolucao_corpus') {
      const owner=currentGroup||group(), details=element('details',undefined,'feedback-history');
      details.append(element('summary','Documentos incorporados nesta rodada'));
      const content=element('div');window.mostrarCorpusNovo(content,data);details.append(content);
      owner.root.insertBefore(details,owner.answers);
    } else if (event.tipo === 'comparativo') {
      const owner=groups.get(data.rodada_atual)||currentGroup||group();
      const panel=element('section',undefined,'panel corpus-comparison');
      window.mostrarComparativo(panel,data,chatId);owner.answers.append(panel);
    } else if (event.tipo === 'delta') agentMessage(data.item, data.texto, true, '', data.rodada);
    else if (event.tipo === 'resposta') {
      agentMessage(data.item, data.texto, false, data.fase, data.rodada,
        {publicada:data.publicada, arquivo:data.arquivo, sha256:data.sha256, etapa:data.etapa});
      $('codex-anuncio').textContent=matchMedia('(min-width: 1051px)').matches && !(data.publicada || data.fase === 'final_answer')
        ? 'Atualização de andamento disponível. A análise continua.'
        : 'Resposta disponível. Confira a análise e as fontes consultadas.';
    }
    else if (event.tipo === 'fonte') source(data, chatId);
    else if (event.tipo === 'erro') {
      fail(data.mensagem);
      $('codex-atividades').append(element('li', `Erro: ${data.mensagem}${data.codigo ? ' · ' + data.codigo : ''}`));
    } else if (event.tipo === 'escopo') {
      currentRound = data.rodada;
      $('codex-versao-editorial').textContent=`Documentos desta conversa: versão ${data.corpus_id} · análise ${data.rodada}.`;
      if (currentGroup) groups.set(currentRound, currentGroup);
      $('codex-escopo').textContent = `${data.caso} / ${data.rodada} · corpus ${data.corpus_id} · modelo informado pelo Codex: ${data.modelo || 'desconhecido'}`;
    } else if (event.tipo === 'ferramenta') {
      $('codex-atividades').append(element('li', `${data.acao}${data.etapa ? ' · ' + data.etapa : ''}${data.retornados !== null && data.retornados !== undefined ? ' · ' + data.retornados + ' trecho(s)' : ''} · ${data.arquivo}`));
    } else if (event.tipo === 'etapa') {
      currentStage = stageLabels[data.etapa] || data.etapa;
      $('codex-atividades').append(element('li', `${data.numero}/${data.total} · ${currentStage}${data.tentativa > 1 ? ' · nova tentativa automática' : ''}`));
    } else if (event.tipo === 'publicacao') {
      $('codex-atividades').append(element('li', `Achados publicados e verificados: ${data.caso} / ${data.rodada} · ${data.achados} achado(s). Conferência humana não realizada.`));
      const link = element('button','Consultar achados desta rodada','secondary'); link.type = 'button';
      link.addEventListener('click', async () => {
        try {
          await window.abrirAchadosDaRodada(data);
        } catch (error) { fail(error.message); }
      });
      (groups.get(data.rodada) || currentGroup)?.actions.append(link);
    } else if (event.tipo === 'plano') {
      $('codex-atividades').append(element('li', data.plano.map(p => `${p.step}: ${p.status}`).join(' · ')));
    } else if (event.tipo === 'aviso') $('codex-atividades').append(element('li', data.mensagem));
  }
  function approvals(items, chatId) {
    const container = $('codex-aprovacoes'), live = new Set(items.map(item => String(item.id)));
    for (const [id, record] of approvalCards) {
      if (!live.has(id)) { record.panel.remove(); approvalCards.delete(id); }
    }
    container.hidden = !items.length;
    for (const item of items) {
      const id = String(item.id);
      let record = approvalCards.get(id);
      if (!record) {
        const panel = element('section'), reason = element('p'), command = element('pre'), permissions = element('pre');
        const questions = element('div'), notice = element('p'), button = element('button', '', 'secondary');
        button.type = 'button'; panel.dataset.solicitacao = id;
        panel.append(element('h3', 'Codex aguarda uma decisão'), reason, command, permissions, questions, notice, button);
        record = {panel, reason, command, permissions, questions, notice, button, fields:new Map(), sending:false};
        approvalCards.set(id, record); container.append(panel);
        button.addEventListener('click', async () => {
          if (record.sending) return;
          record.sending = true; button.disabled = true;
          try {
            await api('codex-aprovacao', {conversa:chatId, solicitacao:record.item.id,
              respostas:Object.fromEntries([...record.fields].map(([key, field]) => [key,{answers:[field.input.value]}]))});
          } catch (error) {
            if (approvalCards.get(id) === record && conversation === chatId) {
              fail(error.message); record.sending = false; button.disabled = false;
            }
          }
        });
      }
      record.item = item;
      record.reason.textContent = item.motivo || '';
      record.command.textContent = item.comando || ''; record.command.hidden = !item.comando;
      record.permissions.textContent = item.permissoes ? JSON.stringify(item.permissoes, null, 2) : '';
      record.permissions.hidden = !item.permissoes;
      const questions = item.metodo === 'item/tool/requestUserInput' ? item.perguntas || [] : [];
      const liveQuestions = new Set(questions.map(question => String(question.id)));
      for (const [key, field] of record.fields) {
        if (!liveQuestions.has(key)) { field.label.remove(); record.fields.delete(key); }
      }
      if (item.metodo === 'item/tool/requestUserInput') {
        for (const question of questions) {
          const key = String(question.id);
          let field = record.fields.get(key);
          if (!field) {
            const label = element('label'), text = element('span'), options = element('span', '', 'small'), input = element('input');
            input.name = key; input.autocomplete = 'off';
            label.append(text, options, input); record.questions.append(label);
            field = {label, text, options, input}; record.fields.set(key, field);
          }
          field.text.textContent = question.question;
          field.options.textContent = (question.options || []).map(o => `${o.label}: ${o.description}`).join(' · ');
        }
      }
      record.notice.textContent = questions.length ? '' : 'A apuração fechada não permite ampliar acesso de escrita ou rede. Recuse este pedido ou cancele a execução.';
      record.notice.hidden = Boolean(questions.length);
      record.button.textContent = questions.length ? 'Enviar resposta' : 'Recusar solicitação';
    }
  }
  function watch() {
    if (!conversation || trackingPending) return;
    trackingPending = true; controls();
    // Invalidate any older observer; retain the cursor and the rendered conversation.
    poll(++view);
  }
  async function poll(version) {
    const chatId = conversation;
    while (version === view && conversation === chatId) {
      try {
        const data = await api('codex-eventos', {conversa:chatId, cursor, espera:20});
        if (version !== view) return;
        if (trackingPending) fail();
        trackingPending = false; trackingFailed = false;
        for (const [round, inventory] of Object.entries(data.acervos || {})) frozenInventories.set(round, inventory);
        for (const entry of data.eventos) event(entry, chatId);
        cursor = data.cursor;
        state(data.conversa.estado);
        approvals(data.aprovacoes, chatId);
        limitations();
        if (!active && data.eventos.length < 100) { await conversations(); return; }
      } catch (error) {
        if (version !== view) return;
        trackingPending = false; trackingFailed = true;
        fail(`Falha ao acompanhar a execução: ${error.message} A execução pode continuar. Use “Reconectar acompanhamento” para voltar a observá-la.`);
        $('codex-status').textContent = 'Conexão da interface interrompida';
        // Keep cancellation available; an HTTP failure is not a completed turn.
        controls();
        return;
      }
    }
  }
  $('codex-reconectar').addEventListener('click', () => { if (trackingFailed) watch(); });
  $('codex-conectar').addEventListener('click', status);
  $('codex-desligar').addEventListener('click', async () => {
    if (!window.confirm('Encerrar o serviço local? As execuções ativas serão interrompidas. As saídas já salvas serão preservadas; será necessário abrir a Mesa novamente para continuar.')) return;
    try {
      await api('codex-desligar', {});
      ++view; clearTimeout(loginTimer); active = false;
      $('codex-status').textContent = 'Serviço encerrado. Para voltar, abra Abrir mesa.vbs.';
      for (const id of ['codex-enviar','codex-cancelar','codex-login','codex-conectar','codex-desligar']) $(id).disabled = true;
    } catch (error) { fail(error.message); }
  });
  $('codex-login').addEventListener('click', async () => {
    fail(); $('codex-login').disabled = true;
    $('codex-login-erro').hidden = true;
    $('codex-conta').textContent = 'Iniciando login com ChatGPT…';
    try {
      const data = await api('codex-login', {});
      $('codex-conta').textContent = data.mensagem;
      $('codex-login-alternativa').hidden = false;
      await status();
    } catch (error) {
      $('codex-conta').textContent = 'Não foi possível iniciar o login.';
      $('codex-login-erro').textContent = error.message;
      $('codex-login-erro').hidden = false;
      $('codex-login').disabled = false;
    }
  });
  $('codex-cancelar-login').addEventListener('click', async () => {
    try { await api('codex-cancelar-login', {}); await status(); } catch (error) { fail(error.message); }
  });
  $('codex-atualizar').addEventListener('click', async () => { await catalogs(); await conversations(); });
  $('codex-caso').addEventListener('change', async () => { clear(); await conversations(); });
  $('codex-nova').addEventListener('click', () => { clear(); $('codex-conversa').value = ''; });
  $('codex-conversa').addEventListener('change', () => {
    const selected = $('codex-conversa').value; clear(); conversation = selected;
    $('codex-conversa').value = selected;
    switchDraft($('codex-caso').value, selected);
    controls();
    if (selected) watch();
  });
  $('codex-excluir').addEventListener('click', async () => {
    if (active || submitting || !conversation) return;
    submitting = true; controls();
    try {
      const removed = await window.excluirItem({tipo:'conversa', caso:$('codex-caso').value, conversa:conversation},
        $('codex-conversa').selectedOptions[0]?.textContent || 'Conversa');
      if (removed) $('codex-status').textContent = 'Conversa movida para a lixeira. Você pode restaurá-la em Apurações e lixeira.';
    } catch (error) { fail(error.message); }
    finally { submitting = false; controls(); }
  });
  window.addEventListener('acervo-alterado', async ({detail}) => {
    const item = detail.item;
    if (detail.estado === 'excluido' && item.caso === $('codex-caso').value &&
        (item.tipo === 'caso' || item.conversa === conversation)) clear();
    await catalogs();
    await conversations();
  });
  $('codex-cancelar').addEventListener('click', async () => {
    $('codex-status').textContent = 'Cancelamento solicitado…';
    try { await api('codex-cancelar', {conversa:conversation}); }
    catch (error) { fail(error.message); }
  });
  $('codex-observacoes-remover').addEventListener('click', () => {
    if (active || submitting) return;
    pendingFeedback = null; feedbackPreview();
  });
  $('codex-corpus-retirar').addEventListener('click',()=>{if(active||submitting)return;pendingCorpus=null;corpusPreview();});
  $('codex-caderno-retirar').addEventListener('click',()=>{if(active||submitting)return;pendingNotebook=null;notebookPreview();});
  $('codex-diligencias-retirar').addEventListener('click',()=>{if(active||submitting)return;pendingDiligences=null;diligencePreview();});
  async function levarContribuicoes(preview, request, kind) {
    if (active || submitting || trackingPending || trackingFailed) throw new Error('Aguarde a execução ou reconecte o acompanhamento antes de levar observações.');
    const keepDraft = $('codex-caso').value === preview.caso && conversation === (preview.conversa || '');
    const corpusDraft = keepDraft ? pendingCorpus : null;
    const feedbackDraft = keepDraft ? pendingFeedback : null;
    const notebookDraft = keepDraft ? pendingNotebook : null;
    const diligenceDraft = keepDraft ? pendingDiligences : null;
    submitting = true; controls();
    try {
      await catalogs();
      if (![...$('codex-caso').options].some(option => option.value === preview.caso)) throw new Error('A apuração não está mais disponível.');
      clear(); $('codex-caso').value = preview.caso;
      await conversations();
      if (preview.conversa && ![...$('codex-conversa').options].some(option => option.value === preview.conversa)) throw new Error('A conversa de origem não está mais disponível.');
      conversation = preview.conversa || ''; $('codex-conversa').value = conversation;
      switchDraft(preview.caso, conversation);
      const captured={preview:structuredClone(preview),request:structuredClone(request)};
      pendingFeedback=kind==='observacoes'?captured:feedbackDraft;
      pendingNotebook=kind==='caderno'?captured:notebookDraft;
      pendingDiligences=kind==='diligencias'?captured:diligenceDraft;
      pendingCorpus = preview.corpus_novo || corpusDraft; corpusPreview();
      notebookPreview();
      diligencePreview();
      feedbackPreview(); showArea('codex'); heading();
      $('codex-acervo').open = false;
      $('codex-pergunta').value = $('codex-pergunta').value || (kind==='diligencias'?'Retome a questão da diligência selecionada. Confira as respostas documentais, explique o que esclarecem e quais pendências permanecem.':kind==='caderno'?'Considere as contribuições humanas selecionadas no caderno. Reabra os originais, examine os cruzamentos e distinga o que as fontes sustentam das interpretações dos autores.':'Reexamine os achados selecionados considerando estas observações. Confira as fontes e explique as correções ou divergências que permanecerem.');
      saveDraft();
      if (conversation) watch();
      await status();
      window.abrirComposicaoMesa?.();$('codex-form').scrollIntoView({block:'start'}); $('codex-pergunta').focus();
    } finally { submitting = false; controls(); }
  }
  window.continuarComObservacoes=(preview,request)=>levarContribuicoes(preview,request,'observacoes');
  window.continuarComCaderno=(preview,request)=>levarContribuicoes(preview,request,'caderno');
  window.continuarComDiligencias=(preview,request)=>levarContribuicoes(preview,request,'diligencias');
  $('codex-form').addEventListener('submit', async e => {
    e.preventDefault(); if (active || submitting || trackingPending || trackingFailed) return;
    if (draftContext.caso !== $('codex-caso').value || draftContext.conversa !== conversation) {
      fail('O destino da pergunta mudou. Selecione novamente a apuração e a conversa antes de enviar.'); return;
    }
    saveDraft();
    fail(); submitting = true; controls();
    try {
      const request = pendingFeedback?.request;
      const result = await api('codex-perguntar', {caso:$('codex-caso').value,
        conversa:conversation || null, pergunta:$('codex-pergunta').value,
        ...(pendingCorpus ? {atualizar_corpus:pendingCorpus.solicitacao} : {}),
        ...(pendingNotebook ? {registros_caderno:pendingNotebook.request.selecoes} : {}),
        ...(pendingDiligences ? {diligencias:pendingDiligences.request.selecoes} : {}),
        ...(request ? {observacoes_humanas:Object.fromEntries(['rodada','revisao','geracao_achados','selecoes'].map(key => [key,request[key]]))} : {})});
      drafts.delete(draftKey(draftContext));
      conversation = result.conversa;
      draftContext = {caso:$('codex-caso').value, conversa:conversation};
      pendingDiligences=null;diligencePreview();
      if(pendingNotebook){window.limparSelecaoCaderno(pendingNotebook.preview.caso);pendingNotebook=null;notebookPreview();}
      pendingCorpus=null;corpusPreview();
      if (pendingFeedback) { pendingFeedback = null; feedbackPreview(); window.limparObservacoes(); }
      $('codex-acervo').open = false;
      $('codex-pergunta').value = '';
      state(result.estado);
      watch();
    } catch (error) { fail(error.message); }
    finally { submitting = false; controls(); }
  });
  $('codex-pergunta').addEventListener('input', saveDraft);
  window.addEventListener('beforeunload', event => {
    saveDraft();
    if ([...drafts.values()].some(text => text.trim())) { event.preventDefault(); event.returnValue = ''; }
  });
  window.addEventListener('codex-abrir', async () => { await catalogs(); await status(); });
  controls();
})();
