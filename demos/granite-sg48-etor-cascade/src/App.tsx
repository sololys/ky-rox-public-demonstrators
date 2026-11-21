import { useCallback, useEffect, useRef, useState } from 'react';
import {
  build242ByteFrame,
  createInitialHardwareState,
  runScenario,
  type BusRegionId,
  type HardwareState,
  type ScenarioId,
} from './sim/etorProtocol';
import {
  GraniteViewport,
  type CameraPresetId,
  type GraniteViewportHandle,
} from './scene/GraniteViewport';
import type { PcbFinish } from './scene/proceduralTextures';
import { BottomControlDock } from './components/BottomControlDock';
import { ByteMapModal } from './components/ByteMapModal';
import { SnapshotStudioModal } from './components/SnapshotStudioModal';

interface SimSnapshot {
  hwState: HardwareState;
  currentFrame: Uint8Array;
}

export default function App() {
  const viewportRef = useRef<GraniteViewportHandle | null>(null);

  const [sim, setSim] = useState<SimSnapshot>(() => ({
    hwState: createInitialHardwareState(),
    currentFrame: build242ByteFrame({ token: 0x5c, tamperByte54: false }),
  }));
  const [exploded, setExploded] = useState<number>(0.55);
  const [cameraPreset, setCameraPreset] = useState<CameraPresetId>('overview');
  const [cameraPresetTrigger, setCameraPresetTrigger] = useState<number>(0);
  const [pcbFinish, setPcbFinish] = useState<PcbFinish>('obsidian');
  const [highlightedRegion, setHighlightedRegion] = useState<BusRegionId | null>(null);

  const [dockCollapsed, setDockCollapsed] = useState<boolean>(false);
  const [byteMapOpen, setByteMapOpen] = useState<boolean>(false);
  const [studioOpen, setStudioOpen] = useState<boolean>(false);

  const handleRunScenario = useCallback((scenario: ScenarioId) => {
    setSim((prev) => {
      const result = runScenario(prev.hwState, scenario);
      return { hwState: result.state, currentFrame: result.frame };
    });
  }, []);

  const handleSelectCamera = useCallback((preset: CameraPresetId) => {
    setCameraPreset(preset);
    setCameraPresetTrigger((n) => n + 1);
  }, []);

  const handleCaptureViewport = useCallback(() => {
    return viewportRef.current?.capturePngDataUrl() ?? null;
  }, []);

  // Keyboard shortcuts: H toggles Zen mode, 1..4 trigger scenarios, Escape closes modals
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return;
      }
      if (e.key === 'Escape') {
        setByteMapOpen(false);
        setStudioOpen(false);
        return;
      }
      if (e.key === 'h' || e.key === 'H') {
        setDockCollapsed((c) => !c);
      } else if (e.key === '1') {
        handleRunScenario('reset_sequencer');
      } else if (e.key === '2') {
        handleRunScenario('valid_commit');
      } else if (e.key === '3') {
        handleRunScenario('tampered_byte54');
      } else if (e.key === '4') {
        handleRunScenario('l01_manual_reset');
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [handleRunScenario]);

  const { hwState, currentFrame } = sim;

  return (
    <main
      className="relative w-screen h-screen overflow-hidden bg-[#11151B]"
      data-hw-state={hwState.grayState}
      data-valve-enable={hwState.valveEnableOut}
      data-crowbar-trip={hwState.crowbarTripOut}
    >
      {/* Full-bleed 3D Hardware Viewport */}
      <GraniteViewport
        ref={viewportRef}
        exploded={exploded}
        cameraPreset={cameraPreset}
        cameraPresetTrigger={cameraPresetTrigger}
        pcbFinish={pcbFinish}
        hwState={hwState}
        highlightedRegion={highlightedRegion}
      />

      {/* Minimal Top-Left Title & Unboxed Status Line (Zero viewport clutter, zero pills) */}
      <header className="fixed top-5 left-6 z-20 pointer-events-none select-none max-w-[min(460px,82vw)]">
        <h1 className="text-lg sm:text-xl font-semibold tracking-tight text-white">
          Granite SG48 E-TOR Cascade
        </h1>
        <p className="mt-0.5 text-xs text-slate-400 font-mono tabular-nums">
          iCE40 UP5K-SG48 · 12 MHz · 242B UART · {hwState.statusHeadline}
        </p>
        <p className="mt-1 text-xs text-slate-400/90 hidden sm:block">
          {hwState.statusDetail}
        </p>
      </header>

      {/* Unified Collapsible Bottom Control Dock */}
      <BottomControlDock
        collapsed={dockCollapsed}
        onToggleCollapsed={() => setDockCollapsed((c) => !c)}
        hwState={hwState}
        onRunScenario={handleRunScenario}
        exploded={exploded}
        onExplodedChange={setExploded}
        cameraPreset={cameraPreset}
        onSelectCamera={handleSelectCamera}
        pcbFinish={pcbFinish}
        onSelectFinish={setPcbFinish}
        onOpenByteMap={() => setByteMapOpen(true)}
        onOpenSnapshotStudio={() => setStudioOpen(true)}
      />

      {/* Interactive 242B Frame & Spor B Byte Map Modal */}
      <ByteMapModal
        open={byteMapOpen}
        onClose={() => setByteMapOpen(false)}
        frame={currentFrame}
        highlightedRegion={highlightedRegion}
        onSelectRegion={setHighlightedRegion}
      />

      {/* Technical Snapshot & Local Plate Editor Studio */}
      <SnapshotStudioModal
        open={studioOpen}
        onClose={() => setStudioOpen(false)}
        onCaptureViewport={handleCaptureViewport}
        hwState={hwState}
      />
    </main>
  );
}
