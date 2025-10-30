import { useEffect, useMemo, useState } from "react";
import {
  Film,
  Loader2,
  Mic2,
  Music3,
  ScriptText,
  Settings2,
  Waves,
  Wand2
} from "lucide-react";
import api from "./hooks/useApi";
import Card from "./components/Card";

type AnalysisStatus = {
  video_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  message?: string | null;
  result?: {
    summary?: string;
    keywords?: string[];
    transcript?: string;
    transcript_path?: string;
    audio_path?: string;
    scenes?: { scene_id: number; start_time: number; end_time: number; duration: number }[];
  } | null;
};

type VoiceProfile = {
  voice_id: string;
  display_name: string;
  sample_path: string;
};

const SCRIPT_STYLES = [
  { value: "dry", label: "Dry" },
  { value: "dark_sarcastic", label: "Dark Sarcastic" },
  { value: "laid_back", label: "Laid Back" },
  { value: "southern_chill", label: "Southern Chill" },
  { value: "energetic", label: "Energetic" },
  { value: "inspirational", label: "Inspirational" }
];

const AMBIENT_TYPES = [
  "wind",
  "car",
  "plane",
  "footsteps",
  "train",
  "rain"
] as const;

export default function App() {
  const [videoId, setVideoId] = useState<string | null>(null);
  const [uploadedName, setUploadedName] = useState<string>("");
  const [analysis, setAnalysis] = useState<AnalysisStatus | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [scriptStyle, setScriptStyle] = useState<string>(SCRIPT_STYLES[0].value);
  const [scriptText, setScriptText] = useState<string>("");
  const [scriptNotes, setScriptNotes] = useState<string>("");
  const [voices, setVoices] = useState<VoiceProfile[]>([]);
  const [voiceName, setVoiceName] = useState<string>("");
  const [voiceSample, setVoiceSample] = useState<File | null>(null);
  const [selectedVoice, setSelectedVoice] = useState<string>("");
  const [narrationPath, setNarrationPath] = useState<string>("");
  const [musicPrompt, setMusicPrompt] = useState<string>("warm gentle synth pad");
  const [musicMood, setMusicMood] = useState<string>("calm");
  const [musicDuration, setMusicDuration] = useState<number>(45);
  const [musicPath, setMusicPath] = useState<string>("");
  const [ambientType, setAmbientType] = useState<typeof AMBIENT_TYPES[number]>("wind");
  const [ambientDuration, setAmbientDuration] = useState<number>(30);
  const [ambientPaths, setAmbientPaths] = useState<string[]>([]);
  const [timelinePath, setTimelinePath] = useState<string>("");
  const [bundlePath, setBundlePath] = useState<string>("");
  const [bundleAssets, setBundleAssets] = useState<boolean>(true);
  const [loadingMessage, setLoadingMessage] = useState<string | null>(null);

  const canGenerateScript = useMemo(() => analysis?.status === "completed", [analysis]);

  useEffect(() => {
    let interval: number | undefined;
    if (videoId && (analysis?.status === "pending" || analysis?.status === "processing")) {
      interval = window.setInterval(async () => {
        try {
          const { data } = await api.get<AnalysisStatus>(`/videos/${videoId}/analysis`);
          setAnalysis(data);
          if (data.status === "completed" || data.status === "failed") {
            setIsAnalyzing(false);
            if (interval) window.clearInterval(interval);
          }
        } catch (error) {
          console.error(error);
        }
      }, 5000);
    }
    return () => {
      if (interval) window.clearInterval(interval);
    };
  }, [videoId, analysis?.status]);

  const refreshVoices = async () => {
    const { data } = await api.get<Record<string, VoiceProfile>>("/voices");
    const profiles = Object.values(data);
    setVoices(profiles);
    if (profiles.length && !selectedVoice) {
      setSelectedVoice(profiles[0].voice_id);
    }
  };

  useEffect(() => {
    refreshVoices().catch(console.error);
  }, []);

  const handleUpload = async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    setLoadingMessage("Uploading video");
    const { data } = await api.post<VideoUploadResponse>("/videos", form, {
      headers: { "Content-Type": "multipart/form-data" }
    });
    setVideoId(data.video_id);
    setUploadedName(data.filename);
    setAnalysis({ video_id: data.video_id, status: "pending", message: "Ready for analysis" });
    setScriptText("");
    setNarrationPath("");
    setMusicPath("");
    setAmbientPaths([]);
    setTimelinePath("");
    setBundlePath("");
    setLoadingMessage(null);
  };

  const startAnalysis = async () => {
    if (!videoId) return;
    setIsAnalyzing(true);
    setLoadingMessage("Analyzing video (scene cuts, transcription, keywords)");
    const { data } = await api.post<AnalysisStatus>(`/videos/${videoId}/analyze`);
    setAnalysis(data);
    setLoadingMessage(null);
  };

  const generateScript = async () => {
    if (!videoId) return;
    setLoadingMessage("Crafting script with tone adjustments");
    const { data } = await api.post<{ video_id: string; script: string }>("/scripts", {
      video_id: videoId,
      style: scriptStyle,
      duration_seconds: 120,
      extra_notes: scriptNotes
    });
    setScriptText(data.script);
    setLoadingMessage(null);
  };

  const registerVoice = async () => {
    if (!voiceSample || !voiceName.trim()) return;
    const form = new FormData();
    form.append("display_name", voiceName.trim());
    form.append("sample", voiceSample);
    setLoadingMessage("Extracting voice fingerprint");
    await api.post("/voices", form, { headers: { "Content-Type": "multipart/form-data" } });
    setVoiceName("");
    setVoiceSample(null);
    await refreshVoices();
    setLoadingMessage(null);
  };

  const synthesizeVoice = async () => {
    if (!selectedVoice || !scriptText.trim()) return;
    setLoadingMessage("Rendering narration with cloned voice");
    const { data } = await api.post<{ path: string }>("/voices/synthesize", {
      voice_id: selectedVoice,
      text: scriptText,
      speed: 1.0
    });
    setNarrationPath(data.path);
    setLoadingMessage(null);
  };

  const generateMusicTrack = async () => {
    setLoadingMessage("Designing background music bed");
    const { data } = await api.post<{ path: string }>("/audio/music", {
      prompt: musicPrompt,
      mood: musicMood,
      duration_seconds: musicDuration
    });
    setMusicPath(data.path);
    setLoadingMessage(null);
  };

  const generateAmbientLayer = async () => {
    setLoadingMessage("Generating ambient layer");
    const { data } = await api.post<{ path: string }>("/audio/ambient", {
      ambient_type: ambientType,
      duration_seconds: ambientDuration,
      intensity: 0.7
    });
    setAmbientPaths((prev) => [...prev, data.path]);
    setLoadingMessage(null);
  };

  const buildTimeline = async () => {
    if (!videoId || !narrationPath) return;
    setLoadingMessage("Packing assets for YouCut alignment");
    const { data } = await api.post<TimelineResponse>("/timeline", {
      video_id: videoId,
      narration_path: narrationPath,
      music_path: musicPath || null,
      ambient_paths: ambientPaths,
      beat_alignment: true,
      bundle_assets: bundleAssets
    });
    setTimelinePath(data.export_path);
    setBundlePath(data.bundle_path ?? "");
    setLoadingMessage(null);
  };

  return (
    <div
      style={{
        maxWidth: "1200px",
        margin: "0 auto",
        padding: "48px 24px 96px",
        display: "flex",
        flexDirection: "column",
        gap: "24px"
      }}
    >
      <header style={{ textAlign: "center", display: "flex", flexDirection: "column", gap: "8px" }}>
        <h1 style={{ fontSize: "2.4rem", fontWeight: 700 }}>Creator Forge · AI Video Companion</h1>
        <p style={{ color: "#cbd5f5", maxWidth: "720px", margin: "0 auto" }}>
          Prototype pipeline powered by open-source AI: analyze uploaded footage, build tone-flexible scripts,
          render cloned-voice narration, synthesize ambient beds, and export aligned assets for YouCut.
        </p>
        {loadingMessage && (
          <div
            style={{
              marginTop: "12px",
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 16px",
              borderRadius: "999px",
              background: "rgba(15, 118, 110, 0.2)",
              color: "#5eead4"
            }}
          >
            <Loader2 className="spin" size={18} />
            <span>{loadingMessage}</span>
          </div>
        )}
      </header>

      <main style={{ display: "grid", gap: "24px" }}>
        <Card
          title="1 · Upload Footage"
          subtitle={uploadedName ? `Loaded: ${uploadedName}` : "Supports .mp4, .mov, .mkv"}
          actions={
            videoId && (
              <button
                disabled={isAnalyzing}
                onClick={startAnalysis}
                style={primaryButtonStyle(isAnalyzing)}
              >
                {isAnalyzing ? <Loader2 className="spin" size={16} /> : <Wand2 size={16} />} Analyze
              </button>
            )
          }
        >
          <label
            htmlFor="video-upload"
            style={{
              border: "2px dashed rgba(148, 163, 184, 0.35)",
              borderRadius: "16px",
              padding: "48px",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "12px",
              cursor: "pointer"
            }}
          >
            <Film size={48} color="#38bdf8" />
            <span>Drag & drop or click to browse</span>
            <input
              id="video-upload"
              type="file"
              accept="video/*"
              style={{ display: "none" }}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) {
                  handleUpload(file).catch(console.error);
                }
              }}
            />
          </label>
        </Card>

        <Card
          title="2 · Analysis Dashboard"
          subtitle="Scene detection · Whisper speech-to-text · keyword mining"
          actions={
            analysis?.status === "completed" && analysis.result?.transcript_path ? (
              <a href={`/api/files?path=${encodeURIComponent(analysis.result.transcript_path)}`} style={linkStyle}>
                Download transcript
              </a>
            ) : null
          }
        >
          {analysis ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <StatusBadge status={analysis.status} message={analysis.message} />
              {analysis.result?.summary && (
                <div style={summaryBoxStyle}>
                  <h3>Summary</h3>
                  <p>{analysis.result.summary}</p>
                </div>
              )}
              {!!analysis.result?.keywords?.length && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                  {analysis.result.keywords.map((keyword) => (
                    <span key={keyword} style={chipStyle}>
                      #{keyword}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <p style={{ color: "#94a3b8" }}>Upload a video to unlock analysis insights.</p>
          )}
        </Card>

        <Card
          title="3 · Script Studio"
          subtitle="Style-aware script drafting"
          actions={
            canGenerateScript && (
              <button onClick={generateScript} style={primaryButtonStyle(false)}>
                <ScriptText size={16} /> Generate script
              </button>
            )
          }
        >
          <div style={{ display: "flex", gap: "12px", marginBottom: "12px", flexWrap: "wrap" }}>
            <select value={scriptStyle} onChange={(event) => setScriptStyle(event.target.value)} style={inputStyle}>
              {SCRIPT_STYLES.map((style) => (
                <option key={style.value} value={style.value}>
                  {style.label}
                </option>
              ))}
            </select>
            <input
              value={scriptNotes}
              onChange={(event) => setScriptNotes(event.target.value)}
              placeholder="Optional notes (calls-to-action, sponsors, language)"
              style={{ ...inputStyle, flex: 1, minWidth: "240px" }}
            />
          </div>
          <textarea
            value={scriptText}
            onChange={(event) => setScriptText(event.target.value)}
            placeholder="Generated script will appear here"
            rows={10}
            style={{ ...inputStyle, resize: "vertical" }}
          />
        </Card>

        <Card
          title="4 · Voice Forge"
          subtitle="Clone voice fingerprints and render narration"
          actions={
            scriptText && selectedVoice && (
              <button onClick={synthesizeVoice} style={primaryButtonStyle(false)}>
                <Mic2 size={16} /> Synthesize narration
              </button>
            )
          }
        >
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "12px" }}>
              <input
                value={voiceName}
                onChange={(event) => setVoiceName(event.target.value)}
                placeholder="Voice label"
                style={inputStyle}
              />
              <input
                type="file"
                accept="audio/*"
                onChange={(event) => setVoiceSample(event.target.files?.[0] ?? null)}
                style={inputStyle}
              />
              <button onClick={registerVoice} style={secondaryButtonStyle}>
                Register voice
              </button>
            </div>
            <div>
              <label style={{ display: "block", marginBottom: "4px", color: "#cbd5f5" }}>Select voice</label>
              <select
                value={selectedVoice}
                onChange={(event) => setSelectedVoice(event.target.value)}
                style={inputStyle}
              >
                <option value="">Choose a voice</option>
                {voices.map((voice) => (
                  <option key={voice.voice_id} value={voice.voice_id}>
                    {voice.display_name}
                  </option>
                ))}
              </select>
            </div>
            {narrationPath && (
              <a href={`/api/files?path=${encodeURIComponent(narrationPath)}`} style={linkStyle}>
                Download narration take
              </a>
            )}
          </div>
        </Card>

        <Card
          title="5 · Audio Atmospherics"
          subtitle="Procedural music + ambiences"
          actions={
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              <button onClick={generateMusicTrack} style={secondaryButtonStyle}>
                <Music3 size={16} /> Music
              </button>
              <button onClick={generateAmbientLayer} style={secondaryButtonStyle}>
                <Waves size={16} /> Ambient
              </button>
            </div>
          }
        >
          <div style={{ display: "grid", gap: "12px" }}>
            <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
              <input value={musicPrompt} onChange={(event) => setMusicPrompt(event.target.value)} style={inputStyle} />
              <select value={musicMood} onChange={(event) => setMusicMood(event.target.value)} style={inputStyle}>
                <option value="calm">Calm</option>
                <option value="uplifting">Uplifting</option>
                <option value="suspense">Suspense</option>
                <option value="energetic">Energetic</option>
                <option value="ambient">Ambient</option>
              </select>
              <input
                type="number"
                min={5}
                max={300}
                value={musicDuration}
                onChange={(event) => setMusicDuration(parseInt(event.target.value, 10))}
                style={{ ...inputStyle, width: "120px" }}
              />
            </div>
            {musicPath && (
              <a href={`/api/files?path=${encodeURIComponent(musicPath)}`} style={linkStyle}>
                Download music track
              </a>
            )}
            <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "center" }}>
              <select
                value={ambientType}
                onChange={(event) => setAmbientType(event.target.value as typeof AMBIENT_TYPES[number])}
                style={inputStyle}
              >
                {AMBIENT_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
              <input
                type="number"
                value={ambientDuration}
                min={5}
                max={300}
                onChange={(event) => setAmbientDuration(parseInt(event.target.value, 10))}
                style={{ ...inputStyle, width: "120px" }}
              />
            </div>
            {ambientPaths.length > 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                {ambientPaths.map((path) => (
                  <a key={path} href={`/api/files?path=${encodeURIComponent(path)}`} style={linkStyle}>
                    Ambient layer · {path.split("/").slice(-1)[0]}
                  </a>
                ))}
              </div>
            )}
          </div>
        </Card>

        <Card
          title="6 · Export for YouCut"
          subtitle="Timeline JSON + assets bundle"
          actions={
            narrationPath && (
              <button onClick={buildTimeline} style={primaryButtonStyle(false)}>
                <Settings2 size={16} /> Build timeline
              </button>
            )
          }
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "12px" }}>
            <input
              id="bundle-assets"
              type="checkbox"
              checked={bundleAssets}
              onChange={(event) => setBundleAssets(event.target.checked)}
            />
            <label htmlFor="bundle-assets" style={{ color: "#cbd5f5" }}>
              Include narration/music/ambient assets in a zip bundle
            </label>
          </div>
          {timelinePath ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              <p style={{ color: "#94a3b8" }}>
                Import the JSON into YouCut, then drop the bundled audio layers. Video source stays in your library.
              </p>
              <a href={`/api/files?path=${encodeURIComponent(timelinePath)}`} style={linkStyle}>
                Download timeline JSON
              </a>
              {bundlePath && (
                <a href={`/api/files?path=${encodeURIComponent(bundlePath)}`} style={linkStyle}>
                  Download zip bundle
                </a>
              )}
            </div>
          ) : (
            <p style={{ color: "#94a3b8" }}>Generate narration, music, or ambient layers to enable export.</p>
          )}
        </Card>
      </main>
    </div>
  );
}

