"""JSON settings interface shared by native chat questions and embedded forms."""
import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from amazon_catalog import Catalog, category_key


def validate_scope(url, market, category, kind=None):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname != urlsplit(market['origin']).hostname:
        raise ValueError('采集链接与所选国家站点不一致。')
    if category_key(url) != category['key']:
        raise ValueError('采集链接与所选类目不一致；不能仅修改报告上的国家或类目标签。')
    if kind == 'best_sellers' and '/zgbs/' not in parsed.path:
        raise ValueError('热销榜链接必须指向该类目的 Best Sellers。')
    if kind == 'new_releases' and '/gp/new-releases/' not in parsed.path:
        raise ValueError('新品榜链接必须指向该类目的 New Releases。')


def selected_market(catalog, country):
    market = next((item for item in catalog.markets() if item['country'] == country), None)
    if market is None:
        raise ValueError('国家不在从 Amazon 获取的选项中。')
    return market


def selected_path(catalog, market, keys):
    if not keys:
        raise ValueError('请先选择目标品类。')
    url, path = market['origin'] + '/Best-Sellers/zgbs', []
    for key in keys:
        item = next((item for item in catalog.categories(url) if item['key'] == key), None)
        if item is None:
            raise ValueError('类目不属于所选国家或父类；请重新选择。')
        validate_scope(item['url'], market, item)
        path.append(item)
        url = item['url']
    return path


def build_config(previous, market, path, values, workspace):
    scheduled = values.get('schedule_enabled', False)
    if not isinstance(scheduled, bool):
        raise ValueError('schedule_enabled 必须为布尔值。')
    time = values.get('time') or ''
    timezone = values.get('timezone') or ''
    if scheduled:
        if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', time):
            raise ValueError('运行时间请填写 HH:MM。')
        try:
            ZoneInfo(timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError('请填写有效的 IANA 时区。')
    category = path[-1]
    sources = [
        {'name': 'Best Sellers', 'list': 'best_sellers', 'target': 100, 'url': category['url']},
        {'name': 'New Releases', 'list': 'new_releases', 'target': 100,
         'url': market['origin'] + '/gp/new-releases/' + category['key']},
    ]
    custom = values.get('custom_sources')
    if custom:
        if len(custom) != 2:
            raise ValueError('请提供热销榜和新品榜两个链接。')
        for source, url in zip(sources, custom):
            source['url'] = url.strip()
    for source in sources:
        validate_scope(source['url'], market, category, source['list'])
    output = values.get('output_directory')
    if output is not None and not output.strip():
        raise ValueError('保存目录不能是空字符串；使用默认目录时传 null。')
    directory = Path(output).expanduser() if output else Path(workspace) / 'outputs'
    if not directory.is_absolute():
        directory = Path(workspace) / directory
    config = {**previous, 'platform': 'amazon', 'country': market['country'], 'marketplace': market,
              'category_path': path, 'sources': sources, 'engine': 'python', 'unique_product_target': 200,
              'supplemental_sources_allowed': False, 'shortfall_policy': 'report',
              'schedule_enabled': scheduled, 'time': time if scheduled else None, 'timezone': timezone,
              'output_directory': str(directory.resolve()), 'format': 'html'}
    if previous.get('country') != market['country']:
        for key in ('storage_state', 'delivery'):
            config.pop(key, None)
    return config


def execute(action, values, workspace, catalog=None):
    workspace = Path(workspace).resolve()
    catalog = catalog or Catalog(workspace / 'work/product-research-catalog.json')
    config_path = workspace / 'product-research.config.json'
    previous = json.loads(config_path.read_text(encoding='utf-8-sig')) if config_path.exists() else {}
    if action == 'markets':
        # Do not return local session paths or account information to a rendered widget.
        safe = {key: previous.get(key) for key in ('country', 'category_path', 'schedule_enabled', 'time', 'timezone', 'output_directory')}
        safe['sources'] = [{'url': source['url']} for source in previous.get('sources', [])]
        return {'platform': 'Amazon', 'markets': catalog.markets(values.get('refresh', False)), 'previous': safe}
    if action == 'plan':
        if not previous:
            raise ValueError('尚未保存设置。')
        market = selected_market(catalog, previous['country'])
        path = selected_path(catalog, market, [item['key'] for item in previous['category_path']])
        for source in previous['sources']:
            validate_scope(source['url'], market, path[-1], source.get('list'))
        return {'config_path': str(config_path), 'country': market['country'], 'category_path': path,
                'sources': previous['sources'], 'output_directory': previous['output_directory']}
    market = selected_market(catalog, values['country'])
    keys = values.get('category_keys', [])
    path = selected_path(catalog, market, keys) if keys else []
    if action == 'categories':
        if values.get('refresh') and not path:
            catalog.invalidate_categories(market['origin'])
        url = path[-1]['url'] if path else market['origin'] + '/Best-Sellers/zgbs'
        children = catalog.categories(url, values.get('refresh', False))
        return {'country': market['country'], 'parent': path[-1] if path else None,
                'path': path, 'choices': ([{**path[-1], 'is_self': True}] if path else []) + children,
                'source': catalog.data[url]['source'], 'fetched_at': catalog.data[url]['fetched_at']}
    if action != 'save':
        raise ValueError('不支持的设置操作。')
    if not path:
        raise ValueError('请先选择目标品类。')
    config = build_config(previous, market, path, values, workspace)
    directory = Path(config['output_directory'])
    directory.mkdir(parents=True, exist_ok=True)
    import tempfile
    with tempfile.TemporaryFile(dir=directory):
        pass
    workspace.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'saved': True, 'config_path': str(config_path), 'config': config,
            'schedule_status': 'pending_native_tool' if config['schedule_enabled'] else 'manual',
            'next_step': '由聊天助手使用此配置采集；定时计划须通过宿主原生工具落实。'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--action', required=True, choices=['markets', 'categories', 'save', 'plan'])
    parser.add_argument('--input', help='JSON file; otherwise reads JSON from stdin')
    args = parser.parse_args()
    try:
        raw = Path(args.input).read_text(encoding='utf-8-sig') if args.input else sys.stdin.read()
        values = json.loads(raw) if raw.strip() else {}
        result = execute(args.action, values, args.workspace)
        print(json.dumps(result, ensure_ascii=False))
    except (ValueError, OSError, KeyError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False))
        return 1
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
