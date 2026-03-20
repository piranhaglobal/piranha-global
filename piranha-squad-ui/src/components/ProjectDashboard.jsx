import { useState, useEffect } from 'react';
import axios from 'axios';
import { Zap, Clock, CheckCircle, AlertCircle, ArrowRight, Users, Bot, ShieldCheck, Building2 } from 'lucide-react';

const STATUS_CONFIG = {
    active:   { label: 'Activo',       color: 'emerald', icon: CheckCircle },
    planning: { label: 'Planeamento',  color: 'blue',    icon: Clock },
    backlog:  { label: 'Backlog',      color: 'slate',   icon: AlertCircle },
};

const COLOR_CONFIG = {
    red:    { bg: 'from-red-950/80 to-red-900/40',    border: 'border-red-800/50', accent: 'bg-red-500',    text: 'text-red-400',   glow: 'shadow-red-900/40',    badge: 'bg-red-900/60 text-red-300 border-red-700/50' },
    blue:   { bg: 'from-blue-950/80 to-blue-900/40',  border: 'border-blue-800/50', accent: 'bg-blue-500',  text: 'text-blue-400',  glow: 'shadow-blue-900/40',   badge: 'bg-blue-900/60 text-blue-300 border-blue-700/50' },
    purple: { bg: 'from-purple-950/80 to-violet-900/40', border: 'border-purple-800/50', accent: 'bg-purple-500', text: 'text-purple-400', glow: 'shadow-purple-900/40', badge: 'bg-purple-900/60 text-purple-300 border-purple-700/50' },
    amber:  { bg: 'from-amber-950/80 to-amber-900/40',  border: 'border-amber-800/50', accent: 'bg-amber-500', text: 'text-amber-400',  glow: 'shadow-amber-900/40',  badge: 'bg-amber-900/60 text-amber-300 border-amber-700/50' },
    green:  { bg: 'from-emerald-950/80 to-emerald-900/40', border: 'border-emerald-800/50', accent: 'bg-emerald-500', text: 'text-emerald-400', glow: 'shadow-emerald-900/40', badge: 'bg-emerald-900/60 text-emerald-300 border-emerald-700/50' },
    default: { bg: 'from-gray-900/80 to-gray-800/40', border: 'border-gray-700/50', accent: 'bg-gray-500', text: 'text-gray-400', glow: 'shadow-gray-900/40', badge: 'bg-gray-800 text-gray-300 border-gray-700' },
};

// Mini pixel character preview per project
function MiniCrew({ count, color }) {
    const c = COLOR_CONFIG[color] || COLOR_CONFIG.default;
    const chars = Array.from({ length: Math.min(count, 6) }, (_, i) => i);
    return (
        <div className="flex items-center gap-1 mt-3">
            {chars.map(i => (
                <div key={i} className="relative">
                    <svg width="20" height="28" viewBox="0 0 10 14" style={{ imageRendering: 'pixelated' }}>
                        {/* Head */}
                        <rect x="3" y="0" width="4" height="4" fill="#d4a76a" />
                        <rect x="4" y="1" width="1" height="1" fill="#2a1a0a" />
                        <rect x="6" y="1" width="1" height="1" fill="#2a1a0a" />
                        {/* Body */}
                        <rect x="2" y="4" width="6" height="5" fill={color === 'red' ? '#991b1b' : color === 'blue' ? '#1d4ed8' : color === 'purple' ? '#7c3aed' : color === 'amber' ? '#b45309' : color === 'green' ? '#065f46' : '#374151'} />
                        {/* Arms */}
                        <rect x="0" y="5" width="2" height="3" fill={color === 'red' ? '#991b1b' : color === 'blue' ? '#1d4ed8' : color === 'purple' ? '#7c3aed' : color === 'amber' ? '#b45309' : color === 'green' ? '#065f46' : '#374151'} />
                        <rect x="8" y="5" width="2" height="3" fill={color === 'red' ? '#991b1b' : color === 'blue' ? '#1d4ed8' : color === 'purple' ? '#7c3aed' : color === 'amber' ? '#b45309' : color === 'green' ? '#065f46' : '#374151'} />
                        {/* Legs */}
                        <rect x="2" y="9" width="2" height="5" fill="#1e293b" />
                        <rect x="6" y="9" width="2" height="5" fill="#1e293b" />
                    </svg>
                    <div className={`absolute -top-0.5 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full ${c.accent}`} />
                </div>
            ))}
            {count > 6 && <span className="text-xs text-gray-500 ml-1">+{count - 6}</span>}
        </div>
    );
}

