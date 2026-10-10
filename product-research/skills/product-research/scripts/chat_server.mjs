import {createServer} from 'node:http';
import {readFileSync} from 'node:fs';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {parseArgs} from 'node:util';
import {McpServer} from '@modelcontextprotocol/sdk/server/mcp.js';
import {StdioServerTransport} from '@modelcontextprotocol/sdk/server/stdio.js';
import {StreamableHTTPServerTransport} from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import {registerAppResource, registerAppTool, RESOURCE_MIME_TYPE} from '@modelcontextprotocol/ext-apps/server';
import {z} from 'zod';

const scripts = path.dirname(fileURLToPath(import.meta.url));
const resourceUri = 'ui://product-research/settings.html';
const html = readFileSync(path.join(scripts, '../assets/settings.html'), 'utf8');
let queue = Promise.resolve();

export function settings(action, values, workspace) {
  const run = () => new Promise((resolve, reject) => {
    const child = spawn(process.env.PRODUCT_RESEARCH_PYTHON || 'python',
      ['-X', 'utf8', path.join(scripts, 'settings.py'), '--workspace', workspace, '--action', action],
      {stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true});
    let output = '', error = '';
    child.stdout.on('data', data => output += data);
    child.stderr.on('data', data => error += data);
    child.on('error', reject);
    child.on('close', code => {
      try {
        const result = JSON.parse(output);
        if (code || result.error) reject(Error(result.error || error));
        else resolve(result);
      } catch (failure) { reject(Error(error || failure.message)); }
    });
    child.stdin.end(JSON.stringify(values));
  });
  const result = queue.then(run, run);
  queue = result.catch(() => {});
  return result;
}

export function createResearchServer(workspace, execute = settings) {
  const server = new McpServer({name: 'product-research', version: '1.1.0'});
  registerAppResource(server, 'Product Research settings', resourceUri, {}, async () => ({
    contents: [{uri: resourceUri, mimeType: RESOURCE_MIME_TYPE, text: html,
      _meta: {ui: {prefersBorder: true, csp: {connectDomains: [], resourceDomains: []}}}}],
  }));
  const handle = action => async values => {
    try {
      const result = await execute(action, values, workspace);
      if (result.config) {
        delete result.config.storage_state;
        delete result.config.delivery;
      }
      return {content: [{type: 'text', text: result.saved ? '设置已保存；采集和原生计划尚需聊天助手继续执行。' : '从 Amazon 取得的 Product Research 选项。'}], structuredContent: result};
    } catch (error) { return {isError: true, content: [{type: 'text', text: error.message}]}; }
  };
  registerAppTool(server, 'product_research_settings', {
    title: '启动 Product Research', description: '显示聊天内研究设置表单。首次读取 Amazon 国家，之后复用缓存；用户明确更新时才传 refresh。',
    inputSchema: {refresh: z.boolean().optional()},
    annotations: {readOnlyHint: true, openWorldHint: true},
    _meta: {ui: {resourceUri}},
  }, handle('markets'));
  registerAppTool(server, 'product_research_categories', {
    title: '读取 Amazon 品类', description: '读取所选国家/父类的实际下级；choices 同时包含父类自身。',
    inputSchema: {country: z.string(), category_keys: z.array(z.string()).default([]), refresh: z.boolean().optional()},
    annotations: {readOnlyHint: true, openWorldHint: true},
    _meta: {ui: {visibility: ['app', 'model']}},
  }, handle('categories'));
  registerAppTool(server, 'product_research_save', {
    title: '保存研究设置', description: '仅在用户提交表单后保存国家、品类和链接；不会创建计划或启动爬虫。',
    inputSchema: {country: z.string(), category_keys: z.array(z.string()).min(1), schedule_enabled: z.boolean(),
      time: z.string().optional(), timezone: z.string(), output_directory: z.string().nullable().optional(),
      custom_sources: z.array(z.string()).length(2).optional()},
    annotations: {readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: false},
    _meta: {ui: {visibility: ['app', 'model']}},
  }, handle('save'));
  return server;
}

async function main() {
  const {values} = parseArgs({options: {workspace: {type: 'string'}, http: {type: 'boolean'}, port: {type: 'string', default: '8787'}}});
  if (!values.workspace) throw Error('Required: --workspace <customer workspace>');
  const workspace = path.resolve(values.workspace);
  if (!values.http) return createResearchServer(workspace).connect(new StdioServerTransport());
  const http = createServer(async (req, res) => {
    if (req.url !== '/mcp') { res.writeHead(404).end('Not Found'); return; }
    const server = createResearchServer(workspace);
    const transport = new StreamableHTTPServerTransport({sessionIdGenerator: undefined, enableJsonResponse: true});
    res.on('close', () => { transport.close(); server.close(); });
    try {
      await server.connect(transport);
      await transport.handleRequest(req, res);
    } catch (error) {
      console.error(error);
      if (!res.headersSent) res.writeHead(500).end('MCP request failed');
    }
  });
  http.listen(Number(values.port), '127.0.0.1', () => console.error(`Product Research MCP: http://127.0.0.1:${values.port}/mcp`));
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await main();
