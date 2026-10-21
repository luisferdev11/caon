"""Pruebas del laboratorio de jugadas por texto (A9, AC-10)."""
import json
import pathlib
import socket
import sys
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import nlplay, openrouter
from app.env import load_env
from app.play_rules import PlayParseError, parse_rules
from app.play_schema import Play

FIX = json.loads((ROOT / 'pipeline' / 'fixtures' / 'nl_phrases.json').read_text(encoding='utf-8'))
SHAPE = FIX['shape']
FAKE_KEY = 'sk-or-v1-TESTSECRET123'


def phrase_ok(play, lab):
    """True si tipos, zonas etiquetadas, reanudación y desenlace coinciden."""
    types = [s['type'] for s in play['steps']]
    if types != lab['types'] or play['start']['restart'] != lab['restart']:
        return False
    for step, zone in zip(play['steps'], lab['zones']):
        if zone is not None and step['zone'] != zone:
            return False
    return play['steps'][-1].get('outcome') == lab['outcome'] or lab['outcome'] is None


def app_client():
    app = FastAPI()
    app.include_router(nlplay.router)
    return TestClient(app)


class RulesTests(unittest.TestCase):
    def test_fixture_has_30_phrases(self):
        self.assertGreaterEqual(len(FIX['phrases']), 30)

    def test_accuracy_at_least_90(self):
        fails = []
        for lab in FIX['phrases']:
            play = parse_rules(lab['text'], SHAPE).model_dump()
            if not phrase_ok(play, lab):
                fails.append((lab['text'], [(s['type'], s['zone']) for s in play['steps']], play['start']['restart']))
        acc = 1 - len(fails) / len(FIX['phrases'])
        self.assertGreaterEqual(acc, 0.9, '\n'.join(map(str, fails)))

    def test_actor_by_number_and_surname(self):
        play = parse_rules('Calderón conduce por banda izquierda y el 10 dispara: gol', SHAPE)
        self.assertEqual(play.steps[0].actor.name, 'Cristian Calderón')
        self.assertEqual(play.steps[1].actor.num, 10)

    def test_defaults_are_assumptions(self):
        play = parse_rules('dispara: gol', SHAPE)
        self.assertTrue(play.assumptions)

    def test_unknown_raises_with_suggestions(self):
        with self.assertRaises(PlayParseError) as cm:
            parse_rules('hola qué tal', SHAPE)
        self.assertTrue(cm.exception.suggestions)

    def test_validates_against_schema(self):
        play = parse_rules(FIX['phrases'][0]['text'], SHAPE)
        Play.model_validate(play.model_dump())
        self.assertEqual(play.schema_id, 'play.v1')


class EnvTests(unittest.TestCase):
    def test_load_env_parses_without_printing(self):
        p = ROOT / 'pipeline' / 'fixtures' / '_tmp_env'
        p.write_text('A=1\n# c\nB="dos"\n', encoding='utf-8')
        try:
            self.assertEqual(load_env(p), {'A': '1', 'B': 'dos'})
        finally:
            p.unlink()

    def test_missing_env_file(self):
        self.assertEqual(load_env(ROOT / 'no_existe.env'), {})


GOOD_LLM = {'start': {'restart': 'open'}, 'steps': [
    {'type': 'cross', 'actor': {'num': 10}, 'zone': 'segundo_palo'},
    {'type': 'header', 'actor': {'num': 9}, 'zone': 'segundo_palo', 'outcome': 'gol'}]}


def fake_post(content):
    def post(url, headers, body, timeout):
        return {'choices': [{'message': {'content': content}}], 'usage': {'cost': 0.0001}}
    return post


class LLMTests(unittest.TestCase):
    def test_llm_valid_json(self):
        play, _usage = openrouter.parse_llm('el 10 centra', FAKE_KEY, 'm', post=fake_post(json.dumps(GOOD_LLM)))
        self.assertEqual(play.source, 'llm')
        self.assertEqual([s.type for s in play.steps], ['cross', 'header'])

    def test_llm_invalid_json_raises(self):
        with self.assertRaises(openrouter.LLMError):
            openrouter.parse_llm('x', FAKE_KEY, 'm', post=fake_post('no es json'))

    def test_input_truncated_500(self):
        seen = {}

        def post(url, headers, body, timeout):
            seen['body'] = body
            return {'choices': [{'message': {'content': json.dumps(GOOD_LLM)}}]}
        openrouter.parse_llm('a' * 900, FAKE_KEY, 'm', post=post)
        self.assertNotIn('a' * 501, json.dumps(seen['body']))

    def test_fallback_no_key(self):
        with patch('app.nlplay.api_key', return_value=None):
            r = nlplay.parse_play({'text': 'el 10 centra al segundo palo y el 9 cabecea: gol', 'mode': 'llm'}, SHAPE)
        self.assertEqual(r['source'], 'rules')
        self.assertIn('llm_sin_key', r['warnings'])

    def test_fallback_timeout_and_invalid(self):
        def timeout_post(*a, **k):
            raise socket.timeout('timed out')  # noqa: UP041 (py3.9)
        for post, code in ((timeout_post, 'llm_fallo'), (fake_post('{"steps": 5}'), 'llm_fallo')):
            with patch('app.nlplay.api_key', return_value=FAKE_KEY), patch('app.openrouter.http_post', post):
                r = nlplay.parse_play({'text': 'el 10 centra y el 9 cabecea: gol', 'mode': 'llm'}, SHAPE)
            self.assertEqual(r['source'], 'rules')
            self.assertIn(code, r['warnings'])
            self.assertNotIn(FAKE_KEY, json.dumps(r))

    def test_auto_prefers_rules_and_uses_llm_when_rules_fail(self):
        with patch('app.nlplay.api_key', return_value=FAKE_KEY), \
                patch('app.openrouter.http_post', fake_post(json.dumps(GOOD_LLM))):
            ok = nlplay.parse_play({'text': 'el 10 centra al segundo palo y el 9 cabecea: gol', 'mode': 'auto'}, SHAPE)
            hard = nlplay.parse_play({'text': 'un balón bombeado que termina en la red', 'mode': 'auto'}, SHAPE)
        self.assertEqual(ok['source'], 'rules')
        self.assertEqual(hard['source'], 'llm')

    def test_auto_unknown_without_key_raises(self):
        with patch('app.nlplay.api_key', return_value=None), self.assertRaises(PlayParseError):
            nlplay.parse_play({'text': 'buenos días', 'mode': 'auto'}, SHAPE)


class RouterTests(unittest.TestCase):
    def test_parse_endpoint_rules(self):
        with patch('app.nlplay.team_shape', return_value=SHAPE):
            r = app_client().post('/api/play/parse', json={'text': 'el 10 centra al segundo palo y el 9 cabecea: gol', 'mode': 'rules'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['schema_id'], 'play.v1')

    def test_parse_endpoint_422(self):
        with patch('app.nlplay.team_shape', return_value=SHAPE):
            r = app_client().post('/api/play/parse', json={'text': 'buenos días', 'mode': 'rules'})
        self.assertEqual(r.status_code, 422)
        self.assertTrue(r.json()['detail']['sugerencias'])

    def test_capabilities_never_returns_key(self):
        with patch('app.nlplay.api_key', return_value=FAKE_KEY):
            r = app_client().get('/api/play/capabilities')
        self.assertTrue(r.json()['llm'])
        self.assertNotIn(FAKE_KEY, r.text)


if __name__ == '__main__':
    unittest.main()
