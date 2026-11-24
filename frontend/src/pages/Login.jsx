import React, { useState } from 'react';
import api from '../api';

export default function Login() {
  const [f, setF] = useState({ username: '', password: '' });
  const [err, setErr] = useState('');
  const submit = async (e) => {
    e.preventDefault();
    try {
      const r = await api.post('auth/token/', f);
      localStorage.setItem('token', r.data.access);
      window.location.href = '/';
    } catch { setErr('Invalid username or password'); }
  };
  return (
    <form onSubmit={submit} className="card" style={{ maxWidth: 340, margin: '10vh auto' }}>
      <h2>Aura ERP – Login</h2>
      <label>Username</label><input value={f.username} onChange={(e) => setF({ ...f, username: e.target.value })} />
      <label style={{ marginTop: 8 }}>Password</label>
      <input type="password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} />
      <p className="err">{err}</p><button>Login</button>
    </form>
  );
}
