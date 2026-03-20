#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');

const DEFAULT_LAYOUT_NAME = 'layout.json';

// Tile values (from Pixel Agents TileType enum)
const TILE = {
  VOID: 255,
  WALL: 0,
  FLOOR_1: 1,
  FLOOR_2: 2,
  FLOOR_3: 3,
  FLOOR_4: 4,
  FLOOR_5: 5,
  FLOOR_6: 6,
  FLOOR_7: 7,
  FLOOR_8: 8,
  FLOOR_9: 9,
};

function ensureDir(dir) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function loadJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function writeJson(filePath, data) {
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2) + '\n', 'utf8');
}

function uid(prefix, type, col, row) {
  // Stable UID across runs (same type/coords => same uid)
  return `piranha-${prefix}-${type}-${col}-${row}`;
}

function hslColor(h, s, b, c = 0, colorize = false) {
  return { h, s, b, c, colorize };
}

function createEmptyLayout(cols = 21, rows = 22) {
  const tiles = new Array(cols * rows).fill(TILE.VOID);
  const tileColors = new Array(cols * rows).fill(null);

  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const idx = r * cols + c;
      // Outer border is wall
      if (r === 0 || r === rows - 1 || c === 0 || c === cols - 1) {
        tiles[idx] = TILE.WALL;
        tileColors[idx] = null;
        continue;
      }
      // Default floor
      tiles[idx] = TILE.FLOOR_1;
      tileColors[idx] = null;
    }
  }

  return {
    version: 1,
    cols,
    rows,
    layoutRevision: 1,
    tiles,
    tileColors,
    furniture: [],
  };
}

function setTileRegion(layout, col, row, width, height, tileValue, floorColor = null) {
  for (let r = row; r < row + height; r++) {
    for (let c = col; c < col + width; c++) {
      const idx = r * layout.cols + c;
      if (idx < 0 || idx >= layout.tiles.length) continue;
      layout.tiles[idx] = tileValue;
      layout.tileColors[idx] = floorColor;
    }
  }
}

const REPO_ROOT = path.join(__dirname, '..');

