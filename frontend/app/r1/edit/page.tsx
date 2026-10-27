'use client';

import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

export default function R1EditPage() {
  const [draft, setDraft] = useState('');
  const [message, setMessage] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetch(`${API}/r1/career-profile`, { credentials: 'include' })
      .then(async response => {
        if (response.status === 401) { window.location.href = '/'; return null; }
        if (!response.ok) throw new Error('Could not load profile');
        return response.json();
      })
      .then(value => {
        if (!value) return;
        setDraft(JSON.stringify({ profile: value.profile ?? {}, experiences: value.experiences, education: value.education, projects: value.projects, certifications: value.certifications, skills: value.skills }, null, 2));
      })
      .catch(error => setMessage(error.message));
  }, []);

  async function save() {
    setSaving(true); setMessage('');
    try {
      const payload = JSON.parse(draft);
      const response = await fetch(`${API}/r1/career-profile`, { method: 'PUT', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || 'Could not save profile');
      setMessage('Corrections saved. Return to Career Profile and confirm when ready.');
    } catch (error: any) {
      setMessage(error instanceof SyntaxError ? 'Invalid JSON. Fix the JSON before saving.' : error.message);
    } finally { setSaving(false); }
  }

  return <main style={{ minHeight: '100vh', padding: 40, background: '#f7f5ef', fontFamily: 'Arial, sans-serif', color: '#17241f' }}>
    <section style={{ maxWidth: 1000, margin: '0 auto', background: 'white', padding: 28, borderRadius: 16 }}>
      <a href="/r1" style={{ color: 'inherit' }}>← Career Profile</a>
      <h1>Edit Career Profile</h1>
      <p>Correct AI-extracted values here. Saving does not confirm the profile; confirmation is the explicit user-authority step.</p>
      <textarea value={draft} onChange={e => setDraft(e.target.value)} style={{ width: '100%', minHeight: 650, boxSizing: 'border-box', padding: 16, fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', fontSize: 13, borderRadius: 10, border: '1px solid #ccc' }} spellCheck={false} />
      <div style={{ marginTop: 12, display: 'flex', gap: 10 }}><button onClick={save} disabled={saving} style={{ padding: '11px 16px' }}>{saving ? 'Saving…' : 'Save corrections'}</button><a href="/r1" style={{ padding: '11px 16px' }}>Cancel</a></div>
      {message && <p>{message}</p>}
    </section>
  </main>;
}
