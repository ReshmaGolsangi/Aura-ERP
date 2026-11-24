// Single axios instance: attaches the login token and redirects to /login on expiry.
import axios from 'axios';
const api = axios.create({ baseURL: '/api' });
api.interceptors.request.use((c) => {
  const t = localStorage.getItem('token');
  if (t) c.headers.Authorization = 'Bearer ' + t;
  return c;
});
api.interceptors.response.use((r) => r, (e) => {
  if (e.response?.status === 401 && !e.config.url.includes('auth/token')) {
    localStorage.clear(); window.location.href = '/login';
  }
  return Promise.reject(e);
});
export const inr = (n) => '₹ ' + Number(n || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 });
export default api;

// Opens a PDF in a new tab (needs the login token, so we fetch it as a blob first).
export const openPdf = async (path) => {
  const r = await api.get(path + 'pdf/', { responseType: 'blob' });
  window.open(URL.createObjectURL(r.data), '_blank');
};
// Emails + WhatsApps a document to the customer/distributor on record.
export const sendDoc = async (path) => {
  try {
    const r = await api.post(path + 'send/', {});
    alert(r.data.message);
    if (!r.data.whatsapp_sent && r.data.whatsapp_link && window.confirm('Open WhatsApp chat to send manually?'))
      window.open(r.data.whatsapp_link, '_blank');
  } catch (e) { alert(JSON.stringify(e.response?.data ?? 'Failed')); }
};
