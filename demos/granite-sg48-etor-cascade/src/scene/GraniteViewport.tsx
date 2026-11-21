import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
} from 'react';
import * as THREE from 'three';
import type { BusRegionId, HardwareState } from '../sim/etorProtocol';
import {
  createPackageTopTexture,
  createPcbTexture,
  type PcbFinish,
} from './proceduralTextures';

export type CameraPresetId = 'overview' | 'die_closeup' | 'uart_bus' | 'crowbar_rail';

export interface GraniteViewportHandle {
  capturePngDataUrl: () => string | null;
}

interface GraniteViewportProps {
  exploded: number;
  cameraPreset: CameraPresetId;
  cameraPresetTrigger: number;
  pcbFinish: PcbFinish;
  hwState: HardwareState;
  highlightedRegion: BusRegionId | null;
}

const CAMERA_PRESETS: Record<
  CameraPresetId,
  { spherical: [number, number, number]; target: [number, number, number] }
> = {
  overview: { spherical: [8.8, 0.92, 0.65], target: [0, 0.35, 0] },
  die_closeup: { spherical: [4.4, 0.68, 0.35], target: [0, 0.95, 0] },
  uart_bus: { spherical: [6.2, 1.05, -0.85], target: [-1.4, 0.4, 0.2] },
  crowbar_rail: { spherical: [5.8, 0.95, 1.35], target: [1.5, 0.45, 0.0] },
};

