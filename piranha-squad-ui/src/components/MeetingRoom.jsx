import { useState, useRef, useEffect } from 'react';
import { X, Bot, Users, Send, FileText, Copy, Check, Loader2, UserCheck } from 'lucide-react';

const SQUAD_LABELS = {
    'piranha-leads': { label: 'SALES', color: 'bg-red-900/60 text-red-300 border-red-700/50' },
    'piranha-workshops': { label: 'WORKSHOPS', color: 'bg-blue-900/60 text-blue-300 border-blue-700/50' },
    'piranha-comms': { label: 'COMMS', color: 'bg-purple-900/60 text-purple-300 border-purple-700/50' },
    'piranha-supplies': { label: 'SUPPLIES', color: 'bg-amber-900/60 text-amber-300 border-amber-700/50' },
    'piranha-studio': { label: 'ESTÚDIO', color: 'bg-emerald-900/60 text-emerald-300 border-emerald-700/50' },
};

const SQUAD_COLORS = {
    'piranha-leads': '#b91c1c',
    'piranha-workshops': '#1d4ed8',
    'piranha-comms': '#7c3aed',
    'piranha-supplies': '#b45309',
    'piranha-studio': '#065f46',
};

function AgentAvatar({ agent, size = 'sm' }) {
    const color = SQUAD_COLORS[agent.squadId] || '#374151';
    const dim = size === 'sm' ? 'w-7 h-7 text-xs' : 'w-9 h-9 text-sm';
    return (
        <div
            className={`${dim} rounded-lg flex items-center justify-center flex-shrink-0 font-bold border`}
            style={{ background: color + '30', borderColor: color + '60', color }}
            title={agent.name || agent.data?.label}
        >
            <Bot size={size === 'sm' ? 12 : 14} />
        </div>
    );
}

function HumanAvatar({ user, size = 'sm' }) {
    const dim = size === 'sm' ? 'w-7 h-7 text-base' : 'w-9 h-9 text-lg';
    return (
        <div className={`${dim} rounded-lg flex items-center justify-center bg-indigo-900/40 border border-indigo-700/50 flex-shrink-0`} title={user.name}>
            <span>{user.avatar || '👤'}</span>
        </div>
    );
}

