# DataAgent: Natural Language Data Analysis Agent

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-teal.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/framework-Flask%203.0-0F766E.svg)](https://flask.palletsprojects.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-teal.svg)](LICENSE)

> **Hackathon Theme Core**: *"Given a dataset and a business question, determine an appropriate analysis, execute it, validate results, and explain findings with traceable evidence."*  
> **Brand Slogan**: *"No answer without evidence."*

---

## 🌟 Executive Overview

**DataAgent** is a production-style, AI-powered business intelligence web platform that allows business analysts and executives to upload one or multiple datasets, ask business questions in natural language, and receive validated, evidence-backed answers with interactive charts, mathematical proof, and traceable records.

### 🛡️ Core Capabilities

- **Natural Language Understanding**: Uses Gemini GenAI SDK (`google-genai`) paired with high-precision fallback NLP heuristics.
- **Secure Sandbox Execution**: Executes Python data analysis code in an isolated containerized Docker sandbox (with secure local subprocess fallback with memory, CPU, and timeout limits).
- **Iterative Self-Correction**: Automatically diagnoses execution syntax or runtime errors and self-corrects code up to 3 retries without surfacing raw tracebacks.
- **Traceable Evidence & Proof**: Every numeric answer includes exact row counts, breakdown values, step-by-step arithmetic proof, and interactive "View Source Data" modal inspection.
- **Validation Checklist**: Automated checks verify dataset, schema columns, aggregation calculations, ranking, and alignment with the question.
- **Multi-Dataset Relationships**: Automatically detects candidate primary keys, foreign keys, matching columns, and value overlap across multiple files.
- **Professional PDF Export**: Produces branded ReportLab PDF summaries of complete analysis sessions.
- **Strict User Data Isolation**: Scopes every dataset, analysis session, chat history, and report to the logged-in user.

---

## 🎨 Design System

Built on a modern SaaS palette with generous whitespace and clean typography:

| Token | Hex | Role |
| :--- | :--- | :--- |
| **Primary** | `#0F766E` | Primary buttons, active nav, icons |
| **Primary Dark** | `#115E59` | Hover states, headings |
| **Accent** | `#14B8A6` | Highlights, badges |
| **Background** | `#F8FAFC` | App background |
| **Cards** | `#FFFFFF` | Rounded cards with subtle shadows |
| **Main Text** | `#0F172A` | Core typography |
| **Secondary Text** | `#64748B` | Metadata, subtitles |
| **Borders** | `#E2E8F0` | Dividers, subtle borders |
| **Success** | `#16A34A` | Verification checkmarks, badges |

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+ (Tested on Python 3.14)
- Pip & Virtualenv (optional)
- Docker Desktop (optional, for containerized sandbox)

### 2. Installation
```bash
git clone <repo-url>
cd natural-language-data-analysis-agent

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Optionally configure your Gemini API Key in `.env`:
```ini
GEMINI_API_KEY=your_gemini_api_key_here
```
*(Note: If `GEMINI_API_KEY` is omitted, DataAgent runs using its deterministic heuristic NLP engine!)*

### 4. Run Application
```bash
python run.py
```
Open your browser and navigate to: `http://127.0.0.1:5000`

---

## 🧪 Running Test Suite

DataAgent includes automated unit and integration tests covering authentication, multi-file uploads, profiling, relationship detection, sandbox execution, validation, chat history, and PDF generation:

```bash
python -m unittest discover tests
```

---

## 📁 Sample Developer Datasets

Three developer datasets are included in `data/developer/` for immediate testing:
1. `ecommerce_sales.csv`: Multi-region orders, customer segments, sales, profit, discounts.
2. `employee_data.csv`: HR compensation, departments, experience, and performance.
3. `marketing_data.csv`: Multi-channel campaign spend, impressions, clicks, conversions, and revenue.

---

## 🔐 Security Architecture

- **AST Security Gate**: Analyzes generated code for forbidden modules (`os`, `sys`, `subprocess`, `socket`, `eval`, `exec`).
- **Resource Constraints**: 15s execution timeout, 512MB RAM cap.
- **Network Isolation**: Outbound network requests are completely blocked during analysis execution.
- **Passwords**: Hashed with Werkzeug `scrypt`.
