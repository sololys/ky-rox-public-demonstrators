// Bit-faithful L1/L1.5 browser model of granite_sg48_etor_cascade_top.sv
// Evidence boundary: INSPIRED_BY != IMPLEMENTS != PROVES (0.00 V DC physical authority).

export type GrayState =
  | 'RAW (000)'
  | 'ESTIMATE (001)'
  | 'STRUCT (011)'
  | 'AUTHORIZED (010)'
  | 'COMMITTED (110)'
  | 'SCRAM (111)';

export type ScenarioId =
  | 'reset_sequencer'
  | 'valid_commit'
  | 'tampered_byte54'
  | 'l01_manual_reset';

export type BusRegionId =
  | 'bind_x'
  | 'seq_id'
  | 'etor_tap'
  | 'phronesis_spor_b'
  | 'w_pre_hash'
  | 'w_post_commit';

export interface BusRegionMeta {
  id: BusRegionId;
  label: string;
  startByte: number;
  endByte: number;
  role: string;
  accent: string;
}

export const FRAME_REGIONS: BusRegionMeta[] = [
  {
    id: 'bind_x',
    label: 'Bind X Header',
    startByte: 0,
    endByte: 36,
    role: '37B Gödel-Moreau consequence header (u_ppm, xi_budget, paid_work, collar, flags)',
    accent: '#94A3B8',
  },
  {
    id: 'seq_id',
    label: 'Monotonic Seq ID',
    startByte: 37,
    endByte: 44,
    role: '8B little-endian anti-replay sequence_id (bytes 37..39 logged to BRAM4K)',
    accent: '#60A5FA',
  },
  {
    id: 'etor_tap',
    label: 'E-TOR 3B Tap (Spor A)',
    startByte: 53,
    endByte: 55,
    role: 'Byte 53 token_byte, Byte 54 token_inv (x ^ 0xAA), Byte 55 Gray target — committed atomically on sg48_eval_done',
    accent: '#E2B76B',
  },
  {
    id: 'phronesis_spor_b',
    label: 'Phronesis 14B Tap (Spor B)',
    startByte: 56,
    endByte: 69,
    role: 'Reserved 14B (7x 16-bit LE: rho_diag0..3, e+, e-, tof_ns) for 5-DSP Phronesis gate',
    accent: '#7DD3FC',
  },
  {
    id: 'w_pre_hash',
    label: 'WitnessPreCommit Hash',
    startByte: 124,
    endByte: 155,
    role: '32B w_pre_hash verified bit-for-bit against WitnessPostCommit bytes 172..203',
    accent: '#A78BFA',
  },
  {
    id: 'w_post_commit',
    label: 'WitnessPostCommit',
    startByte: 156,
    endByte: 241,
    role: '86B post-commit envelope (seq_id, w_pre_hash, HPIS latch, f32 exhaust, w_post_hash)',
    accent: '#6EE7B7',
  },
];

export interface HardwareState {
  grayState: GrayState;
  grayCodeBits: string;
  valveEnableOut: boolean;
  crowbarTripOut: boolean;
  bootLocked: boolean;
  trapTamper: boolean;
  blackboxFrozen: boolean;
  tokenByte: number;
  tokenInvByte: number;
  dualRailOk: boolean;
  seqId: number;
  voltageMv: number;
  statusHeadline: string;
  statusDetail: string;
  lastScenario: ScenarioId;
}

export const STA_METRICS = {
  device: 'iCE40UP5K-SG48',
  lcUsed: 4648,
  lcTotal: 5280,
  lcPct: 88,
  dspUsed: 3,
  dspTotal: 8,
  bramUsed: 4,
  bramTotal: 30,
  ioUsed: 16,
  ioTotal: 39,
  icetimeFmaxMhz: 26.22,
  icetimeCritNs: 38.14,
  requiredClockMhz: 12.0,
} as const;

export function build242ByteFrame(opts: {
  token: number;
  tamperByte54: boolean;
  targetBits?: number;
  seqId?: number;
}): Uint8Array {
  const frame = new Uint8Array(242);
  const seq = opts.seqId ?? 4;
  const tok = opts.token & 0xff;
  const inv = opts.tamperByte54 ? ((tok ^ 0xaa) ^ 0x01) & 0xff : (tok ^ 0xaa) & 0xff;
  const target = (opts.targetBits ?? 0b110) & 0x07;

  // Bind X nominal header (bytes 0..36)
  const writeU32LE = (offset: number, val: number) => {
    frame[offset] = val & 0xff;
    frame[offset + 1] = (val >>> 8) & 0xff;
    frame[offset + 2] = (val >>> 16) & 0xff;
    frame[offset + 3] = (val >>> 24) & 0xff;
  };
  writeU32LE(0, 800_000); // u_ppm
  writeU32LE(8, 300_000); // xi_budget
  writeU32LE(24, 2_500); // collar
  frame[36] = 0x06; // evidence_ok=1, h_diode_ok=1, vulcan_en=0

  // Monotonic seq_id in Pre (37..44) and Post (156..163)
  writeU32LE(37, seq);
  writeU32LE(156, seq);

  // E-TOR 3-byte atomic tap (53..55)
  frame[53] = tok;
  frame[54] = inv;
  frame[55] = target;

  // Spor B Phronesis 14-byte sample (56..69): rho0=0xFFFF, e+=0xFFFF, e-=0x0000, tof=83ns
  frame[56] = 0xff;
  frame[57] = 0xff;
  frame[64] = 0xff;
  frame[65] = 0xff;
  frame[68] = 83;
  frame[69] = 0;

  // WitnessPreCommit gate_decision = OPEN (0x01) at 37 + 52 = 89
  frame[89] = 0x01;

  // Deterministic w_pre_hash mirrored at 124..155 and 172..203
  for (let i = 0; i < 32; i++) {
    const b = (0x79 + i * 17) & 0xff;
    frame[124 + i] = b;
    frame[172 + i] = b;
  }

  // WitnessPostCommit HPIS latch (204), positive f32 thermo_exhaust (205..208), final_status (209)
  frame[204] = 0x01;
  frame[205] = 0x00;
  frame[206] = 0x00;
  frame[207] = 0x02;
  frame[208] = 0x43;
  frame[209] = 0x01;

  return frame;
}

