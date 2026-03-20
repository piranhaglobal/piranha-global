const express = require('express');
const fs = require('fs-extra');
const path = require('path');
const yaml = require('yaml');
const cors = require('cors');
const { spawn } = require('child_process');
require('dotenv').config();
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');
const JWT_SECRET = process.env.JWT_SECRET || 'piranha-hq-2026';
const usersPath = path.join(__dirname, 'data', 'users.json');
function getUsers() { try { return JSON.parse(fs.readFileSync(usersPath, 'utf8')); } catch { return []; } }
function saveUsers(u) { fs.ensureDirSync(path.join(__dirname, 'data')); fs.writeFileSync(usersPath, JSON.stringify(u, null, 2)); }

const Anthropic = require('@anthropic-ai/sdk');
const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

const app = express();
app.use(cors());
app.use(express.json({ limit: '2mb' }));

const squadsDir = path.join(__dirname, 'squads');
const configPath = path.join(squadsDir, 'piranha-dev', 'config.yaml');

// List all available squads
app.get('/api/squads', (req, res) => {
    try {
        const squadDirs = fs.readdirSync(squadsDir).filter(d => {
            const dPath = path.join(squadsDir, d);
            const cfg = path.join(dPath, 'config.yaml');
            return fs.statSync(dPath).isDirectory() && fs.existsSync(cfg);
        });
        const squads = squadDirs.map(d => {
            const cfg = path.join(squadsDir, d, 'config.yaml');
            const data = yaml.parse(fs.readFileSync(cfg, 'utf8'));
            return {
                id: d,
                name: data.name,
                description: data.description,
                color: data.color || 'blue',
                icon: data.icon || '🤖',
                priority: data.priority || 99,
                status: data.status || 'active',
                agentCount: (data.agents || []).length
            };
        });
        squads.sort((a, b) => a.priority - b.priority);
        res.json(squads);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// Get specific squad config by ID
app.get('/api/squad/:squadId', (req, res) => {
    try {
        const squadPath = path.join(squadsDir, req.params.squadId, 'config.yaml');
        if (!fs.existsSync(squadPath)) {
            return res.status(404).json({ error: `Squad '${req.params.squadId}' not found` });
        }
        const data = yaml.parse(fs.readFileSync(squadPath, 'utf8'));
        res.json(data);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// Backward-compatible default squad (piranha-dev)
app.get('/api/squad', (req, res) => {
    try {
        if (!fs.existsSync(configPath)) {
            return res.status(404).json({ error: 'config.yaml not found' });
        }
        const fileContent = fs.readFileSync(configPath, 'utf8');
        const data = yaml.parse(fileContent);
        res.json(data);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.post('/api/squad', (req, res) => {
    try {
        const newYaml = yaml.stringify(req.body);
        fs.writeFileSync(configPath, newYaml, 'utf8');
        res.json({ success: true });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// ─── API: Agent prompt (squad-aware) ─────────────────────────────────────────
app.get('/api/agent/:id', (req, res) => {
    try {
        const { id } = req.params;
        const squadId = req.query.squad || 'piranha-dev';
        const agentsDir = path.join(__dirname, 'squads', squadId, 'agents');

        // Try exact match first, then with -piranha suffix, then without
        const candidates = [
            path.join(agentsDir, `${id}.md`),
            path.join(agentsDir, `${id}-piranha.md`),
        ];
        let content = '';
        for (const p of candidates) {
            if (fs.existsSync(p)) { content = fs.readFileSync(p, 'utf8'); break; }
        }
        res.json({ content });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.post('/api/agent/:id', (req, res) => {
    try {
        const { id } = req.params;
        const squadId = req.query.squad || 'piranha-dev';
        const agentsDir = path.join(__dirname, 'squads', squadId, 'agents');
        fs.ensureDirSync(agentsDir);

        // Determine file name: if existing file has -piranha, keep it; else use id.md
        let mdPath = path.join(agentsDir, `${id}.md`);
        const legacyPath = path.join(agentsDir, `${id}-piranha.md`);
        if (fs.existsSync(legacyPath)) mdPath = legacyPath;

        fs.writeFileSync(mdPath, req.body.content || '', 'utf8');
        res.json({ success: true });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// ─── API: Knowledge Base ──────────────────────────────────────────────────────
app.get('/api/knowledge', (req, res) => {
    try {
        const squadId = req.query.squad || 'piranha-dev';
        const kbDir = path.join(__dirname, 'squads', squadId, 'knowledge');
        if (!fs.existsSync(kbDir)) return res.json({ entries: [] });
        const files = fs.readdirSync(kbDir).filter(f => f.endsWith('.md') || f.endsWith('.txt'));
        const entries = files.map(f => {
            const fullPath = path.join(kbDir, f);
            return {
                id: f,
                name: f.replace(/\.(md|txt)$/, ''),
                content: fs.readFileSync(fullPath, 'utf8'),
                updatedAt: fs.statSync(fullPath).mtime.toISOString()
            };
        });
        res.json({ entries });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.post('/api/knowledge', (req, res) => {
    try {
        const squadId = req.query.squad || 'piranha-dev';
        const { name, content } = req.body;
        if (!name || !content) return res.status(400).json({ error: 'name and content required' });
        const kbDir = path.join(__dirname, 'squads', squadId, 'knowledge');
        fs.ensureDirSync(kbDir);
        const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
        const filePath = path.join(kbDir, `${slug}.md`);
        fs.writeFileSync(filePath, `# ${name}\n\n${content}`, 'utf8');
        res.json({ success: true, id: `${slug}.md` });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.delete('/api/knowledge/:id', (req, res) => {
    try {
        const squadId = req.query.squad || 'piranha-dev';
        const filePath = path.join(__dirname, 'squads', squadId, 'knowledge', req.params.id);
        if (fs.existsSync(filePath)) fs.removeSync(filePath);
        res.json({ success: true });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

const PORT = 3001;

// ─── Squad-aware path helpers ─────────────────────────────────────────────────
function getSquadPaths(squadId) {
    const base = path.join(__dirname, 'squads', squadId || 'piranha-dev', 'data');
    return {
        dataDir: base,
        logsPath: path.join(base, 'logs.jsonl'),
        statePath: path.join(base, 'state.json'),
    };
}

// ─── Workflow Simulation (for squads without orchestrator.py) ─────────────────
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function simulateWorkflow(squadId, config, task) {
    const { logsPath, statePath } = getSquadPaths(squadId);

    const writeLog = (agent, action) => {
        const entry = JSON.stringify({
            time: new Date().toLocaleTimeString('pt-PT'),
            agent,
            action
        }) + '\n';
        fs.appendFileSync(logsPath, entry);
    };

    const waitForApproval = () => new Promise(resolve => {
        const check = setInterval(() => {
            try {
                const s = JSON.parse(fs.readFileSync(statePath, 'utf8'));
                if (s.status === 'resolved') { clearInterval(check); resolve(s.decision); }
            } catch {}
        }, 500);
    });

    const workflow = config.workflows?.[0];
    if (!workflow) {
        writeLog('system', 'Nenhum workflow configurado para este squad.');
        fs.writeFileSync(statePath, JSON.stringify({ status: 'completed' }));
        return;
    }

    writeLog('system', `📋 Pipeline: ${workflow.description}`);
    writeLog('system', `📝 Pedido: ${task.substring(0, 80)}${task.length > 80 ? '...' : ''}`);
    await sleep(800);

    for (const step of workflow.steps) {
        const agentConf = config.agents?.find(a => a.id === step.agent);
        const label = agentConf?.activation || `@${step.agent}`;
        const taskName = step.task.replace(/-/g, ' ');

        writeLog(label, `A iniciar: ${taskName}`);
        await sleep(1200);
        writeLog(label, `A processar pedido...`);
        await sleep(2000 + Math.random() * 1500);
        writeLog(label, `✓ ${taskName} concluído`);
        await sleep(400);

        if (step.gate === 'human_approval') {
            writeLog('@human', `⏸ Quality Gate — Aguarda aprovação de Pedro Dias`);
            fs.writeFileSync(statePath, JSON.stringify({
                status: 'waiting_human_approval',
                prompt: `O ${label} concluiu "${taskName}".\nAprovar para continuar o pipeline?`
            }));
            const decision = await waitForApproval();
            if (decision === 'n') {
                writeLog('system', '❌ Pipeline interrompido — decisão humana.');
                fs.writeFileSync(statePath, JSON.stringify({ status: 'rejected' }));
                return;
            }
            fs.writeFileSync(statePath, JSON.stringify({ status: 'running' }));
            writeLog('@human', `✓ Aprovado — a continuar...`);
            await sleep(500);
        }
    }

    writeLog('system', '✅ Pipeline concluído com sucesso!');
    fs.writeFileSync(statePath, JSON.stringify({ status: 'completed' }));
}

// ─── API: Logs ─────────────────────────────────────────────────────────────────
app.get('/api/logs', (req, res) => {
    try {
        const { logsPath, statePath } = getSquadPaths(req.query.squad);
        if (!fs.existsSync(logsPath)) return res.json({ logs: [], state: null });
        const logs = fs.readFileSync(logsPath, 'utf8')
            .split('\n').filter(l => l.trim()).map(l => JSON.parse(l));
        let state = null;
        if (fs.existsSync(statePath)) state = JSON.parse(fs.readFileSync(statePath, 'utf8'));
        res.json({ logs, state });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// ─── API: Run pipeline ────────────────────────────────────────────────────────
app.post('/api/run', (req, res) => {
    try {
        const { request, squadId = 'piranha-dev' } = req.body;
        const { dataDir, logsPath, statePath } = getSquadPaths(squadId);
        fs.ensureDirSync(dataDir);
        fs.writeFileSync(logsPath, '', 'utf8');
        fs.writeFileSync(statePath, JSON.stringify({ status: 'running' }), 'utf8');

        const orchPath = path.join(__dirname, 'squads', squadId, 'orchestrator.py');
        if (fs.existsSync(orchPath)) {
            spawn('python3', ['orchestrator.py', '--headless', request], {
                cwd: path.join(__dirname, 'squads', squadId)
            });
            res.json({ success: true, mode: 'orchestrator' });
        } else {
            // Simulation mode for squads without orchestrator.py
            const cfgPath = path.join(__dirname, 'squads', squadId, 'config.yaml');
            const config = yaml.parse(fs.readFileSync(cfgPath, 'utf8'));
            res.json({ success: true, mode: 'simulation' });
            simulateWorkflow(squadId, config, request).catch(console.error);
        }
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// ─── API: Approve quality gate ────────────────────────────────────────────────
app.post('/api/approve', (req, res) => {
    try {
        const { decision, squadId = 'piranha-dev' } = req.body;
        const { statePath } = getSquadPaths(squadId);
        if (fs.existsSync(statePath)) {
            const state = JSON.parse(fs.readFileSync(statePath, 'utf8'));
            if (state.status === 'waiting_human_approval') {
                state.status = 'resolved';
                state.decision = decision;
                fs.writeFileSync(statePath, JSON.stringify(state), 'utf8');
                return res.json({ success: true });
            }
        }
        res.status(400).json({ error: 'No pending approval' });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// ─── API: Chat with agent (streaming SSE) ────────────────────────────────────
app.post('/api/chat', async (req, res) => {
    try {
        const { squadId = 'piranha-dev', agentId, message, history = [] } = req.body;

        // Load agent system prompt
        const agentsDir = path.join(__dirname, 'squads', squadId, 'agents');
        const candidates = [
            path.join(agentsDir, `${agentId}.md`),
            path.join(agentsDir, `${agentId}-piranha.md`),
        ];
        let systemPrompt = '';
        for (const f of candidates) {
            if (fs.existsSync(f)) { systemPrompt = fs.readFileSync(f, 'utf8'); break; }
        }
        if (!systemPrompt) {
            return res.status(404).json({ error: `Agent ${agentId} not found in squad ${squadId}` });
        }

        // Also inject squad knowledge base if available
        const kbDir = path.join(__dirname, 'squads', squadId, 'knowledge');
        if (fs.existsSync(kbDir)) {
            const kbFiles = fs.readdirSync(kbDir).filter(f => f.match(/\.(md|txt)$/));
            if (kbFiles.length > 0) {
                const kbContent = kbFiles.map(f =>
                    `\n\n## Conhecimento: ${f}\n${fs.readFileSync(path.join(kbDir, f), 'utf8')}`
                ).join('');
                systemPrompt += `\n\n---\n# Base de Conhecimento do Squad\n${kbContent}`;
            }
        }

        // SSE streaming response
        res.setHeader('Content-Type', 'text/event-stream');
        res.setHeader('Cache-Control', 'no-cache');
        res.setHeader('Connection', 'keep-alive');

        const messages = [
            ...history.map(h => ({ role: h.role, content: h.content })),
            { role: 'user', content: message }
        ];

        const stream = await anthropic.messages.stream({
            model: 'claude-sonnet-4-5-20251001',
            max_tokens: 2048,
            system: systemPrompt,
            messages,
        });

        for await (const chunk of stream) {
            if (chunk.type === 'content_block_delta' && chunk.delta?.text) {
                res.write(`data: ${JSON.stringify({ text: chunk.delta.text })}\n\n`);
            }
        }
        res.write('data: [DONE]\n\n');
        res.end();
    } catch (err) {
        console.error('Chat error:', err.message);
        if (!res.headersSent) res.status(500).json({ error: err.message });
    }
});

// ─── API: Organogram ──────────────────────────────────────────────────────────
app.get('/api/organogram', (req, res) => {
    try {
        const orgPath = path.join(__dirname, 'knowledge', 'organogram.json');
        if (!fs.existsSync(orgPath)) return res.json({ members: [], hierarchy: [] });
        res.json(JSON.parse(fs.readFileSync(orgPath, 'utf8')));
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// ─── API: Auth — Register ─────────────────────────────────────────────────────
app.post('/api/auth/register', async (req, res) => {
    try {
        const { memberId, name, role, level, avatar, email, password } = req.body;
        if (!email || !password || !name) return res.status(400).json({ error: 'Campos obrigatórios em falta.' });
        const users = getUsers();
        if (users.find(u => u.email === email)) return res.status(409).json({ error: 'Este e-mail já está registado.' });
        const passwordHash = await bcrypt.hash(password, 10);
        const id = memberId || `user-${Date.now()}`;
        const user = { id, email, name, role: role || '', level: level || 'specialist', avatar: avatar || '👤', passwordHash };
        users.push(user);
        saveUsers(users);
        const payload = { id, email, name, avatar: user.avatar, role: user.role, level: user.level };
        const token = jwt.sign(payload, JWT_SECRET, { expiresIn: '30d' });
        res.json({ token, user: { id, name, role: user.role, avatar: user.avatar, level: user.level } });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// ─── API: Auth — Login ────────────────────────────────────────────────────────
app.post('/api/auth/login', async (req, res) => {
    try {
        const { email, password } = req.body;
        if (!email || !password) return res.status(400).json({ error: 'E-mail e palavra-passe são obrigatórios.' });
        const users = getUsers();
        const user = users.find(u => u.email === email);
        if (!user) return res.status(401).json({ error: 'Credenciais inválidas.' });
        const valid = await bcrypt.compare(password, user.passwordHash);
        if (!valid) return res.status(401).json({ error: 'Credenciais inválidas.' });
        const payload = { id: user.id, email: user.email, name: user.name, avatar: user.avatar, role: user.role, level: user.level };
        const token = jwt.sign(payload, JWT_SECRET, { expiresIn: '30d' });
        res.json({ token, user: { id: user.id, name: user.name, role: user.role, avatar: user.avatar, level: user.level } });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// ─── API: Auth — List Users ───────────────────────────────────────────────────
app.get('/api/auth/users', (req, res) => {
    try {
        const users = getUsers().map(({ passwordHash, ...u }) => u);
        res.json({ users });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// ─── API: Meeting Chat (SSE streaming) ───────────────────────────────────────
app.post('/api/meeting/chat', async (req, res) => {
    try {
        const { participants = [], message, history = [], topic = '' } = req.body;

        res.setHeader('Content-Type', 'text/event-stream');
        res.setHeader('Cache-Control', 'no-cache');
        res.setHeader('Connection', 'keep-alive');

        const agentParticipants = participants.filter(p => p.type === 'agent');

        for (const participant of agentParticipants) {
            const { agentId, squadId, name } = participant;
            const agentsDir = path.join(__dirname, 'squads', squadId || 'piranha-dev', 'agents');
            const candidates = [
                path.join(agentsDir, `${agentId}.md`),
                path.join(agentsDir, `${agentId}-piranha.md`),
            ];
            let systemPrompt = '';
            for (const f of candidates) {
                if (fs.existsSync(f)) { systemPrompt = fs.readFileSync(f, 'utf8'); break; }
            }
            if (!systemPrompt) {
                systemPrompt = `És ${name}, um agente de IA da Piranha Global.`;
            }
            systemPrompt += `\n\n---\n# REUNIÃO VIRTUAL\nEstás numa reunião com outros agentes e membros da equipa.\nTópico: ${topic}\nResponde de forma concisa (máx 3 parágrafos) e focada no tópico.`;

            res.write(`data: ${JSON.stringify({ type: 'agent_start', agentId, name })}\n\n`);

            const messages = [
                ...history.map(h => ({ role: h.role, content: h.content })),
                { role: 'user', content: message }
            ];

            try {
                const stream = await anthropic.messages.stream({
                    model: 'claude-sonnet-4-5-20251001',
                    max_tokens: 600,
                    system: systemPrompt,
                    messages,
                });

                for await (const chunk of stream) {
                    if (chunk.type === 'content_block_delta' && chunk.delta?.text) {
                        res.write(`data: ${JSON.stringify({ type: 'text', agentId, text: chunk.delta.text })}\n\n`);
                    }
                }
            } catch (streamErr) {
                res.write(`data: ${JSON.stringify({ type: 'text', agentId, text: `[Erro: ${streamErr.message}]` })}\n\n`);
            }

            res.write(`data: ${JSON.stringify({ type: 'agent_done', agentId })}\n\n`);
        }

        res.write('data: [DONE]\n\n');
        res.end();
    } catch (err) {
        console.error('Meeting chat error:', err.message);
        if (!res.headersSent) res.status(500).json({ error: err.message });
    }
});

app.listen(PORT, () => {
    console.log(`Squad Server running on http://localhost:${PORT}`);
});
