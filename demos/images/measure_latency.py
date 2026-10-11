"""Measure local HTTP API calls with loaded models and repeatable payloads."""
from __future__ import annotations

import argparse
import base64
import json
import platform
import socket
import statistics
import subprocess
import threading
import time
from pathlib import Path

import httpx
import uvicorn


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image_dir', type=Path)
    parser.add_argument('--repeats', type=int, default=5)
    parser.add_argument('--output', type=Path, default=Path('build/image-evaluation/api-timings.json'))
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error('--repeats must be positive')

    from opendecision import ImageDecisionEngine, OpenDecisionEngine
    from opendecision.api.app import app

    app.state.engine = OpenDecisionEngine()
    app.state.model_name = app.state.engine.model_name
    app.state.image_engine = ImageDecisionEngine()
    manifest = json.loads(Path(__file__).with_name('questions.json').read_text())
    requests = {'customer_routing': {
        'state': 'I was charged twice and I need this fixed before my meeting this afternoon.',
        'questions': {
            'department': {'type': 'choice', 'instructions': 'Which department should handle this?',
                           'criteria': {'billing': 'Payments and refunds', 'technical': 'Software problems', 'sales': 'Purchasing questions'}},
            'urgent': {'type': 'noul', 'instructions': 'Is this request urgent?',
                       'criteria': {'true': 'The customer needs the issue resolved before a meeting this afternoon.',
                                    'false': 'The customer has no deadline and can wait.'}},
        },
    }}
    for case in manifest['cases']:
        data = base64.b64encode((args.image_dir / case['image']).read_bytes()).decode('ascii')
        requests[case['image']] = {
            'state': {'type': 'image', 'data': data},
            'questions': {key: spec['question'] for key, spec in case['questions'].items()},
        }
    featured = {'PXL_20250524_124127738.jpg': ['animal_present', 'animal_type'],
                'binn.jpg': ['bin_present', 'bin_condition', 'ground_litter'],
                'fenn.jpg': ['fence_present', 'fence_condition']}
    for image, names in featured.items():
        payload = requests[image]
        requests[f'featured:{image}'] = {**payload, 'questions': {name: payload['questions'][name] for name in names}}

    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    port = listener.getsockname()[1]
    config = uvicorn.Config(app, lifespan='off', log_level='error', access_log=False)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, kwargs={'sockets': [listener]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 30
        while not server.started:
            if not thread.is_alive() or time.monotonic() > deadline:
                raise RuntimeError('Local timing server failed to start.')
            time.sleep(.05)
        hardware = platform.machine()
        if platform.system() == 'Darwin':
            hardware = subprocess.check_output(['sysctl', '-n', 'machdep.cpu.brand_string'], text=True).strip()
        report = {'hardware': hardware, 'device': str(app.state.image_engine.model.device),
                  'method': 'Client HTTP round-trip on loopback, including JSON serialization and response parsing. Models preloaded. One unmeasured warmup per payload. Sequential requests.',
                  'repeats': args.repeats, 'cases': {}}
        with httpx.Client(base_url=f'http://127.0.0.1:{port}', timeout=120, trust_env=False) as client:
            for name, payload in requests.items():
                warmup = client.post('/v1/systemone', json=payload)
                warmup.raise_for_status()
                samples = []
                for _ in range(args.repeats):
                    start = time.perf_counter()
                    response = client.post('/v1/systemone', json=payload)
                    response.raise_for_status()
                    body = response.json()
                    samples.append((time.perf_counter() - start) * 1000)
                result = {'question_count': len(payload['questions']),
                          'median_ms': round(statistics.median(samples), 1),
                          'min_ms': round(min(samples), 1), 'max_ms': round(max(samples), 1),
                          'samples_ms': [round(s, 1) for s in samples],
                          'request': {'state': {'type': 'image', 'file': name.removeprefix('featured:')} if isinstance(payload['state'], dict) else payload['state'],
                                      'questions': payload['questions']},
                          'response': body}
                report['cases'][name] = result
                print(f'{name}: {result["median_ms"]} ms ({result["question_count"]} questions)', flush=True)
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(report, indent=2)+'\n')
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()
    print(args.output)


if __name__ == '__main__':
    main()
