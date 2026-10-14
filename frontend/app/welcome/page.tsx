'use client';

import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
type User = { id: number; username: string; email: string; is_active: boolean };

export default function WelcomePage() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    fetch(`${API_BASE}/auth/me`, { credentials: "include" })
      .then(async response => { if (!response.ok) throw new Error("unauthenticated"); return response.json(); })
      .then(setUser).catch(() => { window.location.href = "/"; }).finally(() => setLoading(false));
  }, []);
  async function logout() { await fetch(`${API_BASE}/auth/logout`, { method: "POST", credentials: "include" }); window.location.href = "/"; }
  if (loading) return <main style={{minHeight:"100vh",display:"grid",placeItems:"center"}}>Loading…</main>;
  if (!user) return null;
  return <main style={{minHeight:"100vh",display:"grid",placeItems:"center",padding:24,fontFamily:"Arial, sans-serif",color:"#17241f"}}><section style={{maxWidth:560,width:"100%",textAlign:"center"}}><div style={{fontSize:38,marginBottom:12}}>✳</div><p style={{letterSpacing:2,fontSize:12}}>FUTUREPATH AI</p><h1>Welcome, {user.username}.</h1><p>You are securely signed in as {user.email}.</p><a href="/profile" style={{display:"inline-block",marginTop:18,padding:"12px 18px",borderRadius:8,background:"#17241f",color:"white",textDecoration:"none"}}>Build your career profile</a><div><button onClick={logout} style={{marginTop:14,padding:"10px 18px",cursor:"pointer"}}>Sign out</button></div></section></main>;
}
