// ============================================================
// Piranha Global — World Engine v2
// Canvas 2D · Navigable Top-Down Corporate Office
// Premium Corporate Style — NO pixel art
// ============================================================

export const WORLD_W = 2400;
export const WORLD_H = 1400;

// ─── Zone definitions ─────────────────────────────────────────────────────────
export const ZONES = [
    // Top row
    { id: 'executive',  label: 'DIRECÇÃO',         x: 50,   y: 50,  w: 500, h: 580, floor: '#0a0b1e', accent: '#6366f1' },
    { id: 'marketing',  label: 'MARKETING',         x: 620,  y: 50,  w: 720, h: 580, floor: '#0c0516', accent: '#a855f7' },
    { id: 'studio',     label: 'ESTÚDIO CRIATIVO',  x: 1420, y: 50,  w: 500, h: 580, floor: '#050e08', accent: '#10b981' },
    { id: 'boardroom',  label: 'BOARDROOM',          x: 2000, y: 50,  w: 350, h: 270, floor: '#0a0814', accent: '#f59e0b' },
    { id: 'meeting1',   label: 'SALA DE REUNIÃO',   x: 2000, y: 360, w: 350, h: 270, floor: '#07070f', accent: '#6366f1' },
    // Corridor
    { id: 'corridor',   label: '',                  x: 0,    y: 680, w: 2400, h: 80, floor: '#0c0f14', accent: '#374151' },
    // Bottom row
    { id: 'sales',      label: 'VENDAS',            x: 50,   y: 810, w: 500, h: 540, floor: '#120405', accent: '#ef4444' },
    { id: 'operations', label: 'OPERAÇÕES',         x: 620,  y: 810, w: 720, h: 540, floor: '#040e05', accent: '#10b981' },
    { id: 'finance',    label: 'FINANÇAS',          x: 1420, y: 810, w: 500, h: 540, floor: '#0e0a02', accent: '#f59e0b' },
    { id: 'break',      label: 'CAFÉ & LOUNGE',     x: 2000, y: 810, w: 350, h: 540, floor: '#0a0a0a', accent: '#6b7280' },
];

// ─── State colors & labels ────────────────────────────────────────────────────
export const STATE_COLORS = {
    available:            '#22c55e',
    focused:              '#3b82f6',
    in_meeting:           '#a855f7',
    working:              '#f59e0b',
    idle:                 '#475569',
    away:                 '#9ca3af',
    blocked:              '#ef4444',
    waiting_human_input:  '#ec4899',
    researching:          '#06b6d4',
    generating:           '#8b5cf6',
};

export const STATE_LABELS = {
    available:            'Disponível',
    focused:              'Focado',
    in_meeting:           'Em Reunião',
    working:              'A Trabalhar',
    idle:                 'Em Espera',
    away:                 'Ausente',
    blocked:              'Bloqueado',
    waiting_human_input:  'Aguarda Aprovação',
    researching:          'A Investigar',
    generating:           'A Gerar',
};

// ─── Level colors ─────────────────────────────────────────────────────────────
const LEVEL_COLOR = {
    leadership: '#dc2626',
    'c-level':  '#2563eb',
    director:   '#9333ea',
    manager:    '#d97706',
    specialist: '#475569',
};

// ─── Squad → Zone mapping ─────────────────────────────────────────────────────
const SQUAD_ZONE = {
    'piranha-leads':     'sales',
    'piranha-workshops': 'marketing',
    'piranha-comms':     'marketing',
    'piranha-supplies':  'operations',
    'piranha-studio':    'studio',
};

// ─── Squad colors ─────────────────────────────────────────────────────────────
const SQUAD_COLOR = {
    'piranha-leads':     '#b91c1c',
    'piranha-workshops': '#1d4ed8',
    'piranha-comms':     '#7c3aed',
    'piranha-supplies':  '#b45309',
    'piranha-studio':    '#065f46',
};

