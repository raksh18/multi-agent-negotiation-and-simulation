# Multi-Agent Negotiation and Simulation

A React/Vite frontend and FastAPI backend for vendor pricing, job offer, and project budget negotiations.

## 1. Run Locally

### Backend Setup

Open a terminal and run:

```powershell
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\Activate.ps1

# Install backend dependencies
python -m pip install -r requirements.txt

# Start FastAPI server
python -m uvicorn main:app --reload --port 8000
```

Backend runs at:

- API: http://localhost:8000
- Swagger documentation: http://localhost:8000/docs
- ReDoc documentation: http://localhost:8000/redoc

### Frontend Setup

Open a second terminal:

```powershell
cd frontend-react

# Install frontend dependencies
npm ci

# Start Vite development server
npm run dev
```

Open the frontend URL displayed in the terminal.

Vite proxies `/api` and `/ws` requests to `localhost:8000`.

## 2. Run Backend Tests

Backend tests use **pytest**.

Open a terminal:

```powershell
cd backend

# Activate virtual environment
venv\Scripts\Activate.ps1

# Install development dependencies
python -m pip install -r requirements-dev.txt

# Run all backend tests
python -m pytest -v
```

### Run Tests from the App Tests Folder

To run only the tests inside `app/tests`:

```powershell
python -m pytest app/tests -v
```

### Run Individual Test Files

Run each test file separately to identify failures:

```powershell
python -m pytest app/tests/test_state.py -v

python -m pytest app/tests/test_history.py -v

python -m pytest app/tests/test_turns.py -v

python -m pytest app/tests/test_orchestrator.py -v

python -m pytest app/tests/test_negotiation_improvements.py -v

python -m pytest app/tests/test_backend_integration.py -v
```

### Check Test Discovery

To see which tests pytest discovers:

```powershell
python -m pytest --collect-only -q
```

### Run Tests with Detailed Failure Information

```powershell
python -m pytest -v --tb=long
```

### Run Tests and Generate Coverage Report

If `pytest-cov` is installed:

```powershell
python -m pytest app/tests --cov=app --cov-report=term-missing
```

## 3. Backend Syntax Validation

Check Python files for syntax errors:

```powershell
python -m compileall app
python -m py_compile main.py
```

## 4. Frontend Validation

Open a terminal:

```powershell
cd frontend-react

# Install dependencies
npm ci

# Run production build
npm run build
```

## 5. Backend API Testing

Start the backend first:

```powershell
python -m uvicorn main:app --reload --port 8000
```

Open Swagger:

http://localhost:8000/docs

Use Swagger to test:

- `GET /api/scenarios`
- `GET /api/scenarios/{scenario_id}`
- `POST /api/negotiations`
- `GET /api/negotiations/{session_id}`
- `GET /api/negotiations/{session_id}/transcript`
- `GET /api/negotiations/{session_id}/report`

WebSocket endpoint:

```text
/ws/negotiations/{session_id}
```

## 6. Backend and Agent Integration Status

The backend owns negotiation state, validates turns, serves scenario/session/transcript/report APIs, and streams live events over WebSockets.

Session state is process-local memory. It is not durable or shared across multiple worker processes.

The repository does not contain the teammate-owned LLM Reasoning Agent or Offer Evaluation Agent.

Register implementations through:

```python
app.integrations.agents.configure_agents
```

The adapter contracts are:

- `generate_turn(context)`
- `evaluate_offer(context)`

Both return structured dictionaries.

The reasoning result must include an action and an offer object for offer/counter actions.

When evaluating a pending offer, the evaluator must return:

```text
decision: accept | reject | counter
```

The reasoning agent supplies the corresponding response text and counter terms.

The evaluator can supply report data under `agents` and `concession_timeline`. Missing evaluation data is reported as unevaluated.

Without a registered reasoning agent, AI turns send an explicit WebSocket error. The backend does not fabricate AI responses.

## 7. Test Coverage and Limitations

See:

```text
backend/app/tests/
```

The test suite covers:

- Negotiation state management
- Negotiation history management
- Turn management
- Orchestrator behavior
- Negotiation validation and improvements
- Backend API and WebSocket integration

The AI flow integration test uses a stub provider. It does not verify a real model or teammate integration.

Passing backend tests confirms the tested backend behavior, but does not establish that the real teammate-owned AI agents are integrated or working.

## 8. Useful Commands

| Task | Command |
|---|---|
| Run all tests | `python -m pytest -v` |
| Run app tests | `python -m pytest app/tests -v` |
| Check syntax | `python -m compileall app` |
| Start backend | `python -m uvicorn main:app --reload --port 8000` |
| Start frontend | `npm run dev` |
| Build frontend | `npm run build` |
| Check Git changes | `git status --short` |