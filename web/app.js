
async function loadJSON(path){ try{ const r=await fetch(path); if(!r.ok) return null; return await r.json(); }catch(e){ return null; } }
function text(id, v){ document.getElementById(id).textContent = v }
const PAGE_SIZE = 10;
(async()=>{
  const grouped = await loadJSON('/data/latest_headlines.json');
  const summary = await loadJSON('/data/latest_summary.json');
  const history = await loadJSON('/data/history.json');
  if(summary){
    text('kpi-headlines', summary.headlines?.count ?? 0);
    text('kpi-slow', summary.perf?.slow ?? 0);
    text('kpi-schema', summary.schema?.issues ?? 0);
    document.getElementById('summary').textContent = JSON.stringify(summary, null, 2);
  }
  if(history && Array.isArray(history) && history.length){
    const ctx=document.getElementById('chartRuns');
    const labels=history.map(h=>h.ts.slice(0,10)+' '+h.ts.slice(11,19));
    const dataHead=history.map(h=>h.summary?.headlines?.count||0);
    const dataSlow=history.map(h=>h.summary?.perf?.slow||0);
    const dataSchema=history.map(h=>h.summary?.schema?.issues||0);
    new Chart(ctx,{type:'line',data:{labels,datasets:[
      {label:'Headlines', data:dataHead, borderColor:'#60a5fa'},
      {label:'Slow URLs', data:dataSlow, borderColor:'#f59e0b'},
      {label:'Schema issues', data:dataSchema, borderColor:'#34d399'}
    ]}, options:{plugins:{legend:{labels:{color:'#e2e8f0'}}}, scales:{x:{ticks:{color:'#9ca3af'}}, y:{ticks:{color:'#9ca3af'}}}}});
  }
  const select = document.getElementById('sectionSelect');
  const tbody = document.querySelector('#tbl-headlines tbody');
  const pageLabel = document.getElementById('pageLabel');
  const prevBtn = document.getElementById('prevBtn');
  const nextBtn = document.getElementById('nextBtn');
  let sections = [];
  let dataBySection = {};
  let currentSection = '';
  let currentPage = 1;
  function renderOptions(){
    sections.forEach(s=>{ const opt=document.createElement('option'); opt.value=s; opt.textContent=s; select.appendChild(opt); });
  }
  function renderTable(){
    tbody.innerHTML='';
    const list = (dataBySection[currentSection] || []);
    const total = list.length;
    const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    if(currentPage > totalPages) currentPage = totalPages;
    const start = (currentPage-1) * PAGE_SIZE;
    const slice = list.slice(start, start+PAGE_SIZE);
    slice.forEach((row,i)=>{
      const tr=document.createElement('tr');
      const displayRank = start + i + 1;
      tr.innerHTML = `<td>${displayRank}</td><td>${row.title||''}</td><td>${row.section||''}</td><td><a href="${row.url}" target="_blank">open</a></td>`;
      tbody.appendChild(tr);
    });
    pageLabel.textContent = `${currentPage}/${totalPages}`;
    prevBtn.disabled = (currentPage<=1);
    nextBtn.disabled = (currentPage>=totalPages);
  }
  function setSection(sec){ currentSection = sec; currentPage = 1; renderTable(); }
  prevBtn.onclick = ()=>{ if(currentPage>1){ currentPage--; renderTable(); } };
  nextBtn.onclick = ()=>{ currentPage++; renderTable(); };
  select.onchange = ()=> setSection(select.value);
  if(grouped && grouped.by_section){
    sections = grouped.sections || Object.keys(grouped.by_section);
    dataBySection = grouped.by_section;
    renderOptions();
    setSection(sections[0] || '');
  }
})();
