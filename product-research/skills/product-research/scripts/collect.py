"""Collect a configured source, binding marketplace and category to actual URLs."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import os

from python_crawler import crawl
from settings import execute


def collect_python(source, config, state, output, config_path, cache_path=None):
    scope = {'market': config['marketplace'], 'category': config['category_path'][-1], 'list': source['list']}
    cache = json.loads(cache_path.read_text(encoding='utf-8')) if cache_path and cache_path.exists() else {}
    def fetch(session):
        try:
            return crawl(source['url'], 'amazon', config['country'], source['target'], True, session,
                         scope=scope, detail_cache=cache, workers=2)
        finally:
            if cache_path:
                cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding='utf-8')
    try:
        result = fetch(state)
    except ValueError as error:
        if getattr(error, 'code', None) != 'browser_challenge':
            raise
        result = {'source_url': source['url'], 'products': [], 'collection_stop':
                  {'code': 'browser_challenge', 'url': source['url'], 'reason': str(error)}}
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    stop = result.get('collection_stop') or {}
    if stop.get('code') != 'browser_challenge':
        return result
    previous = output.with_name(output.stem + '-before-verification.json')
    previous.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    session = Path(config_path).parent / 'work/.auth' / ('amazon-' + config['country'] + '-verified.json')
    command = [os.environ.get('PRODUCT_RESEARCH_NODE') or 'node', str(Path(__file__).with_name('verify_session.mjs')), '--url', stop.get('url') or source['url'],
               '--output', str(session)]
    if state:
        command += ['--storage-state', str(state)]
    verified = subprocess.run(command)
    if verified.returncode != 0:
        result['verification_status'] = 'cancelled_or_failed'
    else:
        config['storage_state'] = str(session)
        for configured in config['sources']:
            if configured['list'] == source['list'] and configured.get('storage_state'):
                configured['storage_state'] = str(session)
        Path(config_path).write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
        try:
            resumed = fetch(str(session))
            # Preserve the first snapshot even if the retry returns less data.
            resumed['previous_result'] = str(previous)
            resumed['verification_status'] = 'completed'
            result = resumed
        except Exception as error:
            result['verification_status'] = 'retry_failed'
            result['retry_error'] = str(error)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--source', choices=['best_sellers', 'new_releases'], required=True)
    parser.add_argument('--engine', choices=['python', 'playwright'], default='python')
    parser.add_argument('--output', required=True)
    parser.add_argument('--python-result')
    parser.add_argument('--detail-cache', help='Shared only within one collection run')
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    plan = execute('plan', {}, workspace)
    config = json.loads(Path(plan['config_path']).read_text(encoding='utf-8'))
    source = next(s for s in plan['sources'] if s['list'] == args.source)
    state = source.get('storage_state') or config.get('storage_state')
    if state and not Path(state).is_absolute():
        state = str(workspace / state)
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.engine == 'python':
        result = collect_python(source, config, state, output, plan['config_path'], Path(args.detail_cache) if args.detail_cache else None)
        print(json.dumps({'output': str(output), 'count': len(result['products'])}))
        if result.get('collection_stop'):
            return 2
    else:
        command = [os.environ.get('PRODUCT_RESEARCH_NODE') or 'node', str(Path(__file__).with_name('playwright_crawler.mjs')), '--platform', 'amazon',
                   '--country', config['country'], '--url', source['url'], '--limit', str(source['target']),
                   '--details', '--output', str(output), '--profile', str(workspace / 'work/browser'),
                   '--expected-origin', config['marketplace']['origin'], '--expected-category', plan['category_path'][-1]['key']]
        if state:
            command += ['--storage-state', state]
        if args.python_result:
            command += ['--python-result', args.python_result]
        subprocess.run(command, check=True)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    raise SystemExit(main())
