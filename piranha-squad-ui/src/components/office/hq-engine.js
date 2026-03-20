// ============================================================
// Piranha Global — HQ Engine
// Canvas 2D · Multi-room Virtual Office · Top-down pixel art
// ============================================================

export const HQ_W = 1280;
export const HQ_H = 600;

// ─── Room definitions ─────────────────────────────────────────────────────────
export const ROOM_DEFS = [
    {
        id: 'piranha-leads',
        label: 'SALES',
        icon: '🦈',
        accent: '#ef4444',
        floor: '#100505',
        border: '#7f1d1d',
        x: 15, y: 15, w: 220, h: 215,
        slotsKey: 'small3',
    },
    {
        id: 'piranha-workshops',
        label: 'WORKSHOPS',
        icon: '🎓',
        accent: '#3b82f6',
        floor: '#020a14',
        border: '#1e3a5f',
        x: 255, y: 15, w: 220, h: 215,
        slotsKey: 'small3',
    },
    {
        id: 'piranha-comms',
        label: 'COMMS',
        icon: '📢',
        accent: '#a855f7',
        floor: '#0b0414',
        border: '#4c1d95',
        x: 495, y: 15, w: 220, h: 215,
        slotsKey: 'comms4',
    },
    {
        id: 'piranha-supplies',
        label: 'SUPPLIES',
        icon: '📦',
        accent: '#f59e0b',
        floor: '#0f0800',
        border: '#78350f',
        x: 15, y: 310, w: 340, h: 225,
        slotsKey: 'supplies',
    },
    {
        id: 'piranha-studio',
        label: 'ESTÚDIO',
        icon: '🏢',
        accent: '#10b981',
        floor: '#020d07',
        border: '#064e3b',
        x: 375, y: 310, w: 355, h: 225,
        slotsKey: 'studio',
    },
];

// ─── Desk slot offsets (relative to room x,y) ────────────────────────────────
const DESK_SLOTS = {
    small3: [
        { dx: 25, dy: 55 }, { dx: 90, dy: 55 }, { dx: 155, dy: 55 },
        { dx: 25, dy: 140 }, { dx: 90, dy: 140 }, { dx: 155, dy: 140 },
    ],
    comms4: [
        { dx: 15, dy: 55 }, { dx: 65, dy: 55 }, { dx: 115, dy: 55 }, { dx: 165, dy: 55 },
        { dx: 15, dy: 140 }, { dx: 65, dy: 140 }, { dx: 115, dy: 140 }, { dx: 165, dy: 140 },
    ],
    supplies: [
        { dx: 20, dy: 60 }, { dx: 90, dy: 60 }, { dx: 160, dy: 60 }, { dx: 235, dy: 60 },
        { dx: 20, dy: 150 }, { dx: 90, dy: 150 }, { dx: 160, dy: 150 }, { dx: 235, dy: 150 },
    ],
    studio: [
        { dx: 20, dy: 60 }, { dx: 110, dy: 60 }, { dx: 200, dy: 60 },
        { dx: 20, dy: 150 }, { dx: 110, dy: 150 }, { dx: 200, dy: 150 },
    ],
};

// ─── Meeting room ─────────────────────────────────────────────────────────────
export const MEETING_DEF = {
    x: 740, y: 15, w: 525, h: 555,
    label: 'SALA DE REUNIÃO',
    icon: '🪑',
    accent: '#6366f1',
    floor: '#08080f',
    border: '#312e81',
    tableX: 835, tableY: 140, tableW: 330, tableH: 255,
};

// ─── Meeting seats (absolute pixel positions, 14 seats) ──────────────────────
const MEETING_SEATS = [
    // Top row (5)
    { x: 860, y: 112 }, { x: 925, y: 112 }, { x: 990, y: 112 }, { x: 1055, y: 112 }, { x: 1120, y: 112 },
    // Bottom row (5)
    { x: 860, y: 430 }, { x: 925, y: 430 }, { x: 990, y: 430 }, { x: 1055, y: 430 }, { x: 1120, y: 430 },
    // Left (2)
    { x: 800, y: 200 }, { x: 800, y: 330 },
    // Right (2)
    { x: 1190, y: 200 }, { x: 1190, y: 330 },
];

