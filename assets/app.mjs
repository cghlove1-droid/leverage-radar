import {symbols,validate,drawdown,rsi,cutoff,calculate,sentiment,expectedSession,freshness,validDate} from './core.mjs';
const $=id=>document.getElementById(id),fmt=(v,n=2)=>Number.isFinite(v)?v.toLocaleString('ko-KR',{minimumFractionDigits:n,maximumFractionDigits:n}):'—';
let market,rows=[],range=1,calendar,status,local=false;
function demo(){const out=[];for(let i=0;i<2200;i++){const d=new Date(Date.UTC(2020,0,2)+i*864e5);if([0,6].includes(d.getUTCDay()))continue;const t=out.length;out.push({date:d.toISOString().slice(0,10),QQQ:200*Math.exp(.0005*t+.13*Math.sin(t/80)),TQQQ:30*Math.exp(.0008*t+.42*Math.sin(t/80)),SOXL:20*Math.exp(.0007*t+.6*Math.sin(t/65))});}return out;}
function cellRow(values){const tr=document.createElement('tr');for(const value of values){const td=document.createElement('td');td.textContent=value;tr.append(td);}return tr;}
function svgNode(tag,attrs,text){const n=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v]of Object.entries(attrs))n.setAttribute(k,String(v));if(text)n.textContent=text;return n;}
function chart(series){const svg=$('mddChart');svg.replaceChildren();const width=Math.max(320,svg.clientWidth);svg.setAttribute('viewBox',`0 0 ${width} 330`);const colors=['#60a5fa','#f59e0b','#fb7185'];const min=Math.min(-10,...series.flatMap(s=>s.map(x=>x.value)));const x=i=>55+i/Math.max(1,series[0].length-1)*(width-75),y=v=>25+v/min*255;
 for(let i=0;i<=4;i++){const v=min*i/4;svg.append(svgNode('line',{x1:55,x2:width-20,y1:y(v),y2:y(v),stroke:'#2a3650'}),svgNode('text',{x:2,y:y(v)+4,fill:'#98a9c4','font-size':13},fmt(v,1)+'%'));}
 series.forEach((s,i)=>{svg.append(svgNode('polyline',{points:s.map((r,j)=>`${x(j)},${y(r.value)}`).join(' '),fill:'none',stroke:colors[i],'stroke-width':2}));svg.append(svgNode('text',{x:55+i*90,y:320,fill:colors[i],'font-size':16},symbols[i]));});
 const s=series[0];(width<600?[0,s.length-1]:[0,Math.floor((s.length-1)/2),s.length-1]).forEach((i,j)=>svg.append(svgNode('text',{x:x(i),y:300,fill:'#98a9c4','font-size':13,'text-anchor':i===0?'start':i===s.length-1?'end':'middle'},s[i].date)));
 const cursor=svgNode('line',{x1:65,x2:65,y1:20,y2:280,stroke:'#fff',opacity:0});const tooltip=svgNode('text',{x:5,y:17,fill:'#fff','font-size':width<600?10:13});svg.append(cursor,tooltip);
 svg.onpointermove=e=>{const b=svg.getBoundingClientRect(),px=(e.clientX-b.left)/b.width*width,i=Math.max(0,Math.min(s.length-1,Math.round((px-55)/(width-75)*(s.length-1))));cursor.setAttribute('x1',x(i));cursor.setAttribute('x2',x(i));cursor.setAttribute('opacity',.6);tooltip.textContent=s[i].date+'  '+symbols.map((k,j)=>k+' '+fmt(series[j][i].value,1)+'%').join(' / ');};
 svg.onpointerleave=()=>{cursor.setAttribute('opacity',0);tooltip.textContent='';};
}
function render(){
 const expected=expectedSession(calendar),demoMode=market.demo===true;
 const licenseOK=validDate(market.license_valid_until)&&market.license_valid_until>=new Date().toISOString().slice(0,10);
 const fresh=!demoMode&&!local&&licenseOK&&freshness(rows.at(-1).date,expected,calendar?.sessions??[]);
 const mode=demoMode?'DEMO / DATA NOT CONNECTED':local?'LOCAL CSV / 출처 미검증':fresh?'실데이터 · 최신 종가':'실데이터 · 미확인/지연';
 $('mode').textContent=mode;
 $('updated').textContent=`최종 거래일 ${rows.at(-1).date} | 갱신 ${market.updated_at?new Date(market.updated_at).toLocaleString('ko-KR',{timeZone:'Asia/Seoul'})+' KST':'없음'}`;
 $('notice').textContent=demoMode?'가상 시뮬레이션입니다. 실제 시세가 아닙니다. ETF · VIX · 하이일드 스프레드 API가 연결되지 않았습니다.':local?'CSV는 이 브라우저에서만 사용됩니다. 데이터 출처·조정 방식·실제 여부를 검증하지 않았습니다.':`출처: ${market.source||'미상'} | 주식분할 조정 · 배당 미조정\n${market.attribution||''}\n가격 상태: ${fresh?'정상':'미확인 — 지연, 달력 범위 또는 라이선스를 확인하세요.'}`;
 if(status?.state==='error'||status?.state==='not_configured')$('notice').textContent+=`\n자동 갱신: ${status.code} (${status.checked_at||'시각 미상'}) · 기존 데이터 보존`;
 const from=cutoff(rows.at(-1).date,range),all=symbols.map(k=>drawdown(rows,k)),recent=all.map(a=>a.filter(r=>r.date>=from));
 $('summary').replaceChildren(...symbols.map((k,i)=>{const div=document.createElement('div');div.className='card';const current=recent[i].at(-1).value,max=Math.min(...recent[i].map(x=>x.value));div.innerHTML=`<small>${k} 현재 고점 대비 ${demoMode?'(가상)':''}</small><div class="metric red">${fmt(current,1)}%</div><small>선택 기간 최대 낙폭 ${fmt(max,1)}% · 종가 $${fmt(rows.at(-1)[k])}</small>`;return div;}));
 chart(recent);
 const values=rows.map(r=>r.QQQ),rr=rsi(values),ma=values.length>=200?values.slice(-200).reduce((a,b)=>a+b)/200:null,delta=ma?(values.at(-1)/ma-1)*100:null;
 const ext=key=>{const item=market.indicators?.[key];const ok=!demoMode&&!local&&licenseOK&&item?.status==='ok'&&validDate(item.license_valid_until)&&item.license_valid_until>=new Date().toISOString().slice(0,10)&&freshness(item.date,expected,calendar?.sessions??[],3);return {...item,ok,value:ok?item.value:null};};
 const vix=ext('vix'),hy=ext('hySpread');
 const metrics=[['VIX',vix.value,'',vix.date,vix.source,vix.ok,vix.attribution],['하이일드 스프레드',hy.value,'%',hy.date,hy.source,hy.ok,hy.attribution],['QQQ RSI (14)',rr,'',rows.at(-1).date,market.source||'가상 데이터',fresh,'Wilder 방식'],['QQQ 200일선 이격도',delta,'%',rows.at(-1).date,market.source||'가상 데이터',fresh,`SMA200 $${fmt(ma)}`]];
 $('riskMetrics').replaceChildren(...metrics.map(([name,value,unit,date,source,ok,credit])=>{const d=document.createElement('div');d.className='riskbox';const label=document.createElement('small'),b=document.createElement('b'),info=document.createElement('small');label.textContent=name;b.textContent=demoMode&&name.startsWith('QQQ')?`가상 ${fmt(value)}`:ok&&Number.isFinite(value)?fmt(value)+unit:'미확인';info.textContent=`${source||'미연결'} · ${date||'관측일 없음'} · ${ok?'확인':demoMode?'데모':'지연/누락/미검증'} ${credit||''}`;d.append(label,b,info);return d;}));
 const score=fresh?sentiment({rsi:rr,delta,dd:all[0].at(-1).value,vix:vix.value,spread:hy.value}):null;
 $('fearScore').textContent=score??'—';$('fearLabel').textContent=score===null?'필수 지표 미확인':score<25?'극단적 공포':score<45?'공포':score<56?'중립':score<75?'탐욕':'극단적 탐욕';$('needle').hidden=score===null;$('needle').style.left=(score??50)+'%';
 $('dataStatus').replaceChildren(...[...symbols.map(k=>[k+' 종가','$'+fmt(rows.at(-1)[k]),rows.at(-1).date,mode]),['VIX',fmt(vix.value),vix.date||'—',vix.ok?'확인':'미확인'],['HY 스프레드',fmt(hy.value),hy.date||'—',hy.ok?'확인':'미확인']].map(cellRow));
}
function calc(){try{const number=id=>$(id).value.trim()===''?NaN:Number($(id).value);const result=calculate(number('nowPrice'),[1,2,3,4].map(i=>({price:number('p'+i),value:number('a'+i)})),$('calcMode').value);$('calcResult').classList.remove('error');$('calcResult').innerHTML=`평균 매수가 <strong>$${fmt(result.avg)}</strong><br>총투입금 $${fmt(result.total)} · 총수량 ${fmt(result.shares,4)}주<br>평가금액 $${fmt(result.value)}<br>평가손익률 <strong>${fmt(result.pnl)}%</strong><br>원금회복 필요 상승률 <strong>${fmt(result.recovery)}%</strong>`;}catch(e){$('calcResult').classList.add('error');$('calcResult').textContent=e.message;}}
$('calcMode').onchange=()=>{for(let i=1;i<=4;i++)document.querySelector(`label[for="a${i}"]`).textContent=($('calcMode').value==='amount'?'투자금 ($)':'수량 (주)')+' '+i;calc();};
document.querySelectorAll('.formgrid input').forEach(e=>e.addEventListener('input',calc));
document.querySelectorAll('input').forEach(e=>{const label=e.previousElementSibling;if(label?.tagName==='LABEL')label.htmlFor=e.id;});calc();
document.querySelectorAll('[data-range]').forEach(b=>b.onclick=()=>{range=Number(b.dataset.range);document.querySelectorAll('[data-range]').forEach(x=>x.classList.toggle('active',x===b));render();});
$('csvBtn').onclick=()=>$('csv').click();$('csv').onchange=async e=>{const file=e.target.files[0];if(!file)return;try{if(file.size>5e6)throw Error('CSV는 5MB 이하만 가능합니다.');const lines=(await file.text()).replace(/^\uFEFF/,'').trim().split(/\r?\n/);if(lines.shift().trim()!=='date,QQQ,TQQQ,SOXL')throw Error('헤더는 date,QQQ,TQQQ,SOXL 순서여야 합니다.');const next=validate(lines.map(l=>{const a=l.split(',').map(x=>x.trim());if(a.length!==4)throw Error('CSV 열 수가 잘못되었습니다.');return {date:a[0],QQQ:Number(a[1]),TQQQ:Number(a[2]),SOXL:Number(a[3])};}));rows=next;market={demo:false,source:'LOCAL CSV'};local=true;render();}catch(err){alert('CSV 오류: '+err.message);}};
async function json(url){const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);return r.json();}
const results=await Promise.allSettled([json('./data/market.json'),json('./data/status.json'),json('./data/calendar.json')]);
status=results[1].status==='fulfilled'?results[1].value:null;calendar=results[2].status==='fulfilled'?results[2].value:null;
try{if(results[0].status!=='fulfilled')throw Error('not connected');market=results[0].value;if(market.demo!==false)throw Error('demo');if(market.adjustment!=='split_only'||!market.source)throw Error('invalid metadata');rows=validate(market.prices);}catch{market={demo:true};rows=demo();}render();

let resizeTimer;window.addEventListener("resize",()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>{if(rows.length)render();},120);});
