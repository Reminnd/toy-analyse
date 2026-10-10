export function validateSourceScope(url, source, detail = false) {
  if (!source.expectedOrigin) return;
  const actual = new URL(url);
  if (actual.origin !== source.expectedOrigin) throw Error('页面跳转到其他国家；停止合并。');
  if (detail) return;
  const key = actual.pathname.split(/\/(?:zgbs|gp\/new-releases)\//)[1]?.split('/ref=')[0].replace(/\/$/, '');
  if (key !== source.expectedCategory) throw Error('榜单页面与所选类目不一致；停止采集。');
  const expectedType = new URL(source.url).pathname.includes('/gp/new-releases/') ? '/gp/new-releases/' : '/zgbs/';
  if (!actual.pathname.includes(expectedType)) throw Error('榜单类型发生变化；停止采集。');
}
