
import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api";
const defaultProfile = { name: "", cutoff: "", community: "", district: "ALL", branch: "ALL" };

async function api(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Something went wrong. Please try again.");
  }
  return res.json();
}

function useHashPage() {
  const get = () => {
    const h = window.location.hash.replace("#/", "");
    return ["chat", "calculator", "finder"].includes(h) ? h : "chat";
  };
  const [page, setPage] = useState(get);
  useEffect(() => {
    const onHash = () => setPage(get());
    window.addEventListener("hashchange", onHash);
    if (!window.location.hash) window.location.hash = "#/chat";
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  return page;
}

function navigate(page) {
  window.location.hash = `/${page}`;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function App() {
  const page = useHashPage();
  const [meta, setMeta] = useState(null);
  const [apiError, setApiError] = useState("");

  useEffect(() => {
    api("/meta").then(setMeta).catch(e => setApiError(e.message));
  }, []);

  return (
    <div className="app-shell">
      <Header page={page} />
      <main>
        <Hero meta={meta} />
        <PageTabs page={page} />
        {apiError && <div className="error-banner">{apiError} · Start the backend on port 8000.</div>}
        <div className="page-wrap">
          {page === "chat" && <ChatPage meta={meta} />}
          {page === "calculator" && <CalculatorPage />}
          {page === "finder" && <FinderPage meta={meta} />}
        </div>
      </main>
      <Footer />
    </div>
  );
}

function Header({ page }) {
  return (
    <header className="topbar">
      <button className="brand" onClick={() => navigate("chat")} aria-label="Campus AI home">
        <span className="brand-mark">CA</span>
        <span>
          <strong>Campus AI</strong>
          <small>TNEA Counselling</small>
        </span>
      </button>
      <nav className="desktop-nav" aria-label="Primary navigation">
        <button className={page === "chat" ? "nav-active" : ""} onClick={() => navigate("chat")}>Campus AI</button>
        <button className={page === "calculator" ? "nav-active" : ""} onClick={() => navigate("calculator")}>Cutoff Calculator</button>
        <button className={page === "finder" ? "nav-active" : ""} onClick={() => navigate("finder")}>College Finder</button>
      </nav>
    </header>
  );
}

function Hero({ meta }) {
  return (
    <section className="hero">
      <div className="hero-inner">
        <div className="eyebrow"><span className="dot" /> 2025 DATASET · TNEA GUIDANCE</div>
        <h1>Campus AI — TNEA Counselling<br className="desktop-only" /> Recommendation System</h1>
        <p>
          Calculate your cutoff, explore colleges by district and branch, and chat with a
          dataset-grounded counselling assistant built around the supplied TNEA 2025 records.
        </p>
        <div className="stats">
          <Stat value={meta?.colleges ?? "—"} label="Colleges tracked" />
          <Stat value={meta?.records?.toLocaleString() ?? "—"} label="Branch listings" />
          <Stat value={meta?.districts?.length ?? "—"} label="Districts covered" />
        </div>
      </div>
    </section>
  );
}

function Stat({ value, label }) {
  return <div className="stat"><strong>{value}</strong><span>{label}</span></div>;
}

function PageTabs({ page }) {
  const tabs = [
    ["chat", "01", "Campus AI"],
    ["calculator", "02", "Cutoff Calculator"],
    ["finder", "03", "College Finder"],
  ];
  return (
    <div className="tabs-wrap">
      <div className="tabs">
        {tabs.map(([key, num, label]) => (
          <button key={key} className={`tab ${page === key ? "selected" : ""}`} onClick={() => navigate(key)}>
            <span>{num}</span>{label}
          </button>
        ))}
      </div>
    </div>
  );
}

function ChatPage({ meta }) {
  const [profile, setProfile] = useState(() => JSON.parse(localStorage.getItem("campusProfile") || "null") || defaultProfile);
  const [messages, setMessages] = useState(() => JSON.parse(localStorage.getItem("campusChat") || "null") || []);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [records, setRecords] = useState([]);
  const [onboarding, setOnboarding] = useState(() => {
    const saved = JSON.parse(localStorage.getItem("campusProfile") || "null");
    return saved?.name && saved?.cutoff && saved?.community ? "ready" : "start";
  });
  const endRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (!messages.length) {
      setMessages([{
        role: "assistant",
        text: "Welcome to Campus AI. Say Hi to begin, or ask me directly about TNEA colleges, cutoffs, branches or counselling."
      }]);
    }
  }, []);

  useEffect(() => {
    localStorage.setItem("campusChat", JSON.stringify(messages.slice(-60)));
    localStorage.setItem("campusProfile", JSON.stringify(profile));
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, profile]);

  function add(role, text) {
    setMessages(m => [...m, { role, text }]);
  }

  function nextPrompt(step, p) {
    if (step === "start") {
      setOnboarding("name");
      add("assistant", "Hello! I’m Campus AI. What’s your name?");
    } else if (step === "name") {
      const name = text.trim();
      const next = { ...p, name };
      setProfile(next);
      setOnboarding("cutoff");
      add("assistant", `Nice to meet you, ${name}. What is your TNEA cutoff mark?`);
    } else if (step === "cutoff") {
      const val = parseFloat(text);
      if (!Number.isFinite(val) || val < 0 || val > 200) {
        add("assistant", "Please enter a cutoff between 0 and 200, for example 185 or 172.5.");
        return false;
      }
      const next = { ...p, cutoff: val };
      setProfile(next);
      setOnboarding("community");
      add("assistant", "Got it. Which community should I use? You can choose OC, BC, BCM, MBC, SC, SCA or ST.");
    } else if (step === "community") {
      const val = text.trim().toUpperCase().replace(/\s+/g, "");
      const aliases = { GENERAL:"OC", "OPEN":"OC", "OPENCATEGORY":"OC", MBCDNC:"MBC" };
      const c = aliases[val] || val;
      if (!["OC","BC","BCM","MBC","SC","SCA","ST"].includes(c)) {
        add("assistant", "Please choose one of OC, BC, BCM, MBC, SC, SCA or ST.");
        return false;
      }
      const next = { ...p, community: c };
      setProfile(next);
      setOnboarding("district");
      add("assistant", "Which district are you looking for? You can type a district, or say “all districts”.");
    } else if (step === "district") {
      const next = { ...p, district: text.trim() || "ALL" };
      setProfile(next);
      setOnboarding("branch");
      add("assistant", "Which branch are you interested in? You can type CSE, ECE, EEE, AI & DS, IT, or say “all branches”.");
    } else if (step === "branch") {
      const next = { ...p, branch: text.trim() || "ALL" };
      setProfile(next);
      setOnboarding("ready");
      return true;
    }
    return true;
  }

  async function send() {
    const value = text.trim();
    if (!value || busy) return;
    setText("");
    add("user", value);

    // Guided first conversation.
    if (onboarding !== "ready") {
      const ok = nextPrompt(onboarding, profile);
      if (ok && onboarding === "branch") {
        setBusy(true);
        try {
          const data = await api("/chat", {
            method: "POST",
            body: JSON.stringify({
            name: profile.name, cutoff: profile.cutoff, community: profile.community,
            district: profile.district || "ALL", branch: value || "ALL", message: value
          })
          });
          setProfile(p => ({ ...p, ...data.profile, district: value, branch: value }));
          setRecords(data.records || []);
          add("assistant", data.reply);
        } catch (e) { add("assistant", e.message); }
        finally { setBusy(false); }
      }
      return;
    }

    setBusy(true);
    try {
      const data = await api("/chat", {
        method: "POST",
        body: JSON.stringify({
          name: profile.name || "Student",
          cutoff: profile.cutoff === "" ? null : Number(profile.cutoff),
          community: profile.community || null,
          district: profile.district || "ALL",
          branch: profile.branch || "ALL",
          message: value
        })
      });
      setProfile(p => ({ ...p, ...data.profile }));
      setRecords(data.records || []);
      add("assistant", data.reply);
    } catch (e) {
      add("assistant", e.message);
    } finally {
      setBusy(false);
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }

  function resetChat() {
    localStorage.removeItem("campusChat");
    localStorage.removeItem("campusProfile");
    setProfile(defaultProfile);
    setMessages([{ role:"assistant", text:"Welcome to Campus AI. Say Hi to begin, or ask me directly about TNEA colleges, cutoffs, branches or counselling." }]);
    setRecords([]);
    setOnboarding("start");
  }

  const quick = [
    "Which colleges can I get with 180 cutoff?",
    "Which colleges offer CSE?",
    "Suggest colleges in Chennai.",
    "What documents are needed for counselling?"
  ];

  return (
    <section className="content-section">
      <div className="section-heading">
        <div>
          <span className="section-kicker">01 · DATA-GROUNDED ASSISTANT</span>
          <h2>Talk to Campus AI</h2>
          <p>Ask naturally. Branch and district abbreviations are understood, and your profile is remembered on this device.</p>
        </div>
        <button className="secondary-btn" onClick={resetChat}>Reset conversation</button>
      </div>

      <div className="chat-card">
        <div className="chat-header">
          <div className="assistant-avatar">CA</div>
          <div><strong>Campus AI Assistant</strong><span>2025 TNEA dataset · Guidance mode</span></div>
          <div className="online-dot" title="Local API connected" />
        </div>
        <div className="chat-body">
          <div className="messages">
            {messages.map((m, i) => <ChatBubble key={i} role={m.role} text={m.text} />)}
            {busy && <div className="typing"><span /><span /><span /> Campus AI is checking the records…</div>}
            <div ref={endRef} />
          </div>
          {records.length > 0 && <ResultsTable records={records} title="Matching 2025 records" compact />}
          <div className="quick-prompts">
            {quick.map(q => <button key={q} onClick={() => { setText(q); inputRef.current?.focus(); }}>{q}</button>)}
          </div>
          <form className="chat-input-row" onSubmit={e => {e.preventDefault(); send();}}>
            <input ref={inputRef} value={text} onChange={e => setText(e.target.value)}
              placeholder="Type your question…" aria-label="Chat message" autoComplete="off" />
            <button className="primary-btn" disabled={busy || !text.trim()}>Send</button>
          </form>
          <p className="chat-note">Guidance only. Cutoffs can change by year; verify current counselling dates and rules through official TNEA sources before making decisions.</p>
        </div>
      </div>
    </section>
  );
}

function ChatBubble({ role, text }) {
  return <div className={`bubble-row ${role === "user" ? "user-row" : ""}`}>
    {role !== "user" && <div className="mini-avatar">CA</div>}
    <div className={`bubble ${role}`}>{text}</div>
  </div>;
}

function CalculatorPage() {
  const [marks, setMarks] = useState({ mathematics:"", physics:"", chemistry:"" });
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function calculate(e) {
    e.preventDefault();
    setError(""); setResult(null);
    const vals = Object.values(marks).map(Number);
    if (vals.some(v => !Number.isFinite(v) || v < 0 || v > 100)) {
      setError("Enter valid marks from 0 to 100 for every subject.");
      return;
    }
    setBusy(true);
    try {
      setResult(await api("/calculate-cutoff", { method:"POST", body:JSON.stringify({
        mathematics: vals[0], physics: vals[1], chemistry: vals[2]
      })}));
    } catch(e) { setError(e.message); }
    finally { setBusy(false); }
  }

  return <section className="content-section narrow">
    <div className="section-heading">
      <div><span className="section-kicker">02 · CUT-OFF CALCULATOR</span><h2>Calculate your TNEA cutoff</h2>
      <p>Enter your HSC marks. The calculation follows the formula specified for this project.</p></div>
    </div>
    <div className="calculator-card">
      <div className="formula-box"><span>Formula</span><strong>Mathematics + Physics / 2 + Chemistry / 2</strong><small>Maximum cutoff: 200</small></div>
      <form className="mark-grid" onSubmit={calculate}>
        {[
          ["mathematics","Mathematics"],
          ["physics","Physics"],
          ["chemistry","Chemistry"]
        ].map(([key,label]) => <label key={key}>{label} <span>/100</span>
          <input type="number" min="0" max="100" step="0.01" value={marks[key]}
            placeholder={key==="mathematics" ? "e.g. 96" : key==="physics" ? "e.g. 88" : "e.g. 90"}
            onChange={e => setMarks({...marks,[key]:e.target.value})} required />
        </label>)}
        {error && <div className="inline-error">{error}</div>}
        <button className="primary-btn large" disabled={busy}>{busy ? "Calculating…" : "Calculate cutoff"}</button>
      </form>
      {result && <div className="cutoff-result">
        <div><span>Your calculated cutoff</span><strong>{result.cutoff.toFixed(2)}</strong><small>/ 200</small></div>
        <div className="result-meter"><span style={{width:`${Math.min(result.cutoff/200*100,100)}%`}} /></div>
        <p>Use this cutoff in <button onClick={() => navigate("finder")}>College Finder</button> for a community, district and branch-based shortlist.</p>
      </div>}
    </div>
  </section>
}

function FinderPage({ meta }) {
  const [form, setForm] = useState({ name:"", cutoff:"", community:"OC", district:"ALL", branch:"ALL" });
  const [records, setRecords] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function search(e) {
    e?.preventDefault();
    setError(""); setLoading(true);
    try {
      const data = await api("/recommend", { method:"POST", body:JSON.stringify({
        ...form, cutoff:Number(form.cutoff), limit:300
      })});
      setRecords(data.records || []); setTotal(data.count || 0);
      localStorage.setItem("campusProfile", JSON.stringify(form));
    } catch(e) { setError(e.message); setRecords([]); }
    finally { setLoading(false); }
  }
  function reset() {
    setForm({name:"",cutoff:"",community:"OC",district:"ALL",branch:"ALL"}); setRecords([]); setTotal(0); setError("");
  }
  return <section className="content-section">
    <div className="section-heading">
      <div><span className="section-kicker">03 · COLLEGE FINDER</span><h2>Find colleges that fit your profile</h2>
      <p>Filter the supplied 2025 dataset by cutoff, community, district and branch. Results show the community closing cutoff and margin.</p></div>
    </div>
    <div className="finder-layout">
      <form className="finder-card" onSubmit={search}>
        <label>Your name <input value={form.name} placeholder="e.g. Mahalakshmi" onChange={e=>setForm({...form,name:e.target.value})} /></label>
        <label>Your cutoff mark <input type="number" min="0" max="200" step="0.01" value={form.cutoff} placeholder="e.g. 172.5" onChange={e=>setForm({...form,cutoff:e.target.value})} required /></label>
        <label>Community
          <select value={form.community} onChange={e=>setForm({...form,community:e.target.value})}>
            {["OC","BC","BCM","MBC","SC","SCA","ST"].map(x=><option key={x}>{x}</option>)}
          </select>
        </label>
        <label>District
          <select value={form.district} onChange={e=>setForm({...form,district:e.target.value})}>
            <option value="ALL">All districts</option>
            {(meta?.districts || []).map(x=><option key={x} value={x}>{titleDistrict(x)}</option>)}
          </select>
        </label>
        <label>Branch
          <select value={form.branch} onChange={e=>setForm({...form,branch:e.target.value})}>
            <option value="ALL">All branches</option>
            {(meta?.branches || []).map(x=><option key={x} value={x}>{x}</option>)}
          </select>
        </label>
        {error && <div className="inline-error">{error}</div>}
        <div className="form-actions"><button className="primary-btn large" disabled={loading}>{loading ? "Searching…" : "Search colleges"}</button>
        <button type="button" className="secondary-btn" onClick={reset}>Reset filters</button></div>
      </form>
      <div className="results-card">
        <div className="results-head"><div><span className="section-kicker">RESULTS</span><h3>{loading ? "Checking records…" : `${total.toLocaleString()} matching records`}</h3></div>
          {records.length > 0 && <span className="result-count">Showing {records.length}</span>}</div>
        {loading ? <LoadingRows /> : records.length ? <ResultsTable records={records} /> :
          <div className="empty-state"><div className="empty-icon">⌕</div><h3>Ready for your search</h3><p>Enter your profile and search to see matching college + branch records.</p></div>}
      </div>
    </div>
  </section>
}

function ResultsTable({ records, title, compact=false }) {
  return <div className={`table-wrap ${compact ? "compact-table" : ""}`}>
    {title && <div className="table-title">{title}</div>}
    <table>
      <thead><tr><th>College</th><th>District</th><th>Branch</th><th>2025 cutoff</th><th>Margin</th><th>Fit</th></tr></thead>
      <tbody>{records.map((r,i)=><tr key={`${r.college_code}-${r.branch_code}-${i}`}>
        <td><div className="college-cell"><strong>{r.college_name}</strong><small>Code {r.college_code}</small></div></td>
        <td>{titleDistrict(r.district)}</td><td>{r.branch}<small className="branch-code">{r.branch_code}</small></td>
        <td><strong>{Number(r.closing_cutoff).toFixed(2)}</strong></td>
        <td>+{Number(r.margin).toFixed(1)}</td>
        <td><span className={`fit ${r.status.toLowerCase()}`}>{r.status}</span></td>
      </tr>)}</tbody>
    </table>
  </div>
}

function LoadingRows() {
  return <div className="loading-list">{Array.from({length:6}).map((_,i)=><div className="skeleton" key={i}><span/><span/><span/></div>)}</div>;
}
function titleDistrict(x) { return String(x || "").toLowerCase().replace(/\b\w/g, c=>c.toUpperCase()); }

function Footer() {
  return <footer><p><strong>Campus AI</strong> · TNEA Counselling Recommendation System</p>
    <p>Built from the supplied TNEA 2025 dataset for guidance. Always cross-check current counselling rules, dates and college details with official sources.</p></footer>;
}

createRoot(document.getElementById("root")).render(<App />);
