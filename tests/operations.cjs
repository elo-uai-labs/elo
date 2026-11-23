'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const net = require('node:net');
const { spawn } = require('node:child_process');
const { once } = require('node:events');
const { existsSync } = require('node:fs');
const { chromium } = require('playwright');
(async () => {
  const temporary = await fs.mkdtemp(path.join(os.tmpdir(), 'elo-operations-'));
  const probe = net.createServer().listen(0, '127.0.0.1'); await once(probe, 'listening');
  const port = probe.address().port; await new Promise(resolve => probe.close(resolve));
  const url = `http://127.0.0.1:${port}`;
  const server = spawn(process.env.PYTHON || (existsSync('.venv/bin/python3') ? '.venv/bin/python3' : 'python3'), ['backend/server.py', '--port', String(port), '--db', path.join(temporary, 'test.sqlite3'), '--dist', path.resolve('dist')], { env: {...process.env, ELO_AUTH_USERS_FILE: '', ELO_ENV:'test', ELO_REQUIRE_AUTH:'0'}, stdio: ['ignore', 'ignore', 'pipe'] });
  let logs = ''; server.stderr.on('data', chunk => logs += chunk);
  let browser;
  try {
    for (let i=0;i<100;i++) { try { if((await fetch(`${url}/health`)).ok) break; } catch {} await new Promise(resolve=>setTimeout(resolve,100)); }
    const post = async (endpoint,payload) => {
      const response=await fetch(`${url}/api/${endpoint}`,{method:'POST',headers:{'Content-Type':'application/json',Origin:url},body:JSON.stringify(payload)});
      assert.equal(response.status,200,await response.text().then(text => response.status===200?'':text));
    };
    const today=new Intl.DateTimeFormat('en-CA',{timeZone:'America/Sao_Paulo'}).format(new Date());
    const yesterday=new Date(`${today}T12:00:00Z`); yesterday.setUTCDate(yesterday.getUTCDate()-1);
    const future=new Date(`${today}T12:00:00Z`); future.setUTCDate(future.getUTCDate()+10);
    for (const [title,owner,due,priority] of [['Revisão vencida','Ana Demo',yesterday.toISOString().slice(0,10),'high'],['Revisão hoje','Bia Demo',today,'normal'],['Revisão futura','Ana Demo',future.toISOString().slice(0,10),'normal']]) {
      await post('work/create',{title,owner,due,priority,description:'Escopo sintético de teste',priority_reason:'Priorização humana sintética',case_ids:[],actor:'Gestora Demo',reason:'Planejamento de teste'});
    }
    browser=await chromium.launch();
    const output=path.resolve('output/validation'); await fs.mkdir(output,{recursive:true});
    const results=[];
    for (const [label,viewport] of [['desktop',{width:1440,height:1000}],['mobile',{width:390,height:844}]]) {
      const page=await browser.newPage({viewport}); const errors=[]; page.on('pageerror',e=>errors.push(e.message));
      await page.goto(`${url}/#governanca`);
      await page.getByTestId('operations-panel').waitFor();
      await page.getByTestId('operation-work:WRK-001:deadline').waitFor();
      await page.getByTestId('operations-panel').getByText('Prazo vencido',{exact:true}).waitFor();
      assert.equal(await page.locator('[data-testid^="work-item-"]').count(),3);
      const choose=async(id,text)=>{const host=page.locator(id);await host.getByRole('combobox').click();await host.getByRole('option',{name:text,exact:true}).click();};
      await choose('#work-filter-owner','Ana Demo'); await choose('#work-filter-deadline','Pendentes atrasados');
      await page.getByRole('button',{name:'Aplicar filtros dos trabalhos',exact:true}).click();
      await page.getByText('1 de 3 trabalhos.',{exact:false}).waitFor();
      assert.equal(await page.locator('[data-testid^="work-item-"]').count(),1);
      await page.getByLabel('Buscar título, descrição ou ID (opcional)').fill('inexistente');
      await page.getByRole('button',{name:'Aplicar filtros dos trabalhos',exact:true}).click();
      await page.getByText('Nenhum trabalho corresponde aos filtros.',{exact:true}).waitFor();
      await Promise.all([page.waitForResponse(r=>r.url().endsWith('/api/work/summary')),page.getByRole('button',{name:'Atualizar avisos e indicadores',exact:true}).click()]);
      await page.waitForFunction(()=>document.querySelector('#view').getAttribute('aria-busy')==='false');
      await page.getByTestId('operation-work:WRK-001:deadline').waitFor();
      await page.getByTestId('operations-panel').scrollIntoViewIfNeeded();
      await page.evaluate(()=>document.fonts.ready);
      assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
      const heading=page.getByTestId('operations-panel').locator('p-heading').first();
      const font=await heading.evaluate(host=>{const s=getComputedStyle(host.shadowRoot.querySelector('h3'));return {family:s.fontFamily,size:s.fontSize,weight:s.fontWeight,line:s.lineHeight};});
      assert.match(font.family,/Porsche Next/);
      const cdp=await page.context().newCDPSession(page);await cdp.send('DOM.enable');
      const doc=await cdp.send('DOM.getDocument',{depth:-1,pierce:true});
      function find(nodes) {for(const n of nodes){if(n.nodeName==='P-HEADING' && n.shadowRoots?.length){const h=n.shadowRoots.flatMap(x=>x.children||[]).find(x=>/^H[1-6]$/.test(x.nodeName));if(h)return h.nodeId;}const nested=find([...(n.children||[]),...(n.shadowRoots||[])]);if(nested)return nested;}}
      const nodeId=find([doc.root]); assert.ok(nodeId);await cdp.send('CSS.enable');
      const fonts=await cdp.send('CSS.getPlatformFontsForNode',{nodeId});assert.ok(fonts.fonts.some(f=>f.isCustomFont&&f.glyphCount>0));
      assert.deepEqual(errors,[]); await page.screenshot({path:path.join(output,`operations-${label}.png`)});
      results.push({viewport:label,filters:true,notifications:true,overflow:false,font,webfont:true});await page.close();
    }
    const read=async()=>await(await fetch(`${url}/api/state`)).json();let state=await read();let item=state.work_items[0];
    await post('work/status',{id:item.id,revision:item.revision,status:'in_progress',actor:item.owner,reason:'Execução de teste'});
    item=(await read()).work_items[0];await post('work/status',{id:item.id,revision:item.revision,status:'completed',result:'Concluído em teste',actor:item.owner,reason:'Conclusão de teste'});
    const report=await(await fetch(`${url}/api/work/summary`)).json();
    assert.equal(report.operations.notifications.some(n=>n.entity_id===item.id),false);assert.equal(report.operations.sla.evaluated,1);assert.equal(report.operations.sla.on_time,0);
    await fs.writeFile(path.join(output,'operations-e2e.json'),JSON.stringify({date:new Date().toISOString(),results,completedNoticeRemoved:true,lateCompletionDenominator:true},null,2));
    console.log('Operação: filtros, avisos, resolução, SLA, desktop/celular e webfont PDS verificados.');
  } catch(e) {console.error(logs.slice(-1000));throw e;} finally {if(browser)await browser.close();server.kill('SIGTERM');await once(server,'exit');await fs.rm(temporary,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exitCode=1;});