// ─── Corridor ─────────────────────────────────────────────────────────────────
const CORRIDOR = { x: 15, y: 240, w: 710, h: 65 };

// ─── Squad shirt colors ───────────────────────────────────────────────────────
const SQUAD_COLOR = {
    'piranha-leads': '#b91c1c',
    'piranha-workshops': '#1d4ed8',
    'piranha-comms': '#7c3aed',
    'piranha-supplies': '#b45309',
    'piranha-studio': '#065f46',
};

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

// ─── Helper: drawHQDesk ───────────────────────────────────────────────────────
function drawHQDesk(ctx, x, y, active, accentColor) {
    const now = Date.now();

    // Desk body
    ctx.fillStyle = '#3a2e1e';
    ctx.fillRect(x, y + 12, 34, 24);
    ctx.fillStyle = '#4e3d28';
    ctx.fillRect(x, y + 12, 34, 5);

    // Monitor frame
    ctx.fillStyle = '#111827';
    ctx.strokeStyle = '#374151';
    ctx.lineWidth = 1;
    roundRect(ctx, x + 4, y, 26, 14, 2);
    ctx.fill(); ctx.stroke();

    // Screen
    if (active) {
        ctx.fillStyle = '#001a1a';
        ctx.fillRect(x + 5, y + 1, 24, 12);

        // Scrolling code lines
        const scroll = (now / 120) % 10;
        ctx.fillStyle = '#22d3ee';
        for (let i = 0; i < 3; i++) {
            const lineW = 4 + Math.abs(Math.sin(i * 1.7 + now / 500)) * 14;
            const lineY = y + 2 + ((i * 4 + scroll) % 11);
            ctx.fillRect(x + 6, lineY, lineW, 1);
        }

        // Desk glow
        ctx.save();
        ctx.shadowColor = accentColor;
        ctx.shadowBlur = 10;
        ctx.globalAlpha = 0.15 + Math.sin(now / 400) * 0.08;
        ctx.fillStyle = accentColor;
        ctx.fillRect(x, y + 12, 34, 24);
        ctx.restore();
    } else {
        ctx.fillStyle = '#0a0f14';
        ctx.fillRect(x + 5, y + 1, 24, 12);
        ctx.fillStyle = '#1f2937';
        ctx.fillRect(x + 14, y + 6, 4, 2);
    }

    // Monitor stand
    ctx.fillStyle = '#374151';
    ctx.fillRect(x + 15, y + 14, 4, 2);

    // Desk legs
    ctx.fillStyle = '#2a1e10';
    ctx.fillRect(x + 2, y + 34, 3, 6);
    ctx.fillRect(x + 29, y + 34, 3, 6);
}

// ─── Helper: drawHQChar ──────────────────────────────────────────────────────
function drawHQChar(ctx, x, y, color, state, frame, scale = 2.0) {
    const s = scale;
    const c = color || '#374151';
    const ox = x - 5 * s;
    const oy = y - 14 * s;

    ctx.save();

    // Head
    ctx.fillStyle = '#d4a76a';
    ctx.fillRect(ox + 3 * s, oy, 4 * s, 4 * s);

    // Eyes
    ctx.fillStyle = '#1a0a00';
    ctx.fillRect(ox + 4 * s, oy + s, s, s);
    ctx.fillRect(ox + 6 * s, oy + s, s, s);

    // Smile when typing
    if (state === 'typing') {
        ctx.fillStyle = '#1a0a00';
        ctx.fillRect(ox + 4 * s, oy + 3 * s, s, s);
        ctx.fillRect(ox + 6 * s, oy + 3 * s, s, s);
    }

    // Body
    ctx.fillStyle = c;
    ctx.fillRect(ox + 2 * s, oy + 4 * s, 6 * s, 5 * s);

    // Arms — bob when typing
    const armBob = (state === 'typing' && frame % 2 === 0) ? s : 0;
    ctx.fillRect(ox, oy + 5 * s + armBob, 2 * s, 3 * s - armBob);
    ctx.fillRect(ox + 8 * s, oy + 5 * s + armBob, 2 * s, 3 * s - armBob);

    // Legs — walk cycle or standing
    ctx.fillStyle = '#1e293b';
    if (state === 'walking') {
        const phase = frame % 4;
        const l1 = phase < 2 ? 0 : s;
        const l2 = phase < 2 ? s : 0;
        ctx.fillRect(ox + 2 * s, oy + 9 * s + l1, 3 * s, 5 * s - l1);
        ctx.fillRect(ox + 6 * s, oy + 9 * s + l2, 3 * s, 5 * s - l2);
    } else {
        ctx.fillRect(ox + 2 * s, oy + 9 * s, 3 * s, 5 * s);
        ctx.fillRect(ox + 6 * s, oy + 9 * s, 3 * s, 5 * s);
    }

    // Shoes
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(ox + s, oy + 12 * s, 3 * s, 2 * s);
    ctx.fillRect(ox + 6 * s, oy + 12 * s, 3 * s, 2 * s);

    ctx.restore();
}

