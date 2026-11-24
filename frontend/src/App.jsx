// App shell: login guard, top navigation, and routes.
import React, { useEffect, useState } from 'react';
import { Link, NavLink, Navigate, Route, Routes } from 'react-router-dom';
import api from './api';
import Login from './pages/Login.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Quotations from './pages/Quotations.jsx';
import CrudPage from './pages/CrudPage.jsx';
import Billing from './pages/Billing.jsx';
import PurchaseOrders from './pages/PurchaseOrders.jsx';

const STATES = ['Maharashtra', 'Gujarat', 'Karnataka', 'Delhi', 'Tamil Nadu', 'Telangana', 'West Bengal', 'Rajasthan', 'Uttar Pradesh', 'Madhya Pradesh', 'Kerala', 'Punjab', 'Haryana', 'Goa', 'Other'];

const customerCfg = {
  title: 'Customers', endpoint: 'customers',
  columns: ['name', 'contact_person', 'phone', 'email', 'city', 'state'],
  fields: [
    { name: 'name', label: 'Company Name', required: true }, { name: 'contact_person', label: 'Contact Person' },
    { name: 'phone', label: 'Phone' }, { name: 'email', label: 'Email', type: 'email' },
    { name: 'gstin', label: 'GSTIN' }, { name: 'city', label: 'City' },
    { name: 'state', label: 'State', options: STATES }, { name: 'address', label: 'Address', type: 'textarea' }],
};
const productCfg = {
  title: 'Products', endpoint: 'products', adminOnly: true,
  columns: ['code', 'name', 'hsn_sac', 'unit_price', 'gst_percent', 'is_active'],
  fields: [
    { name: 'code', label: 'Product Code', required: true }, { name: 'name', label: 'Name', required: true },
    { name: 'hsn_sac', label: 'HSN/SAC' }, { name: 'unit_price', label: 'Unit Price (ex-GST)', type: 'number' },
    { name: 'gst_percent', label: 'GST %', type: 'number', default: 18 },
    { name: 'is_active', label: 'Active', type: 'checkbox', default: true },
    { name: 'description', label: 'Description', type: 'textarea' }],
};
const staffCfg = {
  title: 'Sales Staff', endpoint: 'users', adminOnly: true,
  columns: ['username', 'first_name', 'last_name', 'email', 'role', 'is_active'],
  fields: [
    { name: 'username', label: 'Username', required: true }, { name: 'first_name', label: 'First Name' },
    { name: 'last_name', label: 'Last Name' }, { name: 'email', label: 'Email', type: 'email' },
    { name: 'role', label: 'Role', options: ['SALES', 'ADMIN'], default: 'SALES' },
    { name: 'password', label: 'Password (leave blank to keep)', type: 'password' },
    { name: 'is_active', label: 'Active', type: 'checkbox', default: true }],
};
const targetCfg = {
  title: 'Targets (ex-GST, per FY)', endpoint: 'targets', adminOnly: true,
  columns: ['staff_name', 'fy', 'amount'],
  fields: [
    { name: 'staff', label: 'Staff', lookup: 'users', lookupLabel: 'username', required: true },
    { name: 'fy', label: 'Financial Year (e.g. 2026-27)', required: true },
    { name: 'amount', label: 'Target Amount', type: 'number', required: true }],
};

const distributorCfg = {
  title: 'Distributors', endpoint: 'distributors', adminOnly: true,
  columns: ['name', 'contact_person', 'phone', 'email', 'state'],
  fields: [
    { name: 'name', label: 'Distributor Name', required: true }, { name: 'contact_person', label: 'Contact Person' },
    { name: 'phone', label: 'Phone' }, { name: 'email', label: 'Email', type: 'email' },
    { name: 'gstin', label: 'GSTIN' }, { name: 'state', label: 'State', options: STATES },
    { name: 'address', label: 'Address', type: 'textarea' }],
};
const distProductCfg = {
  title: 'Distributor Products (what each distributor supplies + our cost)', endpoint: 'distributor-products', adminOnly: true,
  columns: ['distributor_name', 'product_code', 'product_name', 'cost_price'],
  fields: [
    { name: 'distributor', label: 'Distributor', lookup: 'distributors', lookupLabel: 'name', required: true },
    { name: 'product', label: 'Product', lookup: 'products', lookupLabel: 'code', required: true },
    { name: 'cost_price', label: 'Cost Price (ex-GST)', type: 'number' }],
};

export default function App() {
  const [me, setMe] = useState(null);
  const token = localStorage.getItem('token');
  useEffect(() => { if (token) api.get('me/').then((r) => setMe(r.data)); }, [token]);
  if (!token) return <Routes><Route path="*" element={<Login />} /></Routes>;
  if (!me) return <p style={{ padding: 20 }}>Loading…</p>;
  const admin = me.role === 'ADMIN';
  const logout = () => { localStorage.clear(); window.location.href = '/login'; };
  return (
    <>
      <nav>
        <Link to="/" style={{ display: 'flex', alignItems: 'center', marginRight: 14, textDecoration: 'none' }}>
          <img
            src="/aura-logo.png"
            alt="Aura"
            style={{ height: 34, width: 'auto', marginRight: 8, display: 'block' }}
          />
          <b>Aura ERP</b>
        </Link>
        <NavLink to="/">Dashboard</NavLink><NavLink to="/quotations">Quotations</NavLink>
        <NavLink to="/customers">Customers</NavLink><NavLink to="/products">Products</NavLink>
        <NavLink to="/billing">Billing</NavLink>
        {admin && <><NavLink to="/purchase-orders">Purchase Orders</NavLink><NavLink to="/distributors">Distributors</NavLink>
          <NavLink to="/distributor-products">Dist. Products</NavLink><NavLink to="/staff">Staff</NavLink><NavLink to="/targets">Targets</NavLink></>}
        <span className="sp" /><span style={{ fontSize: 13 }}>{me.name}</span>
        <button className="sec sm" style={{ marginLeft: 10 }} onClick={logout}>Logout</button>
      </nav>
      <main>
        <Routes>
          <Route path="/" element={<Dashboard me={me} />} />
          <Route path="/quotations" element={<Quotations me={me} />} />
          <Route path="/customers" element={<CrudPage cfg={customerCfg} me={me} />} />
          <Route path="/products" element={<CrudPage cfg={productCfg} me={me} />} />
          {admin && <Route path="/staff" element={<CrudPage cfg={staffCfg} me={me} />} />}
          {admin && <Route path="/targets" element={<CrudPage cfg={targetCfg} me={me} />} />}
          <Route path="/billing" element={<Billing />} />
          {admin && <Route path="/purchase-orders" element={<PurchaseOrders />} />}
          {admin && <Route path="/distributors" element={<CrudPage cfg={distributorCfg} me={me} />} />}
          {admin && <Route path="/distributor-products" element={<CrudPage cfg={distProductCfg} me={me} />} />}
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
    </>
  );
}