# Negotiation Arena – Frontend

React + TypeScript + Vite + Tailwind + Recharts + jsPDF.

    npm install
    cp .env.example .env
    npm run dev        # http://localhost:5173, proxies /api and /ws to localhost:8000

All data (scenarios, sessions, turns, reports) comes from the backend. See `src/types.ts` and `src/lib/api.ts`
for the exact contract; align them with `app/schemas/negotiation.py` and `app/routers/negotiation.py`.
