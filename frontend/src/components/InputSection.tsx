import React, { useState, useRef } from 'react';
import { Sparkles, FileText, Upload, Globe, Users, Loader2 } from 'lucide-react';
import { GenerateRequest } from '../types';
import { uploadPdf } from '../api';

interface InputSectionProps {
  onGenerate: (req: GenerateRequest) => void;
  isGenerating: boolean;
}

const PRESET_TOPICS = [
  "Newton's Second Law (F = ma) for Class 10 students",
  "Photosynthesis and Light Reactions for High School",
  "Binary Search Algorithm & O(log n) Complexity",
  "Ohm's Law: Voltage, Current, and Resistance (V = IR)",
];

const DEFAULT_NOTES = `Newton's Second Law of Motion states that the rate of change of momentum of an object is directly proportional to the applied unbalanced force and takes place in the direction of the force.
Mathematically: F = m * a.
Where:
- F is the net force measured in Newtons (N)
- m is the mass in kilograms (kg)
- a is the acceleration in m/s^2.
For a given mass, a larger force produces greater acceleration. Conversely, a heavier mass experiences less acceleration for the same force.`;

export const InputSection: React.FC<InputSectionProps> = ({ onGenerate, isGenerating }) => {
  const [topic, setTopic] = useState("Newton's Second Law (F = ma) for Class 10 students");
  const [activeTab, setActiveTab] = useState<'text' | 'pdf'>('text');
  const [inputText, setInputText] = useState(DEFAULT_NOTES);
  const [pdfFilename, setPdfFilename] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [language, setLanguage] = useState<'en' | 'hi'>('en');
  const [audience, setAudience] = useState('Class 10 students');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setIsUploading(true);
      const res = await uploadPdf(file);
      setPdfFilename(res.filename);
    } catch (err: any) {
      alert(`Upload failed: ${err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) {
      alert("Please enter a topic title.");
      return;
    }

    onGenerate({
      topic,
      input_text: activeTab === 'text' ? inputText : undefined,
      pdf_filename: activeTab === 'pdf' ? (pdfFilename || undefined) : undefined,
      language,
      target_audience: audience,
    });
  };

  return (
    <div className="studio-card">
      <h2 className="card-title">
        <Sparkles className="text-sky-400" size={20} />
        Generate New Explainer Video
      </h2>
      <p className="card-desc">Provide your lecture notes, textbook excerpt, or topic to automatically synthesize an animation.</p>

      <form onSubmit={handleSubmit}>
        {/* Topic Input */}
        <div className="form-group">
          <label className="form-label">Topic / Concept Title</label>
          <input
            type="text"
            className="form-input"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. Newton's Second Law..."
            disabled={isGenerating}
            required
          />
          <div className="quick-pills">
            {PRESET_TOPICS.map((preset, idx) => (
              <button
                key={idx}
                type="button"
                className="pill-btn"
                onClick={() => setTopic(preset)}
                disabled={isGenerating}
              >
                {preset.split('(')[0].trim()}
              </button>
            ))}
          </div>
        </div>

        {/* Input Method Switcher */}
        <div className="tab-switcher">
          <button
            type="button"
            className={`tab-btn ${activeTab === 'text' ? 'active' : ''}`}
            onClick={() => setActiveTab('text')}
          >
            <FileText size={16} />
            Paste Notes / Text
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === 'pdf' ? 'active' : ''}`}
            onClick={() => setActiveTab('pdf')}
          >
            <Upload size={16} />
            Upload PDF Document
          </button>
        </div>

        {/* Text Area */}
        {activeTab === 'text' && (
          <div className="form-group">
            <label className="form-label">Source Notes & Explanations</label>
            <textarea
              className="form-textarea"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Paste study material here..."
              disabled={isGenerating}
            />
          </div>
        )}

        {/* PDF Upload */}
        {activeTab === 'pdf' && (
          <div className="form-group">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              accept=".pdf"
              style={{ display: 'none' }}
            />
            <div
              className="dropzone"
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="dropzone-icon" />
              <p style={{ fontWeight: 600, marginBottom: '0.2rem' }}>
                {isUploading ? 'Uploading & Extracting PDF...' : (pdfFilename ? `Selected: ${pdfFilename}` : 'Click to Upload Chapter PDF')}
              </p>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>PyMuPDF will automatically extract and clean all chapter text</p>
            </div>
          </div>
        )}

        {/* Settings Grid (Language & Audience) */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
          <div>
            <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Globe size={14} /> Narration Language
            </label>
            <select
              className="form-select"
              value={language}
              onChange={(e) => setLanguage(e.target.value as 'en' | 'hi')}
              disabled={isGenerating}
            >
              <option value="en">English (US - Aria Neural)</option>
              <option value="hi">Hindi (IN - Swara Neural)</option>
            </select>
          </div>

          <div>
            <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Users size={14} /> Target Audience
            </label>
            <input
              type="text"
              className="form-input"
              value={audience}
              onChange={(e) => setAudience(e.target.value)}
              placeholder="e.g. Class 10 students"
              disabled={isGenerating}
            />
          </div>
        </div>

        {/* Action Button */}
        <button
          type="submit"
          className="btn-primary"
          disabled={isGenerating || isUploading}
        >
          {isGenerating ? (
            <>
              <Loader2 className="animate-spin" size={18} />
              Generating Autonomous Explainer...
            </>
          ) : (
            <>
              <Sparkles size={18} />
              Generate Explainer Video
            </>
          )}
        </button>
      </form>
    </div>
  );
};
