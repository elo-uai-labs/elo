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
  const temporary = await fs.mkdtemp(path.join(os.tmpdir(), 'elo-supervision-'));
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
    await post('import', {actor:'Gestora Demo',synthetic:true,dataset:{employees:[],suppliers:[],contracts:[
      {id:'CTR-SUP-1',supplier_id:'FOR-031',approver_id:'EMP-014',title:'Caso sintético A'},
      {id:'CTR-SUP-2',supplier_id:'FOR-031',approver_id:'EMP-014',title:'Caso sintético B'}]}});
    await post('detect',{});
    let initial=await(await fetch(`${url}/api/state`)).json();
    for (const [index,item] of initial.cases.entries()) {
      await post('dossier',{mode:'local',case_id:item.id});
      const current=(await(await fetch(`${url}/api/state?case_id=${item.id}`)).json()).case;
      await post('decision',{case_id:item.id,dossier_revision:current.dossier.revision,linkage_revision:current.linkage_revision,
        actor:index===0?'Ana Demo':'Bia Demo',review:index===0?'adjust':'accept',outcome:'monitor',reason:index===0?'Conferir documentação original':'Revisão sintética concluída'});
    }
    const snapshotBefore=await(await fetch(`${url}/api/state`)).json();
    browser=await chromium.launch();
    const output=path.resolve('output/validation'); await fs.mkdir(output,{recursive:true});
    const results=[];
    for (const [label,viewport] of [['desktop',{width:1440,height:1000}],['mobile',{width:390,height:844}]]) {
      const page=await browser.newPage({viewport}); const errors=[]; page.on('pageerror',e=>errors.push(e.message));
      await page.goto(`${url}/#governanca`);
      await page.getByRole('button',{name:'Atualizar indicadores de supervisão',exact:true}).click();
      await page.getByTestId('supervision-filter-panel').waitFor();
      const apply=async(error=false)=>{const form=await page.locator('[data-endpoint=supervision-filter]').elementHandle();await page.getByRole('button',{name:'Aplicar filtros de supervisão',exact:true}).click();if(error) await page.getByText('A data inicial deve ser anterior ou igual à data final.',{exact:true}).waitFor();else await page.waitForFunction(old=>!old.isConnected,form);};
      const choose=async(id,text)=>{const host=page.locator(id);await host.getByRole('combobox').click();await host.getByRole('option',{name:text,exact:true}).click();};
      assert.equal(await page.getByTestId('supervision-record').count(),3);
      const globalBefore=await page.getByTestId('supervision-summary').textContent();
      await choose('#supervision-actor','Ana Demo'); await choose('#supervision-review','Ajustou a sugestão');
      await choose('#supervision-mode','Síntese local');await choose('#supervision-identity','Legada ou autodeclarada');
      await page.getByLabel('Buscar caso ou justificativa (opcional)',{exact:true}).fill('DOCUMENTAÇÃO');
      await apply();assert.equal(await page.getByTestId('supervision-record').count(),1);
      assert.match(await page.getByTestId('supervision-record').textContent(),/Conferir documentação original/);
      assert.equal(await page.getByTestId('supervision-summary').textContent(),globalBefore);
      await choose('#supervision-identity','Autenticada local');await apply();
      await page.getByText('Nenhuma decisão corresponde aos filtros.',{exact:true}).waitFor();
      await choose('#supervision-identity','Legada ou autodeclarada');
      const date=new Date().toISOString().slice(0,10);
      await page.getByLabel('Decisões desde (UTC, opcional)',{exact:true}).fill(date);
      await page.getByLabel('Decisões até (UTC, opcional)',{exact:true}).fill(date);await apply();
      assert.equal(await page.getByTestId('supervision-record').count(),1);
      await page.getByLabel('Decisões desde (UTC, opcional)',{exact:true}).fill('2099-01-01');await apply(true);
      await page.getByText('A data inicial deve ser anterior ou igual à data final.',{exact:true}).waitFor();
      assert.equal(await page.getByTestId('supervision-record').count(),1);
      await page.getByLabel('Decisões até (UTC, opcional)',{exact:true}).fill('2099-01-02');await apply();
      await page.getByText('Nenhuma decisão corresponde aos filtros.',{exact:true}).waitFor();
      await page.getByLabel('Decisões desde (UTC, opcional)',{exact:true}).fill('');await page.getByLabel('Decisões até (UTC, opcional)',{exact:true}).fill('');await apply();
      const oldForm=await page.locator('[data-endpoint=supervision-filter]').elementHandle();
      const applyButton=page.getByRole('button',{name:'Aplicar filtros de supervisão',exact:true});await applyButton.focus();await page.keyboard.press('Enter');await page.waitForFunction(old=>!old.isConnected,oldForm);
      await page.getByTestId('supervision-filter-panel').scrollIntoViewIfNeeded();
      await page.evaluate(()=>document.fonts.ready);
      assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
      const heading=page.getByTestId('supervision-filter-panel').locator('p-heading').first();
      const font=await heading.evaluate(host=>{const s=getComputedStyle(host.shadowRoot.querySelector('h3'));return {family:s.fontFamily,size:s.fontSize,weight:s.fontWeight,line:s.lineHeight};});
      assert.match(font.family,/Porsche Next/);
      const cdp=await page.context().newCDPSession(page);await cdp.send('DOM.enable');
      const doc=await cdp.send('DOM.getDocument',{depth:-1,pierce:true});
      function find(nodes) {for(const n of nodes){if(n.nodeName==='P-HEADING' && n.shadowRoots?.length){const h=n.shadowRoots.flatMap(x=>x.children||[]).find(x=>/^H[1-6]$/.test(x.nodeName));if(h)return h.nodeId;}const nested=find([...(n.children||[]),...(n.shadowRoots||[])]);if(nested)return nested;}}
      const nodeId=find([doc.root]); assert.ok(nodeId);await cdp.send('CSS.enable');
      const fonts=await cdp.send('CSS.getPlatformFontsForNode',{nodeId});assert.ok(fonts.fonts.some(f=>f.isCustomFont&&f.glyphCount>0));
      assert.deepEqual(errors,[]); await page.screenshot({path:path.join(output,`supervision-${label}.png`)});
      results.push({viewport:label,filters:true,globalTotalsPreserved:true,keyboard:true,overflow:false,font,webfont:true});await page.close();
    }
    const snapshotAfter=await(await fetch(`${url}/api/state`)).json();
    assert.deepEqual(snapshotAfter.audit,snapshotBefore.audit);
    assert.deepEqual(snapshotAfter.cases,snapshotBefore.cases);
    await fs.writeFile(path.join(output,'supervision-e2e.json'),JSON.stringify({date:new Date().toISOString(),results,readOnly:true,scope:'Local synthetic decisions, actual HTTP backend; no model call'},null,2));
    console.log('Supervisão: filtros combinados, vazio, datas, totais preservados, desktop/celular e webfont PDS verificados.');
  } catch(e) {console.error(logs.slice(-1000));throw e;} finally {if(browser)await browser.close();server.kill('SIGTERM');await once(server,'exit');await fs.rm(temporary,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exitCode=1;});
