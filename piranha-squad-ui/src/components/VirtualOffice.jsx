import { useState, useEffect, useRef } from 'react';
import { OfficeEngine, VIRTUAL_W, VIRTUAL_H } from './office/engine.js';

// ─── Approval Modal ───────────────────────────────────────────────────────────
function ApprovalModal({ gameState, onApprove }) {
    if (!gameState || gameState.status !== 'waiting_human_approval') return null;
    return (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
            <div className="bg-gray-900 border border-indigo-500/60 rounded-2xl p-6 max-w-sm w-full mx-4 shadow-2xl">
                <div className="flex items-center gap-2 mb-4">
                    <span className="relative flex h-3 w-3">
                        <span className="animate-ping absolute h-full w-full rounded-full bg-pink-400 opacity-75" />
                        <span className="relative h-2.5 w-2.5 rounded-full bg-pink-500 inline-flex" />
                    </span>
                    <span className="text-xs font-bold text-pink-400 uppercase tracking-wider">
                        Quality Gate — Aprovação Necessária
                    </span>
                </div>
                <p className="text-sm text-gray-200 leading-relaxed mb-6 whitespace-pre-line">
                    {gameState.prompt}
                </p>
                <div className="flex gap-3">
                    <button
                        onClick={() => onApprove('s')}
                        className="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3 rounded-xl transition-colors"
                    >
                        ✓ Aprovar
                    </button>
                    <button
                        onClick={() => onApprove('n')}
                        className="flex-1 bg-gray-800 hover:bg-red-900/40 text-gray-300 hover:text-red-400 font-bold border border-gray-700 py-3 rounded-xl transition-colors"
                    >
                        ✕ Rejeitar
                    </button>
                </div>
            </div>
        </div>
    );
}

// ─── Status bar ───────────────────────────────────────────────────────────────
function StatusBar({ pipelineStatus, activeLabel, agentCount }) {
    const statusMap = {
        running:                 { dot: 'bg-green-500',  text: 'Pipeline em Execução',         ping: 'bg-green-400' },
        waiting_human_approval:  { dot: 'bg-pink-500',   text: '⏸ Quality Gate — Pedro Dias',  ping: 'bg-pink-400'  },
        completed:               { dot: 'bg-blue-400',   text: '✅ Pipeline Concluído',          ping: 'bg-blue-300'  },
        rejected:                { dot: 'bg-red-500',    text: '❌ Pipeline Rejeitado',          ping: 'bg-red-400'   },
        simulation:              { dot: 'bg-amber-500',  text: 'Modo Simulação',                ping: 'bg-amber-400' },
    };
    const s = statusMap[pipelineStatus] || { dot: 'bg-gray-600', text: 'Virtual Office — Pronto', ping: 'bg-gray-500' };

    return (
        <div className="h-10 bg-gray-900/90 border-b border-gray-800 flex items-center px-5 justify-between z-10 flex-shrink-0 font-mono">
            <div className="flex items-center gap-3">
                <span className="relative flex h-2 w-2">
                    <span className={`animate-ping absolute h-full w-full rounded-full opacity-60 ${s.ping}`} />
                    <span className={`relative h-2 w-2 rounded-full inline-flex ${s.dot}`} />
                </span>
                <span className="text-xs font-bold text-gray-400 uppercase tracking-widest">{s.text}</span>
            </div>
            <div className="flex gap-4 text-xs text-gray-600">
                {activeLabel && (
                    <span className="text-green-400 animate-pulse">● {activeLabel} a trabalhar</span>
                )}
                <span>{agentCount} agentes</span>
            </div>
        </div>
    );
}

