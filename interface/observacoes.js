'use strict';
(() => {
  const selected = new Map();
  let scope = null, busy = false;
  const choices = () => $('achados-resultados').querySelectorAll('input[data-observacao-achado]');
  function error(message = '') {
    $('observacoes-erro').textContent = message; $('observacoes-erro').hidden = !message;
  }
  function controls() {
    $('observacoes-contagem').textContent = selected.size ? Leitura.quantidade(selected.size, 'observação selecionada', 'observações selecionadas') + '.' : 'Nenhuma observação selecionada.';
    $('observacoes-continuar').disabled = busy || !selected.size;
    $('observacoes-limpar').disabled = busy || !selected.size;
    for (const input of choices()) {
      input.disabled = busy;
      input.checked = selected.has(input.dataset.observacaoAchado);
    }
  }
  window.limparObservacoes = () => {
    selected.clear(); scope = null; error(); controls();
  };
  window.observacoesAchado = (item, query) => {
    if (!item.revisao_humana?.evento_id) return null;
    const current = Object.fromEntries(['caso','rodada','revisao','geracao_achados'].map(key => [key,query[key]]));
    if (scope && JSON.stringify(scope) !== JSON.stringify(current)) window.limparObservacoes();
    scope = current;
    const previous = selected.get(item.id);
    if (previous && (previous.evento_id !== item.revisao_humana.evento_id || previous.achado_versao !== item.versao)) {
      selected.delete(item.id); error('Uma marcação selecionada mudou. Confira e selecione novamente.');
    }
    const label = element('label', undefined, 'feedback-choice'), input = element('input');
    input.dataset.observacaoAchado = item.id;
    input.type = 'checkbox'; input.checked = selected.has(item.id); input.disabled = busy;
    input.setAttribute('aria-label', `Levar observação para a próxima pergunta: ${item.redacao}`);
    input.addEventListener('change', () => {
      if (busy || JSON.stringify(scope) !== JSON.stringify(current)) { controls(); return; }
      error();
      if (input.checked) {
        if (selected.size >= 20) { input.checked = false; error('Selecione até 20 observações por pergunta.'); return; }
        selected.set(item.id, {achado_id:item.id, achado_versao:item.versao,
          evento_id:item.revisao_humana.evento_id, registros_sha256:findingResult.registros_sha256});
      } else selected.delete(item.id);
      controls();
    });
    label.append(input, element('span', 'Levar à próxima pergunta')); controls();
    return label;
  };
  window.mostrarObservacoes = (container, data, sourceScope) => {
    container.replaceChildren();
    for (const item of data.observacoes) {
      const entry = element('article', undefined, 'feedback-item');
      entry.append(element('p', humanReviewStates[item.estado][0], 'meta'),
        element('blockquote', item.redacao_anterior),
        element('p', item.observacao || 'Marcação sem observação adicional.', 'human-review-note'));
      const sources = element('details'), list = element('div');
      sources.append(element('summary', Leitura.quantidade(item.fontes.length, 'fonte vinculada', 'fontes vinculadas')), list);
      for (const evidence of item.fontes) {
        const block = element('div', undefined, 'feedback-source');
        block.append(element('p', Leitura.fonte({...evidence,...evidence.localizador}), 'small'),
          element('blockquote', evidence.trecho || 'Fonte visual: confira o original.'));
        const downloadSource = element('button','Baixar original','secondary'), feedback = element('p','','small');
        downloadSource.type = 'button'; feedback.setAttribute('role','status');
        downloadSource.addEventListener('click', async () => {
          downloadSource.disabled = true;
          try { download(await api('achados-original', {...sourceScope,evidencia_id:evidence.id}, true), evidence.original.split('/').pop()); }
          catch (failure) { feedback.textContent = failure.message; }
          finally { downloadSource.disabled = false; }
        });
        block.append(downloadSource, feedback); list.append(block);
      }
      if (!item.fontes.length) list.append(element('p','A marcação não tem fonte vinculada. O modelo deverá declarar essa limitação.','small'));
      entry.append(sources, Leitura.tecnicos(`${sourceScope.caso}/${sourceScope.rodada}/${sourceScope.revisao} · ${item.achado_id}@v${item.achado_versao} · marcação ${item.evento_id}`));
      container.append(entry);
    }
  };
  $('observacoes-limpar').addEventListener('click', window.limparObservacoes);
  $('observacoes-continuar').addEventListener('click', async () => {
    if (busy || !scope || !selected.size) return;
    const version = findingEpoch;
    const request = {...scope, selecoes:[...selected.values()]};
    busy = true; error(); controls();
    try {
      const preview = await api('codex-observacoes', request);
      if (version !== findingEpoch) return;
      await window.continuarComObservacoes(preview, request);
    } catch (failure) { if (version === findingEpoch) error(failure.message); }
    finally { busy = false; controls(); }
  });
})();
