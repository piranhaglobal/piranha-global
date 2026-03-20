import { useState, useEffect, useRef } from 'react';
import { ArrowLeft, LogOut, LogIn } from 'lucide-react';
import { WorldEngine, WORLD_W, WORLD_H, ZONES, STATE_COLORS, STATE_LABELS } from './office/world-engine.js';
import LoginPage from './LoginPage.jsx';
import MeetingRoom from './MeetingRoom.jsx';
import EntityPanel from './EntityPanel.jsx';

export default function VirtualHQ({ currentUser, onLogin, onBack }) {
    const canvasRef = useRef(null);
    const engineRef = useRef(null);
    const rafRef = useRef(null);
    const lastTsRef = useRef(null);
    const prevLogRef = useRef(null);

    const [loading, setLoading] = useState(true);
    const [allAgents, setAllAgents] = useState([]); // flat list
    const [registeredUsers, setRegisteredUsers] = useState([]);
    const [organogramMembers, setOrganogramMembers] = useState([]);
    const [showMeeting, setShowMeeting] = useState(false);
    const [showLogin, setShowLogin] = useState(false);
    const [selectedEntity, setSelectedEntity] = useState(null);
    const [showChat, setShowChat] = useState(null);

    // ── Initialise engine once ──
    useEffect(() => {
        engineRef.current = new WorldEngine();
    }, []);

    // ── Keyboard listeners ──
    useEffect(() => {
        const onKeyDown = e => { engineRef.current?.handleKey(e.key, true); };
        const onKeyUp   = e => { engineRef.current?.handleKey(e.key, false); };
        window.addEventListener('keydown', onKeyDown);
        window.addEventListener('keyup',   onKeyUp);
        return () => {
            window.removeEventListener('keydown', onKeyDown);
            window.removeEventListener('keyup',   onKeyUp);
        };
    }, []);

    // ── Load squads + agents ──
    useEffect(() => {
        const loadAll = async () => {
            try {
                const squadsRes = await fetch('http://localhost:3001/api/squads');
                const squads = await squadsRes.json();

                const flat = [];
                await Promise.all(squads.map(async (squad) => {
                    try {
                        const r = await fetch(`http://localhost:3001/api/squad/${squad.id}`);
                        const cfg = await r.json();
                        const nodes = (cfg.agents || []).map(a => ({
                            id: a.id,
                            data: { label: a.activation || a.id },
                            squadId: squad.id,
                        }));
                        if (engineRef.current) engineRef.current.setAgents(squad.id, nodes);
                        nodes.filter(n => n.id !== 'human-user').forEach(n => flat.push(n));
                    } catch { /* squad load error */ }
                }));
                setAllAgents(flat);
            } catch { /* server offline */ }
            setLoading(false);
        };
        loadAll();
    }, []);

    // ── Load registered users ──
    useEffect(() => {
        const fetchUsers = async () => {
            try {
                const res = await fetch('http://localhost:3001/api/auth/users');
                const data = await res.json();
                setRegisteredUsers(data.users || []);
                if (engineRef.current) engineRef.current.setHumans(data.users || []);
            } catch { /* offline */ }
        };
        fetchUsers();
        const timer = setInterval(fetchUsers, 15000);
        return () => clearInterval(timer);
    }, []);

    // ── Load organogram members ──
    useEffect(() => {
        fetch('http://localhost:3001/api/organogram')
            .then(r => r.json())
            .then(d => setOrganogramMembers(d.members || []))
            .catch(() => {});
    }, []);

    // ── Update engine when currentUser changes ──
    useEffect(() => {
        if (engineRef.current) {
            // Set player avatar/character
            engineRef.current.setPlayer(currentUser);

            const usersToShow = currentUser
                ? [currentUser, ...registeredUsers.filter(u => u.id !== currentUser.id)]
                : registeredUsers;
            engineRef.current.setHumans(usersToShow);
        }
    }, [currentUser, registeredUsers]);

    // ── Canvas rendering loop ──
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const resize = () => {
            const p = canvas.parentElement;
            if (!p) return;
            canvas.width  = p.clientWidth;
            canvas.height = p.clientHeight;
            engineRef.current?.setViewport(p.clientWidth, p.clientHeight);
        };
        resize();
        const ro = new ResizeObserver(resize);
        ro.observe(canvas.parentElement);

        const tick = (ts) => {
            if (!lastTsRef.current) lastTsRef.current = ts;
            const dt = Math.min((ts - lastTsRef.current) / 1000, 0.05);
            lastTsRef.current = ts;

            const engine = engineRef.current;
            const ctx = canvas.getContext('2d');
            if (engine && ctx) {
                engine.update(dt);
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                engine.setViewport(canvas.width, canvas.height);
                engine.render(ctx);
            }
            rafRef.current = requestAnimationFrame(tick);
        };
        rafRef.current = requestAnimationFrame(tick);

        return () => {
            cancelAnimationFrame(rafRef.current);
            ro.disconnect();
        };
    }, []);

    // ── Click handler ──
    const handleCanvasClick = (e) => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const rect = canvas.getBoundingClientRect();

        const vx = (e.clientX - rect.left) * (canvas.width  / rect.width);
        const vy = (e.clientY - rect.top)  * (canvas.height / rect.height);

        const target = engineRef.current?.getClickTarget(vx, vy);
        if (target?.type === 'entity' || target?.type === 'player') {
            setSelectedEntity(target.entity);
        } else if (target?.type === 'meeting') {
            setShowMeeting(true);
        } else {
            setSelectedEntity(null);
        }
    };

    // ── Log polling ──
    useEffect(() => {
        let timer;
        const poll = async () => {
            try {
                const res  = await fetch('http://localhost:3001/api/logs?squad=piranha-dev');
                const data = await res.json();
                const engine = engineRef.current;
                if (data.logs?.length > 0) {
                    const ordered = [...data.logs].reverse();
                    const latest  = ordered[0];
                    const logKey  = `${latest.agent}:${latest.action}`;
                    if (engine && logKey !== prevLogRef.current) {
                        prevLogRef.current = logKey;
                        if (latest.agent !== 'system' && latest.agent !== '@human') {
                            engine.onLog(latest.agent, latest.action);
                        } else if (latest.agent === 'system') {
                            engine.resetAll();
                        }
                    }
                } else {
                    if (engine && prevLogRef.current !== null) {
                        engine.resetAll();
                        prevLogRef.current = null;
                    }
                }
            } catch { /* offline */ }
            timer = setTimeout(poll, 2000);
        };
        poll();
        return () => clearTimeout(timer);
    }, []);

    const handleLogout = () => {
        localStorage.removeItem('piranha_token');
        onLogin(null);
    };

    const handleLoginSuccess = (user, token) => {
        localStorage.setItem('piranha_token', token);
        onLogin(user);
        setShowLogin(false);
    };

    const allHumansForMeeting = currentUser
        ? [currentUser, ...registeredUsers.filter(u => u.id !== currentUser.id)]
        : registeredUsers;

    return (
        <div className="h-full w-full flex flex-col bg-[#060a0f] font-mono">
            {/* Header */}
            <header className="flex-shrink-0 h-12 bg-gray-950/90 border-b border-gray-800/60 backdrop-blur-md px-5 flex items-center justify-between z-10">
                <div className="flex items-center gap-4">
                    <button
                        onClick={onBack}
                        className="flex items-center gap-1.5 text-gray-500 hover:text-gray-300 transition-colors text-xs"
                    >
                        <ArrowLeft size={13} /> Voltar
                    </button>
                    <div className="w-px h-4 bg-gray-700" />
                    <div className="flex items-center gap-2">
                        <span className="text-base">🦈</span>
                        <span className="text-sm font-black text-white tracking-wider uppercase">
                            PIRANHA GLOBAL HQ
                        </span>
                    </div>
                    {loading && (
                        <span className="text-[10px] text-gray-600 animate-pulse">A carregar escritório...</span>
                    )}
                </div>

                <div className="flex items-center gap-3">
                    {currentUser ? (
                        <div className="flex items-center gap-3">
                            <div className="flex items-center gap-2 bg-gray-900/60 border border-gray-700/50 rounded-lg px-3 py-1.5">
                                <span className="text-base">{currentUser.avatar || '👤'}</span>
                                <div>
                                    <div className="text-xs font-semibold text-white leading-none">{currentUser.name}</div>
                                    <div className="text-[9px] text-gray-500 leading-none mt-0.5 capitalize">{currentUser.level}</div>
                                </div>
                            </div>
                            <button
                                onClick={handleLogout}
                                className="flex items-center gap-1.5 text-gray-500 hover:text-red-400 transition-colors text-xs border border-gray-700/50 hover:border-red-900/50 rounded-lg px-2.5 py-1.5"
                                title="Terminar sessão"
                            >
                                <LogOut size={12} /> Sair
                            </button>
                        </div>
                    ) : (
                        <button
                            onClick={() => setShowLogin(true)}
                            className="flex items-center gap-1.5 bg-indigo-900/40 hover:bg-indigo-800/60 border border-indigo-700/50 text-indigo-300 text-xs font-bold px-3 py-1.5 rounded-lg transition-colors"
                        >
                            <LogIn size={12} /> Iniciar Sessão
                        </button>
                    )}
                </div>
            </header>

            {/* Canvas area */}
            <div className="flex-1 relative overflow-hidden">
                <canvas
                    ref={canvasRef}
                    className="w-full h-full block cursor-pointer"
                    onClick={handleCanvasClick}
                />

                {/* Legend overlay */}
                <div className="absolute top-4 left-4 bg-gray-950/80 border border-gray-800/60 rounded-xl p-3 text-[10px] font-mono pointer-events-none">
                    <div className="text-gray-500 uppercase tracking-wider mb-2 text-[9px]">Estados</div>
                    {Object.entries(STATE_COLORS).slice(0, 6).map(([state, color]) => (
                        <div key={state} className="flex items-center gap-1.5 mb-1">
                            <div style={{ backgroundColor: color }} className="w-2 h-2 rounded-full" />
                            <span className="text-gray-500">{STATE_LABELS[state]}</span>
                        </div>
                    ))}
                </div>

                {/* Bottom hint */}
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 pointer-events-none flex gap-4">
                    <span className="text-[10px] text-gray-700 bg-gray-950/70 px-3 py-1.5 rounded-full border border-gray-800/50">
                        WASD / ↑↓←→ mover · Clica em entidades para interagir · Clica nas salas de reunião
                    </span>
                </div>

                {/* Entity panel */}
                {selectedEntity && (
                    <EntityPanel
                        entity={selectedEntity}
                        onClose={() => setSelectedEntity(null)}
                        onStartChat={(e) => { setSelectedEntity(null); setShowChat(e); }}
                        onInviteMeeting={(e) => { setSelectedEntity(null); setShowMeeting(true); }}
                    />
                )}
            </div>

            {/* Overlays */}
            {showMeeting && (
                <MeetingRoom
                    allAgents={allAgents}
                    humanUsers={allHumansForMeeting}
                    currentUser={currentUser}
                    onClose={() => setShowMeeting(false)}
                />
            )}

            {showLogin && (
                <LoginPage
                    organogramMembers={organogramMembers}
                    onLogin={handleLoginSuccess}
                />
            )}
        </div>
    );
}