// ─── Helper: drawHQBadge ─────────────────────────────────────────────────────
function drawHQBadge(ctx, cx, y, label, active, color) {
    ctx.font = 'bold 8px monospace';
    const display = label.length > 12 ? label.substring(0, 12) : label;
    const tw = ctx.measureText(display).width;
    const bw = tw + 8;
    const bx = cx - bw / 2;

    ctx.fillStyle = active ? '#083344' : '#1f2937';
    ctx.strokeStyle = active ? (color || '#22d3ee') + '80' : '#37415180';
    ctx.lineWidth = 1;
    roundRect(ctx, bx, y, bw, 12, 2);
    ctx.fill(); ctx.stroke();

    ctx.fillStyle = active ? (color || '#22d3ee') : '#6b7280';
    ctx.textAlign = 'center';
    ctx.fillText(display, cx, y + 9);
    ctx.textAlign = 'left';
}

// ─── Helper: drawBubble ──────────────────────────────────────────────────────
function drawBubble(ctx, cx, cy, text, alpha) {
    if (alpha <= 0 || !text) return;
    const display = text.length > 28 ? text.substring(0, 28) + '…' : text;

    ctx.save();
    ctx.globalAlpha = Math.min(1, alpha);
    ctx.font = 'bold 8px monospace';
    const tw = ctx.measureText(display).width;
    const bw = tw + 10;
    const bh = 16;
    const bx = cx - bw / 2;
    const bubbleY = cy - 60;

    ctx.fillStyle = '#ffffff';
    ctx.strokeStyle = '#d1d5db';
    ctx.lineWidth = 0.5;
    roundRect(ctx, bx, bubbleY, bw, bh, 3);
    ctx.fill(); ctx.stroke();

    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.moveTo(cx - 3, bubbleY + bh);
    ctx.lineTo(cx + 3, bubbleY + bh);
    ctx.lineTo(cx, bubbleY + bh + 5);
    ctx.closePath(); ctx.fill();

    ctx.fillStyle = '#111827';
    ctx.textAlign = 'center';
    ctx.fillText(display, cx, bubbleY + 11);
    ctx.textAlign = 'left';
    ctx.restore();
}

// ─── Helper: drawRoom ─────────────────────────────────────────────────────────
function drawRoom(ctx, roomDef) {
    const { x, y, w, h, floor, border, accent, icon, label } = roomDef;

    // Floor fill
    ctx.fillStyle = floor;
    ctx.fillRect(x, y, w, h);

    // Subtle inner grid
    ctx.strokeStyle = border + '20';
    ctx.lineWidth = 0.5;
    for (let gx = x; gx < x + w; gx += 30) {
        ctx.beginPath(); ctx.moveTo(gx, y); ctx.lineTo(gx, y + h); ctx.stroke();
    }
    for (let gy = y; gy < y + h; gy += 30) {
        ctx.beginPath(); ctx.moveTo(x, gy); ctx.lineTo(x + w, gy); ctx.stroke();
    }

    // Room outline
    ctx.strokeStyle = border;
    ctx.lineWidth = 1;
    ctx.strokeRect(x, y, w, h);

    // Room label (icon + name) centered at top
    ctx.font = 'bold 10px monospace';
    const labelText = `${icon} ${label}`;
    const tw = ctx.measureText(labelText).width;
    const lx = x + (w - tw) / 2;

    ctx.fillStyle = accent + 'cc';
    ctx.fillText(labelText, lx, y + 16);
}

