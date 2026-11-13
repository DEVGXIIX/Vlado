'use strict';
(() => {
  const labels = {caso:'Apuração', conversa:'Conversa', rodada:'Rodada'};
  const running = new Set(['preparando','executando','aguardando_aprovacao','cancelando','publicando']);
  let data = null, sequence = 0, busy = false;
  function fail(message = '') {
    $('gerenciar-erro').textContent = message;
    $('gerenciar-erro').hidden = !message;
  }
  function controls() {
    for (const control of $('area-gerenciar').querySelectorAll('button, select')) {
      control.disabled = busy || control.dataset.blocked === 'true';
    }
  }
  function row(title, description, buttonText, action, blocked = false, metadata = null) {
    const item = element('li'), text = element('div');
    text.append(element('h4', title), element('p', description, 'small'));
    if (metadata) text.append(Leitura.tecnicos(element('pre', JSON.stringify(metadata, null, 2), 'raw-briefing')));
    const button = element('button', buttonText, buttonText === 'Excluir' ? 'danger' : 'secondary');
    button.type = 'button'; button.disabled = blocked || busy;
    button.dataset.blocked = String(blocked);
    button.setAttribute('aria-label', `${buttonText} ${title}`);
    button.addEventListener('click', async () => {
      try { await action(); } catch (error) { fail(error.message); }
    });
    item.append(text, button);
    return item;
  }
  function emptyList(id, message) {
    if (!$(id).children.length) $(id).append(element('li', message, 'manage-empty'));
  }
  function render() {
    const selected = data.casos.find(c => c.id === $('gerenciar-caso').value);
    $('gerenciar-selecao').hidden = !selected;
    $('gerenciar-conversas').replaceChildren(); $('gerenciar-rodadas').replaceChildren();
    if (selected) {
      $('gerenciar-nome').textContent = selected.titulo;
      $('gerenciar-resumo').textContent = `${Leitura.quantidade(data.conversas.length, 'conversa')} · ${Leitura.quantidade(selected.rodadas.length, 'rodada')}`;
      $('gerenciar-tecnicos').replaceChildren(Leitura.tecnicos(`Identificador: ${selected.id}`));
      const active = data.conversas.some(c => running.has(c.estado));
      $('gerenciar-excluir-caso').dataset.blocked = String(active);
      $('gerenciar-excluir-caso').title = active ? 'Aguarde o encerramento das execuções deste caso.' : '';
      for (const chat of data.conversas) {
        const rounds = chat.rodadas || [], blocked = running.has(chat.estado);
        $('gerenciar-conversas').append(row(chat.titulo,
          `${Leitura.quantidade(rounds.length, 'rodada')}${blocked ? ' · Execução em andamento' : ''}`,
          'Excluir', () => window.excluirItem({tipo:'conversa', caso:selected.id, conversa:chat.id}, chat.titulo), blocked, chat));
      }
      const owned = new Set(data.conversas.flatMap(c => c.rodadas || []));
      for (const round of selected.rodadas.filter(r => !owned.has(r.id))) {
        const title = `Rodada ${parseInt(round.id.slice(1), 10)}`;
        $('gerenciar-rodadas').append(row(title, selected.titulo,
          'Excluir', () => window.excluirItem({tipo:'rodada', caso:selected.id, rodada:round.id}, title), active, round));
      }
      emptyList('gerenciar-conversas', 'Nenhuma conversa nesta apuração.');
      emptyList('gerenciar-rodadas', 'Nenhuma rodada avulsa nesta apuração.');
    }
    $('gerenciar-lixeira').replaceChildren();
    $('lixeira-contagem').textContent = `${data.lixeira.length} ${data.lixeira.length === 1 ? 'item' : 'itens'}`;
    for (const item of [...data.lixeira].reverse()) {
      const date = new Date(item.excluido_em_utc).toLocaleString('pt-BR');
      const blocked = item.tipo !== 'caso' && data.lixeira.some(i => i.tipo === 'caso' && i.caso === item.caso);
      const title = item.tipo === 'rodada' ? `Rodada ${parseInt(item.rodada.slice(1), 10)}` : item.titulo;
      const caseTitle = data.casos.find(c => c.id === item.caso)?.titulo || data.lixeira.find(c => c.tipo === 'caso' && c.caso === item.caso)?.titulo || 'Apuração preservada';
      $('gerenciar-lixeira').append(row(item.tipo === 'rodada' ? title : `${labels[item.tipo]} · ${title}`,
        `${caseTitle} · Excluído em ${date}${blocked ? ' · Restaure a apuração primeiro' : ''}`,
        'Restaurar', () => mutate('restaurar', {item:item.id}), blocked, item));
    }
    emptyList('gerenciar-lixeira', 'A lixeira está vazia.');
    controls();
  }
  async function load() {
    const version = ++sequence, selected = window.contextoCaso?.() ?? $('gerenciar-caso').value;
    fail();
    try {
      const result = await api('gerenciar-listar', {caso:selected || null});
      if (version !== sequence) return;
      data = result;
      $('gerenciar-caso').replaceChildren(new Option('Selecione uma apuração', ''),
        ...data.casos.map(c => new Option(c.titulo, c.id)));
      if (data.casos.some(c => c.id === selected)) $('gerenciar-caso').value = selected;
      render();
    } catch (error) { if (version === sequence) fail(error.message); }
  }
  async function mutate(operation, scope) {
    if (busy) return false;
    busy = true; controls(); fail();
    try {
      const result = await api(operation, scope);
      $('gerenciar-status').textContent = result.estado === 'restaurado'
        ? `${labels[result.item.tipo]} restaurada: ${result.item.titulo}.`
        : `${labels[result.item.tipo]} movida para a lixeira: ${result.item.titulo}.`;
      window.dispatchEvent(new CustomEvent('acervo-alterado', {detail:result}));
      await load();
      return true;
    } finally { busy = false; controls(); }
  }
  window.excluirItem = async (scope, title) => {
    const dialog = $('excluir-dialogo');
    if (dialog.open || busy) return false;
    $('excluir-titulo').textContent = `Excluir ${labels[scope.tipo].toLowerCase()}?`;
    const effect = scope.tipo === 'caso' ? 'A apuração, suas conversas e rodadas sairão das listas.'
      : scope.tipo === 'conversa' ? 'A conversa, suas perguntas complementares e rodadas sairão das listas.'
      : 'Esta rodada e seus achados sairão das consultas.';
    $('excluir-descricao').textContent = `“${title}” — ${effect}`;
    dialog.returnValue = '';
    const answer = new Promise(resolve => dialog.addEventListener('close', () => resolve(dialog.returnValue), {once:true}));
    dialog.showModal();
    if (await answer !== 'excluir') return false;
    return mutate('excluir', scope);
  };
  $('gerenciar-excluir-caso').addEventListener('click', async () => {
    const selected = data?.casos.find(c => c.id === $('gerenciar-caso').value);
    if (!selected) return;
    try { await window.excluirItem({tipo:'caso', caso:selected.id}, selected.titulo); }
    catch (error) { fail(error.message); }
  });
  $('gerenciar-atualizar').addEventListener('click', load);
  $('gerenciar-caso').addEventListener('change', () => {
    // Do not leave actions for the previous case available during the request.
    $('gerenciar-selecao').hidden = true;
    load();
  });
  window.addEventListener('gerenciar-abrir', load);
})();
