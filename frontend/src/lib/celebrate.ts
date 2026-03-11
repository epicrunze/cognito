// Canvas-based task completion celebration system
// Singleton particle engine with confetti + sparkle effects, priority-scaled tiers

export type CelebrationTier = 'epic' | 'grand' | 'standard' | 'modest' | 'minimal';

interface TierConfig {
  confettiCount: [number, number]; // [min, max]
  sparkleCount: number;
  spread: number; // px radius
  duration: number; // ms
}

const TIER_CONFIG: Record<CelebrationTier, TierConfig> = {
  epic:     { confettiCount: [80, 100], sparkleCount: 7, spread: 400, duration: 1200 },
  grand:    { confettiCount: [50, 60],  sparkleCount: 4, spread: 300, duration: 1000 },
  standard: { confettiCount: [25, 35],  sparkleCount: 2, spread: 200, duration: 800 },
  modest:   { confettiCount: [10, 15],  sparkleCount: 1, spread: 120, duration: 600 },
  minimal:  { confettiCount: [5, 8],    sparkleCount: 0, spread: 60,  duration: 400 },
};

const DONE_GREEN = '#5BBC6E';
const ACCENT = '#E8772E';

interface ConfettiParticle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  width: number;
  height: number;
  rotation: number;
  rotationSpeed: number;
  color: string;
  life: number;
  maxLife: number;
  shape: 'rect' | 'circle';
}

interface SparkleParticle {
  x: number;
  y: number;
  originX: number;
  originY: number;
  angle: number;
  speed: number;
  curve: number;
  radius: number;
  life: number;
  maxLife: number;
  color: string;
  trail: { x: number; y: number; alpha: number }[];
}

function randRange(min: number, max: number): number {
  return min + Math.random() * (max - min);
}

function randInt(min: number, max: number): number {
  return Math.floor(randRange(min, max + 1));
}

function hexToComponents(hex: string): [number, number, number] | null {
  const clean = hex.replace('#', '');
  if (clean.length !== 6) return null;
  return [
    parseInt(clean.substring(0, 2), 16),
    parseInt(clean.substring(2, 4), 16),
    parseInt(clean.substring(4, 6), 16),
  ];
}

class CelebrationCanvas {
  private static instance: CelebrationCanvas | null = null;
  private canvas: HTMLCanvasElement | null = null;
  private ctx: CanvasRenderingContext2D | null = null;
  private confetti: ConfettiParticle[] = [];
  private sparkles: SparkleParticle[] = [];
  private animating = false;
  private lastTime = 0;

  static getInstance(): CelebrationCanvas {
    if (!CelebrationCanvas.instance) {
      CelebrationCanvas.instance = new CelebrationCanvas();
    }
    return CelebrationCanvas.instance;
  }

  private ensureCanvas(): CanvasRenderingContext2D {
    if (!this.canvas) {
      this.canvas = document.createElement('canvas');
      this.canvas.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:9999;';
      document.body.appendChild(this.canvas);
    }
    this.canvas.width = window.innerWidth;
    this.canvas.height = window.innerHeight;
    if (!this.ctx) {
      this.ctx = this.canvas.getContext('2d')!;
    }
    return this.ctx;
  }

  private startLoop() {
    if (this.animating) return;
    this.animating = true;
    this.lastTime = performance.now();
    requestAnimationFrame((t) => this.loop(t));
  }

  private loop(time: number) {
    const dt = Math.min((time - this.lastTime) / 1000, 0.05); // cap at 50ms
    this.lastTime = time;

    const ctx = this.ensureCanvas();
    ctx.clearRect(0, 0, this.canvas!.width, this.canvas!.height);

    this.updateConfetti(dt);
    this.updateSparkles(dt);
    this.drawConfetti(ctx);
    this.drawSparkles(ctx);

    // Remove dead particles
    this.confetti = this.confetti.filter(p => p.life > 0);
    this.sparkles = this.sparkles.filter(p => p.life > 0);

    if (this.confetti.length === 0 && this.sparkles.length === 0) {
      this.animating = false;
      this.cleanup();
      return;
    }

    requestAnimationFrame((t) => this.loop(t));
  }

  private cleanup() {
    if (this.canvas && this.canvas.parentNode) {
      this.canvas.parentNode.removeChild(this.canvas);
    }
    this.canvas = null;
    this.ctx = null;
  }

  private updateConfetti(dt: number) {
    const gravity = 800;
    for (const p of this.confetti) {
      p.life -= dt;
      p.vy += gravity * dt;
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.vx *= (1 - 1.5 * dt); // air resistance
      p.rotation += p.rotationSpeed * dt;
    }
  }

  private updateSparkles(dt: number) {
    for (const p of this.sparkles) {
      p.life -= dt;
      const t = 1 - (p.life / p.maxLife);
      const curvedAngle = p.angle + p.curve * t;
      p.x = p.originX + Math.cos(curvedAngle) * p.speed * t * p.radius;
      p.y = p.originY + Math.sin(curvedAngle) * p.speed * t * p.radius - 50 * t * (1 - t); // arc upward

      // Update trail
      p.trail.push({ x: p.x, y: p.y, alpha: p.life / p.maxLife });
      if (p.trail.length > 8) p.trail.shift();
    }
  }

  private drawConfetti(ctx: CanvasRenderingContext2D) {
    for (const p of this.confetti) {
      const alpha = Math.min(1, p.life * 3); // fade out in last third
      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.rotate(p.rotation);
      ctx.globalAlpha = alpha;
      ctx.fillStyle = p.color;
      if (p.shape === 'circle') {
        ctx.beginPath();
        ctx.arc(0, 0, p.width / 2, 0, Math.PI * 2);
        ctx.fill();
      } else {
        ctx.fillRect(-p.width / 2, -p.height / 2, p.width, p.height);
      }
      ctx.restore();
    }
  }

