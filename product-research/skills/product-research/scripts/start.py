"""Wait for settings, then collect both sources without another user prompt."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime


def start(workspace, timezone):
    scripts = Path(__file__).parent
    result = subprocess.run([sys.executable, str(scripts / 'setup.py'), '--workspace', str(workspace),
                             '--timezone', timezone], capture_output=True, text=True, encoding='utf-8', check=True)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    saved = json.loads(result.stdout)
    if not saved.get('saved'):
        return {'saved': False, 'status': 'cancelled'}
    print('设置已保存，自动开始采集。', flush=True)
    run = Path(workspace) / 'work' / ('run-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    outputs = []
    for source in ('best_sellers', 'new_releases'):
        output = run / (source + '.json')
        collected = subprocess.run([sys.executable, str(scripts / 'collect.py'), '--workspace', str(workspace),
                                    '--source', source, '--output', str(output), '--detail-cache', str(run/'details.json')])
        outputs.append({'source': source, 'output': str(output), 'returncode': collected.returncode})
        if collected.returncode != 0:
            return {'saved': True, 'status': 'collection_stopped', 'outputs': outputs}
    return {'saved': True, 'status': 'ready_for_analysis', 'outputs': outputs}


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--timezone', default='')
    args = parser.parse_args()
    print(json.dumps(start(Path(args.workspace).resolve(), args.timezone), ensure_ascii=False))
