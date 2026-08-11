# Campus AI — TNEA Counselling Recommendation System

A calm, responsive full-stack MVP built with **React + Vite** on the frontend and **FastAPI + Pandas + SQLite** on the backend.

## Included
- Campus AI chat assistant with guided profile onboarding.
- NLP-style alias handling for common branch/district abbreviations (CSE, ECE, EEE, IT, AI & DS, etc.).
- Cutoff calculator: Mathematics + Physics/2 + Chemistry/2.
- College Finder: name, cutoff, community, district and branch filters.
- 2025 dataset-grounded recommendations.
- Chat history persisted in SQLite using name + community + cutoff as the profile key.
- Browser localStorage keeps the active profile and recent chat on the same device.
- Responsive UI for mobile, tablet, laptop and desktop.
- No dark full-page background; calm green/cream professional palette inspired by the supplied example PDF.

## Dataset
`backend/data/Final_TNEA_dataset.csv` is the supplied dataset and is used directly by the backend.

The dataset contains 3,474 branch records across 438 college names. Some source rows have blank/irregular district values; the backend normalizes common suffix artifacts for filtering and displays unspecified district values as "District not specified". It does not invent missing cutoff values.

## Requirements
- Windows 10/11
- Python 3.10+
- Node.js 18+
- VS Code

## Run in VS Code

### 1. Open the project
Extract the ZIP, then open the extracted `Campus-AI-TNEA-Counselling-Recommendation-System` folder in VS Code.

### 2. Start backend
Open Terminal 1:
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

If PowerShell blocks activation, use:
```powershell
.\.venv\Scriptsctivate.bat
```

Backend health check:
`http://127.0.0.1:8000/api/health`

### 3. Start frontend
Open Terminal 2:
```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, normally:
`http://localhost:5173`

### 4. Recommended first test
1. Open Campus AI.
2. Type `Hi`.
3. Enter a name.
4. Enter a cutoff such as `180`.
5. Enter a community such as `OC`.
6. Enter `Chennai` or `all districts`.
7. Enter `CSE` or `all branches`.
8. Ask follow-up questions such as:
   - Which colleges can I get with 180 cutoff?
   - Which colleges offer CSE?
   - Suggest colleges in Chennai.
   - What was the previous cutoff for this college?
   - What documents are needed for counselling?

## Important accuracy note
This application only makes college/cutoff recommendations from the supplied 2025 dataset. It does not invent placement, fee, hostel, transport, or current-year cutoff figures. Counselling dates and current rules can change, so verify the current official TNEA instructions before making a final choice.

## Architecture
```text
Campus-AI-TNEA-Counselling-Recommendation-System/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   └── main.py
│   ├── data/
│   │   └── Final_TNEA_dataset.csv
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
└── README.md
```
