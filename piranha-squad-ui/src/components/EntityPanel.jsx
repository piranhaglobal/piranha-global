import { X, MessageSquare, Users } from 'lucide-react';
import { STATE_COLORS, STATE_LABELS } from './office/world-engine.js';

const SQUAD_LABEL = {
    'piranha-leads':     'VENDAS',
    'piranha-workshops': 'WORKSHOPS',
    'piranha-comms':     'COMUNICAÇÃO',
    'piranha-supplies':  'OPERAÇÕES',
    'piranha-studio':    'ESTÚDIO',
};

const LEVEL_LABEL = {
    leadership: 'Leadership',
    'c-level':  'C-Level',
    director:   'Director',
    manager:    'Manager',
    specialist: 'Equipa',
};

export default function EntityPanel({ entity, onClose, onStartChat, onInviteMeeting }) {
    if (!entity) return null;

    const stateColor = STATE_COLORS[entity.state] || STATE_COLORS.idle;
    const stateLabel = STATE_LABELS[entity.state] || 'Em Espera';
    const isAgent = entity.type === 'agent';

    const initials = entity.name
        ? entity.name.split(' ').map(w => w[0]).join('').substring(0, 2).toUpperCase()
        : '??';

    return (
        <div className="absolute top-0 right-0 h-full w-72 bg-gray-900/95 border-l border-gray-800 z-30 flex flex-col font-mono shadow-2xl">
            {/* Header */}
            <div className="flex-shrink-0 p-4 border-b border-gray-800/60">
                <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                        {/* Avatar circle */}
                        <div
                            className="w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0 text-lg font-bold relative"
                            style={{ backgroundColor: entity.color || '#4f46e5' }}
                        >
                            {entity.avatar && !/^[A-Z]{1,3}$/.test(entity.avatar) ? (
                                <span className="text-xl">{entity.avatar}</span>
                            ) : (
                                <span className="text-white text-sm">{initials}</span>
                            )}
                            {/* State dot */}
                            <div
                                className="absolute bottom-0 right-0 w-3 h-3 rounded-full border-2 border-gray-900"
                                style={{ backgroundColor: stateColor }}
                            />
                        </div>
                        <div className="flex-1 min-w-0">
                            <div className="text-white font-bold text-sm truncate">{entity.name}</div>
                            <div className="text-gray-500 text-[10px] truncate mt-0.5">
                                {isAgent
                                    ? (SQUAD_LABEL[entity.squadId] || entity.squadId || 'Agente')
                                    : (LEVEL_LABEL[entity.level] || entity.level || 'Colaborador')
                                }
                            </div>
                            {/* Type badge */}
                            <div className={`inline-flex items-center mt-1 px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider ${
                                isAgent
                                    ? 'bg-indigo-950/70 text-indigo-400 border border-indigo-800/50'
                                    : 'bg-blue-950/70 text-blue-400 border border-blue-800/50'
                            }`}>
                                {isAgent ? 'AGENTE IA' : 'COLABORADOR'}
                            </div>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="flex-shrink-0 p-1 text-gray-600 hover:text-gray-300 transition-colors rounded"
                    >
                        <X size={14} />
                    </button>
                </div>
            </div>

            {/* Status section */}
            <div className="flex-shrink-0 p-4 border-b border-gray-800/40">
                <div className="text-[9px] text-gray-600 uppercase tracking-wider mb-2">Estado Actual</div>
                <div className="flex items-center gap-2">
                    <div
                        className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                        style={{ backgroundColor: stateColor }}
                    />
                    <span className="text-sm font-semibold" style={{ color: stateColor }}>
                        {stateLabel}
                    </span>
                </div>
                {entity.bubble && entity.bubbleAlpha > 0 && (
                    <div className="mt-2 bg-gray-800/60 border border-gray-700/40 rounded-lg p-2.5">
                        <div className="text-[9px] text-gray-600 uppercase tracking-wider mb-1">Tarefa Actual</div>
                        <p className="text-xs text-gray-300 leading-relaxed">{entity.bubble}</p>
                    </div>
                )}
            </div>

            {/* Department / Squad info */}
            <div className="flex-shrink-0 p-4 border-b border-gray-800/40">
                <div className="text-[9px] text-gray-600 uppercase tracking-wider mb-2">
                    {isAgent ? 'Equipa / Squad' : 'Nível Hierárquico'}
                </div>
                {isAgent ? (
                    <div className="flex items-center gap-2">
                        <div
                            className="w-2 h-2 rounded-full"
                            style={{ backgroundColor: '#6366f1' }}
                        />
                        <span className="text-xs text-gray-300">
                            {SQUAD_LABEL[entity.squadId] || entity.squadId || '—'}
                        </span>
                        <span className="text-[9px] text-gray-600 uppercase">
                            {entity.squadId || ''}
                        </span>
                    </div>
                ) : (
                    <div className="flex items-center gap-2">
                        <div
                            className="w-2 h-2 rounded-full"
                            style={{ backgroundColor: entity.color || '#475569' }}
                        />
                        <span className="text-xs text-gray-300">
                            {LEVEL_LABEL[entity.level] || entity.level || '—'}
                        </span>
                    </div>
                )}
            </div>

            {/* Action buttons */}
            <div className="flex-1 p-4 flex flex-col gap-2">
                <div className="text-[9px] text-gray-600 uppercase tracking-wider mb-1">Acções</div>
                <button
                    onClick={() => onStartChat && onStartChat(entity)}
                    className="w-full flex items-center gap-2.5 bg-indigo-900/30 hover:bg-indigo-800/50 border border-indigo-700/40 hover:border-indigo-600/60 text-indigo-300 text-xs font-semibold px-3 py-2.5 rounded-lg transition-all"
                >
                    <MessageSquare size={13} />
                    Iniciar Conversa
                </button>
                <button
                    onClick={() => onInviteMeeting && onInviteMeeting(entity)}
                    className="w-full flex items-center gap-2.5 bg-purple-900/30 hover:bg-purple-800/50 border border-purple-700/40 hover:border-purple-600/60 text-purple-300 text-xs font-semibold px-3 py-2.5 rounded-lg transition-all"
                >
                    <Users size={13} />
                    Convocar Reunião
                </button>
            </div>

            {/* Footer */}
            <div className="flex-shrink-0 p-3 border-t border-gray-800/40">
                <p className="text-[9px] text-gray-700 text-center">
                    Clica no escritório para fechar
                </p>
            </div>
        </div>
    );
}