function ProjectCard({ project, onEnter }) {
    const c = COLOR_CONFIG[project.color] || COLOR_CONFIG.default;
    const statusConf = STATUS_CONFIG[project.status] || STATUS_CONFIG.backlog;
    const StatusIcon = statusConf.icon;

    return (
        <div
            className={`
                relative group cursor-pointer overflow-hidden
                bg-gradient-to-br ${c.bg}
                border ${c.border}
                rounded-2xl p-6 flex flex-col gap-4
                shadow-xl ${c.glow}
                hover:scale-[1.02] hover:shadow-2xl
                transition-all duration-300
            `}
            onClick={() => onEnter(project.id)}
        >
            {/* Priority badge */}
            <div className="absolute top-4 right-4 text-xs font-bold text-gray-600 font-mono">
                #{project.priority}
            </div>

            {/* Header */}
            <div className="flex items-start gap-4">
                <div className={`text-4xl p-3 rounded-xl bg-black/20 border ${c.border} flex-shrink-0`}>
                    {project.icon}
                </div>
                <div className="flex-1 min-w-0">
                    <h2 className={`text-xl font-black uppercase tracking-widest ${c.text}`}>
                        {project.name}
                    </h2>
                    <p className="text-sm text-gray-400 font-mono mt-0.5">{project.id}</p>
                </div>
            </div>

            {/* Description */}
            <p className="text-sm text-gray-400 leading-relaxed line-clamp-3">
                {project.description}
            </p>

            {/* Crew preview */}
            <MiniCrew count={project.agentCount} color={project.color} />

            {/* Footer */}
            <div className="flex items-center justify-between mt-auto pt-3 border-t border-white/5">
                <div className={`flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full border ${c.badge}`}>
                    <StatusIcon size={11} />
                    {statusConf.label}
                </div>
                <div className={`flex items-center gap-1.5 text-xs ${c.text}`}>
                    <Bot size={12} />
                    <span className="font-mono">{project.agentCount} agentes</span>
                </div>
            </div>

            {/* Enter arrow - appears on hover */}
            <div className={`
                absolute inset-0 flex items-center justify-center
                bg-black/60 backdrop-blur-sm opacity-0 group-hover:opacity-100
                transition-opacity duration-200 rounded-2xl
            `}>
                <div className={`flex items-center gap-3 font-bold text-lg ${c.text}`}>
                    Entrar no Escritório <ArrowRight size={20} />
                </div>
            </div>
        </div>
    );
}

const LEVEL_CONFIG = {
    leadership: { label: 'Leadership',  color: 'text-red-400',    border: 'border-red-800/50',    bg: 'bg-red-950/40'    },
    'c-level':  { label: 'C-Level',     color: 'text-blue-400',   border: 'border-blue-800/50',   bg: 'bg-blue-950/40'   },
    director:   { label: 'Directores',  color: 'text-purple-400', border: 'border-purple-800/50', bg: 'bg-purple-950/40' },
    manager:    { label: 'Managers',    color: 'text-amber-400',  border: 'border-amber-800/50',  bg: 'bg-amber-950/40'  },
    specialist: { label: 'Equipa',      color: 'text-gray-400',   border: 'border-gray-700/50',   bg: 'bg-gray-900/40'   },
};

const SQUAD_BADGE = {
    'piranha-leads':     { label: 'SALES',      color: 'bg-red-900/60 text-red-300 border-red-700/50' },
    'piranha-workshops': { label: 'WORKSHOPS',  color: 'bg-blue-900/60 text-blue-300 border-blue-700/50' },
    'piranha-comms':     { label: 'COMMS',      color: 'bg-purple-900/60 text-purple-300 border-purple-700/50' },
    'piranha-supplies':  { label: 'SUPPLIES',   color: 'bg-amber-900/60 text-amber-300 border-amber-700/50' },
    'piranha-studio':    { label: 'ESTÚDIO',    color: 'bg-emerald-900/60 text-emerald-300 border-emerald-700/50' },
};

