# Snov.io Integration Application

A web application that integrates with the **Snov.io REST API** to retrieve prospect lists, perform automated business email lookups using the Snov.io Email Finder API, and add successfully resolved prospects to designated lists.

## 🚀 Features
*   **Prospect List View**: Displays all prospect lists in your Snov.io account with their names and prospect counts.
*   **Single Prospect Addition**:
    *   Find and add prospects using First Name, Last Name, and Company Domain.
    *   Initiates an asynchronous email search task and polls Snov.io for results.
    *   Only creates and inserts prospects if a valid/unknown business email address is found.
*   **Robust Session Token Cache**: Automates the Snov.io OAuth lifecycle in-memory without persistent databases, automatically refreshing expired tokens.
*   **Premium Visuals**: High-end dark theme design with glassmorphic cards, micro-animations, progress stepper feedback, and a clean responsive interface.

---

## 🛠️ Tech Stack
*   **Backend**: Python, FastAPI, Uvicorn, HTTPX/Requests
*   **Frontend**: React, Vite, Vanilla CSS

---

## 📦 Setup & Installation

Before running the application, make sure Snov.io credentials are set up.

### 1. Backend Configuration
1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   * **Windows (PowerShell):**
     ```powershell
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```
   * **Windows (CMD):**
     ```cmd
     python -m venv .venv
     .venv\Scripts\activate.bat
     ```
   * **macOS / Linux:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file in the `backend/` directory:
   ```env
   SNOV_CLIENT_ID=your_api_client_id
   SNOV_CLIENT_SECRET=your_api_client_secret
   ```

### 2. Frontend Configuration
1. Navigate to the `frontend/` directory:
   ```bash
   cd ../frontend
   ```
2. Install npm packages:
   ```bash
   npm install
   ```

---

## ⚡ How to Start

### 1. Start the Backend Server
From the `backend/` directory (with virtual environment active):
```bash
uvicorn main:app --reload
```
*Note: If `uvicorn` is installed globally or in your current environment, you can also launch it via:*
```bash
python -m uvicorn main:app --reload
```
The backend server runs at **`http://localhost:8000`**.

### 2. Start the Frontend Dev Server
From the `frontend/` directory:
```bash
npm run dev
```
The frontend dev server runs at **`http://localhost:5173`**. You can open this URL in your browser to interact with the application.

