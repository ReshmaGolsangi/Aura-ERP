// Quotation list + create/revise form + revision history.
import React, { useEffect, useState } from 'react';
import api, { inr, openPdf, sendDoc } from '../api';

const STATUS = ['DRAFT', 'SENT', 'NEGOTIATION', 'WON', 'LOST'];
const emptyItem = { product: '', description: '', hsn_sac: '', qty: 1, rate: 0, discount_percent: 0, gst_percent: 18 };
const calc = (i) => { const t = i.qty * i.rate * (1 - i.discount_percent / 100); return { t, tax: (t * i.gst_percent) / 100 }; };

export default function Quotations({ me }) {
  const [rows, setRows] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [products, setProducts] = useState([]);
  const [form, setForm] = useState(null);   // null = hidden; {id?} = editing (revise)
  const [hist, setHist] = useState(null);
  const [err, setErr] = useState('');

  const load = () => api.get('quotations/').then((r) => setRows(r.data));
  useEffect(() => { load(); api.get('customers/').then((r) => setCustomers(r.data)); api.get('products/').then((r) => setProducts(r.data.filter((p) => p.is_active))); }, []);

  const newForm = () => setForm({ customer: '', subject: '', notes: '', terms: '', expected_close_date: '', items: [{ ...emptyItem }] });
  const edit = (q) => setForm({ id: q.id, customer: q.customer, expected_close_date: q.expected_close_date || '',
    subject: q.latest.subject, notes: q.latest.notes, terms: q.latest.terms, items: q.latest.items.map(({ taxable, tax, id, ...i }) => i) });

  const setItem = (idx, patch) => setForm({ ...form, items: form.items.map((it, i) => (i === idx ? { ...it, ...patch } : it)) });
  const pick = (idx, pid) => {
    const p = products.find((x) => String(x.id) === pid);
    setItem(idx, p ? { product: p.id, description: p.name, hsn_sac: p.hsn_sac, rate: p.unit_price, gst_percent: p.gst_percent } : { product: '' });
  };
  const totals = form ? form.items.reduce((a, i) => { const c = calc(i); return { sub: a.sub + c.t, tax: a.tax + c.tax }; }, { sub: 0, tax: 0 }) : null;

  const save = async () => {
    setErr('');
    const items = form.items.map((i) => ({ ...i, product: i.product || null }));
    const body = { ...form, items, expected_close_date: form.expected_close_date || null };
    try {
      if (form.id) {
        await api.post(`quotations/${form.id}/revise/`, body);
        await api.patch(`quotations/${form.id}/`, { customer: form.customer, expected_close_date: body.expected_close_date });
      } else await api.post('quotations/', body);
      setForm(null); load();
    } catch (e) { setErr(JSON.stringify(e.response?.data ?? 'Error', null, 1)); }
  };
  const patch = (q, d) => api.patch(`quotations/${q.id}/`, d).then(load);
  const makePI = async (q) => {
    const po = window.prompt('Customer PO number?'); if (!po) return;
    const dt = window.prompt('PO date (YYYY-MM-DD)', new Date().toISOString().slice(0, 10));
    try { const r = await api.post('proformas/', { quotation: q.id, po_number: po, po_date: dt || null }); alert('Proforma ' + r.data.number + ' created. See Billing.'); load(); }
    catch (e) { alert(e.response?.data?.detail || JSON.stringify(e.response?.data)); }
  };
  const showHist = (q) => api.get(`quotations/${q.id}/history/`).then((r) => setHist({ q, revs: r.data }));

  return (
    <>
      <div className="card">
        <div className="row" style={{ justifyContent: 'space-between' }}><h2 style={{ margin: 0 }}>Quotations</h2><button onClick={newForm}>+ New Quotation</button></div>

        {form && (
          <div className="card" style={{ background: '#f8fafc', marginTop: 12 }}>
            <h3>{form.id ? 'Revise quotation (saves as a new revision)' : 'New quotation'}</h3>
            <div className="grid">
              <div><label>Customer *</label><select value={form.customer} onChange={(e) => setForm({ ...form, customer: e.target.value })}>
                <option value="">-- select --</option>{customers.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></div>
              <div><label>Subject</label><input value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} /></div>
              <div><label>Expected close date</label><input type="date" value={form.expected_close_date} onChange={(e) => setForm({ ...form, expected_close_date: e.target.value })} /></div>
            </div>
            <table style={{ marginTop: 10 }}>
              <thead><tr><th>Product</th><th>Description</th><th>Qty</th><th>Rate</th><th>Disc %</th><th>GST %</th><th>Amount</th><th /></tr></thead>
              <tbody>{form.items.map((it, idx) => (
                <tr key={idx}>
                  <td style={{ width: 160 }}><select value={it.product || ''} onChange={(e) => pick(idx, e.target.value)}><option value="">custom</option>{products.map((p) => <option key={p.id} value={p.id}>{p.code}</option>)}</select></td>
                  <td><input value={it.description} onChange={(e) => setItem(idx, { description: e.target.value })} /></td>
                  {['qty', 'rate', 'discount_percent', 'gst_percent'].map((k) => (
                    <td key={k} style={{ width: 90 }}><input type="number" step="any" value={it[k]} onChange={(e) => setItem(idx, { [k]: Number(e.target.value) })} /></td>))}
                  <td>{inr(calc(it).t)}</td>
                  <td><button className="sm del" onClick={() => setForm({ ...form, items: form.items.filter((_, i) => i !== idx) })}>✕</button></td>
                </tr>))}</tbody>
            </table>
            <button className="sec sm" onClick={() => setForm({ ...form, items: [...form.items, { ...emptyItem }] })}>+ Add line</button>
            <p><b>Subtotal {inr(totals.sub)} · GST {inr(totals.tax)} · Total {inr(totals.sub + totals.tax)}</b></p>
            <div className="grid">
              <div><label>Terms (blank = default)</label><textarea rows={2} value={form.terms} onChange={(e) => setForm({ ...form, terms: e.target.value })} /></div>
              <div><label>Notes</label><textarea rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></div>
            </div>
            <p className="err">{err}</p>
            <button onClick={save}>{form.id ? 'Save as new revision' : 'Create quotation'}</button> <button className="sec" onClick={() => setForm(null)}>Cancel</button>
          </div>)}

        <table style={{ marginTop: 12 }}>
          <thead><tr><th>Number</th><th>Customer</th><th>Owner</th><th>Rev</th><th>Value (ex-GST)</th><th>Total</th><th>Status</th><th>Hot</th><th /></tr></thead>
          <tbody>{rows.map((q) => (
            <tr key={q.id}>
              <td>{q.number}</td><td>{q.customer_name}</td><td>{q.owner_name}</td><td>R{q.latest?.rev_no}</td>
              <td>{inr(q.latest?.subtotal)}</td><td>{inr(q.latest?.grand_total)}</td>
              <td><select value={q.status} onChange={(e) => patch(q, { status: e.target.value })}>{STATUS.map((s) => <option key={s}>{s}</option>)}</select></td>
              <td><input type="checkbox" style={{ width: 'auto' }} checked={q.is_hot} onChange={(e) => patch(q, { is_hot: e.target.checked })} /></td>
              <td><button className="sm" onClick={() => edit(q)}>Revise</button> <button className="sm sec" onClick={() => showHist(q)}>History</button>{' '}
                <button className="sm sec" onClick={() => openPdf(`quotations/${q.id}/`)}>PDF</button>{' '}
                <button className="sm sec" onClick={() => sendDoc(`quotations/${q.id}/`)}>Send</button>
                {q.status === 'WON' && <> <button className="sm" onClick={() => makePI(q)}>Proforma</button></>}</td>
            </tr>))}</tbody>
        </table>
      </div>

      {hist && (
        <div className="card"><h3>History – {hist.q.number}</h3>
          <table><thead><tr><th>Rev</th><th>Date</th><th>Subtotal</th><th>GST</th><th>Total</th><th>Lines</th></tr></thead>
            <tbody>{hist.revs.map((r) => <tr key={r.id}><td>R{r.rev_no}</td><td>{new Date(r.created_at).toLocaleString('en-IN')}</td>
              <td>{inr(r.subtotal)}</td><td>{inr(r.tax_total)}</td><td>{inr(r.grand_total)}</td><td>{r.items.length}</td></tr>)}</tbody></table>
          <button className="sec sm" onClick={() => setHist(null)}>Close</button></div>)}
    </>
  );
}
