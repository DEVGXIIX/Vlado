"""Pilot access: invitations, sessions, quotas and per-guest isolation over HTTP. No model calls."""
import http.client
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import acesso
import test_codex_integracao as integracao  # module import: its TestCase is not re-collected here
from interface_pesquisa import Servidor

ORIGEM = 'https://vlado.test'


class AcessoTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        env = patch.dict(os.environ, {'VLADO_ACESSO': ''})
        env.start()
        self.addCleanup(env.stop)

    def test_convite_guarda_so_hash_do_token_e_abre_sessao(self):
        registro, token = acesso.criar_convite(self.root, 'Repórter convidada', casos=['alpha'], cota_diaria=2, dias=7)
        bruto = (self.root / 'acesso/acesso.json').read_text(encoding='utf-8')
        self.assertNotIn(token, bruto)
        self.assertNotIn('token', json.dumps(acesso.listar(self.root)).replace('token_', ''))
        sid, csrf = acesso.aceitar(self.root, token)
        self.assertNotIn(sid, (self.root / 'acesso/acesso.json').read_text(encoding='utf-8'))
        principal = acesso.sessao(self.root, sid)
        self.assertEqual((principal['convite'], principal['papel'], principal['casos'], principal['csrf']),
                         (registro['id'], 'convidado', ['alpha'], csrf))

    def test_token_invalido_revogado_ou_expirado_e_recusado(self):
        with self.assertRaises(ValueError):
            acesso.aceitar(self.root, 'inexistente')
        registro, token = acesso.criar_convite(self.root, 'A', casos=['alpha'])
        sid, _ = acesso.aceitar(self.root, token)
        acesso.revogar(self.root, registro['id'])
        self.assertIsNone(acesso.sessao(self.root, sid))
        with self.assertRaises(ValueError):
            acesso.aceitar(self.root, token)
        _, vencido = acesso.criar_convite(self.root, 'B', casos=['alpha'], dias=1)
        with patch('acesso.agora', return_value=acesso.agora() + acesso.timedelta(days=2)):
            with self.assertRaises(ValueError):
                acesso.aceitar(self.root, vencido)

    def test_cota_diaria_por_convidado_e_admin_sem_cota(self):
        registro, _ = acesso.criar_convite(self.root, 'C', casos=['alpha'], cota_diaria=2)
        acesso.registrar_consulta(self.root, registro['id'])
        acesso.registrar_consulta(self.root, registro['id'])
        with self.assertRaisesRegex(ValueError, 'Limite diário'):
            acesso.registrar_consulta(self.root, registro['id'])
        admin, _ = acesso.criar_convite(self.root, 'Grupo', papel='admin')
        for _ in range(5):
            acesso.registrar_consulta(self.root, admin['id'])

    def test_consulta_devolvida_volta_para_a_cota(self):
        registro, _ = acesso.criar_convite(self.root, 'D', casos=['alpha'], cota_diaria=1)
        acesso.registrar_consulta(self.root, registro['id'])
        acesso.devolver_consulta(self.root, registro['id'])
        acesso.registrar_consulta(self.root, registro['id'])

    def test_registros_simultaneos_nao_perdem_contagem(self):
        registro, _ = acesso.criar_convite(self.root, 'E', casos=['alpha'], cota_diaria=500)
        threads = [threading.Thread(target=acesso.registrar_consulta, args=(self.root, registro['id'])) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(acesso.registrar_consulta(self.root, registro['id']), 21)

    def test_arquivo_de_acesso_corrompido_gera_erro_claro(self):
        (self.root / 'acesso').mkdir()
        (self.root / 'acesso/acesso.json').write_text('[]', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'ilegível'):
            acesso.listar(self.root)

    def test_entradas_invalidas(self):
        for kwargs in ({'nome': ''}, {'nome': 'x', 'papel': 'root'}, {'nome': 'x', 'casos': ['../a']},
                       {'nome': 'x', 'cota_diaria': 0}, {'nome': 'x', 'dias': 0}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    acesso.criar_convite(self.root, **kwargs)


class PilotoHttpTest(unittest.TestCase):
    """Reuses the synthetic cases alpha/beta from the integration fixture."""

    def setUp(self):
        integracao.CodexIntegrationTest.setUp(self)
        env = patch.dict(os.environ, {'VLADO_ACESSO': ''})
        env.start()
        self.addCleanup(env.stop)
        self.server = Servidor(('127.0.0.1', 0), self.root, modo='piloto', origem=ORIGEM)
        self.server.conversas.close()
        self.server.conversas = self.manager
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (self.server.shutdown(), self.server.server_close(), thread.join(3)))
        self.guest, token = acesso.criar_convite(self.root, 'Convidada', casos=['alpha'], cota_diaria=1)
        self.cookie, self.csrf = self.entrar(token)

    def request(self, method, path, body=None, headers=None):
        con = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=15)
        con.request(method, path, body, {'Host': 'vlado.test', **(headers or {})})
        response = con.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        con.close()
        return result

    def entrar(self, token):
        status, headers, _ = self.request('GET', '/convite/' + token)
        self.assertEqual(status, 303)
        cookie = headers['Set-Cookie']
        self.assertIn('HttpOnly', cookie)
        self.assertIn('Secure', cookie)
        self.assertIn('SameSite=Strict', cookie)
        valor = cookie.split(';')[0]
        status, _, page = self.request('GET', '/', headers={'Cookie': valor})
        self.assertEqual(status, 200)
        page = page.decode('utf-8')
        self.assertIn('data-idioma-padrao="en"', page)
        self.assertIn('data-papel="convidado"', page)
        csrf = page.split('name="session-token" content="')[1].split('"')[0]
        return valor, csrf

    def post(self, operation, data, cookie=None, csrf=None, origin=ORIGEM):
        headers = {'Content-Type': 'application/json', 'Cookie': cookie or self.cookie,
                   'X-Session-Token': csrf or self.csrf}
        if origin:
            headers['Origin'] = origin
        status, _, body = self.request('POST', '/api/' + operation, json.dumps(data), headers)
        return status, json.loads(body or b'{}')

    def test_convite_leva_direto_a_pergunta_e_ao_caso_unico(self):
        _, token = acesso.criar_convite(self.root, 'Uma', casos=['alpha'])
        status, headers, _ = self.request('GET', '/convite/' + token)
        self.assertEqual((status, headers['Location']), (303, '/?area=codex&caso=alpha'))
        _, token = acesso.criar_convite(self.root, 'Duas', casos=['alpha', 'beta'])
        status, headers, _ = self.request('GET', '/convite/' + token)
        self.assertEqual((status, headers['Location']), (303, '/?area=codex'))

    def test_arquivos_estaticos_revalidam_com_etag_e_pagina_nao_e_guardada(self):
        status, headers, corpo = self.request('GET', '/style.css')
        self.assertEqual((status, headers['Cache-Control']), (200, 'no-cache'))
        self.assertTrue(corpo)
        etag = headers['ETag']
        status, headers, corpo = self.request('GET', '/style.css', headers={'If-None-Match': etag})
        self.assertEqual((status, corpo, headers['ETag']), (304, b'', etag))
        status, headers, _ = self.request('GET', '/style.css', headers={'If-None-Match': '"outro"'})
        self.assertEqual(status, 200)
        _, headers, _ = self.request('GET', '/', headers={'Cookie': self.cookie})
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertNotIn('ETag', headers)

    def test_sem_convite_nada_e_acessivel_e_saude_responde(self):
        self.assertEqual(self.request('GET', '/')[0], 401)
        self.assertEqual(self.request('GET', '/api/catalogo')[0], 401)
        self.assertEqual(self.request('GET', '/convite/errado')[0], 403)
        status, _, body = self.request('GET', '/saude', headers={'Host': '127.0.0.1:8765'})
        self.assertEqual((status, json.loads(body)), (200, {'ok': True}))
        self.assertEqual(self.request('GET', '/', headers={'Host': 'outro.test', 'Cookie': self.cookie})[0], 403)

    def test_post_exige_origem_publica_csrf_e_sessao(self):
        self.assertEqual(self.post('codex-status', {}, origin='http://127.0.0.1')[0], 403)
        self.assertEqual(self.post('codex-status', {}, origin=None)[0], 403)
        self.assertEqual(self.post('codex-status', {}, csrf='errado')[0], 403)
        self.assertEqual(self.post('codex-status', {}, cookie='vlado_sessao=forjada')[0], 401)
        self.assertEqual(self.post('codex-status', {})[0], 200)

    def test_convidado_ve_so_seus_casos_e_nao_acessa_operacoes_de_administracao(self):
        status, _, body = self.request('GET', '/api/catalogo', headers={'Cookie': self.cookie})
        self.assertEqual([c['id'] for c in json.loads(body)['casos']], ['alpha'])
        for operation in ('cadastrar', 'ia-config', 'ia-config-salvar', 'gerenciar-listar', 'acesso-listar',
                          'codex-desligar', 'buscar', 'caderno-listar', 'lixeira-alcance', 'lixeira-apagar'):
            with self.subTest(operation=operation):
                self.assertEqual(self.post(operation, {'caso': 'alpha'})[0], 403)
        self.assertEqual(self.post('codex-listar', {'caso': 'beta'})[0], 403)
        self.assertEqual(self.post('codex-perguntar', {'caso': 'beta', 'pergunta': 'Teste.'})[0], 403)
        self.assertEqual(self.post('codex-perguntar', {'caso': 'alpha', 'pergunta': 'Teste.',
                                                        'observacoes_humanas': {}})[0], 403)

    def sessao(self, token):
        status, headers, _ = self.request('GET', '/convite/' + token)
        self.assertEqual(status, 303)
        cookie = headers['Set-Cookie'].split(';')[0]
        page = self.request('GET', '/', headers={'Cookie': cookie})[2].decode('utf-8')
        return cookie, page.split('name="session-token" content="')[1].split('"')[0]

    def test_admin_do_piloto_assina_notas_pela_conta_e_conflito_vira_409(self):
        _, token = acesso.criar_convite(self.root, 'Editora', papel='admin')
        cookie, csrf = self.sessao(token)
        status, result = self.post('apuracao-nota-salvar', {'caso': 'alpha', 'requisicao_id': 'a' * 32,
                                                             'titulo': 'Nota', 'texto': 'Texto.'}, cookie, csrf)
        self.assertEqual(status, 200, result)
        nota = result['nota']
        self.assertEqual(nota['criado_por']['nome'], 'Editora')
        self.assertEqual(nota['criado_por']['origem'], 'conta_autenticada_da_mesa')
        status, result = self.post('apuracao-nota-salvar', {'caso': 'alpha', 'requisicao_id': 'b' * 32,
                                                             'nota_id': nota['id'], 'revisao_nota': nota['revisao'] + 5,
                                                             'titulo': 'Nota', 'texto': 'Outro.'}, cookie, csrf)
        self.assertEqual(status, 409, result)
        self.assertEqual(result['codigo'], 'conflito')
        self.assertEqual(result['atual']['revisao'], nota['revisao'])
        status, result = self.post('apuracao-notas', {'caso': 'alpha'}, cookie, csrf)
        self.assertEqual([n['titulo'] for n in result['notas']], ['Nota'])
        self.assertNotIn('texto', result['notas'][0])
        self.assertEqual(self.post('apuracao-nota-salvar', {'caso': 'alpha'})[0], 403)

    def test_erros_trazem_codigo_estavel_para_a_interface_traduzir(self):
        status, _, body = self.request('GET', '/api/catalogo')
        self.assertEqual((status, json.loads(body)['codigo']), (401, 'sessao_expirada'))
        status, result = self.post('ia-config', {})
        self.assertEqual((status, result['codigo']), (403, 'operacao_proibida'))
        self.assertIn('não permitida', result['erro'])  # the Portuguese message is unchanged
        self.assertEqual(self.post('codex-listar', {'caso': 'beta'})[1]['codigo'], 'caso_nao_liberado')
        self.assertEqual(self.post('codex-status', {}, csrf='errado')[1]['codigo'], 'origem_nao_autorizada')
        status, result = self.post('codex-perguntar', {'caso': 'alpha', 'pergunta': 'Pergunta sintética.'})
        self.assertEqual(status, 200, result)
        self.assertTrue(self.manager.rpc.ready.wait(30))
        status, erro = self.post('codex-perguntar', {'caso': 'alpha', 'pergunta': 'Outra.'})
        self.assertEqual((status, erro['codigo'], erro['parametros']), (400, 'cota_diaria_esgotada', {'cota': 1}))
        self.manager.cancelar(result['conversa'])

    def test_convidado_nao_envia_corpo_grande_nem_em_operacao_de_cadastro(self):
        headers = {'Content-Type': 'application/json', 'Cookie': self.cookie, 'X-Session-Token': self.csrf,
                   'Origin': ORIGEM}
        status, _, body = self.request('POST', '/api/cadastrar', b'{"x": "' + b'a' * 40000 + b'"}', headers)
        self.assertEqual(status, 400)
        self.assertIn('muito grande', json.loads(body)['erro'])

    def test_retomar_do_convidado_devolve_a_cota_quando_recusada(self):
        self.assertEqual(self.post('codex-retomar', {'conversa': '0' * 32, 'caso': 'alpha'})[0], 403)
        status, result = self.post('codex-retomar', {'conversa': '0' * 32})
        self.assertEqual(status, 400, result)
        self.assertIn('indisponível', result['erro'])
        status, result = self.post('codex-perguntar', {'caso': 'alpha', 'pergunta': 'Pergunta sintética.'})
        self.assertEqual(status, 200, result)  # the refused retry gave the only daily question back
        self.assertTrue(self.manager.rpc.ready.wait(30))
        self.manager.cancelar(result['conversa'])

    def test_registro_de_acesso_corrompido_responde_503(self):
        (self.root / 'acesso/acesso.json').write_text('{quebrado', encoding='utf-8')
        self.assertEqual(self.request('GET', '/', headers={'Cookie': self.cookie})[0], 503)
        self.assertEqual(self.post('codex-status', {})[0], 503)

    def test_conversas_isoladas_por_convidado_cota_e_revogacao(self):
        status, result = self.post('codex-perguntar', {'caso': 'alpha', 'pergunta': ''})
        self.assertEqual(status, 400)  # refused question does not spend the daily quota
        status, result = self.post('codex-perguntar', {'caso': 'alpha', 'pergunta': 'Pergunta sintética.'})
        self.assertEqual(status, 200, result)
        conversa = result['conversa']
        self.assertTrue(self.manager.rpc.ready.wait(30))
        self.assertEqual(self.post('codex-listar', {'caso': 'alpha'})[1]['conversas'][0]['id'], conversa)
        self.assertEqual(self.post('codex-eventos', {'conversa': conversa})[0], 200)
        status, result = self.post('codex-perguntar', {'caso': 'alpha', 'pergunta': 'Outra.'})
        self.assertEqual(status, 400)
        self.assertIn('Limite diário', result['erro'])
        outro, token = acesso.criar_convite(self.root, 'Outro', casos=['alpha'])
        cookie, csrf = self.entrar(token)
        self.assertEqual(self.post('codex-listar', {'caso': 'alpha'}, cookie, csrf)[1]['conversas'], [])
        for operation in ('codex-eventos', 'codex-cancelar', 'codex-original'):
            with self.subTest(operation=operation):
                status, result = self.post(operation, {'conversa': conversa, 'referencia': '0' * 64}, cookie, csrf)
                self.assertEqual(status, 400)
                self.assertIn('indisponível', result['erro'])
        acesso.revogar(self.root, outro['id'])
        self.assertEqual(self.post('codex-listar', {'caso': 'alpha'}, cookie, csrf)[0], 401)
        self.manager.cancelar(conversa)

    def test_administrador_gerencia_convites_pela_interface(self):
        admin, token = acesso.criar_convite(self.root, 'Grupo', papel='admin')
        cookie, csrf = self.entrar_admin(token)
        status, result = self.post('acesso-criar', {'nome': 'Nova', 'casos': ['alpha'], 'cota_diaria': 3, 'dias': 5},
                                   cookie, csrf)
        self.assertEqual(status, 200, result)
        self.assertTrue(result['link'].startswith(ORIGEM + '/convite/'))
        listados = self.post('acesso-listar', {}, cookie, csrf)[1]['convites']
        self.assertIn('Nova', [c['nome'] for c in listados])
        self.assertNotIn(result['link'].rsplit('/', 1)[1], json.dumps(listados))
        self.assertEqual(self.post('acesso-revogar', {'id': result['convite']['id']}, cookie, csrf)[0], 200)
        self.assertNotEqual(self.post('ia-config', {}, cookie, csrf)[0], 403)  # fixture config has no provider
        self.assertEqual(self.post('codex-desligar', {}, cookie, csrf)[0], 403)

    def entrar_admin(self, token):
        status, headers, _ = self.request('GET', '/convite/' + token)
        cookie = headers['Set-Cookie'].split(';')[0]
        page = self.request('GET', '/', headers={'Cookie': cookie})[2].decode('utf-8')
        self.assertIn('data-papel="admin"', page)
        return cookie, page.split('name="session-token" content="')[1].split('"')[0]


if __name__ == '__main__':
    unittest.main()
