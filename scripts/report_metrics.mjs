import {readFileSync} from 'node:fs';
import {symbols,drawdown,rsi,sentiment} from '../assets/core.mjs';
const input=JSON.parse(readFileSync(0,'utf8')),rows=input.prices??[];
const result={etfs:[],rsi:null,sma200:null,delta:null,score:null};
if(rows.length){
 result.etfs=symbols.map(key=>{const series=drawdown(rows,key);return {symbol:key,close:rows.at(-1)[key],dayChange:rows.length>1?(rows.at(-1)[key]/rows.at(-2)[key]-1)*100:null,drawdown:series.at(-1).value,mdd:Math.min(...series.map(x=>x.value)),series};});
 const prices=rows.map(x=>x.QQQ);result.rsi=rsi(prices);result.sma200=prices.length>=200?prices.slice(-200).reduce((a,b)=>a+b)/200:null;
 result.delta=result.sma200?(prices.at(-1)/result.sma200-1)*100:null;
 if(input.priceFresh)result.score=sentiment({rsi:result.rsi,delta:result.delta,dd:result.etfs[0].drawdown,vix:input.vix,spread:input.spread});
}
process.stdout.write(JSON.stringify(result));
