import React, { useState } from 'react';
import { NavLink, Link } from 'react-router-dom';
import {
  Compass,
  Cpu,
  FileText,
  Layers,
  ShieldAlert,
  Terminal,
  Code2,
  BookOpen,
  ChevronDown,
  ChevronRight,
  Search,
  CheckCircle2,
  Users,
  X,
  BarChart2,
} from 'lucide-react';
import { DOCS_CATEGORIES, type DocCategory } from './docsRegistry';

interface DocsSidebarProps {
  currentSlug: string;
  onSelectDoc?: () => void;
}

const CATEGORY_ICONS: Record<string, React.ElementType> = {
  Compass,
  Cpu,
  FileText,
  Layers,
  ShieldAlert,
  Terminal,
  Code2,
  BookOpen,
};

export const DocsSidebar: React.FC<DocsSidebarProps> = ({ currentSlug, onSelectDoc }) => {
  const [filterText, setFilterText] = useState('');
  const [collapsedCategories, setCollapsedCategories] = useState<Record<string, boolean>>({});

  const toggleCategory = (catName: string) => {
    setCollapsedCategories((prev) => ({
      ...prev,
      [catName]: !prev[catName],
    }));
  };

  const filteredCategories: DocCategory[] = DOCS_CATEGORIES.map((cat) => {
    const matchingItems = cat.items.filter((item) => {
      const match =
        !filterText.trim() ||
        item.title.toLowerCase().includes(filterText.toLowerCase()) ||
        item.description.toLowerCase().includes(filterText.toLowerCase()) ||
        cat.name.toLowerCase().includes(filterText.toLowerCase());
      return match;
    });

    return {
      ...cat,
      items: matchingItems,
    };
  }).filter((cat) => cat.items.length > 0);

  return (
    <aside className="w-full lg:w-72 xl:w-80 shrink-0 h-full flex flex-col bg-[#fafaf9] border-r border-stone-200 select-none">
      {/* Mobile Drawer Header with Close Button */}
      {onSelectDoc && (
        <div className="flex items-center justify-between p-3 border-b border-stone-200 bg-[#f5f5f4]">
          <div className="flex items-center gap-2">
            <div className="size-6 bg-stone-900 text-white font-mono font-bold text-[10px] flex items-center justify-center rounded-xs">
              DW
            </div>
            <div>
              <span className="font-mono text-xs font-bold text-stone-900 uppercase tracking-wider block leading-tight">
                DRILLWISE DOCS
              </span>
              <span className="font-mono text-[9px] text-stone-500 uppercase tracking-widest block">
                SIH26121 · OIL INDIA
              </span>
            </div>
          </div>
          <button
            onClick={onSelectDoc}
            className="p-1.5 rounded-sm hover:bg-stone-200 text-stone-600 hover:text-stone-950 transition border border-stone-300 bg-white"
            aria-label="Close navigation drawer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Mobile Quick Rig Navigation */}
      {onSelectDoc && (
        <div className="grid grid-cols-2 gap-2 p-2.5 border-b border-stone-200 bg-white">
          <Link
            to="/app"
            onClick={onSelectDoc}
            className="flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-sm bg-stone-900 text-white font-mono text-[11px] font-semibold tracking-wider uppercase shadow-2xs hover:bg-stone-800 transition"
          >
            <Terminal className="w-3.5 h-3.5 text-amber-400" />
            <span>Rig Cockpit</span>
          </Link>
          <a
            href="/benchmarks"
            className="flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-sm border border-stone-300 bg-stone-50 hover:bg-stone-100 text-stone-800 font-mono text-[11px] font-semibold tracking-wider uppercase transition shadow-2xs"
          >
            <BarChart2 className="w-3.5 h-3.5 text-stone-500" />
            <span>Benchmarks</span>
          </a>
        </div>
      )}

      {/* Search Filter Header */}
      <div className="p-3 border-b border-stone-200 bg-[#f5f5f4]">
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-stone-400" />
          <input
            type="text"
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            placeholder="Filter specifications..."
            className="w-full pl-8 pr-3 py-1.5 rounded-sm bg-white border border-stone-300 focus:border-stone-500 text-xs text-stone-800 placeholder-stone-400 outline-none font-mono transition shadow-2xs"
          />
        </div>
      </div>

      {/* Nav Categories List */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-5 scrollbar-thin scrollbar-thumb-stone-300">
        {filteredCategories.map((category) => {
          const Icon = CATEGORY_ICONS[category.iconName] || FileText;
          const isCollapsed = !!collapsedCategories[category.name] && !filterText.trim();

          return (
            <div key={category.name} className="space-y-1">
              {/* Category Header */}
              <button
                onClick={() => toggleCategory(category.name)}
                className="w-full flex items-center justify-between px-2 py-1 rounded text-[11px] font-mono uppercase tracking-wider text-stone-500 hover:text-stone-900 transition font-bold group"
              >
                <div className="flex items-center gap-2 truncate">
                  <Icon className="w-3.5 h-3.5 text-stone-700 group-hover:text-stone-950 transition" />
                  <span className="truncate">{category.name}</span>
                </div>
                <div className="flex items-center gap-1.5 text-stone-400">
                  <span className="text-[10px] font-mono">{category.items.length}</span>
                  {isCollapsed ? (
                    <ChevronRight className="w-3 h-3 text-stone-400" />
                  ) : (
                    <ChevronDown className="w-3 h-3 text-stone-400" />
                  )}
                </div>
              </button>

              {/* Category Items */}
              {!isCollapsed && (
                <div className="space-y-0.5 pt-1 pl-1 border-l border-stone-200 ml-2.5">
                  {category.items.map((item) => {
                    const isActive =
                      currentSlug.toLowerCase() === item.slug.toLowerCase() ||
                      (currentSlug === '' && item.slug === 'overview');

                    return (
                      <NavLink
                        key={item.id}
                        to={`/docs/${item.slug}`}
                        onClick={onSelectDoc}
                        className={`group relative flex items-center justify-between px-2.5 py-1.5 rounded-r-sm text-xs transition-all ${
                          isActive
                            ? 'bg-stone-200/90 text-stone-950 font-bold border-l-2 border-stone-900 -ml-[1px] shadow-2xs'
                            : 'text-stone-600 hover:text-stone-950 hover:bg-stone-100'
                        }`}
                      >
                        <span className="truncate pr-2">{item.title}</span>
                        <div className="flex items-center gap-1 shrink-0">
                          {item.badge && (
                            <span
                              className={`text-[9px] font-mono px-1.5 py-0.2 rounded uppercase ${
                                isActive
                                  ? 'bg-stone-900 text-white font-semibold'
                                  : 'bg-stone-200/80 text-stone-600 group-hover:text-stone-800'
                              }`}
                            >
                              {item.badge}
                            </span>
                          )}
                        </div>
                      </NavLink>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer Info Box */}
      <div className="p-3 border-t border-stone-200 bg-[#f5f5f4] text-[11px] font-mono text-stone-600 space-y-1">
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-1.5 font-semibold text-stone-800">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            <span>23 Core Specifications</span>
          </span>
          <span className="text-[10px] bg-stone-200 text-stone-700 px-1 py-0.2 rounded font-semibold uppercase">
            SIH 2026
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-[10px] text-stone-500 pt-0.5">
          <Users className="w-3 h-3 text-stone-400" />
          <span>Team: Midnight Ciphers</span>
        </div>
      </div>
    </aside>
  );
};