// ─── Helper: drawMeetingRoom ─────────────────────────────────────────────────
function drawMeetingRoom(ctx, meetingDef, isActive) {
    const { x, y, w, h, floor, border, accent, tableX, tableY, tableW, tableH } = meetingDef;
    const now = Date.now();

    // Floor fill
    ctx.fillStyle = floor;
    ctx.fillRect(x, y, w, h);

    // Subtle grid
    ctx.strokeStyle = border + '20';
    ctx.lineWidth = 0.5;
    for (let gx = x; gx < x + w; gx += 30) {
        ctx.beginPath(); ctx.moveTo(gx, y); ctx.lineTo(gx, y + h); ctx.stroke();
    }
    for (let gy = y; gy < y + h; gy += 30) {
        ctx.beginPath(); ctx.moveTo(x, gy); ctx.lineTo(x + w, gy); ctx.stroke();
    }

    // Border (pulse glow if active)
    if (isActive) {
        ctx.save();
        const pulse = 0.3 + Math.sin(now / 400) * 0.2;
        ctx.shadowColor = accent;
        ctx.shadowBlur = 16 * pulse;
        ctx.strokeStyle = accent;
        ctx.lineWidth = 1.5;
        ctx.strokeRect(x, y, w, h);
        ctx.restore();
    } else {
        ctx.strokeStyle = border;
        ctx.lineWidth = 1;
        ctx.strokeRect(x, y, w, h);
    }

    // Label at top
    ctx.font = 'bold 11px monospace';
    const labelText = `🪑 SALA DE REUNIÃO`;
    const tw = ctx.measureText(labelText).width;
    ctx.fillStyle = accent + 'cc';
    ctx.fillText(labelText, x + (w - tw) / 2, y + 18);

    // Conference table
    ctx.fillStyle = '#1a1a2e';
    roundRect(ctx, tableX, tableY, tableW, tableH, 8);
    ctx.fill();

    // Table inner surface
    ctx.fillStyle = '#1e1e3a';
    roundRect(ctx, tableX + 6, tableY + 6, tableW - 12, tableH - 12, 5);
    ctx.fill();

    // Table grid detail
    ctx.strokeStyle = '#312e81' + '40';
    ctx.lineWidth = 0.5;
    for (let gx = tableX + 6; gx < tableX + tableW - 6; gx += 30) {
        ctx.beginPath(); ctx.moveTo(gx, tableY + 6); ctx.lineTo(gx, tableY + tableH - 6); ctx.stroke();
    }
    for (let gy = tableY + 6; gy < tableY + tableH - 6; gy += 30) {
        ctx.beginPath(); ctx.moveTo(tableX + 6, gy); ctx.lineTo(tableX + tableW - 6, gy); ctx.stroke();
    }

    // Table border
    ctx.strokeStyle = '#4f46e5' + '60';
    ctx.lineWidth = 1;
    roundRect(ctx, tableX, tableY, tableW, tableH, 8);
    ctx.stroke();

    // If not active: hint text
    if (!isActive) {
        ctx.font = '9px monospace';
        ctx.fillStyle = '#4f46e5' + '50';
        ctx.textAlign = 'center';
        ctx.fillText('Clica para convocar reunião', x + w / 2, y + h - 20);
        ctx.textAlign = 'left';
    }
}

// ─── HQAgent ──────────────────────────────────────────────────────────────────
export class HQAgent {
    constructor(id, label, deskX, deskY, color) {
        this.id = id;
        this.label = label;
        this.deskX = deskX;
        this.deskY = deskY;
        this.color = color;

        this.px = deskX + 17;
        this.py = deskY + 56;

        this.state = 'idle';
        this.frame = 0;
        this.frameTimer = 0;
        this.isActive = false;
        this.inMeeting = false;
        this.bubbleText = '';
        this.bubbleAlpha = 0;
        this.bobOffset = Math.random() * Math.PI * 2;
    }
}

