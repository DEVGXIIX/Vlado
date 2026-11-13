'use strict';
(() => {
  const dialog = $('revisao-dialogo');
  let session = null, sequence = 0, saving = false, ready = false;
  function fail(message = '') {
    $('revisao-erro').textContent = message; $('revisao-erro').hidden = !message;
  }
  function controls() {
    for (const control of $('revisao-form').elements) control.disabled = saving || !ready;
    $('revisao-fechar').disabled = saving;
  }
  function describe() {
    $('revisao-significado').textContent = humanReviewStates[$('revisao-estado').value][1];
    $('revisao-caracteres').textContent = `${$('revisao-observacao').value.length} de 500 caracteres`;
  }
  function history(mark) {
    const list = element('div');
    for (const event of mark.historico || []) {
      list.append(element('p', `${new Date(event.em_utc).toLocaleString('pt-BR')} · ${humanReviewStates[event.estado][0]}${event.observacao ? ' · ' + event.observacao : ''}`, 'small human-review-note'));
    }
    $('revisao-historico').replaceChildren(Leitura.tecnicos(
      element('p', 'As marcações são declarações registradas pela interface, sem autenticação individual do jornalista.', 'small'),
      list, element('pre', JSON.stringify(mark, null, 2), 'raw-briefing')));
  }
  window.conferirAchado = async (item, scope, version) => {
    if (saving) return;
    const request = ++sequence;
    ready = false; session = null; fail(); controls();
    $('revisao-afirmacao').textContent = item.redacao;
    $('revisao-fontes').replaceChildren(element('p', 'Abrindo os trechos citados…', 'small'));
    $('revisao-situacao').textContent = 'Carregando a marcação atual e as fontes.';
    $('revisao-historico').replaceChildren();
    $('revisao-estado').value = 'pendente'; $('revisao-observacao').value = ''; describe();
    if (!dialog.open) dialog.showModal();
    try {
      const detail = await api('achados-detalhe', {...scope, achado_id:item.id});
      if (request !== sequence || !dialog.open) return;
      const claim = detail.achado, mark = claim.revisao_humana;
      session = {scope:{...scope}, version, item:claim, mark, hash:detail.registros_sha256};
      $('revisao-afirmacao').textContent = claim.redacao;
      $('revisao-estado').value = mark.estado; $('revisao-observacao').value = mark.observacao;
      describe(); history(mark);
      $('revisao-fontes').replaceChildren();
      const evidences = claim.evidencias.filter(e => claim.vinculos.some(link => link.evidencia_id === e.id));
      if (!evidences.length) $('revisao-fontes').append(element('p', 'Este achado não tem trechos vinculados nesta revisão. Você pode registrar uma pendência, um ajuste ou suporte insuficiente.', 'notice'));
      const loaded = await Promise.allSettled(evidences.map(async evidence => {
        const block = element('article', undefined, 'review-evidence');
        const roles = claim.vinculos.filter(link => link.evidencia_id === evidence.id).map(link => pretty(link.papel));
        block.append(element('h4', Leitura.fonte({...evidence, ...evidence.localizador})),
          element('p', roles.join(' · '), 'small'),
          element('blockquote', evidence.trecho || 'Leitura visual registrada; consulte o original.'),
          element('p', evidence.contexto, 'small'));
        const feedback = element('p', '', 'small'); feedback.setAttribute('role', 'status');
        const original = element('button', 'Conferir original', 'secondary'); original.type = 'button';
        original.addEventListener('click', async () => {
          original.disabled = true;
          try {
            const blob = await api('achados-original', {...scope, evidencia_id:evidence.id}, true);
            await window.abrirOriginal(blob, evidence.original.split('/').pop(),evidence.pagina_pdf || evidence.localizador?.pagina_pdf, claim.redacao + '\n\n' + (evidence.trecho || 'Fonte visual: confira o original.'));
          } catch (error) { feedback.textContent = error.message; }
          finally { original.disabled = false; }
        });
        block.append(original, feedback); $('revisao-fontes').append(block);
        try {
          const result = await api('achados-evidencia', {...scope, evidencia_id:evidence.id});
          if (result.contexto) {
            const context = element('details', undefined, 'review-context');
            const text = element('div', undefined, 'context');
            for (const line of result.contexto) text.append(element('p', line.texto));
            context.append(element('summary', 'Ler contexto da fonte'), text); block.append(context);
          } else block.append(element('p', 'Fonte visual: confira a página no original.', 'small'));
          block.append(Leitura.tecnicos(element('pre', JSON.stringify(result.evidencia, null, 2), 'raw-briefing')));
        } catch (error) {
          block.append(element('p', `Não foi possível recuperar esta fonte: ${error.message}`, 'notice'));
          throw error;
        }
      }));
      if (request !== sequence || !dialog.open) return;
      ready = true; controls();
      const canConfirm = evidences.length > 0 && loaded.every(result => result.status === 'fulfilled');
      $('revisao-estado').querySelector('[value="conferida_no_original"]').disabled = !canConfirm;
      $('revisao-situacao').textContent = 'A marcação vale para este achado, nesta revisão. O texto da IA será preservado.';
    } catch (error) {
      if (request === sequence && dialog.open) { fail(error.message); $('revisao-situacao').textContent = 'Não foi possível abrir a conferência.'; }
    }
  };
  $('revisao-estado').addEventListener('change', describe);
  $('revisao-observacao').addEventListener('input', describe);
  $('revisao-fechar').addEventListener('click', () => { if (!saving) dialog.close(); });
  dialog.addEventListener('cancel', event => { if (saving) event.preventDefault(); });
  dialog.addEventListener('close', () => { ++sequence; session = null; ready = false; });
  $('revisao-form').addEventListener('submit', async event => {
    event.preventDefault(); if (!session || !ready || saving) return;
    const captured = session;
    saving = true; controls(); fail(); $('revisao-situacao').textContent = 'Salvando sua marcação…';
    try {
      const result = await api('achados-revisao-salvar', {...captured.scope,
        achado_id:captured.item.id, achado_versao:captured.item.versao,
        registros_sha256:captured.hash, anterior:captured.mark.evento_id,
        estado:$('revisao-estado').value, observacao:$('revisao-observacao').value});
      dialog.close();
      const current = findingQuery;
      if (current && captured.version === findingEpoch &&
          ['caso','rodada','revisao','geracao_achados'].every(key => current[key] === captured.scope[key])) {
        await searchFindings({...current});
        $('achados-revisao-feedback').textContent = `Marcação salva: ${humanReviewStates[result.revisao_humana.estado][0]}. O texto original da IA foi preservado.`;
      }
    } catch (error) {
      fail(error.message); $('revisao-situacao').textContent = 'A marcação não foi confirmada. Sua observação continua no formulário.';
    } finally { saving = false; controls(); }
  });
  $('achados-marcacao').addEventListener('change', () => {
    $('achados-so-pendentes').setAttribute('aria-pressed', String($('achados-marcacao').value === 'pendente'));
    if ($('achados-geracao').value) searchFindings({...findingScope(), filtros:findingFilters(), limite:Number($('achados-limite').value), deslocamento:0});
  });
  $('achados-so-pendentes').addEventListener('click', () => {
    $('achados-marcacao').value = $('achados-marcacao').value === 'pendente' ? '' : 'pendente';
    $('achados-marcacao').dispatchEvent(new Event('change'));
  });
})();