function MemberCard({ member }) {
    const lc = LEVEL_CONFIG[member.level] || LEVEL_CONFIG.specialist;
    return (
        <div className={`flex flex-col gap-2.5 p-4 rounded-xl border ${lc.border} ${lc.bg} hover:scale-[1.02] transition-transform`}>
            <div className="flex items-center gap-3">
                <div className={`text-2xl w-10 h-10 rounded-xl flex items-center justify-center bg-black/20 border ${lc.border} flex-shrink-0`}>
                    {member.avatar}
                </div>
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                        <span className={`text-sm font-bold truncate ${lc.color}`}>{member.name}</span>
                        {member.approver && (
                            <ShieldCheck size={12} className="text-yellow-500 flex-shrink-0" title="Aprovador" />
                        )}
                    </div>
                    <p className="text-[10px] text-gray-500 leading-snug truncate">{member.role}</p>
                </div>
            </div>
            {member.squads.length > 0 && (
                <div className="flex flex-wrap gap-1">
                    {member.squads.map(s => {
                        const b = SQUAD_BADGE[s];
                        return b ? (
                            <span key={s} className={`text-[9px] font-bold px-1.5 py-0.5 rounded border ${b.color} uppercase tracking-wider`}>
                                {b.label}
                            </span>
                        ) : null;
                    })}
                </div>
            )}
        </div>
    );
}

