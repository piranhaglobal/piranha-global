import { useState, useCallback, useEffect } from 'react';
import ReactFlow, {
    Controls,
    Background,
    applyNodeChanges,
    applyEdgeChanges,
    addEdge
} from 'reactflow';
import 'reactflow/dist/style.css';
import axios from 'axios';
import CustomNode from './CustomNode';
import AgentConfigPanel from './AgentConfigPanel';
import VirtualOffice from './VirtualOffice';
import ChatPanel from './ChatPanel';
import { Play, Save, Settings2, Users, Bot, User, LayoutGrid, MonitorPlay, ArrowLeft, Terminal, Loader2, AlertTriangle, X, Send, MessageSquare } from 'lucide-react';

const nodeTypes = { custom: CustomNode };

// ─── Run Task Modal ──────────────────────────────────────────────────────────
function RunTaskModal({ onConfirm, onCancel }) {
    const [task, setTask] = useState('');
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
            <div className="bg-gray-900 border border-gray-700 rounded-2xl p-6 w-full max-w-md mx-4 shadow-2xl">
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                        <Terminal size={18} className="text-green-400" />
                        <h3 className="font-bold text-white">Iniciar Pipeline</h3>
                    </div>
                    <button onClick={onCancel} className="p-1 text-gray-500 hover:text-gray-300 rounded"><X size={16} /></button>
                </div>
                <p className="text-xs text-gray-500 mb-3">Descreve o que o squad deve executar nesta sessão.</p>
                <textarea
                    autoFocus
                    className="w-full bg-gray-950 border border-gray-700 rounded-lg p-3 text-sm text-gray-200 font-mono h-28 resize-none focus:outline-none focus:border-green-500/60"
                    placeholder="Ex: Criar blueprint para o projecto piranha-leads com scraping de estúdios PMU..."
                    value={task}
                    onChange={e => setTask(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter' && e.metaKey) onConfirm(task); }}
                />
                <div className="flex gap-3 mt-4">
                    <button
                        onClick={() => onConfirm(task || 'Executar pipeline padrão')}
                        disabled={!task.trim()}
                        className="flex-1 flex items-center justify-center gap-2 bg-green-700 hover:bg-green-600 disabled:bg-gray-800 disabled:text-gray-600 text-white font-bold py-3 rounded-xl transition-colors"
                    >
                        <Send size={15} /> Iniciar <span className="text-xs opacity-60 font-normal">⌘↵</span>
                    </button>
                    <button onClick={onCancel} className="px-4 text-gray-400 hover:text-gray-200 border border-gray-700 rounded-xl transition-colors">
                        Cancelar
                    </button>
                </div>
            </div>
        </div>
    );
}

// ─── Server Offline Banner ───────────────────────────────────────────────────
function ServerOfflineBanner() {
    return (
        <div className="flex-1 flex flex-col items-center justify-center gap-6 p-8">
            <div className="text-center">
                <div className="w-16 h-16 rounded-2xl bg-orange-900/30 border border-orange-800/50 flex items-center justify-center mx-auto mb-4">
                    <AlertTriangle size={28} className="text-orange-400" />
                </div>
                <h2 className="text-xl font-bold text-white mb-2">Servidor não está a correr</h2>
                <p className="text-sm text-gray-400 max-w-xs">O <code className="text-orange-300">squad-server.js</code> precisa de estar activo para carregar os agentes.</p>
            </div>
            <div className="bg-gray-950 border border-gray-800 rounded-xl p-5 w-full max-w-sm font-mono text-sm">
                <div className="text-gray-500 text-xs mb-2 uppercase tracking-wider">Terminal — na pasta do projecto</div>
                <div className="flex items-center gap-2 text-green-400">
                    <span className="text-gray-600">$</span>
                    <span>node squad-server.js</span>
                </div>
                <div className="mt-3 pt-3 border-t border-gray-800 text-gray-600 text-xs">
                    Porta: <span className="text-gray-400">3001</span>
                </div>
            </div>
            <p className="text-xs text-gray-600">Depois de arrancar, refresca esta página.</p>
        </div>
    );
}

// ─── Main Component ──────────────────────────────────────────────────────────
export default function SquadBuilder({ projectId, onBack }) {
    const [nodes, setNodes] = useState([]);
    const [edges, setEdges] = useState([]);
    const [config, setConfig] = useState(null);
    const [selectedNode, setSelectedNode] = useState(null);
    const [serverOnline, setServerOnline] = useState(null); // null = checking
    const [showRunModal, setShowRunModal] = useState(false);
    const [showChat, setShowChat] = useState(false);

    // Entrar pelo dashboard → ir directo para o escritório
    const [viewMode, setViewMode] = useState(projectId ? 'office' : 'builder');

    const loadConfig = () => {
        const url = projectId
            ? `http://localhost:3001/api/squad/${projectId}`
            : 'http://localhost:3001/api/squad';

        axios.get(url).then(res => {
            setConfig(res.data);
            setServerOnline(true);

            const newNodes = res.data.agents.map((ag, i) => ({
                id: ag.id,
                type: 'custom',
                position: { x: 350 + (i % 2) * 280, y: 100 + Math.floor(i / 2) * 160 },
                data: {
                    label: ag.activation,
                    description: ag.description,
                    role: ag.role,
                    model: ag.model,
                    type: 'bot'
                }
            }));

            newNodes.push({
                id: 'human-user',
                type: 'custom',
                position: { x: 50, y: 250 },
                data: { label: '@human', description: 'Aprovação Humana (Quality Gate)', role: 'gate', type: 'human' }
            });

            setNodes(newNodes);

            // Build edges from the first workflow
            const newEdges = [];
            const workflow = res.data.workflows?.[0];
            if (workflow) {
                for (let i = 0; i < workflow.steps.length - 1; i++) {
                    const step = workflow.steps[i];
                    const nextStep = workflow.steps[i + 1];
                    newEdges.push({
                        id: `e-${step.agent}-${nextStep.agent}`,
                        source: step.agent,
                        target: nextStep.agent,
                        animated: true,
                        style: { stroke: '#3b82f6', strokeWidth: 2 }
                    });
                    if (step.gate === 'human_approval') {
                        newEdges.push({
                            id: `gate-${step.agent}`,
                            source: step.agent,
                            target: 'human-user',
                            animated: true,
                            label: 'Gate',
                            style: { stroke: '#ec4899', strokeWidth: 2 },
                            labelStyle: { fill: '#fff', fontWeight: 700 },
                            labelBgStyle: { fill: '#1f2937' },
                        });
                    }
                }
            }
            setEdges(newEdges);
        }).catch(() => {
            setServerOnline(false);
        });
    };

    useEffect(() => {
        loadConfig();
        // Poll server status every 5s so it auto-recovers when server starts
        const poll = setInterval(loadConfig, 5000);
        return () => clearInterval(poll);
    }, [projectId]);

    const onNodesChange = useCallback((changes) => setNodes(nds => applyNodeChanges(changes, nds)), []);
    const onEdgesChange = useCallback((changes) => setEdges(eds => applyEdgeChanges(changes, eds)), []);
    const onConnect    = useCallback((params) => setEdges(eds => addEdge(params, eds)), []);

    const handleRunConfirm = async (task) => {
        setShowRunModal(false);
        try {
            await axios.post('http://localhost:3001/api/run', {
                request: task,
                squadId: projectId || 'piranha-dev'
            });
            setViewMode('office');
        } catch {
            alert('Erro ao iniciar. Verifica se o squad-server.js está a correr na porta 3001.');
        }
    };

    const squadName = config?.name || (projectId ? projectId.replace('piranha-', '').toUpperCase() : 'Piranha UI');
    const squadColor = config?.color || 'default';

    return (
        <div className="h-full w-full flex bg-gray-950 font-sans">
            {/* Sidebar */}
            <div className="w-72 bg-gray-900/80 backdrop-blur-md border-r border-gray-800/60 p-5 flex flex-col gap-6 z-10 shadow-2xl flex-shrink-0">

                {/* Header */}
                <div>
                    {onBack && (
                        <button onClick={onBack} className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 mb-3 transition-colors">
                            <ArrowLeft size={13} /> Dashboard
                        </button>
                    )}
                    <div className="flex items-center gap-2 mb-1">
                        <Users size={18} className="text-blue-400 flex-shrink-0" />
                        <h1 className="text-lg font-black text-white leading-tight">{squadName}</h1>
                    </div>
                    <p className="text-xs text-gray-500 leading-snug line-clamp-2">{config?.description || 'A carregar...'}</p>

                    {/* Server status indicator */}
                    <div className={`mt-3 flex items-center gap-2 text-xs px-2.5 py-1.5 rounded-md border ${
                        serverOnline === null ? 'border-gray-700 text-gray-500' :
                        serverOnline ? 'border-green-800/50 bg-green-950/30 text-green-400' :
                        'border-orange-800/50 bg-orange-950/30 text-orange-400'
                    }`}>
                        {serverOnline === null && <Loader2 size={11} className="animate-spin" />}
                        {serverOnline === true  && <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />}
                        {serverOnline === false && <AlertTriangle size={11} />}
                        <span>
                            {serverOnline === null && 'A verificar servidor...'}
                            {serverOnline === true  && `${nodes.filter(n => n.id !== 'human-user').length} agentes carregados`}
                            {serverOnline === false && 'squad-server.js offline'}
                        </span>
                    </div>
                </div>

                {/* View toggle */}
                <div className="flex bg-gray-950 p-1 rounded-lg border border-gray-800 gap-1">
                    <button
                        onClick={() => setViewMode('builder')}
                        className={`flex-1 flex justify-center items-center gap-1.5 py-2 rounded-md text-xs font-semibold transition-all ${viewMode === 'builder' ? 'bg-gray-800 text-white shadow' : 'text-gray-500 hover:text-gray-300'}`}
                    >
                        <LayoutGrid size={13} /> Builder
                    </button>
                    <button
                        onClick={() => setViewMode('office')}
                        className={`flex-1 flex justify-center items-center gap-1.5 py-2 rounded-md text-xs font-semibold transition-all ${viewMode === 'office' ? 'bg-blue-600/20 text-blue-400 border border-blue-500/20 shadow' : 'text-gray-500 hover:text-gray-300'}`}
                    >
                        <MonitorPlay size={13} /> Escritório
                    </button>
                </div>

                {/* Actions */}
                <div className="flex flex-col gap-2.5">
                    <button
                        onClick={() => serverOnline ? setShowRunModal(true) : null}
                        disabled={!serverOnline}
                        className={`flex justify-center items-center gap-2 px-4 py-3 rounded-xl font-bold text-sm transition-all border shadow-lg ${
                            serverOnline
                                ? 'bg-green-700 hover:bg-green-600 text-white border-green-600/40 shadow-green-900/30 cursor-pointer'
                                : 'bg-gray-800/50 text-gray-600 border-gray-700 cursor-not-allowed'
                        }`}
                    >
                        <Play size={16} />
                        {serverOnline === false ? 'Servidor offline' : 'Executar Pipeline'}
                    </button>

                    <button
                        onClick={() => setShowChat(v => !v)}
                        disabled={!serverOnline}
                        className={`flex justify-center items-center gap-2 px-4 py-2.5 rounded-xl font-medium text-sm transition-all border ${
                            showChat
                                ? 'bg-cyan-900/40 text-cyan-300 border-cyan-700/60 shadow-cyan-900/20'
                                : serverOnline
                                    ? 'bg-gray-800 hover:bg-gray-700 text-cyan-400 border-cyan-800/30'
                                    : 'bg-gray-800/50 text-gray-600 border-gray-700 cursor-not-allowed'
                        }`}
                    >
                        <MessageSquare size={15} /> {showChat ? 'Fechar Chat' : 'Chat com Agentes'}
                    </button>

                    {viewMode === 'builder' && serverOnline && (
                        <button className="flex justify-center items-center gap-2 bg-gray-800 hover:bg-gray-700 text-blue-400 px-4 py-2.5 rounded-xl font-medium text-sm transition-all border border-blue-500/20">
                            <Save size={15} /> Guardar config.yaml
                        </button>
                    )}
                </div>

                {/* Server offline - start command */}
                {serverOnline === false && (
                    <div className="bg-gray-950 border border-gray-800 rounded-xl p-4 font-mono text-xs">
                        <div className="text-gray-600 mb-2 uppercase tracking-wider" style={{ fontSize: '10px' }}>Para arrancar o servidor:</div>
                        <div className="text-green-400">
                            <span className="text-gray-600">$ </span>node squad-server.js
                        </div>
                        <div className="text-gray-600 mt-2 pt-2 border-t border-gray-800" style={{ fontSize: '10px' }}>
                            Na pasta: <span className="text-gray-400">piranha-global/</span>
                        </div>
                    </div>
                )}

                {/* Agent list when online */}
                {serverOnline && nodes.length > 0 && (
                    <div className="flex-1 overflow-y-auto">
                        <h3 className="text-xs font-bold text-gray-600 uppercase tracking-wider mb-3 flex items-center gap-2">
                            <Settings2 size={12} /> Agentes
                        </h3>
                        <div className="flex flex-col gap-2">
                            {nodes.filter(n => n.id !== 'human-user').map(node => (
                                <div
                                    key={node.id}
                                    onClick={() => { setSelectedNode(node); setViewMode('builder'); }}
                                    className="flex items-center gap-2.5 bg-gray-800/40 border border-gray-700/50 p-2.5 rounded-lg cursor-pointer hover:border-cyan-500/40 hover:bg-gray-800/80 transition-all"
                                >
                                    <div className="bg-cyan-500/10 p-1.5 rounded-md">
                                        <Bot size={13} className="text-cyan-400" />
                                    </div>
                                    <div className="overflow-hidden">
                                        <div className="text-xs font-bold text-gray-200 truncate font-mono">{node.data.label}</div>
                                        <div className="text-[10px] text-gray-600 truncate">
                                            {node.data.model?.includes('opus') ? 'Opus' : node.data.model?.includes('sonnet') ? 'Sonnet' : 'Haiku'}
                                        </div>
                                    </div>
                                </div>
                            ))}
                            {/* Human node */}
                            <div className="flex items-center gap-2.5 bg-indigo-900/20 border border-indigo-800/30 p-2.5 rounded-lg">
                                <div className="bg-indigo-500/10 p-1.5 rounded-md">
                                    <User size={13} className="text-indigo-400" />
                                </div>
                                <div>
                                    <div className="text-xs font-bold text-indigo-300 font-mono">@human</div>
                                    <div className="text-[10px] text-gray-600">Quality Gate</div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Main Area */}
            <div className="flex-1 h-full flex min-w-0">
                <div className="flex-1 relative min-w-0">
                    {serverOnline === false && viewMode !== 'office' ? (
                        <ServerOfflineBanner />
                    ) : viewMode === 'builder' ? (
                        <>
                            {nodes.length === 0 ? (
                                <div className="flex items-center justify-center h-full">
                                    <div className="text-center text-gray-600">
                                        <Loader2 size={32} className="animate-spin mx-auto mb-3" />
                                        <p className="text-sm">A carregar grafo de agentes...</p>
                                    </div>
                                </div>
                            ) : (
                                <>
                                    <div className="absolute top-4 left-4 z-10">
                                        <div className="flex items-center gap-2 bg-gray-800/80 backdrop-blur-md px-3 py-1.5 rounded-full border border-gray-700/50 shadow">
                                            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                                            <span className="text-xs font-medium text-gray-300">{squadName} — {nodes.filter(n=>n.id!=='human-user').length} agentes</span>
                                        </div>
                                    </div>
                                    <ReactFlow
                                        nodes={nodes}
                                        edges={edges}
                                        onNodesChange={onNodesChange}
                                        onEdgesChange={onEdgesChange}
                                        onConnect={onConnect}
                                        onNodeClick={(e, node) => setSelectedNode(node)}
                                        nodeTypes={nodeTypes}
                                        fitView
                                        attributionPosition="bottom-right"
                                        className="bg-gray-950"
                                    >
                                        <Background color="#334155" size={1} gap={20} />
                                        <Controls className="bg-gray-800 border-gray-700 fill-gray-400" />
                                    </ReactFlow>
                                    {selectedNode && (
                                        <AgentConfigPanel
                                            node={selectedNode}
                                            onClose={() => setSelectedNode(null)}
                                            squadId={projectId || 'piranha-dev'}
                                        />
                                    )}
                                </>
                            )}
                        </>
                    ) : (
                        <VirtualOffice agents={nodes} squadColor={squadColor} squadId={projectId || 'piranha-dev'} />
                    )}
                </div>

                {/* Chat Side Panel */}
                {showChat && serverOnline && (
                    <div className="w-80 flex-shrink-0 h-full border-l border-gray-800">
                        <ChatPanel
                            agents={nodes}
                            squadId={projectId || 'piranha-dev'}
                            onClose={() => setShowChat(false)}
                        />
                    </div>
                )}
            </div>

            {/* Run Task Modal */}
            {showRunModal && (
                <RunTaskModal
                    onConfirm={handleRunConfirm}
                    onCancel={() => setShowRunModal(false)}
                />
            )}
        </div>
    );
}