  private drawSparkles(ctx: CanvasRenderingContext2D) {
    for (const p of this.sparkles) {
      // Draw trail
      for (let i = 0; i < p.trail.length - 1; i++) {
        const seg = p.trail[i];
        const next = p.trail[i + 1];
        ctx.save();
        ctx.globalAlpha = seg.alpha * 0.4 * (i / p.trail.length);
        ctx.strokeStyle = p.color;
        ctx.lineWidth = 2 * (i / p.trail.length);
        ctx.beginPath();
        ctx.moveTo(seg.x, seg.y);
        ctx.lineTo(next.x, next.y);
        ctx.stroke();
        ctx.restore();
      }
      // Draw dot
      const alpha = p.life / p.maxLife;
      ctx.save();
      ctx.globalAlpha = alpha;
      ctx.fillStyle = p.color;
      ctx.shadowColor = p.color;
      ctx.shadowBlur = 6;
      ctx.beginPath();
      ctx.arc(p.x, p.y, 3, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }
  }

  emit(origin: { x: number; y: number }, tier: CelebrationTier, color: string) {
    const config = TIER_CONFIG[tier];
    const count = randInt(config.confettiCount[0], config.confettiCount[1]);
    const colors = this.makeColors(color);
    const sparkleColors = [ACCENT, '#F5A623', '#FFD700', DONE_GREEN];

    // Spawn confetti
    for (let i = 0; i < count; i++) {
      const angle = randRange(-Math.PI * 0.9, -Math.PI * 0.1); // mostly upward
      const speed = randRange(200, 500) * (config.spread / 200);
      const life = config.duration / 1000 * randRange(0.7, 1.0);
      this.confetti.push({
        x: origin.x + randRange(-10, 10),
        y: origin.y + randRange(-5, 5),
        vx: Math.cos(angle) * speed + randRange(-30, 30),
        vy: Math.sin(angle) * speed,
        width: randRange(4, 8),
        height: randRange(3, 6),
        rotation: randRange(0, Math.PI * 2),
        rotationSpeed: randRange(-8, 8),
        color: colors[Math.floor(Math.random() * colors.length)],
        life,
        maxLife: life,
        shape: Math.random() > 0.5 ? 'rect' : 'circle',
      });
    }

    // Spawn sparkles
    for (let i = 0; i < config.sparkleCount; i++) {
      const angle = randRange(0, Math.PI * 2);
      const life = config.duration / 1000 * randRange(0.6, 1.0);
      this.sparkles.push({
        x: origin.x,
        y: origin.y,
        originX: origin.x,
        originY: origin.y,
        angle,
        speed: randRange(0.8, 1.5),
        curve: randRange(-1, 1),
        radius: config.spread * 0.6,
        life,
        maxLife: life,
        color: sparkleColors[Math.floor(Math.random() * sparkleColors.length)],
        trail: [],
      });
    }

    this.ensureCanvas();
    this.startLoop();
    this.playSound(tier);
  }

  private makeColors(projectColor: string): string[] {
    const base = [ACCENT, DONE_GREEN, '#ffffff'];
    const parsed = hexToComponents(projectColor);
    if (parsed) {
      base.push(`rgb(${parsed[0]}, ${parsed[1]}, ${parsed[2]})`);
      // Lighter variant
      base.push(`rgb(${Math.min(255, parsed[0] + 50)}, ${Math.min(255, parsed[1] + 50)}, ${Math.min(255, parsed[2] + 50)})`);
    }
    return base;
  }

  private playSound(tier: CelebrationTier) {
    if (typeof localStorage === 'undefined') return;
    if (localStorage.getItem('cognito-celebration-sounds') !== 'true') return;

    try {
      const ctx = new AudioContext();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);

      // Different tones per tier
      const freqs: Record<CelebrationTier, number[]> = {
        epic:     [523, 659, 784, 1047],
        grand:    [523, 659, 784],
        standard: [523, 659],
        modest:   [659],
        minimal:  [784],
      };
      const notes = freqs[tier];
      const noteDuration = 0.12;

      osc.type = 'sine';
      gain.gain.setValueAtTime(0.15, ctx.currentTime);

      let time = ctx.currentTime;
      for (const freq of notes) {
        osc.frequency.setValueAtTime(freq, time);
        time += noteDuration;
      }

      gain.gain.exponentialRampToValueAtTime(0.001, time + 0.1);
      osc.start(ctx.currentTime);
      osc.stop(time + 0.15);

      // Cleanup
      osc.onended = () => ctx.close();
    } catch {
      // Audio not available — silent fail
    }
  }
}

// --- Element registry ---
const celebrationElements = new Map<number, HTMLElement>();

export function registerCelebrationElement(taskId: number, element: HTMLElement) {
  celebrationElements.set(taskId, element);
}

export function unregisterCelebrationElement(taskId: number) {
  celebrationElements.delete(taskId);
}

// --- Public API ---

export function getTier(priority: number): CelebrationTier {
  if (priority >= 5) return 'epic';
  if (priority >= 4) return 'grand';
  if (priority >= 3) return 'standard';
  if (priority >= 2) return 'modest';
  return 'minimal';
}

export function celebrate(origin: { x: number; y: number }, tier: CelebrationTier, color: string): void {
  CelebrationCanvas.getInstance().emit(origin, tier, color);
}

export function celebrateTask(taskId: number, priority: number, color: string): void {
  const el = celebrationElements.get(taskId);
  let origin: { x: number; y: number };
  if (el) {
    const rect = el.getBoundingClientRect();
    origin = { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
  } else {
    origin = { x: window.innerWidth / 2, y: window.innerHeight / 2 };
  }
  celebrate(origin, getTier(priority), color);
}
