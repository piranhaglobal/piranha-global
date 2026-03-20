'use strict';

const path = require('path');
const fs = require('fs-extra');
const chalk = require('chalk');
const ora = require('ora');
const { execSync } = require('child_process');

async function runInit(projectName, options) {
  const targetDir = path.resolve(process.cwd(), projectName);

  console.log();
  console.log(chalk.bold.cyan('  aiox-core') + chalk.gray(' v' + require('../../package.json').version));
  console.log(chalk.gray('  Inicializando projeto: ') + chalk.white.bold(projectName));
  console.log();

  // Verifica se o diretório já existe
  if (fs.existsSync(targetDir)) {
    console.log(chalk.red(`  Erro: o diretório "${projectName}" já existe.`));
    process.exit(1);
  }

  const spinner = ora({ text: 'Criando estrutura do projeto...', color: 'cyan' }).start();

  try {
    // Cria estrutura de diretórios
    await fs.ensureDir(path.join(targetDir, 'src', 'agent'));
    await fs.ensureDir(path.join(targetDir, 'src', 'tools'));
    await fs.ensureDir(path.join(targetDir, 'src', 'prompts'));
    await fs.ensureDir(path.join(targetDir, 'src', 'config'));
    await fs.ensureDir(path.join(targetDir, 'tests'));

    spinner.text = 'Gerando arquivos do projeto...';

    // package.json do projeto gerado
    await fs.writeJSON(
      path.join(targetDir, 'package.json'),
      {
        name: projectName,
        version: '0.1.0',
        description: `Projeto de IA gerado pelo aiox-core`,
        main: 'src/index.js',
        type: 'commonjs',
        scripts: {
          start: 'node src/index.js',
          dev: 'node --watch src/index.js',
          test: 'node tests/index.test.js',
        },
        dependencies: {
          '@anthropic-ai/sdk': '^0.39.0',
          'dotenv': '^16.4.5',
        },
        devDependencies: {
          'nodemon': '^3.1.0',
        },
      },
      { spaces: 2 }
    );

    // .env.example
    await fs.writeFile(
      path.join(targetDir, '.env.example'),
      [
        '# ===================================',
        `# ${projectName.toUpperCase()} — Configurações`,
        '# ===================================',
        '',
        '# ANTHROPIC (obrigatório)',
        'ANTHROPIC_API_KEY=sk-ant-COLOQUE_SUA_CHAVE_AQUI',
        '',
        '# SHOPIFY (preencher quando tiver)',
        'SHOPIFY_STORE_URL=sua-loja.myshopify.com',
        'SHOPIFY_ACCESS_TOKEN=shpat_COLOQUE_AQUI',
        'SHOPIFY_API_VERSION=2024-10',
        '',
        '# EVOLUTION API (preencher quando tiver)',
        'EVOLUTION_API_URL=https://sua-evolution.dominio.com',
        'EVOLUTION_API_KEY=COLOQUE_AQUI',
        'EVOLUTION_INSTANCE=piranha-instance',
        '',
        '# ULTRAVOX (preencher quando tiver)',
        'ULTRAVOX_API_KEY=COLOQUE_AQUI',
        '',
        '# CARTESIA (preencher quando tiver)',
        'CARTESIA_API_KEY=COLOQUE_AQUI',
        '',
        '# TELNYX (preencher quando tiver)',
        'TELNYX_API_KEY=KEY_COLOQUE_AQUI',
        'TELNYX_CONNECTION_ID=COLOQUE_AQUI',
        '',
        '# AMBIENTE',
        'NODE_ENV=development',
        'AIOX_DEBUG=false',
      ].join('\n') + '\n'
    );

    // .env (cópia do .env.example)
    await fs.copy(
      path.join(targetDir, '.env.example'),
      path.join(targetDir, '.env')
    );

    // .gitignore
    await fs.writeFile(
      path.join(targetDir, '.gitignore'),
      [
        'node_modules/',
        '.env',
        '.DS_Store',
        '*.log',
        'dist/',
        '.cache/',
      ].join('\n') + '\n'
    );

    // src/config/index.js
    await fs.writeFile(
      path.join(targetDir, 'src', 'config', 'index.js'),
      `'use strict';

require('dotenv').config();

module.exports = {
  anthropicApiKey: process.env.ANTHROPIC_API_KEY,
  model: process.env.CLAUDE_MODEL || 'claude-sonnet-4-6',
  maxTokens: parseInt(process.env.AGENT_MAX_TOKENS || '8192', 10),
};
`
    );

    // src/tools/index.js
    await fs.writeFile(
      path.join(targetDir, 'src', 'tools', 'index.js'),
      `'use strict';

/**
 * Ferramentas disponíveis para o agente.
 * Adicione novas ferramentas aqui seguindo o schema de tool_use do Claude.
 */
const tools = [
  {
    name: 'get_current_time',
    description: 'Retorna a data e hora atual do sistema.',
    input_schema: {
      type: 'object',
      properties: {},
      required: [],
    },
  },
];

/**
 * Executa uma ferramenta pelo nome.
 * @param {string} name - Nome da ferramenta
 * @param {object} input - Parâmetros de entrada
 * @returns {Promise<string>} Resultado da ferramenta
 */
async function executeTool(name, input) {
  switch (name) {
    case 'get_current_time':
      return new Date().toISOString();

    default:
      throw new Error(\`Ferramenta desconhecida: \${name}\`);
  }
}

module.exports = { tools, executeTool };
`
    );

    // src/prompts/system.js
    await fs.writeFile(
      path.join(targetDir, 'src', 'prompts', 'system.js'),
      `'use strict';

const SYSTEM_PROMPT = \`Você é um assistente de IA poderoso e prestativo chamado ${projectName}.

Você tem acesso a ferramentas que pode usar para ajudar os usuários.
Sempre seja preciso, direto e útil.

Responda sempre em português do Brasil, a menos que o usuário escreva em outro idioma.\`;

module.exports = { SYSTEM_PROMPT };
`
    );

    // src/agent/index.js
    await fs.writeFile(
      path.join(targetDir, 'src', 'agent', 'index.js'),
      `'use strict';

const Anthropic = require('@anthropic-ai/sdk');
const { tools, executeTool } = require('../tools');
const { SYSTEM_PROMPT } = require('../prompts/system');
const config = require('../config');

const client = new Anthropic({ apiKey: config.anthropicApiKey });

/**
 * Executa o agente com uma mensagem do usuário.
 * Lida automaticamente com tool_use em loop.
 * @param {string} userMessage - Mensagem do usuário
 * @param {Array} conversationHistory - Histórico da conversa
 * @returns {Promise<{response: string, history: Array}>}
 */
async function runAgent(userMessage, conversationHistory = []) {
  const messages = [
    ...conversationHistory,
    { role: 'user', content: userMessage },
  ];

  let finalResponse = '';

  while (true) {
    const response = await client.messages.create({
      model: config.model,
      max_tokens: config.maxTokens,
      system: SYSTEM_PROMPT,
      tools,
      messages,
    });

    messages.push({ role: 'assistant', content: response.content });

    if (response.stop_reason === 'end_turn') {
      const textBlock = response.content.find((b) => b.type === 'text');
      finalResponse = textBlock ? textBlock.text : '';
      break;
    }

    if (response.stop_reason === 'tool_use') {
      const toolResults = [];

      for (const block of response.content) {
        if (block.type !== 'tool_use') continue;

        let result;
        try {
          result = await executeTool(block.name, block.input);
        } catch (err) {
          result = \`Erro ao executar ferramenta: \${err.message}\`;
        }

        toolResults.push({
          type: 'tool_result',
          tool_use_id: block.id,
          content: String(result),
        });
      }

      messages.push({ role: 'user', content: toolResults });
    } else {
      // stop_reason inesperado
      const textBlock = response.content.find((b) => b.type === 'text');
      finalResponse = textBlock ? textBlock.text : '';
      break;
    }
  }

  return { response: finalResponse, history: messages };
}

module.exports = { runAgent };
`
    );

    // src/index.js (entry point interativo)
    await fs.writeFile(
      path.join(targetDir, 'src', 'index.js'),
      `'use strict';

const readline = require('readline');
const { runAgent } = require('./agent');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

const conversationHistory = [];

function prompt(question) {
  return new Promise((resolve) => rl.question(question, resolve));
}

async function main() {
  console.log('\\n=== ${projectName} ===');
  console.log('Digite "sair" para encerrar.\\n');

  while (true) {
    const userInput = await prompt('Voce: ');

    if (!userInput.trim()) continue;
    if (userInput.toLowerCase() === 'sair') {
      console.log('\\nAte logo!');
      rl.close();
      break;
    }

    try {
      const { response, history } = await runAgent(userInput, conversationHistory);
      conversationHistory.length = 0;
      conversationHistory.push(...history);
      console.log(\`\\nAssistente: \${response}\\n\`);
    } catch (err) {
      console.error('\\nErro:', err.message);
      if (err.message.includes('ANTHROPIC_API_KEY')) {
        console.error('Dica: copie .env.example para .env e adicione sua chave da API.\\n');
      }
    }
  }
}

main().catch(console.error);
`
    );

    // tests/index.test.js
    await fs.writeFile(
      path.join(targetDir, 'tests', 'index.test.js'),
      `'use strict';

const { executeTool } = require('../src/tools');

async function runTests() {
  console.log('Executando testes basicos...\\n');
  let passed = 0;
  let failed = 0;

  async function test(name, fn) {
    try {
      await fn();
      console.log(\`  PASSOU: \${name}\`);
      passed++;
    } catch (err) {
      console.log(\`  FALHOU: \${name} - \${err.message}\`);
      failed++;
    }
  }

  await test('get_current_time retorna uma string ISO', async () => {
    const result = await executeTool('get_current_time', {});
    if (typeof result !== 'string') throw new Error('Esperava uma string');
    if (isNaN(Date.parse(result))) throw new Error('Data invalida');
  });

  await test('ferramenta desconhecida lanca erro', async () => {
    try {
      await executeTool('nao_existe', {});
      throw new Error('Deveria ter lancado um erro');
    } catch (err) {
      if (!err.message.includes('desconhecida')) throw err;
    }
  });

  console.log(\`\\nResultado: \${passed} passaram, \${failed} falharam.\`);
  process.exit(failed > 0 ? 1 : 0);
}

runTests().catch((err) => {
  console.error(err);
  process.exit(1);
});
`
    );

    spinner.text = 'Instalando dependências...';

    if (!options.skipInstall) {
      try {
        execSync('npm install', { cwd: targetDir, stdio: 'pipe' });
        spinner.succeed(chalk.green('Projeto criado com sucesso!'));
      } catch {
        spinner.warn(chalk.yellow('Projeto criado, mas a instalação de dependências falhou.'));
        console.log(chalk.gray('  Execute manualmente: cd ' + projectName + ' && npm install'));
      }
    } else {
      spinner.succeed(chalk.green('Projeto criado com sucesso!'));
    }

    // Instruções finais
    console.log();
    console.log(chalk.bold('  Proximos passos:'));
    console.log();
    console.log(chalk.cyan('  cd ' + projectName));
    console.log(chalk.cyan('  cp .env.example .env'));
    console.log(chalk.gray('  # Edite .env e adicione sua ANTHROPIC_API_KEY'));
    console.log(chalk.cyan('  npm start'));
    console.log();
    console.log(chalk.gray('  Documentacao: https://docs.anthropic.com'));
    console.log();
  } catch (err) {
    spinner.fail(chalk.red('Falha ao criar o projeto.'));
    console.error(chalk.red(err.message));
    // Limpa diretório parcialmente criado
    await fs.remove(targetDir).catch(() => {});
    process.exit(1);
  }
}

module.exports = { runInit };