// ─── Desk grid per zone ───────────────────────────────────────────────────────
const DESK_GRID = {
    executive:  { x: 100,  y: 200, cols: 3, rows: 3, gx: 150, gy: 150 },
    marketing:  { x: 660,  y: 200, cols: 4, rows: 3, gx: 160, gy: 150 },
    studio:     { x: 1460, y: 200, cols: 3, rows: 3, gx: 150, gy: 150 },
    sales:      { x: 100,  y: 890, cols: 3, rows: 3, gx: 150, gy: 150 },
    operations: { x: 660,  y: 890, cols: 4, rows: 3, gx: 155, gy: 150 },
    finance:    { x: 1460, y: 890, cols: 3, rows: 3, gx: 150, gy: 150 },
};

function getDeskSlots(zoneId) {
    const g = DESK_GRID[zoneId];
    if (!g) return [];
    const slots = [];
    for (let row = 0; row < g.rows; row++) {
        for (let col = 0; col < g.cols; col++) {
            slots.push({ x: g.x + col * g.gx, y: g.y + row * g.gy });
        }
    }
    return slots;
}

// ─── Helper: roundRect ────────────────────────────────────────────────────────
function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y); ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r); ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h); ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r); ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
}

// ─── drawZone ────────────────────────────────────────────────────────────────
function drawZone(ctx, zone, now) {
    const { x, y, w, h, floor, accent, label } = zone;

    // Floor fill
    ctx.fillStyle = floor;
    ctx.fillRect(x, y, w, h);

    // Faint inner grid
    ctx.strokeStyle = accent + '0d';
    ctx.lineWidth = 0.5;
    for (let gx = x; gx <= x + w; gx += 60) {
        ctx.beginPath(); ctx.moveTo(gx, y); ctx.lineTo(gx, y + h); ctx.stroke();
    }
    for (let gy = y; gy <= y + h; gy += 60) {
        ctx.beginPath(); ctx.moveTo(x, gy); ctx.lineTo(x + w, gy); ctx.stroke();
    }

    // Zone border
    ctx.strokeStyle = accent + '22';
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, w, h);

    // Zone label
    if (label) {
        ctx.font = 'bold 12px sans-serif';
        ctx.fillStyle = accent + '45';
        ctx.fillText(label, x + 18, y + 24);
    }
}

// ─── drawDesk ────────────────────────────────────────────────────────────────
function drawDesk(ctx, cx, cy, color, active, now) {
    // Desk surface (58×34) centered at (cx, cy)
    const dx = cx - 29;
    const dy = cy - 17;

    // Shadow/glow for active
    if (active) {
        ctx.save();
        ctx.shadowColor = color;
        ctx.shadowBlur = 18;
        ctx.globalAlpha = 0.3 + Math.sin(now / 400) * 0.1;
        ctx.fillStyle = color;
        roundRect(ctx, dx, dy, 58, 34, 4);
        ctx.fill();
        ctx.restore();
    }

    // Desk surface
    ctx.fillStyle = '#2d2a22';
    roundRect(ctx, dx, dy, 58, 34, 4);
    ctx.fill();

    // Desk top edge lighter
    ctx.fillStyle = '#3a362c';
    ctx.fillRect(dx + 4, dy, 50, 5);

    // Monitor frame (42×20) centered above desk
    const mx = cx - 21;
    const my = cy - 82;
    ctx.fillStyle = '#111827';
    roundRect(ctx, mx, my, 42, 20, 3);
    ctx.fill();

    if (active) {
        // Active screen
        ctx.fillStyle = '#001825';
        ctx.fillRect(mx + 2, my + 2, 38, 16);

        // Scrolling cyan code lines
        const scroll = (now / 160) % 12;
        ctx.fillStyle = '#22d3ee';
        for (let i = 0; i < 3; i++) {
            const lineW = 8 + Math.abs(Math.sin(i * 1.9 + now / 500)) * 20;
            const lineY = my + 3 + ((i * 5 + scroll) % 13);
            if (lineY > my + 2 && lineY < my + 17) {
                ctx.fillRect(mx + 3, lineY, lineW, 1.5);
            }
        }
    } else {
        // Inactive screen
        ctx.fillStyle = '#080d14';
        ctx.fillRect(mx + 2, my + 2, 38, 16);
        // Faint screensaver dot
        ctx.fillStyle = '#1e2530';
        ctx.fillRect(mx + 18, my + 9, 4, 4);
    }

    // Monitor stand
    ctx.fillStyle = '#374151';
    ctx.fillRect(cx - 3, cy - 62, 6, 4);
    ctx.fillRect(cx - 8, cy - 59, 16, 3);
}

