import { memo } from 'react';
import { Handle, Position } from 'reactflow';
import { Bot, User, CheckCircle2, Cpu } from 'lucide-react';

export default memo(({ data, isConnectable }) => {
  const Icon = data.type === 'human' ? User : Bot;
  const isQA = data.role === 'qa';

  return (
    <div className="px-5 py-4 shadow-2xl rounded-xl bg-gray-800/90 border border-gray-700/50 backdrop-blur-sm min-w-[220px] max-w-[250px] hover:border-blue-500/50 hover:shadow-blue-900/20 transition-all cursor-pointer">
      <Handle type="target" position={Position.Top} isConnectable={isConnectable} className="w-3 h-3 bg-blue-500 border-2 border-gray-900" />
      
      <div className="flex items-center gap-4">
        <div className={`p-2.5 rounded-lg shadow-inner ${data.type === 'human' ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30' : 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'}`}>
          {isQA ? <CheckCircle2 size={20} className="text-green-400" /> : <Icon size={20} />}
        </div>
        <div className="overflow-hidden">
          <div className="font-bold text-gray-100 text-sm truncate">{data.label}</div>
          <div className="text-[11px] text-gray-400 font-mono mt-0.5 flex items-center gap-1">
            <Cpu size={12} className="text-gray-500 flex-shrink-0" /> <span className="truncate">{data.model || 'Agent'}</span>
          </div>
        </div>
      </div>
      
      <div className="mt-3 text-xs leading-relaxed text-gray-400 line-clamp-2">{data.description}</div>
      
      <Handle type="source" position={Position.Bottom} isConnectable={isConnectable} className="w-3 h-3 bg-blue-500 border-2 border-gray-900" />
    </div>
  );
});
