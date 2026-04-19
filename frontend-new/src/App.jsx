import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { 
  Upload, 
  Send, 
  FileText, 
  ShieldCheck, 
  CheckCircle, 
  Info,
  Loader2,
  ChevronDown,
  AlertCircle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const API_BASE = "http://localhost:8000";

const App = () => {
  const [file, setFile] = useState(null);
  const [docId, setDocId] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [stats, setStat] = useState({ pages: 0, chunks: 0 });
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleFileUpload = async (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;

    setFile(selectedFile);
    setIsUploading(true);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const res = await axios.post(`${API_BASE}/upload`, formData);
      setDocId(res.data.document_id);
      setStat({ pages: "N/A", chunks: res.data.total_chunks });
      setMessages([{ role: 'ai', content: `Success! I've indexed "${selectedFile.name}". You can now ask questions about it.` }]);
    } catch (err) {
      setMessages([{ role: 'ai', content: "Upload failed. Please try a valid PDF or TXT file.", isError: true }]);
    } finally {
      setIsUploading(false);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || !docId) return;

    const userQuery = input.trim();
    setMessages(prev => [...prev, { role: 'user', content: userQuery }]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await axios.post(`${API_BASE}/ask`, {
        document_id: docId,
        question: userQuery
      });

      setMessages(prev => [...prev, { 
        role: 'ai', 
        content: res.data.answer,
        evaluation: res.data.evaluation,
        sources: res.data.sources
      }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'ai', content: "Error: " + (err.response?.data?.detail || "Failed to get answer."), isError: true }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-[#020617] text-slate-200 font-sans overflow-hidden">
      {/* Sidebar / Upload Panel */}
      <div className="w-80 bg-[#0f172a] border-r border-slate-800 p-6 flex flex-col">
        <div className="flex items-center gap-3 mb-10">
          <div className="bg-indigo-500 p-2 rounded-xl shadow-lg shadow-indigo-500/20">
            <FileText size={24} className="text-white" />
          </div>
          <h1 className="text-xl font-bold tracking-tight text-white">DocAuditor AI</h1>
        </div>

        <div className="space-y-6">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-widest">Document Ingestion</div>
          
          <label className={`
            relative border-2 border-dashed rounded-2xl p-8 transition-all cursor-pointer flex flex-col items-center text-center
            ${docId ? 'border-emerald-500/50 bg-emerald-500/5' : 'border-slate-700 hover:border-indigo-500/50 hover:bg-indigo-500/5'}
          `}>
            <input type="file" className="hidden" onChange={handleFileUpload} accept=".pdf,.txt" />
            {isUploading ? (
              <Loader2 className="animate-spin text-indigo-500 mb-2" size={32} />
            ) : docId ? (
              <CheckCircle className="text-emerald-500 mb-2" size={32} />
            ) : (
              <Upload className="text-slate-500 mb-2" size={32} />
            )}
            <span className="text-sm font-medium text-slate-300">
              {docId ? "Document Ready" : isUploading ? "Indexing..." : "Upload PDF/TXT"}
            </span>
            <span className="text-[10px] text-slate-500 mt-1">Max size 10MB</span>
          </label>

          {docId && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
              <div className="text-xs text-slate-500 mb-2">Active Document Stats</div>
              <div className="flex justify-between">
                <span className="text-sm font-bold text-white">{stats.chunks} Chunks</span>
                <span className="text-sm font-medium text-emerald-400 italic text-[10px]">Optimized Vector Store</span>
              </div>
            </motion.div>
          )}
        </div>

        <div className="mt-auto space-y-4">
          <div className="p-4 bg-indigo-500/10 border border-indigo-500/20 rounded-xl">
            <div className="flex items-center gap-2 mb-1">
              <ShieldCheck size={16} className="text-indigo-400" />
              <span className="text-xs font-bold text-indigo-400 uppercase">Trust Engine</span>
            </div>
            <p className="text-[10px] text-slate-400 leading-relaxed">
              Every response is evaluated by a secondary Judge LLM for accuracy and faithfulness.
            </p>
          </div>
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col relative bg-[#020617]">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-10 space-y-8 custom-scrollbar pb-32">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto opacity-40">
              <div className="bg-slate-800 p-4 rounded-full mb-4">
                <Info size={40} className="text-slate-400" />
              </div>
              <h2 className="text-xl font-bold mb-2">Start Auditing</h2>
              <p className="text-sm">Upload a technical document to begin querying with real-time accuracy scoring.</p>
            </div>
          )}
          {messages.map((m, i) => (
            <MessageBubble key={i} message={m} />
          ))}
          {isLoading && (
            <div className="flex gap-4 animate-pulse">
              <div className="w-8 h-8 rounded-lg bg-slate-800 shrink-0" />
              <div className="bg-slate-800 h-10 w-48 rounded-2xl rounded-tl-none" />
            </div>
          )}
          <div ref={scrollRef} />
        </div>

        {/* Input Area */}
        <div className="absolute bottom-0 left-0 right-0 p-8 bg-gradient-to-t from-[#020617] via-[#020617] to-transparent">
          <div className="max-w-4xl mx-auto relative group">
            <input 
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSend()}
              disabled={!docId || isLoading}
              placeholder={docId ? "Ask about the document content..." : "Upload a document first to chat..."}
              className="w-full bg-[#1e293b] border border-slate-700 focus:border-indigo-500/50 focus:ring-4 focus:ring-indigo-500/10 rounded-2xl py-4 px-6 pr-14 text-slate-100 outline-none transition-all shadow-2xl disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <button 
              onClick={handleSend}
              disabled={isLoading || !input.trim() || !docId}
              className="absolute right-3 top-1/2 -translate-y-1/2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-600 text-white p-2.5 rounded-xl transition-all shadow-lg"
            >
              {isLoading ? <Loader2 className="animate-spin" size={20} /> : <Send size={20} />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

const MessageBubble = ({ message }) => {
  const isAI = message.role === 'ai';
  const evalData = message.evaluation;

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={`flex gap-4 ${!isAI ? 'flex-row-reverse' : ''}`}>
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 shadow-lg ${
        isAI ? 'bg-indigo-600 text-white font-bold' : 'bg-slate-800 text-slate-400 border border-slate-700'
      }`}>
        {isAI ? 'AI' : <Upload size={18} />}
      </div>
      
      <div className={`space-y-3 max-w-[85%] ${!isAI ? 'text-right' : ''}`}>
        <div className={`p-5 rounded-2xl shadow-xl leading-relaxed text-[15px] ${
          isAI 
            ? 'bg-[#1e293b] border border-slate-700 rounded-tl-none text-slate-200' 
            : 'bg-indigo-600 text-white rounded-tr-none'
        }`}>
          {message.content}
        </div>

        {isAI && evalData && (
          <div className="grid grid-cols-2 gap-3 animate-in fade-in duration-700">
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-3">
              <div className="flex justify-between items-center mb-1">
                <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Faithfulness</span>
                <span className={`text-xs font-bold ${evalData.faithfulness > 80 ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {evalData.faithfulness}%
                </span>
              </div>
              <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                <motion.div 
                  initial={{ width: 0 }} 
                  animate={{ width: `${evalData.faithfulness}%` }} 
                  className={`h-full ${evalData.faithfulness > 80 ? 'bg-emerald-500' : 'bg-amber-500'}`} 
                />
              </div>
            </div>
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-3">
              <div className="flex justify-between items-center mb-1">
                <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Relevancy</span>
                <span className={`text-xs font-bold ${evalData.relevancy > 80 ? 'text-indigo-400' : 'text-amber-400'}`}>
                  {evalData.relevancy}%
                </span>
              </div>
              <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                <motion.div 
                  initial={{ width: 0 }} 
                  animate={{ width: `${evalData.relevancy}%` }} 
                  className={`h-full ${evalData.relevancy > 80 ? 'bg-indigo-500' : 'bg-amber-500'}`} 
                />
              </div>
            </div>
            {evalData.reasoning && (
              <div className="col-span-2 p-3 bg-indigo-500/5 border border-indigo-500/10 rounded-xl">
                <div className="flex items-center gap-2 text-[10px] font-bold text-indigo-400 uppercase mb-1">
                  <ShieldCheck size={12} />
                  Judge Reasoning
                </div>
                <p className="text-[11px] text-slate-400 italic">"{evalData.reasoning}"</p>
              </div>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
};

export default App;
