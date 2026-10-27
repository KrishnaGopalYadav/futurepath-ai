'use client';

import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

type Evidence = { id: string; filename: string };
type Item = Record<string, any>;
type R1 = { confirmed: boolean; profile: Item | null; experiences: Item[]; education: Item[]; projects: Item[]; certifications: Item[]; skills: Item[]; evidence: Record<string, Evidence> };

function EvidenceBadge({ id, evidence }: { id?: string | null; evidence: Record<string, Evidence> }) {
  if (!id || !evidence[id]) return <span style={{ fontSize: 12, opacity: .6 }}>No source linked</span>;
  return <span title={`Source resume: ${evidence[id].filename}`} style={{ fontSize: 12, padding: '3px 7px', borderRadius: 12, border: '1px solid #cfcac0' }}>Source: {evidence[id].filename}</span>;
}

export default function R1Page() {
  const [data, setData] = useState<R1 | null>(null);
  const [loading, setLoading] = useState(true);
  const [confirming, setConfirming] = useState(false);
  const [message, setMessage] = useState('');

  async function load() {
    const response = await fetch(`${API}/r1/career-profile`, { credentials: 'include' });
    if (response.status === 401) { window.location.href = '/'; return; }
    if (!response.ok) throw new Error('Could not load R1 profile');
    setData(await response.json());
  }

  useEffect(() => { load().catch(e => setMessage(e.message)).finally(() => setLoading(false)); }, []);

  async function confirm() {
    setConfirming(true); setMessage('');
    const response = await fetch(`${API}/r1/career-profile/confirm`, { method: 'POST', credentials: 'include' });
    if (!response.ok) { setMessage('Could not confirm the profile.'); setConfirming(false); return; }
    await load(); setMessage('Career profile confirmed. Future resume processing will not overwrite confirmed data.'); setConfirming(false);
  }

  if (loading) return <main style={{ padding: 48 }}>Loading R1 career profile…</main>;
  if (!data) return <main style={{ padding: 48 }}>Unable to load profile.</main>;
  const p = data.profile ?? {};

  return <main style={{ minHeight: '100vh', padding: '42px 24px', background: '#f7f5ef', color: '#17241f', fontFamily: 'Arial, sans-serif' }}>
    <section style={{ maxWidth: 1050, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 28 }}>
        <div><div style={{ letterSpacing: 2, fontSize: 12 }}>FUTUREPATH AI · R1</div><h1 style={{ margin: '8px 0' }}>Career Profile</h1><p style={{ margin: 0 }}>AI-extracted facts are evidence; your confirmed corrections are authoritative.</p></div>
        <a href="/welcome" style={{ color: 'inherit' }}>Back to dashboard</a>
      </div>

      <section style={card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 20, alignItems: 'center' }}>
          <div><h2 style={{ margin: 0 }}>{p.headline || 'Career profile'}</h2><p>{p.professional_summary || 'No professional summary has been extracted yet.'}</p></div>
          <div style={{ textAlign: 'right' }}>{data.confirmed ? <strong>✓ Confirmed by you</strong> : <button onClick={confirm} disabled={confirming} style={button}>{confirming ? 'Confirming…' : 'Confirm career profile'}</button>}</div>
        </div>
        {message && <p style={{ marginBottom: 0 }}>{message}</p>}
      </section>

      <section style={card}><h2>Experience</h2>{data.experiences.length ? data.experiences.map((x, i) => <article key={x.id ?? i} style={item}><h3 style={{ marginBottom: 5 }}>{x.job_title} · {x.company_name}</h3><p>{x.start_date || '?'} – {x.is_current ? 'Present' : (x.end_date || '?')}</p><p>{x.description}</p><EvidenceBadge id={x.source_resume_id} evidence={data.evidence}/></article>) : <p>No experience records extracted.</p>}</section>

      <section style={card}><h2>Education</h2>{data.education.length ? data.education.map((x, i) => <article key={x.id ?? i} style={item}><h3>{x.qualification || 'Education'}</h3><p>{x.institution}</p><p>{x.start_date || '?'} – {x.end_date || '?'}</p><EvidenceBadge id={x.source_resume_id} evidence={data.evidence}/></article>) : <p>No education records extracted.</p>}</section>

      <section style={card}><h2>Skills <span style={{ fontSize: 14, fontWeight: 'normal' }}>({data.skills.length})</span></h2><div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>{data.skills.map((x, i) => <span key={x.id ?? i} title={x.evidence_notes || undefined} style={pill}>{x.name}{x.category ? ` · ${x.category}` : ''}</span>)}</div></section>

      <section style={card}><h2>Projects</h2>{data.projects.length ? data.projects.map((x, i) => <article key={x.id ?? i} style={item}><h3>{x.name}</h3><p>{x.description}</p><EvidenceBadge id={x.source_resume_id} evidence={data.evidence}/></article>) : <p>No projects extracted.</p>}</section>

      <section style={card}><h2>Certifications</h2>{data.certifications.length ? data.certifications.map((x, i) => <article key={x.id ?? i} style={item}><h3>{x.name}</h3><p>{x.issuing_organization || ''}</p><EvidenceBadge id={x.source_resume_id} evidence={data.evidence}/></article>) : <p>No certifications extracted.</p>}</section>
    </section>
  </main>;
}

const card: React.CSSProperties = { background: 'white', borderRadius: 16, padding: 28, boxShadow: '0 4px 24px rgba(0,0,0,.06)', marginBottom: 20 };
const item: React.CSSProperties = { borderTop: '1px solid #e5e1d8', paddingTop: 16, marginTop: 16 };
const button: React.CSSProperties = { padding: '11px 16px', cursor: 'pointer' };
const pill: React.CSSProperties = { padding: '8px 10px', border: '1px solid #d7d2c7', borderRadius: 20, fontSize: 13 };
