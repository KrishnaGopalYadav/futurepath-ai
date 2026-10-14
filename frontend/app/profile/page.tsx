'use client';

import { FormEvent, useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Experience = { company: string; title: string; start_date: string; end_date: string; is_current: boolean; description: string };
type Education = { institution: string; degree: string; field_of_study: string; start_date: string; end_date: string };
type Skill = { name: string; proficiency: string };
type Profile = {
  id: number; full_name: string; headline: string; summary: string; location: string;
  target_role: string; target_industry: string; career_interests: string;
  experiences: Experience[]; education: Education[]; skills: Skill[];
};

const emptyExperience = (): Experience => ({ company: "", title: "", start_date: "", end_date: "", is_current: false, description: "" });
const emptyEducation = (): Education => ({ institution: "", degree: "", field_of_study: "", start_date: "", end_date: "" });
const emptySkill = (): Skill => ({ name: "", proficiency: "" });

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetch(`${API_BASE}/profile`, { credentials: "include" })
      .then(async r => {
        if (r.status === 401) { window.location.href = "/"; return null; }
        if (!r.ok) throw new Error("Unable to load profile");
        return r.json();
      })
      .then(data => setProfile(data ?? {
        id: 0, full_name: "", headline: "", summary: "", location: "", target_role: "", target_industry: "", career_interests: "",
        experiences: [], education: [], skills: []
      }))
      .catch(e => setMessage(e.message))
      .finally(() => setLoading(false));
  }, []);

  function update<K extends keyof Profile>(key: K, value: Profile[K]) { setProfile(p => p ? { ...p, [key]: value } : p); }
  function updateArray<K extends "experiences" | "education" | "skills">(key: K, index: number, value: Partial<Profile[K][number]>) {
    setProfile(p => {
      if (!p) return p;
      const copy = [...p[key]] as Array<Profile[K][number]>;
      copy[index] = { ...copy[index], ...value } as Profile[K][number];
      return { ...p, [key]: copy };
    });
  }
  function removeArray(key: "experiences" | "education" | "skills", index: number) {
    setProfile(p => p ? { ...p, [key]: p[key].filter((_, i) => i !== index) } : p);
  }

  async function save(e: FormEvent) {
    e.preventDefault();
    if (!profile) return;
    setSaving(true); setMessage("");
    const clean = {
      ...profile,
      id: undefined,
      experiences: profile.experiences.filter(x => x.company.trim() || x.title.trim()),
      education: profile.education.filter(x => x.institution.trim() || x.degree.trim()),
      skills: profile.skills.filter(x => x.name.trim()),
    };
    const response = await fetch(`${API_BASE}/profile`, {
      method: "PUT", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify(clean)
    });
    if (response.ok) { setProfile(await response.json()); setMessage("Profile saved successfully."); }
    else { const data = await response.json().catch(() => ({})); setMessage(data.detail ?? "Unable to save profile."); }
    setSaving(false);
  }

  if (loading) return <main className="profile-page"><p>Loading your career profile…</p></main>;
  if (!profile) return <main className="profile-page"><p>{message || "Unable to load profile."}</p></main>;

  return (
    <main className="profile-page">
      <div className="profile-shell">
        <header className="profile-header">
          <div><p className="eyebrow">FUTUREPATH AI</p><h1>Your Career Profile</h1><p>Tell FuturePath where you are today and where you want to go.</p></div>
          <a href="/welcome">Back</a>
        </header>
        <form onSubmit={save}>
          <section className="profile-card">
            <h2>About you</h2>
            <div className="form-grid">
              <label>Full name<input value={profile.full_name} onChange={e => update("full_name", e.target.value)} /></label>
              <label>Location<input value={profile.location} onChange={e => update("location", e.target.value)} /></label>
              <label className="wide">Professional headline<input value={profile.headline} onChange={e => update("headline", e.target.value)} placeholder="e.g. Senior Software Engineer" /></label>
              <label className="wide">Career summary<textarea rows={5} value={profile.summary} onChange={e => update("summary", e.target.value)} /></label>
            </div>
          </section>

          <section className="profile-card">
            <h2>Career direction</h2>
            <div className="form-grid">
              <label>Target role<input value={profile.target_role} onChange={e => update("target_role", e.target.value)} placeholder="e.g. Solutions Architect" /></label>
              <label>Target industry<input value={profile.target_industry} onChange={e => update("target_industry", e.target.value)} placeholder="e.g. Technology" /></label>
              <label className="wide">Career interests<textarea rows={3} value={profile.career_interests} onChange={e => update("career_interests", e.target.value)} placeholder="What areas or problems interest you?" /></label>
            </div>
          </section>

          <section className="profile-card">
            <div className="section-title"><h2>Experience</h2><button type="button" onClick={() => update("experiences", [...profile.experiences, emptyExperience()])}>+ Add experience</button></div>
            {profile.experiences.map((x,i) => <div className="repeat-card" key={i}>
              <div className="form-grid"><label>Company<input value={x.company} onChange={e => updateArray("experiences",i,{company:e.target.value})}/></label><label>Role<input value={x.title} onChange={e => updateArray("experiences",i,{title:e.target.value})}/></label><label>Start date<input type="date" value={x.start_date} onChange={e => updateArray("experiences",i,{start_date:e.target.value})}/></label><label>End date<input type="date" disabled={x.is_current} value={x.end_date} onChange={e => updateArray("experiences",i,{end_date:e.target.value})}/></label><label className="wide">Description<textarea rows={4} value={x.description} onChange={e => updateArray("experiences",i,{description:e.target.value})}/></label></div>
              <label className="check"><input type="checkbox" checked={x.is_current} onChange={e => updateArray("experiences",i,{is_current:e.target.checked,end_date:e.target.checked?"":x.end_date})}/> Currently working here</label>
              <button className="danger" type="button" onClick={() => removeArray("experiences",i)}>Remove</button>
            </div>)}
          </section>

          <section className="profile-card">
            <div className="section-title"><h2>Education</h2><button type="button" onClick={() => update("education", [...profile.education, emptyEducation()])}>+ Add education</button></div>
            {profile.education.map((x,i) => <div className="repeat-card" key={i}><div className="form-grid"><label>Institution<input value={x.institution} onChange={e=>updateArray("education",i,{institution:e.target.value})}/></label><label>Degree<input value={x.degree} onChange={e=>updateArray("education",i,{degree:e.target.value})}/></label><label>Field of study<input value={x.field_of_study} onChange={e=>updateArray("education",i,{field_of_study:e.target.value})}/></label><label>End date<input type="date" value={x.end_date} onChange={e=>updateArray("education",i,{end_date:e.target.value})}/></label></div><button className="danger" type="button" onClick={()=>removeArray("education",i)}>Remove</button></div>)}
          </section>

          <section className="profile-card">
            <div className="section-title"><h2>Skills</h2><button type="button" onClick={() => update("skills", [...profile.skills, emptySkill()])}>+ Add skill</button></div>
            {profile.skills.map((x,i) => <div className="skill-row" key={i}><input value={x.name} placeholder="Skill" onChange={e=>updateArray("skills",i,{name:e.target.value})}/><input value={x.proficiency} placeholder="Proficiency (e.g. Advanced)" onChange={e=>updateArray("skills",i,{proficiency:e.target.value})}/><button className="danger" type="button" onClick={()=>removeArray("skills",i)}>Remove</button></div>)}
          </section>

          <div className="save-row"><span>{message}</span><button className="save" disabled={saving}>{saving ? "Saving…" : "Save career profile"}</button></div>
        </form>
      </div>
    </main>
  );
}
