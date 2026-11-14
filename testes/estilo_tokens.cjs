'use strict';
// Style sheet contracts that need no browser: control borders reach 3:1 (WCAG 1.4.11) in both
// themes, each theme has one token set, and text sizes come from one small scale (12px minimum).
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const raiz = path.join(__dirname, '..', 'interface');
const css = fs.readFileSync(path.join(raiz, 'style.css'), 'utf8');

// WCAG relative luminance contrast.
const canal = c => { c /= 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
const luminancia = hex => { const n = parseInt(hex.slice(1, 7), 16); return 0.2126 * canal(n >> 16) + 0.7152 * canal((n >> 8) & 255) + 0.0722 * canal(n & 255); };
const contraste = (a, b) => { const [x, y] = [luminancia(a), luminancia(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };

// Declarations of every block opened by exactly this selector, later blocks winning.
function declaracoes(seletor) {
  const escapado = seletor.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const blocos = [...css.matchAll(new RegExp(`(?:^|[}\\s])${escapado}\\{([^}]*)\\}`, 'g'))].map(m => m[1]);
  return Object.fromEntries(blocos.flatMap(bloco => [...bloco.matchAll(/(--[\w-]+)\s*:\s*([^;]+)/g)].map(m => [m[1], m[2].trim()])));
}
const claro = declaracoes(':root');
const escuro = {...claro, ...declaracoes(':root[data-theme=dark]')};
const cor = (tema, nome) => {
  const valor = tema[`--theme-${nome}`];
  assert.match(String(valor), /^#[0-9a-f]{6}$/i, `--theme-${nome} precisa de uma cor definida no tema`);
  return valor;
};

test('bordas de controles interativos alcançam 3:1 nos dois temas', () => {
  const pares = [
    ['claro', claro, 'input-line', ['surface', 'background', 'soft', 'reading']],
    ['claro', claro, 'danger-line', ['surface', 'reading']],
    ['claro', claro, 'accent-line', ['surface']],
    ['escuro', escuro, 'input-line', ['surface', 'background']],
    ['escuro', escuro, 'danger-line', ['surface']],
    ['escuro', escuro, 'accent-line', ['surface']],
  ];
  for (const [nome, tema, borda, fundos] of pares) {
    for (const fundo of fundos) {
      const razao = contraste(cor(tema, borda), cor(tema, fundo));
      assert.ok(razao >= 3, `${nome}: ${borda} ${cor(tema, borda)} sobre ${fundo} ${cor(tema, fundo)} = ${razao.toFixed(2)} < 3`);
    }
  }
});

test('campos e botões secundários usam a borda de controle, sem cor fixa', () => {
  assert.match(css, /input,select,textarea\{[^}]*border-color:var\(--theme-input-line\)/);
  assert.match(css, /\.secondary\{[^}]*border-color:var\(--theme-input-line\)/);
  assert.match(css, /\.danger\{[^}]*border-color:var\(--theme-danger-line\)/);
});

// Innermost rule blocks, comments removed: {seletor, corpo}.
const regras = [...css.replace(/\/\*[\s\S]*?\*\//g, '').matchAll(/([^{}]+)\{([^{}]*)\}/g)].map(m => ({seletor: m[1].trim(), corpo: m[2]}));
const defineTema = regra => /--theme-[\w-]+\s*:/.test(regra.corpo);
const nomesTema = regra => [...regra.corpo.matchAll(/(--theme-[\w-]+)\s*:/g)].map(m => m[1]).sort();

test('cada tema tem um único conjunto de tokens, com os mesmos nomes', () => {
  const blocos = regras.filter(defineTema);
  assert.deepEqual(blocos.map(b => b.seletor), [':root', ':root[data-theme=dark]']);
  assert.deepEqual(nomesTema(blocos[0]), nomesTema(blocos[1]));
});

test('nenhuma cor fica fora dos tokens: sem valores de reserva nem hexadecimais soltos', () => {
  assert.deepEqual(css.match(/var\(--theme-[\w-]+\s*,/g) || [], [], 'var(--theme-x, reserva)');
  const soltos = regras.filter(r => !defineTema(r)).flatMap(r => (r.corpo.match(/#[0-9a-f]{3,8}\b/gi) || []).map(hex => `${r.seletor} ${hex}`));
  assert.deepEqual(soltos, []);
  const definidos = new Set(nomesTema(regras.find(defineTema)));
  const usados = [...new Set([...css.matchAll(/var\((--theme-[\w-]+)\)/g)].map(m => m[1]))];
  assert.deepEqual(usados.filter(nome => !definidos.has(nome)), [], 'tokens usados sem definição');
  assert.deepEqual(fs.readFileSync(path.join(raiz, 'desktop.js'), 'utf8').match(/#[0-9a-f]{6}\b/gi) || [], [], 'cor fixa em desktop.js');
});

test('texto usa uma escala curta e nunca fica abaixo de 12px', t => {
  const escala = Object.entries(claro).filter(([nome]) => nome.startsWith('--text-'));
  const interface_ = escala.filter(([nome]) => !['--text-quote', '--text-brand'].includes(nome));
  assert.ok(interface_.length >= 6 && interface_.length <= 7, `${interface_.length} degraus de interface`);
  for (const [nome, valor] of escala) {
    assert.match(valor, /^\d+px$/, nome);
    assert.ok(parseInt(valor, 10) >= 12, `${nome}: ${valor}`);
  }
  const fixos = regras.flatMap(r => (r.corpo.match(/font(?:-size)?\s*:[^;]*?\d+px[^;]*/g) || []).map(d => `${r.seletor} { ${d} }`));
  assert.deepEqual(fixos, [], 'tamanho de texto fora da escala');
  t.diagnostic(`escala: ${escala.map(([nome, valor]) => `${nome.slice(7)} ${valor}`).join(', ')}`);
});

module.exports = {css, raiz, declaracoes, claro, escuro, contraste, cor};
