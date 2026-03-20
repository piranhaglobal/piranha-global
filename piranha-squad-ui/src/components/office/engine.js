// ============================================================
// Piranha Squad — Office Engine
// Canvas 2D · BFS Pathfinding · Character State Machine
// Inspired by: github.com/pablodelucca/pixel-agents
// ============================================================

export const TILE = 48;
export const COLS = 22;
export const ROWS = 10;
export const VIRTUAL_W = COLS * TILE; // 1056
export const VIRTUAL_H = ROWS * TILE; // 480

const WALK_SPEED    = 3.2; // tiles/sec
const WALK_FRAME_S  = 0.13;
const TYPE_FRAME_S  = 0.28;
const WANDER_MIN    = 4;
const WANDER_MAX    = 10;

// ─── Colours ─────────────────────────────────────────────────────────────────
const SHIRT = {
    red:     '#b91c1c',
    blue:    '#1d4ed8',
    purple:  '#7c3aed',
    amber:   '#b45309',
    green:   '#065f46',
    default: '#374151',
    cyan:    '#0e7490',
    indigo:  '#4338ca',
};

// ─── BFS pathfinding (4-connected grid) ──────────────────────────────────────
export function findPath(sx, sy, ex, ey, blocked) {
    if (sx === ex && sy === ey) return [];
    const key = (x, y) => `${x},${y}`;
    const passable = (x, y) => {
        if (x < 0 || x >= COLS || y < 0 || y >= ROWS) return false;
        if (x === ex && y === ey) return true; // always allow destination
        return !blocked.has(key(x, y));
    };

    const queue = [{ x: sx, y: sy, path: [] }];
    const visited = new Set([key(sx, sy)]);

    while (queue.length) {
        const { x, y, path } = queue.shift();
        for (const [dx, dy] of [[0,-1],[0,1],[-1,0],[1,0]]) {
            const nx = x + dx, ny = y + dy;
            const k = key(nx, ny);
            if (!passable(nx, ny) || visited.has(k)) continue;
            const np = [...path, [nx, ny]];
            if (nx === ex && ny === ey) return np;
            visited.add(k);
            queue.push({ x: nx, y: ny, path: np });
        }
    }
    return []; // unreachable
}

// ─── Canvas helpers ───────────────────────────────────────────────────────────
function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y); ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r); ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h); ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r); ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
}

// ─── Pixel character renderer ─────────────────────────────────────────────────
// Character is 10×14 px units, drawn centered on (cx, cy) where cy = foot level
export function drawCharacter(ctx, cx, cy, color, state, frame, scale = 3) {
    const s   = scale;
    const c   = SHIRT[color] || SHIRT.default;
    const ox  = cx - 5 * s;  // left edge
    const oy  = cy - 14 * s; // top of head

    ctx.save();

    // Head
    ctx.fillStyle = '#d4a76a';
    ctx.fillRect(ox + 3*s, oy, 4*s, 4*s);

    // Eyes
    ctx.fillStyle = '#1a0a00';
    ctx.fillRect(ox + 4*s, oy + s,   s, s);
    ctx.fillRect(ox + 6*s, oy + s,   s, s);

    // Smile when typing
    if (state === 'typing') {
        ctx.fillRect(ox + 4*s, oy + 3*s, s, s);
        ctx.fillRect(ox + 6*s, oy + 3*s, s, s);
    }

    // Body
    ctx.fillStyle = c;
    ctx.fillRect(ox + 2*s, oy + 4*s, 6*s, 5*s);

    // Arms — bob when typing
    const armBob = (state === 'typing' && frame % 2 === 0) ? s : 0;
    ctx.fillRect(ox,       oy + 5*s + armBob, 2*s, 3*s - armBob);
    ctx.fillRect(ox + 8*s, oy + 5*s + armBob, 2*s, 3*s - armBob);

    // Legs — walk cycle or standing
    ctx.fillStyle = '#1e293b';
    if (state === 'walking') {
        const phase = frame % 4;
        const l1 = (phase < 2) ? 0 : s;
        const l2 = (phase < 2) ? s : 0;
        ctx.fillRect(ox + 2*s, oy + 9*s + l1, 3*s, 5*s - l1);
        ctx.fillRect(ox + 6*s, oy + 9*s + l2, 3*s, 5*s - l2);
    } else {
        ctx.fillRect(ox + 2*s, oy + 9*s, 3*s, 5*s);
        ctx.fillRect(ox + 6*s, oy + 9*s, 3*s, 5*s);
    }

    // Shoes
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(ox +   s, oy + 12*s, 3*s, 2*s);
    ctx.fillRect(ox + 6*s, oy + 12*s, 3*s, 2*s);

    ctx.restore();
}

