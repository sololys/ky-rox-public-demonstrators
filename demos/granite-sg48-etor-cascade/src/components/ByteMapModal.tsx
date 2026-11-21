import { useEffect, useRef } from 'react';
import { FRAME_REGIONS, type BusRegionId } from '../sim/etorProtocol';

interface ByteMapModalProps {
  open: boolean;
  onClose: () => void;
  frame: Uint8Array;
  highlightedRegion: BusRegionId | null;
  onSelectRegion: (region: BusRegionId | null) => void;
}

function getRegionForByte(index: number) {
  return FRAME_REGIONS.find((r) => index >= r.startByte && index <= r.endByte) ?? null;
}

export function ByteMapModal({
  open,
  onClose,
  frame,
  highlightedRegion,
  onSelectRegion,
}: ByteMapModalProps) {
  const dialogRef = useRef<HTMLDialogElement | null>(null);

  useEffect(() => {
    const dlg = dialogRef.current;
    if (!dlg) return;
    if (open && !dlg.open) {
      dlg.showModal();
    } else if (!open && dlg.open) {
      dlg.close();
    }
  }, [open]);

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      onClick={(e) => {
        if (e.target === dialogRef.current) onClose();
      }}
      className="w-[min(860px,94vw)] max-h-[86vh] bg-[#141920] text-slate-100 border border-slate-700 p-0 font-mono"
    >
      <div className="p-5 flex flex-col gap-4 max-h-[86vh] overflow-y-auto">
        <div className="flex items-start justify-between gap-4 border-b border-slate-800 pb-3">
          <div>
            <h2 className="text-sm font-semibold tracking-wide text-white">
              242-BYTE UART FRAME &amp; SPOR A / SPOR B TAP MAP
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              37B Bind X Header + 119B WitnessPreCommit + 86B WitnessPostCommit (Little-Endian)
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

        {/* Region legend buttons */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {FRAME_REGIONS.map((reg) => {
            const selected = highlightedRegion === reg.id;
            return (
              <button
                key={reg.id}
                type="button"
                onClick={() => onSelectRegion(selected ? null : reg.id)}
                className={`text-left p-2.5 border transition-colors ${
                  selected
                    ? 'border-amber-400 bg-slate-800/90'
                    : 'border-slate-800 bg-slate-900/50 hover:border-slate-600'
                }`}
              >
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold" style={{ color: reg.accent }}>
                    {reg.label}
                  </span>
                  <span className="text-slate-400 tabular-nums">
                    B{reg.startByte}..{reg.endByte} ({reg.endByte - reg.startByte + 1}B)
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1 leading-snug">{reg.role}</p>
              </button>
            );
          })}
        </div>

        {/* Hex grid of all 242 bytes */}
        <div className="grid grid-cols-11 sm:grid-cols-16 gap-1 text-[10px] tabular-nums bg-[#0E1217] p-3 border border-slate-800">
          {Array.from(frame).map((byteVal, idx) => {
            const reg = getRegionForByte(idx);
            const isHi = reg && highlightedRegion === reg.id;
            return (
              <div
                key={idx}
                title={`Byte ${idx}: 0x${byteVal.toString(16).padStart(2, '0').toUpperCase()}${
                  reg ? ` (${reg.label})` : ''
                }`}
                className={`px-1 py-0.5 text-center border ${
                  isHi
                    ? 'border-amber-400 bg-amber-500/20 text-amber-100'
                    : reg
                      ? 'border-slate-800 bg-slate-900/80 text-slate-200'
                      : 'border-transparent text-slate-600'
                }`}
                style={reg && !isHi ? { borderColor: `${reg.accent}44` } : undefined}
              >
                {byteVal.toString(16).padStart(2, '0').toUpperCase()}
              </div>
            );
          })}
        </div>
      </div>
    </dialog>
  );
}