function parseAgentLabel(agentFilePath) {
  try {
    const content = fs.readFileSync(agentFilePath, 'utf8');
    const match = content.match(/^#\s*(.+)/m);
    if (match) return match[1].trim();
  } catch {
    // ignore
  }
  return null;
}

function getSquadDefs() {
  return [
    { id: 'leads', folder: 'piranha-leads', label: 'SALES', color: hslColor(0, 35, -20, 0) },
    { id: 'workshops', folder: 'piranha-workshops', label: 'WORKSHOPS', color: hslColor(220, 30, -18, 0) },
    { id: 'comms', folder: 'piranha-comms', label: 'COMMS', color: hslColor(270, 25, -15, 0) },
    { id: 'supplies', folder: 'piranha-supplies', label: 'SUPPLIES', color: hslColor(35, 35, -16, 0) },
    { id: 'studio', folder: 'piranha-studio', label: 'STUDIO', color: hslColor(150, 25, -12, 0) },
  ];
}

function getSquadsWithAgents() {
  const squads = getSquadDefs();
  return squads.map((squad) => {
    const agentsDir = path.join(REPO_ROOT, 'squads', squad.folder, 'agents');
    let files = [];
    try {
      files = fs.readdirSync(agentsDir).filter((f) => f.endsWith('.md')).sort();
    } catch {
      // ignore missing squad folder
    }

    const agents = files.map((file, idx) => {
      const filePath = path.join(agentsDir, file);
      return {
        file,
        filePath,
        name: `${squad.id}-${idx + 1}`,
        label: parseAgentLabel(filePath) || `${squad.label} ${idx + 1}`,
      };
    });

    return { ...squad, agents };
  });
}

function computeLayoutSize(squads) {
  const bandHeight = 4; // each squad uses 4 rows
  const rows = Math.max(22, 2 + squads.length * bandHeight);
  const maxAgents = Math.max(0, ...squads.map((s) => s.agents.length));
  // Each workstation uses 2 columns; add a small buffer
  const cols = Math.max(21, 2 + maxAgents * 2 + 4);
  return { cols, rows };
}

function buildMeetingCorner(originCol, originRow) {
  const items = [];
  items.push({ uid: uid('meeting', 'table', originCol, originRow), type: 'TABLE_FRONT', col: originCol, row: originRow });
  items.push({ uid: uid('meeting', 'chair-top', originCol + 1, originRow - 1), type: 'WOODEN_CHAIR_SIDE', col: originCol + 1, row: originRow - 1 });
  items.push({ uid: uid('meeting', 'chair-bottom', originCol + 1, originRow + 4), type: 'WOODEN_CHAIR_SIDE', col: originCol + 1, row: originRow + 4 });
  items.push({ uid: uid('meeting', 'chair-left', originCol - 1, originRow + 1), type: 'WOODEN_CHAIR_SIDE', col: originCol - 1, row: originRow + 1 });
  items.push({ uid: uid('meeting', 'chair-right', originCol + 3, originRow + 1), type: 'WOODEN_CHAIR_SIDE:left', col: originCol + 3, row: originRow + 1 });
  items.push({ uid: uid('meeting', 'whiteboard', originCol + 4, originRow - 1), type: 'WHITEBOARD', col: originCol + 4, row: originRow - 1 });
  return items;
}

function buildSquadBand(layout, squad, baseRow, seatMap, maxColInclusive = layout.cols - 2) {
  // Each agent gets one desk + PC + chair.
  // We use side-facing desks (1x4 footprint) to pack more workstations in a single band.
  const count = squad.agents.length;
  const interiorWidth = maxColInclusive; // columns 1..maxColInclusive (inclusive)
  const maxWorkstations = Math.floor(interiorWidth / 2);
  const workstations = Math.min(count, maxWorkstations);

  const startCol = 1 + Math.max(0, Math.floor((interiorWidth - workstations * 2) / 2));

  const items = [];
  for (let i = 0; i < workstations; i += 1) {
    const col = startCol + i * 2;
    const row = baseRow;

    const orientationSuffix = i % 2 === 0 ? '' : ':left';
    const deskType = `DESK_SIDE${orientationSuffix}`;
    const pcType = `PC_SIDE${orientationSuffix}`;
    const chairType = `WOODEN_CHAIR_SIDE${orientationSuffix}`;

    const deskUid = uid(squad.id, 'desk', col, row);
    const pcUid = uid(squad.id, 'pc', col, row + 1);
    const chairUid = uid(squad.id, 'chair', col + 1, row + 2);

    items.push({ uid: deskUid, type: deskType, col, row, color: squad.color });
    items.push({ uid: pcUid, type: pcType, col, row: row + 1 });
    items.push({ uid: chairUid, type: chairType, col: col + 1, row: row + 2 });

    seatMap.push({
      squadId: squad.id,
      squadLabel: squad.label,
      deskIndex: i + 1,
      seatId: chairUid,
      seatCol: col + 1,
      seatRow: row + 2,
    });
  }

  if (count > maxWorkstations) {
    console.warn(`Squad ${squad.id} has ${count} agents but only room for ${maxWorkstations} desks in this band.`);
  }

  return items;
}

function buildOfficeLayout(baseLayout, squads, seatMap) {
  const layout = { ...baseLayout };
  const bandHeight = 4; // Each squad occupies a 4-row band (desk + chair fit in 4 rows)
  const furniture = [];

  for (let i = 0; i < squads.length; i += 1) {
    const squad = squads[i];
    const baseRow = 1 + i * bandHeight; // leave row 0 as wall

    setTileRegion(layout, 1, baseRow, layout.cols - 2, bandHeight, TILE.FLOOR_2, squad.color);

    // For the studio band, reserve right side for a meeting corner.
    if (squad.id === 'studio') {
      const meetingStartCol = layout.cols - 1 - 4; // leave 1 column buffer + 3 wide table
      furniture.push(...buildMeetingCorner(meetingStartCol, baseRow));
      furniture.push(...buildSquadBand(layout, squad, baseRow, seatMap, meetingStartCol - 1));
    } else {
      furniture.push(...buildSquadBand(layout, squad, baseRow, seatMap));
    }
  }

  // Shared lobby area (top-left) decor
  furniture.push({ uid: uid('lobby', 'clock', 10, 1), type: 'CLOCK', col: 10, row: 1 });
  furniture.push({ uid: uid('lobby', 'plant', 3, 1), type: 'LARGE_PLANT', col: 3, row: 1 });
  furniture.push({ uid: uid('lobby', 'bookshelf', 16, 1), type: 'DOUBLE_BOOKSHELF', col: 16, row: 1 });
  furniture.push({ uid: uid('lobby', 'painting', 10, 4), type: 'LARGE_PAINTING', col: 10, row: 4 });

  layout.furniture = furniture;
  layout.layoutRevision = (layout.layoutRevision || 1) + 1;
  return layout;
}

function getClaudeProjectDir(workspacePath) {
  // Claude uses a project hash that replaces :, \\, / with -
  return path.join(
    os.homedir(),
    '.claude',
    'projects',
    workspacePath.replace(/[:\\/]/g, '-'),
  );
}

function createSession(workspacePath, sessionId, agentLabel, { seatId } = {}) {
  const projectDir = getClaudeProjectDir(workspacePath);
  ensureDir(projectDir);

  const sessionFile = path.join(projectDir, `${sessionId}.jsonl`);
  const now = new Date().toISOString();
  const lines = [];

  // Metadata record: used by Pixel Agents to assign seats and display a label.
  lines.push(
    JSON.stringify({
      type: 'system',
      subtype: 'agent_metadata',
      label: agentLabel,
      seatId: seatId || null,
      timestamp: now,
    }),
  );

  lines.push(
    JSON.stringify({
      type: 'user',
      message: {
        role: 'user',
        content: `Olá! Sou o agente ${agentLabel} e estou pronto para trabalhar no escritório Piranha.`,
      },
      timestamp: now,
    }),
  );

  lines.push(
    JSON.stringify({
      type: 'assistant',
      message: {
        role: 'assistant',
        content: [
          {
            type: 'text',
            text: `Bem-vindo! Eu sou ${agentLabel}. Use este agente para testar a sala e interagir com ferramentas.`,
          },
        ],
      },
      timestamp: now,
    }),
  );

  lines.push(
    JSON.stringify({
      type: 'system',
      subtype: 'turn_duration',
      timestamp: now,
    }),
  );

  fs.writeFileSync(sessionFile, lines.join('\n') + '\n', 'utf8');
  return sessionFile;
}

function createAgentSessions(workspacePath, squads, seatMap) {
  const sessions = [];
  let seatIndex = 0;
  const now = Date.now();

  for (const squad of squads) {
    for (const agent of squad.agents) {
      const seat = seatMap[seatIndex++] || null;
      const sessionId = `${agent.name}-${now}`;
      const file = createSession(workspacePath, sessionId, agent.label, {
        seatId: seat?.seatId,
      });
      sessions.push({
        squadId: squad.id,
        squadLabel: squad.label,
        agentName: agent.name,
        agentLabel: agent.label,
        sessionId,
        file,
        seatId: seat?.seatId,
        seatCol: seat?.seatCol,
        seatRow: seat?.seatRow,
      });
    }
  }

  return sessions;
}

function formatAgentMap(sessions, layout) {
  const lines = [];
  lines.push(`Office layout: ${layout.cols} cols x ${layout.rows} rows`);
  lines.push('');
  lines.push('Agent seating map (launch sessions in the order shown to keep seat mapping stable):');
  lines.push('');

  for (const s of sessions) {
    const seatDesc = s.seatId ? `seat ${s.seatId} @ (${s.seatCol},${s.seatRow})` : 'no seat assigned';
    lines.push(`- ${s.agentLabel} (${s.agentName}) — ${seatDesc}  → claude --session-id ${s.sessionId}`);
  }

  return lines.join('\n');
}

function main() {
  const home = os.homedir();
  const pixelDir = path.join(home, '.pixel-agents');
  const layoutPath = path.join(pixelDir, DEFAULT_LAYOUT_NAME);
  const backupPath = path.join(pixelDir, `layout.backup-${Date.now()}.json`);

  ensureDir(pixelDir);

  const squads = getSquadsWithAgents();
  const { cols, rows } = computeLayoutSize(squads);
  const baseLayout = createEmptyLayout(cols, rows);

  const seatMap = [];
  const newLayout = buildOfficeLayout(baseLayout, squads, seatMap);

  if (fs.existsSync(layoutPath)) {
    fs.copyFileSync(layoutPath, backupPath);
    console.log(`Backed up existing layout to ${backupPath}`);
  } else {
    console.log('No existing layout.json found; creating a fresh layout based on a blank floor.');
  }

  writeJson(layoutPath, newLayout);
  console.log(`Wrote new layout to ${layoutPath}`);
  console.log('Open VS Code, open the Pixel Agents view, and verify the new office layout.');
  console.log('If you want to revert, restore the backup file from above.');

  const workspace = process.cwd();

  if (process.argv.includes('--demo')) {
    const demoSession = createSession(workspace, `demo-${Date.now()}`, 'Demo Agent');
    console.log(`Created demo Claude session at ${demoSession}`);
    console.log('Open Pixel Agents and it should automatically adopt this new session.');
  }

  if (process.argv.includes('--agents')) {
    const sessions = createAgentSessions(workspace, squads, seatMap);
    if (sessions.length === 0) {
      console.log('No agents found in squads/*/agents. Create agent files in those folders and rerun with --agents.');
    } else {
      console.log(`Created ${sessions.length} agent sessions.`);
      const mapText = formatAgentMap(sessions, newLayout);
      const mapFile = path.join(pixelDir, 'piranha-agent-map.txt');
      fs.writeFileSync(mapFile, mapText + '\n', 'utf8');
      console.log(`Wrote agent seating map to ${mapFile}`);
      console.log('To launch them as agents in Pixel Agents, open the Pixel Agents panel and click + Agent for each session, then run the corresponding command in the new terminal:');
      console.log('');
      console.log(mapText);
    }
  }
}

if (require.main === module) {
  main();
}
