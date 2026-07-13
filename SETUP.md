# Setup

## Backend Setup

1. Create virtual environment:
```
python -m venv .venv
```

2. Activate virtual environment:
```
.venv\Scripts\activate
```

3. Install dependencies:
```
pip install -r backend/requirements.txt
```

4. Run backend server:
```
python backend/app.py
```

Backend runs on http://localhost:8000

## Frontend Setup

1. Install dependencies:
```
cd web
npm install
```

2. Run development server:
```
npm run dev
```

Frontend runs on http://localhost:5173

## API Testing

Backend API docs available at http://localhost:8000/docs