// ─── Desk renderer ────────────────────────────────────────────────────────────
export function drawDesk(ctx, tx, ty, isActive, color) {
    const x = tx * TILE;
    const y = ty * TILE;
    const accent = SHIRT[color] || SHIRT.default;
    const now = Date.now();

    // Desk body
    ctx.fillStyle = '#3a2e1e';
    ctx.fillRect(x + 4, y + 18, 40, 24);
    ctx.fillStyle = '#4e3d28';
    ctx.fillRect(x + 4, y + 18, 40, 5);

    // Monitor frame
    ctx.fillStyle = '#111827';
    ctx.strokeStyle = '#374151';
    ctx.lineWidth = 1;
    ctx.beginPath();
    roundRect(ctx, x + 10, y + 2, 28, 18, 2);
    ctx.fill(); ctx.stroke();

    // Screen
    if (isActive) {
        // Glowing screen
        ctx.fillStyle = '#001a1a';
        ctx.fillRect(x + 12, y + 4, 24, 14);

        // Scrolling code lines
        const scroll = (now / 120) % 12;
        ctx.fillStyle = '#22d3ee';
        for (let i = 0; i < 4; i++) {
            const lineW = 6 + Math.abs(Math.sin((i * 1.7 + now / 500))) * 16;
            const lineY = y + 5 + ((i * 4 + scroll) % 14);
            ctx.fillRect(x + 13, lineY, lineW, 1);
        }

        // Subtle desk glow
        ctx.save();
        ctx.shadowColor = accent;
        ctx.shadowBlur = 12;
        ctx.globalAlpha = 0.15 + Math.sin(now / 400) * 0.08;
        ctx.fillStyle = accent;
        ctx.fillRect(x + 4, y + 18, 40, 24);
        ctx.restore();
    } else {
        ctx.fillStyle = '#0a0f14';
        ctx.fillRect(x + 12, y + 4, 24, 14);
        // Screensaver dot
        ctx.fillStyle = '#1f2937';
        ctx.fillRect(x + 22, y + 10, 4, 2);
    }

    // Monitor stand
    ctx.fillStyle = '#374151';
    ctx.fillRect(x + 22, y + 20, 4, 2);

    // Desk legs
    ctx.fillStyle = '#2a1e10';
    ctx.fillRect(x + 6,  y + 40, 4, 8);
    ctx.fillRect(x + 38, y + 40, 4, 8);
}

// ─── Name badge ───────────────────────────────────────────────────────────────
function drawBadge(ctx, cx, by, label, isActive) {
    ctx.font = 'bold 10px monospace';
    const tw = ctx.measureText(label).width;
    const bw = tw + 10;
    const bx = cx - bw / 2;

    ctx.fillStyle = isActive ? '#083344' : '#1f2937';
    ctx.strokeStyle = isActive ? '#22d3ee60' : '#37415180';
    ctx.lineWidth = 1;
    roundRect(ctx, bx, by, bw, 14, 3);
    ctx.fill(); ctx.stroke();

    ctx.fillStyle = isActive ? '#22d3ee' : '#6b7280';
    ctx.textAlign = 'center';
    ctx.fillText(label, cx, by + 10);
    ctx.textAlign = 'left';
}