export function createInitialHardwareState(): HardwareState {
  return {
    grayState: 'RAW (000)',
    grayCodeBits: '000',
    valveEnableOut: false,
    crowbarTripOut: false,
    bootLocked: true,
    trapTamper: false,
    blackboxFrozen: false,
    tokenByte: 0x00,
    tokenInvByte: 0xaa,
    dualRailOk: true,
    seqId: 0,
    voltageMv: 0,
    statusHeadline: 'BOOT_LOCKED · 0.00 V DC',
    statusDetail:
      'Reset Sequencer holds valve_enable_out = 0 until L01 unlock + 8 clean settle cycles.',
    lastScenario: 'reset_sequencer',
  };
}

export function runScenario(
  prev: HardwareState,
  scenario: ScenarioId,
): { state: HardwareState; frame: Uint8Array } {
  if (scenario === 'reset_sequencer') {
    const frame = build242ByteFrame({
      token: 0x00,
      tamperByte54: false,
      targetBits: 0b000,
      seqId: 0,
    });
    return {
      state: createInitialHardwareState(),
      frame,
    };
  }

  if (scenario === 'l01_manual_reset') {
    const frame = build242ByteFrame({
      token: 0x00,
      tamperByte54: false,
      targetBits: 0b000,
      seqId: prev.seqId,
    });
    return {
      state: {
        grayState: 'RAW (000)',
        grayCodeBits: '000',
        valveEnableOut: false,
        crowbarTripOut: false,
        bootLocked: false,
        trapTamper: false,
        blackboxFrozen: false,
        tokenByte: 0x00,
        tokenInvByte: 0xaa,
        dualRailOk: true,
        seqId: prev.seqId,
        voltageMv: 0,
        statusHeadline: 'L01 RESET CLEAN · 0.00 V DC',
        statusDetail:
          'Sticky SCRAM cleared via physical L01 key; counter-locked sequencer released Frisch & E-TOR to RAW (000).',
        lastScenario: 'l01_manual_reset',
      },
      frame,
    };
  }

  if (scenario === 'tampered_byte54') {
    const nextSeq = prev.seqId + 1;
    const frame = build242ByteFrame({
      token: 0x5c,
      tamperByte54: true,
      targetBits: 0b110,
      seqId: nextSeq,
    });
    return {
      state: {
        grayState: 'SCRAM (111)',
        grayCodeBits: '111',
        valveEnableOut: false,
        crowbarTripOut: true,
        bootLocked: false,
        trapTamper: true,
        blackboxFrozen: true,
        tokenByte: frame[53],
        tokenInvByte: frame[54],
        dualRailOk: false,
        seqId: nextSeq,
        voltageMv: 0,
        statusHeadline: 'STICKY SCRAM · CROWBAR 0.00 V DC',
        statusDetail:
          'Byte 54 involution breach (0x5C ^ 0xAA != 0xF7) latched crowbar_trip_out = 1 and froze BRAM4K black-box.',
        lastScenario: 'tampered_byte54',
      },
      frame,
    };
  }

  // scenario === 'valid_commit'
  if (prev.grayState === 'SCRAM (111)') {
    const frame = build242ByteFrame({
      token: 0x5c,
      tamperByte54: false,
      targetBits: 0b110,
      seqId: prev.seqId,
    });
    return {
      state: {
        ...prev,
        statusHeadline: 'SCRAM LATCHED · L01 RESET REQUIRED',
        statusDetail:
          'Valid frame rejected while sticky SCRAM (111) is active. Press [4] L01 Manual Reset first.',
        lastScenario: 'valid_commit',
      },
      frame,
    };
  }

  const nextSeq = Math.max(prev.seqId + 1, 4);
  const frame = build242ByteFrame({
    token: 0x5c,
    tamperByte54: false,
    targetBits: 0b110,
    seqId: nextSeq,
  });
  return {
    state: {
      grayState: 'COMMITTED (110)',
      grayCodeBits: '110',
      valveEnableOut: true,
      crowbarTripOut: false,
      bootLocked: false,
      trapTamper: false,
      blackboxFrozen: false,
      tokenByte: frame[53],
      tokenInvByte: frame[54],
      dualRailOk: true,
      seqId: nextSeq,
      voltageMv: 5000,
      statusHeadline: 'COMMITTED (110) · 5.00 V DC (SIM)',
      statusDetail:
        'Gray ladder RAW→ESTIMATE→STRUCT→AUTHORIZED→COMMITTED verified on sg48_eval_done; valve_enable_out = 1 (L1.5 model).',
      lastScenario: 'valid_commit',
    },
    frame,
  };
}
