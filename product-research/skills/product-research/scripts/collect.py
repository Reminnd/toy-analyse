"""Collect a configured source, binding marketplace and category to actual URLs."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from python_crawler import crawl
from settings import execute


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--source', choices=['best_sellers', 'new_releases'], required=True)
    parser.add_argument('--engine', choices=['python', 'playwright'], default='python')
    parser.add_argument('--output', required=True)
    parser.add_argument('--python-result')
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
        result = crawl(source['url'], 'amazon', config['country'], source['target'], True, state,
                       scope={'market': config['marketplace'], 'category': plan['category_path'][-1], 'list': source['list']})
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'output': str(output), 'count': len(result['products'])}))
    else:
        command = ['node', str(Path(__file__).with_name('playwright_crawler.mjs')), '--platform', 'amazon',
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
    main()
