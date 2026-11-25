// Generic master screen (list + add + edit + delete) driven by a config object.
import React, { useEffect, useState } from 'react';
import api from '../api';

export default function CrudPage({ cfg, me }) {
  const canEdit = !cfg.adminOnly || me.role === 'ADMIN';
  const blank = Object.fromEntries(cfg.fields.map((f) => [f.name, f.default ?? (f.type === 'checkbox' ? false : '')]));
  const [rows, setRows] = useState([]);
  const [lookups, setLookups] = useState({});
  const [form, setForm] = useState(null);
  const [err, setErr] = useState('');

  const load = () => api.get(cfg.endpoint + '/').then((r) => setRows(r.data));
  useEffect(() => {
    load();
    cfg.fields.filter((f) => f.lookup).forEach((f) =>
      api.get(f.lookup + '/').then((r) => setLookups((l) => ({ ...l, [f.name]: r.data }))));
  }, [cfg.endpoint]);

  const save = async () => {
    setErr('');
    const body = { ...form };
    if (form.id && !body.password) delete body.password; // never blank-out a password
    try {
      if (form.id) await api.patch(`${cfg.endpoint}/${form.id}/`, body);
      else await api.post(cfg.endpoint + '/', body);
      setForm(null); load();
    } catch (e) { setErr(JSON.stringify(e.response?.data ?? 'Error', null, 1)); }
  };
  const del = async (r) => {
    if (!window.confirm('Delete this record?')) return;
    try { await api.delete(`${cfg.endpoint}/${r.id}/`); load(); }
    catch { alert('Cannot delete: record is in use elsewhere. Mark it inactive instead.'); }
  };
  const show = (v) => (v === true ? 'Yes' : v === false ? 'No' : v);

  return (
    <div className="card">
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h2 style={{ margin: 0 }}>{cfg.title}</h2>
        {canEdit && <button onClick={() => setForm({ ...blank })}>+ Add</button>}
      </div>
      {form && (
        <div className="card" style={{ background: '#f8fafc', marginTop: 12 }}>
          <div className="grid">
            {cfg.fields.map((f) => (
              <div key={f.name}>
                <label>{f.label}{f.required && ' *'}</label>
                {f.type === 'textarea' ? <textarea rows={2} value={form[f.name] ?? ''} onChange={(e) => setForm({ ...form, [f.name]: e.target.value })} />
                  : f.type === 'checkbox' ? <input type="checkbox" style={{ width: 'auto' }} checked={!!form[f.name]} onChange={(e) => setForm({ ...form, [f.name]: e.target.checked })} />
                  : (f.options || f.lookup) ? (
                    <select value={form[f.name] ?? ''} onChange={(e) => setForm({ ...form, [f.name]: e.target.value })}>
                      <option value="">-- select --</option>
                      {f.options ? f.options.map((o) => <option key={o}>{o}</option>)
                        : (lookups[f.name] || []).map((o) => <option key={o.id} value={o.id}>{o[f.lookupLabel]}</option>)}
                    </select>
                  ) : <input type={f.type || 'text'} step="any" value={form[f.name] ?? ''} onChange={(e) => setForm({ ...form, [f.name]: e.target.value })} />}
              </div>
            ))}
          </div>
          <p className="err">{err}</p>
          <button onClick={save}>Save</button> <button className="sec" onClick={() => setForm(null)}>Cancel</button>
        </div>
      )}
      <table style={{ marginTop: 12 }}>
        <thead><tr>{cfg.columns.map((c) => <th key={c}>{c.replace(/_/g, ' ').replace(/\b\w/g, (m) => m.toUpperCase())}</th>)}<th /></tr></thead>
                  
        <tbody>{rows.map((r) => (
          <tr key={r.id}>
            {cfg.columns.map((c) => <td key={c}>{String(show(r[c]) ?? '')}</td>)}
            <td>{canEdit && <><button className="sm" onClick={() => setForm({ ...r })}>Edit</button>{' '}
              <button className="sm del" onClick={() => del(r)}>Delete</button></>}</td>
          </tr>))}</tbody>
      </table>
    </div>
  );
}
