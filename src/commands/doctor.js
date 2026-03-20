'use strict';

const chalk = require('chalk');
const { execSync } = require('child_process');

function check(label, fn) {
  try {
    const result = fn();
    console.log(chalk.green('  OK') + '  ' + label + (result ? chalk.gray(' (' + result + ')') : ''));
    return true;
  } catch (err) {
    console.log(chalk.red('  FALHA') + '  ' + label + chalk.gray(' - ' + err.message));
    return false;
  }
}

async function runDoctor() {
  console.log();
  console.log(chalk.bold.cyan('  aiox-core doctor'));
  console.log(chalk.gray('  Verificando o ambiente...\n'));

  let allOk = true;

  // Node.js
  allOk &= check('Node.js instalado', () => {
    const v = process.version;
    const major = parseInt(v.slice(1));
    if (major < 18) throw new Error('Requer Node.js >= 18, encontrado ' + v);
    return v;
  });

  // npm
  allOk &= check('npm disponivel', () => {
    return execSync('npm --version', { stdio: 'pipe' }).toString().trim();
  });

  // npx
  allOk &= check('npx disponivel', () => {
    return execSync('npx --version', { stdio: 'pipe' }).toString().trim();
  });

  // aiox-core linkado
  allOk &= check('aiox-core linkado globalmente', () => {
    const bin = execSync('which aiox-core', { stdio: 'pipe' }).toString().trim();
    if (!bin) throw new Error('aiox-core nao encontrado no PATH');
    return bin;
  });

  // @anthropic-ai/sdk acessivel no registry
  allOk &= check('@anthropic-ai/sdk acessivel no registry', () => {
    const v = execSync('npm show @anthropic-ai/sdk version', { stdio: 'pipe' }).toString().trim();
    if (!v) throw new Error('Pacote nao encontrado no registry');
    return v;
  });

  // Versao do aiox-core
  allOk &= check('aiox-core versao', () => {
    return require('../../package.json').version;
  });

  console.log();

  if (allOk) {
    console.log(chalk.bold.green('  Tudo certo! O ambiente esta pronto.'));
    console.log(chalk.gray('  Use: npx aiox-core init <nome-do-projeto>\n'));
  } else {
    console.log(chalk.bold.yellow('  Alguns problemas foram encontrados. Verifique os itens acima.\n'));
    process.exit(1);
  }
}

module.exports = { runDoctor };
