import React, { useMemo, useState } from 'react';

const makeId = (prefix) => `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

const getRoxSymbolicLine = (route, status) => {
  if (status === 'KILL' || status === 'QKILL') {
    return {
      symbols: '○ → □ → △ → ✗',
      translation: '≢ ✗ (Ontologisk brudd / ulovlig tilstand)'
    };
  }

  const hasShortcut = route.includes('RAW') && route.includes('STRUCT') && !route.includes('ESTIMATE');
  if (hasShortcut) {
    return {
      symbols: '○ → △ → ✗',
      translation: '≢ ✗ (Kortslutning detektert)'
    };
  }

  switch (status) {
    case 'OPEN':
    case 'QOPEN':
      return {
        symbols: '○ → □ → ○ → ✓',
        translation: '≡ ✓ (Legitim realisering / OPEN)'
      };
    case 'HOLD':
    case 'QHOLD':
      return {
        symbols: '○ → □ → ○ → ◉',
        translation: '≡ ◉ (Suspendert / rekalibrering pågår)'
      };
    default:
      return {
        symbols: '○ → □ → ○',
        translation: '≡ (Under evaluering)'
      };
  }
};

const initialCandidates = [
  {
    id: 'cand-1',
    name: 'Standard Koherent Krets',
    route: ['RAW', 'ESTIMATE', 'STRUCT', 'GATE'],
    currentStep: 0,
    rA: 0.12,
    calibration: 0.95,
    syndrome: 'Ingen avvik',
    risk: 0.05,
    status: 'UNDER_EVALUERING',
    log: ['Opprettet rå-kandidat.']
  },
  {
    id: 'cand-2',
    name: 'Uautorisert Direkte-oppdatering',
    route: ['RAW', 'STRUCT', 'GATE'],
    currentStep: 0,
    rA: 0.05,
    calibration: 1.0,
    syndrome: 'Ingen avvik',
    risk: 0.1,
    status: 'UNDER_EVALUERING',
    log: ['Opprettet rå-kandidat.']
  },
  {
    id: 'cand-3',
    name: 'Støyende Måleprotokoll',
    route: ['RAW', 'ESTIMATE', 'STRUCT', 'GATE'],
    currentStep: 0,
    rA: 0.38,
    calibration: 0.72,
    syndrome: 'Fase-skift detektert',
    risk: 0.3,
    status: 'UNDER_EVALUERING',
    log: ['Opprettet rå-kandidat.']
  }
];

const initialWitness = [
  {
    id: 'wit-0',
    timestamp: new Date(Date.now() - 3600000).toLocaleTimeString(),
    name: 'Kalibrert Base-Hamiltonian',
    mode: 'QUANTUM',
    details: 'Måleresultater integrert. rA = 0.08'
  }
];

const emptyDelta = () => ({ accepted: 0, holded: 0, killed: 0, typeBreaks: 0 });

function evaluateAdmissibilityPure(candidate, mode, incomingLog = candidate.log) {
  const log = [...incomingLog];
  const delta = emptyDelta();
  const result = { candidate: null, witness: null, hold: null, delta };

  if (mode === 'QUANTUM') {
    const rA = Number(candidate.rA);
    log.push(`Måler residual-lekkasje r_A(ρ) = ${rA}`);

    if (rA > 0.45 || Number(candidate.risk) > 0.5) {
      log.push('KILL: residual overskrider kritisk grense eller risiko er for høy. Status: QKILL.');
      delta.killed += 1;
      result.candidate = { ...candidate, currentStep: candidate.route.indexOf('GATE'), status: 'QKILL', log };
      return result;
    }

    if (rA > 0.2) {
      log.push('HOLD: admissibilitet ikke bekreftet. Status: QHOLD. Venter på dynamical decoupling.');
      delta.holded += 1;
      result.hold = { ...candidate, currentStep: candidate.route.indexOf('GATE'), status: 'QHOLD', log };
      result.candidate = result.hold;
      return result;
    }

    log.push('OPEN: protokollen er validert. Status: QOPEN. Erfaring frigis til Witness.');
    delta.accepted += 1;
    result.candidate = { ...candidate, currentStep: candidate.route.indexOf('GATE'), status: 'QOPEN', log };
    result.witness = {
      id: makeId('wit'),
      timestamp: new Date().toLocaleTimeString(),
      name: candidate.name,
      mode: 'QUANTUM',
      details: `Validert med rA = ${rA}. Ingen spøkelseserfaringer.`
    };
    return result;
  }

  if (Number(candidate.risk) > 0.4) {
    log.push('KILL: for høy klassisk usikkerhet. Status: KILL.');
    delta.killed += 1;
    result.candidate = { ...candidate, currentStep: candidate.route.indexOf('GATE'), status: 'KILL', log };
    return result;
  }

  if (Number(candidate.risk) > 0.15) {
    log.push('HOLD: klassisk usikkerhet moderat. Status: HOLD.');
    delta.holded += 1;
    result.hold = { ...candidate, currentStep: candidate.route.indexOf('GATE'), status: 'HOLD', log };
    result.candidate = result.hold;
    return result;
  }

  log.push('OPEN: klassisk forslag godkjent. Status: OPEN.');
  delta.accepted += 1;
  result.candidate = { ...candidate, currentStep: candidate.route.indexOf('GATE'), status: 'OPEN', log };
  result.witness = {
    id: makeId('wit'),
    timestamp: new Date().toLocaleTimeString(),
    name: candidate.name,
    mode: 'CLASSICAL',
    details: 'Klassisk forslag commitet til læring.'
  };
  return result;
}

function mergeDelta(a, b) {
  return {
    accepted: a.accepted + b.accepted,
    holded: a.holded + b.holded,
    killed: a.killed + b.killed,
    typeBreaks: a.typeBreaks + b.typeBreaks
  };
}

function StatusPill({ value }) {
  const color = value.includes('OPEN')
    ? 'text-emerald-300 border-emerald-500/30 bg-emerald-500/10'
    : value.includes('HOLD')
      ? 'text-amber-300 border-amber-500/30 bg-amber-500/10'
      : value.includes('KILL')
        ? 'text-rose-300 border-rose-500/30 bg-rose-500/10'
        : 'text-slate-300 border-slate-700 bg-slate-900';

  return <span className={`rounded border px-2 py-0.5 text-[10px] font-bold uppercase ${color}`}>{value}</span>;
}

function MetricCard({ label, value, tone }) {
  const tones = {
    teal: 'text-teal-300',
    rose: 'text-rose-400',
    purple: 'text-purple-300',
    amber: 'text-amber-300'
  };

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
      <span className="block text-[10px] font-bold uppercase text-slate-400">{label}</span>
      <span className={`text-2xl font-bold ${tones[tone]}`}>{value}</span>
    </div>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState('simulator');
  const [systemMode, setSystemMode] = useState('QUANTUM');
  const [candidates, setCandidates] = useState(initialCandidates);
  const [witnessLedger, setWitnessLedger] = useState(initialWitness);
  const [holdBuffer, setHoldBuffer] = useState([]);
  const [stats, setStats] = useState({ totalProcessed: 3, accepted: 1, holded: 0, killed: 0, typeBreaks: 0 });
  const [newCandidate, setNewCandidate] = useState({
    name: 'Egendefinert Eksperiment',
    routeType: 'VALID',
    rA: 0.2,
    calibration: 0.9,
    risk: 0.15,
    syndrome: 'Ingen'
  });

  const activeCandidates = useMemo(
    () => candidates.filter((candidate) => candidate.status === 'UNDER_EVALUERING'),
    [candidates]
  );

  const stepPipeline = () => {
    let aggregateDelta = emptyDelta();
    const witnessEntries = [];
    const holdEntries = [];

    const advanced = candidates.map((candidate) => {
      if (candidate.status !== 'UNDER_EVALUERING') return candidate;

      const nextStepIdx = candidate.currentStep + 1;
      if (nextStepIdx >= candidate.route.length) return candidate;

      const prevNode = candidate.route[candidate.currentStep];
      const nextNode = candidate.route[nextStepIdx];
      const log = [...candidate.log];

      if (prevNode === 'RAW' && nextNode === 'STRUCT') {
        log.push('TYPEBRUDD: forsøkte RAW -> STRUCT uten ESTIMATE.');
        log.push('KILL: kandidaten forkastes før den kan skrive til Witness.');
        aggregateDelta = mergeDelta(aggregateDelta, { ...emptyDelta(), killed: 1, typeBreaks: 1 });
        return { ...candidate, currentStep: nextStepIdx, status: 'KILL', log };
      }

      log.push(`Overgang: ${prevNode} -> ${nextNode}`);

      if (nextNode === 'GATE') {
        const evaluation = evaluateAdmissibilityPure(candidate, systemMode, log);
        aggregateDelta = mergeDelta(aggregateDelta, evaluation.delta);
        if (evaluation.witness) witnessEntries.push(evaluation.witness);
        if (evaluation.hold) holdEntries.push(evaluation.hold);
        return evaluation.candidate;
      }

      return { ...candidate, currentStep: nextStepIdx, log };
    });

    setCandidates(advanced.filter((candidate) => candidate.status === 'UNDER_EVALUERING'));

    if (witnessEntries.length > 0) {
      setWitnessLedger((previous) => [...witnessEntries, ...previous]);
    }

    if (holdEntries.length > 0) {
      setHoldBuffer((previous) => [...previous, ...holdEntries]);
    }

    if (aggregateDelta.accepted || aggregateDelta.holded || aggregateDelta.killed || aggregateDelta.typeBreaks) {
      setStats((previous) => ({
        ...previous,
        accepted: previous.accepted + aggregateDelta.accepted,
        holded: previous.holded + aggregateDelta.holded,
        killed: previous.killed + aggregateDelta.killed,
        typeBreaks: previous.typeBreaks + aggregateDelta.typeBreaks
      }));
    }
  };

  const applyDynamicalDecoupling = (id) => {
    const target = holdBuffer.find((candidate) => candidate.id === id);
    if (!target) return;

    const adjustedRA = Math.max(0.05, Number((Number(target.rA) * 0.3).toFixed(3)));
    const adjustedRisk = Math.max(0.02, Number((Number(target.risk) * 0.5).toFixed(3)));
    const log = [
      ...target.log,
      'Rekalibrering: dynamical decoupling iverksatt.',
      `Residual r_A redusert til ${adjustedRA}.`
    ];

    const evaluation = evaluateAdmissibilityPure(
      { ...target, rA: adjustedRA, risk: adjustedRisk, status: 'UNDER_EVALUERING' },
      systemMode,
      log
    );

    setHoldBuffer((previous) => {
      const remaining = previous.filter((candidate) => candidate.id !== id);
      return evaluation.hold ? [...remaining, evaluation.hold] : remaining;
    });

    if (evaluation.witness) {
      setWitnessLedger((previous) => [evaluation.witness, ...previous]);
    }

    setStats((previous) => ({
      ...previous,
      holded: Math.max(0, previous.holded - 1 + evaluation.delta.holded),
      accepted: previous.accepted + evaluation.delta.accepted,
      killed: previous.killed + evaluation.delta.killed
    }));
  };

  const manualKillFromHold = (id) => {
    setHoldBuffer((previous) => previous.filter((candidate) => candidate.id !== id));
    setStats((previous) => ({
      ...previous,
      holded: Math.max(0, previous.holded - 1),
      killed: previous.killed + 1
    }));
  };

  const handleCreateCandidate = (event) => {
    event.preventDefault();

    const route = newCandidate.routeType === 'VALID'
      ? ['RAW', 'ESTIMATE', 'STRUCT', 'GATE']
      : ['RAW', 'STRUCT', 'GATE'];

    const candidate = {
      id: makeId('cand'),
      name: newCandidate.name || 'Uten navn',
      route,
      currentStep: 0,
      rA: Number(newCandidate.rA),
      calibration: Number(newCandidate.calibration),
      syndrome: newCandidate.syndrome || 'Manuell injeksjon',
      risk: Number(newCandidate.risk),
      status: 'UNDER_EVALUERING',
      log: ['Injisert kandidat i realiseringssløyfen.']
    };

    setCandidates((previous) => [...previous, candidate]);
    setStats((previous) => ({ ...previous, totalProcessed: previous.totalProcessed + 1 }));
  };

  return (
    <div className="min-h-screen bg-slate-950 p-4 font-sans text-slate-100 selection:bg-teal-500 selection:text-slate-950 md:p-6">
      <header className="mx-auto mb-6 flex max-w-7xl flex-col items-start justify-between gap-4 border-b border-slate-800 pb-4 md:flex-row md:items-center">
        <div>
          <div className="flex items-center gap-3">
            <span className="rounded bg-teal-500 px-2.5 py-1 text-xs font-bold uppercase tracking-widest text-slate-950 shadow-lg shadow-teal-500/20">
              KY-Gate v0.1
            </span>
            <h1 className="text-2xl font-bold tracking-tight text-white">Admissibel Læringssimulator</h1>
          </div>
          <p className="mt-1 text-sm text-slate-400">Epistemisk dørvakt for klassisk og kvantebasert erfaringsovervåking</p>
        </div>

        <div className="flex gap-2 rounded-lg border border-slate-800 bg-slate-900 p-1.5">
          {['simulator', 'teori'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`rounded-md px-4 py-1.5 text-sm font-medium transition-all ${
                activeTab === tab ? 'bg-slate-800 text-teal-300 shadow' : 'text-slate-400 hover:text-white'
              }`}
            >
              {tab === 'simulator' ? 'Aktiv Simulator' : 'Formelt Manifest'}
            </button>
          ))}
        </div>
      </header>

      <main className="mx-auto max-w-7xl">
        {activeTab === 'simulator' ? (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
            <section className="flex flex-col gap-6 lg:col-span-4">
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-5 shadow-xl">
                <h2 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-slate-400">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-cyan-400" />
                  Portvakt-modus
                </h2>
                <div className="grid grid-cols-2 gap-2 rounded-lg border border-slate-800 bg-slate-950 p-1">
                  <button
                    onClick={() => setSystemMode('CLASSICAL')}
                    className={`rounded px-3 py-2 text-xs font-bold transition-all ${systemMode === 'CLASSICAL' ? 'bg-amber-500 text-slate-950' : 'text-slate-400 hover:text-slate-200'}`}
                  >
                    Klassisk (Ω)
                  </button>
                  <button
                    onClick={() => setSystemMode('QUANTUM')}
                    className={`rounded px-3 py-2 text-xs font-bold transition-all ${systemMode === 'QUANTUM' ? 'bg-teal-500 text-slate-950' : 'text-slate-400 hover:text-slate-200'}`}
                  >
                    Kvantebasert (Ω_Q)
                  </button>
                </div>
                <p className="mt-3 text-xs italic leading-relaxed text-slate-400">
                  {systemMode === 'QUANTUM'
                    ? 'Overvåker tetthetsoperator ρ_t og residuallekkasje r_A ut av admissibelt subrom.'
                    : 'Klassisk dørvakt basert på deterministiske risikomål og legitimitet.'}
                </p>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-900 p-5 shadow-xl">
                <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-slate-400">Injiser ny kandidat</h2>
                <form onSubmit={handleCreateCandidate} className="flex flex-col gap-3">
                  <label className="text-[10px] font-bold uppercase text-slate-400">
                    Eksperimentnavn
                    <input
                      value={newCandidate.name}
                      onChange={(event) => setNewCandidate({ ...newCandidate, name: event.target.value })}
                      className="mt-1 w-full rounded border border-slate-800 bg-slate-950 px-3 py-1.5 text-xs text-slate-200 outline-none focus:border-teal-500"
                    />
                  </label>

                  <label className="text-[10px] font-bold uppercase text-slate-400">
                    Type-progresjon
                    <select
                      value={newCandidate.routeType}
                      onChange={(event) => setNewCandidate({ ...newCandidate, routeType: event.target.value })}
                      className="mt-1 w-full rounded border border-slate-800 bg-slate-950 px-2 py-1.5 text-xs text-slate-200 outline-none focus:border-teal-500"
                    >
                      <option value="VALID">Admissibel: RAW -> ESTIMATE -> STRUCT</option>
                      <option value="SHORTCUT">Ontologisk snarvei: RAW -> STRUCT</option>
                    </select>
                  </label>

                  <div className="grid grid-cols-2 gap-2">
                    <label className="text-[10px] font-bold uppercase text-slate-400">
                      Residual r_A
                      <input
                        type="number"
                        min="0"
                        max="1"
                        step="0.01"
                        value={newCandidate.rA}
                        onChange={(event) => setNewCandidate({ ...newCandidate, rA: event.target.value })}
                        className="mt-1 w-full rounded border border-slate-800 bg-slate-950 px-3 py-1.5 text-xs text-slate-200 outline-none focus:border-teal-500"
                      />
                    </label>
                    <label className="text-[10px] font-bold uppercase text-slate-400">
                      Risk
                      <input
                        type="number"
                        min="0"
                        max="1"
                        step="0.01"
                        value={newCandidate.risk}
                        onChange={(event) => setNewCandidate({ ...newCandidate, risk: event.target.value })}
                        className="mt-1 w-full rounded border border-slate-800 bg-slate-950 px-3 py-1.5 text-xs text-slate-200 outline-none focus:border-teal-500"
                      />
                    </label>
                  </div>

                  <button className="mt-2 rounded border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-bold text-slate-200 transition-colors hover:bg-slate-700">
                    Generer og injiser
                  </button>
                </form>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-900 p-5 shadow-xl">
                <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-slate-400">Integritets-monitor</h2>
                <div className="grid grid-cols-2 gap-4">
                  <MetricCard label="Realisert erfaring" value={stats.accepted} tone="teal" />
                  <MetricCard label="Forkastet" value={stats.killed} tone="rose" />
                  <MetricCard label="Typebrudd" value={stats.typeBreaks} tone="purple" />
                  <MetricCard label="Aktivt HOLD" value={stats.holded} tone="amber" />
                </div>
              </div>
            </section>

            <section className="flex flex-col gap-6 lg:col-span-8">
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 shadow-xl">
                <div className="mb-6 flex flex-col justify-between gap-4 md:flex-row md:items-center">
                  <div>
                    <h2 className="text-base font-bold text-white">Nodeprosessering i sanntid</h2>
                    <p className="text-xs text-slate-400">Trykk for å drive kandidatene framover gjennom livssyklusen.</p>
                  </div>
                  <button
                    onClick={stepPipeline}
                    disabled={activeCandidates.length === 0}
                    className="rounded bg-teal-500 px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-950 shadow-lg shadow-teal-500/10 transition-all hover:bg-teal-400 disabled:opacity-50 disabled:hover:bg-teal-500"
                  >
                    Driver pipeline ->
                  </button>
                </div>

                <div className="mb-6 grid grid-cols-4 gap-2 rounded-xl border border-slate-800 bg-slate-950 px-2 py-4 text-center">
                  {[
                    ['1. RAW', 'Ubehandlet forslag', 'text-teal-300'],
                    ['2. ESTIMATE', 'Sannsynlighetsestimat', 'text-cyan-300'],
                    ['3. STRUCT', 'Type-konsistens', 'text-purple-300'],
                    ['4. GATE (Ω)', 'Ternær avgjørelse', 'text-amber-300']
                  ].map(([title, subtitle, color]) => (
                    <div key={title} className="rounded-lg border border-slate-800 bg-slate-900 p-3">
                      <div className={`text-xs font-bold ${color}`}>{title}</div>
                      <div className="mt-1 text-[9px] text-slate-500">{subtitle}</div>
                    </div>
                  ))}
                </div>

                <h3 className="mb-3 text-xs font-bold uppercase tracking-wider text-slate-400">Aktive kandidat-strømmer</h3>
                <div className="flex flex-col gap-3">
                  {activeCandidates.length === 0 ? (
                    <div className="rounded-lg border border-dashed border-slate-800 py-8 text-center text-xs text-slate-500">Ingen uforløste kandidater i pipelinen nå.</div>
                  ) : (
                    activeCandidates.map((candidate) => {
                      const currentNode = candidate.route[candidate.currentStep];
                      const rox = getRoxSymbolicLine(candidate.route, candidate.status);
                      return (
                        <div key={candidate.id} className="rounded-lg border border-slate-800 bg-slate-950 p-4">
                          <div className="mb-3 flex flex-col justify-between gap-2 border-b border-slate-900 pb-2 md:flex-row md:items-center">
                            <div>
                              <h4 className="text-sm font-bold text-white">{candidate.name}</h4>
                              <p className="text-[10px] text-slate-500">Id: {candidate.id}</p>
                            </div>
                            <span className="rounded border border-slate-800 bg-slate-900 px-2 py-0.5 font-mono text-[9px] text-slate-400">
                              Gjeldende node: <strong className="text-teal-300">{currentNode}</strong>
                            </span>
                          </div>

                          <div className="mb-4 flex items-center gap-2 font-mono text-[10px]">
                            {['RAW', 'ESTIMATE', 'STRUCT', 'GATE'].map((node) => {
                              const included = candidate.route.includes(node);
                              const active = currentNode === node;
                              const passed = included && candidate.route.indexOf(node) < candidate.currentStep;
                              const cls = active
                                ? 'border-teal-500 bg-teal-500/20 text-teal-300 font-bold'
                                : passed
                                  ? 'border-slate-700 bg-slate-800 text-slate-400'
                                  : included
                                    ? 'border-slate-800 bg-slate-900 text-slate-600'
                                    : 'border-rose-900 bg-rose-950/20 text-rose-500/60 line-through';
                              return <div key={node} className={`flex-1 rounded border px-2 py-1.5 text-center ${cls}`}>{node}</div>;
                            })}
                          </div>

                          <div className="mb-3 flex flex-col justify-between gap-1.5 rounded border border-slate-800 bg-slate-900/60 px-3 py-2 font-mono text-xs sm:flex-row sm:items-center">
                            <span className="text-slate-400">ROX-linje:</span>
                            <span className="font-bold tracking-wider text-cyan-300">{rox.symbols}</span>
                            <span className="text-teal-300">{rox.translation}</span>
                          </div>

                          <div className="grid grid-cols-3 gap-2 font-mono text-[10px] text-slate-400">
                            <div className="rounded bg-slate-900/40 p-2">r_A: <strong className="text-slate-200">{candidate.rA}</strong></div>
                            <div className="rounded bg-slate-900/40 p-2">Kalibrering: <strong className="text-slate-200">{candidate.calibration}</strong></div>
                            <div className="rounded bg-slate-900/40 p-2">Syndrom: <strong className="block truncate text-slate-200">{candidate.syndrome}</strong></div>
                          </div>

                          <div className="mt-3 max-h-24 overflow-y-auto rounded border border-slate-900 bg-slate-950 p-2 font-mono text-[9px] text-slate-400">
                            <div className="mb-1 border-b border-slate-900 pb-1 text-[10px] font-bold uppercase text-slate-500">Historikklogg</div>
                            {candidate.log.map((entry, index) => <div key={`${candidate.id}-${index}`}>{entry}</div>)}
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 shadow-xl">
                <h2 className="text-base font-bold text-white">Aktivt Hold-Buffer</h2>
                <p className="mb-4 text-xs text-slate-400">HOLD/QHOLD er ikke forsinket OPEN. Kandidaten må rekalibreres og testes på nytt.</p>
                <div className="flex flex-col gap-3">
                  {holdBuffer.length === 0 ? (
                    <div className="rounded-lg border border-dashed border-slate-800 py-6 text-center text-xs text-slate-500">Ingen suspenderte kandidater.</div>
                  ) : (
                    holdBuffer.map((candidate) => (
                      <div key={candidate.id} className="flex flex-col justify-between gap-4 rounded-lg border border-amber-500/20 bg-slate-950 p-4 md:flex-row">
                        <div className="flex-1">
                          <div className="mb-1 flex items-center gap-2">
                            <span className="h-2 w-2 animate-ping rounded-full bg-amber-500" />
                            <h4 className="text-sm font-bold text-amber-300">{candidate.name}</h4>
                            <StatusPill value={candidate.status} />
                          </div>
                          <p className="mb-2 font-mono text-xs text-slate-400">Residual r_A: <strong className="text-slate-200">{candidate.rA}</strong> | Risiko: <strong className="text-slate-200">{candidate.risk}</strong></p>
                          <div className="rounded border border-slate-900 bg-slate-900/40 p-2 font-mono text-[9px] text-slate-500">Siste hendelse: {candidate.log[candidate.log.length - 1]}</div>
                        </div>
                        <div className="flex shrink-0 gap-2 md:flex-col md:justify-end">
                          <button onClick={() => applyDynamicalDecoupling(candidate.id)} className="rounded border border-amber-500/20 bg-amber-500/10 px-3 py-1.5 text-[11px] font-bold text-amber-300 transition-all hover:bg-amber-500 hover:text-slate-950">
                            Kjør dynamical decoupling
                          </button>
                          <button onClick={() => manualKillFromHold(candidate.id)} className="rounded border border-rose-900/30 bg-rose-950/40 px-3 py-1.5 text-[11px] font-bold text-rose-300 transition-all hover:bg-rose-600 hover:text-white">
                            Aborter og KILL
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 shadow-xl">
                <div className="mb-4 flex flex-col justify-between gap-2 md:flex-row md:items-center">
                  <div>
                    <h2 className="text-base font-bold text-white">Witness Ledger</h2>
                    <p className="text-xs text-slate-400">Registrerer kun det som faktisk har passert dørvakten.</p>
                  </div>
                  <span className="rounded border border-emerald-500/20 bg-emerald-500/10 px-2 py-1 text-[10px] font-bold text-emerald-300">Sikker epistemisk tilstand</span>
                </div>
                <div className="flex max-h-60 flex-col gap-2 overflow-y-auto pr-1">
                  {witnessLedger.map((entry) => (
                    <div key={entry.id} className="flex items-center justify-between gap-4 rounded border border-slate-800 bg-slate-950 p-3 text-xs">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                          <span className="font-bold text-slate-200">{entry.name}</span>
                        </div>
                        <span className="mt-0.5 block font-mono text-[10px] text-slate-500">{entry.details}</span>
                      </div>
                      <div className="shrink-0 text-right">
                        <span className="mb-1 block rounded border border-slate-800 bg-slate-900 px-1.5 py-0.5 font-mono text-[9px] uppercase text-slate-400">{entry.mode}</span>
                        <span className="font-mono text-[10px] text-slate-500">{entry.timestamp}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          </div>
        ) : (
          <div className="mx-auto max-w-4xl rounded-xl border border-slate-800 bg-slate-900 p-6 leading-relaxed text-slate-300 shadow-2xl md:p-8">
            <h2 className="mb-4 border-b border-slate-800 pb-2 text-xl font-bold text-white">Det epistemiske manifest: KY-Gate</h2>

            <section className="mb-6">
              <h3 className="mb-2 text-sm font-bold uppercase tracking-wider text-teal-300">1. Separativ aksiomatikk</h3>
              <p className="mb-3 text-xs text-slate-400">Forslag må ikke forveksles med realisert erfaring. Kandidater kan utforskes. Bare admissible konsekvenser får skrives til Witness.</p>
              <div className="grid grid-cols-2 gap-4 rounded border border-slate-800 bg-slate-950 p-4 text-center font-mono text-xs">
                <div>
                  <div className="mb-1 text-slate-500">Det generative rom</div>
                  <div className="font-bold text-amber-300">Kandidater / muligheter</div>
                </div>
                <div className="border-l border-slate-800">
                  <div className="mb-1 text-slate-500">Det admissible rom</div>
                  <div className="font-bold text-teal-300">Realisert erfaring</div>
                </div>
              </div>
            </section>

            <section className="mb-6">
              <h3 className="mb-2 text-sm font-bold uppercase tracking-wider text-teal-300">2. Type-progresjon</h3>
              <p className="mb-3 text-xs text-slate-400">En node må følge en ufravikelig livssyklus før den kan bli realisert konsekvens.</p>
              <div className="flex items-center justify-center gap-2 rounded border border-slate-800 bg-slate-950 p-3 text-center font-mono text-xs">
                <span className="font-bold text-teal-300">RAW</span>
                <span className="text-slate-600">-></span>
                <span className="font-bold text-cyan-300">ESTIMATE</span>
                <span className="text-slate-600">-></span>
                <span className="font-bold text-purple-300">STRUCT</span>
                <span className="text-slate-600">-></span>
                <span className="font-bold text-amber-300">GATE</span>
              </div>
              <p className="mt-2 font-mono text-xs text-rose-300">RAW -> STRUCT uten ESTIMATE tolkes som ontologisk typebrudd og utløser KILL.</p>
            </section>

            <section className="mb-6">
              <h3 className="mb-2 text-sm font-bold uppercase tracking-wider text-teal-300">3. Kvantebasert tilsyn Ω_Q</h3>
              <p className="mb-3 text-xs text-slate-400">For QML opererer simulatoren i Hilbert-rommet ℋ der systemet representeres ved tetthetsoperatoren ρ_t. Protokollen ℰ_θ genererer kandidattilstanden:</p>
              <div className="mb-3 rounded border border-slate-800 bg-slate-950 p-3 text-center font-mono text-xs text-slate-200">ρ_cand(t+1) = ℰ_θ(ρ_t)</div>
              <p className="mb-3 text-xs text-slate-400">Vi verifiserer mot et admissibelt subrom S_A ⊆ ℋ via prosjektor P_A. Det admissible tilstandsrommet er:</p>
              <div className="mb-3 rounded border border-slate-800 bg-slate-950 p-3 text-center font-mono text-xs text-slate-200">𝒜 = {'{'} ρ ∈ D(ℋ) : Tr[(I - P_A)ρ] ≤ ε {'}'}</div>
              <p className="mb-3 text-xs text-slate-400">Residuallekkasjen måles kontinuerlig:</p>
              <div className="rounded border border-slate-800 bg-slate-950 p-3 text-center font-mono text-xs text-slate-200">r_A(ρ) = Tr[(I - P_A)ρ]</div>
            </section>

            <section>
              <h3 className="mb-2 text-sm font-bold uppercase tracking-wider text-teal-300">4. Witness-prinsippet</h3>
              <p className="text-xs text-slate-400">Witness er skrivebeskyttet for alt unntatt fullførte, realiserte og godkjente tilstander. Predikerte, uforløste og suspenderte kandidater får ikke skrives til denne historien.</p>
            </section>
          </div>
        )}
      </main>

      <footer className="mx-auto mt-12 max-w-7xl border-t border-slate-900 pt-4 text-center font-mono text-xs text-slate-600">
        KY-Gate Admissibility Control System // AI skal bare lære fra erfaringer den hadde rett til å produsere.
      </footer>
    </div>
  );
}
