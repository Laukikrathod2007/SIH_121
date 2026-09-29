import React, { useState, useEffect } from 'react';
import {
  FileUp,
  FileText,
  CheckCircle,
  Clock,
  ArrowRight,
  Upload,
  Cpu,
  ShieldCheck,
  Code,
  Download,
  Eye,
} from 'lucide-react';
import { api } from '../services/api';
import { DocumentJob } from '../types';

export const DocumentIngestionPage: React.FC = () => {
  const [jobs, setJobs] = useState<DocumentJob[]>([]);
  const [activeStep, setActiveStep] = useState<number>(6);
  const [uploading, setUploading] = useState<boolean>(false);
  const [previewTab, setPreviewTab] = useState<'formations' | 'npt' | 'witsml'>('formations');

  const layers = [
    { num: 1, name: 'PDF PARSING & OCR', desc: 'pypdfium2 text + vector geometry layout extraction' },
    { num: 2, name: 'TABLE MORPHOLOGY', desc: 'OpenCV morphological line detection & cell rasterization' },
    { num: 3, name: 'DOMAIN NER', desc: 'Lithology, bit size, casing points, & IADC hazard entities' },
    { num: 4, name: 'COORDINATE TEMPLATES', desc: 'Layout alignment & learned bounding box matching' },
    { num: 5, name: 'PHYSICS VALIDATION', desc: 'Layer 5 sanity check on mud weights, UCS & depths' },
    { num: 6, name: 'WITSML DATA STORE', desc: 'Standardized XML / JSON persistence into NWISDataStore' },
  ];

  // Pre-cooked demonstration extracted records
  const sampleFormations = [
    { name: 'Tipam Sandstone', top: 1840.0, base: 2400.0, lithology: 'Coarse Sandstone', confidence: 0.98 },
    { name: 'Barail Sandstone', top: 2400.0, base: 2820.0, lithology: 'Fine to medium sand with shales', confidence: 0.96 },
    { name: 'Barail Lower Sand', top: 2820.0, base: 3150.0, lithology: 'Shaly sandstone & coal streaks', confidence: 0.94 },
    { name: 'Kopili Formation', top: 3150.0, base: 3480.0, lithology: 'Splintery marine shale', confidence: 0.92 },
  ];

  const sampleNpt = [
    { code: '05', hazard: 'Lost Circulation', depth: 2465.0, formation: 'Barail Sandstone', hours: 4.5, cost: '₹ 18.5 L', status: 'MITIGATED' },
    { code: '07', hazard: 'Tight Hole / Drag', depth: 2835.0, formation: 'Barail Lower Sand', hours: 2.0, cost: '₹ 8.2 L', status: 'MITIGATED' },
    { code: '12', hazard: 'Bit Balling / MSE Spike', depth: 3180.0, formation: 'Kopili Formation', hours: 3.0, cost: '₹ 12.0 L', status: 'RESOLVED' },
  ];

  const handleSimulatedUpload = (filename: string) => {
    setUploading(true);
    setActiveStep(1);

    const stepInterval = setInterval(() => {
      setActiveStep((prev) => {
        if (prev >= 6) {
          clearInterval(stepInterval);
          setUploading(false);
          return 6;
        }
        return prev + 1;
      });
    }, 400);
  };

  return (
    <div className="p-4 space-y-4 max-w-[1600px] mx-auto">
      {/* Header */}
      <div className="scada-panel p-3 flex items-center justify-between border-l-4 border-l-cyan-500">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-cyan-500/10 border border-cyan-500/30 rounded text-cyan-400">
            <FileUp className="w-5 h-5" />
          </div>
          <div>
            <div className="text-sm font-bold text-slate-100 flex items-center gap-2">
              MODULE 1: DOCUMENT INTELLIGENCE & OCR EXTRACTION PIPELINE
              <span className="text-[10px] font-mono bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 px-1.5 py-0.5 rounded">
                6-LAYER EXTRACTION
              </span>
            </div>
            <div className="text-xs text-slate-400 font-mono">
              Daily Drilling Reports (DDR) | Well Completion Reports (WCR) | IADC NPT Taxonomy | Layer 5 Physics Check
            </div>
          </div>
        </div>

        <div className="text-xs font-mono text-emerald-400 flex items-center gap-1.5">
          <CheckCircle className="w-4 h-4" />
          <span>Pipeline Ready</span>
        </div>
      </div>

      {/* 6-Layer Extraction Architecture Stepper */}
      <div className="scada-panel p-4 space-y-3">
        <div className="text-xs font-mono font-bold text-slate-200">
          6-LAYER EXTRACTION & VALIDATION PIPELINE ARCHITECTURE
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
          {layers.map((l) => (
            <div
              key={l.num}
              className={`p-2.5 rounded border text-xs font-mono space-y-1 transition ${
                activeStep >= l.num
                  ? 'bg-cyan-950/40 border-cyan-500/40 text-cyan-200'
                  : 'bg-slate-900/60 border-slate-800 text-slate-400'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="w-5 h-5 rounded-full bg-slate-800 text-slate-200 flex items-center justify-center font-bold text-[10px]">
                  {l.num}
                </span>
                {activeStep >= l.num && <span className="text-[10px] text-emerald-400 font-bold">✓ PASS</span>}
              </div>
              <div className="font-bold text-[11px] text-slate-100">{l.name}</div>
              <div className="text-[9px] text-slate-400 leading-tight">{l.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Upload Zone & Quick Sample Loaders */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left: Drag & Drop Zone */}
        <div className="scada-panel p-4 flex flex-col justify-between space-y-3">
          <div>
            <div className="text-xs font-mono font-bold text-slate-200 pb-2 border-b border-slate-800">
              UPLOAD LEGACY DRILLING REPORT
            </div>

            <div className="mt-3 p-6 border-2 border-dashed border-slate-700 hover:border-cyan-500 rounded-lg text-center space-y-2 cursor-pointer transition bg-slate-900/40">
              <Upload className="w-8 h-8 text-cyan-400 mx-auto" />
              <div className="text-xs font-mono text-slate-200">
                Drag & Drop PDF or Click to Browse
              </div>
              <div className="text-[10px] font-mono text-slate-400">
                Supports: Oil India Limited DDRs, WCRs, Mud Logs (PDF)
              </div>
            </div>

            {/* Quick Demo Pre-load buttons */}
            <div className="mt-4 space-y-2">
              <div className="text-[10px] font-mono text-slate-400 uppercase tracking-widest">
                FAST JUDGING DEMO PRESETS:
              </div>
              <button
                disabled={uploading}
                onClick={() => handleSimulatedUpload('Tengakhat-04-DDR.pdf')}
                className="w-full text-left p-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 rounded text-xs font-mono flex items-center justify-between transition"
              >
                <div>
                  <div className="text-slate-200 font-semibold">Tengakhat-04 Daily Report</div>
                  <div className="text-[10px] text-amber-400">Lost Circulation (4.5 hrs NPT)</div>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-cyan-400" />
              </button>

              <button
                disabled={uploading}
                onClick={() => handleSimulatedUpload('Well-16A-Completion.pdf')}
                className="w-full text-left p-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 rounded text-xs font-mono flex items-center justify-between transition"
              >
                <div>
                  <div className="text-slate-200 font-semibold">Well 16A(78)-32 Summary</div>
                  <div className="text-[10px] text-emerald-400">4 Stratigraphic Tops Extracted</div>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-cyan-400" />
              </button>
            </div>
          </div>

          <div className="pt-2 border-t border-slate-800 text-[10px] font-mono text-slate-400">
            OCR Engine: Native Docling / pypdfium2 OCR with Layer 5 Physical Validation
          </div>
        </div>

        {/* Right 2 Cols: Extracted Results Inspector */}
        <div className="lg:col-span-2 scada-panel p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <div className="flex items-center space-x-2 text-xs font-mono font-bold text-slate-200">
                <FileText className="w-4 h-4 text-cyan-400" />
                <span>EXTRACTION OUTCOME: Tengakhat-04-DDR.pdf</span>
              </div>

              {/* Tabs */}
              <div className="flex items-center space-x-1 text-xs font-mono">
                <button
                  onClick={() => setPreviewTab('formations')}
                  className={`px-2.5 py-1 rounded ${
                    previewTab === 'formations' ? 'bg-cyan-500 text-slate-950 font-bold' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Formation Tops
                </button>
                <button
                  onClick={() => setPreviewTab('npt')}
                  className={`px-2.5 py-1 rounded ${
                    previewTab === 'npt' ? 'bg-cyan-500 text-slate-950 font-bold' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  IADC NPT Events
                </button>
                <button
                  onClick={() => setPreviewTab('witsml')}
                  className={`px-2.5 py-1 rounded ${
                    previewTab === 'witsml' ? 'bg-cyan-500 text-slate-950 font-bold' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  WITSML XML
                </button>
              </div>
            </div>

            {/* Tab 1: Formations */}
            {previewTab === 'formations' && (
              <div className="mt-3 overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-slate-900 text-slate-400 text-[10px] uppercase border-b border-slate-800">
                    <tr>
                      <th className="p-2">Formation Name</th>
                      <th className="p-2">Top (m TVDSS)</th>
                      <th className="p-2">Base (m TVDSS)</th>
                      <th className="p-2">Thickness</th>
                      <th className="p-2">Lithology</th>
                      <th className="p-2">Confidence</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-200">
                    {sampleFormations.map((f) => (
                      <tr key={f.name} className="hover:bg-slate-900/40">
                        <td className="p-2 text-amber-300 font-bold">{f.name}</td>
                        <td className="p-2">{f.top.toFixed(1)}</td>
                        <td className="p-2">{f.base.toFixed(1)}</td>
                        <td className="p-2">{(f.base - f.top).toFixed(1)} m</td>
                        <td className="p-2 text-slate-400">{f.lithology}</td>
                        <td className="p-2 text-emerald-400 font-bold">{(f.confidence * 100).toFixed(0)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Tab 2: NPT Hazards */}
            {previewTab === 'npt' && (
              <div className="mt-3 overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-slate-900 text-slate-400 text-[10px] uppercase border-b border-slate-800">
                    <tr>
                      <th className="p-2">IADC Code</th>
                      <th className="p-2">Hazard Event</th>
                      <th className="p-2">Depth</th>
                      <th className="p-2">Formation</th>
                      <th className="p-2">NPT Hours</th>
                      <th className="p-2">Cost Impact</th>
                      <th className="p-2">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-200">
                    {sampleNpt.map((n) => (
                      <tr key={n.code} className="hover:bg-slate-900/40">
                        <td className="p-2 text-cyan-400 font-bold">{n.code}</td>
                        <td className="p-2 text-rose-400 font-bold">{n.hazard}</td>
                        <td className="p-2">{n.depth} m</td>
                        <td className="p-2 text-slate-300">{n.formation}</td>
                        <td className="p-2 font-bold">{n.hours} hrs</td>
                        <td className="p-2 text-amber-300">{n.cost}</td>
                        <td className="p-2 text-emerald-400 font-bold">{n.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Tab 3: WITSML Preview */}
            {previewTab === 'witsml' && (
              <div className="mt-3 bg-slate-950 p-3 rounded border border-slate-800 font-mono text-[11px] text-cyan-300 max-h-64 overflow-y-auto">
                <pre>{`<?xml version="1.0" encoding="UTF-8"?>
<formationTops version="1.4.1.1" xmlns="http://www.witsml.org/schemas/1series">
  <formationTop uid="fmt-01">
    <nameFormation>Barail Sandstone</nameFormation>
    <md uom="m">2460.0</md>
    <tvd uom="m">2400.0</tvd>
    <lithology>Sandstone with intercalated shale</lithology>
    <confidence>0.96</confidence>
    <provenance>EXTRACTED_FROM_DDR</provenance>
  </formationTop>
  <hazardEvent uid="hzd-01">
    <type>LOST_CIRCULATION</type>
    <iadcCode>05</iadcCode>
    <lossRate uom="bbl/hr">75</lossRate>
  </hazardEvent>
</formationTops>`}</pre>
              </div>
            )}
          </div>

          <div className="mt-3 pt-2 border-t border-slate-800 text-[11px] font-mono text-slate-400 flex items-center justify-between">
            <span>Validated Against Layer 5 Physics Bounds</span>
            <span className="text-emerald-400">Stored in NWISDataStore</span>
          </div>
        </div>
      </div>
    </div>
  );
};
