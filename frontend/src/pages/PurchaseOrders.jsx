// Purchase orders to distributors. Only products the distributor supplies can be picked (cost price auto-filled).
import React, { useEffect, useState } from 'react';
import api, { inr, openPdf, sendDoc } from '../api';

const STATUS = ['DRAFT', 'SENT', 'CONFIRMED', 'RECEIVED', 'CANCELLED'];
const blankItem = { product: '', description: '', hsn_sac: '', qty: 1, rate: 0, gst_percent: 18 };

export default function PurchaseOrders() {
  const [rows, setRows] = useState([]);
  const [dists, setDists] = useState([]);
  const [dprods, setDprods] = useState([]);
  const [form, setForm] = useState(null);
  const [err, setErr] = useState('');

  const load = () => api.get('purchase-orders/').then((r) => setRows(r.data));
  useEffect(() => { load(); api.get('distributors/').then((r) => setDists(r.data)); }, []);
  const loadProducts = (d) => (d ? api.get('distributor-products/', { params: { distributor: d } }).then((r) => setDprods(r.data)) : setDprods([]));

  const chooseDist = (d) => { setForm({ ...form, distributor: d, items: [{ ...blankItem }] }); loadProducts(d); };
  const edit = (po) => { loadProducts(po.distributor); setForm({ id: po.id, distributor: po.distributor, expected_delivery: po.expected_delivery || '', reference: po.reference, notes: po.notes, terms: po.terms, items: po.items.map(({ taxable, tax, id, ...i }) => i) }); };
  const setItem = (idx, patch) => setForm({ ...form, items: form.items.map((it, i) => (i === idx ? { ...it, ...patch } : it)) });
  const pick = (idx, pid) => {
    const d = dprods.find((x) => String(x.product) === pid);
    setItem(idx, d ? { product: d.product, description: d.product_name, hsn_sac: d.product_hsn, rate: d.cost_price, gst_percent: d.product_gst } : { product: '' });
  };
  const sub = form ? form.items.reduce((a, i) => a + i.qty * i.rate, 0) : 0;
  const tax = form ? form.items.reduce((a, i) => a + (i.qty * i.rate * i.gst_percent) / 100, 0) : 0;

  const save = async () => {
    setErr('');
    const body = { ...form, expected_delivery: form.expected_delivery || null, items: form.items.map((i) => ({ ...i, product: i.product || null })) };
    try { form.id ? await api.patch(`purchase-orders/${form.id}/`, body) : await api.post('purchase-orders/', body); setForm(null); load(); }
    catch (e) { setErr(JSON.stringify(e.response?.data ?? 'Error', null, 1)); }
  };

  return (
    <div className="card">
      <div className="row" style={{ justifyContent: 'space-between' }}><h2 style={{ margin: 0 }}>Purchase Orders</h2>
        <button onClick={() => { setDprods([]); setForm({ distributor: '', expected_delivery: '', reference: '', notes: '', terms: '', items: [] }); }}>+ New PO</button></div>
      {form && (
        <div className="card" style={{ background: '#f8fafc', marginTop: 12 }}>
          <div className="grid">
            <div><label>Distributor *</label><select value={form.distributor} disabled={!!form.id} onChange={(e) => chooseDist(e.target.value)}>
              <option value="">-- select --</option>{dists.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}</select></div>
            <div><label>Expected delivery</label><input type="date" value={form.expected_delivery} onChange={(e) => setForm({ ...form, expected_delivery: e.target.value })} /></div>
            <div><label>Reference (customer / quotation)</label><input value={form.reference} onChange={(e) => setForm({ ...form, reference: e.target.value })} /></div>
          </div>
          {form.distributor && <>
            <table style={{ marginTop: 10 }}><thead><tr><th>Product</th><th>Description</th><th>Qty</th><th>Cost rate</th><th>GST %</th><th>Amount</th><th /></tr></thead>
              <tbody>{form.items.map((it, idx) => (
                <tr key={idx}>
                  <td style={{ width: 170 }}><select value={it.product || ''} onChange={(e) => pick(idx, e.target.value)}><option value="">-- pick --</option>{dprods.map((d) => <option key={d.id} value={d.product}>{d.product_code}</option>)}</select></td>
                  <td><input value={it.description} onChange={(e) => setItem(idx, { description: e.target.value })} /></td>
                  {['qty', 'rate', 'gst_percent'].map((k) => <td key={k} style={{ width: 100 }}><input type="number" step="any" value={it[k]} onChange={(e) => setItem(idx, { [k]: Number(e.target.value) })} /></td>)}
                  <td>{inr(it.qty * it.rate)}</td>
                  <td><button className="sm del" onClick={() => setForm({ ...form, items: form.items.filter((_, i) => i !== idx) })}>✕</button></td></tr>))}</tbody></table>
            <button className="sec sm" onClick={() => setForm({ ...form, items: [...form.items, { ...blankItem }] })}>+ Add line</button>
            <p><b>Subtotal {inr(sub)} · GST {inr(tax)} · Total {inr(sub + tax)}</b></p></>}
          <div className="grid"><div><label>Terms (blank = default)</label><textarea rows={2} value={form.terms} onChange={(e) => setForm({ ...form, terms: e.target.value })} /></div>
            <div><label>Notes</label><textarea rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></div></div>
          <p className="err">{err}</p><button onClick={save}>{form.id ? 'Save changes' : 'Create PO'}</button> <button className="sec" onClick={() => setForm(null)}>Cancel</button>
        </div>)}
      <table style={{ marginTop: 12 }}><thead><tr><th>PO No</th><th>Distributor</th><th>Date</th><th>Total</th><th>Status</th><th /></tr></thead>
        <tbody>{rows.map((po) => (
          <tr key={po.id}><td>{po.number}</td><td>{po.distributor_name}</td><td>{po.order_date}</td><td>{inr(po.grand_total)}</td>
            <td><select value={po.status} onChange={(e) => api.patch(`purchase-orders/${po.id}/`, { status: e.target.value }).then(load)}>{STATUS.map((s) => <option key={s}>{s}</option>)}</select></td>
            <td><button className="sm" onClick={() => edit(po)}>Edit</button> <button className="sm sec" onClick={() => openPdf(`purchase-orders/${po.id}/`)}>PDF</button>{' '}
              <button className="sm sec" onClick={() => sendDoc(`purchase-orders/${po.id}/`)}>Send</button></td></tr>))}</tbody></table>
    </div>
  );
}
