# Career Venture Lab: Team Healthcare (Pathway NUR-2)

**Course:** Precalculus (Challenge Level: Advanced)  
**Pathway:** NUR-2 — Healthcare / Nursing: Nurse-led health education simulation  
**Team ID:** Team Healthcare  

> **Simulation Disclaimer:** Fictional business, customers, transactions, and funding for educational simulation only. Models fictional general health education—no medical diagnosis, clinical treatment, or real patient/student data.

---

## Project Structure

- `app.py` — Main Stage 1 Streamlit dashboard (Inputs & Funding, Precalculus Math Skills & Levels, Operations & Finance Ledger, Snapshot Save/Load JSON, CSV Export, and Fixture Replay).
- `engine.py` — Deterministic simulation engine, Decimal-safe accounting logic, Precalculus math functions, and snapshot validation.
- `requirements.txt` — Python dependencies for local runs and Render deployment.
- `sample_data/monthly_fixture.csv` — Official NUR-2 acceptance test fixture.
- `tests/test_nur2.py` — Automated pytest suite verifying all NUR-2 and Precalculus acceptance checks.

---

## Step 1: Run Locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the acceptance tests:
   ```bash
   pytest
   ```
3. Launch the Streamlit app:
   ```bash
   streamlit run app.py
   ```

---

## Step 2: Push to GitHub

1. Create a new repository on GitHub (e.g., `team-healthcare-nur2`).
2. Upload all files (`app.py`, `engine.py`, `requirements.txt`, `README.md`, `sample_data/`, `tests/`) or push via Git:
   ```bash
   git init
   git add .
   git commit -m "Stage 1 NUR-2 Precalculus simulation"
   git branch -M main
   git remote add origin https://github.com/<YOUR-USERNAME>/team-healthcare-nur2.git
   git push -u origin main
   ```

---

## Step 3: Deploy on Render

1. Log in to [Render](https://render.com) and click **New +** -> **Web Service**.
2. Connect your GitHub repository (`team-healthcare-nur2`).
3. Configure the service settings:
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `streamlit run app.py --server.address 0.0.0.0 --server.port $PORT`
4. Click **Create Web Service** and wait for the build to finish.
5. **Persistence Check:** Render's filesystem resets on redeploy/restart. Always use the dashboard's **Download Snapshot JSON** button to save your state locally and **Upload / Restore Snapshot JSON** when returning.
