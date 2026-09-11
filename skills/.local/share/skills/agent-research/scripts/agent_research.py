#!/usr/bin/env python3
"""Bounded weekly research with durable reports and no automatic workflow edits."""
import argparse
import fcntl
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

ASSETS = Path(__file__).resolve().parent.parent
DEFAULTS = dict(model='gpt-5.6-sol', effort='medium', timeout_seconds=900,
                max_web_calls=40, timezone='America/Los_Angeles', weekday=4, hour=9,
                codex='codex', enabled=True)
RATES = {'gpt-5.6-sol': (4.0, 0.4, 20.0)}
PRICE_SOURCE = 'https://developers.openai.com/api/docs/models/gpt-5.6-sol'
COST_NOTE = ('API-equivalent token estimate at base rates, not an invoice. '
             'Excludes search fees and any large-context or cache-write surcharges. '
             'Unknown usage is not counted as zero. Rates checked 2026-09-11.')


def utc_now():
    return datetime.now(timezone.utc)


def iso(value):
    return value.astimezone(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def date(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    with temp.open('w') as handle:
        json.dump(value, handle, indent=2)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    temp.replace(path)


def read_json(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def next_due(now, zone, weekday, hour):
    local = now.astimezone(ZoneInfo(zone))
    due = local.replace(hour=hour, minute=0, second=0, microsecond=0)
    due += timedelta(days=(weekday - local.weekday()) % 7)
    if due <= local:
        due += timedelta(days=7)
    return iso(due)


def is_due(state, now):
    if state.get('retry_after') and date(state['retry_after']) > now:
        return False
    return state.get('status') == 'running' or not state.get('next_due_at') or date(state['next_due_at']) <= now


def source_key(url, version):
    parts = urlsplit(url)
    if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password:
        raise ValueError(f'Invalid source URL {url!r}; use a public HTTPS source')
    if parts.hostname in ('arxiv.org', 'www.arxiv.org'):
        match = re.search(r'/(?:abs|html|pdf)/(\d{4}\.\d{4,5})(v\d+)?', parts.path)
        if match:
            return f'arxiv:{match[1]}:{match[2] or version}'
    query = urlencode(sorted((k, v) for k, v in parse_qsl(parts.query)
                             if not k.lower().startswith('utm_') and k.lower() not in ('fbclid', 'gclid')))
    return urlunsplit(('https', parts.netloc.lower(), parts.path.rstrip('/'), query, '')) + ':' + version


def validate(value, schema, where='result'):
    kind = schema['type']
    if kind == 'object':
        if not isinstance(value, dict) or set(value) != set(schema['required']):
            raise ValueError(f'{where}: expected fields {schema["required"]}; received {value!r}')
        for key, child in schema['properties'].items():
            validate(value[key], child, where + '.' + key)
    elif kind == 'array':
        if not isinstance(value, list) or len(value) > schema.get('maxItems', 100):
            raise ValueError(f'{where}: invalid list or too many items')
        if len(value) < schema.get('minItems', 0):
            raise ValueError(f'{where}: requires at least {schema["minItems"]} items')
        for item in value:
            validate(item, schema['items'], where + '[]')
    elif kind == 'string':
        if not isinstance(value, str) or len(value) > 16000:
            raise ValueError(f'{where}: expected bounded text')
        if 'enum' in schema and value not in schema['enum']:
            raise ValueError(f'{where}: invalid value {value!r}')


def prepare_result(data, seen):
    validate(data, read_json(ASSETS / 'schema.json', {}))
    if data['coverage'] == 'partial' and not data['coverage_notes']:
        raise ValueError('Partial coverage needs an explanation')
    if not data['search_queries']:
        raise ValueError('No search queries recorded; run a real discovery scan')
    reviewed = set(data['sources_reviewed'])
    for url in reviewed:
        source_key(url, '')
    findings = []
    for item in data['findings']:
        keys = sorted({source_key(s['url'], s['version']) for s in item['sources']})
        if any(s['url'] not in reviewed for s in item['sources']):
            raise ValueError('Finding cites a source that was not read')
        if set(keys) <= seen:
            continue
        for key in ('title', 'claim', 'evidence', 'limitations', 'relevance', 'suggestion'):
            if not item[key].strip():
                raise ValueError(f'Finding requires {key}')
        item = dict(item, source_keys=keys, id=hashlib.sha256('\n'.join(keys).encode()).hexdigest()[:20])
        findings.append(item)
        seen = seen | set(keys)
    return dict(data, findings=findings)


def estimate_cost(events, model):
    usages = [e['usage'] for e in events if e.get('type') == 'turn.completed' and isinstance(e.get('usage'), dict)]
    if not usages or model not in RATES:
        return None
    total = 0.0
    for usage in usages:
        if not all(isinstance(usage.get(k), int) and usage[k] >= 0 for k in ('input_tokens', 'cached_input_tokens', 'output_tokens')):
            return None
        inp, cached, out = (usage[k] for k in ('input_tokens', 'cached_input_tokens', 'output_tokens'))
        if cached > inp:
            return None
        rates = RATES[model]
        total += ((inp - cached) * rates[0] + cached * rates[1] + out * rates[2]) / 1_000_000
    return round(total, 8)


def events_from(path):
    events = []
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                events.append(json.loads(line))
            except ValueError:
                continue  # A running provider can leave its final line incomplete.
    return events


def run_provider(directory, config, prompt):
    args = [config.get('codex', 'codex'), 'exec', '--ignore-user-config', '--json',
            '--skip-git-repo-check', '--sandbox', 'read-only', '--model', config['model'],
            '-c', 'approval_policy="never"', '-c', 'mcp_servers={}', '-c', 'web_search="live"',
            '-c', 'project_doc_max_bytes=0', '-c', f'model_reasoning_effort="{config.get("effort", "medium")}"',
            '--disable', 'apps', '--disable', 'plugins', '--disable', 'multi_agent',
            '--disable', 'shell_tool', '--disable', 'unified_exec', '--disable', 'skill_mcp_dependency_install',
            '--cd', str(directory), '--output-schema', str(ASSETS / 'schema.json'),
            '--output-last-message', str(directory / 'result.json'), '-']
    (directory / 'prompt.txt').write_text(prompt)
    with (directory / 'events.jsonl').open('w') as output, (directory / 'stderr.log').open('w') as err:
        proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=output, stderr=err,
                                text=True, start_new_session=True)
        try:
            proc.stdin.write(prompt)
            proc.stdin.close()
            deadline = time.monotonic() + config.get('timeout_seconds', 900)
            while proc.poll() is None:
                if time.monotonic() > deadline:
                    raise RuntimeError('Research exceeded its time limit; reduce scan depth or retry manually')
                events = events_from(directory / 'events.jsonl')
                web_calls = sum(e.get('type') == 'item.completed' and e.get('item', {}).get('type') == 'web_search' for e in events)
                if web_calls >= config.get('max_web_calls', 40):
                    raise RuntimeError('Research exceeded its web-call limit; reduce scan depth')
                time.sleep(1)
            if proc.returncode:
                tail = (directory / 'stderr.log').read_text()[-1200:]
                raise RuntimeError(f'Research provider exited {proc.returncode}: {tail}')
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
    events = events_from(directory / 'events.jsonl')
    if not any(e.get('type') == 'item.completed' and e.get('item', {}).get('type') == 'web_search' for e in events):
        raise RuntimeError('Provider performed no recorded web research; check search availability')
    return read_json(directory / 'result.json', {}), events


def markdown(report):
    cost = 'Unknown' if report['estimated_cost_usd'] is None else f"${report['estimated_cost_usd']:.2f}"
    lines = ['# Weekly agent research', '', report['summary'], '',
             f"Generated: {report['generated_at']} · Coverage: {report['coverage']} · Estimated token cost: {cost}",
             '', report['cost_note'], '']
    lines += [f'- {note}' for note in report['coverage_notes']]
    if not report['findings']:
        lines += ['', 'No new recommendations in the sources reviewed.']
    for item in report['findings']:
        lines += ['', '## ' + item['title'], '', item['claim'], '', '**Evidence:** ' + item['evidence'],
                  '', '**Limits:** ' + item['limitations'], '', '**Why it matters here:** ' + item['relevance'],
                  '', '**Try during your normal work:** ' + item['suggestion'], '', '**Sources:**']
        lines += [f"- {s['title']} ({s['published_at']}; {s['version']}): {s['url']}" for s in item['sources']]
    lines += ['', '## Coverage', '', 'Searches:'] + ['- ' + q for q in report['search_queries']]
    lines += ['', 'Sources read:'] + ['- ' + u for u in report['sources_reviewed']]
    return '\n'.join(lines) + '\n'


def scan(root, config, force=False, now=None):
    now = now or utc_now()
    root.mkdir(parents=True, exist_ok=True)
    with (root / 'run.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {'skipped': 'Research is already running'}
        state = read_json(root / 'state.json', {})
        if not config.get('enabled', True):
            return {'skipped': 'Research is paused in configuration'}
        if not force and not is_due(state, now):
            return {'skipped': 'No scan due', 'next_due_at': state.get('next_due_at')}
        recent_attempts = [r for r in state.get('recent_runs', [])
                           if date(r['started_at']) > now - timedelta(days=7)]
        if not force and len(recent_attempts) >= 2:
            return {'skipped': 'Two scans already attempted in seven days; retry manually if needed'}
        run_id = str(uuid.uuid4())
        directory = root / 'runs' / run_id
        directory.mkdir(parents=True)
        state.update(schema_version=1, status='running', updated_at=iso(now), last_attempt_at=iso(now), last_error=None)
        atomic_json(root / 'state.json', state)
        run = dict(run_id=run_id, status='running', started_at=iso(now), model=config['model'])
        events = []
        try:
            seen = read_json(root / 'sources.json', {})
            brief = config.get('brief_text') or Path(config['brief_path']).expanduser().read_text()
            if len(brief) > 24000:
                raise ValueError('Research brief exceeds 24000 characters; shorten the workflow profile')
            prompt = (ASSETS / 'prompt.md').read_text() + '\n\n' + json.dumps(dict(
                today=iso(now), discovery_since=iso(now-timedelta(days=14)), workflow_profile=brief,
                already_reported=list(seen)[-500:], max_recommendations=3))
            data, events = run_provider(directory, config, prompt)
            report = prepare_result(data, set(seen))
            finished = utc_now()
            report.update(run_id=run_id, generated_at=iso(finished), report_path=str(directory/'report.md'),
                          estimated_cost_usd=estimate_cost(events, config['model']), cost_note=COST_NOTE,
                          model=config['model'], price_source=PRICE_SOURCE,
                          session_id=next((e.get('thread_id') for e in events if e.get('type')=='thread.started'), None))
            if data['findings'] and not report['findings']:
                report['summary'] = 'No new recommendations; the returned sources were already covered.'
            atomic_json(directory / 'report.json', report)
            (directory / 'report.md').write_text(markdown(report))
            for finding in report['findings']:
                for key in finding['source_keys']:
                    seen[key] = dict(first_seen=iso(finished), run_id=run_id, title=finding['title'])
            state.update(status='idle', last_report=report, retry_after=None)
            if report['coverage'] == 'complete':
                state.update(last_success_at=iso(finished), last_complete_report=report,
                             next_due_at=next_due(finished, config['timezone'], config['weekday'], config['hour']))
            else:
                state['next_due_at'] = iso(now + timedelta(days=1))
            run.update(status='succeeded', report_path=report['report_path'], coverage=report['coverage'])
            atomic_json(root / 'state.json', state)
            atomic_json(root / 'sources.json', seen)
        except BaseException as error:
            events = events or events_from(directory / 'events.jsonl')
            state.update(status='failed', last_error=str(error), retry_after=iso(now+timedelta(days=1)))
            run.update(status='failed', error=str(error))
            raise
        finally:
            run.update(finished_at=iso(utc_now()), estimated_cost_usd=estimate_cost(events, config['model']))
            atomic_json(directory / 'run.json', run)
            state['recent_runs'] = ([run] + state.get('recent_runs', []))[:52]
            state['updated_at'] = run['finished_at']
            atomic_json(root / 'state.json', state)
        return state


def interrupted(signum, _frame):
    raise InterruptedError(f'Research interrupted by signal {signum}; the provider was stopped')


def main():
    signal.signal(signal.SIGTERM, interrupted)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='Run now even if the next weekly scan is not due')
    parser.add_argument('--status', action='store_true', help='Read local state without calling a model')
    parser.add_argument('--config', type=Path, default=Path(os.getenv('XDG_CONFIG_HOME', str(Path.home()/'.config')))/'agent-research/config.json')
    parser.add_argument('--state-dir', type=Path, default=Path(os.getenv('XDG_STATE_HOME', str(Path.home()/'.local/state')))/'agent-research')
    args = parser.parse_args()
    if args.status:
        print(json.dumps(read_json(args.state_dir/'state.json', {}), indent=2))
        return
    config = DEFAULTS | read_json(args.config, {})
    if not config.get('brief_path'):
        raise ValueError(f'{args.config}: set brief_path to your workflow profile before running research')
    if not 0 <= config['weekday'] <= 6 or not 0 <= config['hour'] <= 23:
        raise ValueError('weekday must be 0..6 (Monday..Sunday) and hour must be 0..23')
    if not 30 <= config['timeout_seconds'] <= 1800 or not 1 <= config['max_web_calls'] <= 100:
        raise ValueError('timeout_seconds must be 30..1800 and max_web_calls must be 1..100')
    print(json.dumps(scan(args.state_dir, config, force=args.run), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, RuntimeError, KeyError) as error:
        print(f'agent-research: {error}', file=sys.stderr)
        sys.exit(1)
