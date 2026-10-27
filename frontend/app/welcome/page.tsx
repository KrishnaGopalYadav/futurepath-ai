'use client';

import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
type User = { id: string; username: string; email?: string | null; is_active: boolean; auth_provider: string };
type Profile = { headline?: string | null; professional_summary?: string | null; current_location?: string | null; preferred_locations?: string[] | null; preferred_work_modes?: string[] | null; target_roles?: string[] | null; years_experience?: number | null; is_open_to_opportunities: boolean };
type R1Response = { profile?: Profile | null; confirmed?: boolean; experiences?: unknown[]; education?: unknown[]; projects?: unknown[]; certifications?: unknown[]; skills?: unknown[] };
type Resume = { id: string; original_filename: string; file_size_bytes?: number | null; created_at: string };
type Job = { id: string; resume_id: string; status: string; attempt_count: number; max_attempts: number; error_message?: string | null };

async function apiJson(path: string, init?: RequestInit) {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...init, credentials: "include" });
  } catch {
    throw new Error(`Cannot reach the FuturePath API at ${API_BASE}. Make sure Docker Compose is running.`);
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(data?.detail ?? `Request failed (${response.status})`);
  return data;
}

export default function WelcomePage() {
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<Profile>({ is_open_to_opportunities: false });
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [jobs, setJobs] = useState<Record<string, Job>>({});
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");

  async function loadData() {
    setPageError("");
    try {
      const u = await apiJson("/auth/me");
      setUser(u);
      const [p, r] = await Promise.all([apiJson("/r1/career-profile"), apiJson("/resumes")]);
      const r1 = p as R1Response;
      setProfile(r1.profile ?? { is_open_to_opportunities: false });
      setResumes(r);
      const entries = await Promise.all(r.map(async (resume: Resume) => {
        try { return [resume.id, await apiJson(`/resumes/${resume.id}/processing-job`)] as const; }
        catch { return [resume.id, null] as const; }
      }));
      setJobs(Object.fromEntries(entries.filter(([, job]) => job)));
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Unable to load your career workspace.");
    }
  }

  useEffect(() => { loadData().finally(() => setLoading(false)); }, []);

  useEffect(() => {
    const active = Object.values(jobs).some(j => j.status === "queued" || j.status === "running");
    if (!active) return;
    const timer = setInterval(() => loadData().catch(() => undefined), 2500);
    return () => clearInterval(timer);
  }, [jobs]);

  async function saveProfile(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSaving(true); setSaved(false);
    try {
      await apiJson("/r1/career-profile", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ profile }) });
      setSaved(true);
      await loadData();
    } catch (error) { setPageError(error instanceof Error ? error.message : "Unable to save your profile."); }
    finally { setSaving(false); }
  }

  async function uploadResume(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]; if (!file) return;
    setUploadError(""); setUploading(true);
    try {
      const form = new FormData(); form.append("file", file);
      await apiJson("/resumes", { method: "POST", body: form });
      await loadData();
    } catch (error) { setUploadError(error instanceof Error ? error.message : "Resume upload failed."); }
    finally { setUploading(false); event.target.value = ""; }
  }

  async function retry(jobId: string) {
    try { await apiJson(`/processing-jobs/${jobId}/retry`, { method: "POST" }); await loadData(); }
    catch (error) { setPageError(error instanceof Error ? error.message : "Unable to retry processing."); }
  }

  async function logout() { try { await apiJson("/auth/logout", { method: "POST" }); } finally { window.location.href = "/"; } }

  if (loading) return <main className="workspace-shell"><div className="workspace-loading"><div className="loading-mark">✦</div><h1>Preparing your career workspace</h1><p>Loading your profile and resume intelligence…</p></div></main>;

  return <main className="workspace-shell">
    <div className="workspace-container">
      <header className="workspace-nav">
        <a className="workspace-brand" href="/" aria-label="FuturePath AI home"><span className="brand-mark"><span /></span><span>futurepath<span className="brand-ai">.ai</span></span></a>
        <div className="nav-actions">{user && <span className="user-chip">{user.email ?? user.username}</span>}<button className="ghost-button" onClick={logout}>Sign out</button></div>
      </header>

      {pageError && <section className="workspace-alert"><strong>We couldn't finish loading this workspace.</strong><span>{pageError}</span><button onClick={loadData}>Retry</button></section>}

      {user && <>
        <section className="workspace-hero">
          <div><p className="workspace-kicker">YOUR CAREER WORKSPACE</p><h1>Welcome, {user.username}.</h1><p>Turn your experience into a career profile you can review, correct and build on.</p></div>
          <div className="hero-status"><span className="status-dot" /> R1 · CAREER PROFILE</div>
        </section>

        <div className="workspace-grid">
          <section className="workspace-card upload-card">
            <div className="card-top"><div><p className="card-kicker">01 · RESUME EVIDENCE</p><h2>Build your profile</h2></div><span className="card-icon">↗</span></div>
            <p className="card-copy">Upload a PDF and FuturePath will process it in the background into structured career data.</p>
            <label className={`upload-zone${uploading ? " uploading" : ""}`}>
              <span className="upload-symbol">{uploading ? "…" : "↑"}</span><strong>{uploading ? "Uploading resume…" : "Choose a PDF resume"}</strong><small>{uploading ? "Your file is being submitted securely" : "PDF only · maximum 10 MB"}</small>
              <input type="file" accept="application/pdf,.pdf" onChange={uploadResume} disabled={uploading} />
            </label>
            {uploadError && <p className="error-message" role="alert">{uploadError}</p>}
          </section>

          <section className="workspace-card status-card">
            <div className="card-top"><div><p className="card-kicker">02 · PROCESSING</p><h2>Resume activity</h2></div><span className="card-count">{resumes.length}</span></div>
            {resumes.length === 0 ? <div className="empty-state"><span>◌</span><p>No resume uploaded yet.</p><small>Your first upload will appear here.</small></div> : <div className="resume-list">{resumes.map(resume => { const job = jobs[resume.id]; const status = job?.status ?? "queued"; return <div className="resume-row" key={resume.id}><div className="file-badge">PDF</div><div className="resume-meta"><strong>{resume.original_filename}</strong><small>{new Date(resume.created_at).toLocaleString()}</small></div><span className={`job-status ${status}`}>{status}</span>{status === "failed" && <button className="retry-button" onClick={() => retry(job.id)}>Retry</button>}</div>; })}</div>}
          </section>
        </div>

        <section className="workspace-card profile-card">
          <div className="card-top"><div><p className="card-kicker">03 · YOUR SOURCE OF TRUTH</p><h2>Career profile</h2><p className="card-copy">AI extraction is a starting point. You control what becomes part of your profile.</p></div><span className="confirmed-badge">USER CONTROLLED</span></div>
          <form onSubmit={saveProfile} className="profile-form">
            <label>Headline<input value={profile.headline ?? ""} onChange={e => setProfile({ ...profile, headline: e.target.value })} placeholder="e.g. Backend Engineer | Python & Cloud" /></label>
            <label>Professional summary<textarea value={profile.professional_summary ?? ""} onChange={e => setProfile({ ...profile, professional_summary: e.target.value })} rows={5} placeholder="Summarize your experience, strengths and direction." /></label>
            <div className="form-grid"><label>Current location<input value={profile.current_location ?? ""} onChange={e => setProfile({ ...profile, current_location: e.target.value })} placeholder="e.g. Pune, India" /></label><label>Years of experience<input type="number" min="0" max="99.9" step="0.1" value={profile.years_experience ?? ""} onChange={e => setProfile({ ...profile, years_experience: e.target.value ? Number(e.target.value) : null })} /></label></div>
            <label>Target roles<input value={(profile.target_roles ?? []).join(", ")} onChange={e => setProfile({ ...profile, target_roles: e.target.value.split(",").map(v => v.trim()).filter(Boolean) })} placeholder="e.g. Backend Engineer, Platform Engineer" /></label>
            <label>Preferred work modes<input value={(profile.preferred_work_modes ?? []).join(", ")} onChange={e => setProfile({ ...profile, preferred_work_modes: e.target.value.split(",").map(v => v.trim()).filter(Boolean) })} placeholder="e.g. Remote, Hybrid" /></label>
            <label className="checkbox-row"><input type="checkbox" checked={profile.is_open_to_opportunities} onChange={e => setProfile({ ...profile, is_open_to_opportunities: e.target.checked })} /> Open to new opportunities</label>
            <div className="save-row"><button className="save-button" type="submit" disabled={saving}>{saving ? "Saving…" : "Save career profile"}<span>→</span></button>{saved && <span className="saved-message">Saved successfully ✓</span>}</div>
          </form>
        </section>
      </>}
    </div>
  </main>;
}
