import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, X, FileText, ChevronRight, CornerDownLeft, Sparkles } from 'lucide-react';
import { searchDocs, ALL_DOCS, type DocItem } from './docsRegistry';

interface DocsSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const DocsSearchModal: React.FC<DocsSearchModalProps> = ({ isOpen, onClose }) => {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const results = query.trim()
    ? searchDocs(query).slice(0, 8)
    : ALL_DOCS.slice(0, 6).map((doc) => ({
        doc,
        matchSnippet: doc.description,
      }));

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev < results.length - 1 ? prev + 1 : 0));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : results.length - 1));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (results[selectedIndex]) {
          handleSelect(results[selectedIndex].doc);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, results, selectedIndex]);

  const handleSelect = (doc: DocItem) => {
    navigate(`/docs/${doc.slug}`);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-16 sm:pt-24 px-4 bg-stone-900/40 backdrop-blur-xs animate-in fade-in duration-150">
      <div
        className="w-full max-w-2xl bg-white border border-stone-300 rounded-lg shadow-2xl overflow-hidden flex flex-col max-h-[80vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input Bar */}
        <div className="flex items-center px-4 py-3.5 border-b border-stone-200 bg-[#fafaf9] gap-3">
          <Search className="w-4 h-4 text-stone-500 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search all 23 engineering specifications, formulas, and APIs..."
            className="flex-1 bg-transparent text-stone-900 placeholder-stone-400 text-sm md:text-base outline-none font-sans"
          />
          {query && (
            <button
              onClick={() => setQuery('')}
              className="p-1 text-stone-400 hover:text-stone-700 transition rounded"
            >
              <X className="w-4 h-4" />
            </button>
          )}
          <span className="hidden sm:inline-block text-[12px] font-mono px-1.5 py-0.5 rounded bg-stone-100 text-stone-500 border border-stone-300">
            ESC
          </span>
        </div>

        {/* Results Container */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {results.length === 0 ? (
            <div className="p-8 text-center text-stone-500 font-mono text-sm">
              No matching specifications found for &quot;<span className="text-stone-900 font-semibold">{query}</span>&quot;
            </div>
          ) : (
            results.map((item, idx) => {
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={item.doc.id}
                  onClick={() => handleSelect(item.doc)}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`group flex items-start gap-3 p-3 rounded-sm cursor-pointer transition ${
                    isSelected
                      ? 'bg-stone-100 border border-stone-300 text-stone-950 shadow-2xs'
                      : 'hover:bg-stone-50 border border-transparent text-stone-700'
                  }`}
                >
                  <div
                    className={`mt-0.5 p-2 rounded-sm shrink-0 ${
                      isSelected
                        ? 'bg-stone-900 text-white'
                        : 'bg-stone-100 text-stone-500 group-hover:text-stone-800'
                    }`}
                  >
                    <FileText className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[12px] font-mono uppercase tracking-wider text-stone-500 font-bold">
                        {item.doc.category}
                      </span>
                      {item.doc.badge && (
                        <span className="text-[11px] font-mono px-1.5 py-0.2 rounded bg-stone-100 text-stone-700 border border-stone-200">
                          {item.doc.badge}
                        </span>
                      )}
                    </div>
                    <div className="text-sm font-semibold text-stone-900 group-hover:text-stone-950 truncate">
                      {item.doc.title}
                    </div>
                    <div className="text-xs text-stone-600 line-clamp-2 mt-0.5 font-sans leading-relaxed">
                      {item.matchSnippet}
                    </div>
                  </div>
                  <ChevronRight
                    className={`w-4 h-4 self-center shrink-0 transition ${
                      isSelected ? 'text-stone-900 translate-x-0.5' : 'text-stone-400'
                    }`}
                  />
                </div>
              );
            })
          )}
        </div>

        {/* Footer Shortcut Bar */}
        <div className="px-4 py-2.5 border-t border-stone-200 bg-[#f5f5f4] flex items-center justify-between text-[13px] font-mono text-stone-500">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <kbd className="px-1 py-0.5 rounded bg-white text-stone-700 border border-stone-300">↑</kbd>
              <kbd className="px-1 py-0.5 rounded bg-white text-stone-700 border border-stone-300">↓</kbd> Navigate
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 rounded bg-white text-stone-700 border border-stone-300 flex items-center">
                <CornerDownLeft className="w-3 h-3 inline" />
              </kbd>{' '}
              Open
            </span>
          </div>
          <div className="flex items-center gap-1.5 text-stone-600">
            <Sparkles className="w-3 h-3 text-[#c96a12]" />
            <span>Team Midnight Ciphers</span>
          </div>
        </div>
      </div>
    </div>
  );
};
