import { useState, useRef, useEffect } from 'react';
import { MessageSquare, Send, X, Bot, User, Loader2, ChevronDown, Trash2 } from 'lucide-react';

// ─── Markdown-lite renderer ───────────────────────────────────────────────────
function MsgText({ text }) {
    // Bold **text**, inline code `code`, line breaks
    const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\n)/g);
    return (
        <span>
            {parts.map((p, i) => {
                if (p.startsWith('**') && p.endsWith('**'))
                    return <strong key={i}>{p.slice(2, -2)}</strong>;
                if (p.startsWith('`') && p.endsWith('`'))
                    return <code key={i} className="bg-gray-800 px-1 rounded text-cyan-300 text-[10px]">{p.slice(1, -1)}</code>;
                if (p === '\n') return <br key={i} />;
                return p;
            })}
        </span>
    );
}

// ─── Single message bubble ────────────────────────────────────────────────────
function Message({ msg }) {
    const isUser = msg.role === 'user';
    return (
        <div className={`flex gap-2.5 ${isUser ? 'flex-row-reverse' : ''}`}>
            {/* Avatar */}
            <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 text-xs font-bold
                ${isUser ? 'bg-indigo-700 text-indigo-200' : 'bg-cyan-900/60 text-cyan-300 border border-cyan-800/50'}`}>
                {isUser ? <User size={14} /> : <Bot size={14} />}
            </div>
            {/* Bubble */}
            <div className={`max-w-[80%] px-3 py-2 rounded-xl text-xs leading-relaxed
                ${isUser
                    ? 'bg-indigo-700/30 text-indigo-100 border border-indigo-700/40 rounded-tr-none'
                    : 'bg-gray-800/60 text-gray-200 border border-gray-700/50 rounded-tl-none'
                }`}>
                {msg.streaming && !msg.content ? (
                    <span className="flex gap-1 items-center text-gray-500">
                        <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce [animation-delay:0s]" />
                        <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce [animation-delay:0.15s]" />
                        <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce [animation-delay:0.3s]" />
                    </span>
                ) : (
                    <MsgText text={msg.content || ''} />
                )}
                {msg.streaming && msg.content && (
                    <span className="inline-block w-1 h-3 bg-cyan-400 ml-0.5 animate-pulse align-middle" />
                )}
            </div>
        </div>
    );
}

// ─── Agent selector dropdown ──────────────────────────────────────────────────
function AgentSelect({ agents, selected, onSelect }) {
    const [open, setOpen] = useState(false);
    const sel = agents.find(a => a.id === selected);

    return (
        <div className="relative">
            <button
                onClick={() => setOpen(v => !v)}
                className="flex items-center gap-2 bg-gray-800/60 border border-gray-700/60 rounded-lg px-3 py-1.5 text-xs text-gray-300 hover:border-cyan-700/50 transition-colors w-full"
            >
                <Bot size={12} className="text-cyan-400 flex-shrink-0" />
                <span className="flex-1 text-left truncate font-mono">
                    {sel ? sel.data?.label || sel.id : 'Seleccionar agente...'}
                </span>
                <ChevronDown size={12} className={`text-gray-500 transition-transform ${open ? 'rotate-180' : ''}`} />
            </button>
            {open && (
                <div className="absolute top-full mt-1 left-0 right-0 bg-gray-900 border border-gray-700 rounded-xl shadow-2xl z-50 overflow-hidden">
                    {agents.filter(a => a.id !== 'human-user').map(a => (
                        <button
                            key={a.id}
                            onClick={() => { onSelect(a.id); setOpen(false); }}
                            className={`flex items-center gap-2.5 w-full px-3 py-2.5 text-xs text-left hover:bg-gray-800 transition-colors ${selected === a.id ? 'bg-gray-800/80 text-cyan-400' : 'text-gray-300'}`}
                        >
                            <Bot size={12} className="text-cyan-600 flex-shrink-0" />
                            <div className="overflow-hidden">
                                <div className="font-mono font-bold truncate">{a.data?.label || a.id}</div>
                                <div className="text-gray-600 truncate" style={{ fontSize: '10px' }}>
                                    {a.data?.description || ''}
                                </div>
                            </div>
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}

// ─── Main ChatPanel ───────────────────────────────────────────────────────────
export default function ChatPanel({ agents, squadId, onClose }) {
    const [selectedAgent, setSelectedAgent] = useState(
        agents.find(a => a.id !== 'human-user')?.id || null
    );
    const [messages, setMessages]   = useState([]);
    const [input, setInput]         = useState('');
    const [sending, setSending]     = useState(false);
    const messagesEndRef            = useRef(null);
    const inputRef                  = useRef(null);

    // Auto-scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Focus input on mount
    useEffect(() => { inputRef.current?.focus(); }, []);

    // Reset conversation when agent changes
    const handleSelectAgent = (id) => {
        setSelectedAgent(id);
        setMessages([]);
    };

    const send = async () => {
        if (!input.trim() || !selectedAgent || sending) return;

        const userMsg = { role: 'user', content: input.trim() };
        const history = messages.filter(m => !m.streaming).map(m => ({
            role: m.role, content: m.content
        }));

        setMessages(prev => [...prev, userMsg, { role: 'assistant', content: '', streaming: true }]);
        setInput('');
        setSending(true);

        try {
            const resp = await fetch('http://localhost:3001/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    squadId,
                    agentId: selectedAgent,
                    message: userMsg.content,
                    history
                })
            });

            if (!resp.ok) {
                const err = await resp.json();
                setMessages(prev => {
                    const copy = [...prev];
                    copy[copy.length - 1] = { role: 'assistant', content: `❌ Erro: ${err.error}` };
                    return copy;
                });
                setSending(false);
                return;
            }

            // Stream SSE
            const reader = resp.body.getReader();
            const decoder = new TextDecoder();
            let accumulated = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');
                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    const data = line.slice(6).trim();
                    if (data === '[DONE]') break;
                    try {
                        const { text } = JSON.parse(data);
                        accumulated += text;
                        setMessages(prev => {
                            const copy = [...prev];
                            copy[copy.length - 1] = { role: 'assistant', content: accumulated, streaming: true };
                            return copy;
                        });
                    } catch {}
                }
            }

            // Finalise (remove streaming flag)
            setMessages(prev => {
                const copy = [...prev];
                copy[copy.length - 1] = { role: 'assistant', content: accumulated, streaming: false };
                return copy;
            });
        } catch (e) {
            setMessages(prev => {
                const copy = [...prev];
                copy[copy.length - 1] = { role: 'assistant', content: '❌ Servidor offline ou erro de ligação.' };
                return copy;
            });
        }
        setSending(false);
        inputRef.current?.focus();
    };

    const handleKey = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
    };

    const agentLabel = agents.find(a => a.id === selectedAgent)?.data?.label || selectedAgent;

    return (
        <div className="flex flex-col h-full bg-gray-900/95 border-l border-gray-800 font-mono">
            {/* Header */}
            <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between flex-shrink-0 bg-gray-800/50">
                <div className="flex items-center gap-2">
                    <MessageSquare size={16} className="text-cyan-400" />
                    <span className="text-sm font-bold text-white">Chat com Agentes</span>
                </div>
                <div className="flex items-center gap-2">
                    {messages.length > 0 && (
                        <button
                            onClick={() => setMessages([])}
                            className="p-1.5 text-gray-600 hover:text-red-400 transition-colors rounded"
                            title="Limpar conversa"
                        >
                            <Trash2 size={13} />
                        </button>
                    )}
                    <button onClick={onClose} className="p-1.5 text-gray-600 hover:text-gray-300 transition-colors rounded">
                        <X size={15} />
                    </button>
                </div>
            </div>

            {/* Agent selector */}
            <div className="px-4 py-3 border-b border-gray-800/60 flex-shrink-0">
                <AgentSelect agents={agents} selected={selectedAgent} onSelect={handleSelectAgent} />
                {selectedAgent && (
                    <div className="mt-2 text-[10px] text-gray-600 flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                        Conectado a {agentLabel} · respostas em PT-PT
                    </div>
                )}
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-3 min-h-0">
                {messages.length === 0 ? (
                    <div className="flex-1 flex flex-col items-center justify-center text-center gap-3 py-8">
                        <div className="w-12 h-12 rounded-2xl bg-cyan-900/30 border border-cyan-800/40 flex items-center justify-center">
                            <MessageSquare size={22} className="text-cyan-500" />
                        </div>
                        <div>
                            <p className="text-sm font-bold text-gray-300 mb-1">
                                {selectedAgent ? `Conversa com ${agentLabel}` : 'Selecciona um agente'}
                            </p>
                            <p className="text-xs text-gray-600 max-w-[180px]">
                                {selectedAgent
                                    ? 'Escreve uma mensagem para começar a conversa.'
                                    : 'Escolhe o agente com quem queres falar no menu acima.'}
                            </p>
                        </div>
                        {selectedAgent && (
                            <div className="flex flex-col gap-1.5 w-full mt-2">
                                {[
                                    'O que podes fazer por mim?',
                                    'Resume as tuas responsabilidades.',
                                    'Que informação precisas de mim?'
                                ].map(q => (
                                    <button
                                        key={q}
                                        onClick={() => { setInput(q); inputRef.current?.focus(); }}
                                        className="text-left text-[11px] text-gray-500 hover:text-cyan-400 px-3 py-1.5 rounded-lg border border-gray-800 hover:border-cyan-900/50 transition-all truncate"
                                    >
                                        {q}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                ) : (
                    messages.map((msg, i) => <Message key={i} msg={msg} />)
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="px-4 py-3 border-t border-gray-800 flex-shrink-0">
                <div className="flex gap-2 items-end">
                    <textarea
                        ref={inputRef}
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        onKeyDown={handleKey}
                        disabled={!selectedAgent || sending}
                        placeholder={selectedAgent ? 'Escreve aqui... (Enter para enviar)' : 'Selecciona um agente'}
                        className="flex-1 bg-gray-950 border border-gray-700/80 rounded-xl px-3 py-2.5 text-xs text-gray-200 placeholder-gray-600 resize-none focus:outline-none focus:border-cyan-700/60 disabled:opacity-40 min-h-[40px] max-h-[100px]"
                        rows={1}
                        style={{ fieldSizing: 'content' }}
                    />
                    <button
                        onClick={send}
                        disabled={!input.trim() || !selectedAgent || sending}
                        className="p-2.5 bg-cyan-700 hover:bg-cyan-600 disabled:bg-gray-800 disabled:text-gray-600 text-white rounded-xl transition-colors flex-shrink-0"
                    >
                        {sending
                            ? <Loader2 size={15} className="animate-spin" />
                            : <Send size={15} />}
                    </button>
                </div>
                <div className="mt-1.5 text-[10px] text-gray-700 text-right">
                    ↵ enviar · Shift+↵ nova linha
                </div>
            </div>
        </div>
    );
}
