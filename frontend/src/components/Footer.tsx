import React from 'react';
import { ShieldCheck, Satellite } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="mt-auto border-t border-slate-800 bg-slate-900/90 text-slate-400 text-xs py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Mandatory Legal Attribution Section */}
        <div className="rounded-xl bg-slate-950/70 border border-slate-800/90 p-4 space-y-2.5">
          <div className="flex items-center space-x-2 text-cyan-400 font-semibold uppercase tracking-wider text-[11px] font-mono">
            <ShieldCheck className="w-4 h-4" />
            <span>Official Data Attribution & Provenance</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[11px] text-slate-300 font-sans leading-relaxed">
            <div className="p-2.5 rounded bg-slate-900/60 border border-slate-800">
              <span className="font-semibold text-slate-200 block mb-1">Copernicus Sentinel Program:</span>
              <p className="font-mono text-[10.5px] text-cyan-200/90">"Contains modified Copernicus Sentinel data 2026."</p>
            </div>
            <div className="p-2.5 rounded bg-slate-900/60 border border-slate-800">
              <span className="font-semibold text-slate-200 block mb-1">Copernicus WorldDEM-30:</span>
              <p className="font-mono text-[10.5px] text-cyan-200/90">
                "Produced using Copernicus WorldDEM-30 © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018 provided under COPERNICUS by the European Union and ESA; all rights reserved."
              </p>
            </div>
            <div className="p-2.5 rounded bg-slate-900/60 border border-slate-800">
              <span className="font-semibold text-slate-200 block mb-1">OpenStreetMap Foundation:</span>
              <p className="font-mono text-[10.5px] text-cyan-200/90">"© OpenStreetMap contributors."</p>
            </div>
          </div>
        </div>

        {/* Disclaimer & Project Context */}
        <div className="flex flex-col md:flex-row items-center justify-between text-[11px] text-slate-400 gap-4">
          <div className="flex items-center space-x-2">
            <Satellite className="w-4 h-4 text-cyan-400" />
            <span>FloodLens AI • Multimodal AI Hackathon 2026 • Track B: Mapping Flood Damage from Space</span>
          </div>
          <div className="text-center md:text-right text-slate-400">
            Educational & Research Prototype. Model outputs require field verification prior to tactical deployment.
          </div>
        </div>
      </div>
    </footer>
  );
};
