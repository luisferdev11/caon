"""Check downloader encoding without invoking network or module-level download loops."""
import ast
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


class DownloadEncodingTests(unittest.TestCase):
    def test_utf8_writers_and_http_failures(self):
        data = [{'team': 'América', 'label': 'Histórico · Posesión'}]
        for module_name, function_name, argument in [('statsbomb', 'get', 'events/1'), ('download_opendata', 'get', 'events/1.json'), ('download_lineups', 'g', 1)]:
            with self.subTest(module=module_name):
                source = Path(__file__).with_name(module_name + '.py').read_text(encoding='utf-8-sig')
                module = ast.parse(source)
                function = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == function_name)
                file = Mock(); file.exists.return_value = False
                class Directory:
                    def __truediv__(self, other): return file
                response = SimpleNamespace(content=json.dumps(data, ensure_ascii=False).encode('utf-8'), raise_for_status=Mock())
                request = Mock(return_value=response)
                scope = dict(CACHE=Directory(), OUT=Directory(), OD=Directory(), API='https://example.invalid', RAW='https://example.invalid',
                             _auth=lambda: (), requests=SimpleNamespace(get=request), json=json)
                exec(compile(ast.Module(body=[function], type_ignores=[]), module_name, 'exec'), scope)
                scope[function_name](argument)
                saved = file.write_text.call_args
                self.assertEqual(saved.kwargs['encoding'], 'utf-8')
                self.assertEqual(json.loads(saved.args[0]), data)
                response.raise_for_status.assert_called_once()
                file.write_text.reset_mock()
                response.raise_for_status.side_effect = RuntimeError('HTTP error')
                with self.assertRaises(RuntimeError): scope[function_name](argument)
                file.write_text.assert_not_called()


if __name__ == '__main__': unittest.main()
