import type { 
  SystemHealth, 
  ConfigStatus, 
  SatelliteSearchResult, 
  CredentialsStatus 
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export async function checkBackendHealth(): Promise<SystemHealth> {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    if (!res.ok) {
      throw new Error(`HTTP error ${res.status}: ${res.statusText}`);
    }
    return await res.json();
  } catch (_error) {
    return {
      status: 'offline',
      timestamp: new Date().toISOString(),
      service: 'FloodLens AI Backend (Unavailable)',
      demo_mode: true,
      geospatial_stack: {},
      study_case: {
        region: 'Trishuli Corridor, Nepal',
        default_bbox: [85.05, 27.75, 85.25, 27.95],
        default_event_date: '2026-08-04',
        osm_snapshot_date: '2026-07-27',
      },
    };
  }
}

export async function fetchConfigStatus(): Promise<ConfigStatus | null> {
  try {
    const res = await fetch(`${API_BASE}/api/config-status`);
    if (!res.ok) return null;
    return await res.json();
  } catch (_error) {
    return null;
  }
}

export async function fetchAttributions(): Promise<{ required_statements: string[]; details: any[] } | null> {
  try {
    const res = await fetch(`${API_BASE}/api/attribution`);
    if (!res.ok) return null;
    return await res.json();
  } catch (_error) {
    return null;
  }
}

export async function searchSatelliteAcquisitions(params: {
  bbox?: number[];
  event_date?: string;
  window_days?: number;
  include_optical?: boolean;
  force_live?: boolean;
}): Promise<SatelliteSearchResult> {
  const res = await fetch(`${API_BASE}/api/satellite/search`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(params),
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `Search failed with status ${res.status}`);
  }

  return await res.json();
}

export async function fetchCredentialsStatus(): Promise<CredentialsStatus | null> {
  try {
    const res = await fetch(`${API_BASE}/api/satellite/credentials-status`);
    if (!res.ok) return null;
    return await res.json();
  } catch (_error) {
    return null;
  }
}

export async function checkDownloadReadiness(productId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/satellite/download-check?product_id=${encodeURIComponent(productId)}`, {
    method: 'POST',
  });
  if (!res.ok) {
    throw new Error(`Download check failed with status ${res.status}`);
  }
  return await res.json();
}
