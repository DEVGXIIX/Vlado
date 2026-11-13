'use strict';
// Hosted pilot: guests stay in "Ask the AI"; administrators manage invitations.
// The server enforces every rule; this script only shapes the screen.
(() => {
  const body = document.body;
  if (body.dataset.modo !== 'piloto') return;
  const t = (texto, vars) => (window.I18N ? window.I18N.t(texto, vars) : texto);
  const sair = document.getElementById('mesa-sair');
  sair.hidden = false;
  sair.addEventListener('click', async () => {
    try { await api('sessao-sair', {}); } catch (_) { /* The session is dropped either way. */ }
    window.location.replace('/');
  });

  if (body.dataset.papel !== 'admin') {
    const original = window.showArea;
    window.showArea = () => original('codex');
    const abrir = () => original('codex');
    if (document.readyState === 'complete') abrir(); else window.addEventListener('load', abrir);
    return;
  }

  const painel = $('acesso-painel');
  painel.hidden = false;
  const situacoes = {ativo: 'Ativo', revogado: 'Revogado', expirado: 'Expirado'};

  function mensagem(texto = '') { $('acesso-mensagem').textContent = texto; }
  async function casos() {
    try {
      const dados = await (await fetch('/api/catalogo')).json();
      $('acesso-casos').replaceChildren(...(dados.casos || []).map(c => new Option(c.titulo, c.id)));
    } catch (error) { mensagem(error.message); }
  }
  function item(convite) {
    const linha = element('li');
    const texto = element('span', `Convite de ${convite.nome} · ${t(situacoes[convite.situacao] || convite.situacao)}`);
    linha.append(texto);
    if (convite.situacao === 'ativo') {
      const botao = element('button', 'Revogar', 'secondary');
      botao.type = 'button';
      botao.addEventListener('click', async () => {
        botao.disabled = true;
        try { await api('acesso-revogar', {id: convite.id}); mensagem(t('Convite revogado.')); await listar(); }
        catch (error) { mensagem(error.message); botao.disabled = false; }
      });
      linha.append(' ', botao);
    }
    return linha;
  }
  async function listar() {
    try {
      const {convites} = await api('acesso-listar', {});
      $('acesso-lista').replaceChildren(...(convites.length ? convites.map(item) : [element('li', 'Nenhum convite criado.')]));
    } catch (error) { mensagem(error.message); }
  }
  $('acesso-form').addEventListener('submit', async event => {
    event.preventDefault();
    const escolhidos = [...$('acesso-casos').selectedOptions].map(o => o.value);
    try {
      const resultado = await api('acesso-criar', {nome: $('acesso-nome').value.trim(), casos: escolhidos,
        cota_diaria: Number($('acesso-cota').value), dias: Number($('acesso-dias').value)});
      $('acesso-link').value = resultado.link;
      $('acesso-link').hidden = false; $('acesso-link-aviso').hidden = false;
      $('acesso-link').select();
      $('acesso-nome').value = '';
      mensagem('');
      await listar();
    } catch (error) { mensagem(error.message); }
  });
  casos();
  listar();
})();
