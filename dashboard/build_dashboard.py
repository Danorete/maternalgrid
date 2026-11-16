# shortcut: written for the original hackathon workspace (reads chatgpt-pack/ and v3_css.txt, writes MaternalGrid_Dashboard.html); kept for provenance. dashboard/index.html is the built output.
import json
D=json.load(open('chatgpt-pack/maternalgrid_data.json'))
C=json.load(open('county_cells.json'))
CSS=open('v3_css.txt').read()

BODY = r'''
<div class="topbar">
  <div class="logo">M</div>
  <div class="brand"><h1>MaternalGrid</h1>
    <p>Georgia labor &amp; delivery access simulation &middot; 159 counties &middot; 68 active facilities</p></div>
  <div class="notice">&#9888;&#65039; AI-assisted scenario estimate from open Georgia health data (GDPH/OASIS). Modeled travel time &mdash; not routed drive time.</div>
</div>

<div class="strip" id="strip"></div>

<div class="tour">
  <span class="eyebrow">Executive demo tour</span>
  <div class="steps">
    <button class="step s1" data-step="1"><span class="idx">1</span>Current crisis</button>
    <span class="arrow">&rarr;</span>
    <button class="step s2" data-step="2"><span class="idx">2</span>Stress test &mdash; closure</button>
    <span class="arrow">&rarr;</span>
    <button class="step s3" data-step="3"><span class="idx">3</span>Strategic remedy &mdash; expansion</button>
  </div>
  <span class="spacer"></span>
  <button class="mini" id="customBtn">Custom simulation &#9662;</button>
  <div class="seg" id="modeSeg">
    <button data-m="desert" class="on">Maternity deserts</button>
    <button data-m="bands">Drive-time bands</button>
    <button data-m="delta">Change</button>
  </div>
  <span class="note" id="tourNote">Start here &mdash; each step stages the scenario and flies the map to the affected region.</span>
</div>
<div class="custom" id="custom">
  <span class="lbl">Custom simulation</span>
  <input class="ctl" id="closeIn" list="faclist" placeholder="Close a facility&hellip;">
  <datalist id="faclist"></datalist>
  <select class="ctl" id="addSel"></select>
  <button class="ctl" id="resetBtn">Reset to baseline</button>
  <div class="chips" id="chips"></div>
</div>
<div class="headline" id="hl"><p id="hlText"></p><div class="meta" id="hlMeta"></div></div>


</div>

<div class="main">
<div class="stage"><svg id="map"></svg>
  <div class="ledger">
    <h3 id="legTitle">Modeled drive time</h3>
    <div id="leg"></div>
    <div class="ldiv"></div>
    <div id="legScen"></div>
    <div class="ldiv"></div>
    <div class="lkey"><span>&#9650; facility</span><span>&#10005; closed</span></div>
    <div class="lkey">Voronoi catchments, not surveyed boundaries</div>
  </div>
</div>
<aside class="side">
  <div class="sh"><div class="st">Inspect</div><div class="sm" id="dmeta"></div>
    <div class="dtabs" id="dtabs">
      <div class="dtab on" data-t="changed">Changed</div>
      <div class="dtab" data-t="absorb">Absorbing</div>
      <div class="dtab" data-t="detail">County</div>
    </div></div>
  <div class="sbody" id="dbody"></div>
</aside>
</div>


</div>

<div id="tip"></div>
<div id="fabWrap">
  <button id="fab" aria-expanded="false" aria-controls="panel" aria-label="Open MaternalGrid assistant">
    &#128172;<span class="badge"></span></button>
  <button id="fabHide" title="Hide assistant for presenting" aria-label="Hide assistant">&times;</button>
</div>
<button id="fabShow" title="Show assistant" aria-label="Show assistant">&#128172; Assistant</button>
<div id="panel" role="dialog" aria-label="MaternalGrid assistant">
  <div class="phead"><div><div class="nm">MaternalGrid Assistant</div>
      <div class="st">Grounded on GDPH/OASIS &middot; planning only</div></div>
    <div class="acts"><button id="pMin" aria-label="Minimize">&minus;</button>
      <button id="pClose" aria-label="Close">&times;</button></div></div>
  <div class="plog" id="plog"></div>
  <div class="pquick">
    <button data-q="What is a maternity care desert?">What is a desert?</button>
    <button data-q="Why 30 minutes?">Why 30 min?</button>
    <button data-q="Where is the biggest gap?">Biggest gap</button>
    <button data-q="Where does this data come from?">Sources</button>
    <button data-q="How is travel time calculated?">Methodology</button>
  </div>
  <div class="pfoot"><input id="pIn" placeholder="Ask about access, methodology, or a county&hellip;"></div>
</div>
'''

