import * as THREE from 'three';

export type PcbFinish = 'obsidian' | 'mineral_slate' | 'enamel_green';

interface FinishPalette {
  base: string;
  trace: string;
  silkscreen: string;
}

const PALETTES: Record<PcbFinish, FinishPalette> = {
  obsidian: {
    base: '#161A20',
    trace: '#2B3440',
    silkscreen: '#C8C1B4',
  },
  mineral_slate: {
    base: '#28313B',
    trace: '#3E4C5B',
    silkscreen: '#E6E1D6',
  },
  enamel_green: {
    base: '#16342A',
    trace: '#245243',
    silkscreen: '#DFD8C8',
  },
};

export function createPcbTexture(finish: PcbFinish): THREE.CanvasTexture {
  const palette = PALETTES[finish];
  const canvas = document.createElement('canvas');
  canvas.width = 1024;
  canvas.height = 1024;
  const ctx = canvas.getContext('2d')!;

  ctx.fillStyle = palette.base;
  ctx.fillRect(0, 0, 1024, 1024);

  // Subtle Ulm-grid copper bus traces
  ctx.strokeStyle = palette.trace;
  ctx.lineWidth = 3;
  for (let i = 64; i < 960; i += 48) {
    ctx.beginPath();
    ctx.moveTo(48, i);
    ctx.lineTo(976, i);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(i, 48);
    ctx.lineTo(i, 976);
    ctx.stroke();
  }

  // Diagonal 45-degree bus fanout from SG48 QFN center
  ctx.strokeStyle = '#6A5B3E';
  ctx.lineWidth = 4;
  for (let k = -6; k <= 6; k++) {
    const off = k * 28;
    ctx.beginPath();
    ctx.moveTo(512 + off, 512 - 140);
    ctx.lineTo(512 + off * 1.6, 150);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(512 + off, 512 + 140);
    ctx.lineTo(512 + off * 1.6, 874);
    ctx.stroke();
  }

  // Engraved silkscreen border & fiducials
  ctx.strokeStyle = palette.silkscreen;
  ctx.lineWidth = 2;
  ctx.strokeRect(28, 28, 968, 968);

  ctx.fillStyle = palette.silkscreen;
  ctx.font = '600 22px monospace';
  ctx.fillText('GRANITE SG48 // E-TOR OMNI CASCADE (SPOR A)', 52, 76);
  ctx.font = '400 18px monospace';
  ctx.fillText('iCE40UP5K-SG48 · 12 MHz · 4648/5280 LC · 3/8 DSP · 26.22 MHz STA', 52, 972);

  const tex = new THREE.CanvasTexture(canvas);
  tex.anisotropy = 4;
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

export function createPackageTopTexture(): THREE.CanvasTexture {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 512;
  const ctx = canvas.getContext('2d')!;

  ctx.fillStyle = '#1D2024';
  ctx.fillRect(0, 0, 512, 512);

  // Pin-1 laser dot
  ctx.fillStyle = '#D6CFC0';
  ctx.beginPath();
  ctx.arc(64, 64, 16, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = '#CFC8B8';
  ctx.font = '700 34px monospace';
  ctx.fillText('LATTICE', 110, 195);
  ctx.font = '600 30px monospace';
  ctx.fillText('iCE40UP5K', 110, 245);
  ctx.fillText('SG48-I', 110, 290);
  ctx.font = '400 22px monospace';
  ctx.fillStyle = '#9EA4AC';
  ctx.fillText('E-TOR // 0xAA', 110, 355);
  ctx.fillText('L1.5 MODEL', 110, 390);

  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}
