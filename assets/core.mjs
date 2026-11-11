export const symbols=['QQQ','TQQQ','SOXL'];
export function validDate(s){return typeof s==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&Number.isFinite(Date.parse(s))&&new Date(s+'T00:00:00Z').toISOString().slice(0,10)===s;}
export function validate(rows){
 if(!Array.isArray(rows)||rows.length<2)throw Error('최소 2행의 가격이 필요합니다.');
 const seen=new Set();return rows.map(r=>{
  if(!validDate(r.date)||seen.has(r.date)||!symbols.every(k=>typeof r[k]==='number'&&Number.isFinite(r[k])&&r[k]>0))throw Error('날짜·중복·양수 가격을 확인하세요.');
  seen.add(r.date);return {date:r.date,...Object.fromEntries(symbols.map(k=>[k,r[k]]))};
 }).sort((a,b)=>a.date.localeCompare(b.date));
}
export function drawdown(rows,key){let peak=0;return rows.map(r=>{peak=Math.max(peak,r[key]);return {date:r.date,value:(r[key]/peak-1)*100};});}
export function rsi(values,n=14){
 if(values.length<=n)return null;let gain=0,loss=0;
 for(let i=1;i<=n;i++){const c=values[i]-values[i-1];gain+=Math.max(0,c)/n;loss+=Math.max(0,-c)/n;}
 for(let i=n+1;i<values.length;i++){const c=values[i]-values[i-1];gain=(gain*(n-1)+Math.max(0,c))/n;loss=(loss*(n-1)+Math.max(0,-c))/n;}
 return gain===0&&loss===0?50:loss===0?100:100-100/(1+gain/loss);
}
export function cutoff(last,years){if(!years)return '';const d=new Date(last+'T00:00:00Z');const month=d.getUTCMonth();d.setUTCFullYear(d.getUTCFullYear()-years);if(d.getUTCMonth()!==month)d.setUTCDate(0);return d.toISOString().slice(0,10);}
export function calculate(current,orders,mode){
 if(!Number.isFinite(current)||current<=0)throw Error('현재 가격은 0보다 큰 숫자여야 합니다.');
 if(!['amount','quantity'].includes(mode))throw Error('입력 방식을 확인하세요.');
 let shares=0,total=0;
 for(const {price,value} of orders){
  if(!Number.isFinite(price)||!Number.isFinite(value)||price<0||value<0)throw Error('음수·빈칸·무한대는 사용할 수 없습니다.');
  if(price===0&&value===0)continue;
  if(price<=0||value<=0)throw Error('회차별 매수가와 금액/수량을 모두 입력하세요. 사용하지 않는 회차는 0을 입력하세요.');
  const q=mode==='quantity'?value:value/price;shares+=q;total+=q*price;
 }
 if(total<=0||shares<=0||!Number.isFinite(total)||!Number.isFinite(shares))throw Error('유효한 매수 내역이 필요합니다.');
 const avg=total/shares,pnl=(current/avg-1)*100,recovery=Math.max(0,(avg/current-1)*100);
 if(![avg,pnl,recovery,total*current/avg].every(Number.isFinite))throw Error('입력값이 너무 큽니다.');
 return {shares,total,avg,pnl,recovery,value:shares*current};
}
export function sentiment({rsi,delta,dd,vix,spread}){
 if(![rsi,delta,dd,vix,spread].every(Number.isFinite))return null;
 const clamp=x=>Math.max(0,Math.min(100,x));
 return Math.round([rsi,50+delta*2,100+dd*3,100-(vix-10)*3,100-(spread-2)*20].map(clamp).reduce((a,b)=>a+b)/5);
}
export function expectedSession(calendar,now=new Date()){
 if(!calendar?.sessions?.length||now.toISOString().slice(0,10)>calendar.coverage_end)return null;
 return calendar.sessions.filter(s=>Date.parse(s.close)<=now.getTime()).at(-1)?.date??null;
}
export function freshness(date,expected,sessions,lag=0){
 if(!validDate(date)||!expected||date>expected)return false;
 return sessions.filter(s=>s.date>date&&s.date<=expected).length<=lag;
}