// ─── HQHuman ──────────────────────────────────────────────────────────────────
export class HQHuman {
    constructor(id, name, level, avatar) {
        this.id = id;
        this.name = name;
        this.level = level;
        this.avatar = avatar || '👤';

        const levelColors = {
            leadership: '#dc2626',
            'c-level': '#2563eb',
            director: '#9333ea',
            manager: '#d97706',
            specialist: '#6b7280',
        };
        this.color = levelColors[level] || levelColors.specialist;

        this.px = 100 + Math.random() * 500;
        this.py = CORRIDOR.y + 35;

        this.state = 'idle';
        this.frame = 0;
        this.frameTimer = 0;
        this.inMeeting = false;
        this.seatIdx = -1;
    }
}

// ─── HQEngine ─────────────────────────────────────────────────────────────────
export class HQEngine {
    constructor() {
        this.agentsByRoom = {};
        this.humanUsers = [];
        this.meetingActive = false;
        this.meetingParticipants = [];
    }

    setAgents(squadId, nodes) {
        const roomDef = ROOM_DEFS.find(r => r.id === squadId);
        if (!roomDef) return;
        const slots = DESK_SLOTS[roomDef.slotsKey] || [];
        const color = SQUAD_COLOR[squadId] || '#374151';
        const filtered = (nodes || []).filter(n => n.id !== 'human-user');
        this.agentsByRoom[squadId] = filtered.slice(0, slots.length).map((node, i) => {
            const slot = slots[i];
            const deskX = roomDef.x + slot.dx;
            const deskY = roomDef.y + slot.dy;
            const label = node.data?.label || node.id;
            return new HQAgent(node.id, label, deskX, deskY, color);
        });
    }

    setHumans(users) {
        this.humanUsers = (users || []).map(u => new HQHuman(u.id, u.name, u.level, u.avatar));
    }

    startMeeting(participants) {
        this.meetingActive = true;
        this.meetingParticipants = participants.map((p, i) => ({ ...p, seatIdx: i }));
        const allAgents = this._allAgents();
        allAgents.forEach(agent => {
            if (participants.some(p => p.type === 'agent' && p.agentId === agent.id)) {
                agent.inMeeting = true;
            }
        });
    }

    endMeeting() {
        this.meetingActive = false;
        this.meetingParticipants = [];
        this._allAgents().forEach(a => { a.inMeeting = false; });
    }

    onLog(agentLabel, action) {
        const allAgents = this._allAgents();
        const agent = allAgents.find(a =>
            a.label === agentLabel ||
            agentLabel.replace('@', '').toLowerCase().includes(a.id.split('-')[0].toLowerCase())
        );
        if (!agent) return;

        allAgents.forEach(a => {
            if (a.id !== agent.id && a.isActive) {
                a.isActive = false;
                a.state = 'idle';
            }
        });

        agent.isActive = true;
        agent.state = 'typing';
        agent.bubbleText = action;
        agent.bubbleAlpha = 1;
    }

    resetAll() {
        this._allAgents().forEach(a => {
            a.isActive = false;
            a.state = 'idle';
            a.bubbleAlpha = 0;
        });
    }

    getClickTarget(vx, vy) {
        const m = MEETING_DEF;
        if (vx >= m.x && vx <= m.x + m.w && vy >= m.y && vy <= m.y + m.h) {
            return { type: 'meeting' };
        }
        return null;
    }

    _allAgents() {
        return Object.values(this.agentsByRoom).flat();
    }

    update(dt) {
        const TYPE_FRAME_S = 0.28;
        const IDLE_FRAME_S = 0.5;

        this._allAgents().forEach(a => {
            a.frameTimer += dt;
            const dur = a.state === 'typing' ? TYPE_FRAME_S : IDLE_FRAME_S;
            if (a.frameTimer >= dur) {
                a.frameTimer = 0;
                a.frame = (a.frame + 1) % 4;
            }
            if (!a.isActive && a.bubbleAlpha > 0) {
                a.bubbleAlpha = Math.max(0, a.bubbleAlpha - dt * 0.5);
            }
        });

        this.humanUsers.forEach(h => {
            h.frameTimer += dt;
            if (h.frameTimer >= IDLE_FRAME_S) {
                h.frameTimer = 0;
                h.frame = (h.frame + 1) % 4;
            }
        });
    }

