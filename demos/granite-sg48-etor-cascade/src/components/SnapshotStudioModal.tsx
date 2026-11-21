import { useEffect, useRef, useState } from 'react';
import { STA_METRICS, type HardwareState } from '../sim/etorProtocol';

interface SnapshotStudioModalProps {
  open: boolean;
  onClose: () => void;
  onCaptureViewport: () => string | null;
  hwState: HardwareState;
}

type PlateGround = 'linen' | 'obsidian';

export function SnapshotStudioModal({
  open,
  onClose,
  onCaptureViewport,
  hwState,
}: SnapshotStudioModalProps) {
  const dialogRef = useRef<HTMLDialogElement | null>(null);
  const [ground, setGround] = useState<PlateGround>('linen');
  const [plateTitle, setPlateTitle] = useState<string>(
    'PLATE I — GRANITE SG48 E-TOR OMNI CASCADE (SPOR A)',
  );
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  useEffect(() => {
    const dlg = dialogRef.current;
    if (!dlg) return;
    if (open && !dlg.open) {
      dlg.showModal();
      setPreviewUrl(onCaptureViewport());
    } else if (!open && dlg.open) {
      dlg.close();
    }
  }, [open, onCaptureViewport]);

  const handleDownloadPlate = () => {
    if (!previewUrl) return;
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = 1400;
      canvas.height = 960;
      const ctx = canvas.getContext('2d')!;

      const isLinen = ground === 'linen';
      ctx.fillStyle = isLinen ? '#E6E1D6' : '#11151B';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      ctx.strokeStyle = isLinen ? '#3B3730' : '#475569';
      ctx.lineWidth = 2;
      ctx.strokeRect(32, 32, canvas.width - 64, canvas.height - 64);

      ctx.drawImage(img, 56, 96, 1288, 700);

      ctx.fillStyle = isLinen ? '#1C1B18' : '#E2E8F0';
      ctx.font = '600 22px Georgia, serif';
      ctx.fillText(plateTitle, 56, 74);

      ctx.font = '400 16px monospace';
      ctx.fillStyle = isLinen ? '#423E37' : '#94A3B8';
      ctx.fillText(
        `${STA_METRICS.device} · ${STA_METRICS.lcUsed}/${STA_METRICS.lcTotal} LC (${STA_METRICS.lcPct}%) · ${STA_METRICS.dspUsed}/${STA_METRICS.dspTotal} DSP · ${STA_METRICS.ioUsed}/${STA_METRICS.ioTotal} IO · ${STA_METRICS.icetimeFmaxMhz} MHz STA`,
        56,
        844,
      );
      ctx.fillText(
        `STATE=${hwState.grayState} · VALVE=${hwState.valveEnableOut ? '1' : '0'} · CROWBAR=${
          hwState.crowbarTripOut ? '1' : '0'
        } · INSPIRED_BY != IMPLEMENTS != PROVES (L1.5 MODEL, 0.00 V DC PHYSICAL)`,
        56,
        878,
      );

      const link = document.createElement('a');
      link.download = 'granite_sg48_etor_cascade_plate.png';
      link.href = canvas.toDataURL('image/png');
      link.click();
    };
    img.src = previewUrl;
  };

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      onClick={(e) => {
        if (e.target === dialogRef.current) onClose();
      }}
      className="w-[min(780px,94vw)] bg-[#141920] text-slate-100 border border-slate-700 p-0 font-mono"
    >
      <div className="p-5 flex flex-col gap-4">
        <div className="flex items-start justify-between border-b border-slate-800 pb-3">
          <div>
            <h2 className="text-sm font-semibold tracking-wide text-white">
              ARCHIVAL PLATE STUDIO
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Composite WebGL capture onto mineral linen (#E6E1D6) or obsidian plate
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="px-2.5 py-1 text-xs border border-slate-700 text-slate-300 hover:border-slate-500"
          >
            Close [Esc]
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-3 text-xs">
          <input
            type="text"
            value={plateTitle}
            onChange={(e) => setPlateTitle(e.target.value)}
            className="flex-1 min-w-[240px] bg-slate-900 border border-slate-700 px-2.5 py-1.5 text-slate-100"
          />
          <div className="flex items-center gap-1">
            {(['linen', 'obsidian'] as PlateGround[]).map((g) => (
              <button
                key={g}
                type="button"
                onClick={() => setGround(g)}
                className={`px-2.5 py-1.5 border ${
                  ground === g
                    ? 'border-amber-400 text-amber-200 bg-amber-500/10'
                    : 'border-slate-700 text-slate-400'
                }`}
              >
                {g === 'linen' ? 'Linen #E6E1D6' : 'Obsidian'}
              </button>
            ))}
          </div>
        </div>

        <div
          className="border border-slate-800 p-3 flex items-center justify-center min-h-[260px]"
          style={{ backgroundColor: ground === 'linen' ? '#E6E1D6' : '#11151B' }}
        >
          {previewUrl ? (
            <img
              src={previewUrl}
              alt="Viewport snapshot preview"
              className="max-h-[340px] object-contain border border-slate-700/60"
            />
          ) : (
            <span className="text-xs text-slate-500">No viewport frame captured.</span>
          )}
        </div>

        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={() => setPreviewUrl(onCaptureViewport())}
            className="px-3 py-1.5 text-xs border border-slate-700 text-slate-300 hover:border-slate-500"
          >
            Recapture Viewport
          </button>
          <button
            type="button"
            onClick={handleDownloadPlate}
            disabled={!previewUrl}
            className="px-3.5 py-1.5 text-xs border border-amber-400/80 bg-amber-500/15 text-amber-100 hover:bg-amber-500/25 disabled:opacity-40"
          >
            Export Archival PNG
          </button>
        </div>
      </div>
    </dialog>
  );
}