export default function MeetingRoom({ allAgents = [], humanUsers = [], currentUser, onClose }) {
    const [step, setStep] = useState('setup');
    const [topic, setTopic] = useState('');
    const [selectedAgents, setSelectedAgents] = useState(new Set());
    const [selectedHumans, setSelectedHumans] = useState(new Set(currentUser ? [currentUser.id] : []));
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [sending, setSending] = useState(false);
    const [sketchContent, setSketchContent] = useState('');
    const [showSketch, setShowSketch] = useState(false);
    const [generatingSketch, setGeneratingSketch] = useState(false);
    const [copied, setCopied] = useState(false);
    const messagesEndRef = useRef(null);
    const inputRef = useRef(null);

    useEffect(() => {
        if (messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages]);

    // Group agents by squad
    const agentsBySquad = allAgents.reduce((acc, agent) => {
        const sq = agent.squadId || 'unknown';
        if (!acc[sq]) acc[sq] = [];
        acc[sq].push(agent);
        return acc;
    }, {});

    const toggleAgent = (id) => {
        setSelectedAgents(prev => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id); else next.add(id);
            return next;
        });
    };

    const toggleHuman = (id) => {
        if (currentUser && id === currentUser.id) return; // cannot deselect self
        setSelectedHumans(prev => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id); else next.add(id);
            return next;
        });
    };

    const canStart = topic.trim().length > 0 && selectedAgents.size > 0;

    const startMeeting = () => {
        setStep('meeting');
        setMessages([{
            id: Date.now(),
            type: 'system',
            content: `Reunião iniciada sobre: "${topic}"`,
        }]);
    };

    const buildParticipants = () => {
        const agents = allAgents
            .filter(a => selectedAgents.has(a.id))
            .map(a => ({
                type: 'agent',
                agentId: a.id,
                squadId: a.squadId,
                name: a.data?.label || a.id,
            }));
        const humans = humanUsers
            .filter(h => selectedHumans.has(h.id))
            .map(h => ({ type: 'human', userId: h.id, name: h.name }));
        return [...agents, ...humans];
    };

    const sendMessage = async () => {
        if (!input.trim() || sending) return;
        const userMsg = input.trim();
        setInput('');
        setSending(true);

        const userMsgObj = {
            id: Date.now(),
            type: 'user',
            from: currentUser?.name || 'Utilizador',
            content: userMsg,
        };
        setMessages(prev => [...prev, userMsgObj]);

        const participants = buildParticipants();
        const agentParticipants = participants.filter(p => p.type === 'agent');

        // Add placeholder for each agent
        const placeholders = agentParticipants.map(p => ({
            id: `${Date.now()}-${p.agentId}`,
            type: 'agent',
            agentId: p.agentId,
            from: p.name,
            content: '',
            streaming: true,
            color: SQUAD_COLORS[p.squadId] || '#374151',
        }));
        setMessages(prev => [...prev, ...placeholders]);

        const history = messages
            .filter(m => m.type === 'user' || (m.type === 'agent' && !m.streaming))
            .map(m => ({
                role: m.type === 'user' ? 'user' : 'assistant',
                content: m.content,
            }));

        try {
            const res = await fetch('http://localhost:3001/api/meeting/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    participants: agentParticipants,
                    message: userMsg,
                    history,
                    topic,
                }),
            });

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop();

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    const raw = line.slice(6).trim();
                    if (raw === '[DONE]') { setSending(false); break; }
                    try {
                        const evt = JSON.parse(raw);
                        if (evt.type === 'text') {
                            setMessages(prev => prev.map(m => {
                                if (m.agentId === evt.agentId && m.streaming) {
                                    return { ...m, content: m.content + evt.text };
                                }
                                return m;
                            }));
                        } else if (evt.type === 'agent_done') {
                            setMessages(prev => prev.map(m => {
                                if (m.agentId === evt.agentId && m.streaming) {
                                    return { ...m, streaming: false };
                                }
                                return m;
                            }));
                        }
                    } catch { /* ignore parse errors */ }
                }
            }
        } catch (err) {
            setMessages(prev => [...prev, {
                id: Date.now(),
                type: 'system',
                content: `Erro de ligação: ${err.message}`,
            }]);
        } finally {
            setSending(false);
        }
    };

    const generateSketch = async () => {
        setGeneratingSketch(true);
        setShowSketch(true);
        const transcript = messages
            .filter(m => m.type !== 'system')
            .map(m => `${m.from || 'Sistema'}: ${m.content}`)
            .join('\n\n');

        const summaryRequest = `Aqui está a transcrição de uma reunião sobre "${topic}":\n\n${transcript}\n\nCria um esboço técnico estruturado com: objectivos, decisões tomadas, próximas acções e responsáveis. Formato markdown.`;

        setSketchContent('');
        try {
            const res = await fetch('http://localhost:3001/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    squadId: 'piranha-dev',
                    agentId: 'architect',
                    message: summaryRequest,
                    history: [],
                }),
            });

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop();
                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    const raw = line.slice(6).trim();
                    if (raw === '[DONE]') break;
                    try {
                        const evt = JSON.parse(raw);
                        if (evt.text) setSketchContent(prev => prev + evt.text);
                    } catch { /* ignore */ }
                }
            }
        } catch (err) {
            setSketchContent(`Erro ao gerar esboço: ${err.message}`);
        } finally {
            setGeneratingSketch(false);
        }
    };

    const copySketch = () => {
        navigator.clipboard.writeText(sketchContent).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        });
    };

    const allParticipants = buildParticipants();
    const agentCount = selectedAgents.size;

    return (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-stretch font-mono">
            <div className="flex-1 flex overflow-hidden rounded-none">
                {/* Left Panel */}
                <div className="flex flex-col bg-[#08080f] border-r border-indigo-900/40" style={{ width: '340px', minWidth: '340px' }}>
                    {/* Header */}
                    <div className="flex items-center gap-3 px-5 py-4 border-b border-indigo-900/40 flex-shrink-0">
                        <span className="text-xl">🪑</span>
                        <div className="flex-1 min-w-0">
                            <h2 className="text-sm font-black text-white uppercase tracking-wider">
                                {step === 'setup' ? 'Convocar Reunião' : 'Sala de Reunião'}
                            </h2>
                            {step === 'meeting' && (
                                <p className="text-[10px] text-indigo-400 truncate mt-0.5">{topic}</p>
                            )}
                        </div>
                        <button
                            onClick={onClose}
                            className="text-gray-500 hover:text-gray-300 transition-colors flex-shrink-0"
                        >
                            <X size={16} />
                        </button>
                    </div>

                    {step === 'setup' ? (
                        /* ── SETUP ── */
                        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-5">
                            {/* Topic */}
                            <div>
                                <label className="block text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1.5">
                                    Tópico da reunião
                                </label>
                                <textarea
                                    value={topic}
                                    onChange={e => setTopic(e.target.value)}
                                    placeholder="Sobre o que é esta reunião?"
                                    rows={3}
                                    className="w-full bg-gray-900 border border-gray-700 rounded-xl px-3 py-2.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500 resize-none transition-colors"
                                />
                            </div>

                            {/* Agents selection */}
                            <div>
                                <label className="block text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2">
                                    Agentes <span className="text-indigo-400">({agentCount} seleccionados)</span>
                                </label>
                                <div className="flex flex-col gap-1.5 max-h-48 overflow-y-auto pr-1">
                                    {Object.entries(agentsBySquad).map(([squadId, agents]) => {
                                        const badge = SQUAD_LABELS[squadId];
                                        return (
                                            <div key={squadId}>
                                                <div className={`text-[9px] font-bold px-2 py-0.5 rounded border mb-1 inline-block ${badge?.color || 'bg-gray-800 text-gray-400 border-gray-700'}`}>
                                                    {badge?.label || squadId}
                                                </div>
                                                {agents.map(agent => (
                                                    <button
                                                        key={agent.id}
                                                        type="button"
                                                        onClick={() => toggleAgent(agent.id)}
                                                        className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg mb-0.5 transition-colors text-left ${
                                                            selectedAgents.has(agent.id)
                                                                ? 'bg-indigo-900/40 border border-indigo-700/50'
                                                                : 'hover:bg-gray-800/60 border border-transparent'
                                                        }`}
                                                    >
                                                        <div className={`w-4 h-4 rounded flex items-center justify-center flex-shrink-0 border ${
                                                            selectedAgents.has(agent.id)
                                                                ? 'bg-indigo-600 border-indigo-500'
                                                                : 'border-gray-600'
                                                        }`}>
                                                            {selectedAgents.has(agent.id) && <Check size={10} className="text-white" />}
                                                        </div>
                                                        <AgentAvatar agent={agent} size="sm" />
                                                        <span className="text-xs text-white truncate flex-1">
                                                            {agent.data?.label || agent.id}
                                                        </span>
                                                    </button>
                                                ))}
                                            </div>
                                        );
                                    })}
                                    {allAgents.length === 0 && (
                                        <p className="text-xs text-gray-600 px-2">Nenhum agente disponível.</p>
                                    )}
                                </div>
                            </div>

                            {/* Humans selection */}
                            <div>
                                <label className="block text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2">
                                    Equipa Humana
                                </label>
                                <div className="flex flex-col gap-1">
                                    {currentUser && (
                                        <div className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-indigo-900/30 border border-indigo-700/40">
                                            <div className="w-4 h-4 rounded flex items-center justify-center bg-indigo-600 border-indigo-500 flex-shrink-0">
                                                <Check size={10} className="text-white" />
                                            </div>
                                            <HumanAvatar user={currentUser} size="sm" />
                                            <span className="text-xs text-indigo-300 flex-1 truncate">{currentUser.name}</span>
                                            <span className="text-[9px] text-indigo-600">Tu</span>
                                        </div>
                                    )}
                                    {humanUsers.filter(h => h.id !== currentUser?.id).map(user => (
                                        <button
                                            key={user.id}
                                            type="button"
                                            onClick={() => toggleHuman(user.id)}
                                            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg transition-colors text-left ${
                                                selectedHumans.has(user.id)
                                                    ? 'bg-indigo-900/40 border border-indigo-700/50'
                                                    : 'hover:bg-gray-800/60 border border-transparent'
                                            }`}
                                        >
                                            <div className={`w-4 h-4 rounded flex items-center justify-center flex-shrink-0 border ${
                                                selectedHumans.has(user.id)
                                                    ? 'bg-indigo-600 border-indigo-500'
                                                    : 'border-gray-600'
                                            }`}>
                                                {selectedHumans.has(user.id) && <Check size={10} className="text-white" />}
                                            </div>
                                            <HumanAvatar user={user} size="sm" />
                                            <span className="text-xs text-white truncate flex-1">{user.name}</span>
                                        </button>
                                    ))}
                                    {humanUsers.length === 0 && !currentUser && (
                                        <p className="text-xs text-gray-600 px-2">Nenhum utilizador registado.</p>
                                    )}
                                </div>
                            </div>
                        </div>
                    ) : (
                        /* ── MEETING: Participant strip ── */
                        <div className="flex-1 overflow-y-auto p-4">
                            <div className="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-3">
                                Participantes ({allParticipants.length})
                            </div>
                            <div className="flex flex-col gap-2">
                                {allParticipants.map((p, i) => {
                                    if (p.type === 'agent') {
                                        const agent = allAgents.find(a => a.id === p.agentId);
                                        if (!agent) return null;
                                        return (
                                            <div key={i} className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-gray-900/50">
                                                <AgentAvatar agent={agent} size="sm" />
                                                <div className="flex-1 min-w-0">
                                                    <div className="text-xs text-white font-semibold truncate">{p.name}</div>
                                                    <div className="text-[9px] text-gray-600">{SQUAD_LABELS[agent.squadId]?.label || agent.squadId}</div>
                                                </div>
                                            </div>
                                        );
                                    } else {
                                        const human = p.userId === currentUser?.id ? currentUser : humanUsers.find(h => h.id === p.userId);
                                        if (!human) return null;
                                        return (
                                            <div key={i} className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-indigo-950/30">
                                                <HumanAvatar user={human} size="sm" />
                                                <div className="flex-1 min-w-0">
                                                    <div className="text-xs text-indigo-300 font-semibold truncate">{human.name}</div>
                                                    <div className="text-[9px] text-indigo-700 capitalize">{human.level || 'Utilizador'}</div>
                                                </div>
                                                {p.userId === currentUser?.id && <UserCheck size={10} className="text-indigo-500" />}
                                            </div>
                                        );
                                    }
                                })}
                            </div>

                            {/* Sketch panel */}
                            {showSketch && (
                                <div className="mt-4 bg-gray-900/80 border border-gray-700/50 rounded-xl p-3">
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Esboço</span>
                                        <button
                                            onClick={copySketch}
                                            disabled={!sketchContent || generatingSketch}
                                            className="flex items-center gap-1 text-[10px] text-gray-500 hover:text-gray-300 transition-colors disabled:opacity-40"
                                        >
                                            {copied ? <><Check size={10} className="text-green-400" /> Copiado</> : <><Copy size={10} /> Copiar Esboço</>}
                                        </button>
                                    </div>
                                    {generatingSketch && !sketchContent ? (
                                        <div className="flex items-center gap-2 py-2 text-xs text-gray-500">
                                            <Loader2 size={12} className="animate-spin" /> A gerar esboço...
                                        </div>
                                    ) : (
                                        <pre className="text-[10px] text-gray-300 whitespace-pre-wrap max-h-48 overflow-y-auto leading-relaxed">
                                            {sketchContent}
                                            {generatingSketch && <span className="animate-pulse text-indigo-400">▋</span>}
                                        </pre>
                                    )}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Action buttons */}
                    <div className="p-4 border-t border-indigo-900/40 flex-shrink-0">
                        {step === 'setup' ? (
                            <button
                                onClick={startMeeting}
                                disabled={!canStart}
                                className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold py-3 rounded-xl transition-colors text-sm flex items-center justify-center gap-2"
                            >
                                <Users size={14} /> Iniciar Reunião
                            </button>
                        ) : (
                            <div className="flex flex-col gap-2">
                                {messages.filter(m => m.type !== 'system').length >= 3 && (
                                    <button
                                        onClick={generateSketch}
                                        disabled={generatingSketch}
                                        className="w-full bg-emerald-900/40 hover:bg-emerald-800/50 border border-emerald-700/50 text-emerald-300 font-bold py-2 rounded-xl transition-colors text-xs flex items-center justify-center gap-2"
                                    >
                                        {generatingSketch ? <Loader2 size={12} className="animate-spin" /> : <FileText size={12} />}
                                        Gerar Esboço
                                    </button>
                                )}
                                <button
                                    onClick={onClose}
                                    className="w-full bg-red-950/40 hover:bg-red-900/50 border border-red-800/50 text-red-400 font-bold py-2.5 rounded-xl transition-colors text-sm flex items-center justify-center gap-2"
                                >
                                    <X size={14} /> Terminar Reunião
                                </button>
                            </div>
                        )}
                    </div>
                </div>

                {/* Right Panel — Chat */}
                <div className="flex-1 flex flex-col bg-[#060a0f] min-w-0">
                    {step === 'setup' ? (
                        /* Setup preview */
                        <div className="flex-1 flex items-center justify-center text-center px-8">
                            <div>
                                <div className="text-5xl mb-4">🪑</div>
                                <h3 className="text-lg font-black text-white mb-2">Sala de Reunião</h3>
                                <p className="text-sm text-gray-500 max-w-xs mx-auto leading-relaxed">
                                    Selecciona os agentes e o tópico na coluna da esquerda para convocar uma reunião virtual.
                                </p>
                                {agentCount > 0 && topic.trim() && (
                                    <div className="mt-6 bg-indigo-950/30 border border-indigo-800/50 rounded-xl p-4 text-sm text-indigo-300">
                                        <strong>{agentCount} agente{agentCount > 1 ? 's' : ''}</strong> convidado{agentCount > 1 ? 's' : ''} · "{topic}"
                                    </div>
                                )}
                            </div>
                        </div>
                    ) : (
                        <>
                            {/* Messages */}
                            <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
                                {messages.map((msg) => {
                                    if (msg.type === 'system') {
                                        return (
                                            <div key={msg.id} className="text-center">
                                                <span className="text-[10px] text-gray-600 bg-gray-900/50 px-3 py-1 rounded-full">
                                                    {msg.content}
                                                </span>
                                            </div>
                                        );
                                    }
                                    if (msg.type === 'user') {
                                        return (
                                            <div key={msg.id} className="flex justify-end">
                                                <div className="max-w-[70%]">
                                                    <div className="text-[9px] text-indigo-400 text-right mb-1 font-semibold uppercase tracking-wider">
                                                        {msg.from}
                                                    </div>
                                                    <div className="bg-indigo-900/60 border border-indigo-700/50 rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm text-white leading-relaxed">
                                                        {msg.content}
                                                    </div>
                                                </div>
                                            </div>
                                        );
                                    }
                                    if (msg.type === 'agent') {
                                        const agent = allAgents.find(a => a.id === msg.agentId);
                                        const color = msg.color || SQUAD_COLORS[agent?.squadId] || '#374151';
                                        return (
                                            <div key={msg.id} className="flex justify-start gap-2.5">
                                                {agent && <AgentAvatar agent={agent} size="sm" />}
                                                <div className="max-w-[75%]">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span
                                                            className="text-[9px] font-bold uppercase tracking-wider"
                                                            style={{ color }}
                                                        >
                                                            {msg.from}
                                                        </span>
                                                        {msg.streaming && (
                                                            <span className="flex gap-0.5">
                                                                <span className="w-1 h-1 rounded-full animate-bounce" style={{ background: color, animationDelay: '0ms' }} />
                                                                <span className="w-1 h-1 rounded-full animate-bounce" style={{ background: color, animationDelay: '150ms' }} />
                                                                <span className="w-1 h-1 rounded-full animate-bounce" style={{ background: color, animationDelay: '300ms' }} />
                                                            </span>
                                                        )}
                                                    </div>
                                                    <div
                                                        className="rounded-2xl rounded-tl-sm px-4 py-2.5 text-sm text-white leading-relaxed border"
                                                        style={{ background: color + '15', borderColor: color + '30' }}
                                                    >
                                                        {msg.content || (msg.streaming && <span className="animate-pulse text-gray-500">A pensar...</span>)}
                                                        {msg.streaming && msg.content && (
                                                            <span className="animate-pulse ml-0.5" style={{ color }}>▋</span>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        );
                                    }
                                    return null;
                                })}
                                <div ref={messagesEndRef} />
                            </div>

                            {/* Input area */}
                            <div className="p-4 border-t border-gray-800/50 flex-shrink-0">
                                <div className="flex gap-2.5">
                                    <textarea
                                        ref={inputRef}
                                        value={input}
                                        onChange={e => setInput(e.target.value)}
                                        onKeyDown={e => {
                                            if (e.key === 'Enter' && !e.shiftKey) {
                                                e.preventDefault();
                                                sendMessage();
                                            }
                                        }}
                                        placeholder="Escreve uma mensagem para os agentes... (Enter para enviar)"
                                        rows={2}
                                        disabled={sending}
                                        className="flex-1 bg-gray-900 border border-gray-700 rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500 resize-none transition-colors disabled:opacity-50"
                                    />
                                    <button
                                        onClick={sendMessage}
                                        disabled={!input.trim() || sending}
                                        className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white px-4 rounded-xl transition-colors flex items-center justify-center flex-shrink-0"
                                    >
                                        {sending ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                                    </button>
                                </div>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
