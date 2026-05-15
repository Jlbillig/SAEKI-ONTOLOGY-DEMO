import React, {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {Activity, AlertTriangle, Database, Search, Play, Square, RefreshCcw, Zap, Download} from 'lucide-react';
import './styles.css';

const API = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

function formatTs(iso){
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleTimeString('en-GB', {hour:'2-digit', minute:'2-digit', second:'2-digit'}) +
    ' ' + d.toLocaleDateString('en-GB', {day:'2-digit', month:'short'});
}

const QUERY_BUTTONS = [
  {id:'most_failure_prone_tool', label:'Most failure-prone tool'},
  {id:'batch_risk', label:'Material batch risk'},
  {id:'machine_anomaly_history', label:'Machine anomaly history'},
  {id:'parts_at_risk', label:'Parts at risk'},
];

function App(){
  const [health, setHealth] = useState(null);
  const [events, setEvents] = useState([]);
  const [failed, setFailed] = useState([]);
  const [part, setPart] = useState('');
  const [investigation, setInvestigation] = useState(null);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  const [liveRunning, setLiveRunning] = useState(false);
  const [queryResult, setQueryResult] = useState(null);
  const [queryLoading, setQueryLoading] = useState(false);
  const [similarFailures, setSimilarFailures] = useState(null);
  const [exporting, setExporting] = useState(false);

  async function safeJson(url, fallback){
    try {
      const r = await fetch(url);
      if (!r.ok) return fallback;
      return await r.json();
    } catch { return fallback; }
  }

  async function load(){
    const h = await safeJson(`${API}/health`, null);
    setHealth(h);
    if (h?.live_running !== undefined) setLiveRunning(h.live_running);
    setEvents(await safeJson(`${API}/events/recent`, []));
    setFailed(await safeJson(`${API}/queries/failed-parts`, []));
  }

  async function startLive(){
    setError('');
    setInvestigation(null);
    setQueryResult(null);
    const r = await fetch(`${API}/live/start`, {method:'POST'});
    const data = await r.json();
    setLiveRunning(true);
    setStatus('Live simulation running — events streaming from factory floor.');
    await load();
  }

  async function stopLive(){
    await fetch(`${API}/live/stop`, {method:'POST'});
    setLiveRunning(false);
    setStatus('Simulation stopped.');
    await load();
  }

  async function seedDemo(){
    setError('');
    setInvestigation(null);
    setQueryResult(null);
    setStatus('Loading deterministic scenario...');
    const r = await fetch(`${API}/demo/seed`, {method:'POST'});
    const data = await r.json();
    setStatus(`${data.events_inserted} events loaded. Primary failed part: ${data.primary_failed_part}.`);
    await load();
    setPart(data.primary_failed_part);
    await investigate(data.primary_failed_part);
  }

  async function resetAll(){
    setError('');
    setInvestigation(null);
    setQueryResult(null);
    setStatus('Resetting...');
    await fetch(`${API}/demo/reset`, {method:'POST'});
    setLiveRunning(false);
    setPart('');
    setStatus('Graph reset.');
    await load();
  }

  async function exportRdf(){
    setError('');
    setExporting(true);
    setStatus('Exporting RDF graph...');
    try {
      const r = await fetch(`${API}/graph/export`);
      if (!r.ok) {
        setError(`Export failed: ${r.status} ${r.statusText}`);
        setStatus('');
        return;
      }
      const data = await r.json();
      const turtle = data.turtle || '';
      if (!turtle.trim()) {
        setError('Graph is empty — seed the demo or start a live run first.');
        setStatus('');
        return;
      }
      // Trigger browser download
      const blob = new Blob([turtle], {type: 'text/turtle'});
      const url = URL.createObjectURL(blob);
      const ts = new Date().toISOString().replace(/[:.]/g,'-').slice(0,19);
      const a = document.createElement('a');
      a.href = url;
      a.download = `factorytrace-${ts}.ttl`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      const sizeKb = (turtle.length / 1024).toFixed(1);
      setStatus(`Downloaded factorytrace-${ts}.ttl (${sizeKb} KB, ${health?.triples ?? '?'} triples).`);
    } catch (e) {
      setError(`Export failed: ${e.message}`);
      setStatus('');
    } finally {
      setExporting(false);
    }
  }

  async function investigate(selectedPart){
    const target = selectedPart || part;
    if (!target) return;
    setError('');
    setSimilarFailures(null);
    const r = await fetch(`${API}/parts/${target}/investigation`);
    if (!r.ok){
      setInvestigation(null);
      setError(`No data found for ${target}. Try a part from the failed parts table.`);
      return;
    }
    const data = await r.json();
    setInvestigation(data);
    const sf = await safeJson(`${API}/parts/${target}/similar-failures`, null);
    setSimilarFailures(sf);
  }

  async function runQuery(queryId){
    setQueryLoading(true);
    setQueryResult(null);
    const data = await safeJson(`${API}/queries/named/${queryId}`, null);
    setQueryResult(data);
    setQueryLoading(false);
  }

  useEffect(()=>{
    load();
    const id = setInterval(load, 3000);
    return () => clearInterval(id);
  },[]);

  const scenarioLabel = health?.live_scenario
    ? health.live_scenario.replace(/_/g,' ')
    : null;

  const hasGraphData = (health?.triples ?? 0) > 0;

  return <div className="page">
    <header>
      <div>
        <h1>FactoryTrace</h1>
        <p>Semantic root-cause engine for CNC quality deviations</p>
      </div>
      <div className="status">
        <Database size={18}/>
        {liveRunning
          ? <span style={{color:'#16a34a'}}>● Live · {scenarioLabel}</span>
          : health?.status || 'connecting'}
      </div>
    </header>

    <section className="panel hero">
      <div>
        <h2>Production simulation</h2>
        <p>
          Start a live run to stream continuous CNC events into the graph — each run generates
          a different failure scenario (machine fault, tool wear, bad batch, or dual cluster).
          Or load the fixed demo scenario for a reproducible walkthrough.
        </p>
      </div>
      <div className="actions">
        {liveRunning
          ? <button onClick={stopLive} style={{background:'#b91c1c',border:'none'}}><Square size={16}/>Stop live run</button>
          : <button onClick={startLive}><Zap size={16}/>Start live run</button>
        }
        <button className="secondary" onClick={seedDemo}><Play size={16}/>Load demo scenario</button>
        <button
          className="secondary"
          onClick={exportRdf}
          disabled={exporting || !hasGraphData}
          title={hasGraphData ? 'Download the current RDF graph as Turtle' : 'Seed the demo or start a live run first'}
        >
          <Download size={16}/>{exporting ? 'Exporting…' : 'Export RDF (.ttl)'}
        </button>
        <button className="secondary" onClick={resetAll}><RefreshCcw size={16}/>Reset</button>
      </div>
      {status && <p className="notice">{status}</p>}
    </section>

    <section className="grid cards">
      <Card icon={<Activity/>} label="Events ingested" value={health?.recent_events ?? events.length}/>
      <Card icon={<AlertTriangle/>} label="Failed parts" value={failed.length}/>
      <Card icon={<Database/>} label="Graph store" value={health ? `RDFLib · ${health.triples} triples` : 'RDFLib'}/>
    </section>

    <section className="panel" style={{marginBottom:16}}>
      <h2>Semantic queries</h2>
      <p style={{color:'#6b7280',margin:'0 0 12px',fontSize:14}}>
        Run a SPARQL-backed query against the live graph. Results update as new events arrive.
      </p>
      <div className="actions" style={{marginBottom:12}}>
        {QUERY_BUTTONS.map(q =>
          <button key={q.id} className="secondary" onClick={()=>runQuery(q.id)}>{q.label}</button>
        )}
      </div>
      {queryLoading && <p style={{color:'#6b7280',fontSize:13}}>Querying graph...</p>}
      {queryResult && <QueryResult result={queryResult}/>}
    </section>

    <main className="grid main">
      <section className="panel large">
        <h2>Part investigation</h2>
        <p style={{color:'#6b7280',margin:'0 0 12px',fontSize:14}}>
          Enter any part ID to trace its full causal context — machine, tool, batch, telemetry anomalies, and related failures.
        </p>
        <div className="search">
          <input
            value={part}
            onChange={e=>setPart(e.target.value)}
            placeholder="e.g. PART-1000-015"
            onKeyDown={e=>e.key==='Enter' && investigate(part)}
          />
          <button onClick={()=>investigate(part)}><Search size={16}/>Investigate</button>
        </div>

        {error && <p className="error">{error}</p>}

        {investigation && <div className="investigation">
          <h3>{investigation.part_id}</h3>
          <p>{investigation.explanation}</p>

          <div className="facts">
            <Fact label="Inspection" value={investigation.inspection_status}/>
            <Fact label="Deviation type" value={investigation.deviation_type}/>
            {investigation.deviation_measurement && <>
              <Fact
                label={investigation.deviation_measurement.label}
                value={`${investigation.deviation_measurement.measured} ${investigation.deviation_measurement.unit}`}
              />
              <Fact
                label="Tolerance limit"
                value={investigation.deviation_measurement.limit_label}
              />
            </>}
            <Fact label="Machine" value={investigation.machine_id}/>
            <Fact label="Tool" value={investigation.tool_id}/>
            {investigation.tool_operations_before_failure > 0 &&
              <Fact label="Tool ops before failure" value={`${investigation.tool_operations_before_failure} operations`}/>
            }
            <Fact label="Material batch" value={investigation.material_batch_id}/>
            <Fact label="Vibration" value={`${investigation.vibration_mm_s} mm/s`}/>
            <Fact label="Temperature" value={`${investigation.temperature_c} C`}/>
            <Fact label="Anomaly flags" value={investigation.telemetry_flags.join(', ') || 'none'}/>
          </div>

          {investigation.potentially_affected_parts.length > 0 && <>
            <h4>Potentially affected parts</h4>
            <div className="chips">
              {investigation.potentially_affected_parts.map(p=>
                <span key={p} style={{cursor:'pointer'}} onClick={()=>{setPart(p); investigate(p);}}>{p}</span>
              )}
            </div>
          </>}

          {similarFailures && (similarFailures.cross_machine_failures?.length > 0 || similarFailures.same_machine_failures?.length > 0) && <>
            <h4>Cross-system failure analysis</h4>
            <SimilarFailures data={similarFailures} onInvestigate={(p)=>{setPart(p);investigate(p);}}/>
          </>}

          <h4>Semantic gap</h4>
          <SemanticGapPanel investigation={investigation}/>

          <h4>Traceability graph</h4>
          <TraceGraph investigation={investigation}/>

          <h4>SPARQL evidence</h4>
          <pre>{investigation.sparql_evidence.part_investigation_query}</pre>
        </div>}
      </section>

      <section className="panel">
        <h2>Failed parts</h2>
        <p style={{color:'#6b7280',margin:'0 0 10px',fontSize:13}}>Click any row to investigate.</p>
        <table>
          <thead><tr><th>Part</th><th>Machine</th><th>Tool</th><th>Batch</th><th>Time</th></tr></thead>
          <tbody>
            {failed.map((r,i)=>
              <tr key={i} onClick={()=>{setPart(r.partId); investigate(r.partId);}} style={{cursor:'pointer'}} title={`Investigate ${r.partId}`}>
                <td><span style={{textDecoration:'underline',textDecorationStyle:'dotted'}}>{r.partId}</span></td>
                <td>{r.machineId}</td>
                <td>{r.toolId}</td>
                <td>{r.batchId}</td>
                <td style={{fontSize:12,color:'#6b7280',whiteSpace:'nowrap'}}>{formatTs(r.timestamp)}</td>
              </tr>
            )}
            {failed.length === 0 && <tr><td colSpan={5} style={{color:'#9ca3af',textAlign:'center',padding:16}}>No failures yet</td></tr>}
          </tbody>
        </table>
      </section>
    </main>

    <section className="panel">
      <h2>Live event stream</h2>
      <table>
        <thead><tr><th>Time</th><th>Event</th><th>Type</th><th>Part</th><th>Machine</th><th>Status</th></tr></thead>
        <tbody>
          {events.slice(0,20).map(e=>
            <tr key={e.event_id} style={e.event_type==='alarm'?{background:'#fef3c7'}:{}}>
              <td style={{fontSize:12,color:'#6b7280',whiteSpace:'nowrap'}}>{formatTs(e.timestamp)}</td>
              <td>{e.event_id}</td>
              <td>{e.event_type}</td>
              <td>{e.part_id
                ? <span style={{textDecoration:'underline',textDecorationStyle:'dotted',cursor:'pointer'}} onClick={()=>{setPart(e.part_id); investigate(e.part_id);}}>{e.part_id}</span>
                : '—'}</td>
              <td>{e.machine_id}</td>
              <td>{e.inspection_status || e.status}</td>
            </tr>
          )}
        </tbody>
      </table>
    </section>
  </div>
}

function QueryResult({result}){
  if (!result?.results?.length) return <p style={{color:'#6b7280',fontSize:13}}>No results.</p>;
  const keys = Object.keys(result.results[0]);
  return <div>
    <p style={{fontSize:13,color:'#374151',marginBottom:6}}><strong>{result.label}</strong> — {result.description}</p>
    <table>
      <thead><tr>{keys.map(k=><th key={k}>{k}</th>)}</tr></thead>
      <tbody>
        {result.results.map((row,i)=>
          <tr key={i}>{keys.map(k=><td key={k}>{row[k]}</td>)}</tr>
        )}
      </tbody>
    </table>
    <details style={{marginTop:8}}>
      <summary style={{fontSize:12,color:'#6b7280',cursor:'pointer'}}>Show SPARQL</summary>
      <pre style={{fontSize:11}}>{result.sparql}</pre>
    </details>
  </div>;
}

function SimilarFailures({data, onInvestigate}){
  const cross = data.cross_machine_failures || [];
  const same = data.same_machine_failures || [];
  return <div style={{marginBottom:12}}>
    <p style={{fontSize:13,color:'#374151',marginBottom:8,padding:'8px 10px',background:'#fef9c3',borderRadius:6,borderLeft:'3px solid #ca8a04'}}>
      {data.insight}
    </p>
    {cross.length > 0 && <>
      <p style={{fontSize:12,fontWeight:600,color:'#b91c1c',marginBottom:4}}>
        ⚠ Same deviation on different machines ({cross.length})
      </p>
      <table style={{marginBottom:8}}>
        <thead><tr><th>Part</th><th>Machine</th><th>Tool</th><th>Batch</th><th>Deviation</th></tr></thead>
        <tbody>{cross.slice(0,8).map((r,i)=>
          <tr key={i} style={{cursor:'pointer'}} onClick={()=>onInvestigate(r.partId)}>
            <td><span style={{textDecoration:'underline',textDecorationStyle:'dotted'}}>{r.partId}</span></td>
            <td>{r.machineId}</td><td>{r.toolId}</td><td>{r.batchId}</td>
            <td style={{fontSize:11}}>{r.deviationType}</td>
          </tr>
        )}</tbody>
      </table>
    </>}
    {same.length > 0 && <>
      <p style={{fontSize:12,fontWeight:600,color:'#6b7280',marginBottom:4}}>
        Same machine, same pattern ({same.length})
      </p>
      <table>
        <thead><tr><th>Part</th><th>Tool</th><th>Batch</th></tr></thead>
        <tbody>{same.slice(0,5).map((r,i)=>
          <tr key={i} style={{cursor:'pointer'}} onClick={()=>onInvestigate(r.partId)}>
            <td><span style={{textDecoration:'underline',textDecorationStyle:'dotted'}}>{r.partId}</span></td>
            <td>{r.toolId}</td><td>{r.batchId}</td>
          </tr>
        )}</tbody>
      </table>
    </>}
  </div>;
}

function SemanticGapPanel({investigation}){
  const flatJson = JSON.stringify({
    "node_id": "ns=2;s=CNC02.Spindle.Vibration",
    "value": investigation.vibration_mm_s,
    "quality": "Good",
    "timestamp": investigation.telemetry_flags.length > 0 ? "2026-05-11T09:31:00Z" : "—",
    "source_machine": investigation.machine_id,
    "status_code": "0x00000000"
  }, null, 2);

  const rdfTriples = [
    `ft:Event_EVT_telemetry a ft:TelemetryEvent ;`,
    `  ft:vibrationMMs "${investigation.vibration_mm_s}"^^xsd:decimal ;`,
    `  ft:timestampValue "2026-05-11T09:31:00Z"^^xsd:dateTime ;`,
    `  ft:associatedWithMachine ft:Machine_${investigation.machine_id?.replace('-','_')} ;`,
    `  ft:associatedWithPart ft:Part_${investigation.part_id?.replace(/-/g,'_')} .`,
    ``,
    `ft:Part_${investigation.part_id?.replace(/-/g,'_')} a ft:Part ;`,
    `  ft:processedMaterialBatch ft:MaterialBatch_${investigation.material_batch_id?.replace('-','_')} ;`,
    `  ft:hasInspectionResult ft:Event_inspection .`,
    ``,
    `ft:RootCauseHypothesis_RCH a ft:RootCauseHypothesis ;`,
    `  ft:hypothesizedCausePart ft:Part_${investigation.part_id?.replace(/-/g,'_')} ;`,
    `  ft:hypothesizedCauseMachine ft:Machine_${investigation.machine_id?.replace('-','_')} ;`,
    `  ft:hypothesizedCauseTool ft:Tool_${investigation.tool_id?.replace('-','_')} .`,
  ].join('\n');

  return <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12,marginBottom:12}}>
    <div>
      <p style={{fontSize:12,fontWeight:600,color:'#6b7280',marginBottom:4}}>
        OPC-UA / MTConnect flat output — syntactic only
      </p>
      <pre style={{fontSize:11,maxHeight:180}}>{flatJson}</pre>
    </div>
    <div>
      <p style={{fontSize:12,fontWeight:600,color:'#16a34a',marginBottom:4}}>
        FactoryTrace semantic graph
      </p>
      <pre style={{fontSize:11,maxHeight:180}}>{rdfTriples}</pre>
    </div>
  </div>;
}

