'use strict';
// Keyboard shortcuts. Ctrl/Cmd+Enter sends the question; J and K (or Alt+↓ and Alt+↑) move
// between findings. Both are listed under "Como começar" in the sidebar.
(() => {
  const announce = message => { $('codex-anuncio').textContent = window.I18N.t(message); };
  $('codex-pergunta').addEventListener('keydown', event => {
    if (event.key !== 'Enter' || !(event.ctrlKey || event.metaKey) || event.altKey || event.shiftKey || event.isComposing) return;
    event.preventDefault();
    // The button carries every reason sending may be blocked: no case, a run in progress, lost tracking.
    if ($('codex-enviar').disabled) { announce('O envio não está disponível agora.'); return; }
    if (!$('codex-pergunta').value.trim()) { announce('Escreva a pergunta antes de enviar.'); return; }
    announce('Pergunta enviada.');
    $('codex-form').requestSubmit();
  });

  const typing = target => Boolean(target?.closest?.('input,textarea,select,[contenteditable="true"],.vditor'));
  function findingStep(event) {
    if (event.ctrlKey || event.metaKey || event.shiftKey) return 0;
    if (event.altKey) return event.key === 'ArrowDown' ? 1 : event.key === 'ArrowUp' ? -1 : 0;
    return event.key === 'j' ? 1 : event.key === 'k' ? -1 : 0;
  }
  document.addEventListener('keydown', event => {
    const step = findingStep(event);
    if (!step || event.defaultPrevented || event.isComposing || typing(event.target)) return;
    if ($('area-achados').hidden || $('mesa-achados').hidden || document.querySelector('dialog[open]')) return;
    const findings = [...$('achados-resultados').querySelectorAll('.finding-open')];
    if (!findings.length) return;
    const current = findings.findIndex(button => button.getAttribute('aria-pressed') === 'true');
    const next = Math.min(findings.length - 1, Math.max(0, current + step));
    event.preventDefault();
    if (next === current) return;
    // The button's own handler opens the finding and moves focus to its heading.
    findings[next].click();
    findings[next].scrollIntoView({block: 'nearest'});
  });
})();
