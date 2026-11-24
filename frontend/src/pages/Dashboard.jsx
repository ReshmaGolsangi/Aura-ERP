// Staff dashboard: target vs achieved, PIP (pending logic), live funnel, hot funnel, funnel vs closure.
import React, { useEffect, useState } from 'react';
import api, { inr } from '../api';

const Kpi = ({ t, v }) => <div className="card kpi">{t}<b>{v}</b></div>;

export default function Dashboard({ me }) {
  const [d, setD] = useState(null);
  const [fun, setFun] = useState(null);
  const [staff, setStaff] = useState([]);
  const [sel, setSel] = useState('');

  useEffect(() => { if (me.role === 'ADMIN') api.get('users/').then((r) => setStaff(r.data)); }, []);
  useEffect(() => { api.get('dashboard/', { params: sel ? { staff: sel } : {} }).then((r) => setD(r.data)); }, [sel]);
  useEffect(() => { api.get('funnel/').then((r) => setFun(r.data)); }, []);
  if (!d || !fun) return <p>Loading…</p>;

  return (
    <>
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h2>Dashboard – {d.staff} (FY {d.fy})</h2>
        {me.role === 'ADMIN' && (
          <div style={{ width: 220 }}><label>View staff</label>
            <select value={sel} onChange={(e) => setSel(e.target.value)}>
              <option value="">Myself</option>{staff.map((s) => <option key={s.id} value={s.id}>{s.username}</option>)}
            </select></div>)}
      </div>
      <div className="grid">
        <Kpi t="Assigned Target" v={inr(d.target)} />
        <Kpi t="Achieved (Won, ex-GST)" v={`${inr(d.achieved)} (${d.achieved_percent}%)`} />
        <Kpi t="Remaining to Target" v={inr(d.remaining)} />
        <Kpi t="PIP / Incentive" v={d.pip == null ? 'Logic pending' : inr(d.pip)} />
        <Kpi t="Remaining for PIP" v={d.pip_remaining == null ? 'Logic pending' : inr(d.pip_remaining)} />
      </div>

      <div className="card"><h3>Live Funnel (latest revisions only, ex-GST)</h3>
        <table><thead><tr><th>Stage</th><th>Quotations</th><th>Value</th></tr></thead>
          <tbody>{fun.stages.map((s) => <tr key={s.status}><td>{s.status}</td><td>{s.count}</td><td>{inr(s.value)}</td></tr>)}</tbody></table>
        <p className="hot">🔥 Hot funnel: {fun.hot.count} quotations · {inr(fun.hot.value)}</p>
      </div>

      <div className="card"><h3>Per-Staff Funnel</h3>
        <table><thead><tr><th>Staff</th><th>Open #</th><th>Open Value</th><th>Hot #</th><th>Hot Value</th><th>Won Value</th></tr></thead>
          <tbody>{fun.by_staff.map((s) => (
            <tr key={s.staff}><td>{s.staff}</td><td>{s.open_count || 0}</td><td>{inr(s.open_value)}</td>
              <td>{s.hot_count || 0}</td><td>{inr(s.hot_value)}</td><td>{inr(s.won_value)}</td></tr>))}</tbody></table>
      </div>

      <div className="card"><h3>Funnel vs Closure (this FY, by month)</h3>
        <table><thead><tr><th>Month</th><th>Quoted</th><th>Closed (Won)</th></tr></thead>
          <tbody>{fun.monthly.map((m) => <tr key={m.month}><td>{m.month}</td><td>{inr(m.quoted)}</td><td>{inr(m.won)}</td></tr>)}</tbody></table>
      </div>
    </>
  );
}