// ─── Terminal panel ───────────────────────────────────────────────────────────
function Terminal({ logs }) {
    const ref = useRef(null);
    useEffect(() => { if (ref.current) ref.current.scrollTop = 0; }, [logs]);

    return (
        <div className="h-48 bg-[#050a0f] border-t border-gray-800 flex flex-col z-20 flex-shrink-0 font-mono">
            <div className="px-4 py-1.5 border-b border-gray-800/60 bg-gray-900/40 flex items-center gap-2 flex-shrink-0">
                <span className="w-2 h-2 rounded-full bg-green-700 flex-shrink-0" />
                <span className="text-[10px] font-bold text-gray-600 uppercase tracking-wider">
                    Pipeline Terminal — Execução em Tempo Real
                </span>
            </div>
            <div ref={ref} className="flex-1 p-3 overflow-y-auto flex flex-col gap-1">
                {logs.length === 0 ? (
                    <div className="text-gray-700 text-center mt-6 text-xs animate-pulse">
                        Aguarda pipeline... Execute para ver actividade aqui.
                    </div>
                ) : logs.map((log, i) => (
                    <div key={i} className={`flex gap-3 text-[11px] ${i === 0 ? 'text-gray-200' : 'text-gray-600'}`}>
                        <span className="text-blue-900 flex-shrink-0">[{log.time}]</span>
                        <span className={`flex-shrink-0 font-bold ${
                            log.agent === '@human'  ? 'text-indigo-400' :
                            log.agent === 'system'  ? 'text-yellow-700' :
                            'text-green-600'
                        }`}>{log.agent}</span>
                        <span className="flex-1 truncate">{log.action}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function VirtualOffice({ agents, squadColor = 'blue', squadId = 'piranha-dev' }) {
    const canvasRef  = useRef(null);
    const engineRef  = useRef(null);
    const rafRef     = useRef(null);
    const lastTsRef  = useRef(null);
    const prevLogRef = useRef(null); // last processed log key

    const [logs, setLogs]             = useState([]);
    const [gameState, setGameState]   = useState(null);
    const [activeLabel, setActiveLabel] = useState(null);

    // ── Init / reinit engine when agents change ──
    useEffect(() => {
        if (agents.length === 0) return;
        engineRef.current = new OfficeEngine(agents, squadColor);
        prevLogRef.current = null;
    }, [agents, squadColor]);

    // ── Game loop ──
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const resize = () => {
            const p = canvas.parentElement;
            if (!p) return;
            canvas.width  = p.clientWidth;
            canvas.height = p.clientHeight;
        };
        resize();
        const ro = new ResizeObserver(resize);
        ro.observe(canvas.parentElement);

        const tick = (ts) => {
            if (!lastTsRef.current) lastTsRef.current = ts;
            const dt = Math.min((ts - lastTsRef.current) / 1000, 0.05);
            lastTsRef.current = ts;

            const engine = engineRef.current;
            const ctx    = canvas.getContext('2d');
            if (engine && ctx) {
                engine.update(dt);

                // Scale virtual world → canvas size
                const sx = canvas.width  / VIRTUAL_W;
                const sy = canvas.height / VIRTUAL_H;
                const sc = Math.min(sx, sy);
                const offX = (canvas.width  - VIRTUAL_W * sc) / 2;
                const offY = (canvas.height - VIRTUAL_H * sc) / 2;

                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.fillStyle = '#0d1117';
                ctx.fillRect(0, 0, canvas.width, canvas.height);

                ctx.save();
                ctx.translate(offX, offY);
                ctx.scale(sc, sc);
                engine.render(ctx);
                ctx.restore();
            }
            rafRef.current = requestAnimationFrame(tick);
        };
        rafRef.current = requestAnimationFrame(tick);

        return () => {
            cancelAnimationFrame(rafRef.current);
            ro.disconnect();
        };
    }, []);

    // ── Log polling ──
    useEffect(() => {
        let timer;
        const poll = async () => {
            try {
                const res  = await fetch(`http://localhost:3001/api/logs?squad=${squadId}`);
                const data = await res.json();
                const engine = engineRef.current;

                if (data.logs?.length > 0) {
                    const ordered = [...data.logs].reverse(); // newest first
                    setLogs(ordered);

                    const latest = ordered[0];
                    const logKey = `${latest.agent}:${latest.action}`;

                    if (engine && logKey !== prevLogRef.current) {
                        prevLogRef.current = logKey;

                        if (latest.agent === 'system') {
                            engine.onSystemLog(latest.action);
                            setActiveLabel(null);
                        } else if (latest.agent === '@human') {
                            const isWaiting = data.state?.status === 'waiting_human_approval';
                            engine.onHumanGate(isWaiting);
                            setActiveLabel(null);
                        } else {
                            engine.onLog(latest.agent, latest.action);
                            setActiveLabel(latest.agent);
                        }
                    }
                } else {
                    if (engine && prevLogRef.current !== null) {
                        engine.resetAll();
                        prevLogRef.current = null;
                        setActiveLabel(null);
                    }
                    setLogs([]);
                }

                setGameState(data.state || null);
            } catch { /* server offline */ }
            timer = setTimeout(poll, 1500);
        };
        poll();
        return () => clearTimeout(timer);
    }, [agents, squadId]);

    const sendApproval = async (decision) => {
        await fetch('http://localhost:3001/api/approve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ decision, squadId })
        });
        setGameState(null);
        if (engineRef.current) engineRef.current.onHumanGate(false);
    };

    const pipelineStatus = gameState?.status;
    const agentCount     = agents.filter(a => a.id !== 'human-user').length;

    return (
        <div className="flex-1 h-full flex flex-col bg-[#0d1117] relative overflow-hidden">
            <StatusBar
                pipelineStatus={pipelineStatus}
                activeLabel={activeLabel}
                agentCount={agentCount}
            />

            {/* Canvas fills remaining space */}
            <div className="flex-1 relative overflow-hidden" style={{ minHeight: 0 }}>
                <canvas
                    ref={canvasRef}
                    className="w-full h-full block"
                    style={{ imageRendering: 'pixelated' }}
                />
            </div>

            <Terminal logs={logs} />
            <ApprovalModal gameState={gameState} onApprove={sendApproval} />
        </div>
    );
}
