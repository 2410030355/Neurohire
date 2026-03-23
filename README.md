# Neurohire

**AI Resume Analyzer platform** -a full-stack application for recruiters and job seekers, built with **Django** (backend) and **React** (frontend).

## About

Neurohire helps recruiters analyze resumes with AI, search talent across platforms, schedule interviews, and track hiring decisions. Job seekers can improve their resumes, practice with mock interviews, generate project Q&A, and browse job listings.

### Features

- **Resume analysis** - Upload resumes; get AI-powered fit scores, skill gaps, and improvement suggestions
- **Talent search** -Search candidates via GitHub or job portals (LinkedIn, Naukri, Internshala, Indeed)
- **Scheduling** -Schedule interviews and manage waitlists
- **AI analytics** - Track AI vs recruiter agreement on hiring decisions
- **Job seeker tools** - Resume improver, project Q&A generator, audio mock interviews, job board

## Tech stack

- **Frontend:** React 18, Vite, TanStack Query, Tailwind CSS, Framer Motion
- **Backend:** Django REST API at `http://127.0.0.1:8000`

## Prerequisites

- Node.js 18+
- Python 3.10+ (for Django backend)
- npm or yarn

## Setup

### 1. Clone and install frontend dependencies

```bash
git clone <repository-url>
cd Neurohire
npm install
```

### 2. Django backend

Run your Django backend at **http://127.0.0.1:8000** and ensure these API routes are implemented:

- **Auth:** `POST /api/auth/login/`, `POST /api/auth/register/`, `GET /api/auth/me/`, `POST /api/auth/logout/`
- **Candidates:** `GET /api/candidates/`, `PATCH /api/candidates/:id/`
- **Resumes:** `POST /api/upload-resume/`, `POST /api/resume-improvement/`
- **Jobs:** `GET /api/jobs/`
- **Interviews:** `GET /api/interviews/`, `POST /api/interviews/`, `PATCH /api/interviews/:id/`
- **Waitlist:** `GET /api/waitlist/`, `DELETE /api/waitlist/:id/`
- **AI / LLM:** `POST /api/project-qa/`, `POST /api/mock-interview/start/`, `POST /api/mock-interview/analyze/`, `POST /api/talent-search/`
- **Misc:** `GET /api/ai-decision-logs/`, `POST /api/upload-file/`

### 3. Run the frontend

```bash
npm run dev
```

Open the URL shown in the terminal (e.g. `http://localhost:5173`). The app talks to the Django API at `http://127.0.0.1:8000` by default.

### 4. Build for production

```bash
npm run build
```

Output is in the `dist/` folder. Point your web server or Django static files at this build.

## Scripts

| Command        | Description              |
|----------------|--------------------------|
| `npm run dev`  | Start Vite dev server    |
| `npm run build`| Production build         |
| `npm run preview` | Preview production build |
| `npm run lint` | Run ESLint               |

## Project structure

- `src/` -React app (pages, components, API client)
- `src/api/http.js` -Shared API base URL and `jsonFetch` helper for Django REST
- `src/pages/` - Seeker and recruiter auth, dashboards, home
- `src/components/` - UI components, recruiter (analysis, talent search, scheduling), seeker (resume improver, mock interview, job board)
