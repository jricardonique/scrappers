
async function loadJSON(path){ try{ const r=await fetch(path); if(!r.ok) return null; return await r.json(); }catch(e){ return null; } }
function text(el, v){ document.getElementById(el).textContent = v }

(async()=>{
  const latest = await loadJSON('/data/latest_headlines.json');
  const summary = await loadJSON('/data/latest_summary.json');
  const history = await loadJSON('/data/history.json');

  // KPIs
  if(summary){
    text('kpi-headlines', summary.headlines?.count ?? 0);
    text('kpi-media', summary.multimedia?.checked ?? 0);
    text('kpi-media-err', summary.multimedia?.errors ?? 0);
    text('kpi-slow', summary.perf?.slow ?? 0);
    text('kpi-schema', summary.schema?.issues ?? 0);
    document.getElementById('summary').textContent = JSON.stringify(summary, null, 2);
  }

  // Headlines table
  if(latest && Array.isArray(latest)){
    const tbody=document.querySelector('#tbl-headlines tbody');
    latest.slice(0,20).forEach((row,i)=>{
      const tr=document.createElement('tr');
      tr.innerHTML=`<td>${i+1}</td><td>${row.title||''}</td><td>${row.section||''}</td><td><a href="${row.url}" target="_blank">open</a></td>`;
      tbody.appendChild(tr);
    });
  }

  // Trend chart
  if(history && Array.isArray(history) && history.length){
    const ctx=document.getElementById('chartRuns');
    const labels=history.map(h=>h.ts.slice(0,10)+' '+h.ts.slice(11,19));
    const dataHead=history.map(h=>h.summary?.headlines?.count||0);
    const dataMediaErr=history.map(h=>h.summary?.multimedia?.errors||0);
    const dataSlow=history.map(h=>h.summary?.perf?.slow||0);
    const dataSchema=history.map(h=>h.summary?.schema?.issues||0);
    new Chart(ctx,{type:'line',data:{labels,datasets:[
      {label:'Headlines', data:dataHead, borderColor:'#60a5fa'},
      {label:'Media errors', data:dataMediaErr, borderColor:'#f87171'},
      {label:'Slow URLs', data:dataSlow, borderColor:'#f59e0b'},
      {label:'Schema issues', data:dataSchema, borderColor:'#34d399'}
    ]}, options:{plugins:{legend:{labels:{color:'#e2e8f0'}}}, scales:{x:{ticks:{color:'#9ca3af'}}, y:{ticks:{color:'#9ca3af'}}}}});
  }
})();
