import React, { useState, useEffect, useRef } from 'react';
import {
  Bot,
  Sparkles,
  Send,
  RotateCcw,
  ShieldCheck,
  AlertTriangle,
  Loader2,
  FileText,
  ChevronDown,
  ChevronUp,
  Database,
  ExternalLink,
  Square,
  CheckCircle2,
  Layers,
  Compass,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';
import { AgentChatMessage, AgentToolCall, AgentMode } from '../types';
import { PdfEvidenceViewer } from '../components/PdfEvidenceViewer';

interface ActivePdfEvidence {
  sourceFilename: string;
  page?: number | null;
  contextLabel?: string;
}

const QUICK_PROMPTS = [
  'What are the top offset wells for our active well at current depth?',
  'Show historical kick and loss incidents in Barail Sandstone',
  'What risk corridors lie ahead of our current bit depth?',
  'What mitigation measures resolved stuck pipe in Tipam Sandstone?',
  'Check active alerts and live hazard status for the active well',
];

export const CopilotPage: React.FC = () => {
  const { activeWellId, activeDepth, wells } = useApp();
  const [messages, setMessages] = useState<AgentChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentToolCalls, setCurrentToolCalls] = useState<AgentToolCall[]>([]);
  const [currentStreamingText, setCurrentStreamingText] = useState('');
  const [activeMode, setActiveMode] = useState<AgentMode>('agentic');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [expandedToolsIndex, setExpandedToolsIndex] = useState<Record<string, boolean>>({});
  const [activePdf, setActivePdf] = useState<ActivePdfEvidence | null>(null);

  const abortControllerRef = useRef<(() => void) | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const activeWell = wells.find((w) => w.well_id === activeWellId);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentStreamingText, currentToolCalls]);

  const toggleToolsExpanded = (msgId: string) => {
    setExpandedToolsIndex((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  const handleSend = (textToSend?: string) => {
    const query = (textToSend || input).trim();
    if (!query || isStreaming) return;

    setErrorMessage(null);
    setInput('');

    const userMessageId = `user-${Date.now()}`;
    const userMsg: AgentChatMessage = {
      id: userMessageId,
      role: 'user',
      content: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsStreaming(true);
    setCurrentToolCalls([]);
    setCurrentStreamingText('');

    const toolCallsCollector: AgentToolCall[] = [];
    let assistantMode: AgentMode = 'agentic';
    let finalText = '';

    const abortFn = api.streamAgentChat(
      {
        message: query,
        active_well_id: activeWellId,
        active_depth: activeDepth,
      },
      (event) => {
        if (event.type === 'mode' && event.mode) {
          assistantMode = event.mode;
          setActiveMode(event.mode);
        } else if (event.type === 'tool_call') {
          const newCall: AgentToolCall = {
            tool: event.tool || 'unknown_tool',
            arguments: event.arguments || {},
          };
          toolCallsCollector.push(newCall);
          setCurrentToolCalls([...toolCallsCollector]);
        } else if (event.type === 'tool_result') {
          // Attach result to the matching tool call
          const target = toolCallsCollector.find(
            (t) => t.tool === event.tool && t.result === undefined
          );
          if (target) {
            target.result = event.result;
          }
          setCurrentToolCalls([...toolCallsCollector]);
        } else if (event.type === 'answer') {
          finalText = event.text || '';
          setCurrentStreamingText(finalText);
        } else if (event.type === 'error') {
          setErrorMessage(event.detail || 'The Knowledge Copilot encountered an error.');
        }
      },
      (err) => {
        console.error('Agent chat stream error:', err);
        setErrorMessage(
          err?.message || 'Failed to connect to the Knowledge Copilot service.'
        );
        setIsStreaming(false);
      },
      () => {
        // Stream completed
        if (finalText || toolCallsCollector.length > 0) {
          // Extract citations from tool results for grounded proofs
          const citations: AgentChatMessage['citations'] = [];
          for (const tc of toolCallsCollector) {
            if (tc.tool === 'search_events' && tc.result?.results) {
              for (const ev of tc.result.results) {
                if (ev.source_document || ev.event_id) {
                  citations.push({
                    well_id: ev.well_id,
                    event_id: ev.event_id,
                    source_document: ev.source_document,
                    source_page: ev.source_page,
                  });
                }
              }
            }
          }

          const assistantMsg: AgentChatMessage = {
            id: `asst-${Date.now()}`,
            role: 'assistant',
            content: finalText || 'No grounded answer was produced for this query.',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            mode: assistantMode,
            toolCalls: [...toolCallsCollector],
            citations: citations.length > 0 ? citations : undefined,
          };
          setMessages((prev) => [...prev, assistantMsg]);
        }
        setIsStreaming(false);
        setCurrentToolCalls([]);
        setCurrentStreamingText('');
      }
    );

    abortControllerRef.current = abortFn;
  };

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
  };

  const handleClear = () => {
    handleStop();
    setMessages([]);
    setErrorMessage(null);
    setCurrentToolCalls([]);
    setCurrentStreamingText('');
  };

  return (
    <div className="p-4 space-y-4 max-w-[1300px] mx-auto flex flex-col h-[calc(100vh-100px)]">
      {/* SCADA Header */}
      <div className="scada-panel p-3 flex flex-wrap items-center justify-between gap-3 border-l-4 border-l-cyan-500 shrink-0">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-cyan-500/10 border border-cyan-500/30 rounded text-cyan-400">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <div className="text-sm font-bold text-slate-100 flex items-center gap-2">
              DRILLING KNOWLEDGE COPILOT
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300">
                Agentic RAG
              </span>
            </div>
            <div className="text-xs text-slate-400 font-mono">
              Tool-calling orchestrator querying real offset-well knowledge, formations, and historical NPT incidents
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap text-xs font-mono">
          {/* Active Context Chip */}
          <div className="px-2.5 py-1 rounded bg-slate-900 border border-slate-700 text-slate-300 flex items-center gap-1.5">
            <Compass className="w-3.5 h-3.5 text-cyan-400" />
            <span>Active:</span>
            <span className="font-bold text-cyan-300">{activeWellId}</span>
            <span className="text-slate-500">@</span>
            <span className="text-amber-300">{activeDepth.toFixed(1)}m MD</span>
          </div>

          {/* Mode Indicator */}
          {activeMode === 'agentic' ? (
            <div className="px-2.5 py-1 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>AI-Assisted (Gemini)</span>
            </div>
          ) : (
            <div className="px-2.5 py-1 rounded bg-amber-500/10 border border-amber-500/30 text-amber-300 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-amber-400" />
              <span>Keyword Search Fallback</span>
            </div>
          )}

          {/* Grounding guarantee */}
          <span className="hidden lg:flex text-[10px] bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 px-2 py-1 rounded items-center gap-1">
            <ShieldCheck className="w-3 h-3 text-cyan-400" /> Zero Hallucination Policy
          </span>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="scada-panel flex-1 p-4 overflow-y-auto space-y-4 border border-slate-800 bg-slate-950/70 rounded-lg">
        {messages.length === 0 && !isStreaming && (
          <div className="h-full flex flex-col justify-center items-center text-center p-6 space-y-4 max-w-2xl mx-auto">
            <div className="w-14 h-14 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
              <Bot className="w-8 h-8" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-100 font-sans">
                Real-Time Offset Well & Historical Intelligence Assistant
              </h3>
              <p className="text-xs text-slate-400 mt-1.5 font-mono leading-relaxed">
                Ask operational questions in natural language. The agent inspects real offset-well distances (DORS),
                formation correlator depths, risk corridors ahead of the bit, and verified daily drilling reports with zero fabrication.
              </p>
            </div>

            <div className="w-full pt-4 space-y-2 text-left">
              <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-semibold flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-cyan-400" /> Recommended Drilling Queries
              </div>
              <div className="grid grid-cols-1 gap-2">
                {QUICK_PROMPTS.map((prompt, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(prompt)}
                    className="p-2.5 text-xs text-left font-mono bg-slate-900/90 hover:bg-slate-850 hover:border-cyan-500/50 border border-slate-800 rounded text-slate-300 transition flex items-center justify-between group"
                  >
                    <span>{prompt}</span>
                    <span className="text-slate-600 group-hover:text-cyan-400 font-mono text-[10px]">
                      Ask &rarr;
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Message History */}
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${
              msg.role === 'user' ? 'items-end' : 'items-start'
            } space-y-1.5`}
          >
            <div className="text-[10px] font-mono text-slate-500 px-1">
              {msg.role === 'user' ? 'Drilling Engineer' : 'Knowledge Copilot'} &bull; {msg.timestamp}
            </div>

            <div
              className={`max-w-[88%] rounded-lg p-3.5 ${
                msg.role === 'user'
                  ? 'bg-cyan-950/40 border border-cyan-800/60 text-slate-100 font-mono text-xs'
                  : 'bg-slate-900/90 border border-slate-800 text-slate-200 text-xs font-sans space-y-3'
              }`}
            >
              {/* Tool Execution Drawer for Assistant messages */}
              {msg.toolCalls && msg.toolCalls.length > 0 && (
                <div className="border border-slate-800 rounded bg-slate-950/60 overflow-hidden font-mono text-[11px]">
                  <button
                    onClick={() => toggleToolsExpanded(msg.id)}
                    className="w-full p-2 flex items-center justify-between text-slate-400 hover:text-slate-200 bg-slate-900/50"
                  >
                    <div className="flex items-center gap-1.5">
                      <Database className="w-3.5 h-3.5 text-cyan-400" />
                      <span>
                        Tool Executions: {msg.toolCalls.map((t) => t.tool).join(', ')} ({msg.toolCalls.length})
                      </span>
                    </div>
                    {expandedToolsIndex[msg.id] ? (
                      <ChevronUp className="w-3.5 h-3.5" />
                    ) : (
                      <ChevronDown className="w-3.5 h-3.5" />
                    )}
                  </button>

                  {expandedToolsIndex[msg.id] && (
                    <div className="p-2 space-y-2 border-t border-slate-800/80 bg-slate-950">
                      {msg.toolCalls.map((tc, tcIdx) => (
                        <div
                          key={tcIdx}
                          className="p-2 rounded bg-slate-900/80 border border-slate-800 space-y-1"
                        >
                          <div className="flex items-center justify-between text-cyan-400 font-bold">
                            <span>{tc.tool}</span>
                            <span className="text-[10px] text-slate-500 font-normal">
                              {tc.result?.data_source ? `source: ${tc.result.data_source}` : 'executed'}
                            </span>
                          </div>
                          <div className="text-slate-400 text-[10px]">
                            Arguments: <span className="text-slate-200">{JSON.stringify(tc.arguments)}</span>
                          </div>
                          {tc.result && (
                            <div className="text-[10px] text-slate-300 max-h-32 overflow-y-auto p-1 bg-slate-950 rounded border border-slate-850">
                              <pre className="whitespace-pre-wrap font-mono text-[9px] text-slate-400">
                                {JSON.stringify(tc.result, null, 2)}
                              </pre>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Formatted Content */}
              <div className="whitespace-pre-wrap leading-relaxed font-sans text-xs">
                {msg.content}
              </div>

              {/* Citations and Provenance Badge */}
              {msg.citations && msg.citations.length > 0 && (
                <div className="pt-2 border-t border-slate-800/80 space-y-1.5 font-mono text-[10px]">
                  <div className="text-slate-400 font-bold uppercase tracking-wider flex items-center gap-1.5">
                    <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                    Verified Citations & Evidence ({msg.citations.length})
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {msg.citations.map((c, cIdx) => (
                      <div
                        key={cIdx}
                        className="px-2 py-1 rounded bg-slate-950 border border-slate-800 flex items-center gap-2 text-slate-300"
                      >
                        <span>
                          {c.well_id} {c.event_id ? `(${c.event_id})` : ''}
                        </span>
                        {c.source_document && (
                          <button
                            onClick={() =>
                              setActivePdf({
                                sourceFilename: c.source_document || '',
                                page: c.source_page ?? 1,
                                contextLabel: `${c.well_id} — ${c.event_id || 'Evidence'}`,
                              })
                            }
                            className="px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 hover:bg-cyan-500/30 flex items-center gap-1 border border-cyan-500/40"
                          >
                            <FileText className="w-2.5 h-2.5" />
                            <span>Proof PDF</span>
                            <ExternalLink className="w-2.5 h-2.5" />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Live Streaming State */}
        {isStreaming && (
          <div className="flex flex-col items-start space-y-1.5">
            <div className="text-[10px] font-mono text-cyan-400 px-1 flex items-center gap-1.5">
              <Loader2 className="w-3 h-3 animate-spin" />
              <span>Analyzing live wellbore context...</span>
            </div>

            <div className="max-w-[88%] rounded-lg p-3.5 bg-slate-900/90 border border-cyan-800/50 text-slate-200 text-xs space-y-3">
              {/* Tool calling in progress */}
              {currentToolCalls.length > 0 && (
                <div className="space-y-1.5 font-mono text-[11px]">
                  <div className="text-slate-400 flex items-center gap-1.5">
                    <Database className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Executing database & correlator queries:</span>
                  </div>
                  <div className="space-y-1">
                    {currentToolCalls.map((tc, idx) => (
                      <div
                        key={idx}
                        className="p-1.5 rounded bg-slate-950/80 border border-slate-800 flex items-center justify-between text-[10px]"
                      >
                        <span className="text-cyan-300 font-bold">{tc.tool}</span>
                        <span className="text-slate-400">
                          {tc.result ? (
                            <span className="text-emerald-400 flex items-center gap-1">
                              <CheckCircle2 className="w-3 h-3" /> Done
                            </span>
                          ) : (
                            <span className="text-amber-400 flex items-center gap-1">
                              <Loader2 className="w-2.5 h-2.5 animate-spin" /> Querying...
                            </span>
                          )}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Streaming partial text */}
              {currentStreamingText && (
                <div className="whitespace-pre-wrap leading-relaxed font-sans text-xs">
                  {currentStreamingText}
                </div>
              )}
            </div>
          </div>
        )}

        {errorMessage && (
          <div className="p-3 bg-rose-950/40 border border-rose-800/60 rounded text-rose-300 text-xs font-mono flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{errorMessage}</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input / Control Bar */}
      <div className="scada-panel p-3 border border-slate-800 bg-slate-900 rounded-lg space-y-2 shrink-0">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            disabled={isStreaming}
            placeholder={`Ask about offset wells, formations, risk corridors, or past incidents for ${activeWellId}...`}
            className="flex-1 bg-slate-950 border border-slate-700 px-3.5 py-2.5 rounded text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono disabled:opacity-50"
          />

          {isStreaming ? (
            <button
              onClick={handleStop}
              className="px-4 py-2.5 bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs font-mono rounded transition flex items-center gap-1.5"
            >
              <Square className="w-3.5 h-3.5" />
              <span>STOP</span>
            </button>
          ) : (
            <button
              onClick={() => handleSend()}
              disabled={!input.trim()}
              className="px-4 py-2.5 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-40 text-slate-950 font-bold text-xs font-mono rounded transition flex items-center gap-1.5"
            >
              <Send className="w-3.5 h-3.5" />
              <span>ASK</span>
            </button>
          )}

          {messages.length > 0 && (
            <button
              onClick={handleClear}
              title="Clear conversation"
              className="p-2.5 border border-slate-700 hover:border-slate-600 text-slate-400 hover:text-slate-200 rounded transition"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          )}
        </div>

        <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 px-1">
          <div className="flex items-center gap-2">
            <span>Context:</span>
            <span className="text-cyan-400 font-bold">{activeWellId}</span>
            <span>({activeWell?.well_name || 'Active Borehole'})</span>
            <span>&bull;</span>
            <span>Bit Depth: {activeDepth.toFixed(1)}m MD</span>
          </div>
          <div className="text-slate-500 hidden sm:block">
            Strict tool-retrieval grounding &bull; Press Enter to send
          </div>
        </div>
      </div>

      {/* PDF Evidence Proof Modal */}
      {activePdf && (
        <PdfEvidenceViewer
          onClose={() => setActivePdf(null)}
          sourceFilename={activePdf.sourceFilename}
          page={activePdf.page ?? 1}
          contextLabel={activePdf.contextLabel}
        />
      )}
    </div>
  );
};
