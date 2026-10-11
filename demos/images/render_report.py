"""Create a self-contained visual report from image API evaluation results."""
import argparse
import base64
import html
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('results', type=Path)
parser.add_argument('image_dir', type=Path)
parser.add_argument('--output', type=Path, default=Path('build/image-evaluation/report.html'))
args = parser.parse_args()
report = json.loads(args.results.read_text())
images = args.image_dir
summary = report['summary']
esc = lambda x: html.escape(str(x))
parts = ['''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>OpenDecision image evaluation</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f3f5f8;color:#172334;font:16px/1.55 system-ui,sans-serif}main{max-width:1400px;margin:auto;padding:32px}h1{margin:0;font-size:32px}h2{font-size:22px;margin:0 0 14px}.intro{max-width:900px;color:#526176}.summary{display:flex;gap:16px;flex-wrap:wrap;margin:24px 0}.stat{padding:12px 20px;background:white;border-radius:12px;border:1px solid #dae1ea}.case{background:white;border:1px solid #dae1ea;border-radius:16px;margin:28px 0;padding:24px}.layout{display:grid;grid-template-columns:minmax(260px,40%) 1fr;gap:24px;align-items:start}.photo{position:sticky;top:16px}.photo img{width:100%;max-height:75vh;object-fit:contain;background:#edf0f4;border-radius:10px}.question{padding:16px 0;border-top:1px solid #e5e9ef}.question:first-child{border-top:0;padding-top:0}.label{color:#637186;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.04em}.asked{font-size:18px;font-weight:600;margin:6px 0}.answer{background:#eff5ff;border-radius:8px;padding:12px;margin:10px 0}.options{font-size:14px;color:#526176;margin:8px 0;padding-left:20px}.badge{display:inline-block;border-radius:5px;padding:2px 8px;font-size:12px;font-weight:600}.pass{background:#e7f6ee;color:#16633b}.fail{background:#ffeded;color:#a52424}.unknown{background:#fff4da;color:#785609}.note{font-size:14px;color:#647184}.alarm{padding:12px;border:1px solid #c8d7ed;border-radius:8px;margin-top:14px}pre{font-size:12px;white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f7fa;padding:12px;border-radius:8px}details{margin-top:10px}nav{display:flex;flex-wrap:wrap;gap:8px}nav a{color:#24559b;font-size:14px;text-decoration:none;padding:5px 10px;background:#e7edf7;border-radius:5px}@media(max-width:800px){main{padding:16px}.case{padding:16px}.layout{grid-template-columns:1fr}.photo{position:static}.photo img{max-height:55vh}}@media print{.photo{position:static}.case{break-before:page}.layout{grid-template-columns:40% 1fr}details{display:none}nav{display:none}}
</style><main><h1>Image questions &amp; answers</h1><p class="intro">Actual responses from <strong>google/siglip2-base-patch16-224</strong> through <code>/v1/systemone</code>. Images, exact instructions, candidate captions, and answers appear together below. Captions were refined during testing. The results below come from these sample images.</p>
<div class="summary"><div class="stat"><strong>IMAGE_COUNT</strong> images</div><div class="stat"><strong>QUESTION_COUNT</strong> questions</div></div><p class="note">Scores are uncalibrated. Noul with criteria compares two captions; its 0.5 threshold is a demo policy. The model matches images against the supplied captions. Counting and negation remain unreliable.</p><nav>''']
parts[0] = parts[0].replace('IMAGE_COUNT', str(len(report['cases']))).replace(
    'QUESTION_COUNT', str(sum(len(case['checks']) for case in report['cases'])))
for i,c in enumerate(report['cases']):
    parts.append(f'<a href="#image-{i}">{esc(c["image"])}</a>')
