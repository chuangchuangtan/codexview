"""Run a disposable, synthetic CodexView demo; never reads your Codex home."""
import argparse
import json
from pathlib import Path
import runpy
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def message(role, text, timestamp):
    return {'timestamp': timestamp, 'type': 'response_item', 'payload': {
        'type': 'message', 'role': role, 'content': [{'type': 'input_text' if role == 'user' else 'output_text', 'text': text}]}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=17866)
    args = parser.parse_args()
    module = runpy.run_path(str(ROOT / 'codexview'), run_name='codexview_demo')
    with tempfile.TemporaryDirectory(prefix='codexview-demo-') as temporary:
        home = Path(temporary).resolve()
        directory = home / 'sessions/2026/10/01'
        directory.mkdir(parents=True)
        sessions = [
            ('00000000-0000-4000-8000-000000000001', 'Ship a smaller, faster release'),
            ('00000000-0000-4000-8000-000000000002', 'Investigate a failing integration test'),
            ('00000000-0000-4000-8000-000000000003', 'Review the read-only data boundary'),
        ]
        titles = []
        for sid, title in sessions:
            records = [
                message('user', 'Inspect the release pipeline and identify unnecessary work.', '2026-10-01T09:00:00.000Z'),
                message('assistant', '## A smaller path to the first answer\n\nThe session shell loads first. Task metadata and execution evidence follow only when needed.\n\n- Native discovery stays enabled.\n- Source files stay read-only.\n- Review notes remain separate.\n\n```python\nwith open(source, "rb") as stream:\n    record = stream.readline()\n```', '2026-10-01T09:00:10.000Z'),
                message('user', 'Verify the changes and summarize the results.', '2026-10-01T09:05:00.000Z'),
                message('assistant', 'I will check the functional contract, source integrity, and release contents.', '2026-10-01T09:05:03.000Z'),
                {'timestamp': '2026-10-01T09:05:04.000Z', 'type': 'response_item', 'payload': {'type': 'function_call', 'name': 'exec_command', 'call_id': 'demo-check', 'arguments': '{"cmd":"python3 -m unittest discover -s tests -v"}'}},
                {'timestamp': '2026-10-01T09:05:06.000Z', 'type': 'response_item', 'payload': {'type': 'function_call_output', 'call_id': 'demo-check', 'output': 'Synthetic example: functional checks passed. Source hashes unchanged. No external requests.'}},
                message('assistant', '## Ready for review\n\n| Check | Result |\n| --- | --- |\n| Native discovery | Enabled |\n| Source writes | None |\n| Reader window | 3 tasks |\n| Release contents | Public allowlist |\n\nThe release is ready for a **public preview**. First-time full-text search and future record schemas remain explicit limitations.\n\n> These are synthetic demonstration results, not benchmark measurements.', '2026-10-01T09:05:10.000Z'),
                message('user', 'Keep the task list readable on a smaller screen.', '2026-10-01T09:10:00.000Z'),
                message('assistant', 'The navigator uses three compact control rows. The remaining height belongs to tasks, with a mobile drawer and keyboard navigation.', '2026-10-01T09:10:10.000Z'),
            ]
            path = directory / ('rollout-2026-10-01T09-00-00-' + sid + '.jsonl')
            path.write_text(''.join(json.dumps(record) + '\n' for record in records), encoding='utf-8')
            titles.append({'id': sid, 'thread_name': title})
        (home / 'session_index.jsonl').write_text(''.join(json.dumps(x) + '\n' for x in titles), encoding='utf-8')
        runtime = module['runtime'](home)
        module['ensure_rt'](runtime)
        store = module['Store'](home, runtime, [])
        server = module['ThreadingHTTPServer'](('127.0.0.1', args.port), module['App'](store).handler())
        print('Synthetic demo: http://127.0.0.1:' + str(args.port), flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()


if __name__ == '__main__':
    main()
