import type { HardwareState, ScenarioId } from '../sim/etorProtocol';
import type { CameraPresetId } from '../scene/GraniteViewport';
import type { PcbFinish } from '../scene/proceduralTextures';

interface BottomControlDockProps {
  collapsed: boolean;
  onToggleCollapsed: () => void;
  hwState: HardwareState;
  onRunScenario: (scenario: ScenarioId) => void;
  exploded: number;
  onExplodedChange: (val: number) => void;
  cameraPreset: CameraPresetId;
  onSelectCamera: (preset: CameraPresetId) => void;
  pcbFinish: PcbFinish;
  onSelectFinish: (finish: PcbFinish) => void;
  onOpenByteMap: () => void;
  onOpenSnapshotStudio: () => void;
}

const SCENARIOS: { id: ScenarioId; key: string; label: string }[] = [
  { id: 'reset_sequencer', key: '1', label: 'Cold Boot' },
  { id: 'valid_commit', key: '2', label: 'Valid 242B' },
  { id: 'tampered_byte54', key: '3', label: 'Tamper B54' },
  { id: 'l01_manual_reset', key: '4', label: 'L01 Reset' },
];

const CAMERAS: { id: CameraPresetId; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'die_closeup', label: 'SG48 Die' },
  { id: 'uart_bus', label: 'UART RX' },
  { id: 'crowbar_rail', label: 'Crowbar' },
];

const FINISHES: { id: PcbFinish; label: string }[] = [
  { id: 'obsidian', label: 'Obsidian' },
  { id: 'mineral_slate', label: 'Slate' },
  { id: 'enamel_green', label: 'Enamel' },
];

export function BottomControlDock({
  collapsed,
  onToggleCollapsed,
  hwState,
  onRunScenario,
  exploded,
  onExplodedChange,
  cameraPreset,
  onSelectCamera,
  pcbFinish,
  onSelectFinish,
  onOpenByteMap,
  onOpenSnapshotStudio,
}: BottomControlDockProps) {
  if (collapsed) {
    return (
      <div className="fixed bottom-4 right-5 z-20">
        <button
          type="button"
          onClick={onToggleCollapsed}
          className="px-3 py-1.5 text-xs font-mono tracking-wide text-slate-200 bg-[#171C24]/90 border border-slate-700/80 hover:border-slate-500 transition-colors"
        >
          Controls [H]
        </button>
      </div>
    );
  }

  return (
    <aside
      aria-label="Hardware Control Dock"
      className="fixed bottom-4 left-1/2 -translate-x-1/2 z-20 w-[min(960px,95vw)] bg-[#151A22]/92 backdrop-blur-md border border-slate-700/80 px-4 py-3 text-xs text-slate-200 font-mono"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Scenarios 1..4 */}
        <div className="flex flex-wrap items-center gap-1.5">
          {SCENARIOS.map((s) => {
            const active = hwState.lastScenario === s.id;
            return (
              <button
                key={s.id}
                type="button"
                onClick={() => onRunScenario(s.id)}
                className={`px-2.5 py-1.5 border transition-colors ${
                  active
                    ? 'border-amber-400/80 bg-amber-500/15 text-amber-200'
                    : 'border-slate-700 bg-slate-900/60 text-slate-300 hover:border-slate-500'
                }`}
              >
                <span className="text-slate-500 mr-1">[{s.key}]</span>
                {s.label}
              </button>
            );
          })}
        </div>

        {/* Exploded slider */}
        <label className="flex items-center gap-2 text-slate-400">
          <span>EXPLODE</span>
          <input
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={exploded}
            onChange={(e) => onExplodedChange(Number(e.target.value))}
            className="w-24 accent-amber-400"
          />
          <span className="w-8 text-right tabular-nums text-slate-300">
            {Math.round(exploded * 100)}%
          </span>
        </label>

        {/* Modals & Collapse */}
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={onOpenByteMap}
            className="px-2.5 py-1.5 border border-slate-700 bg-slate-900/60 hover:border-slate-500 text-slate-200"
          >
            242B Map
          </button>
          <button
            type="button"
            onClick={onOpenSnapshotStudio}
            className="px-2.5 py-1.5 border border-slate-700 bg-slate-900/60 hover:border-slate-500 text-slate-200"
          >
            Plate Studio
          </button>
          <button
            type="button"
            onClick={onToggleCollapsed}
            title="Toggle Zen mode (H)"
            className="px-2 py-1.5 border border-slate-700/80 text-slate-400 hover:text-slate-200"
          >
            [H]
          </button>
        </div>
      </div>

      {/* Secondary row: Camera presets, PCB finish, Live hardware telemetry */}
      <div className="mt-2.5 pt-2 border-t border-slate-800/90 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-400">
        <div className="flex items-center gap-1">
          <span className="mr-1 text-slate-500">CAM:</span>
          {CAMERAS.map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => onSelectCamera(c.id)}
              className={`px-2 py-0.5 border ${
                cameraPreset === c.id
                  ? 'border-slate-400 text-white bg-slate-800'
                  : 'border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1">
          <span className="mr-1 text-slate-500">PCB:</span>
          {FINISHES.map((f) => (
            <button
              key={f.id}
              type="button"
              onClick={() => onSelectFinish(f.id)}
              className={`px-2 py-0.5 border ${
                pcbFinish === f.id
                  ? 'border-slate-400 text-white bg-slate-800'
                  : 'border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className="tabular-nums text-slate-300">
          VALVE={hwState.valveEnableOut ? '1' : '0'} · CROWBAR={hwState.crowbarTripOut ? '1' : '0'} ·
          0xAA={hwState.dualRailOk ? 'OK' : 'BREACH'} · SEQ={hwState.seqId}
        </div>
      </div>
    </aside>
  );
}
