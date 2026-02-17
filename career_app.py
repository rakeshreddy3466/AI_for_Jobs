import streamlit as st
from huggingface_hub import InferenceClient
import json
import re
from pathlib import Path
from pypdf import PdfReader

# ==========================================
# 🔐 CONFIGURATION
# ==========================================
# PASTE YOUR TOKEN HERE
HF_TOKEN = ""

# Model: Qwen 2.5 Coder 32B (Best for Logic + LaTeX)
REPO_ID = "Qwen/Qwen2.5-Coder-32B-Instruct"

# PATH SETUP
BASE_DIR = Path(__file__).parent
TEMPLATE_DIR = BASE_DIR / "Template"
MASTER_JSON_PATH = BASE_DIR / "master_data.json"

# ==========================================
# 🛠️ DATA ENGINE
# ==========================================

def get_master_resume_content(uploaded_file=None):
    """
    Reads the 'Source of Truth' (Master Resume PDF).
    """
    text = ""
    try:
        # 1. Check Uploaded File
        if uploaded_file:
            reader = PdfReader(uploaded_file)
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
            
        # 2. Check Local File
        local_path = BASE_DIR / "Master_Resume.pdf"
        if local_path.exists():
            reader = PdfReader(local_path)
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
            
    except Exception as e:
        return f"Error reading PDF: {e}"
    
    return None