JS = r'''
const DATA=__DATA__, CELLS=__CELLS__;
const CO=DATA.counties, FA=DATA.facilities, M=DATA.meta.model, BASE=DATA.verified_baseline;
const RAMP=['#FFF3E0','#FDBE73','#F57C00','#D32F2F','#7B1616'];
const DIV=['#D32F2F','#F0928A','#E8EDF3','#86C295','#2E7D32'];
const BUCK=[[0,15,'Under 15 min'],[15,30,'15–30 min'],[30,45,'30–45 min'],[45,60,'45–60 min'],[60,1e9,'Over 60 min']];
const DIVL=[['#D32F2F','Worse by 10+ min'],['#F0928A','Worse 2–10 min'],['#E8EDF3','No change'],
            ['#86C295','Better 2–10 min'],['#2E7D32','Better by 10+ min']];
const LVLW={IV:4,III:3,II:2,I:1};
const closed=new Set(), added=[];
let selected=null, tab='changed', view='desert', step=0;
const CRISIS='#DC2626', RESCUE='#16A34A', SAFE='#E2E8F0';
const HIGH=['III','IV'];
// nearest Level III/IV facility — the acuity question judges ask
function nearestHigh(c){let b=null,bm=Infinity,bd=0;
  for(const f of actF()){ if(!HIGH.includes(f.level)) continue;
    const m=minutes(c,f); if(m<bm){bm=m;b=f;bd=m*M.avg_mph/60/M.road_factor;} }
  return b?{f:b,min:bm,mi:bd}:null;}
const CELLOF={}; CELLS.geoids.forEach((g,i)=>CELLOF[g]=CELLS.cells[i]);

const rad=d=>d*Math.PI/180, fmt=n=>Math.round(n).toLocaleString('en-US');
function minutes(c,f){const dp=rad(f.lat-c.lat),dl=rad(f.lon-c.lon);
  const h=Math.sin(dp/2)**2+Math.cos(rad(c.lat))*Math.cos(rad(f.lat))*Math.sin(dl/2)**2;
  return (2*M.earth_radius_miles*Math.asin(Math.sqrt(h))*M.road_factor/M.avg_mph)*60;}
const actF=()=>FA.filter(f=>f.status==='active'&&!closed.has(f.id)).concat(added);
function solve(){const a=actF(),o={};
  for(const c of CO){let b=null,bm=Infinity;for(const f of a){const m=minutes(c,f);if(m<bm){bm=m;b=f;}}o[c.geoid]={min:bm,fac:b};}
  return o;}
const B0=solve();
const capOf=l=>l.reduce((t,f)=>t+(LVLW[f.level]||1),0);
function risk(S){let w=0,t=0;for(const c of CO){w+=c.births*Math.max(0,(S[c.geoid].min-30)/30);t+=c.births;}return 100*w/t;}
function stats(S){let no=0,bn=0,tot=0,w=0;
  for(const c of CO){const m=S[c.geoid].min;w+=m*c.births;tot+=c.births;if(m>30){no++;bn+=c.births;}}
  return{no,bn,avg:w/tot,risk:risk(S),cap:capOf(actF())};}
function band(S){const b=CO.map(c=>({m:S[c.geoid].min,b:c.births})),tot=b.reduce((t,x)=>t+x.b,0),N=400,o=[];
  for(let i=0;i<N;i++){const k=((1.20+Math.random()*.25)/M.road_factor)*(M.avg_mph/(38+Math.random()*14));
    let w=0;for(const x of b)w+=x.m*k*x.b;o.push(w/tot);}
  o.sort((a,b)=>a-b);return{p10:o[40],p90:o[359]};}
const bIdx=m=>BUCK.findIndex(b=>m>=b[0]&&m<b[1]);
const dIdx=d=>d>10?0:d>2?1:d>=-2?2:d>=-10?3:4;

function tile(lab,fig,pill,pcls,sub,tcls,anchor){
  return `<div class="tile ${tcls||''}${anchor?' anchor':''}">
    <div class="lab">${lab}${anchor?' <span class="crisisbadge">Crisis</span>':''}</div>
    <div class="fig num">${fig}</div>
    <div class="foot">${pill?`<span class="pill ${pcls}">${pill}</span>`:''}<span class="sub">${sub}</span></div></div>`;}

function render(){
  const staged=closed.size||added.length;
  const S=staged?solve():B0, st=stats(S), b0=stats(B0), cb=band(S);
  const capB=capOf(FA.filter(f=>f.status==='active')), nB=FA.filter(f=>f.status==='active').length;
  const rows=CO.map(c=>{const a=B0[c.geoid],b=S[c.geoid];
    const ha=a.min<=30,hb=b.min<=30;
    let s='unchanged'; if(ha&&!hb)s='lost'; else if(!ha&&hb)s='gained'; else if(a.fac.id!==b.fac.id)s='shifted';
    return{c,base:a,scen:b,delta:b.min-a.min,state:s};});
  const changed=rows.filter(r=>r.state!=='unchanged').sort((x,y)=>y.delta-x.delta);
  const lost=rows.filter(r=>r.state==='lost'), gained=rows.filter(r=>r.state==='gained');
  const disp=lost.reduce((t,r)=>t+r.c.births,0), resc=gained.reduce((t,r)=>t+r.c.births,0);
  const worst=changed.length?Math.max(...changed.map(r=>r.delta)):0;
  const best=changed.length?Math.min(...changed.map(r=>r.delta)):0;

  const P=(d,unit,inv)=>{const up=d>0.049,dn=d<-0.049;
    const cls=!up&&!dn?'flat':(inv?(up?'down':'up'):(up?'up':'down'));
    return staged?[`${up?'▲ +':dn?'▼ ':'● '}${Math.abs(d).toFixed(unit==='min'||unit==='idx'?1:0)}${unit==='min'?' min':unit==='idx'?'':''}`,cls]:['',''];};
  const [p1,c1]=P(st.no-b0.no,''), [p2,c2]=P(st.bn-b0.bn,''), [p3,c3]=P(st.avg-b0.avg,'min'),
        [p4,c4]=P(st.risk-b0.risk,'idx'), [p5,c5]=P(st.cap-capB,'',true), [p6,c6]=P(actF().length-nB,'',true);
  document.getElementById('strip').innerHTML=
    tile('Counties beyond 30 min',st.no,p1,c1,staged?'of 159':'46.5% of 159 counties','',true)+
    tile('Births beyond 30 min',fmt(st.bn),p2,c2,staged?'annual exposed':'7.8% of GA births','',true)+
    tile('Avg drive time',st.avg.toFixed(1)+' min',p3,c3,`90% band ${cb.p10.toFixed(1)}–${cb.p90.toFixed(1)} min`,c3==='up'?'warn':c3==='down'?'pos':'')+
    tile('Access risk index',st.risk.toFixed(1),p4,c4,'births-weighted excess exposure',c4==='up'?'crit':c4==='down'?'pos':'')+
    tile('L&amp;D capacity',st.cap,p5,c5,'level-weighted proxy · grade C',c5==='down'?'crit':c5==='up'?'pos':'')+
    tile('Active facilities',actF().length,p6,c6,staged?'in scenario':'62 in-state + 6 border',c6==='down'?'crit':c6==='up'?'pos':'');

  const names=[...closed].map(id=>FA.find(f=>f.id===id).name);
  let sev='', txt;
  if(added.length&&!closed.size){ sev='pos';
    txt=gained.length?`Opening a Level III maternity center in ${added[0].city} County reduces modeled drive time by up to ${Math.round(-best)} minutes for ${changed.length} ${changed.length===1?'county':'counties'}, bringing ${fmt(resc)} annual births inside the 30-minute access threshold.`
      :`Opening a Level III maternity center in ${added[0].city} County shortens drive time for ${changed.length} counties, but none cross inside the 30-minute threshold.`;
  } else if(!staged){ sev='';
    txt=`No facility changes staged — statewide baseline: <b>74 of 159 counties (46.5%)</b> already lie beyond the 30-minute emergency access threshold, covering <b>13,029 annual births</b>.`;
  } else { sev=lost.length?'crit':(worst>10?'warn':'');
    const ev=names.length===1?`Closing the L&amp;D unit at <b>${names[0]}</b>`:`Closing <b>${names.length}</b> L&amp;D units`;
    txt=changed.length?`${ev} raises modeled drive time by up to <b>${Math.round(worst)} minutes</b> across <b>${changed.length}</b> ${changed.length===1?'county':'counties'}${disp?`, shifting <b>${fmt(disp)} annual births</b> beyond the 30-minute access threshold.`:'.'}`
      :`${ev} leaves modeled travel time unchanged statewide.`;}
  document.getElementById('hl').className='headline '+sev;
  document.getElementById('hlText').innerHTML=txt;
  document.getElementById('hlMeta').innerHTML=staged
    ? `<span class="tag">Modeled estimate</span><span class="tag">Confidence ${DATA.meta.confidence_grade}</span><span class="tag">Haversine ×1.30 / 45 mph</span><span class="tag">Not routed drive time</span>`
    : `<span class="tag">Verified baseline</span><span class="tag">GDPH OASIS 2024</span><span class="tag">March of Dimes 2026</span>`;

  // ledger
  document.getElementById('legTitle').textContent=
    view==='delta'?'Change vs baseline':view==='desert'?'Maternity deserts':'Modeled drive time';
  if(view==='desert'){
    let nd=0; for(const x of CO) if(S[x.geoid].min>30) nd++;
    document.getElementById('leg').innerHTML=
      `<div class="lrow"><span class="dotpill" style="background:${CRISIS}"></span><span class="t">Beyond 30 min &mdash; desert</span><span class="n num">${nd}</span></div>
       <div class="lrow"><span class="dotpill" style="background:${SAFE};border-color:#CBD5E1"></span><span class="t">Within 30 min</span><span class="n num">${159-nd}</span></div>
       <div class="lrow"><span class="t muted">${fmt(CO.filter(c=>S[c.geoid].min>30).reduce((t,c)=>t+c.births,0))} births exposed</span></div>`;
  } else if(view==='delta'){const c=[0,0,0,0,0];for(const r of rows)c[dIdx(r.delta)]++;
    document.getElementById('leg').innerHTML=DIVL.map((b,i)=>
      `<div class="lrow"><span class="dotpill" style="background:${b[0]}"></span><span class="t">${b[1]}</span><span class="n num">${c[i]}</span></div>`).join('');
  } else {const c=[0,0,0,0,0];for(const x of CO)c[bIdx(S[x.geoid].min)]++;
    document.getElementById('leg').innerHTML=BUCK.map((b,i)=>
      `<div class="lrow"><span class="dotpill" style="background:${RAMP[i]}"></span><span class="t">${b[2]}</span><span class="n num">${c[i]}</span></div>`).join('');}
  document.getElementById('legScen').innerHTML=staged
    ?`<div class="lrow"><span class="t">Lost</span><span class="n num" style="color:#B71C1C">${lost.length}</span></div>
      <div class="lrow"><span class="t">Gained</span><span class="n num" style="color:#1B5E20">${gained.length}</span></div>
      <div class="lrow"><span class="t">Displaced</span><span class="n num">${fmt(disp)}</span></div>`
    :'<div class="lrow"><span class="t muted">Baseline &mdash; no changes staged</span></div>';

  drawMap(S,rows); drawDrawer(changed,rows);
  if(typeof placePanel==='function') requestAnimationFrame(placePanel);
  document.getElementById('dmeta').textContent=
    (staged?`${changed.length} counties changed · `:'Baseline · ')+(selected?selected.name+' County':'click a county on the map');
  document.getElementById('chips').innerHTML=
    [...closed].map(id=>{const f=FA.find(x=>x.id===id);
      return `<span class="chip">${f.name}<button data-un="${id}">&times;</button></span>`;}).join('')+
    added.map((a,i)=>`<span class="chip add">+ ${a.name}<button data-rm="${i}">&times;</button></span>`).join('');
  document.querySelectorAll('[data-un]').forEach(b=>b.onclick=e=>{closed.delete(e.target.dataset.un);render();});
  document.querySelectorAll('[data-rm]').forEach(b=>b.onclick=e=>{added.splice(+e.target.dataset.rm,1);render();});
}

function drawMap(S,rows){
  const svg=document.getElementById('map'), kx=CELLS.kx, B=CELLS.bbox;
  const w=B[2]-B[0], h=B[3]-B[1], pad=w*0.02;
  // viewBox scales with the container, so the map never clips when the drawer
  // resizes the stage. y is flipped at emit time (north up).
  svg.setAttribute('viewBox',`${(B[0]-pad).toFixed(3)} ${(-pad).toFixed(3)} ${(w+2*pad).toFixed(3)} ${(h+2*pad).toFixed(3)}`);
  svg.setAttribute('preserveAspectRatio','xMidYMid meet');
  const X=u=>u, Y=v=>B[3]-v;
  let g='', marks=[];
  for(const r of rows){
    const cell=CELLOF[r.c.geoid]; if(!cell) continue;
    const fill = view==='delta' ? DIV[dIdx(r.delta)]
               : view==='desert' ? (S[r.c.geoid].min>30 ? CRISIS : SAFE)
               : RAMP[bIdx(S[r.c.geoid].min)];
    const d=cell.map((p,i)=>(i?'L':'M')+p[0].toFixed(3)+','+Y(p[1]).toFixed(3)).join('')+'Z';
    const hi=r.state==='lost'?CRISIS:r.state==='gained'?RESCUE:null;
    g+=`<path class="cell${selected&&selected.geoid===r.c.geoid?' sel':''}" d="${d}" fill="${fill}"
        ${hi?`stroke="${hi}" stroke-width="2.6"`:''} vector-effect="non-scaling-stroke" data-g="${r.c.geoid}"/>`;
    if(hi) marks.push({r,hi});
  }
  // Secondary encoding: red/green alone is ΔE 5.0 for deuteranopes, so every
  // affected county also gets a pulse ring (motion) and a glyph (shape).
  for(const m of marks){
    const x=m.r.c.lon*kx, y=Y(m.r.c.lat), lost=m.r.state==='lost';
    if(lost) g+=`<circle class="pulse" cx="${x.toFixed(3)}" cy="${y.toFixed(3)}" r="0.13" stroke="${CRISIS}" vector-effect="non-scaling-stroke"/>`;
    g+=`<circle cx="${x.toFixed(3)}" cy="${y.toFixed(3)}" r="0.085" fill="${m.hi}" stroke="#fff" stroke-width="1.6" vector-effect="non-scaling-stroke"/>`;
    g+=`<text class="cmark" x="${x.toFixed(3)}" y="${(y+0.045).toFixed(3)}" fill="#fff">${lost?'!':'\u2713'}</text>`;
  }
  const T=0.055;
  for(const f of actF()){
    const x=f.lon*kx, y=Y(f.lat), nw=f.id.startsWith('new_');
    g+=`<path d="M${x.toFixed(3)},${(y-T*1.25).toFixed(3)}L${(x+T).toFixed(3)},${(y+T*0.8).toFixed(3)}L${(x-T).toFixed(3)},${(y+T*0.8).toFixed(3)}Z"
        fill="${nw?'#2E7D32':'#0F172A'}" stroke="#fff" stroke-width="1.4" vector-effect="non-scaling-stroke"
        data-f="${f.id}" style="cursor:pointer"/>`;
  }
  for(const f of FA.filter(x=>closed.has(x.id))){
    const x=f.lon*kx, y=Y(f.lat), c=T*1.3;
    g+=`<g data-f="${f.id}" style="cursor:pointer">
      <circle cx="${x.toFixed(3)}" cy="${y.toFixed(3)}" r="${c.toFixed(3)}" fill="#fff" stroke="#D32F2F" stroke-width="2.4" vector-effect="non-scaling-stroke"/>
      <path d="M${(x-c*0.5).toFixed(3)},${(y-c*0.5).toFixed(3)}L${(x+c*0.5).toFixed(3)},${(y+c*0.5).toFixed(3)}M${(x+c*0.5).toFixed(3)},${(y-c*0.5).toFixed(3)}L${(x-c*0.5).toFixed(3)},${(y+c*0.5).toFixed(3)}"
        stroke="#D32F2F" stroke-width="2.2" stroke-linecap="round" vector-effect="non-scaling-stroke"/></g>`;
  }
  svg.innerHTML=g;
  const tip=document.getElementById('tip');
  const move=(e,html)=>{tip.style.opacity=1;tip.innerHTML=html;
    const r=tip.getBoundingClientRect();
    tip.style.left=Math.min(e.clientX+15,innerWidth-r.width-12)+'px';
    tip.style.top=Math.min(e.clientY+15,innerHeight-r.height-12)+'px';};
  svg.querySelectorAll('.cell').forEach(el=>{
    const r=rows.find(x=>x.c.geoid===el.dataset.g);
    el.onmousemove=e=>{
      const m=r.scen.min, hi=nearestHigh(r.c), tags=[];
      if(m>30) tags.push('<span class="tg bad">&#9888; Desert (&gt;30 min)</span>');
      else tags.push('<span class="tg ok">&#10003; Within 30 min</span>');
      if(r.c.desert) tags.push('<span class="tg warn">MoD desert</span>');
      if(r.state==='lost') tags.push('<span class="tg bad">Lost coverage</span>');
      if(r.state==='gained') tags.push('<span class="tg ok">Coverage rescued</span>');
      if(r.state==='shifted') tags.push('<span class="tg n">Reassigned</span>');
      move(e,`<span class="h">${r.c.name} County</span>
        <div class="tags">${tags.join('')}</div>
        <div class="kv">
          <span>Nearest</span><span>${r.scen.fac.name} &middot; ${m.toFixed(1)} min</span>
          <span>Nearest Lvl III+</span><span>${hi?`${hi.f.name} &middot; ${hi.mi.toFixed(0)} mi / ${hi.min.toFixed(0)} min`:'none modeled'}</span>
          <span>Births affected</span><span>${fmt(r.c.births)} / yr</span>
          ${r.state!=='unchanged'?`<span>Change</span><span>${r.base.min.toFixed(1)} &rarr; ${m.toFixed(1)} min (${r.delta>0?'+':''}${r.delta.toFixed(1)})</span>`:''}
        </div>`);};
    el.onmouseleave=()=>tip.style.opacity=0;
    el.onclick=()=>{selected=r.c;tab='detail';
      document.querySelectorAll('.dtab').forEach(x=>x.classList.toggle('on',x.dataset.t==='detail'));
      render();};});
  svg.querySelectorAll('[data-f]').forEach(el=>{
    const f=actF().concat(FA).find(x=>x.id===el.dataset.f); if(!f) return;
    el.onmousemove=e=>move(e,`<span class="h">${f.name}</span><br><span class="m">${f.city}, ${f.state} · Level ${f.level||'—'}${f.border?' · border anchor':''}</span>
      <br><span class="m">${closed.has(f.id)?'CLOSED in scenario — click to reopen':'click to close'}</span>`);
    el.onmouseleave=()=>tip.style.opacity=0;
    el.onclick=()=>{if(f.id.startsWith('new_'))return;closed.has(f.id)?closed.delete(f.id):closed.add(f.id);
      step=0;document.querySelectorAll('.step').forEach(x=>x.classList.remove('on'));render();};});
}

function drawDrawer(changed,rows){
  const b=document.getElementById('dbody');
  if(tab==='changed'){
    // selected county floats to the top so a map click is instantly readable
    const ord=selected?[...changed].sort((a,b)=>(b.c.geoid===selected.geoid)-(a.c.geoid===selected.geoid)):changed;
    b.innerHTML=changed.length?`<table><thead><tr><th>County</th><th class="n">Births</th><th class="n">Drive time</th><th class="n">Change</th></tr></thead><tbody>`+
      ord.map(r=>`<tr data-g="${r.c.geoid}"${selected&&selected.geoid===r.c.geoid?' class="sel"':''}>
        <td><b>${r.c.name}</b><br><span class="muted" style="font-size:10.5px">&rarr; ${r.scen.fac.name}</span></td>
        <td class="n">${fmt(r.c.births)}</td>
        <td class="n">${r.base.min.toFixed(1)} &rarr; ${r.scen.min.toFixed(1)}<br>
          <span class="status ${r.state}">${r.state==='lost'?'Critical':r.state==='gained'?'Gained':'Absorbed'}</span></td>
        <td class="n"><span class="${r.delta>0?'over':'under'}">${r.delta>0?'+':''}${r.delta.toFixed(1)} min</span></td></tr>`).join('')+'</tbody></table>'
      :(()=>{
        const S2=(closed.size||added.length)?solve():B0;
        const gaps=CO.map(c=>({c,m:S2[c.geoid].min})).filter(x=>x.m>30)
                     .sort((a,b)=>b.c.births-a.c.births).slice(0,12);
        return `<p class="muted" style="margin:2px 0 10px;font-size:11.5px">No scenario staged — showing the largest existing access gaps.</p>
        <table><thead><tr><th>County</th><th class="n">Births / yr</th><th class="n">Drive</th><th class="n">Over 30</th></tr></thead><tbody>`+
        gaps.map(g=>`<tr data-g="${g.c.geoid}"${selected&&selected.geoid===g.c.geoid?' class="sel"':''}>
          <td><b>${g.c.name}</b><br><span class="muted" style="font-size:10.5px">&rarr; ${S2[g.c.geoid].fac.name}</span></td>
          <td class="n">${fmt(g.c.births)}</td><td class="n">${g.m.toFixed(1)} min</td>
          <td class="n"><span class="over">+${(g.m-30).toFixed(1)} min</span></td></tr>`).join('')+'</tbody></table>';})();
    b.querySelectorAll('tr[data-g]').forEach(tr=>{tr.style.cursor='pointer';
      tr.onclick=()=>{selected=CO.find(c=>c.geoid===tr.dataset.g);render();};});
  } else if(tab==='absorb'){
    const agg={}; for(const r of changed){ if(r.scen.fac.id===r.base.fac.id)continue;
      (agg[r.scen.fac.id]||={f:r.scen.fac,n:0,b:0}); agg[r.scen.fac.id].n++; agg[r.scen.fac.id].b+=r.c.births;}
    const bb={}; for(const c of CO){const id=B0[c.geoid].fac.id; bb[id]=(bb[id]||0)+c.births;}
    const L=Object.values(agg).sort((a,b)=>b.b-a.b);
    b.innerHTML=L.length?`<table><thead><tr><th>Facility</th><th class="n">Absorbed</th><th class="n">Increase</th></tr></thead><tbody>`+
      L.map(a=>{const base=bb[a.f.id]||0;return `<tr><td><b>${a.f.name}</b><br><span class="muted" style="font-size:10.5px">${a.f.city} · Level ${a.f.level||'—'} · ${a.n} ${a.n===1?'county':'counties'}</span></td>
        <td class="n"><b>${fmt(a.b)}</b><br><span class="muted" style="font-size:10.5px">of ${fmt(base)}</span></td>
        <td class="n">${base?`<span class="status ${100*a.b/base>25?'lost':'shifted'}">+${(100*a.b/base).toFixed(0)}%</span>`:'<span class="muted" style="font-size:10.5px">new<br>catchment</span>'}</td></tr>`;}).join('')+'</tbody></table>'
      :'<p class="muted" style="padding:14px 0">No births reassigned.</p>';
  } else {
    if(!selected){b.innerHTML='<p class="muted" style="padding:14px 0">Click any county on the map to inspect it.</p>';return;}
    const c=selected,r=rows.find(x=>x.c.geoid===c.geoid);
    const tr=((c.births-c.births2015)/c.births2015*100);
    b.innerHTML=`<table class="kv"><tbody>
      <tr><th>County</th><td><b>${c.name}</b> &middot; FIPS ${c.geoid}</td></tr>
      <tr><th>Nearest facility</th><td>${r.scen.fac.name} — ${r.scen.fac.city}, ${r.scen.fac.state}${r.scen.fac.border?' (border anchor)':''} &middot; Level ${r.scen.fac.level||'—'}</td></tr>
      <tr><th>Modeled travel time</th><td><b class="num">${r.scen.min.toFixed(1)} min</b> &nbsp;<span class="status ${r.scen.min<=30?'gained':'lost'}">${r.scen.min<=30?'Within 30 min':'Beyond 30 min'}</span>
        ${r.state!=='unchanged'?` &nbsp;<span class="muted">baseline ${r.base.min.toFixed(1)} min (${r.delta>0?'+':''}${r.delta.toFixed(1)})</span>`:''}</td></tr>
      <tr><th>Annual births (2024)</th><td class="num">${fmt(c.births)} &nbsp;<span class="muted">2015: ${fmt(c.births2015)} · ${tr>0?'+':''}${tr.toFixed(1)}% over the decade</span></td></tr>
      <tr><th>March of Dimes tier</th><td>${c.tier}${c.desert?' &middot; <b>maternity care desert</b>':''}</td></tr></tbody></table>
      <div class="evid"><b>Clinical context.</b><br>${DATA.meta.clinical_evidence.map(e=>`&bull; ${e.band} — ${e.finding}`).join('<br>')}
      <br><span class="muted">${DATA.meta.threshold_note}</span></div>`;
  }
}

// ── assistant ──
const plog=document.getElementById('plog');
const say=(t,who,src)=>{const d=document.createElement('div');d.className='msg '+who;
  d.innerHTML=t+(src?`<span class="src">${src}</span>`:'');plog.appendChild(d);plog.scrollTop=plog.scrollHeight;};
const SRC='Modeled estimate · Confidence B · Haversine ×1.30 / 45 mph · not routed drive time';
function answer(q){const t=q.toLowerCase(),S=(closed.size||added.length)?solve():B0;
  if(/\b(should i|my pregnancy|am i|safest for me|my baby|i'm pregnant|im pregnant|which hospital should)\b/.test(t))
    return["I can't advise on individual medical care or recommend a facility for a specific person. MaternalGrid models geographic access for planning, not clinical decisions. Please consult a healthcare provider — in an emergency, call 911. I'm glad to explain regional access patterns instead.",''];
  if(/desert/.test(t))return[`A <b>maternity care desert</b> is a county with no hospital or birth centre offering obstetric care and no obstetric provider. Georgia has <b>${BASE.mod_deserts} of 159</b> (${BASE.pct_mod_desert}%). They hold just <b>${BASE.desert_births_share_pct}%</b> of the state's births — a small share of births across a large share of its land.`,'March of Dimes 2026 · GDPH OASIS 2024'];
  if(/30 min|thirty|threshold/.test(t))return[`30 minutes is a <b>conservative operational planning threshold, not a published clinical cut-point</b>.<br>${DATA.meta.clinical_evidence.map(e=>`&bull; ${e.band}: ${e.finding}`).join('<br>')}<br>It sits below the first measured risk tier.`,'Peer-reviewed literature'];
  if(/biggest gap|where should|most under|worst|priority/.test(t)){
    const g=CO.map(c=>({c,m:S[c.geoid].min})).filter(x=>x.m>30).sort((a,b)=>b.c.births-a.c.births).slice(0,5);
    return[`Ranked by annual births beyond 30 minutes:<br>${g.map((x,i)=>`${i+1}. <b>${x.c.name}</b> — ${fmt(x.c.births)} births, ${x.m.toFixed(1)} min`).join('<br>')}<br><i>Candidates for analysis, not a funding recommendation.</i>`,SRC];}
  if(/source|data come|where.*data|cite|current/.test(t))
    return[`Births: <b>${DATA.meta.sources.births}</b><br>Access tiers: <b>${DATA.meta.sources.tiers}</b><br>Facilities: <b>${DATA.meta.sources.facilities}</b><br>All public, aggregate, county-level. No patient records, no PHI.`,'Open data — citable'];
  if(/how.*calculat|travel time|method|model|accurate|confiden/.test(t))
    return[`Haversine distance from the county population centre to each facility × road factor <b>1.30</b> ÷ <b>45 mph</b>; nearest active facility wins. <b>Not</b> routed drive time — no traffic, weather or time of day. A 90% band is published on the statewide average.`,SRC];
  const hit=CO.find(c=>t.includes(c.name.toLowerCase()));
  if(hit){const m=S[hit.geoid],b=B0[hit.geoid],d=m.min-b.min;
    return[`<b>${hit.name} County</b> — nearest delivering facility is <b>${m.fac.name}</b> at <b>${m.min.toFixed(1)} min</b> (${m.min<=30?'within':'beyond'} the threshold).<br>${fmt(hit.births)} annual births · MoD tier: ${hit.tier}.`+
      (Math.abs(d)>.05?`<br>Under the staged scenario: ${d>0?'+':''}${d.toFixed(1)} min vs baseline.`:''),SRC];}
  return["I don't have grounded information on that. I can cover maternity care deserts, the 30-minute threshold, methodology, data sources, the largest access gaps, or any Georgia county by name.",''];}
const ask=q=>{say(q,'me');const[a,s]=answer(q);setTimeout(()=>say(a,'bot',s),170);};
const panel=document.getElementById('panel'), fab=document.getElementById('fab');
// Keep the assistant clear of the inspection drawer: anchor it above whatever
// height the drawer currently occupies, and cap it so it never runs off-screen.
function placePanel(){
  const bottom=94;
  panel.style.bottom=bottom+'px';
  panel.style.maxHeight=Math.max(220, Math.round(innerHeight-bottom-24))+'px';
}
addEventListener('resize',placePanel);
fab.onclick=()=>{placePanel();const on=panel.classList.toggle('on');panel.classList.remove('min');
  fab.setAttribute('aria-expanded',on);
  const bd=fab.querySelector('.badge'); if(bd)bd.remove();
  if(on&&!plog.children.length)say("I help interpret MaternalGrid access simulations for planning. My figures are AI-assisted estimates from open Georgia health data, not clinical guidance. For personal medical questions please talk to a healthcare provider — in an emergency, call 911.",'bot');
  if(on)document.getElementById('pIn').focus();};
document.getElementById('pMin').onclick=e=>{e.stopPropagation();panel.classList.toggle('min');};
document.getElementById('pClose').onclick=e=>{e.stopPropagation();panel.classList.remove('on');
  fab.setAttribute('aria-expanded','false');fab.focus();};
addEventListener('keydown',e=>{if(e.key==='Escape'&&panel.classList.contains('on')){panel.classList.remove('on');fab.focus();}});
document.getElementById('fabHide').onclick=e=>{e.stopPropagation();
  panel.classList.remove('on'); fab.setAttribute('aria-expanded','false');
  document.getElementById('fabWrap').classList.add('hid');
  document.getElementById('fabShow').classList.add('on');};
document.getElementById('fabShow').onclick=()=>{
  document.getElementById('fabWrap').classList.remove('hid');
  document.getElementById('fabShow').classList.remove('on');
  fab.focus();};
document.querySelectorAll('.pquick button').forEach(b=>b.onclick=()=>ask(b.dataset.q));
document.getElementById('pIn').addEventListener('keydown',e=>{
  if(e.key==='Enter'&&e.target.value.trim()){ask(e.target.value.trim());e.target.value='';}});

// ── executive tour ──
// Each step stages a scenario, sets the map mode that tells its story, and
// eases the viewBox toward the counties the step is about.
let flyRAF=null;
function flyTo(geoids,pad){
  const svg=document.getElementById('map'), B=CELLS.bbox;
  const full=[B[0]-(B[2]-B[0])*0.02, -(B[2]-B[0])*0.02, (B[2]-B[0])*1.04, (B[3]-B[1])*1.04];
  let target=full;
  if(geoids&&geoids.length){
    let x0=1e9,x1=-1e9,y0=1e9,y1=-1e9;
    for(const g of geoids){const cell=CELLOF[g]; if(!cell)continue;
      for(const p of cell){x0=Math.min(x0,p[0]);x1=Math.max(x1,p[0]);y0=Math.min(y0,B[3]-p[1]);y1=Math.max(y1,B[3]-p[1]);}}
    if(x1>x0){
      const m=(pad||0.9);
      const cx=(x0+x1)/2, cy=(y0+y1)/2;
      let w=Math.max((x1-x0)*(1+m),(B[2]-B[0])*0.62), h=Math.max((y1-y0)*(1+m),(B[3]-B[1])*0.62);
      const ar=full[2]/full[3];
      if(w/h<ar) w=h*ar; else h=w/ar;
      target=[cx-w/2, cy-h/2, w, h];
    }
  }
  const cur=(svg.getAttribute('viewBox')||full.join(' ')).split(/\s+/).map(Number);
  const t0=performance.now(), DUR=760;
  if(flyRAF) cancelAnimationFrame(flyRAF);
  const ease=t=>t<.5?4*t*t*t:1-Math.pow(-2*t+2,3)/2;
  (function tick(now){
    const k=Math.min(1,(now-t0)/DUR), e=ease(k);
    svg.setAttribute('viewBox',cur.map((v,i)=>(v+(target[i]-v)*e).toFixed(3)).join(' '));
    if(k<1) flyRAF=requestAnimationFrame(tick);
  })(t0);
}
const TOURNOTE={
  0:'Start here — each step stages the scenario and flies the map to the affected region.',
  1:'74 of 159 counties already sit beyond the 30-minute emergency threshold — 13,029 births a year.',
  2:'One rural closure pushes Hart County over the line and reassigns its births across a state border.',
  3:'A single Level III center in Effingham pulls 870 births back inside the threshold.'};
function goStep(n){
  step=n; closed.clear(); added.length=0; selected=null;
  if(n===1){ view='desert'; tab='changed'; }
  if(n===2){ closed.add('ga_sacred_heart_medical_center_lavonia'); view='desert'; tab='changed'; }
  if(n===3){ addFac('13103'); view='delta'; tab='changed'; }
  document.querySelectorAll('.dtab').forEach(x=>x.classList.toggle('on',x.dataset.t===tab));
  document.querySelectorAll('.step').forEach(b=>b.classList.toggle('on',+b.dataset.step===n));
  document.getElementById('tourNote').textContent=TOURNOTE[n]||TOURNOTE[0];
  syncMode(); render();
  requestAnimationFrame(()=>{
    if(n===2) flyTo(['13147','13119','13105'],1.6);
    else if(n===3) flyTo(['13103'],2.2);
    else flyTo(null);
  });
}
document.querySelectorAll('.step').forEach(b=>b.onclick=()=>goStep(+b.dataset.step));
document.getElementById('customBtn').onclick=e=>{
  const on=document.getElementById('custom').classList.toggle('on');
  e.target.classList.toggle('on',on);
  e.target.innerHTML='Custom simulation '+(on?'&#9652;':'&#9662;');};
document.getElementById('resetBtn').onclick=()=>goStep(1);

// ── wiring ──
document.getElementById('faclist').innerHTML=FA.filter(f=>f.status==='active').map(f=>`<option value="${f.name}">`).join('');
document.getElementById('addSel').innerHTML='<option value="">Open a Level III facility in…</option>'+
  CO.slice().sort((a,b)=>a.name.localeCompare(b.name)).map(c=>`<option value="${c.geoid}">${c.name} County</option>`).join('');
function addFac(g){const c=CO.find(x=>x.geoid===g); if(!c||added.some(a=>a.geoid===g))return;
  added.push({id:'new_'+g,name:`Proposed Level III — ${c.name}`,city:c.name,state:'GA',border:false,
              level:'III',status:'active',lat:c.lat,lon:c.lon,geoid:g});}
document.getElementById('closeIn').addEventListener('change',e=>{
  const f=FA.find(x=>x.name===e.target.value&&x.status==='active');
  if(f){closed.add(f.id);e.target.value='';step=0;
    document.querySelectorAll('.step').forEach(x=>x.classList.remove('on'));render();}});
document.getElementById('addSel').onchange=e=>{if(e.target.value){addFac(e.target.value);e.target.value='';step=0;
  document.querySelectorAll('.step').forEach(x=>x.classList.remove('on'));render();}};
function syncSeg(){}
function syncDrawer(){}
function syncMode(){document.querySelectorAll('#modeSeg button').forEach(b=>b.classList.toggle('on',b.dataset.m===(view==='scenario'?'bands':view)));}
document.querySelectorAll('#modeSeg button').forEach(b=>b.onclick=()=>{
  view=b.dataset.m==='bands'?'scenario':b.dataset.m; syncMode(); render();});
document.querySelectorAll('.dtab').forEach(t=>t.onclick=()=>{tab=t.dataset.t;
  document.querySelectorAll('.dtab').forEach(x=>x.classList.toggle('on',x===t));render();});
addEventListener('resize',()=>render());
goStep(1);
const v=stats(B0);
console.log('[self-check]',v.no,'/',BASE.counties_beyond_30min,'·',v.bn,'/',BASE.births_beyond_30min,
  '·',v.avg.toFixed(1),'/',BASE.avg_minutes_birth_weighted,
  '·',(v.no===BASE.counties_beyond_30min&&v.bn===BASE.births_beyond_30min)?'PASS':'FAIL');
'''

html=('<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">'
 '<meta name="viewport" content="width=device-width,initial-scale=1">'
 '<title>MaternalGrid</title><style>'+CSS+'</style></head><body>'+BODY+
 '<script>'+JS.replace('__DATA__',json.dumps(D,separators=(',',':')))
             .replace('__CELLS__',json.dumps(C,separators=(',',':')))+'</script></body></html>')
open('MaternalGrid_Dashboard.html','w').write(html)
import os;print(f"built {os.path.getsize('MaternalGrid_Dashboard.html')/1024:.0f} KB")