// ─── drawMeetingTable ─────────────────────────────────────────────────────────
function drawMeetingTable(ctx, cx, cy, w, h, accent, now) {
    const x = cx - w / 2;
    const y = cy - h / 2;

    // Outer fill
    ctx.fillStyle = '#1a1730';
    roundRect(ctx, x, y, w, h, 8);
    ctx.fill();

    // Accent stroke
    ctx.strokeStyle = accent + '55';
    ctx.lineWidth = 1.5;
    roundRect(ctx, x, y, w, h, 8);
    ctx.stroke();

    // Inner surface
    ctx.fillStyle = '#252048';
    roundRect(ctx, x + 8, y + 8, w - 16, h - 16, 5);
    ctx.fill();

    // Subtle inner grid
    ctx.strokeStyle = accent + '15';
    ctx.lineWidth = 0.5;
    const innerX = x + 8;
    const innerY = y + 8;
    const innerW = w - 16;
    const innerH = h - 16;
    for (let gx = innerX; gx <= innerX + innerW; gx += 40) {
        ctx.beginPath(); ctx.moveTo(gx, innerY); ctx.lineTo(gx, innerY + innerH); ctx.stroke();
    }
    for (let gy = innerY; gy <= innerY + innerH; gy += 40) {
        ctx.beginPath(); ctx.moveTo(innerX, gy); ctx.lineTo(innerX + innerW, gy); ctx.stroke();
    }
}

