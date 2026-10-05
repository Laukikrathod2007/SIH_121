import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Menu, X, BarChart2 } from 'lucide-react';

interface DocsNavbarProps {
  currentSlug: string;
  onToggleMobileSidebar: () => void;
  isMobileSidebarOpen: boolean;
}

export const DocsNavbar: React.FC<DocsNavbarProps> = ({
  currentSlug,
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
        <div className="flex items-center justify-between h-16 sm:h-[4.5rem] gap-3">
          {/* Mobile sidebar toggle button */}
          <div className="flex items-center gap-3">
            <button
              onClick={onToggleMobileSidebar}
              className="lg:hidden p-1.5 rounded-full border border-stone-300 bg-white text-stone-700 hover:text-stone-950 hover:bg-stone-100 transition"
              aria-label="Toggle Documentation Navigation Sidebar"
              title="Topics Menu"
            >
              {isMobileSidebarOpen ? <X className="w-5 h-5 text-stone-900" /> : <Menu className="w-5 h-5" />}
            </button>

            {/* Brand Logo & Indicators */}
            <Link to="/" className="flex items-center gap-3 text-left group">
              <img
                src="/brand/drillwise-icon-mark.png"
                alt="DrillWise"
                className="size-9 object-contain shrink-0"
              />
              <div className="min-w-0 hidden sm:block">
                <div className="flex items-center gap-2">
                  <span className="font-sans text-[15px] font-semibold text-stone-950 tracking-tight group-hover:text-stone-700 transition-colors">
                    DrillWise
                  </span>
                  <span className="font-mono text-[12px] bg-stone-100 text-stone-500 border border-stone-200 px-1.5 py-0.5 rounded-full tracking-wide">
                    SIH26121
                  </span>
                </div>
                <span className="block font-mono text-[12px] text-stone-400 tracking-wide leading-none mt-1 truncate">
                  Oil India Limited · eRTMAC-NWIS
                </span>
              </div>
            </Link>
          </div>

          {/* Center Navigation Links - Desktop */}
          <nav className="hidden xl:flex items-center gap-0.5 bg-stone-100/70 rounded-full p-1">
            {topNavLinks.map((link) => {
              const isActive = currentSlug === link.slug;
              return (
                <Link
                  key={link.slug}
                  to={`/docs/${link.slug}`}
                  className={`px-3 py-1.5 rounded-full font-mono text-[13px] tracking-wide transition-colors ${
                    isActive
                      ? 'bg-white text-stone-950 font-semibold shadow-2xs'
                      : 'text-stone-500 hover:text-stone-900'
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>

          {/* Right Action Tools */}
          <div className="flex items-center gap-2 shrink-0">
            {/* Validation Benchmarks */}
            <a
              href="/benchmarks"
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-stone-300 bg-white text-stone-700 hover:text-stone-950 hover:border-stone-400 transition-colors text-[13px] font-mono uppercase tracking-wider shadow-2xs"
            >
              <BarChart2 className="w-3.5 h-3.5 text-stone-500" />
              <span>Benchmarks</span>
            </a>

            {/* Mobile overflow toggle */}
            <button
              onClick={() => setMobileMenuOpen((v) => !v)}
              className="sm:hidden p-1.5 rounded-full border border-stone-300 bg-white text-stone-700 hover:text-stone-950 hover:bg-stone-100 transition"
              aria-label="Toggle documentation links"
            >
              {mobileMenuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
            </button>
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
          <a
            href="/benchmarks"
            onClick={() => setMobileMenuOpen(false)}
            className="flex items-center justify-center gap-2 p-2 rounded border border-stone-300 bg-white text-stone-800"
          >
            <BarChart2 className="w-4 h-4" />
            <span>Benchmarks</span>
          </a>
        </div>
      )}
    </header>
  );
};
