from pathlib import Path
import json,html
R=Path(__file__).parent
# Time anchors are replaced from the narration alignment when available.
starts=[0,6.2,17.6,29.2,44.4,58,72.2,88.4,106.7,119.2,123.1,138,156.1,169.8,180]
shots=[
 ('Da evidência à decisão','Um percurso que pode ser explicado','desktop-inteligencia',[(0,300,1440,720),(30,590,800,560)]),
 ('Elo · Radar de Integridade','Inteligência, riscos e acompanhamento conectados','desktop-visao',[(0,0,1440,760),(20,290,1400,740)]),
 ('Uma visão compartilhada','Casos, riscos e pendências no mesmo fluxo','desktop-visao',[(0,150,1440,740),(25,635,1400,600)]),
 ('Um sinal. Uma investigação.','Coincidência cadastral não comprova irregularidade','desktop-inteligencia',[(840,1200,580,650),(830,675,580,530)]),
 ('Confira cada fonte','Dossiê com referências e limites explícitos','desktop-inteligencia',[(25,595,815,535),(855,680,555,500)]),
 ('A decisão é humana','Justificativa, responsabilidade e revisão','desktop-governanca',[(25,2045,815,330),(430,2100,390,255)]),
 ('Risco e maturidade conectados','Metodologia de maturidade ilustrativa','desktop-impactos',[(25,475,1380,550),(25,1620,815,700)]),
 ('Da análise ao acompanhamento','Trabalhos da segunda linha e planos de ação','desktop-governanca',[(25,390,815,760),(25,1250,815,390)]),
 ('Documentos com revisão','O texto aceito pode apoiar consultas com fontes','desktop-document-review',[(25,210,795,560),(25,410,795,480)]),
 ('Consultas com referências','A resposta preserva as fontes utilizadas','desktop-assistant',[(25,0,810,510)]),
 ('Regras que podem ser avaliadas','Parâmetros versionados e laboratório sintético','desktop-laboratory',[(850,1550,570,700),(850,2530,570,690)]),
 ('Um histórico verificável','Revisões, relatórios e exportações','desktop-report',[(0,0,1440,780),(20,150,810,650)]),
 ('Próximo passo: piloto controlado','Metodologia, integrações e infraestrutura a acordar','desktop-impactos',[(0,170,1440,740),(15,1620,830,740)]),
 ('Elo','Da evidência à decisão humana','desktop-visao',[(0,0,1440,740)])
]
css='''*{box-sizing:border-box}#root{position:absolute;inset:0;background:#f1f1f4;color:#111;font-family:Inter,sans-serif}.header{position:absolute;left:144px;top:64px;width:1632px}h1{font-size:62px;line-height:1.1;font-weight:700;letter-spacing:-2px;margin:0;max-width:1350px}p{font-size:30px;line-height:1.3;margin:18px 0 0;color:#47494e}.frame{position:absolute;left:144px;top:235px;width:1632px;height:745px;overflow:hidden;background:#fff;border-radius:12px}.surface{position:absolute;left:0;top:0;width:1440px;max-width:none;height:auto;transform-origin:0 0}.notice{position:absolute;right:144px;bottom:44px;font-size:28px;color:#47494e}.rule{position:absolute;left:144px;bottom:55px;width:100px;height:4px;background:#006b52}.end{position:absolute;inset:0;background:#050606;color:#fff;display:flex;flex-direction:column;justify-content:center;padding:150px}.end h1{font-size:164px;letter-spacing:-7px}.end p{font-size:44px;color:#eee;max-width:1200px}.end .maker{margin-top:90px;font-size:38px;color:#bfc3c3}.end .scope{margin-top:30px;font-size:28px;color:#bfc3c3}'''
# Font files are embedded by HyperFrames from its verified bundle.
hosts=[]
for i,(title,sub,file,crops) in enumerate(shots):
 sid=f'scene{i:02}';dur=starts[i+1]-starts[i]
 if i==len(shots)-1:
  body=f'<div class="end"><h1 id="{sid}-title">Elo</h1><p>Da evidência à decisão humana.<br>Com continuidade e responsabilidade.</p><p class="maker">Desenvolvido por UAI labs</p><p class="scope">Demonstração local com dados sintéticos · Piloto a acordar</p></div>'
  anim=f'tl.fromTo("#{sid}-title",{{x:-45,opacity:0}},{{x:0,opacity:1,duration:0.55,ease:"power2.out"}},0);'
 else:
  body=f'<div class="header"><h1>{html.escape(title)}</h1><p>{html.escape(sub)}</p></div><div class="frame" data-hold="Narrated inspection of real product UI" data-layout-allow-overflow="true"><img id="{sid}-screen" class="surface" src="assets/screens/{file}.png" alt="Tela real do Elo"></div><div class="rule"></div><div class="notice">Demonstração com dados sintéticos</div>'
  poses=[]
  for x,y,w,h in crops:
   scale=min(1632/w,745/h)
   poses.append({'x':round((1632-w*scale)/2-x*scale,2),'y':round((745-h*scale)/2-y*scale,2),'scale':round(scale,5)})
  anim=f'tl.set("#{sid}-screen",{json.dumps(poses[0])},0);'
  for j,pose in enumerate(poses[1:],1):anim+=f'tl.to("#{sid}-screen",{{...{json.dumps(pose)},duration:0.65,ease:"power2.inOut"}},{round(dur*j/len(poses),2)});'
 (R/'compositions'/f'{sid}.html').write_text(f'<template><style>{css}</style><div id="root" data-composition-id="{sid}" data-width="1920" data-height="1080">{body}</div><script>const tl=gsap.timeline({{paused:true}});{anim}window.__timelines["{sid}"]=tl;</script></template>')
 hosts.append(f'<div id="{sid}" class="clip" data-composition-id="{sid}" data-composition-src="compositions/{sid}.html" data-start="{starts[i]}" data-duration="{dur:.3f}" data-track-index="0" data-track-kind="graphics" data-width="1920" data-height="1080"></div>')
(R/'index.html').write_text('''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script><style>html,body{margin:0;width:1920px;height:1080px;overflow:hidden;background:#f1f1f4}#root{width:100%;height:100%;position:relative}</style></head><body><div id="root" data-composition-id="main" data-start="0" data-duration="180" data-width="1920" data-height="1080" data-fps="30">'''+''.join(hosts)+'''<audio id="narracao" class="clip" src="assets/narracao.wav" data-start="0" data-duration="176" data-track-index="1" data-volume="1"></audio></div><script>window.__timelines["main"]=gsap.timeline({paused:true});</script></body></html>''')
