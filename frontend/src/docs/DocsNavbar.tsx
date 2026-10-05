import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, Menu, X, Terminal, BarChart2, ShieldCheck, ExternalLink } from 'lucide-react';

interface DocsNavbarProps {
  currentSlug: string;
  onOpenSearch: () => void;
  onToggleMobileSidebar: () => void;
  isMobileSidebarOpen: boolean;
}

export const DocsNavbar: React.FC<DocsNavbarProps> = ({
  currentSlug,
  onOpenSearch,
  onToggleMobileSidebar,
  isMobileSidebarOpen,
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const topNavLinks = [
    { label: 'Overview', slug: 'overview' },
    { label: 'Architecture', slug: 'system-design' },
    { label: 'Data Ingestion', slug: 'ingestion-pipeline' },
    { label: 'Offset GIS', slug: 'geospatial-offset-discovery' },
    { label: 'Correlation', slug: 'depth-and-formation-correlation' },
    { label: 'Risk Engine', slug: 'prediction-methodology' },
    { label: 'Formulas', slug: 'algorithms-and-formulas' },
    { label: 'API Reference', slug: 'api-reference' },
  ];

  return (
    <header className="sticky top-0 z-40 w-full border-b border-stone-200 bg-[#f6f5f3]">
      <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 sm:border-x border-stone-200/90 bg-[#fafaf9]/95 backdrop-blur-xs">
        <div className="flex items-center justify-between h-14 sm:h-16 gap-3">
          {/* Mobile sidebar toggle button */}
          <div className="flex items-center gap-3">
            <button
              onClick={onToggleMobileSidebar}
              className="lg:hidden p-1.5 rounded border border-stone-300 bg-white text-stone-700 hover:text-stone-950 hover:bg-stone-100 transition"
              aria-label="Toggle Documentation Navigation Sidebar"
              title="Topics Menu"
            >
              {isMobileSidebarOpen ? <X className="w-5 h-5 text-stone-900" /> : <Menu className="w-5 h-5" />}
            </button>

            {/* Brand Logo & Indicators */}
            <Link to="/" className="flex items-center gap-2.5 text-left group">
              <div className="size-8 bg-stone-900 text-white font-mono font-bold text-xs flex items-center justify-center rounded-xs tracking-tighter shrink-0">
                DW
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold text-stone-950 uppercase tracking-wider group-hover:text-stone-700 transition-colors">
                    DRILLWISE
                  </span>
                  <span className="font-mono text-[9px] bg-stone-200 text-stone-800 px-1.5 py-0.5 rounded uppercase font-semibold">
                    SIH26121
                  </span>
                </div>
                <span className="block font-mono text-[10px] text-stone-500 uppercase tracking-widest leading-none mt-0.5 truncate">
                  OIL INDIA LIMITED · eRTMAC-NWIS
                </span>
              </div>
            </Link>
          </div>

          {/* Center Navigation Links - Desktop */}
          <nav className="hidden xl:flex items-center gap-0.5">
            {topNavLinks.map((link) => {
              const isActive = currentSlug === link.slug;
              return (
                <Link
                  key={link.slug}
                  to={`/docs/${link.slug}`}
                  className={`px-2.5 py-1 rounded font-mono text-[11px] uppercase tracking-wider transition-colors ${
                    isActive
                      ? 'bg-stone-200 text-stone-950 font-bold'
                      : 'text-stone-600 hover:text-stone-900 hover:bg-stone-100'
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>

          {/* Right Action Tools */}
          <div className="flex items-center gap-2 shrink-0">
            {/* Search Trigger */}
            <button
              onClick={onOpenSearch}
              className="flex items-center gap-2 px-2.5 py-1.5 rounded-sm border border-stone-300 bg-white text-stone-600 hover:text-stone-950 hover:border-stone-400 transition-colors text-xs font-mono shadow-2xs"
              title="Search documentation (Cmd+K / Ctrl+K)"
            >
              <Search className="w-3.5 h-3.5 text-stone-500" />
              <span className="hidden sm:inline text-stone-600 font-sans text-xs">Search specs...</span>
              <kbd className="hidden sm:inline font-mono text-[10px] text-stone-400 border border-stone-200 px-1.5 py-0.2 rounded bg-stone-50">
                ⌘K
              </kbd>
            </button>

            {/* Launch Rig Cockpit (/app) */}
            <Link
              to="/app"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-sm bg-stone-900 text-white hover:bg-stone-800 transition text-[11px] font-mono uppercase font-semibold tracking-wider shadow-2xs"
            >
              <Terminal className="w-3.5 h-3.5 text-amber-400" />
              <span className="hidden md:inline">Rig Cockpit</span>
            </Link>

            {/* Validation Benchmarks */}
            <a
              href="/benchmarks"
              className="hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-sm border border-stone-300 bg-white text-stone-700 hover:bg-stone-100 transition text-[11px] font-mono uppercase tracking-wider shadow-2xs"
            >
              <BarChart2 className="w-3.5 h-3.5 text-stone-500" />
              <span>Benchmarks</span>
            </a>

            {/* Problem Statement Link */}
            <Link
              to="/docs/problem-statement"
              className="hidden lg:flex items-center gap-1 px-2.5 py-1.5 rounded-sm border border-stone-200 bg-stone-50 text-stone-700 hover:bg-stone-100 transition text-[11px] font-mono uppercase tracking-wider"
              title="Problem Statement SIH26121"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              <span>PS-121</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="xl:hidden border-t border-stone-200 bg-[#fafaf9] px-4 py-3 space-y-2 text-xs font-mono">
          <div className="grid grid-cols-2 gap-1 pb-2 border-b border-stone-200">
            {topNavLinks.map((link) => (
              <Link
                key={link.slug}
                to={`/docs/${link.slug}`}
                onClick={() => setMobileMenuOpen(false)}
                className="p-2 rounded text-stone-700 hover:bg-stone-100 font-semibold"
              >
                {link.label}
              </Link>
            ))}
          </div>
          <div className="flex gap-2 pt-2">
            <Link
              to="/app"
              onClick={() => setMobileMenuOpen(false)}
              className="flex-1 flex items-center justify-center gap-2 p-2 rounded bg-stone-900 text-white font-semibold"
            >
              <Terminal className="w-4 h-4 text-amber-400" />
              <span>Rig Cockpit</span>
            </Link>
            <a
              href="/benchmarks"
              onClick={() => setMobileMenuOpen(false)}
              className="flex-1 flex items-center justify-center gap-2 p-2 rounded border border-stone-300 bg-white text-stone-800"
            >
              <BarChart2 className="w-4 h-4" />
              <span>Benchmarks</span>
            </a>
          </div>
        </div>
      )}
    </header>
  );
};
