"""Run private image cases through /v1/systemone and compose an alarm rule.

Without --api-url, exercise the actual FastAPI route in process, loading only
SigLIP2. With --api-url, send the same JSON to a running OpenDecision server.
"""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
from time import perf_counter

import httpx

from opendecision.rules import evaluate_rule


def condition_decision(answers, *, presence_question, choice_question,
                       target_choice, action, otherwise,
                       noul_threshold=.5, choice_min_probability=.6,
                       choice_fact=None):
    """Translate typed answers to facts and reuse the four-valued rule engine."""
    presence = answers.get(presence_question)
    kind = answers.get(choice_question)
    present_status = 'unknown'
    target_status = 'unknown'
    if presence is not None:
        present_status = 'established' if presence['noul'] >= noul_threshold else 'refuted'
    if kind is not None:
        winner = kind['choice']
        if kind['probabilities'][winner] >= choice_min_probability:
            target_status = 'established' if winner == target_choice else 'refuted'
    choice_fact = choice_fact or f'{choice_question}_is_{target_choice}'
    facts = {presence_question: present_status, choice_fact: target_status}
    trace = evaluate_rule({'all': [presence_question, choice_fact]}, facts)
    return {'action': action if trace['status'] == 'established' else otherwise,
            'facts': facts, 'trace': trace,
            'conditions': {'presence_question': presence_question,
                           'choice_question': choice_question,
                           'target_choice': target_choice},
            'policy': {'noul_threshold': noul_threshold,
                       'choice_min_probability': choice_min_probability}}


def alarm_decision(answers, *, noul_threshold=.5, choice_min_probability=.6):
    return condition_decision(
        answers, presence_question='animal_present', choice_question='animal_type',
        target_choice='bear', action='sound_alarm', otherwise='no_alarm',
        choice_fact='animal_is_bear', noul_threshold=noul_threshold,
        choice_min_probability=choice_min_probability,
    )


def evaluate_answers(answers, questions, threshold):
    rows = {}
    for name, spec in questions.items():
        answer = answers[name]
        observed = answer['noul'] >= threshold if answer['type'] == 'noul' else answer['choice']
        expected = spec['expected']
        rows[name] = {'observed': observed, 'expected': expected,
                      'passed': None if expected is None else observed == expected,
                      'note': spec.get('note')}
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image_dir', type=Path)
    parser.add_argument('--questions', type=Path, default=Path(__file__).with_name('questions.json'))
    parser.add_argument('--output', type=Path, default=Path('build/image-evaluation/results.json'))
    parser.add_argument('--api-url', help='Server base URL; omit for in-process API testing.')
    parser.add_argument('--compare-raw-noul', action='store_true',
                        help='Also score Noul statements without true/false criteria.')
    args = parser.parse_args()
    manifest = json.loads(args.questions.read_text())
    threshold = manifest['noul_threshold']
    if args.api_url:
        client = httpx.Client(base_url=args.api_url.rstrip('/'), timeout=600)
    else:
        from fastapi.testclient import TestClient
        from opendecision.api.app import app
        from opendecision import ImageDecisionEngine

        app.state.image_engine = ImageDecisionEngine()
        # No lifespan context: avoid loading the unrelated text model.
        client = TestClient(app)
    report = {'model': 'google/siglip2-base-patch16-224',
              'description': 'Development cases; human visual expectations, not a held-out accuracy benchmark.',
              'cases': []}
    for case in manifest['cases']:
        path = args.image_dir / case['image']
        payload = {'state': {'type': 'image', 'data': base64.b64encode(path.read_bytes()).decode('ascii')},
                   'questions': {name: spec['question'] for name, spec in case['questions'].items()}}
        if args.compare_raw_noul:
            for name, spec in case['questions'].items():
                question = spec['question']
                if question['type'] == 'noul':
                    payload['questions'][f'raw_{name}'] = {
                        'type': 'noul', 'instructions': question['instructions']}
        start = perf_counter()
        response = client.post('/v1/systemone', json=payload)
        response.raise_for_status()
        body = response.json()
        checks = evaluate_answers(body['answers'], case['questions'], threshold)
        result = {'image': case['image'], 'seconds': round(perf_counter() - start, 3),
                  'questions': payload['questions'], 'response': body, 'checks': checks}
        if 'decision' in case:
            result['decision'] = condition_decision(
                body['answers'], **case['decision'], noul_threshold=threshold,
                choice_min_probability=manifest['choice_min_probability'],
            )
        elif 'animal_present' in body['answers'] and 'animal_type' in body['answers']:
            result['decision'] = alarm_decision(
                body['answers'], noul_threshold=threshold,
                choice_min_probability=manifest['choice_min_probability'],
            )
        report['cases'].append(result)
        print(case['image'], {name: row['observed'] for name, row in checks.items()}, flush=True)
        # Write after each case so interrupted runs remain inspectable.
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2)+'\n')
    client.close()
    checks = [check for case in report['cases'] for check in case['checks'].values()]
    report['summary'] = {'scored': sum(c['passed'] is not None for c in checks),
                         'passed': sum(c['passed'] is True for c in checks),
                         'unscored': sum(c['passed'] is None for c in checks)}
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(report['summary'], flush=True)
    print(f'Results: {args.output}', flush=True)


if __name__ == '__main__':
    main()