export const GraniteViewport = forwardRef<GraniteViewportHandle, GraniteViewportProps>(
  function GraniteViewport(
    {
      exploded,
      cameraPreset,
      cameraPresetTrigger,
      pcbFinish,
      hwState,
      highlightedRegion,
    },
    ref,
  ) {
    const containerRef = useRef<HTMLDivElement | null>(null);
    const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
    const sceneRef = useRef<THREE.Scene | null>(null);
    const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);

    const stateRef = useRef({ exploded, hwState, highlightedRegion });
    stateRef.current = { exploded, hwState, highlightedRegion };

    const orbitRef = useRef({
      radius: CAMERA_PRESETS.overview.spherical[0],
      phi: CAMERA_PRESETS.overview.spherical[1],
      theta: CAMERA_PRESETS.overview.spherical[2],
      targetRadius: CAMERA_PRESETS.overview.spherical[0],
      targetPhi: CAMERA_PRESETS.overview.spherical[1],
      targetTheta: CAMERA_PRESETS.overview.spherical[2],
      lookAt: new THREE.Vector3(...CAMERA_PRESETS.overview.target),
      targetLookAt: new THREE.Vector3(...CAMERA_PRESETS.overview.target),
      dragging: false,
      lastX: 0,
      lastY: 0,
    });

    const pcbMaterialRef = useRef<THREE.MeshStandardMaterial | null>(null);

    useImperativeHandle(ref, () => ({
      capturePngDataUrl: () => {
        const renderer = rendererRef.current;
        const scene = sceneRef.current;
        const camera = cameraRef.current;
        if (!renderer || !scene || !camera) return null;
        renderer.render(scene, camera);
        return renderer.domElement.toDataURL('image/png');
      },
    }));

    // Apply camera preset transitions
    useEffect(() => {
      const preset = CAMERA_PRESETS[cameraPreset];
      orbitRef.current.targetRadius = preset.spherical[0];
      orbitRef.current.targetPhi = preset.spherical[1];
      orbitRef.current.targetTheta = preset.spherical[2];
      orbitRef.current.targetLookAt.set(...preset.target);
    }, [cameraPreset, cameraPresetTrigger]);

    // Update PCB finish texture cleanly
    useEffect(() => {
      const mat = pcbMaterialRef.current;
      if (!mat) return;
      const prevMap = mat.map;
      mat.map = createPcbTexture(pcbFinish);
      mat.needsUpdate = true;
      prevMap?.dispose();
    }, [pcbFinish]);

    useEffect(() => {
      const container = containerRef.current;
      if (!container) return;

      const scene = new THREE.Scene();
      scene.background = new THREE.Color('#11151B');
      sceneRef.current = scene;

      const camera = new THREE.PerspectiveCamera(
        40,
        container.clientWidth / Math.max(1, container.clientHeight),
        0.1,
        100,
      );
      cameraRef.current = camera;

      const renderer = new THREE.WebGLRenderer({
        antialias: true,
        preserveDrawingBuffer: true,
      });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.setSize(container.clientWidth, container.clientHeight);
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.1;
      container.appendChild(renderer.domElement);
      rendererRef.current = renderer;

      // Studio lighting (sober, architectural)
      const ambient = new THREE.AmbientLight('#D8E0EA', 0.65);
      scene.add(ambient);

      const keyLight = new THREE.DirectionalLight('#FFF6E8', 1.45);
      keyLight.position.set(6, 10, 7);
      scene.add(keyLight);

      const rimLight = new THREE.DirectionalLight('#8AB4F8', 0.55);
      rimLight.position.set(-7, 5, -6);
      scene.add(rimLight);

      // Layer 0: Base FR-4 PCB Substrate
      const pcbGroup = new THREE.Group();
      const pcbMat = new THREE.MeshStandardMaterial({
        map: createPcbTexture(pcbFinish),
        roughness: 0.55,
        metalness: 0.15,
      });
      pcbMaterialRef.current = pcbMat;
      const pcbMesh = new THREE.Mesh(new THREE.BoxGeometry(6.4, 0.18, 4.8), pcbMat);
      pcbGroup.add(pcbMesh);

      // 16 physical SG48 header pins along left & right rails
      const pinGeo = new THREE.CylinderGeometry(0.055, 0.055, 0.42, 12);
      const pinMat = new THREE.MeshStandardMaterial({
        color: '#D4B06A',
        metalness: 0.85,
        roughness: 0.25,
      });
      for (let i = 0; i < 8; i++) {
        const z = -1.75 + i * 0.5;
        const leftPin = new THREE.Mesh(pinGeo, pinMat);
        leftPin.position.set(-2.85, 0.18, z);
        pcbGroup.add(leftPin);

        const rightPin = new THREE.Mesh(pinGeo, pinMat);
        rightPin.position.set(2.85, 0.18, z);
        pcbGroup.add(rightPin);
      }
      scene.add(pcbGroup);

      // Layer 1: Silicon Die Architecture (Bind X, 205B, E-TOR 0xAA, Frisch, BRAM4K)
      const dieGroup = new THREE.Group();
      const makeBlock = (
        w: number,
        h: number,
        d: number,
        color: string,
        x: number,
        z: number,
      ) => {
        const mat = new THREE.MeshStandardMaterial({
          color,
          roughness: 0.35,
          metalness: 0.55,
          emissive: new THREE.Color('#000000'),
          emissiveIntensity: 0.45,
        });
        const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
        mesh.position.set(x, 0, z);
        dieGroup.add(mesh);
        return { mesh, mat };
      };

      const bindXBlock = makeBlock(1.15, 0.22, 0.95, '#64748B', -0.95, -0.65);
      const etorBlock = makeBlock(1.05, 0.24, 0.95, '#C89B4B', 0.0, 0.65);
      const phronesisBlock = makeBlock(0.95, 0.18, 0.72, '#38BDF8', -1.05, 0.72);
      const frischBlock = makeBlock(1.15, 0.22, 0.95, '#475569', 0.95, -0.65);
      const bramBlock = makeBlock(0.95, 0.20, 0.72, '#7C6FB0', 1.05, 0.72);
      scene.add(dieGroup);

      // Layer 2: QFN-48 Lattice iCE40UP5K-SG48 Package Lid
      const lidGroup = new THREE.Group();
      const topTex = createPackageTopTexture();
      const lidSideMat = new THREE.MeshStandardMaterial({
        color: '#20242A',
        roughness: 0.6,
        metalness: 0.2,
      });
      const lidTopMat = new THREE.MeshStandardMaterial({
        map: topTex,
        roughness: 0.5,
        metalness: 0.15,
      });
      const lidMesh = new THREE.Mesh(new THREE.BoxGeometry(2.6, 0.26, 2.6), [
        lidSideMat,
        lidSideMat,
        lidTopMat,
        lidSideMat,
        lidSideMat,
        lidSideMat,
      ]);
      lidGroup.add(lidMesh);
      scene.add(lidGroup);

      // Layer 3: Galvanic Consequence Rail (5.00 V OPEN / 0.00 V HOLD / Crowbar SCRAM)
      const railGroup = new THREE.Group();
      const railMat = new THREE.MeshStandardMaterial({
        color: '#94A3B8',
        roughness: 0.3,
        metalness: 0.7,
        emissive: new THREE.Color('#000000'),
        emissiveIntensity: 0.65,
      });
      const railBar = new THREE.Mesh(new THREE.BoxGeometry(2.1, 0.12, 0.28), railMat);
      railBar.position.set(1.75, 0.22, 0);
      railGroup.add(railBar);

      const crowbarMat = new THREE.MeshStandardMaterial({
        color: '#334155',
        roughness: 0.4,
        metalness: 0.6,
        emissive: new THREE.Color('#000000'),
        emissiveIntensity: 0.7,
      });
      const crowbarRelay = new THREE.Mesh(new THREE.BoxGeometry(0.65, 0.32, 0.9), crowbarMat);
      crowbarRelay.position.set(2.2, 0.28, -1.25);
      railGroup.add(crowbarRelay);
      scene.add(railGroup);

      // Pointer drag & wheel zoom
      const dom = renderer.domElement;
      const onPointerDown = (e: PointerEvent) => {
        orbitRef.current.dragging = true;
        orbitRef.current.lastX = e.clientX;
        orbitRef.current.lastY = e.clientY;
        dom.setPointerCapture(e.pointerId);
      };
      const onPointerMove = (e: PointerEvent) => {
        if (!orbitRef.current.dragging) return;
        const dx = e.clientX - orbitRef.current.lastX;
        const dy = e.clientY - orbitRef.current.lastY;
        orbitRef.current.lastX = e.clientX;
        orbitRef.current.lastY = e.clientY;
        orbitRef.current.targetTheta -= dx * 0.007;
        orbitRef.current.targetPhi = Math.max(
          0.22,
          Math.min(1.42, orbitRef.current.targetPhi - dy * 0.007),
        );
      };
      const onPointerUp = (e: PointerEvent) => {
        orbitRef.current.dragging = false;
        if (dom.hasPointerCapture(e.pointerId)) {
          dom.releasePointerCapture(e.pointerId);
        }
      };
      const onWheel = (e: WheelEvent) => {
        e.preventDefault();
        orbitRef.current.targetRadius = Math.max(
          3.2,
          Math.min(14.0, orbitRef.current.targetRadius + e.deltaY * 0.005),
        );
      };

      dom.addEventListener('pointerdown', onPointerDown);
      dom.addEventListener('pointermove', onPointerMove);
      dom.addEventListener('pointerup', onPointerUp);
      dom.addEventListener('wheel', onWheel, { passive: false });

      const onResize = () => {
        if (!container) return;
        const w = container.clientWidth;
        const h = Math.max(1, container.clientHeight);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        renderer.setSize(w, h);
      };
      window.addEventListener('resize', onResize);

      let rafId = 0;
      const animate = () => {
        rafId = requestAnimationFrame(animate);
        const { exploded: exp, hwState: hw, highlightedRegion: hi } = stateRef.current;

        // Smooth camera interpolation
        const o = orbitRef.current;
        o.radius += (o.targetRadius - o.radius) * 0.1;
        o.phi += (o.targetPhi - o.phi) * 0.1;
        o.theta += (o.targetTheta - o.theta) * 0.1;
        o.lookAt.lerp(o.targetLookAt, 0.1);

        camera.position.set(
          o.lookAt.x + o.radius * Math.sin(o.phi) * Math.sin(o.theta),
          o.lookAt.y + o.radius * Math.cos(o.phi),
          o.lookAt.z + o.radius * Math.sin(o.phi) * Math.cos(o.theta),
        );
        camera.lookAt(o.lookAt);

        // Exploded vertical separation
        dieGroup.position.y = 0.22 + exp * 0.85;
        lidGroup.position.y = 0.25 + exp * 1.95;
        railGroup.position.y = exp * 0.42;

        // Hardware state lighting
        if (hw.crowbarTripOut) {
          railMat.emissive.set('#DC2626');
          crowbarMat.emissive.set('#EF4444');
          etorBlock.mat.emissive.set('#B91C1C');
          frischBlock.mat.emissive.set('#991B1B');
        } else if (hw.valveEnableOut) {
          railMat.emissive.set('#10B981');
          crowbarMat.emissive.set('#000000');
          etorBlock.mat.emissive.set('#D97706');
          frischBlock.mat.emissive.set('#059669');
        } else {
          railMat.emissive.set('#000000');
          crowbarMat.emissive.set('#000000');
          etorBlock.mat.emissive.set('#000000');
          frischBlock.mat.emissive.set('#000000');
        }

        // ByteMap region highlight overrides
        bindXBlock.mat.emissive.set(hi === 'bind_x' || hi === 'seq_id' ? '#3B82F6' : '#000000');
        phronesisBlock.mat.emissive.set(hi === 'phronesis_spor_b' ? '#0EA5E9' : '#000000');
        bramBlock.mat.emissive.set(hi === 'w_pre_hash' || hi === 'w_post_commit' ? '#8B5CF6' : '#000000');
        if (hi === 'etor_tap') {
          etorBlock.mat.emissive.set('#F59E0B');
        }

        renderer.render(scene, camera);
      };
      animate();

      return () => {
        cancelAnimationFrame(rafId);
        window.removeEventListener('resize', onResize);
        dom.removeEventListener('pointerdown', onPointerDown);
        dom.removeEventListener('pointermove', onPointerMove);
        dom.removeEventListener('pointerup', onPointerUp);
        dom.removeEventListener('wheel', onWheel);
        topTex.dispose();
        pcbMat.map?.dispose();
        renderer.dispose();
        if (dom.parentNode === container) {
          container.removeChild(dom);
        }
      };
    }, []);

    return (
      <div
        ref={containerRef}
        className="w-full h-full cursor-grab active:cursor-grabbing"
        aria-label="3D Granite SG48 E-TOR Cascade Hardware Viewport"
      />
    );
  },
);