// ─── Speech bubble ────────────────────────────────────────────────────────────
function drawSpeechBubble(ctx, cx, cy, text, alpha) {
    if (alpha <= 0 || !text) return;

    const display = text.length > 32 ? text.substring(0, 32) + '…' : text;
    ctx.save();
    ctx.globalAlpha = Math.min(1, alpha);
    ctx.font = 'bold 9px monospace';
    const tw = ctx.measureText(display).width;
    const bw = tw + 12;
    const bh = 18;
    const bx = cx - bw / 2;
    const bubbleY = cy - 76;

    // White bubble
    ctx.fillStyle = '#ffffff';
    ctx.strokeStyle = '#d1d5db';
    ctx.lineWidth = 0.5;
    roundRect(ctx, bx, bubbleY, bw, bh, 4);
    ctx.fill(); ctx.stroke();

    // Tail
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.moveTo(cx - 4, bubbleY + bh);
    ctx.lineTo(cx + 4, bubbleY + bh);
    ctx.lineTo(cx, bubbleY + bh + 6);
    ctx.closePath(); ctx.fill();

    // Text
    ctx.fillStyle = '#111827';
    ctx.textAlign = 'center';
    ctx.fillText(display, cx, bubbleY + 12);
    ctx.textAlign = 'left';

    ctx.restore();
}

// ─── Floor & background ───────────────────────────────────────────────────────
function drawFloor(ctx) {
    ctx.fillStyle = '#0d1117';
    ctx.fillRect(0, 0, VIRTUAL_W, VIRTUAL_H);

    // Subtle tile grid
    ctx.strokeStyle = '#141c27';
    ctx.lineWidth = 0.5;
    for (let x = 0; x <= VIRTUAL_W; x += TILE) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, VIRTUAL_H); ctx.stroke();
    }
    for (let y = 0; y <= VIRTUAL_H; y += TILE) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(VIRTUAL_W, y); ctx.stroke();
    }

    // Floor accent strip at bottom
    ctx.fillStyle = '#0a1018';
    ctx.fillRect(0, VIRTUAL_H - TILE * 1.5, VIRTUAL_W, TILE * 1.5);
}

// ─── Human workstation ────────────────────────────────────────────────────────
function drawHumanStation(ctx, isActive) {
    const x = 1 * TILE;
    const y = 7.5 * TILE;
    const cx = x + TILE / 2;
    const cy = y + TILE / 2;
    const now = Date.now();

    // Glow ring when active
    if (isActive) {
        ctx.save();
        ctx.globalAlpha = 0.4 + Math.sin(now / 250) * 0.2;
        ctx.strokeStyle = '#818cf8';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(cx, cy, 22, 0, Math.PI * 2);
        ctx.stroke();
        ctx.restore();
    }

    // Circle bg
    ctx.fillStyle = isActive ? '#312e81' : '#1f2937';
    ctx.strokeStyle = isActive ? '#818cf840' : '#37415140';
    ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.arc(cx, cy, 20, 0, Math.PI * 2);
    ctx.fill(); ctx.stroke();

    // Icon (simple pixel person)
    ctx.fillStyle = isActive ? '#c7d2fe' : '#9ca3af';
    ctx.font = '20px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('👤', cx, cy + 7);
    ctx.textAlign = 'left';

    drawBadge(ctx, cx, cy + 24, '@human', isActive);

    if (isActive) {
        drawSpeechBubble(ctx, cx, cy, 'A aguardar...', 0.9);
    }
}

