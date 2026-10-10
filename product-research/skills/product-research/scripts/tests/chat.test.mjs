import test from 'node:test';
import assert from 'node:assert/strict';
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {InMemoryTransport} from '@modelcontextprotocol/sdk/inMemory.js';
import {createResearchServer} from '../chat_server.mjs';
import {validateSourceScope} from '../source_scope.mjs';

test('MCP exposes embedded HTML and settings tools without a desktop window', async () => {
  const calls=[];
  const server=createResearchServer('/fixture',async (action,args)=>{calls.push({action,args});return {markets:[],previous:{}};});
  const client=new Client({name:'test',version:'1'});
  const [ct,st]=InMemoryTransport.createLinkedPair();
  await server.connect(st);await client.connect(ct);
  try{
    const {tools}=await client.listTools();
    assert.equal(tools.length,3);
    assert.equal(tools.find(t=>t.name==='product_research_settings')._meta.ui.resourceUri,'ui://product-research/settings.html');
    const resource=await client.readResource({uri:'ui://product-research/settings.html'});
    assert.match(resource.contents[0].mimeType,/text\/html/);
    assert.match(resource.contents[0].text,/optgroup/);
    assert.match(resource.contents[0].text,/ui\/message/);
    await client.callTool({name:'product_research_categories',arguments:{country:'US',category_keys:['test']}});
    assert.deepEqual(calls[0],{action:'categories',args:{country:'US',category_keys:['test']}});
    const invalid=await client.callTool({name:'product_research_save',arguments:{country:'US',category_keys:[]}});
    assert.equal(invalid.isError,true);
  }finally{await client.close();await server.close();}
});

test('browser collection rejects wrong market, category and list type',()=>{
  const source={url:'https://www.amazon.com/zgbs/test/123',expectedOrigin:'https://www.amazon.com',expectedCategory:'test/123'};
  validateSourceScope(source.url+'/ref=page2?pg=2',source);
  validateSourceScope('https://www.amazon.com/dp/B000000001',source,true);
  assert.throws(()=>validateSourceScope('https://www.amazon.co.uk/zgbs/test/123',source));
  assert.throws(()=>validateSourceScope('https://www.amazon.com/zgbs/test',source));
  assert.throws(()=>validateSourceScope('https://www.amazon.com/gp/new-releases/test/123',source));
  assert.throws(()=>validateSourceScope('https://www.amazon.co.uk/dp/B000000001',source,true));
});