function TraceGraph({investigation}){
  const cx = 520, cy = 160;
  const nodes = [
    {id:'part', x:cx, y:cy, label:investigation.part_id, sub:investigation.inspection_status==='fail' ? 'ft:Part · FAILED' : 'ft:Part', color:investigation.inspection_status==='fail' ? '#b91c1c' : '#1e3a5f', textColor:'#fff'},
    {id:'machine', x:cx-220, y:cy-100, label:investigation.machine_id, sub:'ft:CNCMachine', color:'#1e3a5f', textColor:'#fff'},
    {id:'tool', x:cx+220, y:cy-100, label:investigation.tool_id, sub:'ft:CuttingTool', color:'#1e3a5f', textColor:'#fff'},
    {id:'batch', x:cx, y:cy-190, label:investigation.material_batch_id, sub:'ft:MaterialBatch', color:'#1e3a5f', textColor:'#fff'},
    {id:'flags', x:cx-220, y:cy+110, label:investigation.telemetry_flags.join(', ') || 'none', sub:'ft:AnomalyState', color:'#92400e', textColor:'#fff'},
  ];
  investigation.potentially_affected_parts.slice(0,4).forEach((p,i)=>{
    const spread = Math.min(investigation.potentially_affected_parts.length, 4);
    const startX = cx - ((spread-1)*100)/2;
    nodes.push({id:`aff${i}`, x:startX+(i*100), y:cy+200, label:p, sub:'ft:Part · failed', color:'#6b1a1a', textColor:'#fca5a5'});
  });
  const edges = [
    {from:'machine', to:'part', label:'ft:performedByMachine'},
    {from:'tool', to:'part', label:'ft:usesTool'},
    {from:'batch', to:'part', label:'ft:processedMaterialBatch'},
    {from:'flags', to:'part', label:'ft:hasTelemetryEvent'},
    ...investigation.potentially_affected_parts.slice(0,4).map((_,i)=>({from:'part', to:`aff${i}`, label:'ft:hasInspectionResult'})),
  ];
  const nodeMap = Object.fromEntries(nodes.map(n=>[n.id,n]));
  const W = 1040, H = 440;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{width:'100%',borderRadius:8,background:'#0f172a',marginBottom:12}}>
      {edges.map((e,i)=>{
        const a=nodeMap[e.from], b=nodeMap[e.to];
        if(!a||!b) return null;
        const mx=(a.x+b.x)/2, my=(a.y+b.y)/2;
        return <g key={i}>
          <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#334155" strokeWidth="1.5" strokeDasharray="4 3"/>
          <text x={mx} y={my-5} textAnchor="middle" fill="#64748b" fontSize="9" fontFamily="monospace">{e.label}</text>
        </g>;
      })}
      {nodes.map(n=>(
        <g key={n.id} transform={`translate(${n.x},${n.y})`}>
          <rect x={-72} y={-22} width={144} height={44} rx={8} fill={n.color} opacity={0.9}/>
          <text textAnchor="middle" y={-5} fill={n.textColor} fontSize="11" fontWeight="bold" fontFamily="monospace">{n.label}</text>
          <text textAnchor="middle" y={11} fill={n.textColor} fontSize="9" opacity={0.75} fontFamily="monospace">{n.sub}</text>
        </g>
      ))}
    </svg>
  );
}

function Card({icon,label,value}){
  return <div className="card">{React.cloneElement(icon,{size:24})}<div><p>{label}</p><strong>{value}</strong></div></div>
}

function Fact({label,value}){
  return <div className="fact"><span>{label}</span><strong>{value||'—'}</strong></div>
}

createRoot(document.getElementById('root')).render(<App/>);