// ─── Agent class ──────────────────────────────────────────────────────────────
export class Agent {
    constructor(id, label, deskTx, deskTy, color) {
        this.id = id;
        this.label = label;
        this.color = color;
        this.deskTx = deskTx;
        this.deskTy = deskTy;
        this.isHuman = false;

        // Spawn just below the desk
        this.tileX = deskTx;
        this.tileY = Math.min(deskTy + 2, ROWS - 1);
        this.px = this.tileX * TILE + TILE / 2;
        this.py = this.tileY * TILE + TILE;

        this.path       = [];
        this.state      = 'idle';  // idle | walking | typing
        this.frame      = 0;
        this.frameTimer = 0;
        this.isActive   = false;
        this.bubbleText = '';
        this.bubbleAlpha = 0;
        this.wanderTimer = WANDER_MIN + Math.random() * (WANDER_MAX - WANDER_MIN);
    }
}

// ─── OfficeEngine ─────────────────────────────────────────────────────────────
export class OfficeEngine {
    constructor(rawAgents, squadColor) {
        this.agents = [];
        this.humanActive = false;
        this._init(rawAgents, squadColor);
    }

    _init(rawAgents, color) {
        const nonHuman = rawAgents.filter(a => a.id !== 'human-user');

        // Desk layout: up to 5 per row, 2 rows
        const perRow = Math.min(5, Math.ceil(nonHuman.length / 2));
        const startCol = Math.max(2, Math.floor((COLS - perRow * 4) / 2));

        this.agents = nonHuman.map((raw, i) => {
            const row = i < perRow ? 0 : 1;
            const col = i < perRow ? i : i - perRow;
            const tx = startCol + col * 4;
            const ty = row === 0 ? 1 : 5;
            return new Agent(raw.id, raw.data?.label || raw.id, tx, ty, color);
        });
    }

    _blockedTiles(excludeId = null) {
        const s = new Set();
        this.agents.forEach(a => {
            if (a.id !== excludeId) s.add(`${a.tileX},${a.tileY}`);
            s.add(`${a.deskTx},${a.deskTy}`); // desks are obstacles
        });
        return s;
    }

    // Called by VirtualOffice when log changes
    onLog(agentLabel, actionText) {
        const agent = this.agents.find(a =>
            a.label === agentLabel ||
            agentLabel.replace('@', '').startsWith(a.id.split('-')[0])
        );

        if (!agent) return;

        // Deactivate others
        this.agents.forEach(a => {
            if (a.id !== agent.id && a.isActive) {
                a.isActive = false;
                a.state = 'idle';
                a.wanderTimer = WANDER_MIN + Math.random() * 3;
            }
        });

        if (!agent.isActive) {
            agent.isActive = true;
            // Walk to desk
            const destTy = agent.deskTy + 1;
            if (agent.tileX !== agent.deskTx || agent.tileY !== destTy) {
                const blocked = this._blockedTiles(agent.id);
                const path = findPath(agent.tileX, agent.tileY, agent.deskTx, destTy, blocked);
                if (path.length > 0) {
                    agent.path = path;
                    agent.state = 'walking';
                } else {
                    agent.state = 'typing';
                }
            } else {
                agent.state = 'typing';
            }
        }

        agent.bubbleText = actionText;
        agent.bubbleAlpha = 1;
    }

    onSystemLog(text) {
        this.agents.forEach(a => {
            a.isActive = false;
            a.state = 'idle';
            a.wanderTimer = WANDER_MIN + Math.random() * 3;
        });
        this.humanActive = false;
    }

    onHumanGate(waiting) {
        this.humanActive = waiting;
        if (waiting) {
            this.agents.forEach(a => {
                a.isActive = false;
                a.state = 'idle';
                a.wanderTimer = 2 + Math.random() * 2;
            });
        }
    }

    resetAll() {
        this.agents.forEach(a => {
            a.isActive = false;
            a.state = 'idle';
            a.bubbleAlpha = 0;
            a.wanderTimer = WANDER_MIN + Math.random() * (WANDER_MAX - WANDER_MIN);
        });
        this.humanActive = false;
    }

