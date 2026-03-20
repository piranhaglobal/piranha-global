#!/usr/bin/env node
'use strict';

const { program } = require('commander');
const { version } = require('../package.json');

program
  .name('aiox-core')
  .description('CLI para criar projetos de IA com Claude')
  .version(version);

program
  .command('doctor')
  .description('Verifica se o ambiente esta configurado corretamente')
  .action(async () => {
    const { runDoctor } = require('../src/commands/doctor');
    await runDoctor();
  });

program
  .command('init <project-name>')
  .description('Inicializa um novo projeto de IA')
  .option('-t, --template <template>', 'template a usar (default: agent)', 'agent')
  .option('--skip-install', 'pular instalação de dependências')
  .action(async (projectName, options) => {
    const { runInit } = require('../src/commands/init');
    await runInit(projectName, options);
  });

program.parse(process.argv);