def load_master_data(uploaded_file=None):
    """
    Loads the Master Data JSON (Projects & Keywords).
    """
    try:
        # 1. Uploaded JSON
        if uploaded_file is not None:
            return json.load(uploaded_file)
        
        # 2. Local JSON
        if MASTER_JSON_PATH.exists():
            with open(MASTER_JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        st.error(f"Error loading JSON: {e}")
    return None

def load_templates():
    """
    Loads the Resume and Cover Letter templates from the 'Template' folder.
    """
    res_temp, cov_temp = None, None
    if TEMPLATE_DIR.exists():
        for f in TEMPLATE_DIR.glob("*.tex"):
            if "resume" in f.name.lower(): 
                res_temp = f.read_text(encoding='utf-8')
            if "cover" in f.name.lower(): 
                cov_temp = f.read_text(encoding='utf-8')
                
    return res_temp, cov_temp

# ==========================================
# 🧠 ELITE RECRUITER PROMPTS (FIXED)
# ==========================================

def get_resume_prompt(master_content, template_content, job_desc, master_data):
    # --- FIX 1: Define data_context here ---
    data_context = json.dumps(master_data, indent=2) if master_data else "No Master JSON provided."

    return f"""[INST]
ROLE: You are an Elite Technical Recruiter & ATS Algorithms Expert.
Your job is to engineer a resume that proves the candidate is the perfect fit.

### 1. THE CANDIDATE'S MASTER DATA (Detailed Projects Source)
{data_context}

### 2. THE CANDIDATE'S MASTER RESUME (Original PDF Content)
{master_content}

### 3. THE TARGET JOB (Analyze Deeply)
{job_desc}

### 4. THE LATEX TEMPLATE (Do Not Break This, Follow It Exactly)
{template_content}

### YOUR MISSION:
1.  **Algorithmic Matching:** Analyze the JD for "Hard Skills" and "Soft Skills" keywords. 
    - *Action:* You MUST inject the top 5 hard skills from the JD into the resume's Skills or Professional Summary section.

2.  **SMART SELECTION (Stop Regurgitating):**
    - Look at the `projects` list in the **Master Data JSON**.
    - Select ONLY the top 3 projects that specifically match the JD's tech stack. **DROP THE REST.**
    - *Logic Check:* If a selected project was done at a company listed in `experience` (e.g., "Tech Concept Lab"), you MUST add the technical details of that project to the **EXPERIENCE** section for that company. Do not bury high-impact work in the "Projects" section if it belongs in "Experience".

3.  **PROJECT DEEP-DIVE (CRITICAL):**
    - Locate the **"Projects"** section.
    - Select the 4 to 5 projects most relevant to this specific Job Description.
    - **Add Descriptions:** For each project, write detailed bullet points explaining:
      - *The Problem:* What was the project solving?
      - *The Tech:* What stack was used? (e.g., "Built using Python, LangChain, and AWS").
      - *The Result:* What was the outcome? (Use numbers/metrics if available in the source).
    - *Format:* Use the template's project command (e.g., `\\cvproject` or `\\item`).
    **PROBLEM:** You have been failing to output LaTeX for the projects section. You must NOT output plain text like "Visimies... itemize".
    - **SOLUTION:** You MUST use valid LaTeX commands.
    - **REQUIRED FORMAT:**
      If the template uses `\\cvproject`, use:
      `\\cvproject{{Project Name}}{{Tech Stack}}`
      `\\begin{{itemize}}`
      `  \\item Detail 1...`
      `\\end{{itemize}}`
      
      If the template uses `\\cventry`, use:
      `\\cventry{{}}{{Project Name}}{{}}{{Tech Stack}}{{}}{{`
      `  \\begin{{itemize}}`
      `    \\item Detail 1...`
      `  \\end{{itemize}}`
      `}}`
    
    - **Add Descriptions:** For each project, write detailed bullet points explaining:
      - *The Problem:* What was the project solving?
      - *The Tech:* What stack was used? (e.g., "Built using Python, LangChain, and AWS").
      - *The Result:* What was the outcome? (Use numbers/metrics if available in the source).

4.  **The "XYZ" Bullet Point Formula:**
    - You must rewrite the candidate's experience using Google's "XYZ" formula:
    - *Formula:* "Accomplished [X] as measured by [Y], by doing [Z]".
    - *Example:* "Reduced API latency by **30% (Y)** by engineering a **Redis caching layer (Z)** for the checkout service **(X)**."
    - *Constraint:* Start every bullet with a high-impact Power Verb (e.g., Architected, Deployed, Engineered, Optimized).

5.  **Crucial "Anti-Robot" Rules:**
    - **NO** generic fluff (e.g., "Team player," "Hard worker").
    - **NO** buzzwords without evidence (e.g., "Synergy," "Spearheaded").
    - **NO** fabricated experience. If the Master Resume doesn't support a skill, do not invent it.

6.  **Formatting & Safety:**
    - Output ONLY the full, valid LaTeX code.
    - Escape all special characters (`&` -> `\\&`, `%` -> `\\%`, `$` -> `\\$`).
    - Do not use markdown blocks.
7. ### 🚨 SYNTAX ENFORCEMENT (DO NOT IGNORE) 🚨
You have been outputting plain text lists. THIS IS AN ERROR. 
You MUST wrap every project and experience in the specific LaTeX commands found in the template.

**INCORRECT OUTPUT:**
Project Name: Tech Stack
itemize
- Bullet 1

**CORRECT OUTPUT (YOU MUST USE THIS):**
\\cvproject{{Project Name}}{{Tech Stack 1, Tech Stack 2}}
\\begin{{itemize}}
    \\item Engineered [X] using [Y] which resulted in [Z].
    \\item Optimized [A] by [B] leading to [C].
\\end{{itemize}}

### OUTPUT:
Provide the singular, best version of the LaTeX code.
[/INST]
"""

def get_cover_letter_prompt(master_content, template_content, job_desc, master_data):
    # --- FIX 2: Added master_data argument & definition ---
    data_context = json.dumps(master_data, indent=2) if master_data else "No Master JSON provided."

    return f"""[INST]
ROLE: You are an Executive Career Strategist & Head of Engineering Hiring.
Your goal is to write a "Strategic Value Proposal" letter that reads like a peer-to-peer consulting pitch, not a desperate job application.

### INPUTS
- **Candidate's Master JSON:** {data_context}
- **Candidate's Master Resume:** {master_content}
- **Target Job (The Problem):** {job_desc}
- **Template:** {template_content}

### THE STRATEGY (3-ACT STRUCTURE):

**ACT 1: The "Value Hook" (No Generic Openers)**
- **BANNED:** "I am writing to apply...", "I was thrilled to see..."
- **REQUIRED:** Start immediately with the intersection of the Company's Challenge (found in the JD) and your specific competence.
- *Example:* "With [Company] scaling its AI agents to [Specific Goal], the challenge of non-deterministic outputs is critical. My recent work on 'The Invisible Engine' directly addresses this by..."
**THE "PROJECT-PROBLEM" MATCH:**
    - Analyze the JD to find the #1 technical challenge they are facing (e.g., Scaling, Security, Latency).
    - Scan the `projects` in Master Data. Pick the **ONE** project that proves you have already solved this exact problem.
    - *Write a "Deep Dive" paragraph:* Explain the tech stack you used (e.g., "I architected 'The Invisible Engine' using n8n and LangChain...") and the specific outcome ("...which reduced process latency by 40%").

**ACT 2: The "Deep-Dive Evidence" (The Meat)**
- Select **ONE (1)** specific, complex project from the Master Resume that best solves the JD's core problem.
- **Deep Dive:** Devote a substantial paragraph to this single project.
- **Explain:**
  1. The Technical Complexity (Mention specific tools: LangChain, n8n, AWS, etc.).
  2. The "Hero Moment": How you solved a specific blocker (e.g., "Latency was too high, so I architected a Redis caching layer...").
  3. The Result: "This reduced process latency by 40%."

**ACT 3: The "Peer-to-Peer" Close**
- **BANNED:** "Thank you for your time," "Looking forward to hearing from you."
- **REQUIRED:** A confident call to action.
- *Example:* "I have specific ideas on how [Skill from JD] could be implemented using [Candidate's Approach] and would value the chance to discuss this with your engineering team."

### CRITICAL CONSTRAINTS:
1.  **Tone:** Professional, Technical, Confident. Write like an Engineer talking to an Engineering Manager.
2.  **Anti-Robot:** Strictly NO em-dashes (—). NO "tapestry", "delve", "esteemed", or "showcase".
3.  **Keywords:** Naturally weave in 3-4 "Hard Skills" from the JD into the narrative.
4.  **Formatting:** Fill the LaTeX template strictly. Output ONLY valid LaTeX code.

[/INST]
"""

# ==========================================
# 🛡️ CLEANER
# ==========================================

def expert_clean_latex(text, doc_type="resume"):
    # 1. Clean Code Blocks
    text = re.sub(r"```latex", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```", "", text)
    
    # 2. Fix Bold Syntax (Convert ** to \textbf)
    text = re.sub(r"\*\*(.*?)\*\*", r"\\textbf{\1}", text)
    
    # 3. Robot Check (Remove Em-dashes)
    text = text.replace("—", "-")
    text = text.replace("–", "-")
    
    # 4. Phrase Fixes
    text = text.replace("Looking forward to hearing from you", "I am available for an interview at your convenience")
    
    return text.strip()

def call_ai_engine(prompt, temp=0.2):
    if "PASTE_YOUR" in HF_TOKEN:
        return "❌ ERROR: Please paste your Hugging Face Token in Line 11!"
    
    client = InferenceClient(api_key=HF_TOKEN)
    try:
        res = client.chat_completion(
            model=REPO_ID, 
            messages=[{"role": "user", "content": prompt}],
            max_tokens=6000, 
            temperature=temp
        )
        return res.choices[0].message.content
    except Exception as e:
        return f"AI Error: {e}"

# ==========================================
# 🖥️ STREAMLIT UI
# ==========================================
st.set_page_config(page_title="Thesis Career Agent", layout="wide", page_icon="🎓")

st.title("🎓 Expert Strategist at Resume")
st.markdown("**Status:** Ready | **Feature:** Master PDF + Master JSON Integration")

# Sidebar
with st.sidebar:
    st.header("1. Input Data")
    
    # PDF Uploader
    uploaded_pdf = st.file_uploader("Upload Master Resume (PDF)", type="pdf")
    master_content = get_master_resume_content(uploaded_pdf)
    
    # --- FIX 3: Added JSON Uploader ---
    uploaded_json = st.file_uploader("Upload master_data.json", type="json")
    master_data = load_master_data(uploaded_json)
    
    # Template Loading
    res_temp, cov_temp = load_templates()
    
    # Status Indicators
    if master_content: 
        st.success(f"✅ Master Resume PDF Loaded")
    else:
        st.info("ℹ️ Upload Master Resume PDF.")
        
    if master_data:
        st.success(f"✅ Master JSON Data Loaded")
    else:
        st.info("ℹ️ Upload master_data.json (Recommended).")
        
    if res_temp: st.success("✅ Resume Template Found")
    else: st.error("❌ No 'resume*.tex' found in Template/ folder")

    if cov_temp: st.success("✅ Cover Letter Template Found")
    else: st.error("❌ No 'cover*.tex' found in Template/ folder")

# Main Interface
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("2. Job Description")
    job_desc = st.text_area("Paste JD here:", height=600, placeholder="The AI will analyze this to select the best projects from your JSON and Resume...")

with col2:
    st.subheader("3. Generate")
    tab1, tab2 = st.tabs(["📄 Resume", "✉️ Cover Letter"])
    
    with tab1:
        if st.button("Generate Resume"):
            if not (master_content and res_temp and job_desc):
                st.error("Missing PDF Data or Template")
            else:
                with st.spinner("Analyzing Projects & Engineering Bullets..."):
                    # --- FIX 4: Passed master_data to the function ---
                    p = get_resume_prompt(master_content, res_temp, job_desc, master_data)
                    raw = call_ai_engine(p, temp=0.2) 
                    clean = expert_clean_latex(raw, doc_type="resume")
                    st.code(clean, language='latex')
    
    with tab2:
        if st.button("Generate Cover Letter"):
            if not (master_content and cov_temp and job_desc):
                st.error("Missing PDF Data or Template")
            else:
                with st.spinner("Drafting Project-Based Narrative..."):
                    # --- FIX 5: Passed master_data to the function ---
                    p = get_cover_letter_prompt(master_content, cov_temp, job_desc, master_data)
                    raw = call_ai_engine(p, temp=0.6)
                    clean = expert_clean_latex(raw, doc_type="cover")
                    st.code(clean, language='latex')