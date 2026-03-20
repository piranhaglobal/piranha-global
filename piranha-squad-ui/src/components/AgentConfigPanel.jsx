import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { X, Save, Wrench, BookOpen, MessageSquare, Plus, Trash2, Upload, FileText, Loader2, ChevronDown, ChevronUp } from 'lucide-react';

// ─── Knowledge Entry Form ─────────────────────────────────────────────────────
function KnowledgeForm({ squadId, onSaved }) {
    const [name, setName] = useState('');
    const [content, setContent] = useState('');
    const [saving, setSaving] = useState(false);
    const fileRef = useRef(null);

    const handleFile = (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (ev) => {
            setContent(ev.target.result);
            if (!name) setName(file.name.replace(/\.(md|txt|pdf)$/, ''));
        };
        reader.readAsText(file);
    };

    const handleSave = async () => {
        if (!name.trim() || !content.trim()) return;
        setSaving(true);
        try {
            await axios.post(`http://localhost:3001/api/knowledge?squad=${squadId}`, { name: name.trim(), content: content.trim() });
            setName('');
            setContent('');
            onSaved();
        } catch (e) {
            console.error('Failed to save knowledge entry', e);
        }
        setSaving(false);
    };

    return (
        <div className="flex flex-col gap-2.5 bg-gray-950/60 border border-amber-900/40 rounded-xl p-3">
            <input
                type="text"
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-amber-500/60"
                placeholder="Nome do documento..."
                value={name}
                onChange={e => setName(e.target.value)}
            />
            <textarea
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 font-mono placeholder-gray-600 h-28 resize-none focus:outline-none focus:border-amber-500/60"
                placeholder="Escreve o conteúdo aqui, ou faz upload de um ficheiro .txt / .md abaixo..."
                value={content}
                onChange={e => setContent(e.target.value)}
            />
            <div className="flex gap-2">
                <button
                    onClick={() => fileRef.current?.click()}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-gray-700 text-xs text-gray-400 hover:border-amber-700/50 hover:text-amber-400 transition-colors"
                >
                    <Upload size={13} /> Ficheiro .txt / .md
                </button>
                <input ref={fileRef} type="file" accept=".txt,.md" className="hidden" onChange={handleFile} />
                <button
                    onClick={handleSave}
                    disabled={!name.trim() || !content.trim() || saving}
                    className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-amber-700 hover:bg-amber-600 disabled:bg-gray-800 disabled:text-gray-600 text-white text-xs font-bold transition-colors"
                >
                    {saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
                    {saving ? 'A guardar...' : 'Guardar'}
                </button>
            </div>
        </div>
    );
}

// ─── Knowledge Entry Item ─────────────────────────────────────────────────────
function KnowledgeItem({ entry, squadId, onDeleted }) {
    const [expanded, setExpanded] = useState(false);
    const [deleting, setDeleting] = useState(false);

    const handleDelete = async () => {
        setDeleting(true);
        try {
            await axios.delete(`http://localhost:3001/api/knowledge/${entry.id}?squad=${squadId}`);
            onDeleted();
        } catch (e) {
            console.error(e);
        }
        setDeleting(false);
    };

    return (
        <div className="border border-gray-700/60 rounded-lg overflow-hidden">
            <div
                className="flex items-center justify-between px-3 py-2 bg-gray-800/40 cursor-pointer hover:bg-gray-800/70 transition-colors"
                onClick={() => setExpanded(v => !v)}
            >
                <div className="flex items-center gap-2 min-w-0">
                    <FileText size={13} className="text-amber-500 flex-shrink-0" />
                    <span className="text-xs font-semibold text-gray-200 truncate">{entry.name}</span>
                </div>
                <div className="flex items-center gap-1.5 flex-shrink-0 ml-2">
                    <button
                        onClick={e => { e.stopPropagation(); handleDelete(); }}
                        disabled={deleting}
                        className="p-1 text-gray-600 hover:text-red-400 transition-colors rounded"
                    >
                        {deleting ? <Loader2 size={11} className="animate-spin" /> : <Trash2 size={11} />}
                    </button>
                    {expanded ? <ChevronUp size={13} className="text-gray-500" /> : <ChevronDown size={13} className="text-gray-500" />}
                </div>
            </div>
            {expanded && (
                <div className="px-3 py-2 bg-gray-950/50 border-t border-gray-700/40 max-h-40 overflow-y-auto">
                    <pre className="text-[11px] text-gray-400 whitespace-pre-wrap font-mono leading-relaxed">{entry.content}</pre>
                </div>
            )}
        </div>
    );
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function AgentConfigPanel({ node, onClose, squadId = 'piranha-dev' }) {
    const [prompt, setPrompt] = useState('');
    const [saving, setSaving] = useState(false);
    const [kbEntries, setKbEntries] = useState([]);
    const [showKbForm, setShowKbForm] = useState(false);

    const loadPrompt = () => {
        if (!node) return;
        setPrompt('A carregar...');
        axios.get(`http://localhost:3001/api/agent/${node.id}?squad=${squadId}`)
            .then(res => setPrompt(res.data.content || ''))
            .catch(() => setPrompt(''));
    };

    const loadKnowledge = () => {
        axios.get(`http://localhost:3001/api/knowledge?squad=${squadId}`)
            .then(res => setKbEntries(res.data.entries || []))
            .catch(() => {});
    };

    useEffect(() => {
        loadPrompt();
        loadKnowledge();
    }, [node, squadId]);

    const handleSave = async () => {
        setSaving(true);
        try {
            await axios.post(`http://localhost:3001/api/agent/${node.id}?squad=${squadId}`, { content: prompt });
            setTimeout(() => setSaving(false), 500);
        } catch (e) {
            console.error('Failed to save', e);
            setSaving(false);
        }
    };

    if (!node) return null;

    return (
        <div className="w-96 bg-gray-900/95 backdrop-blur-md border-l border-gray-700 shadow-2xl flex flex-col h-full right-0 top-0 absolute z-50">
            {/* Header */}
            <div className="p-4 border-b border-gray-800 flex justify-between items-center bg-gray-800/80 flex-shrink-0">
                <div className="overflow-hidden">
                    <h2 className="font-bold text-lg text-gray-100 truncate">{node.data.label}</h2>
                    <span className="text-xs text-blue-400 font-mono truncate block">{node.data.model}</span>
                </div>
                <button onClick={onClose} className="p-1.5 hover:bg-red-500/20 text-gray-400 hover:text-red-400 rounded-md transition-colors flex-shrink-0">
                    <X size={18} />
                </button>
            </div>

            <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-6">
                {/* System Prompt */}
                <div>
                    <label className="flex items-center gap-2 text-sm font-semibold text-gray-300 mb-3">
                        <MessageSquare size={16} className="text-pink-500" /> System Prompt
                    </label>
                    <textarea
                        className="w-full bg-gray-950/80 border border-gray-700/80 rounded-lg p-3 text-sm h-64 focus:border-pink-500/50 focus:ring-1 focus:ring-pink-500/50 font-mono text-gray-300 transition-all resize-none"
                        value={prompt}
                        onChange={e => setPrompt(e.target.value)}
                        placeholder="Diretrizes do agente, papel, tom de voz..."
                    />
                </div>

                {/* Knowledge Base */}
                <div>
                    <div className="flex items-center justify-between mb-3">
                        <label className="flex items-center gap-2 text-sm font-semibold text-gray-300">
                            <BookOpen size={16} className="text-amber-500" /> Base de Conhecimento
                        </label>
                        <button
                            onClick={() => setShowKbForm(v => !v)}
                            className="flex items-center gap-1 text-xs text-amber-500 hover:text-amber-300 transition-colors"
                        >
                            <Plus size={13} /> Adicionar
                        </button>
                    </div>

                    {showKbForm && (
                        <div className="mb-3">
                            <KnowledgeForm
                                squadId={squadId}
                                onSaved={() => { loadKnowledge(); setShowKbForm(false); }}
                            />
                        </div>
                    )}

                    {kbEntries.length > 0 ? (
                        <div className="flex flex-col gap-2">
                            {kbEntries.map(entry => (
                                <KnowledgeItem
                                    key={entry.id}
                                    entry={entry}
                                    squadId={squadId}
                                    onDeleted={loadKnowledge}
                                />
                            ))}
                        </div>
                    ) : (
                        <div
                            onClick={() => setShowKbForm(true)}
                            className="bg-amber-950/20 border border-amber-900/50 border-dashed rounded-lg p-4 text-center cursor-pointer hover:bg-amber-900/20 transition-colors"
                        >
                            <div className="text-sm text-gray-400 hover:text-amber-400 font-medium transition-colors">+ Adicionar documento de conhecimento</div>
                            <div className="text-xs text-gray-600 mt-1">Texto manual ou upload de ficheiro .txt / .md</div>
                        </div>
                    )}
                </div>

                {/* Tools */}
                <div>
                    <label className="flex items-center gap-2 text-sm font-semibold text-gray-300 mb-3">
                        <Wrench size={16} className="text-teal-500" /> Ferramentas
                    </label>
                    <div className="flex flex-col gap-2">
                        {['Evolution API (WhatsApp)', 'Shopify Admin Piranha', 'Instagram Graph API', 'Klaviyo CRM', 'Web Scraper Automático'].map(tool => (
                            <label key={tool} className="flex items-center gap-3 bg-gray-800/60 p-3 rounded-lg cursor-pointer hover:bg-gray-800 border border-transparent hover:border-gray-700 transition-all">
                                <input type="checkbox" className="rounded bg-gray-900 border-gray-700 text-teal-500 focus:ring-teal-500/50 w-4 h-4 cursor-pointer" />
                                <span className="text-sm text-gray-300 font-medium">{tool}</span>
                            </label>
                        ))}
                    </div>
                </div>
            </div>

            {/* Save footer */}
            <div className="p-4 border-t border-gray-800 bg-gray-900/90 backdrop-blur-sm flex-shrink-0">
                <button
                    onClick={handleSave}
                    className="w-full bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white font-medium py-3 rounded-lg flex justify-center items-center gap-2 shadow-lg shadow-blue-900/20 transition-all active:scale-[0.98]"
                >
                    {saving ? (
                        <><Loader2 size={16} className="animate-spin" /> A guardar...</>
                    ) : (
                        <><Save size={18} /> Guardar Perfil</>
                    )}
                </button>
            </div>
        </div>
    );
}