function Organogram({ members }) {
    const levels = ['leadership', 'c-level', 'director', 'manager', 'specialist'];
    return (
        <div className="mt-16">
            <div className="text-center mb-8">
                <div className="inline-flex items-center gap-2 bg-gray-900/60 border border-gray-800 text-gray-400 text-xs font-semibold px-4 py-1.5 rounded-full mb-4 uppercase tracking-wider">
                    <Users size={12} /> Equipa Piranha Global
                </div>
                <h3 className="text-2xl font-black text-white">Organograma</h3>
                <p className="text-sm text-gray-500 mt-1">Pessoas · Responsabilidades · Squads</p>
            </div>
            <div className="flex flex-col gap-6">
                {levels.map(level => {
                    const group = members.filter(m => m.level === level);
                    if (group.length === 0) return null;
                    const lc = LEVEL_CONFIG[level];
                    return (
                        <div key={level}>
                            <div className={`flex items-center gap-2 mb-3`}>
                                <span className={`text-[10px] font-black uppercase tracking-widest ${lc.color}`}>{lc.label}</span>
                                <div className={`flex-1 h-px opacity-20 ${lc.color.replace('text-','bg-')}`} />
                            </div>
                            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
                                {group.map(m => <MemberCard key={m.id} member={m} />)}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

export default function ProjectDashboard({ onEnterProject, onOpenHQ }) {
    const [projects, setProjects] = useState([]);
    const [loading, setLoading] = useState(true);
    const [time, setTime] = useState(new Date());
    const [orgMembers, setOrgMembers] = useState([]);

    useEffect(() => {
        axios.get('http://localhost:3001/api/squads')
            .then(res => { setProjects(res.data); setLoading(false); })
            .catch(() => {
                // Fallback with static data if server is offline
                setProjects([
                    { id: 'piranha-leads',     name: 'SALES',        description: 'Scraping de retalho, estúdios PMU, clínicas e preços estratégicos.', color: 'red',    icon: '🦈', priority: 1, status: 'active',   agentCount: 6 },
                    { id: 'piranha-workshops', name: 'WORKSHOPS',    description: 'Automatização completa do funil — da captação ao fecho e fidelização.', color: 'blue',   icon: '🎓', priority: 2, status: 'planning', agentCount: 6 },
                    { id: 'piranha-comms',     name: 'COMUNICAÇÃO',  description: 'Head of Comms + agentes por canal: Social, Blog, ADS, Email, Lead Magnets.', color: 'purple', icon: '📢', priority: 3, status: 'active',   agentCount: 8 },
                    { id: 'piranha-supplies',  name: 'SUPPLIES',     description: 'Stocks, Supply Chain, Lead Times Ásia, Forecast e Notas de Encomenda.', color: 'amber',  icon: '📦', priority: 4, status: 'planning', agentCount: 8 },
                    { id: 'piranha-studio',    name: 'ESTÚDIO',      description: 'Radiografia do estúdio, quick wins e escalabilidade pós-PIRA + Shopify Plus.', color: 'green',  icon: '🏢', priority: 5, status: 'backlog',  agentCount: 6 },
                ]);
                setLoading(false);
            });

        axios.get('http://localhost:3001/api/organogram')
            .then(res => setOrgMembers(res.data.members || []))
            .catch(() => {});

        const ticker = setInterval(() => setTime(new Date()), 1000);
        return () => clearInterval(ticker);
    }, []);

    const totalAgents = projects.reduce((sum, p) => sum + p.agentCount, 0);
    const activeProjects = projects.filter(p => p.status === 'active').length;

    return (
        <div className="min-h-screen bg-[#030712] text-white overflow-auto">
            {/* Grid background */}
            <div
                className="fixed inset-0 opacity-[0.03] pointer-events-none"
                style={{
                    backgroundImage: 'linear-gradient(#4f46e5 1px, transparent 1px), linear-gradient(90deg, #4f46e5 1px, transparent 1px)',
                    backgroundSize: '60px 60px'
                }}
            />

            {/* Top Navigation */}
            <header className="sticky top-0 z-50 bg-gray-950/90 backdrop-blur-md border-b border-gray-800/60 px-8 py-4 flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-3">
                        <div className="relative">
                            <div className="w-9 h-9 bg-red-600 rounded-lg flex items-center justify-center text-lg shadow-lg shadow-red-900/50">🦈</div>
                            <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-gray-950 animate-pulse" />
                        </div>
                        <div>
                            <h1 className="text-base font-black tracking-wider text-white">PIRANHA GLOBAL</h1>
                            <p className="text-[10px] text-gray-500 font-mono uppercase tracking-widest">Virtual HQ — Agent Command Centre</p>
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-6">
                    <div className="flex items-center gap-4 text-xs text-gray-500 font-mono">
                        <span className="flex items-center gap-1.5">
                            <Zap size={12} className="text-yellow-500" />
                            {totalAgents} agentes configurados
                        </span>
                        <span className="flex items-center gap-1.5">
                            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                            {activeProjects} projectos activos
                        </span>
                    </div>
                    <button onClick={onOpenHQ} className="flex items-center gap-2 bg-indigo-900/40 hover:bg-indigo-800/60 border border-indigo-700/50 text-indigo-300 text-xs font-bold px-3 py-1.5 rounded-lg transition-colors">
                        <Building2 size={13} /> Escritório HQ
                    </button>
                    <div className="text-xs font-mono text-gray-600 tabular-nums">
                        {time.toLocaleTimeString('pt-PT')}
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="max-w-7xl mx-auto px-8 py-12">
                {/* Hero */}
                <div className="mb-12 text-center">
                    <div className="inline-flex items-center gap-2 bg-indigo-950/50 border border-indigo-800/50 text-indigo-300 text-xs font-semibold px-4 py-1.5 rounded-full mb-6 uppercase tracking-wider">
                        <Users size={12} /> Directriz do Chairman — Março 2026
                    </div>
                    <h2 className="text-4xl font-black text-white mb-3 tracking-tight">
                        5 Verticais de Negócio
                    </h2>
                    <p className="text-gray-500 max-w-xl mx-auto text-sm leading-relaxed">
                        Cada vertical tem o seu squad dedicado de agentes IA. Clica num projecto para entrar no escritório virtual e acompanhar a execução em tempo real.
                    </p>
                </div>

                {/* Projects Grid */}
                {loading ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {[...Array(5)].map((_, i) => (
                            <div key={i} className="h-64 bg-gray-900/50 border border-gray-800 rounded-2xl animate-pulse" />
                        ))}
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {projects.map(p => (
                            <ProjectCard key={p.id} project={p} onEnter={onEnterProject} />
                        ))}
                    </div>
                )}

                {/* Organogram */}
                {orgMembers.length > 0 && <Organogram members={orgMembers} />}

                {/* Footer note */}
                <div className="mt-12 text-center text-xs text-gray-700 font-mono">
                    "Evoluir as verticais do negócio, secar o número de horas em processos repetitivos." — Pedro Dias
                </div>
            </main>
        </div>
    );
}
