import React, { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, FileText, X, Loader2, CheckCircle } from "lucide-react";
import { API_BASE_URL } from "@/api/http";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import GlassCard from "@/components/shared/GlassCard";

export default function ResumeUploader({ onAnalysisComplete }) {
  const [files, setFiles] = useState([]);
  const [targetRole, setTargetRole] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [analysisResults, setAnalysisResults] = useState([]);

  // =============================
  // File handlers
  // =============================

  const handleFileChange = (e) => {
    const newFiles = Array.from(e.target.files);
    setFiles((prev) => [...prev, ...newFiles]);
  };

  const removeFile = (idx) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    const droppedFiles = Array.from(e.dataTransfer.files).filter(
      (f) => f.type === "application/pdf" || f.name.endsWith(".docx")
    );
    setFiles((prev) => [...prev, ...droppedFiles]);
  }, []);

  // =============================
  // 🔥 MAIN — Django upload
  // =============================

  const analyzeResumes = async () => {
    if (!files.length) {
      toast.error("Please upload at least one resume");
      return;
    }
    if (!targetRole.trim()) {
      toast.error("Please specify a target role");
      return;
    }

    setAnalyzing(true);
    setProgress(5);
    setAnalysisResults([]);

    try {
      const results = [];

      for (let i = 0; i < files.length; i++) {
        const formData = new FormData();
        formData.append("resume", files[i]);
        formData.append("name", files[i].name);
        formData.append("target_role", targetRole);

        const res = await fetch(`${API_BASE_URL}/api/upload-resume/`, {
          method: "POST",
          credentials: "include",   // ✅ required for session auth
          body: formData,
          // ⚠️ Do NOT set Content-Type — browser sets it with boundary for FormData
        });

        if (res.status === 403) {
          throw new Error("Access denied. Make sure you are logged in as a recruiter.");
        }

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.error || `Upload failed (${res.status})`);
        }

        const data = await res.json();
        results.push(data);
        setProgress(Math.round(((i + 1) / files.length) * 100));
      }

      toast.success(`${results.length} resume(s) analyzed successfully`);
      setAnalysisResults(results);
      onAnalysisComplete?.(results);  // ✅ triggers dashboard refresh → shows CandidateCards with buttons
      setFiles([]);
    } catch (err) {
      console.error("❌ ANALYSIS ERROR:", err);
      toast.error(err.message || "Analysis failed — check console");
    } finally {
      setAnalyzing(false);
    }
  };

  // =============================
  // UI
  // =============================

  return (
    <GlassCard className="mb-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold" style={{ color: "var(--nh-text)" }}>
            Resume Analysis
          </h2>
          <p className="text-sm mt-1" style={{ color: "var(--nh-text-secondary)" }}>
            Upload resumes to analyze candidates with AI
          </p>
        </div>
      </div>

      {/* Target role */}
      <div className="mb-4">
        <Label className="text-sm font-medium mb-1.5 block" style={{ color: "var(--nh-text)" }}>
          Target Role
        </Label>
        <Input
          value={targetRole}
          onChange={(e) => setTargetRole(e.target.value)}
          placeholder="e.g. Senior Frontend Engineer"
          className="rounded-xl border"
          style={{ borderColor: "var(--nh-border)", background: "var(--nh-card)", color: "var(--nh-text)" }}
        />
      </div>

      {/* Drop zone */}
      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        className="border-2 border-dashed rounded-2xl p-8 text-center transition-colors hover:border-indigo-300"
        style={{ borderColor: "var(--nh-border)" }}
      >
        <Upload className="w-10 h-10 mx-auto mb-3" style={{ color: "var(--nh-text-secondary)" }} />
        <p className="font-medium mb-1" style={{ color: "var(--nh-text)" }}>
          Drop resumes here or click to browse
        </p>
        <p className="text-sm mb-4" style={{ color: "var(--nh-text-secondary)" }}>
          Supports PDF and DOCX • Batch upload supported
        </p>
        <label>
          <input type="file" multiple accept=".pdf,.docx" onChange={handleFileChange} className="hidden" />
          <Button variant="outline" className="rounded-xl cursor-pointer" asChild>
            <span>Browse Files</span>
          </Button>
        </label>
      </div>

      {/* File list */}
      <AnimatePresence>
        {files.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-4 space-y-2"
          >
            {files.map((file, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="flex items-center gap-3 p-3 rounded-xl"
                style={{ background: "var(--nh-bg)" }}
              >
                <FileText className="w-5 h-5 flex-shrink-0" style={{ color: "var(--nh-primary)" }} />
                <span className="text-sm flex-1 truncate" style={{ color: "var(--nh-text)" }}>
                  {file.name}
                </span>
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

      {/* Analyze button */}
      <div className="mt-4">
        {analyzing ? (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" style={{ color: "var(--nh-primary)" }} />
              <span className="text-sm font-medium" style={{ color: "var(--nh-text)" }}>
                Analyzing... {progress}%
              </span>
            </div>
            <div className="w-full h-2 rounded-full" style={{ background: "var(--nh-border)" }}>
              <motion.div
                className="h-2 rounded-full gradient-bg"
                animate={{ width: `${progress}%` }}
              />
            </div>
          </div>
        ) : (
          <Button
            onClick={analyzeResumes}
            disabled={!files.length}
            className="gradient-bg text-white rounded-xl w-full disabled:opacity-50"
          >
            <CheckCircle className="w-4 h-4 mr-2" />
            Analyze {files.length > 0 ? `${files.length} Resume${files.length > 1 ? "s" : ""}` : "Resumes"}
          </Button>
        )}
      </div>

      {/* ✅ Success notice — full candidate cards with Schedule/Waitlist shown below */}
      <AnimatePresence>
        {analysisResults.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-4 p-4 rounded-xl flex items-center gap-3"
            style={{ background: 'var(--nh-primary-light)', border: '1px solid var(--nh-border)' }}
          >
            <CheckCircle className="w-5 h-5 flex-shrink-0" style={{ color: 'var(--nh-primary)' }} />
            <p className="text-sm font-medium" style={{ color: 'var(--nh-primary)' }}>
              {analysisResults.length} resume{analysisResults.length > 1 ? 's' : ''} analyzed successfully — scroll down to see candidate cards with Schedule &amp; Waitlist options.
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </GlassCard>
  );
}