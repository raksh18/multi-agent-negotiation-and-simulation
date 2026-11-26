import { Link, Route, Routes } from 'react-router-dom';
import ScenarioSelect from './pages/ScenarioSelect';
import Configure from './pages/Configure';
import Arena from './pages/Arena';
import Outcome from './pages/Outcome';

export default function App() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          <Link to="/" className="font-display text-lg font-bold">Negotiation Arena</Link>
          <span className="text-sm text-ink-soft">Multi-agent negotiation simulator</span>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Routes>
          <Route path="/" element={<ScenarioSelect />} />
          <Route path="/configure/:scenarioId" element={<Configure />} />
          <Route path="/arena/:sessionId" element={<Arena />} />
          <Route path="/outcome/:sessionId" element={<Outcome />} />
          <Route path="*" element={<p>Page not found. <Link className="text-teal underline" to="/">Back to scenarios</Link></p>} />
        </Routes>
      </main>
    </div>
  );
}