type VideoUploadResponse = { video_id: string; filename: string };
type TimelineResponse = { export_path: string; bundle_path?: string };

function StatusBadge({ status, message }: { status: string; message?: string | null }) {
  const colorMap: Record<string, string> = {
    pending: "rgba(148, 163, 184, 0.25)",
    processing: "rgba(56, 189, 248, 0.25)",
    completed: "rgba(34, 197, 94, 0.25)",
    failed: "rgba(244, 63, 94, 0.25)"
  };
  const labelMap: Record<string, string> = {
    pending: "Pending",
    processing: "Processing",
    completed: "Completed",
    failed: "Failed"
  };
  return (
    <div
      style={{
        display: "inline-flex",
        gap: "8px",
        alignItems: "center",
        borderRadius: "999px",
        padding: "8px 14px",
        background: colorMap[status] ?? "rgba(148, 163, 184, 0.2)",
        color: "#e2e8f0"
      }}
    >
      <Loader2 className={status === "processing" ? "spin" : ""} size={16} />
      <span>{labelMap[status] ?? status}</span>
      {message && <span style={{ color: "#94a3b8" }}>{message}</span>}
    </div>
  );
}

const primaryButtonStyle = (disabled: boolean) => ({
  display: "inline-flex",
  alignItems: "center",
  gap: "6px",
  padding: "10px 18px",
  borderRadius: "999px",
  border: "none",
  background: disabled ? "rgba(148, 163, 184, 0.4)" : "linear-gradient(135deg, #0ea5e9, #6366f1)",
  color: "white",
  fontWeight: 600,
  transition: "transform 0.15s ease",
  opacity: disabled ? 0.7 : 1
});

const secondaryButtonStyle: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: "6px",
  padding: "10px 16px",
  borderRadius: "999px",
  border: "1px solid rgba(148, 163, 184, 0.4)",
  background: "rgba(30, 41, 59, 0.6)",
  color: "#e2e8f0",
  fontWeight: 500
};

const inputStyle: React.CSSProperties = {
  background: "rgba(15, 23, 42, 0.6)",
  border: "1px solid rgba(148, 163, 184, 0.3)",
  borderRadius: "10px",
  padding: "10px 14px",
  color: "#e2e8f0",
  minWidth: "180px"
};

const linkStyle: React.CSSProperties = {
  color: "#38bdf8",
  textDecoration: "none",
  fontWeight: 500
};

const summaryBoxStyle: React.CSSProperties = {
  background: "rgba(30, 41, 59, 0.7)",
  borderRadius: "12px",
  padding: "16px",
  display: "flex",
  flexDirection: "column",
  gap: "6px"
};

const chipStyle: React.CSSProperties = {
  padding: "6px 12px",
  borderRadius: "999px",
  background: "rgba(59, 130, 246, 0.2)",
  color: "#93c5fd",
  fontSize: "0.85rem"
};
