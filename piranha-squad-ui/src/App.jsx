import { useState } from 'react';
import ProjectDashboard from './components/ProjectDashboard';
import SquadBuilder from './components/SquadBuilder';
import VirtualHQ from './components/VirtualHQ';
import './index.css';

function App() {
  const [view, setView] = useState('dashboard'); // 'dashboard' | 'builder' | 'hq'
  const [activeProject, setActiveProject] = useState(null);
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const token = localStorage.getItem('piranha_token');
      if (!token) return null;
      const payload = JSON.parse(atob(token.split('.')[1]));
      if (payload.exp * 1000 < Date.now()) { localStorage.removeItem('piranha_token'); return null; }
      return payload;
    } catch { return null; }
  });

  const handleLogin = (user) => setCurrentUser(user);

  return (
    <div className="w-screen h-screen bg-gray-950 text-white overflow-hidden">
      {view === 'hq' ? (
        <VirtualHQ currentUser={currentUser} onLogin={handleLogin} onBack={() => setView('dashboard')} />
      ) : view === 'builder' ? (
        <SquadBuilder projectId={activeProject} onBack={() => { setView('dashboard'); setActiveProject(null); }} />
      ) : (
        <ProjectDashboard
          onEnterProject={(id) => { setActiveProject(id); setView('builder'); }}
          onOpenHQ={() => setView('hq')}
        />
      )}
    </div>
  );
}

export default App;
