
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pathlib import Path
import pandas as pd
import sqlite3, re, unicodedata
from typing import Optional, List

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "Final_TNEA_dataset.csv"
DB_PATH = BASE_DIR / "campus_ai.db"

app = FastAPI(title="Campus AI - TNEA Counselling Recommendation System", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

COMMUNITIES = ["OC", "BC", "BCM", "MBC", "SC", "SCA", "ST"]

BRANCH_ALIASES = {
    "cse": "COMPUTER SCIENCE AND ENGINEERING",
    "computer science": "COMPUTER SCIENCE AND ENGINEERING",
    "cs": "COMPUTER SCIENCE AND ENGINEERING",
    "ece": "ELECTRONICS AND COMMUNICATION ENGINEERING",
    "ec": "ELECTRONICS AND COMMUNICATION ENGINEERING",
    "eee": "ELECTRICAL AND ELECTRONICS ENGINEERING",
    "it": "INFORMATION TECHNOLOGY",
    "ai ds": "Artificial Intelligence and Data Science",
    "aids": "Artificial Intelligence and Data Science",
    "ai&ds": "Artificial Intelligence and Data Science",
    "ai and ds": "Artificial Intelligence and Data Science",
    "ai ml": "Artificial Intelligence and Machine Learning",
    "aiml": "Artificial Intelligence and Machine Learning",
    "cyber security": "Computer Science and Engineering (Cyber Security)",
    "cyber": "Computer Science and Engineering (Cyber Security)",
    "mech": "MECHANICAL ENGINEERING",
    "mechanical": "MECHANICAL ENGINEERING",
    "civil": "CIVIL  ENGINEERING",
    "aero": "AERONAUTICAL ENGINEERING",
    "aeronautical": "AERONAUTICAL ENGINEERING",
    "biotech": "BIO TECHNOLOGY",
    "biomedical": "BIO MEDICAL ENGINEERING",
    "bme": "BIO MEDICAL ENGINEERING",
    "mechatronics": "Mechatronics Engineering",
    "robotics": "ROBOTICS AND AUTOMATION",
    "chemical": "CHEMICAL  ENGINEERING",
    "ece vlsi": "Electronics Engineering (VLSI Design and Technology)",
    "vlsi": "Electronics Engineering (VLSI Design and Technology)",
}

DISTRICT_ALIASES = {
    "madras": "CHENNAI", "chennai city": "CHENNAI",
    "coimbatore city": "COIMBATORE", "kovai": "COIMBATORE",
    "trichy": "TIRUCHIRAPPALLI", "tiruchirapalli": "TIRUCHIRAPPALLI",
    "tirunelveli": "TIRUNELVELI", "nellai": "TIRUNELVELI",
    "erode": "ERODE", "salem": "SALEM", "madurai": "MADURAI",
    "kanchipuram": "KANCHIPURAM", "chengalpattu": "CHENGALPATTU",
    "vellore": "VELLORE", "tiruppur": "TIRUPPUR", "tuticorin": "THOOTHUKUDI",
    "thoothukudi": "THOOTHUKUDI", "thanjavur": "THANJAVUR", "tanjore": "THANJAVUR",
}

STOPWORDS = {"college", "colleges", "engineering", "engg", "branch", "branches", "course", "courses", "in", "at", "the", "for", "with", "my", "cutoff", "mark"}

def clean_text(value):
    if value is None or pd.isna(value):
        return ""
    s = unicodedata.normalize("NFKC", str(value)).strip()
    s = re.sub(r"\s+", " ", s)
    return s

def norm(value):
    s = clean_text(value).upper()
    s = re.sub(r"[^A-Z0-9&]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def normalize_district(value):
    s = clean_text(value)
    n = norm(s)
    n = re.sub(r"\s+(FR|F)$", "", n)
    if n == "637018":
        return "UNKNOWN"
    if n in DISTRICT_ALIASES:
        return DISTRICT_ALIASES[n]
    return n

def normalize_branch(value):
    s = clean_text(value)
    n = norm(s)
    if n in BRANCH_ALIASES:
        return BRANCH_ALIASES[n]
    for alias, target in BRANCH_ALIASES.items():
        if n == norm(alias):
            return target
    return s

def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_key TEXT NOT NULL,
        name TEXT NOT NULL,
        community TEXT,
        cutoff REAL,
        role TEXT NOT NULL,
        message TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    con.commit()
    con.close()

df = pd.read_csv(DATA_PATH)
df["DistrictClean"] = df["District"].apply(normalize_district)
df["BranchClean"] = df["Branch Name"].apply(normalize_branch)
df["CollegeClean"] = df["College Name"].apply(clean_text)
for c in COMMUNITIES:
    df[c] = pd.to_numeric(df[c], errors="coerce")
init_db()

class CutoffRequest(BaseModel):
    mathematics: float = Field(ge=0, le=100)
    physics: float = Field(ge=0, le=100)
    chemistry: float = Field(ge=0, le=100)

class RecommendRequest(BaseModel):
    name: str = "Student"
    cutoff: float = Field(ge=0, le=200)
    community: str = "OC"
    district: str = "ALL"
    branch: str = "ALL"
    limit: int = Field(default=100, ge=1, le=300)

class ChatRequest(BaseModel):
    name: str = "Student"
    community: Optional[str] = None
    cutoff: Optional[float] = Field(default=None, ge=0, le=200)
    district: Optional[str] = "ALL"
    branch: Optional[str] = "ALL"
    message: str = Field(min_length=1, max_length=1000)

def profile_key(name, community, cutoff):
    return f"{norm(name)}|{norm(community or '')}|{round(float(cutoff),1) if cutoff is not None else ''}"

def get_history(name, community=None, cutoff=None):
    key = profile_key(name, community, cutoff)
    con = sqlite3.connect(DB_PATH)
    rows = con.execute("SELECT role,message,created_at FROM chat_history WHERE profile_key=? ORDER BY id", (key,)).fetchall()
    con.close()
    return [{"role": r[0], "message": r[1], "created_at": r[2]} for r in rows]

def save_message(name, community, cutoff, role, message):
    con = sqlite3.connect(DB_PATH)
    con.execute("INSERT INTO chat_history(profile_key,name,community,cutoff,role,message) VALUES(?,?,?,?,?,?)",
                (profile_key(name, community, cutoff), name, community, cutoff, role, message))
    con.commit()
    con.close()

def extract_cutoff(text):
    patterns = [
        r"(?:cutoff|mark|score)\s*(?:is|of|=|:)?\s*(\d{2,3}(?:\.\d+)?)",
        r"\b(\d{2,3}(?:\.\d+)?)\s*(?:cutoff|marks?)\b",
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            v = float(m.group(1))
            if 0 <= v <= 200:
                return v
    return None

def detect_community(text):
    n = norm(text)
    for c in COMMUNITIES:
        if re.search(rf"\b{c}\b", n):
            return c
    aliases = {"GENERAL":"OC", "OPEN CATEGORY":"OC", "OTHER COMMUNITY":"OC", "MBC/DNC":"MBC"}
    for a, c in aliases.items():
        if a in n:
            return c
    return None

def detect_district(text):
    n = norm(text)
    if "ALL DISTRICT" in n or "ANY DISTRICT" in n or "ANYWHERE" in n:
        return "ALL"
    for d in sorted(df["DistrictClean"].dropna().unique(), key=len, reverse=True):
        if d != "UNKNOWN" and d in n:
            return d
    for alias, d in DISTRICT_ALIASES.items():
        if norm(alias) in n:
            return d
    return None

def detect_branch(text):
    n = norm(text)
    if re.search(r"\\bALL BRANCH(?:ES)?\\b|\\bANY BRANCH(?:ES)?\\b", n):
        return "ALL"
    for alias, target in sorted(BRANCH_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        a = norm(alias)
        if a and re.search(rf"(?<![A-Z0-9]){re.escape(a)}(?![A-Z0-9])", n):
            return target
    for b in sorted(df["BranchClean"].dropna().unique(), key=len, reverse=True):
        bn = norm(b)
        if bn and re.search(rf"(?<![A-Z0-9]){re.escape(bn)}(?![A-Z0-9])", n):
            return b
    return None

def find_college_names(text):
    query_tokens = set(t for t in norm(text).split() if t not in STOPWORDS and len(t) >= 3)
    candidates = []
    for name in df["CollegeClean"].dropna().unique():
        tokens = set(t for t in norm(name).split() if t not in STOPWORDS and len(t) >= 3)
        if not tokens:
            continue
        overlap = len(query_tokens & tokens)
        if overlap >= 2:
            score = overlap / max(1, len(tokens)) + min(overlap, 5) * 0.03
            candidates.append((score, name))
    candidates.sort(reverse=True)
    return [name for _, name in candidates[:5]]

def recommendation_frame(cutoff, community, district="ALL", branch="ALL", query_college=None):
    community = community if community in COMMUNITIES else "OC"
    work = df.copy()
    if district and district != "ALL":
        work = work[work["DistrictClean"] == normalize_district(district)]
    if branch and branch != "ALL":
        target = normalize_branch(branch)
        work = work[work["BranchClean"].apply(lambda x: norm(x) == norm(target) or norm(target) in norm(x))]
    if query_college:
        q = norm(query_college)
        work = work[work["CollegeClean"].apply(lambda x: q in norm(x))]
    work["closing"] = work[community]
    work = work[work["closing"].notna()]
    work = work[work["closing"] <= cutoff]
    work["margin"] = (work["cutoff"] if "cutoff" in work else cutoff) if False else cutoff - work["closing"]
    work["status"] = work["margin"].apply(lambda x: "Strong" if x >= 10 else ("Possible" if x >= 3 else "Edge"))
    work["District"] = work["DistrictClean"].replace({"UNKNOWN": "District not specified"})
    return work.sort_values(["closing","CollegeClean"], ascending=[False, True])

def format_records(work, limit=30):
    out=[]
    for _, r in work.head(limit).iterrows():
        out.append({
            "college_code": int(r["College Code"]) if pd.notna(r["College Code"]) else "",
            "college_name": r["CollegeClean"],
            "district": r["District"],
            "branch": clean_text(r["Branch Name"]),
            "branch_code": clean_text(r["Branch Code"]),
            "closing_cutoff": float(r["closing"]) if pd.notna(r["closing"]) else None,
            "margin": round(float(r["margin"]),1),
            "status": r["status"],
        })
    return out

@app.get("/api/health")
def health():
    return {"status":"ok"}

@app.get("/api/meta")
def meta():
    districts = sorted([x for x in df["DistrictClean"].dropna().unique() if x != "UNKNOWN"])
    branches = sorted([clean_text(x) for x in df["Branch Name"].dropna().unique()])
    return {
        "project": "Campus AI - TNEA Counselling Recommendation System",
        "records": int(len(df)),
        "colleges": int(df["College Name"].nunique()),
        "districts": districts,
        "branches": branches,
        "communities": COMMUNITIES,
        "formula": "Mathematics + Physics/2 + Chemistry/2",
        "year": 2025
    }

@app.post("/api/calculate-cutoff")
def calculate_cutoff(req: CutoffRequest):
    cutoff = req.mathematics + req.physics/2 + req.chemistry/2
    return {"cutoff": round(cutoff, 2), "formula": f"{req.mathematics:g} + {req.physics:g}/2 + {req.chemistry:g}/2"}

@app.post("/api/recommend")
def recommend(req: RecommendRequest):
    if req.community not in COMMUNITIES:
        raise HTTPException(400, "Please select a supported community.")
    work = recommendation_frame(req.cutoff, req.community, req.district, req.branch)
    records = format_records(work, req.limit)
    return {
        "count": len(work),
        "showing": len(records),
        "records": records,
        "profile": req.model_dump(),
        "note": "Eligibility is based on the 2025 dataset's community closing-cutoff values. A recommendation is not a counselling guarantee."
    }

@app.get("/api/history/{name}")
def history(name: str, community: Optional[str] = None, cutoff: Optional[float] = None):
    return {"messages": get_history(name, community, cutoff)}

def counselling_answer(text):
    n = norm(text)
    if any(k in n for k in ["DOCUMENT", "CERTIFICATE", "WHAT TO BRING", "NEEDED FOR COUNSELLING"]):
        return ("For TNEA counselling preparation, keep your academic and identity documents ready, "
                "including the certificates/details requested in your official counselling instructions. "
                "Use the official TNEA portal for the current year's exact document checklist and upload rules.")
    if any(k in n for k in ["HOW COUNSELLING WORKS", "COUNSELLING PROCEDURE", "PROCESS", "STEPS", "HOW DOES TNEA"]):
        return ("A practical TNEA flow is: registration/application → verification and rank information → "
                "choice filling → processing of choices → provisional/final allotment → joining/reporting as instructed. "
                "Exact dates and rules change by admission year, so confirm the current schedule on the official TNEA portal.")
    if any(k in n for k in ["BEFORE COUNSELLING", "WHAT SHOULD I KNOW", "TIPS"]):
        return ("Before counselling, calculate your cutoff, confirm your community details, prepare a realistic college/branch preference list, "
                "check the latest official schedule, and keep your certificates and login/application details ready.")
    if "FEE" in n or "FEES" in n:
        return ("The attached 2025 dataset is focused on college, district, branch and community closing-cutoff information. "
                "I won't invent fee figures; check the current college and official TNEA sources for fee details.")
    if "HOSTEL" in n or "TRANSPORT" in n:
        return ("Hostel and transport details are not part of the supplied cutoff dataset, so I will not guess them. "
                "For a specific college, use its official website for current facilities.")
    if "PLACEMENT" in n:
        return ("Placement statistics are not fields in the supplied 2025 cutoff dataset. I can still shortlist colleges using your cutoff, community, district and branch, "
                "but I won't invent placement claims.")
    return None

@app.post("/api/chat")
def chat(req: ChatRequest):
    name = clean_text(req.name) or "Student"
    community = req.community if req.community in COMMUNITIES else None
    cutoff = req.cutoff
    text = clean_text(req.message)
    save_message(name, community, cutoff, "user", text)

    extracted_cutoff = extract_cutoff(text)
    extracted_community = detect_community(text)
    extracted_district = detect_district(text) or (req.district if req.district and req.district != "ALL" else None)
    extracted_branch = detect_branch(text) or (req.branch if req.branch and req.branch != "ALL" else None)
    colleges = find_college_names(text)

    answer = counselling_answer(text)
    records = []
    intent = "general"

    if extracted_cutoff is not None:
        cutoff = extracted_cutoff
        intent = "cutoff"
    if extracted_community:
        community = extracted_community

    # Specific college/branch query
    if colleges:
        intent = "college"
        college = colleges[0]
        if cutoff is not None:
            work = recommendation_frame(cutoff, community or "OC", extracted_district or "ALL", extracted_branch or "ALL", college)
            records = format_records(work, 50)
            if records:
                answer = f"Here are the 2025 dataset records for {college} that match your current cutoff/community filters."
            else:
                # show records for the college regardless of cutoff, without claiming eligibility
                base = df[df["CollegeClean"] == college].copy()
                if extracted_branch:
                    base = base[base["BranchClean"].apply(lambda x: norm(extracted_branch) in norm(x))]
                answer = f"I found {college} in the dataset. Here are its matching branch records; eligibility depends on your cutoff and community."
                base["closing"] = base[community or "OC"]
                records = format_records(base.dropna(subset=["closing"]).assign(margin=cutoff-base["closing"], status="Check"), 50)
        else:
            base = df[df["CollegeClean"] == college].copy()
            if extracted_branch:
                base = base[base["BranchClean"].apply(lambda x: norm(extracted_branch) in norm(x))]
            base["closing"] = base[community or "OC"]
            base = base.dropna(subset=["closing"]).assign(margin=0, status="Dataset record")
            records = format_records(base, 50)
            answer = f"I found {college} in the 2025 dataset. Tell me your cutoff if you want an eligibility-based shortlist."
    elif extracted_district or extracted_branch or extracted_cutoff is not None or ("COLLEG" in norm(text) and ("GET" in norm(text) or "SUGGEST" in norm(text) or "SHOW" in norm(text))):
        intent = "recommendation"
        if cutoff is None:
            answer = "I can shortlist colleges accurately once I have your cutoff. You can enter it directly, for example: “My cutoff is 180.”"
        else:
            work = recommendation_frame(cutoff, community or "OC", extracted_district or "ALL", extracted_branch or "ALL")
            records = format_records(work, 40)
            if records:
                scope=[]
                if extracted_district: scope.append(extracted_district.title())
                if extracted_branch: scope.append(extracted_branch)
                answer = f"I found {len(work)} matching 2025 records" + (f" for {' · '.join(scope)}" if scope else "") + f" using {community or 'OC'} and a {cutoff:g} cutoff. The closest matches are shown below."
            else:
                answer = f"For a {cutoff:g} cutoff under {community or 'OC'}, I couldn't form a reliable eligibility shortlist from the selected filters. Try “all districts”, “all branches”, or another cutoff and I’ll broaden the search."
    elif answer is None:
        if re.search(r"\b(hi|hello|hey|good morning|good afternoon|good evening)\b", text, re.I):
            answer = f"Hello {name}! I'm Campus AI. I can help with TNEA cutoffs, colleges, branches and counselling."
        elif "SAFE" in norm(text):
            if cutoff is None:
                answer = "Share your cutoff and community, and I’ll rank safer choices using the 2025 closing-cutoff margin."
            else:
                work = recommendation_frame(cutoff, community or "OC")
                work = work[work["margin"] >= 10]
                records = format_records(work, 30)
                answer = f"I’ve listed stronger-margin choices for a {cutoff:g} cutoff under {community or 'OC'}."
        elif "PREVIOUS CUTOFF" in norm(text) or "LAST YEAR" in norm(text):
            if colleges:
                pass
            else:
                answer = "Tell me the college name and branch. I can return the corresponding 2025 community closing-cutoff record from the dataset."
        elif re.search(r"\b(THANKS|THANK YOU|THANKS A LOT)\b", norm(text)):
            answer = "You're welcome. I’m here whenever you need a TNEA shortlist or cutoff check."
        else:
            answer = ("I can help with TNEA college search, cutoff-based recommendations, branches, districts, "
                      "specific college records and counselling preparation. Try: “My cutoff is 185, BC, suggest CSE colleges in Chennai.”")

    save_message(name, community, cutoff, "assistant", answer)
    return {
        "reply": answer,
        "intent": intent,
        "profile": {"name": name, "community": community, "cutoff": cutoff},
        "detected": {"district": extracted_district, "branch": extracted_branch, "cutoff": extracted_cutoff, "community": extracted_community},
        "records": records,
        "history": get_history(name, community, cutoff)[-30:]
    }
