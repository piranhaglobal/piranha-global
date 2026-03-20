import { useState, useEffect } from 'react';
import { ChevronDown, Eye, EyeOff, LogIn, UserPlus } from 'lucide-react';

export default function LoginPage({ organogramMembers = [], onLogin }) {
    const [mode, setMode] = useState('login');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [selectedMember, setSelectedMember] = useState(null);
    const [showMemberList, setShowMemberList] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [members, setMembers] = useState([]);

    useEffect(() => {
        fetch('http://localhost:3001/api/organogram')
            .then(r => r.json())
            .then(d => setMembers(d.members || []))
            .catch(() => {});
    }, []);

    const handleRegister = async (e) => {
        e.preventDefault();
        setError('');
        if (!selectedMember) { setError('Por favor, selecciona quem és.'); return; }
        if (!email) { setError('Introduz o teu e-mail.'); return; }
        if (password.length < 8) { setError('A palavra-passe deve ter no mínimo 8 caracteres.'); return; }
        setLoading(true);
        try {
            const res = await fetch('http://localhost:3001/api/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    memberId: selectedMember.id,
                    name: selectedMember.name,
                    role: selectedMember.role,
                    level: selectedMember.level,
                    avatar: selectedMember.avatar,
                    email,
                    password,
                }),
            });
            const data = await res.json();
            if (!res.ok) { setError(data.error || 'Erro ao registar.'); return; }
            localStorage.setItem('piranha_token', data.token);
            onLogin(data.user, data.token);
        } catch {
            setError('Não foi possível ligar ao servidor.');
        } finally {
            setLoading(false);
        }
    };

    const handleLogin = async (e) => {
        e.preventDefault();
        setError('');
        if (!email || !password) { setError('Preenche todos os campos.'); return; }
        setLoading(true);
        try {
            const res = await fetch('http://localhost:3001/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password }),
            });
            const data = await res.json();
            if (!res.ok) { setError(data.error || 'Erro ao iniciar sessão.'); return; }
            localStorage.setItem('piranha_token', data.token);
            onLogin(data.user, data.token);
        } catch {
            setError('Não foi possível ligar ao servidor.');
        } finally {
            setLoading(false);
        }
    };

    const LEVEL_LABEL = {
        leadership: 'Leadership',
        'c-level': 'C-Level',
        director: 'Director',
        manager: 'Manager',
        specialist: 'Equipa',
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-950/95 backdrop-blur-sm font-mono">
            <div className="w-full max-w-md mx-4">
                {/* Logo */}
                <div className="text-center mb-8">
                    <div className="text-5xl mb-3">🦈</div>
                    <h1 className="text-xl font-black tracking-widest text-white uppercase">
                        PIRANHA GLOBAL HQ
                    </h1>
                    <p className="text-xs text-gray-500 mt-1 uppercase tracking-wider">
                        Acesso ao Escritório Virtual
                    </p>
                </div>

                {/* Card */}
                <div className="bg-gray-900/80 border border-gray-700/50 rounded-2xl p-6 shadow-2xl backdrop-blur">
                    {/* Mode tabs */}
                    <div className="flex rounded-xl overflow-hidden border border-gray-700/50 mb-6">
                        <button
                            onClick={() => { setMode('login'); setError(''); }}
                            className={`flex-1 py-2.5 text-xs font-bold uppercase tracking-wider transition-colors flex items-center justify-center gap-2 ${
                                mode === 'login'
                                    ? 'bg-indigo-600 text-white'
                                    : 'text-gray-500 hover:text-gray-300'
                            }`}
                        >
                            <LogIn size={12} /> Iniciar Sessão
                        </button>
                        <button
                            onClick={() => { setMode('register'); setError(''); }}
                            className={`flex-1 py-2.5 text-xs font-bold uppercase tracking-wider transition-colors flex items-center justify-center gap-2 ${
                                mode === 'register'
                                    ? 'bg-indigo-600 text-white'
                                    : 'text-gray-500 hover:text-gray-300'
                            }`}
                        >
                            <UserPlus size={12} /> Registar
                        </button>
                    </div>

                    <form onSubmit={mode === 'login' ? handleLogin : handleRegister} className="flex flex-col gap-4">
                        {/* Register: member picker */}
                        {mode === 'register' && (
                            <div>
                                <label className="block text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1.5">
                                    Quem és tu?
                                </label>
                                <div className="relative">
                                    <button
                                        type="button"
                                        onClick={() => setShowMemberList(v => !v)}
                                        className="w-full flex items-center justify-between bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-sm text-left hover:border-indigo-500/50 transition-colors"
                                    >
                                        {selectedMember ? (
                                            <div className="flex items-center gap-3">
                                                <span className="text-xl">{selectedMember.avatar}</span>
                                                <div>
                                                    <div className="text-white font-semibold text-sm">{selectedMember.name}</div>
                                                    <div className="text-gray-500 text-[10px]">{selectedMember.role}</div>
                                                </div>
                                            </div>
                                        ) : (
                                            <span className="text-gray-500">Selecciona o teu perfil...</span>
                                        )}
                                        <ChevronDown size={14} className="text-gray-500 flex-shrink-0" />
                                    </button>

                                    {showMemberList && (
                                        <div className="absolute top-full mt-1 left-0 right-0 z-50 bg-gray-800 border border-gray-700 rounded-xl shadow-xl max-h-64 overflow-y-auto">
                                            {(members.length > 0 ? members : organogramMembers).length === 0 ? (
                                                <div className="px-4 py-3 text-xs text-gray-500">Nenhum membro disponível</div>
                                            ) : (
                                                (members.length > 0 ? members : organogramMembers).map(m => (
                                                    <button
                                                        key={m.id}
                                                        type="button"
                                                        onClick={() => { setSelectedMember(m); setShowMemberList(false); }}
                                                        className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-indigo-900/30 transition-colors text-left"
                                                    >
                                                        <span className="text-lg flex-shrink-0">{m.avatar}</span>
                                                        <div className="flex-1 min-w-0">
                                                            <div className="text-sm text-white font-semibold truncate">{m.name}</div>
                                                            <div className="text-[10px] text-gray-500 truncate">{m.role}</div>
                                                        </div>
                                                        <span className="text-[9px] text-gray-600 uppercase tracking-wider flex-shrink-0">
                                                            {LEVEL_LABEL[m.level] || m.level}
                                                        </span>
                                                    </button>
                                                ))
                                            )}
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* Email */}
                        <div>
                            <label className="block text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1.5">
                                E-mail
                            </label>
                            <input
                                type="email"
                                value={email}
                                onChange={e => setEmail(e.target.value)}
                                placeholder="utilizador@piranha.pt"
                                className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500 transition-colors"
                                autoComplete="email"
                            />
                        </div>

                        {/* Password */}
                        <div>
                            <label className="block text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1.5">
                                Palavra-passe {mode === 'register' && <span className="text-gray-600 normal-case">(mín. 8 caracteres)</span>}
                            </label>
                            <div className="relative">
                                <input
                                    type={showPassword ? 'text' : 'password'}
                                    value={password}
                                    onChange={e => setPassword(e.target.value)}
                                    placeholder="••••••••"
                                    className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 pr-12 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500 transition-colors"
                                    autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(v => !v)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors"
                                >
                                    {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                                </button>
                            </div>
                        </div>

                        {/* Error */}
                        {error && (
                            <div className="bg-red-950/50 border border-red-800/50 rounded-xl px-4 py-2.5 text-xs text-red-400">
                                {error}
                            </div>
                        )}

                        {/* Submit */}
                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-3 rounded-xl transition-colors flex items-center justify-center gap-2 text-sm mt-1"
                        >
                            {loading ? (
                                <span className="animate-pulse">A processar...</span>
                            ) : mode === 'login' ? (
                                <><LogIn size={14} /> Iniciar Sessão</>
                            ) : (
                                <><UserPlus size={14} /> Criar Conta</>
                            )}
                        </button>
                    </form>

                    {/* Toggle mode link */}
                    <p className="text-center text-xs text-gray-600 mt-4">
                        {mode === 'login' ? (
                            <>Ainda não tens conta?{' '}
                                <button onClick={() => { setMode('register'); setError(''); }} className="text-indigo-400 hover:text-indigo-300 font-semibold">
                                    Registar
                                </button>
                            </>
                        ) : (
                            <>Já tens conta?{' '}
                                <button onClick={() => { setMode('login'); setError(''); }} className="text-indigo-400 hover:text-indigo-300 font-semibold">
                                    Iniciar sessão
                                </button>
                            </>
                        )}
                    </p>
                </div>
            </div>
        </div>
    );
}
