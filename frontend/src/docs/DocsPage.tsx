import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ChevronRight,
  Clock,
  ArrowLeft,
  ArrowRight,
  ShieldCheck,
  Users,
} from 'lucide-react';
import { getDocBySlug, getPrevNextDocs, type DocItem } from './docsRegistry';
import { MarkdownRenderer } from './MarkdownRenderer';
import { DocsNavbar } from './DocsNavbar';
import { DocsSidebar } from './DocsSidebar';
import { DocsTableOfContents } from './DocsTableOfContents';
import { DocsSearchModal } from './DocsSearchModal';

export const DocsPage: React.FC = () => {
  const { slug } = useParams<{ slug?: string }>();

  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  const activeDoc: DocItem = getDocBySlug(slug || 'overview') || getDocBySlug('overview')!;
  const { prev, next } = getPrevNextDocs(activeDoc.slug);

  // Update page title
  useEffect(() => {
    document.title = `${activeDoc.title} · eRTMAC-NWIS Docs | SIH26121`;
    window.scrollTo({ top: 0, behavior: 'smooth' });
    const mainEl = document.getElementById('docs-content-viewport');
    if (mainEl) mainEl.scrollTo({ top: 0, behavior: 'smooth' });
  }, [activeDoc]);

  // Global search shortcut listener (Ctrl+K or Cmd+K)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsSearchOpen((prev) => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className="min-h-screen bg-[#f6f5f3] text-[#1c1917] flex flex-col font-sans selection:bg-amber-100 selection:text-amber-900">
      {/* Top Navbar */}
      <DocsNavbar
        currentSlug={activeDoc.slug}
        onToggleMobileSidebar={() => setIsMobileSidebarOpen((prev) => !prev)}
        isMobileSidebarOpen={isMobileSidebarOpen}
      />

      {/* Main Container Shell */}
      <div className="flex-1 flex w-full max-w-[1400px] mx-auto bg-[#fafaf9] sm:border-x border-stone-200/90 shadow-xs overflow-hidden">
        {/* Left Sidebar - Desktop */}
        <div className="hidden lg:block">
          <DocsSidebar currentSlug={activeDoc.slug} />
        </div>

        {/* Left Sidebar - Mobile Drawer Overlay */}
        {isMobileSidebarOpen && (
          <div className="lg:hidden fixed inset-0 z-50 flex">
            <div
              className="fixed inset-0 bg-stone-900/40 backdrop-blur-xs"
              onClick={() => setIsMobileSidebarOpen(false)}
            />
            <div className="relative z-10 w-80 max-w-[85vw] h-full shadow-2xl bg-white">
              <DocsSidebar
                currentSlug={activeDoc.slug}
                onSelectDoc={() => setIsMobileSidebarOpen(false)}
              />
            </div>
          </div>
        )}

        {/* Central Reading Canvas */}
        <main
          id="docs-content-viewport"
          className="flex-1 overflow-y-auto px-4 sm:px-8 md:px-12 py-8 max-h-[calc(100vh-4rem)] scrollbar-thin scrollbar-thumb-stone-300"
        >
          <div className="max-w-3xl mx-auto space-y-8">
            {/* Breadcrumb Navigation */}
            <div className="flex items-center gap-1.5 text-xs font-mono text-stone-500">
              <Link to="/docs" className="hover:text-stone-900 transition">
                Docs
              </Link>
              <ChevronRight className="w-3.5 h-3.5 text-stone-400" />
              <span className="text-stone-600">{activeDoc.category}</span>
              <ChevronRight className="w-3.5 h-3.5 text-stone-400" />
              <span className="text-stone-900 font-bold truncate">{activeDoc.title}</span>
            </div>

            {/* Document Header Banner */}
            <header className="border-b border-stone-200 pb-6 space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-[12px] font-mono px-2 py-0.5 rounded bg-stone-200 text-stone-800 uppercase font-bold">
                  {activeDoc.category}
                </span>
                {activeDoc.badge && (
                  <span className="text-[12px] font-mono px-2 py-0.5 rounded bg-stone-100 text-stone-700 border border-stone-200 font-semibold">
                    {activeDoc.badge}
                  </span>
                )}
                <span className="flex items-center gap-1 text-[12px] font-mono text-stone-600 bg-white px-2 py-0.5 rounded border border-stone-200">
                  <Clock className="w-3 h-3 text-stone-400" />
                  {activeDoc.readingTime}
                </span>
                <span className="flex items-center gap-1 text-[12px] font-mono text-stone-600 bg-white px-2 py-0.5 rounded border border-stone-200">
                  <ShieldCheck className="w-3 h-3 text-emerald-600" />
                  SIH26121 · OIL INDIA LIMITED
                </span>
                <span className="flex items-center gap-1 text-[12px] font-mono text-stone-600 bg-white px-2 py-0.5 rounded border border-stone-200">
                  <Users className="w-3 h-3 text-[#c96a12]" />
                  Midnight Ciphers
                </span>
              </div>

              <h1 className="text-3xl sm:text-4xl font-sans font-semibold text-stone-950 tracking-tight leading-tight">
                {activeDoc.title}
              </h1>

              <p className="text-base text-stone-600 font-sans leading-relaxed">
                {activeDoc.description}
              </p>
            </header>

            {/* Markdown Body Content */}
            <article className="prose-technical max-w-none text-[#292524]">
              <MarkdownRenderer content={activeDoc.content} />
            </article>

            {/* Previous / Next Document Navigation Cards */}
            <footer className="pt-8 mt-12 border-t border-stone-200">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {prev ? (
                  <Link
                    to={`/docs/${prev.slug}`}
                    className="group p-4 rounded-sm bg-white border border-stone-200 hover:border-stone-400 hover:bg-stone-50 transition flex flex-col justify-between shadow-2xs"
                  >
                    <div className="flex items-center gap-1 text-xs font-mono text-stone-400 mb-1">
                      <ArrowLeft className="w-3 h-3 group-hover:-translate-x-1 transition" />
                      <span>PREVIOUS SPECIFICATION</span>
                    </div>
                    <div className="text-sm font-bold text-stone-900 group-hover:text-stone-950 transition">
                      {prev.title}
                    </div>
                    <div className="text-xs text-stone-500 mt-1 line-clamp-1">{prev.category}</div>
                  </Link>
                ) : (
                  <div />
                )}

                {next ? (
                  <Link
                    to={`/docs/${next.slug}`}
                    className="group p-4 rounded-sm bg-white border border-stone-200 hover:border-stone-400 hover:bg-stone-50 transition flex flex-col justify-between text-right sm:items-end shadow-2xs"
                  >
                    <div className="flex items-center gap-1 text-xs font-mono text-stone-400 mb-1 justify-end">
                      <span>NEXT SPECIFICATION</span>
                      <ArrowRight className="w-3 h-3 group-hover:translate-x-1 transition" />
                    </div>
                    <div className="text-sm font-bold text-stone-900 group-hover:text-stone-950 transition">
                      {next.title}
                    </div>
                    <div className="text-xs text-stone-500 mt-1 line-clamp-1">{next.category}</div>
                  </Link>
                ) : (
                  <div />
                )}
              </div>

              {/* Bottom Attribution */}
              <div className="mt-8 pt-6 border-t border-stone-200 text-center text-xs font-mono text-stone-500 space-y-1">
                <p>
                  eRTMAC-NWIS Documentation · Smart India Hackathon 2026 (Problem Statement SIH26121)
                </p>
                <p className="text-stone-600 font-semibold">
                  Team: Midnight Ciphers · Developed for Oil India Limited (Duliajan Field Operations)
                </p>
              </div>
            </footer>
          </div>
        </main>

        {/* Right Table of Contents - Desktop */}
        <DocsTableOfContents content={activeDoc.content} />
      </div>

      {/* Global Command Palette Search Modal */}
      <DocsSearchModal isOpen={isSearchOpen} onClose={() => setIsSearchOpen(false)} />
    </div>
  );
};

export default DocsPage;