parts.append('</nav>')
for i,case in enumerate(report['cases']):
    path=images/case['image']
    mime='image/png' if path.suffix.lower()=='.png' else 'image/jpeg'
    src=f'data:{mime};base64,'+base64.b64encode(path.read_bytes()).decode('ascii')
    parts.append(f'<section class="case" id="image-{i}"><h2>{esc(case["image"])}</h2><div class="layout"><div class="photo"><img src="{src}" alt="{esc(case["image"])}">')
    if 'api_timing' in case:
        timing = case['api_timing']
        parts.append(f'<p class="note"><strong>API call: {round(timing["median_ms"])} ms</strong> for {timing["question_count"]} questions. Median of five local HTTP calls on an Apple M3 with the model loaded.</p>')
    else:
        parts.append(f'<p class="note">API processing time: {case["seconds"]:.3f} seconds.</p>')
    decision = case.get('decision', case.get('alarm'))
    if decision:
        conditions = decision.get('conditions', {
            'presence_question': 'animal_present', 'choice_question': 'animal_type',
            'target_choice': 'bear'})
        policy = decision['policy']
        rule = (f"{conditions['presence_question']} ≥ {policy['noul_threshold']} AND "
                f"{conditions['choice_question']} = {conditions['target_choice']} AND "
                f"winning type probability ≥ {policy['choice_min_probability']}. Simulated action.")
        parts.append(f'<div class="alarm"><strong>Combined rule: {esc(decision["action"])}</strong><br><span class="note">{esc(rule)}</span><details><summary>Decision trace</summary><pre>{esc(json.dumps(decision,indent=2))}</pre></details></div>')
    parts.append('</div><div>')
    for name,check in case['checks'].items():
        q=case['questions'][name]
        a=case['response']['answers'][name]
        status='pass' if check['passed'] is True else 'fail' if check['passed'] is False else 'unknown'
        badge={'pass':'Matches expectation','fail':'Does not match expectation','unknown':''}[status]
        parts.append(f'<article class="question"><div class="label">{esc(q["type"])} · {esc(name)}</div><div class="asked">{esc(q.get("instructions",q.get("proposition","")))}</div>')
        criteria=q.get('criteria')
        if criteria:
            parts.append('<div class="label">Candidate captions matched to the image</div><ul class="options">')
            for key,value in (criteria.items() if isinstance(criteria,dict) else enumerate(criteria)):
                parts.append(f'<li><strong>{esc(key)}</strong>: {esc(value)}</li>')
            parts.append('</ul>')
        if a['type']=='noul':
            answer=f'{"TRUE" if check["observed"] else "FALSE"}. Noul score {a["noul"]:.4f}'
        elif a['type']=='choice':
            answer=f'{a["choice"]}. Winning probability {a["probabilities"][a["choice"]]:.4f}'
        else:
            answer=json.dumps(a)
        parts.append(f'<div class="answer"><div class="label">Returned answer</div><strong>{esc(answer)}</strong></div>')
        if badge:
            parts.append(f'<span class="badge {status}">{badge}</span>')
        if check['expected'] is not None:
            parts.append(f'<span class="note"> Expected: {esc(check["expected"])}</span>')
        notes = {
            'eagle_present': 'The bird species has not been verified.',
            'bird_kind': 'The bird species has not been verified.',
            'plane_present': 'Contrails are visible in the photo.',
            'backyard_flooded': 'Water is visible in a wooded channel. Its usual water level is unknown.',
            'water_scene': 'Water is visible in a wooded channel.',
        }
        if name in notes:
            parts.append(f'<p class="note">{esc(notes[name])}</p>')
        parts.append(f'<details><summary>Exact question and response JSON</summary><pre>{esc(json.dumps({"question":q,"answer":a},indent=2))}</pre></details></article>')
    parts.append('</div></div></section>')
parts.append('</main></html>')
out = args.output
out.parent.mkdir(parents=True, exist_ok=True)
output = ''.join(parts)
out.write_text(output)
question_count = sum(len(case['checks']) for case in report['cases'])
assert output.count('<img ') == len(report['cases'])
assert output.count('<article ') == question_count
print(f'{out}\n{len(report["cases"])} embedded images, {question_count} question cards; {out.stat().st_size:,} bytes. Self-contained offline report.')