    update(dt) {
        this.agents.forEach(a => {
            // ── Animation frames ──
            a.frameTimer += dt;
            const dur = a.state === 'walking' ? WALK_FRAME_S : TYPE_FRAME_S;
            if (a.frameTimer >= dur) { a.frameTimer = 0; a.frame = (a.frame + 1) % 4; }

            // ── Bubble fade when idle ──
            if (!a.isActive && a.bubbleAlpha > 0) {
                a.bubbleAlpha = Math.max(0, a.bubbleAlpha - dt * 0.4);
            }

            // ── Walking ──
            if (a.state === 'walking' && a.path.length > 0) {
                const [ntx, nty] = a.path[0];
                const tpx = ntx * TILE + TILE / 2;
                const tpy = nty * TILE + TILE;
                const dx = tpx - a.px, dy = tpy - a.py;
                const dist = Math.sqrt(dx * dx + dy * dy);
                const step = WALK_SPEED * TILE * dt;

                if (dist <= step) {
                    a.px = tpx; a.py = tpy;
                    a.tileX = ntx; a.tileY = nty;
                    a.path.shift();
                    if (a.path.length === 0) {
                        a.state = a.isActive ? 'typing' : 'idle';
                    }
                } else {
                    a.px += (dx / dist) * step;
                    a.py += (dy / dist) * step;
                }
            }

            // ── Idle wander ──
            if (a.state === 'idle' && !a.isActive) {
                a.wanderTimer -= dt;
                if (a.wanderTimer <= 0) {
                    a.wanderTimer = WANDER_MIN + Math.random() * (WANDER_MAX - WANDER_MIN);
                    const blocked = this._blockedTiles(a.id);

                    // Pick a random reachable tile away from desks
                    for (let attempt = 0; attempt < 15; attempt++) {
                        const tx = Math.max(0, Math.min(COLS - 1, a.tileX + Math.round(Math.random() * 6 - 3)));
                        const ty = Math.max(0, Math.min(ROWS - 1, a.tileY + Math.round(Math.random() * 4 - 2)));
                        const nearDesk = this.agents.some(ag =>
                            Math.abs(ag.deskTx - tx) <= 1 && Math.abs(ag.deskTy - ty) <= 1
                        );
                        if (!nearDesk && !blocked.has(`${tx},${ty}`)) {
                            const path = findPath(a.tileX, a.tileY, tx, ty, blocked);
                            if (path.length > 0) { a.path = path; a.state = 'walking'; break; }
                        }
                    }
                }
            }
        });
    }

    render(ctx) {
        drawFloor(ctx);

        // Desks (below characters in z-order)
        this.agents.forEach(a => {
            drawDesk(ctx, a.deskTx, a.deskTy, a.isActive, a.color);
        });

        // Human station
        drawHumanStation(ctx, this.humanActive);

        // Z-sorted characters (front = higher py = rendered last)
        [...this.agents]
            .sort((a, b) => a.py - b.py)
            .forEach(a => {
                const now = Date.now();

                // Active glow shadow on floor
                if (a.isActive) {
                    ctx.save();
                    ctx.globalAlpha = 0.3 + Math.sin(now / 300) * 0.1;
                    ctx.strokeStyle = SHIRT[a.color] || '#22d3ee';
                    ctx.lineWidth = 2;
                    ctx.beginPath();
                    ctx.ellipse(a.px, a.py - 1, 13, 4, 0, 0, Math.PI * 2);
                    ctx.stroke();
                    ctx.restore();
                }

                drawCharacter(ctx, a.px, a.py, a.color, a.state, a.frame, 3);
                drawBadge(ctx, a.px, a.py + 5, a.label, a.isActive);

                if (a.bubbleAlpha > 0) {
                    drawSpeechBubble(ctx, a.px, a.py, a.bubbleText, a.bubbleAlpha);
                }
            });
    }
}