// ─── drawBreakArea ────────────────────────────────────────────────────────────
function drawBreakArea(ctx, now) {
    const bx = 2010;
    const by = 820;

    // Sofa — L-shape
    ctx.fillStyle = '#1a2535';
    // Main sofa body
    roundRect(ctx, bx + 10, by + 20, 160, 60, 8);
    ctx.fill();
    // Sofa arm left
    roundRect(ctx, bx + 10, by + 20, 20, 80, 5);
    ctx.fill();
    // Sofa back cushions
    ctx.fillStyle = '#1e2d42';
    roundRect(ctx, bx + 15, by + 22, 55, 15, 4);
    ctx.fill();
    roundRect(ctx, bx + 78, by + 22, 55, 15, 4);
    ctx.fill();

    // Coffee table
    ctx.fillStyle = '#1e2a35';
    roundRect(ctx, bx + 30, by + 100, 120, 55, 6);
    ctx.fill();
    ctx.strokeStyle = '#2d3a4a';
    ctx.lineWidth = 1;
    roundRect(ctx, bx + 30, by + 100, 120, 55, 6);
    ctx.stroke();

    // Coffee machine
    ctx.fillStyle = '#1a2030';
    ctx.fillRect(bx + 200, by + 20, 40, 55);
    // Machine screen
    ctx.fillStyle = '#0d1520';
    ctx.fillRect(bx + 205, by + 25, 28, 18);
    ctx.fillStyle = '#06b6d4';
    // Pulsing light dot
    const pulse = 0.5 + Math.sin(now / 600) * 0.5;
    ctx.globalAlpha = pulse;
    ctx.beginPath();
    ctx.arc(bx + 219, by + 34, 4, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1;

    // Decorative plants
    // Plant 1
    ctx.fillStyle = '#0a1a0a';
    ctx.beginPath();
    ctx.arc(bx + 270, by + 90, 18, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#143d14';
    ctx.beginPath();
    ctx.arc(bx + 270, by + 80, 12, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#1a5c1a';
    ctx.beginPath();
    ctx.arc(bx + 263, by + 74, 7, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(bx + 277, by + 74, 6, 0, Math.PI * 2);
    ctx.fill();

    // Plant 2
    ctx.fillStyle = '#0a1a0a';
    ctx.beginPath();
    ctx.arc(bx + 310, by + 230, 16, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#143d14';
    ctx.beginPath();
    ctx.arc(bx + 310, by + 221, 11, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#1a5c1a';
    ctx.beginPath();
    ctx.arc(bx + 304, by + 215, 6, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(bx + 316, by + 215, 5, 0, Math.PI * 2);
    ctx.fill();
}

// ─── drawWalls ────────────────────────────────────────────────────────────────
function drawWalls(ctx) {
    // Outer building border
    ctx.strokeStyle = '#1a2030';
    ctx.lineWidth = 3;
    ctx.strokeRect(45, 45, 2315, 1310);

    // Vertical wing dividers
    ctx.strokeStyle = '#151c28';
    ctx.lineWidth = 2;

    // Top zone dividers
    const topDividers = [610, 1410, 1990];
    topDividers.forEach(x => {
        ctx.beginPath(); ctx.moveTo(x, 50); ctx.lineTo(x, 675); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(x + 10, 50); ctx.lineTo(x + 10, 675); ctx.stroke();
    });

    // Bottom zone dividers
    const botDividers = [610, 1410, 1990];
    botDividers.forEach(x => {
        ctx.beginPath(); ctx.moveTo(x, 760); ctx.lineTo(x, 1360); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(x + 10, 760); ctx.lineTo(x + 10, 1360); ctx.stroke();
    });

    // Meeting room horizontal divider
    ctx.beginPath(); ctx.moveTo(2000, 355); ctx.lineTo(2355, 355); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(2000, 360); ctx.lineTo(2355, 360); ctx.stroke();
}

// ─── drawSpeechBubble ─────────────────────────────────────────────────────────
function drawSpeechBubble(ctx, cx, tipY, text, alpha) {
    if (alpha <= 0 || !text) return;
    const display = text.length > 38 ? text.substring(0, 38) + '…' : text;

    ctx.save();
    ctx.globalAlpha = Math.min(1, alpha);
    ctx.font = '11px monospace';
    const tw = ctx.measureText(display).width;
    const bw = tw + 16;
    const bh = 22;
    const bx = cx - bw / 2;
    const bubbleY = tipY - bh - 12;

    // Bubble background
    ctx.fillStyle = '#ffffff';
    ctx.strokeStyle = '#d1d5db';
    ctx.lineWidth = 0.8;
    roundRect(ctx, bx, bubbleY, bw, bh, 5);
    ctx.fill();
    ctx.stroke();

    // Tail pointing down
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.moveTo(cx - 5, bubbleY + bh);
    ctx.lineTo(cx + 5, bubbleY + bh);
    ctx.lineTo(cx, tipY);
    ctx.closePath();
    ctx.fill();

    ctx.strokeStyle = '#d1d5db';
    ctx.lineWidth = 0.5;
    ctx.beginPath();
    ctx.moveTo(cx - 4, bubbleY + bh);
    ctx.lineTo(cx, tipY);
    ctx.lineTo(cx + 4, bubbleY + bh);
    ctx.stroke();

    // Text
    ctx.fillStyle = '#111827';
    ctx.textAlign = 'center';
    ctx.fillText(display, cx, bubbleY + 15);
    ctx.textAlign = 'left';
    ctx.restore();
}

// ─── drawEntity ───────────────────────────────────────────────────────────────
function drawEntity(ctx, entity, isPlayer, isNearby, now) {
    const { x, y, radius, color, state, name, type, avatar, bubbleAlpha, bubble } = entity;
    const stateColor = STATE_COLORS[state] || STATE_COLORS.idle;

    // Proximity glow (not for player)
    if (isNearby && !isPlayer) {
        const gPulse = 0.12 + Math.sin(now / 500) * 0.04;
        ctx.save();
        ctx.globalAlpha = gPulse;
        ctx.fillStyle = '#6366f1';
        ctx.beginPath();
        ctx.arc(x, y, radius + 22, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
    }

    // State ring (if not idle)
    if (state && state !== 'idle') {
        ctx.save();
        ctx.shadowColor = stateColor;
        ctx.shadowBlur = 10;
        ctx.strokeStyle = stateColor;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(x, y, radius + 4, 0, Math.PI * 2);
        ctx.stroke();
        ctx.restore();
    }

    // Player pulse ring
    if (isPlayer) {
        const pAlpha = 0.15 + Math.sin(now / 700) * 0.08;
        ctx.save();
        ctx.globalAlpha = pAlpha;
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(x, y, radius + 12, 0, Math.PI * 2);
        ctx.stroke();
        ctx.restore();
    }

    // Avatar circle
    ctx.fillStyle = color || '#4f46e5';
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();

    // Subtle border
    ctx.strokeStyle = 'rgba(255,255,255,0.08)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.stroke();

    // Avatar content
    if (avatar && avatar !== '' && !/^[A-Z]{1,3}$/.test(avatar)) {
        // Emoji avatar
        ctx.font = `${radius}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(avatar, x, y);
        ctx.textBaseline = 'alphabetic';
    } else {
        // Initials fallback
        const initials = name
            ? name.split(' ').map(w => w[0]).join('').substring(0, 2).toUpperCase()
            : '??';
        ctx.font = `bold ${Math.round(radius * 0.65)}px sans-serif`;
        ctx.fillStyle = '#ffffff';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(initials, x, y);
        ctx.textBaseline = 'alphabetic';
    }
    ctx.textAlign = 'left';

    // State dot (bottom-right)
    const dotR = 5;
    const dotX = x + radius * 0.72;
    const dotY = y + radius * 0.72;
    ctx.fillStyle = '#0f172a';
    ctx.beginPath();
    ctx.arc(dotX, dotY, dotR + 1.5, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = stateColor;
    ctx.beginPath();
    ctx.arc(dotX, dotY, dotR, 0, Math.PI * 2);
    ctx.fill();

    // AI badge for agents (top-left)
    if (type === 'agent') {
        const badgeX = x - radius * 0.8;
        const badgeY = y - radius * 0.8;
        ctx.fillStyle = '#0f172a';
        ctx.beginPath();
        ctx.arc(badgeX, badgeY, 7, 0, Math.PI * 2);
        ctx.fill();
        ctx.font = 'bold 6px sans-serif';
        ctx.fillStyle = '#6366f1';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('AI', badgeX, badgeY);
        ctx.textBaseline = 'alphabetic';
        ctx.textAlign = 'left';
    }

    // Name badge below
    const labelText = name || '?';
    ctx.font = '10px monospace';
    const tw = ctx.measureText(labelText).width;
    const lbX = x - tw / 2 - 5;
    const lbY = y + radius + 5;
    ctx.fillStyle = 'rgba(0,0,0,0.6)';
    roundRect(ctx, lbX, lbY, tw + 10, 14, 3);
    ctx.fill();
    ctx.fillStyle = isPlayer ? '#a5b4fc' : '#9ca3af';
    ctx.textAlign = 'center';
    ctx.fillText(labelText, x, lbY + 10);
    ctx.textAlign = 'left';

    // Speech bubble
    if (bubbleAlpha > 0 && bubble) {
        drawSpeechBubble(ctx, x, y - radius - 4, bubble, bubbleAlpha);
    }
}

// ─── WorldEngine ──────────────────────────────────────────────────────────────
export class WorldEngine {
    constructor() {
        this.camera = { x: 0, y: 0 };
        this.player = null;
        this.entities = [];
        this.keys = {};
        this.viewportW = 1280;
        this.viewportH = 720;
        this.nearbyEntity = null;
        this.meetingRooms = [
            { id: 'boardroom', x: 2005, y: 55,  w: 340, h: 260, label: 'BOARDROOM',        accent: '#f59e0b' },
            { id: 'meeting1',  x: 2005, y: 365, w: 340, h: 255, label: 'SALA DE REUNIÃO',  accent: '#6366f1' },
        ];
        this._lastNow = 0;
    }

    setViewport(w, h) {
        this.viewportW = w;
        this.viewportH = h;
    }

    setPlayer(user) {
        if (!user) { this.player = null; return; }
        const existing = this.player && this.player.id === user.id ? this.player : null;
        this.player = {
            id: user.id,
            name: user.name || 'Utilizador',
            avatar: user.avatar || '👤',
            color: LEVEL_COLOR[user.level] || '#4f46e5',
            state: 'available',
            type: 'human',
            x: existing ? existing.x : 1200,
            y: existing ? existing.y : 690,
            radius: 20,
            bubble: '',
            bubbleAlpha: 0,
            animTimer: 0,
        };
    }

    handleKey(key, down) {
        this.keys[key] = down;
    }

    setAgents(squadId, nodes) {
        const zoneId = SQUAD_ZONE[squadId];
        if (!zoneId) return;
        const slots = getDeskSlots(zoneId);
        const filtered = (nodes || []).filter(n => n.id !== 'human-user');
        const color = SQUAD_COLOR[squadId] || '#4f46e5';

        // Remove old agents from this squad
        this.entities = this.entities.filter(e => !(e.type === 'agent' && e.squadId === squadId));

        filtered.slice(0, slots.length).forEach((node, i) => {
            const slot = slots[i];
            const existing = this.entities.find(e => e.id === node.id);
            if (existing) {
                existing.x = slot.x;
                existing.y = slot.y + 55;
                existing.deskX = slot.x;
                existing.deskY = slot.y;
            } else {
                this.entities.push({
                    id: node.id,
                    name: node.data?.label || node.id,
                    type: 'agent',
                    squadId,
                    color,
                    state: 'idle',
                    x: slot.x,
                    y: slot.y + 55,
                    deskX: slot.x,
                    deskY: slot.y,
                    radius: 16,
                    animTimer: Math.random() * Math.PI * 2,
                    bubble: '',
                    bubbleAlpha: 0,
                });
            }
        });
    }

    setHumans(users) {
        // Remove old humans
        this.entities = this.entities.filter(e => e.type !== 'human');
        (users || []).forEach((u, i) => {
            this.entities.push({
                id: u.id,
                name: u.name || 'Utilizador',
                type: 'human',
                level: u.level,
                avatar: u.avatar || '👤',
                color: LEVEL_COLOR[u.level] || '#475569',
                state: 'available',
                x: 300 + i * 130,
                y: 695,
                radius: 18,
                animTimer: i * 0.5,
                bubble: '',
                bubbleAlpha: 0,
            });
        });
    }

    onLog(agentLabel, action) {
        const agentEntities = this.entities.filter(e => e.type === 'agent');
        const agent = agentEntities.find(a =>
            a.name === agentLabel ||
            agentLabel.replace('@', '').toLowerCase().includes(a.id.split('-')[0].toLowerCase()) ||
            a.id.toLowerCase().includes(agentLabel.replace('@', '').toLowerCase())
        );
        if (!agent) return;

        // Deactivate all other agents
        agentEntities.forEach(a => {
            if (a.id !== agent.id) {
                a.state = 'idle';
                a.bubbleAlpha = Math.max(0, a.bubbleAlpha - 0.5);
            }
        });

        agent.state = 'working';
        agent.bubble = action;
        agent.bubbleAlpha = 1.0;
    }

    resetAll() {
        this.entities.filter(e => e.type === 'agent').forEach(a => {
            a.state = 'idle';
            a.bubbleAlpha = 0;
        });
    }

    getClickTarget(vx, vy) {
        // Convert viewport coords to world coords
        const wx = vx + this.camera.x;
        const wy = vy + this.camera.y;

        // Check entities
        for (const entity of this.entities) {
            const dx = entity.x - wx;
            const dy = entity.y - wy;
            if (Math.sqrt(dx * dx + dy * dy) <= entity.radius + 8) {
                return { type: 'entity', entity };
            }
        }

        // Check player
        if (this.player) {
            const dx = this.player.x - wx;
            const dy = this.player.y - wy;
            if (Math.sqrt(dx * dx + dy * dy) <= this.player.radius + 8) {
                return { type: 'player', entity: this.player };
            }
        }

        // Check meeting rooms
        for (const room of this.meetingRooms) {
            if (wx >= room.x && wx <= room.x + room.w && wy >= room.y && wy <= room.y + room.h) {
                return { type: 'meeting', room };
            }
        }

        return null;
    }

    update(dt) {
        const speed = 220;
        const now = Date.now();
        this._lastNow = now;

        if (this.player) {
            let vx = 0;
            let vy = 0;

            if (this.keys['ArrowLeft']  || this.keys['a'] || this.keys['A']) vx -= 1;
            if (this.keys['ArrowRight'] || this.keys['d'] || this.keys['D']) vx += 1;
            if (this.keys['ArrowUp']    || this.keys['w'] || this.keys['W']) vy -= 1;
            if (this.keys['ArrowDown']  || this.keys['s'] || this.keys['S']) vy += 1;

            // Normalize diagonal
            if (vx !== 0 && vy !== 0) {
                const len = Math.sqrt(vx * vx + vy * vy);
                vx /= len;
                vy /= len;
            }

            this.player.x += vx * speed * dt;
            this.player.y += vy * speed * dt;

            // Clamp to world bounds
            const margin = 60;
            this.player.x = Math.max(margin, Math.min(WORLD_W - margin, this.player.x));
            this.player.y = Math.max(margin, Math.min(WORLD_H - margin, this.player.y));

            // Camera follow: center on player, clamp to world
            this.camera.x = Math.max(0, Math.min(WORLD_W - this.viewportW, this.player.x - this.viewportW / 2));
            this.camera.y = Math.max(0, Math.min(WORLD_H - this.viewportH, this.player.y - this.viewportH / 2));
        }

        // Entity anim timers
        this.entities.forEach(e => {
            e.animTimer += dt;
        });

        // Bubble fade for non-working agents
        this.entities.filter(en => en.type === 'agent' && en.state !== 'working').forEach(a => {
            if (a.bubbleAlpha > 0) {
                a.bubbleAlpha = Math.max(0, a.bubbleAlpha - dt * 0.4);
            }
        });

        // Nearby entity detection
        if (this.player) {
            let nearest = null;
            let nearestDist = 70;
            this.entities.forEach(e => {
                const dx = e.x - this.player.x;
                const dy = e.y - this.player.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < nearestDist) {
                    nearestDist = dist;
                    nearest = e;
                }
            });
            this.nearbyEntity = nearest;
        } else {
            this.nearbyEntity = null;
        }
    }

    render(ctx) {
        const now = this._lastNow || Date.now();

        ctx.save();
        ctx.translate(-this.camera.x, -this.camera.y);

        // World background
        ctx.fillStyle = '#080b12';
        ctx.fillRect(0, 0, WORLD_W, WORLD_H);

        // Faint world grid
        ctx.strokeStyle = '#0d1018';
        ctx.lineWidth = 0.5;
        for (let x = 0; x <= WORLD_W; x += 80) {
            ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, WORLD_H); ctx.stroke();
        }
        for (let y = 0; y <= WORLD_H; y += 80) {
            ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(WORLD_W, y); ctx.stroke();
        }

        // Draw all zones
        ZONES.forEach(zone => drawZone(ctx, zone, now));

        // Draw walls
        drawWalls(ctx);

        // Draw meeting room furniture
        this.meetingRooms.forEach(room => {
            const cx = room.x + room.w / 2;
            const cy = room.y + room.h / 2;
            drawMeetingTable(ctx, cx, cy, room.w * 0.72, room.h * 0.52, room.accent, now);

            // Room label
            ctx.font = 'bold 10px sans-serif';
            ctx.fillStyle = room.accent + '99';
            ctx.textAlign = 'center';
            ctx.fillText('▶ ' + room.label, cx, room.y + 22);
            ctx.textAlign = 'left';

            // Click hint
            ctx.font = '9px monospace';
            ctx.fillStyle = room.accent + '44';
            ctx.textAlign = 'center';
            ctx.fillText('Clica para convocar reunião', cx, room.y + room.h - 14);
            ctx.textAlign = 'left';
        });

        // Draw break area
        drawBreakArea(ctx, now);

        // Draw agent desks
        this.entities.filter(e => e.type === 'agent' && e.deskX !== undefined).forEach(e => {
            drawDesk(ctx, e.deskX, e.deskY, e.color, e.state === 'working', now);
        });

        // Collect all entities + player, z-sort by y
        const allRender = [...this.entities];
        if (this.player) allRender.push(this.player);
        allRender.sort((a, b) => a.y - b.y);

        // Player zone label
        let playerZone = null;
        if (this.player) {
            playerZone = ZONES.find(z =>
                z.id !== 'corridor' && z.label &&
                this.player.x >= z.x && this.player.x <= z.x + z.w &&
                this.player.y >= z.y && this.player.y <= z.y + z.h
            );
        }

        allRender.forEach(entity => {
            const isPlayer = this.player && entity.id === this.player.id && entity.type !== 'agent';
            const isNearby = this.nearbyEntity && entity.id === this.nearbyEntity.id;
            drawEntity(ctx, entity, isPlayer, isNearby, now);
        });

        // Zone label tooltip above player
        if (playerZone && this.player) {
            const px = this.player.x;
            const py = this.player.y - this.player.radius - 55;
            ctx.font = 'bold 11px sans-serif';
            const tw = ctx.measureText(playerZone.label).width;
            const pw = tw + 20;
            ctx.fillStyle = 'rgba(0,0,0,0.65)';
            roundRect(ctx, px - pw / 2, py - 9, pw, 18, 9);
            ctx.fill();
            ctx.fillStyle = playerZone.accent + 'cc';
            ctx.textAlign = 'center';
            ctx.fillText(playerZone.label, px, py + 4);
            ctx.textAlign = 'left';
        }

        ctx.restore();

        // Minimap (NOT translated)
        this._renderMinimap(ctx, now);
    }

    _renderMinimap(ctx, now) {
        const scale = 0.07;
        const mmW = Math.round(WORLD_W * scale);
        const mmH = Math.round(WORLD_H * scale);
        const mmX = this.viewportW - mmW - 16;
        const mmY = this.viewportH - mmH - 16;
        const pad = 8;

        // Background
        ctx.fillStyle = 'rgba(5,8,16,0.88)';
        roundRect(ctx, mmX - pad, mmY - pad, mmW + pad * 2, mmH + pad * 2, 8);
        ctx.fill();
        ctx.strokeStyle = 'rgba(55,65,81,0.5)';
        ctx.lineWidth = 1;
        roundRect(ctx, mmX - pad, mmY - pad, mmW + pad * 2, mmH + pad * 2, 8);
        ctx.stroke();

        // Draw zones as tiny fills
        ZONES.forEach(zone => {
            if (!zone.label) return; // skip corridor
            ctx.fillStyle = zone.accent + '30';
            ctx.fillRect(
                mmX + zone.x * scale,
                mmY + zone.y * scale,
                zone.w * scale,
                zone.h * scale
            );
            ctx.strokeStyle = zone.accent + '55';
            ctx.lineWidth = 0.5;
            ctx.strokeRect(
                mmX + zone.x * scale,
                mmY + zone.y * scale,
                zone.w * scale,
                zone.h * scale
            );
        });

        // Draw entities as colored dots
        this.entities.forEach(e => {
            const stateColor = STATE_COLORS[e.state] || STATE_COLORS.idle;
            ctx.fillStyle = stateColor;
            ctx.beginPath();
            ctx.arc(mmX + e.x * scale, mmY + e.y * scale, 2, 0, Math.PI * 2);
            ctx.fill();
        });

        // Player as white dot
        if (this.player) {
            ctx.fillStyle = '#ffffff';
            ctx.beginPath();
            ctx.arc(mmX + this.player.x * scale, mmY + this.player.y * scale, 3, 0, Math.PI * 2);
            ctx.fill();
        }

        // Viewport rect
        ctx.strokeStyle = 'rgba(255,255,255,0.2)';
        ctx.lineWidth = 1;
        ctx.strokeRect(
            mmX + this.camera.x * scale,
            mmY + this.camera.y * scale,
            this.viewportW * scale,
            this.viewportH * scale
        );
    }
}
