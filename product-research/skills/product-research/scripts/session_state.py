"""Reuse domain-scoped cookies from a user-provided Playwright storage state."""
import json
import time
from pathlib import Path
from urllib.parse import urlparse
from requests.cookies import create_cookie


def load_state(session, filename, target_url):
    state = json.loads(Path(filename).read_text(encoding='utf-8-sig'))
    host = urlparse(target_url).hostname
    loaded, expired = 0, 0
    for item in state.get('cookies', []):
        domain = item['domain']
        base = domain.lstrip('.')
        if host != base and not (domain.startswith('.') and host.endswith('.'+base)):
            continue
        expires = item.get('expires', -1)
        if expires > 0 and expires <= time.time():
            expired += 1
            continue
        cookie = create_cookie(name=item['name'], value=item['value'], domain=domain,
                               path=item.get('path','/'), secure=item.get('secure',False),
                               expires=int(expires) if expires > 0 else None,
                               rest={'HttpOnly':item.get('httpOnly',False)})
        cookie.domain_specified = domain.startswith('.')
        session.cookies.set_cookie(cookie)
        loaded += 1
    if state.get('user_agent'):
        session.headers['User-Agent'] = state['user_agent']
    return {'loaded_cookie_count':loaded,'expired_cookie_count':expired,
            'note':'仅复用适用 Cookie；未执行 localStorage、IndexedDB 或浏览器动态令牌逻辑。'}
