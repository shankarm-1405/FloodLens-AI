import React, { useState, useEffect } from 'react';
import { 
  FileText, 
  Copy, 
  Check, 
  Sparkles, 
  ShieldAlert,
  Download,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Languages,
  Layers,
  Building2,
  Route,
  Activity,
  Printer
} from 'lucide-react';
import type { SystemHealth, SituationReport, ReportStatusResponse } from '../types';
import { 
  fetchReportStatus, 
  fetchSituationReport, 
  triggerReportGeneration 
} from '../services/api';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

interface ReportPageProps {
  health: SystemHealth | null;
}

export const ReportPage: React.FC<ReportPageProps> = ({ health }) => {
  const [analysisId, setAnalysisId] = useState<string>('e2e-trishuli-aug2026');
  const [lang, setLang] = useState<'en' | 'ne'>(() => {
    if (typeof window === 'undefined') return 'en';
    const params = new URLSearchParams(window.location.search);
    if (params.get('lang') === 'ne' || window.location.hash.includes('lang=ne')) return 'ne';
    return 'en';
  });
  const [report, setReport] = useState<SituationReport | null>(null);
  const [reportStatus, setReportStatus] = useState<ReportStatusResponse | null>(null);
  
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  // Load status and report on mount / ID / language change
  const loadReportData = async (targetId: string, targetLang: 'en' | 'ne') => {
    setIsLoading(true);
    setError(null);
    try {
      const statusRes = await fetchReportStatus(targetId);
      setReportStatus(statusRes);

      const rep = await fetchSituationReport(targetId, targetLang);
      setReport(rep);
    } catch (err: any) {
      console.warn("Could not load situation report:", err);
      setReport(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (analysisId) {
      loadReportData(analysisId, lang);
    }
  }, [analysisId, lang]);

  const handleGenerate = async () => {
    if (!analysisId) return;
    setIsGenerating(true);
    setError(null);
    try {
      const rep = await triggerReportGeneration({
        analysis_id: analysisId,
        language: lang,
        use_llm: true
      });
      setReport(rep);
      const statusRes = await fetchReportStatus(analysisId);
      setReportStatus(statusRes);
    } catch (err: any) {
      setError(err.message || 'Failed to generate situation report.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopy = () => {
    if (!report) return;
    const sections = report.sections;
    const fullText = `
# ${report.title}
Report ID: ${report.report_id}
Generated: ${report.generated_at}
Provenance: ${report.provenance}

${report.data_notice ? `> Notice: ${report.data_notice}\n` : ''}

## 1. Executive Summary
${sections.executive_summary}

## 2. Candidate Flood Extent & Sensor Telemetry
${sections.flood_extent_and_coverage}

## 3. Potentially Exposed Infrastructure
${sections.infrastructure_exposure}

## 4. Settlement Connectivity & Simulated Access Disruption
${sections.settlement_connectivity_and_isolation}

## 5. Confidence & Modeling Limitations
${sections.confidence_and_data_limitations}

## 6. Recommended Next Steps for Field Verification
${sections.recommended_next_steps}

## 7. Data Sources & Legal Attributions
${sections.data_attributions}

---
${report.disclaimer}
    `.trim();

    navigator.clipboard.writeText(fullText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const readiness = reportStatus?.input_readiness;
  const metrics = report?.summary_metrics;

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center space-x-2.5">
            <FileText className="w-7 h-7 text-emerald-400" />
            <span>Grounded AI Disaster Situation Report Copilot</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-3xl">
            Phase 6: Multi-hazard emergency intelligence synthesizing SAR water masks, OpenStreetMap infrastructure exposure, and settlement disconnection routing.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Language Selector */}
          <div className="flex rounded-lg bg-slate-900 border border-slate-800 p-1 shadow-sm">
            <button
              onClick={() => setLang('en')}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-all cursor-pointer ${
                lang === 'en'
                  ? 'bg-cyan-500 text-slate-950 font-bold shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              English
            </button>
            <button
              onClick={() => setLang('ne')}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-all cursor-pointer ${
                lang === 'ne'
                  ? 'bg-cyan-500 text-slate-950 font-bold shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              नेपाली (Nepali)
            </button>
          </div>

          {/* Copy Button */}
          <button
            onClick={handleCopy}
            disabled={!report}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs border border-slate-700 cursor-pointer disabled:opacity-50"
            title="Copy Report Text"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>
        </div>
      </div>

      {/* Input Status & Parameters Bar */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Analysis ID Input */}
        <div className="rounded-xl bg-slate-900 border border-slate-800 p-4 space-y-2">
          <label className="block text-xs font-semibold text-slate-200 flex items-center space-x-1.5">
            <Activity className="w-3.5 h-3.5 text-cyan-400" />
            <span>Target Flood Analysis ID</span>
          </label>
          <input
            type="text"
            value={analysisId}
            onChange={(e) => setAnalysisId(e.target.value)}
            placeholder="e.g. e2e-trishuli-aug2026"
            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 text-xs font-mono focus:outline-none focus:border-cyan-500"
          />
          <p className="text-[11px] text-slate-400">Analysis run identifier in data/outputs.</p>
        </div>

        {/* Input Readiness Indicators */}
        <div className="rounded-xl bg-slate-900 border border-slate-800 p-4 space-y-2 md:col-span-2">
          <span className="block text-xs font-semibold text-slate-200">Multimodal Input Readiness</span>
          <div className="grid grid-cols-3 gap-2 text-[11px] pt-1">
            <div className={`p-2 rounded border flex items-center space-x-1.5 ${
              readiness?.flood_data ? 'bg-emerald-950/40 border-emerald-800 text-emerald-300' : 'bg-slate-950 border-slate-800 text-slate-500'
            }`}>
              {readiness?.flood_data ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" /> : <XCircle className="w-3.5 h-3.5 text-slate-500 shrink-0" />}
              <span>SAR Flood Mask</span>
            </div>

            <div className={`p-2 rounded border flex items-center space-x-1.5 ${
              readiness?.infrastructure_data ? 'bg-emerald-950/40 border-emerald-800 text-emerald-300' : 'bg-slate-950 border-slate-800 text-slate-500'
            }`}>
              {readiness?.infrastructure_data ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" /> : <XCircle className="w-3.5 h-3.5 text-slate-500 shrink-0" />}
              <span>OSM Exposure</span>
            </div>

            <div className={`p-2 rounded border flex items-center space-x-1.5 ${
              readiness?.connectivity_data ? 'bg-emerald-950/40 border-emerald-800 text-emerald-300' : 'bg-slate-950 border-slate-800 text-slate-500'
            }`}>
              {readiness?.connectivity_data ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" /> : <XCircle className="w-3.5 h-3.5 text-slate-500 shrink-0" />}
              <span>Road Routing</span>
            </div>
          </div>
          <p className="text-[11px] text-slate-400">
            {readiness?.all_inputs_ready 
              ? 'All 3 analytical layers ingested and grounded.' 
              : 'One or more analytical pipelines missing. Missing sections will report UNAVAILABLE.'}
          </p>
        </div>

        {/* Re-generate Action Button */}
        <div className="rounded-xl bg-slate-900 border border-slate-800 p-4 flex flex-col justify-between">
          <div>
            <span className="text-xs font-semibold text-slate-200">Grounded Synthesis</span>
            <p className="text-[11px] text-slate-400 mt-1">Compile bilingual report with strict guardrail checks.</p>
          </div>
          <button
            onClick={handleGenerate}
            disabled={isGenerating || !analysisId}
            className="w-full py-2 px-3 rounded-lg bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-white font-medium text-xs flex items-center justify-center space-x-2 transition-all cursor-pointer shadow-md disabled:opacity-50"
          >
            {isGenerating ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 fill-current" />}
            <span>{isGenerating ? 'Compiling Report...' : 'Generate Situation Report'}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl bg-rose-950/60 border border-rose-800 p-4 text-xs text-rose-200 flex items-start space-x-3">
          <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold">Generation Failed:</span>
            <p className="text-rose-300 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Provenance Banner */}
      {report && (
        <div className={`rounded-xl border p-4 text-xs flex items-start space-x-3 shadow-lg ${
          report.is_synthetic 
            ? 'bg-amber-950/40 border-amber-800/80 text-amber-200' 
            : 'bg-emerald-950/40 border-emerald-800/80 text-emerald-200'
        }`}>
          <ShieldAlert className="w-5 h-5 text-amber-400 mt-0.5 shrink-0" />
          <div className="space-y-1">
            <div className="font-bold flex items-center space-x-2">
              <span className="px-2 py-0.5 rounded font-mono text-[11px] bg-slate-900 border border-slate-700 text-slate-200">
                PROVENANCE: {report.provenance}
              </span>
              <span>{report.data_notice}</span>
            </div>
            <p className="text-slate-300 leading-relaxed text-[11px]">
              {report.is_synthetic 
                ? 'This report is derived from synthetic demonstration fixtures (synthetic Sentinel-1 SAR differences & verified OSM pre-event baseline fixture). All statistics are illustrative and do not reflect confirmed ground casualties or structural collapses.' 
                : 'Report synthesized from operational Copernicus Sentinel satellite telemetry and pre-event historical OpenStreetMap infrastructure.'}
            </p>
          </div>
        </div>
      )}

      {/* Situation Report Preview Document Container */}
      {report ? (
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 sm:p-8 space-y-6 shadow-2xl">
          {/* Document Header & Metadata Bar */}
          <div className="border-b border-slate-800 pb-5 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-cyan-400">
                {report.report_id}
              </span>
              <div className="flex items-center space-x-2 text-[11px] font-mono text-slate-400">
                <span className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-slate-300">
                  Method: {report.generation_method}
                </span>
                <span>Generated: {report.generated_at ? report.generated_at.substring(0, 19) + 'Z' : 'N/A'}</span>
              </div>
            </div>

            <h2 className="text-xl sm:text-2xl font-bold text-white">
              {report.title}
            </h2>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono text-slate-400 pt-2 border-t border-slate-800/60">
              <div>
                <span className="block text-slate-500 text-[10px]">STUDY AREA</span>
                <span className="text-slate-300">{report.study_area}</span>
              </div>
              <div>
                <span className="block text-slate-500 text-[10px]">EVENT DATE</span>
                <span className="text-slate-300">{report.event_date}</span>
              </div>
              <div>
                <span className="block text-slate-500 text-[10px]">LANGUAGE</span>
                <span className="text-cyan-400 font-bold">{report.language.toUpperCase()}</span>
              </div>
              <div>
                <span className="block text-slate-500 text-[10px]">PROVENANCE</span>
                <span className={report.is_synthetic ? 'text-amber-400 font-bold' : 'text-emerald-400 font-bold'}>
                  {report.provenance}
                </span>
              </div>
            </div>
          </div>

          {/* Key Computed Metrics Table */}
          {metrics && (
            <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-3">
              <div className="text-xs font-bold text-slate-200 uppercase tracking-wider font-mono">
                {lang === 'ne' ? 'मुख्य कम्प्युटेड परिमाणहरू (Key Grounded Metrics)' : 'Key Computed Metrics at a Glance'}
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-xs font-mono">
                <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
                  <span className="text-slate-400 text-[10px] block">Candidate Flood</span>
                  <span className="text-cyan-300 font-bold text-sm">
                    {metrics.candidate_flood_area_sqkm !== null ? `${metrics.candidate_flood_area_sqkm} km²` : 'UNAVAILABLE'}
                  </span>
                </div>
                <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
                  <span className="text-slate-400 text-[10px] block">Permanent Water</span>
                  <span className="text-slate-200 font-bold text-sm">
                    {metrics.permanent_water_area_sqkm !== null ? `${metrics.permanent_water_area_sqkm} km²` : 'UNAVAILABLE'}
                  </span>
                </div>
                <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
                  <span className="text-slate-400 text-[10px] block">Exposed Buildings</span>
                  <span className="text-rose-300 font-bold text-sm">
                    {metrics.exposed_buildings_count !== null ? metrics.exposed_buildings_count : 'UNAVAILABLE'}
                  </span>
                </div>
                <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
                  <span className="text-slate-400 text-[10px] block">Exposed Roads</span>
                  <span className="text-rose-300 font-bold text-sm">
                    {metrics.exposed_road_length_km !== null ? `${metrics.exposed_road_length_km} km` : 'UNAVAILABLE'}
                  </span>
                </div>
                <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
                  <span className="text-slate-400 text-[10px] block">Compromised Bridges</span>
                  <span className="text-rose-300 font-bold text-sm">
                    {metrics.exposed_bridges_count !== null ? metrics.exposed_bridges_count : 'UNAVAILABLE'}
                  </span>
                </div>
                <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
                  <span className="text-slate-400 text-[10px] block">Newly Cut-Off</span>
                  <span className="text-rose-400 font-bold text-sm">
                    {metrics.newly_disconnected_count !== null ? metrics.newly_disconnected_count : 'UNAVAILABLE'}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Report Sections Content */}
          <div className="space-y-6 text-xs text-slate-300 leading-relaxed font-sans">
            {/* 1. Executive Summary */}
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-white uppercase tracking-wider font-mono text-cyan-300">
                {lang === 'ne' ? '१. कार्यकारी सारांश र भौगोलिक क्षेत्र' : '1. Executive Summary & Geographic Scope'}
              </h3>
              <p className="whitespace-pre-line leading-relaxed text-slate-200">
                {report.sections.executive_summary}
              </p>
            </div>

            {/* 2. Flood Extent & Coverage */}
            <div className="space-y-2 border-t border-slate-800 pt-4">
              <h3 className="text-sm font-semibold text-white uppercase tracking-wider font-mono text-cyan-300">
                {lang === 'ne' ? '२. सम्भावित बाढी क्षेत्र र उपग्रह कभरेज' : '2. Candidate Flood Extent & Sensor Telemetry'}
              </h3>
              <p className="whitespace-pre-line leading-relaxed text-slate-300 font-mono text-[11px]">
                {report.sections.flood_extent_and_coverage}
              </p>
            </div>

            {/* 3. Infrastructure Exposure */}
            <div className="space-y-2 border-t border-slate-800 pt-4">
              <h3 className="text-sm font-semibold text-white uppercase tracking-wider font-mono text-cyan-300">
                {lang === 'ne' ? '३. सम्भावित पूर्वाधार जोखिम' : '3. Potentially Exposed Infrastructure'}
              </h3>
              <p className="whitespace-pre-line leading-relaxed text-slate-300 font-mono text-[11px]">
                {report.sections.infrastructure_exposure}
              </p>
            </div>

            {/* 4. Settlement Connectivity & Disconnection */}
            <div className="space-y-2 border-t border-slate-800 pt-4">
              <h3 className="text-sm font-semibold text-white uppercase tracking-wider font-mono text-cyan-300">
                {lang === 'ne' ? '४. बस्ती सडक सम्पर्क र आवागमन अवरोध' : '4. Settlement Road Disconnection & Isolation'}
              </h3>
              <p className="whitespace-pre-line leading-relaxed text-slate-300 font-mono text-[11px]">
                {report.sections.settlement_connectivity_and_isolation}
              </p>
            </div>

            {/* 5. Confidence & Data Limitations */}
            <div className="space-y-2 border-t border-slate-800 pt-4">
              <h3 className="text-sm font-semibold text-white uppercase tracking-wider font-mono text-cyan-300">
                {lang === 'ne' ? '५. विश्वसनीयता र तथ्याङ्क सीमितताहरू' : '5. Confidence & Modeling Limitations'}
              </h3>
              <p className="whitespace-pre-line leading-relaxed text-slate-300 text-[11px]">
                {report.sections.confidence_and_data_limitations}
              </p>
            </div>

            {/* 6. Recommended Next Steps */}
            <div className="space-y-2 border-t border-slate-800 pt-4">
              <h3 className="text-sm font-semibold text-white uppercase tracking-wider font-mono text-cyan-300">
                {lang === 'ne' ? '६. स्थलगत प्रमाणीकरणका लागि सिफारिसहरू' : '6. Recommended Next Steps for Field Verification'}
              </h3>
              <p className="whitespace-pre-line leading-relaxed text-slate-300 text-[11px]">
                {report.sections.recommended_next_steps}
              </p>
            </div>

            {/* 7. Data Attributions */}
            <div className="space-y-2 border-t border-slate-800 pt-4">
              <h3 className="text-sm font-semibold text-white uppercase tracking-wider font-mono text-cyan-300">
                {lang === 'ne' ? '७. तथ्याङ्क स्रोत र कानुनी आभार' : '7. Data Sources & Legal Attributions'}
              </h3>
              <p className="whitespace-pre-line leading-relaxed text-slate-400 text-[11px]">
                {report.sections.data_attributions}
              </p>
            </div>
          </div>

          {/* Mandatory Educational Prototype Disclaimer Footer */}
          <div className="pt-4 border-t border-slate-800 text-[11px] text-slate-400 font-mono space-y-1">
            <div className="text-amber-400 font-semibold flex items-center space-x-1.5">
              <ShieldAlert className="w-3.5 h-3.5" />
              <span>Educational & Research Prototype Disclaimer:</span>
            </div>
            <p className="leading-relaxed">
              {report.disclaimer}
            </p>
          </div>
        </div>
      ) : (
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-12 text-center text-slate-500 italic space-y-2">
          <p>{isLoading ? 'Loading situation report...' : 'No situation report generated yet for this analysis ID.'}</p>
          <p className="text-xs text-slate-600">Click "Generate Situation Report" above to compile.</p>
        </div>
      )}

      {/* Export Options & Downloads */}
      {report && (
        <div className="rounded-xl bg-slate-900 border border-slate-800 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-xs font-bold text-white flex items-center space-x-1.5">
              <Download className="w-4 h-4 text-emerald-400" />
              <span>Export Situation Report</span>
            </h3>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Download grounded assessment as formatted Markdown or publication-quality PDF.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <a
              href={`${API_BASE}/api/report/${encodeURIComponent(analysisId)}/export/markdown?language=${lang}`}
              download
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium flex items-center space-x-1.5 border border-slate-700 transition-colors cursor-pointer"
            >
              <FileText className="w-3.5 h-3.5 text-cyan-400" />
              <span>Markdown ({lang.toUpperCase()})</span>
            </a>
            <a
              href={`${API_BASE}/api/report/${encodeURIComponent(analysisId)}/export/pdf?language=${lang}`}
              download
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium flex items-center space-x-1.5 border border-slate-700 transition-colors cursor-pointer"
            >
              <Printer className="w-3.5 h-3.5 text-emerald-400" />
              <span>PDF ({lang.toUpperCase()})</span>
            </a>
          </div>
        </div>
      )}
    </div>
  );
};
