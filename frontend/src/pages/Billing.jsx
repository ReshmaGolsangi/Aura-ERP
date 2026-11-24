// Proforma invoices + payment receipts. Receipts can be emailed / WhatsApped in one click.
import React, { useEffect, useState } from 'react';
import api, { inr, openPdf, sendDoc } from '../api';

export default function Billing() {
  const [pis, setPis] = useState([]);
  const [rcs, setRcs] = useState([]);
  const [pay, setPay] = useState(null); // payment form for one proforma
  const [err, setErr] = useState('');
  const load = () => { api.get('proformas/').then((r) => setPis(r.data)); api.get('receipts/').then((r) => setRcs(r.data)); };
  useEffect(load, []);

  const save = async () => {
    setErr('');
    try {
      const r = await api.post('receipts/', { proforma: pay.id, amount: pay.amount, mode: pay.mode, reference: pay.reference, received_on: pay.received_on });
      setPay(null); load();
      if (window.confirm(`Receipt ${r.data.number} created. Send to customer now (email + WhatsApp)?`)) sendDoc(`receipts/${r.data.id}/`);
    } catch (e) { setErr(JSON.stringify(e.response?.data ?? 'Error', null, 1)); }
  };

  return (
    <>
      <div className="card"><h2>Proforma Invoices</h2>
        <table><thead><tr><th>Number</th><th>Customer</th><th>Quotation</th><th>PO No</th><th>Total</th><th>Paid</th><th>Balance</th><th /></tr></thead>
          <tbody>{pis.map((p) => (
            <tr key={p.id}><td>{p.number}</td><td>{p.customer_name}</td><td>{p.quotation_number}</td><td>{p.po_number}</td>
              <td>{inr(p.total)}</td><td>{inr(p.paid)}</td><td>{inr(p.balance)}</td>
              <td><button className="sm sec" onClick={() => openPdf(`proformas/${p.id}/`)}>PDF</button>{' '}
                <button className="sm sec" onClick={() => sendDoc(`proformas/${p.id}/`)}>Send</button>{' '}
                {Number(p.balance) > 0 && <button className="sm" onClick={() => setPay({ id: p.id, number: p.number, amount: p.balance, mode: 'NEFT/RTGS', reference: '', received_on: new Date().toISOString().slice(0, 10) })}>Record payment</button>}</td></tr>))}</tbody></table>
        {pay && (
          <div className="card" style={{ background: '#f8fafc', marginTop: 12 }}>
            <h3>Record payment – {pay.number}</h3>
            <div className="grid">
              <div><label>Amount received</label><input type="number" step="any" value={pay.amount} onChange={(e) => setPay({ ...pay, amount: e.target.value })} /></div>
              <div><label>Mode</label><select value={pay.mode} onChange={(e) => setPay({ ...pay, mode: e.target.value })}>{['NEFT/RTGS', 'UPI', 'CHEQUE', 'CASH', 'CARD'].map((m) => <option key={m}>{m}</option>)}</select></div>
              <div><label>UTR / Cheque no.</label><input value={pay.reference} onChange={(e) => setPay({ ...pay, reference: e.target.value })} /></div>
              <div><label>Received on</label><input type="date" value={pay.received_on} onChange={(e) => setPay({ ...pay, received_on: e.target.value })} /></div>
            </div>
            <p className="err">{err}</p><button onClick={save}>Save receipt</button> <button className="sec" onClick={() => setPay(null)}>Cancel</button>
          </div>)}
      </div>

      <div className="card"><h2>Receipts</h2>
        <table><thead><tr><th>Number</th><th>Proforma</th><th>Amount</th><th>Mode</th><th>Date</th><th>Emailed</th><th>WhatsApp</th><th /></tr></thead>
          <tbody>{rcs.map((r) => (
            <tr key={r.id}><td>{r.number}</td><td>{r.proforma_number}</td><td>{inr(r.amount)}</td><td>{r.mode}</td><td>{r.received_on}</td>
              <td>{r.emailed_at ? '✔' : '–'}</td><td>{r.whatsapp_at ? '✔' : '–'}</td>
              <td><button className="sm sec" onClick={() => openPdf(`receipts/${r.id}/`)}>PDF</button>{' '}
                <button className="sm sec" onClick={() => sendDoc(`receipts/${r.id}/`)}>Send</button></td></tr>))}</tbody></table>
      </div>
    </>
  );
}
