# Deployment Guide: BlackBox

This guide details how to deploy the **ML/FastAPI Backend** (using Render's Free Tier or Hugging Face Spaces Pro Tier) and the **Vite/React Frontend** (using Vercel's Free Tier).

---

## Phase 1: Deploy Backend on Render (Free Tier)

Render allows you to deploy backend web services for free. Since we already have a `Dockerfile` in the `/backend` folder, we can deploy the backend as a free Docker Web Service.

### Step 1: Push your project to GitHub
If you haven't already, push your entire repository containing the `backend/` and `web/` folders to GitHub (or GitLab/Bitbucket).

### Step 2: Create a Web Service on Render
1. Log in or sign up at [render.com](https://render.com). (A credit card is required for identity verification, but you won't be charged on the free tier).
2. On the dashboard, click **New +** and select **Web Service**.
3. Connect your GitHub repository.
4. Configure the following settings:
   - **Name:** `blackbox-backend` (or any name you prefer)
   - **Root Directory:** Set this to `backend` (this tells Render to execute files and find the `Dockerfile` inside the `backend` folder)
   - **Runtime:** Select **Docker** (recommended because the `Dockerfile` specifies exactly how to run FastAPI and system dependencies for OpenCV/YOLO)
   - **Instance Type:** Select **Free** (512 MB RAM, shared CPU)
5. Click **Deploy Web Service**.

> [!NOTE]
> Since Render's Free tier maps external traffic automatically to the container's exposed port (in our case, port `8000`), the Docker configuration will work out of the box.
>
> **Render Free Tier Limitation:** The service will spin down (sleep) after 15 minutes of inactivity. When a new request is received, it will take 30–60 seconds to spin up (cold start).

### Step 3: Copy the Render API URL
Once deployed successfully, Render will display a public URL at the top of your dashboard (e.g., `https://blackbox-backend.onrender.com`). Copy this URL.

---

## Phase 1 (Alternative): Deploy Backend on Hugging Face Spaces (Requires HF PRO)

If you have a Hugging Face PRO subscription ($9/month) and want to use their high-performance CPU instances (16GB RAM), follow these steps:

### Step 1: Create a new Space
1. Log in at [huggingface.co](https://huggingface.co) and click **New** -> **Space**.
2. **SDK:** Select **Docker**.
3. **Docker Template:** Select **Blank**.
4. **Space Hardware:** Select **CPU basic** (16GB RAM, 2 vCPU).
5. **Visibility:** **Public** (required so the frontend can query it without auth headers).

### Step 2: Push code & configure Port
1. Clone the Space repo locally:
   ```bash
   git clone https://huggingface.co/spaces/<your-username>/<your-space-name>
   cd <your-space-name>
   ```
2. Copy files from the `backend/` directory into it (`app.py`, `predict.py`, `model.pkl`, `requirements.txt`, `Dockerfile`).
3. Update the Space's `README.md` to map requests to port `8000` by placing this YAML block at the top:
   ```yaml
   ---
   title: BlackBox Backend
   emoji: 🗑️
   colorFrom: blue
   colorTo: indigo
   sdk: docker
   app_port: 8000
   pinned: false
   ---
   ```
4. Commit and push:
   ```bash
   git add .
   git commit -m "Deploy FastAPI backend"
   git push origin main
   ```
5. Your public API endpoint will be `https://<your-username>-<your-space-name>.hf.space`.

---

## Phase 2: Deploy Frontend on Vercel (Free Tier)

The React/Vite frontend is lightweight and can be deployed entirely for free on Vercel.

### Step 1: Import the Project in Vercel
1. Log in to [vercel.com](https://vercel.com).
2. Click **Add New** -> **Project**.
3. Import the Git repository containing your project.
4. In the configuration options:
   - **Root Directory:** Click **Edit** and select the `web` folder.
   - **Framework Preset:** Vercel will automatically detect **Vite**.
   - **Build Command:** `npm run build` (default)
   - **Output Directory:** `dist` (default)

### Step 2: Configure Environment Variables
1. Expand the **Environment Variables** section.
2. Add the following variable:
   - **Key:** `VITE_BACKEND_URL`
   - **Value:** Your backend URL (e.g., `https://blackbox-backend.onrender.com` or your HF Space URL). **Do not include a trailing slash.**
3. Click **Add**.

### Step 3: Deploy!
1. Click **Deploy**.
2. Once the build finishes, Vercel will assign a public URL (e.g. `https://your-project.vercel.app`).
3. Open the URL, upload an image, and test the garbage detection app!
