import { useEffect, useRef, useState } from 'react';
import { ShieldCheck, Link2, BarChart3, ArrowUpRight, ArrowRight, Search, Check, Info, AlertTriangle, Globe, RotateCcw, BookOpen, ScanLine, LockKeyhole } from 'lucide-react';

const labels = {low: 'ความเสี่ยงต่ำ', medium: 'ความเสี่ยงปานกลาง', high: 'ความเสี่ยงสูง'};
const ruleLabels = {ip_host: 'ใช้ IP เป็นโฮสต์', userinfo: 'มี @ ก่อนชื่อโฮสต์', shortener: 'บริการย่อลิงก์', long_url: 'ลิงก์ยาว', http: 'ระบุ HTTP', urgency:'เร่งให้ตัดสินใจ', secret:'กล่าวถึงข้อมูลสำคัญ', threat:'ขู่ว่าจะระงับบริการ', reward:'อ้างรางวัลหรือสิทธิพิเศษ'};
async function api(url, options) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(response.status === 429 ? 'มีคำขอจำนวนมาก กรุณารอสักครู่แล้วลองอีกครั้ง' : data.detail || 'เชื่อมต่อระบบไม่ได้ กรุณาลองใหม่');
    error.code = data.code;
    throw error;
  }
  return data;
}
function bangkokDate() { return new Intl.DateTimeFormat('en-CA', {timeZone: 'Asia/Bangkok', year: 'numeric', month: '2-digit', day: '2-digit'}).format(new Date()); }
function initialStart() { const d = new Date(bangkokDate() + 'T12:00:00+07:00'); d.setUTCDate(d.getUTCDate() - 6); return d.toISOString().slice(0,10); }
function shortDate(value) { return new Intl.DateTimeFormat('th-TH', {day:'numeric', month:'short'}).format(new Date(value+'T12:00:00+07:00')); }
export function Stats() {
  const [start, setStart] = useState(initialStart);
  const [end, setEnd] = useState(bangkokDate);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let current = true;
    setData(null); setError('');
    api('/api/statistics/?' + new URLSearchParams({start, end, type:'all'}))
      .then(d => current && setData(d)).catch(e => current && setError(e.message));
    return () => { current = false; };
  }, [start, end, retry]);
  const max = Math.max(1, ...(data?.daily.map(d=>d.count) || [0]));
  return <>
    <div className="eyebrow">COMMUNITY INSIGHTS</div>
    <div className="page-heading"><div><h1>สถิติการตรวจสอบ</h1><p>ภาพรวมการตรวจลิงก์และข้อความของทุกคน โดยไม่ระบุตัวบุคคล</p></div><span className="pill"><span className="live-dot"/>ข้อมูลจากการใช้งานจริง</span></div>
    <div className="filters card"><label>ตั้งแต่วันที่<input aria-label="ตั้งแต่วันที่" type="date" value={start} onChange={e=>setStart(e.target.value)}/></label><span>—</span><label>ถึงวันที่<input aria-label="ถึงวันที่" type="date" value={end} onChange={e=>setEnd(e.target.value)}/></label><div className="filter-note"><Info size={17}/> นับเป็นจำนวนครั้ง ไม่ใช่จำนวนผู้ใช้</div></div>
    {error && <div role="alert" className="error">{error}<button onClick={()=>setRetry(x=>x+1)}>ลองใหม่</button></div>}
    {!data && !error && <p role="status" className="card p-8">กำลังโหลดสถิติ…</p>}
    {data && <>
      <div className="stats-grid">
        {[['ตรวจทั้งหมด',data.total,'ครั้ง','all'],['ความเสี่ยงต่ำ',data.levels.low,'ครั้ง','low'],['ความเสี่ยงปานกลาง',data.levels.medium,'ครั้ง','medium'],['ความเสี่ยงสูง',data.levels.high,'ครั้ง','high']].map(([title,n,unit,color])=><div className={'card metric '+color} key={title}><span>{title}</span><strong>{n.toLocaleString()} <small>{unit}</small></strong></div>)}
      </div>
      <div className="chart-grid">
        <section className="card chart-card"><div className="section-top"><h2>จำนวนการตรวจรายวัน</h2><BarChart3 size={20}/></div>
          {!data.total ? <div className="empty"><BarChart3 size={36}/><h3>ยังไม่มีข้อมูลในช่วงนี้</h3><p>เริ่มตรวจลิงก์ แล้วกลับมาดูภาพรวมได้ที่นี่</p></div> :
          <div className="bars" role="img" aria-label="กราฟจำนวนการตรวจรายวัน"><div className="bar-track">{data.daily.map(d=><div className="bar-col" key={d.date} title={d.date+': '+d.count+' ครั้ง'}><b>{d.count}</b><div className="bar" style={{height: Math.max(2, d.count/max*160)}}/><small>{shortDate(d.date)}</small></div>)}</div></div>}
        </section>
        <section className="card chart-card"><h2>สัดส่วนผลประเมิน</h2><p className="muted">จากผลหลักของแต่ละคำขอในช่วงวันที่ที่เลือก</p>
          <div className="distribution">{Object.keys(labels).map(level=><div key={level}><div className="spread"><span><i className={'dot '+level}/>{labels[level]}</span><b>{data.levels[level]} ครั้ง</b></div><div className="rail"><div className={level} style={{width:(data.total ? data.levels[level]/data.total*100 : 0)+'%'}}/></div><small>{data.total ? Math.round(data.levels[level]/data.total*100) : 0}% ของการตรวจ</small></div>)}</div>
        </section>
      </div>
      <section className="card chart-card"><h2>สัญญาณที่พบบ่อย</h2><p className="muted">หนึ่งครั้งอาจพบหลายสัญญาณ ตัวเลขส่วนนี้จึงอาจรวมมากกว่าจำนวนการตรวจ</p>{data.findings.length ? data.findings.map(f=><div className="finding-row" key={f.rule_code}><span>{ruleLabels[f.rule_code] || f.rule_code}</span><b>{f.count} ครั้ง</b></div>) : <p className="muted py-5">ยังไม่มีสัญญาณที่เข้ากฎในช่วงวันที่นี้</p>}</section>
    </>}
  </>;
}
export default function Scanner({onRecord}) {
  const [page, setPage] = useState('scan');
  const [url, setUrl] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [duplicate, setDuplicate] = useState(false);
  const requestKey = useRef(null);
  const resultRef = useRef(null);
  const inputRef = useRef(null);
  const submitting = useRef(false);
  useEffect(()=>{ if(result) resultRef.current?.scrollIntoView({behavior:'smooth',block:'nearest'}); },[result]);
  function changeUrl(value) {setUrl(value); setResult(null); setError(''); setDuplicate(false); requestKey.current = null;}
  function reset() {changeUrl(''); inputRef.current?.focus();}
  async function submit(e) {
    e.preventDefault();
    if(submitting.current) return;
    submitting.current = true;
    setLoading(true); setError(''); setResult(null);
    requestKey.current ||= crypto.randomUUID();
    try {
      const data = await api('/api/scans/url/', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url,request_key:requestKey.current})});
      setResult(data);
      onRecord?.({type:'url', input:url, result:data});
    } catch(e) {setError(e.message); setDuplicate(e.code==='duplicate_request');}
    finally {setLoading(false); submitting.current = false;}
  }
  return <div className="app-shell">
    <aside className="sidebar">
      <a href="#" className="brand" onClick={e=>{e.preventDefault();setPage('scan');}}><div className="brand-icon"><ShieldCheck size={29}/></div><div>CyberGuard<span>KKU · ตรวจสอบก่อนคลิก</span></div></a>
      <div className="nav-label">พื้นที่การใช้งาน</div>
      <nav aria-label="เมนูหลัก">
        <button className={page==='scan'?'active':''} onClick={()=>setPage('scan')}><Link2 size={21}/>ตรวจสอบ URL<ArrowUpRight size={16} className="nav-arrow"/></button>
        <button className={page==='stats'?'active':''} onClick={()=>setPage('stats')}><BarChart3 size={21}/>สถิติรวม</button>
      </nav>
      <div className="sidebar-bottom"><div className="private-icon"><LockKeyhole size={21}/></div><h3>เริ่มใช้ได้ทันที</h3><p>ไม่ต้องสมัครสมาชิก<br/>ไม่บันทึกลิงก์ที่คุณส่งมาตรวจ</p><div className="sidebar-version">โครงงานนักศึกษา · รุ่นทดลอง 0.1</div></div>
    </aside>
    <div className="workspace">
      <header><span>CyberGuard / <b>{page==='scan'?'ตรวจสอบ URL':'สถิติรวม'}</b></span><span className="header-tag"><ShieldCheck size={16}/> ไม่ต้องเข้าสู่ระบบ</span></header>
      <main>
        {page==='stats' ? <Stats/> : <>
          <div className="eyebrow">PAUSE. CHECK. PROTECT.</div>
          <div className="page-heading"><div><h1>เช็กให้ชัวร์ <span>ก่อนคลิกลิงก์</span></h1><p>มองหาสัญญาณความเสี่ยง พร้อมเข้าใจเหตุผลที่ควรระวัง</p></div><span className="pill"><span className="live-dot"/>วิเคราะห์โดยไม่เปิดลิงก์</span></div>
          <div className="scan-layout">
            <div>
              <section className="card scan-card">
                <div className="section-top"><div className="icon-tile"><Link2 size={25}/></div><span className="mini-label">URL CHECKER</span></div>
                <h2>ลิงก์นี้น่าเชื่อถือแค่ไหน?</h2><p className="muted">วาง URL ที่สงสัย เพื่อดูสัญญาณจากรูปแบบของลิงก์</p>
                <form onSubmit={submit}>
                  <label htmlFor="url-input">URL ที่ต้องการตรวจสอบ</label>
                  <div className="url-field"><Globe size={21}/><input id="url-input" ref={inputRef} value={url} onChange={e=>changeUrl(e.target.value)} maxLength={2048} required disabled={loading} placeholder="https://example.com" autoComplete="off" spellCheck="false" aria-describedby="url-hint"/></div>
                  <p id="url-hint" className="field-hint">รองรับ HTTP / HTTPS · สูงสุด 2,048 ตัวอักษร</p>
                  <div className="actions"><button className="primary" type="submit" disabled={loading || !url.trim() || !!result || duplicate}>{loading ? <span className="spinner"/> : <Search size={19}/>} {loading?'กำลังตรวจสอบ…':'ตรวจสอบลิงก์'}{!loading && <ArrowRight size={18}/>}</button><button className="secondary" type="button" disabled={loading} onClick={reset}><RotateCcw size={17}/>{result || duplicate ? 'เริ่มรายการใหม่':'ล้างข้อมูล'}</button></div>
                  {error && <div role="alert" className="error"><AlertTriangle size={18}/>{error}</div>}
                </form>
                <div className="privacy-strip"><LockKeyhole size={17}/><span>เซิร์ฟเวอร์เก็บเฉพาะผลสรุป ไม่เก็บ URL ต้นฉบับ</span></div>
              </section>
              {!result && <section className="steps"><div><span>01</span><h3>วางลิงก์</h3><p>คัดลอก URL ที่ต้องการตรวจ</p></div><div><span>02</span><h3>อ่านเหตุผล</h3><p>ดูสัญญาณที่ระบบพบ</p></div><div><span>03</span><h3>ตรวจสอบก่อนเชื่อ</h3><p>ยืนยันผ่านช่องทางที่รู้จัก</p></div></section>}
            </div>
            <aside className="tips card"><div className="icon-tile warm"><ScanLine size={23}/></div><h2>เราดูอะไรในลิงก์?</h2><p className="muted">ประเมินจากตัวอักษรและโครงสร้าง URL เท่านั้น</p><ul>{[['01','ปลายทางจริง','ชื่อโฮสต์และการใช้ IP'],['02','ส่วนประกอบที่ชวนสับสน','ข้อมูลก่อน @ ในส่วนโฮสต์'],['03','รูปแบบลิงก์','ลิงก์ย่อ ความยาว และ HTTP']].map(([n,t,d])=><li key={n}><span>{n}</span><div><h3>{t}</h3><p>{d}</p></div></li>)}</ul><div className="tip-bottom"><BookOpen size={19}/><p>HTTPS ช่วยเข้ารหัสการเชื่อมต่อ แต่ไม่ได้ยืนยันว่าเว็บนั้นปลอดภัย</p></div></aside>
          </div>
          {result && <section ref={resultRef} className={'card result '+result.risk_level} aria-live="polite">
            <div className="result-heading"><div><div className="eyebrow">ASSESSMENT RESULT</div><h2>{labels[result.risk_level]}</h2><p>ปลายทางจริง: <strong className="host">{result.host}</strong></p></div><div className="score">{result.score}<span>/ 100</span><small>คะแนนตามกฎ</small></div></div>
            <div className="result-body"><div><h3>เหตุผลที่พบ</h3>{result.findings.length ? result.findings.map(f=><div className="reason" key={f.rule_code}><AlertTriangle size={19}/><div><b>{f.title}</b><p>{f.reason}</p></div><span>+{f.points}</span></div>) : <div className="reason"><Check size={20}/><p>ไม่พบสัญญาณที่เข้ากฎรุ่นนี้ ยังควรตรวจสอบผู้ส่งและบริบทเพิ่มเติม</p></div>}</div><div className="advice"><ShieldCheck size={24}/><h3>ทำอย่างไรต่อดี?</h3><p>{result.advice}</p>{!result.scheme_supplied && <p>คุณไม่ได้ระบุ HTTP/HTTPS ระบบจึงไม่ให้คะแนนเรื่องการเข้ารหัส</p>}<button onClick={()=>setPage('stats')}>ดูสถิติรวม <ArrowUpRight size={16}/></button></div></div>
            <div className="result-footer"><Check size={15}/> บันทึกเฉพาะผลสรุปแล้ว <span>กฎ {result.rule_version}</span></div>
          </section>}
          <div className="disclaimer"><Info size={19}/><p><b>ใช้ผลประเมินประกอบการตัดสินใจ</b> คะแนนเป็นกฎรุ่นทดลอง ไม่ใช่เปอร์เซ็นต์ความน่าจะเป็น และไม่รับรองความปลอดภัยของเว็บไซต์</p></div>
        </>}
        <footer><span>CyberGuard KKU</span><span>โครงงานเพื่อการเรียนรู้ · ไม่ใช่บริการรับรองเว็บไซต์</span></footer>
      </main>
    </div>
  </div>;
}


