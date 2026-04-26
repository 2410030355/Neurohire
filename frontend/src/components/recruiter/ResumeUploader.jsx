import React, { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, FileText, X, Loader2, CheckCircle, ChevronDown, ChevronUp, Briefcase } from "lucide-react";
import { API_BASE_URL } from "@/api/http";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import GlassCard from "@/components/shared/GlassCard";

export default function ResumeUploader({ onAnalysisComplete }) {
  const [files, setFiles]               = useState([]);
  const [targetRole, setTargetRole]     = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [showJD, setShowJD]             = useState(false);
  const [analyzing, setAnalyzing]       = useState(false);
  const [progress, setProgress]         = useState(0);

  const handleFileChange = (e) => {
    setFiles(prev => [...prev, ...Array.from(e.target.files)]);
  };

  const removeFile = (idx) => setFiles(prev => prev.filter((_, i) => i !== idx));

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    const dropped = Array.from(e.dataTransfer.files).filter(
      f => f.type === "application/pdf" || f.name.endsWith(".docx")
    );
    setFiles(prev => [...prev, ...dropped]);
  }, []);

  const analyzeResumes = async () => {
    if (!files.length)        { toast.error("Please upload at least one resume"); return; }
    if (!targetRole.trim())   { toast.error("Please specify a target role"); return; }

    setAnalyzing(true);
    setProgress(5);

    try {
      const results = [];
      for (let i = 0; i < files.length; i++) {
        const formData = new FormData();
        formData.append("resume", files[i]);
        formData.append("name", files[i].name);
        formData.append("target_role", targetRole);
        if (jobDescription.trim()) {
          formData.append("job_description", jobDescription.trim());
        }

        console.log('[ResumeUploader] uploading to:', `${API_BASE_URL}/api/upload-resume/`);

        const res = await fetch(`${API_BASE_URL}/api/upload-resume/`, {
          method: "POST",
          // NO credentials:include — csrf_exempt handles this
          // NO Content-Type header — browser sets multipart boundary automatically
          body: formData,
        });

        console.log('[ResumeUploader] response status:', res.status);
        const rawText = await res.text();
        console.log('[ResumeUploader] raw response:', rawText.slice(0, 500));

        if (!res.ok) {
          let errMsg = `Server error ${res.status}`;
          try { errMsg = JSON.parse(rawText)?.error || errMsg; } catch {}
          throw new Error(errMsg);
        }

        let data;
        try { data = JSON.parse(rawText); }
        catch { throw new Error('Server returned invalid JSON'); }

        results.push(data);
        setProgress(Math.round(((i + 1) / files.length) * 100));
      }

      toast.success(`${results.length} resume(s) analyzed successfully`);
      onAnalysisComplete?.(results);
      setFiles([]);
    } catch (err) {
      console.error('[ResumeUploader] ERROR:', err);
      toast.error(err.message || "Analysis failed — check console (F12)");
    } finally {
      setAnalyzing(false);
    }
  };

  const jdWordCount = jobDescription.trim().split(/\s+/).filter(Boolean).length;

  return (
    <GlassCard className="mb-8">
      <div className="mb-6">
        <h2 className="text-xl font-bold" style={{ color: "var(--nh-text)" }}>
          Resume Analysis
        </h2>
        <p className="text-sm mt-1" style={{ color: "var(--nh-text-secondary)" }}>
          Upload resumes and optionally paste a job description for precise matching
        </p>
      </div>

      {/* ── Target Role ── */}
      <div className="mb-4">
        <Label className="text-sm font-medium mb-1.5 block" style={{ color: "var(--nh-text)" }}>
          Target Role <span style={{ color: "var(--nh-danger)" }}>*</span>
        </Label>
        <Input
          value={targetRole}
          onChange={e => setTargetRole(e.target.value)}
          placeholder="e.g. Senior Frontend Engineer"
          className="rounded-xl border"
          style={{ borderColor: "var(--nh-border)", background: "var(--nh-bg)", color: "var(--nh-text)" }}
        />
      </div>

      {/* ── Job Description (collapsible) — paper §IV.E ── */}
      <div className="mb-4">
        <button
          onClick={() => setShowJD(v => !v)}
          className="w-full flex items-center justify-between px-4 py-3 rounded-xl transition-all text-left"
          style={{
            background: showJD ? "var(--nh-primary-light)" : "var(--nh-bg)",
            border: `1px solid ${showJD ? "rgba(45,212,191,0.4)" : "var(--nh-border)"}`,
          }}
        >
          <div className="flex items-center gap-2">
            <Briefcase className="w-4 h-4" style={{ color: "var(--nh-primary)" }} />
            <span className="text-sm font-medium" style={{ color: "var(--nh-text)" }}>
              Paste Job Description
            </span>
            <span className="text-xs px-2 py-0.5 rounded-full"
              style={{ background: "var(--nh-secondary-light)", color: "var(--nh-secondary)" }}>
              Recommended — paper §IV.E
            </span>
          </div>
          <div className="flex items-center gap-2">
            {jdWordCount > 0 && (
              <span className="text-xs" style={{ color: "var(--nh-primary)" }}>
                {jdWordCount} words
              </span>
            )}
            {showJD
              ? <ChevronUp className="w-4 h-4" style={{ color: "var(--nh-text-secondary)" }} />
              : <ChevronDown className="w-4 h-4" style={{ color: "var(--nh-text-secondary)" }} />
            }
          </div>
        </button>

        <AnimatePresence>
          {showJD && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.2 }}
            >
              <textarea
                value={jobDescription}
                onChange={e => setJobDescription(e.target.value)}
                placeholder="Paste the full job description here…&#10;&#10;The AI will match candidates against this JD using TF-IDF semantic similarity (paper §IV.E), giving a much more accurate role match score than just the role name."
                rows={7}
                className="w-full mt-2 px-4 py-3 rounded-xl text-sm resize-none transition-all"
                style={{
                  background: "var(--nh-bg)",
                  border: "1px solid var(--nh-border)",
                  color: "var(--nh-text)",
                  lineHeight: "1.6",
                }}
              />
              {jdWordCount > 0 && jdWordCount < 30 && (
                <p className="text-xs mt-1 px-1" style={{ color: "var(--nh-warning)" }}>
                  ⚠ Short JD — paste more content for better matching accuracy
                </p>
              )}
              {jdWordCount >= 30 && (
                <p className="text-xs mt-1 px-1" style={{ color: "var(--nh-success)" }}>
                  ✓ Good JD length — role match scores will use semantic analysis
                </p>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ── Drop zone ── */}
      <div
        onDrop={handleDrop}
        onDragOver={e => e.preventDefault()}
        className="border-2 border-dashed rounded-2xl p-8 text-center transition-colors"
        style={{ borderColor: "var(--nh-border)" }}
      >
        <Upload className="w-10 h-10 mx-auto mb-3" style={{ color: "var(--nh-text-secondary)" }} />
        <p className="font-medium mb-1" style={{ color: "var(--nh-text)" }}>
          Drop resumes here or click to browse
        </p>
        <p className="text-sm mb-4" style={{ color: "var(--nh-text-secondary)" }}>
          Supports PDF and DOCX · Batch upload supported
        </p>
        <label>
          <input type="file" multiple accept=".pdf,.docx" onChange={handleFileChange} className="hidden" />
          <Button variant="outline" className="rounded-xl cursor-pointer" asChild>
            <span>Browse Files</span>
          </Button>
        </label>
      </div>

      {/* ── File list ── */}
      <AnimatePresence>
        {files.length > 0 && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }} className="mt-4 space-y-2">
            {files.map((file, i) => (
              <motion.div key={i} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="flex items-center gap-3 p-3 rounded-xl"
                style={{ background: "var(--nh-bg)", border: "1px solid var(--nh-border)" }}>
                <FileText className="w-5 h-5 flex-shrink-0" style={{ color: "var(--nh-primary)" }} />
                <span className="text-sm flex-1 truncate" style={{ color: "var(--nh-text)" }}>{file.name}</span>
                <span className="text-xs" style={{ color: "var(--nh-text-secondary)" }}>
                  {(file.size / 1024).toFixed(0)} KB
                </span>
                <button onClick={() => removeFile(i)} className="p-1 hover:opacity-70">
                  <X className="w-4 h-4" style={{ color: "var(--nh-text-secondary)" }} />
                </button>
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Analyze button ── */}
      <div className="mt-4">
        {analyzing ? (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" style={{ color: "var(--nh-primary)" }} />
              <span className="text-sm font-medium" style={{ color: "var(--nh-text)" }}>
                {jobDescription.trim() ? "Matching against JD…" : "Analyzing…"} {progress}%
              </span>
            </div>
            <div className="w-full h-2 rounded-full" style={{ background: "var(--nh-border)" }}>
              <motion.div className="h-2 rounded-full gradient-bg" animate={{ width: `${progress}%` }} />
            </div>
          </div>
        ) : (
          <Button
            onClick={analyzeResumes}
            disabled={!files.length}
            className="gradient-bg text-white rounded-xl w-full disabled:opacity-50"
          >
            <CheckCircle className="w-4 h-4 mr-2" />
            Analyze {files.length || ""} Resume{files.length !== 1 ? "s" : ""}
            {jobDescription.trim() ? " against JD" : ""}
          </Button>
        )}
      </div>
    </GlassCard>
  );
}