    render(ctx) {
        const now = Date.now();

        // Background
        ctx.fillStyle = '#060a0f';
        ctx.fillRect(0, 0, HQ_W, HQ_H);

        // Background grid
        ctx.strokeStyle = '#0d1520';
        ctx.lineWidth = 0.5;
        for (let x = 0; x < HQ_W; x += 40) {
            ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, HQ_H); ctx.stroke();
        }
        for (let y = 0; y < HQ_H; y += 40) {
            ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(HQ_W, y); ctx.stroke();
        }

        // Corridor
        ctx.fillStyle = '#0a0f14';
        ctx.fillRect(CORRIDOR.x, CORRIDOR.y, CORRIDOR.w, CORRIDOR.h);
        ctx.strokeStyle = '#1a2535';
        ctx.lineWidth = 1;
        ctx.strokeRect(CORRIDOR.x, CORRIDOR.y, CORRIDOR.w, CORRIDOR.h);
        ctx.font = '8px monospace';
        ctx.fillStyle = '#1a2535';
        ctx.fillText('CORREDOR', CORRIDOR.x + 10, CORRIDOR.y + 14);

        // Draw rooms
        ROOM_DEFS.forEach(r => drawRoom(ctx, r));

        // Draw meeting room
        drawMeetingRoom(ctx, MEETING_DEF, this.meetingActive, now);

        // Draw desks (only for agents NOT in meeting)
        Object.entries(this.agentsByRoom).forEach(([squadId, agents]) => {
            const roomDef = ROOM_DEFS.find(r => r.id === squadId);
            if (!roomDef) return;
            agents.forEach(agent => {
                if (!agent.inMeeting) {
                    drawHQDesk(ctx, agent.deskX, agent.deskY, agent.isActive, roomDef.accent);
                }
            });
        });

        // Collect all entities to render, z-sorted by y
        const renderItems = [];

        // Agents at desk (not in meeting)
        this._allAgents().forEach(agent => {
            if (!agent.inMeeting) {
                renderItems.push({ type: 'agent', entity: agent, px: agent.px, py: agent.py });
            }
        });

        // Meeting participants at seats
        if (this.meetingActive) {
            this.meetingParticipants.forEach((p, i) => {
                const seat = MEETING_SEATS[i];
                if (!seat) return;
                if (p.type === 'agent') {
                    const agent = this._allAgents().find(a => a.id === p.agentId);
                    if (agent) {
                        renderItems.push({ type: 'agent-meeting', entity: agent, px: seat.x, py: seat.y });
                    }
                } else if (p.type === 'human') {
                    const human = this.humanUsers.find(h => h.id === p.userId);
                    if (human) {
                        renderItems.push({ type: 'human-meeting', entity: human, px: seat.x, py: seat.y });
                    }
                }
            });
        }

        // Human users in corridor (not in meeting)
        this.humanUsers.forEach(human => {
            if (!human.inMeeting) {
                renderItems.push({ type: 'human', entity: human, px: human.px, py: human.py });
            }
        });

        // Z-sort by y
        renderItems.sort((a, b) => a.py - b.py);

        renderItems.forEach(item => {
            const { entity, px, py } = item;
            const isActive = entity.isActive || false;
            const color = entity.color;
            const state = entity.state || 'idle';
            const frame = entity.frame || 0;
            const label = entity.label || entity.name || '';

            // Active glow
            if (isActive) {
                ctx.save();
                ctx.globalAlpha = 0.3 + Math.sin(now / 300) * 0.1;
                ctx.strokeStyle = color;
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.ellipse(px, py, 11, 4, 0, 0, Math.PI * 2);
                ctx.stroke();
                ctx.restore();
            }

            drawHQChar(ctx, px, py, color, state, frame, 2.0);
            drawHQBadge(ctx, px, py + 4, label, isActive, color);

            if (entity.bubbleAlpha > 0 && entity.bubbleText) {
                drawBubble(ctx, px, py, entity.bubbleText, entity.bubbleAlpha);
            }
        });
    }
}
