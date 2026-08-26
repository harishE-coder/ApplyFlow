import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import confetti from 'canvas-confetti';
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Calendar,
  Building2,
  Trash2,
  Check,
  RefreshCw,
  Edit3,
  SkipForward,
  Layers,
  ArrowRight,
  ShieldAlert,
  Sparkles,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { BrandedLoader } from '@/components/ui/BrandedLoader';
import { useToast } from '@/components/ui/Toast';
import { useAuth } from '@/features/auth/AuthContext';
import api from '@/services/api';
import { formatDate, cn } from '@/utils/cn';

export function UploadPage() {
  const { user, isEmployee } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { success, error: toastError, warning } = useToast();

  const fileInputRef = useRef(null);

  // Form State
  const [assignedClients, setAssignedClients] = useState([]);
  const [selectedClientId, setSelectedClientId] = useState('');
  const [resumeDate, setResumeDate] = useState(new Date().toISOString().split('T')[0]); // Default Today
  const [loadingClients, setLoadingClients] = useState(true);

  // Ingestion Queue State
  const [queue, setQueue] = useState([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isCheckingDuplicates, setIsCheckingDuplicates] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0); // 0 to 100
  const [uploadProgressCount, setUploadProgressCount] = useState({ current: 0, total: 0 });

  // Success State
  const [uploadSuccessSummary, setUploadSuccessSummary] = useState(null);

  // Core Rule: Only employees can upload. Redirect others.
  useEffect(() => {
    if (user && user.role !== 'employee') {
      toastError('Permission Denied', 'Only recruiters can upload resumes. Administrators and Clients cannot upload.');
      navigate('/dashboard');
    }
  }, [user, navigate]);

  // Load only assigned clients
  useEffect(() => {
    const fetchClients = async () => {
      setLoadingClients(true);
      try {
        const res = await api.get('/clients');
        const list = res.data || [];
        setAssignedClients(list);
        if (list.length > 0 && !selectedClientId) {
          setSelectedClientId(list[0].id);
        }
      } catch (err) {
        toastError('Error', 'Failed to load assigned service clients');
      } finally {
        setLoadingClients(false);
      }
    };
    fetchClients();
  }, []);

  // Handle location state initial files if redirected from dashboard
  useEffect(() => {
    if (location.state?.initialFiles) {
      handleFilesSelected(location.state.initialFiles);
    }
    if (location.state?.client_id) {
      setSelectedClientId(location.state.client_id);
    }
  }, [location.state]);

  // Client-side Filename Parser matching ApplyFlow standard:
  // e.g. TCS_JavaDeveloper_RES101.pdf or Amazon_Frontend_RahulSharma.pdf
  const parseFilename = (filename) => {
    const stem = filename.replace(/\.[^/.]+$/, '').trim();
    const cleaned = stem.replace(/[\s\-]+/g, '_');
    const parts = cleaned.split('_').filter(Boolean);

    if (parts.length >= 3) {
      const company = parts[0];
      const roleParts = parts.slice(1, -1);
      const role = roleParts.join(' ') || 'Software Engineer';
      const lastPart = parts[parts.length - 1];

      let resume_id_tag = null;
      let candidate_name = lastPart;

      const idMatch = lastPart.match(/(RES\d+|Resume\d+|\d+)/i);
      if (idMatch && idMatch[0].length >= 3) {
        resume_id_tag = idMatch[0].toUpperCase();
        candidate_name = `Candidate ${resume_id_tag}`;
      } else {
        // Space out camel case if needed
        candidate_name = lastPart.replace(/([a-z])([A-Z])/g, '$1 $2');
      }

      return {
        company: company.length <= 4 ? company.toUpperCase() : company.charAt(0).toUpperCase() + company.slice(1),
        role: role.charAt(0).toUpperCase() + role.slice(1),
        resume_id_tag,
        candidate_name: candidate_name.charAt(0).toUpperCase() + candidate_name.slice(1),
        status: 'valid', // 'valid' | 'duplicate' | 'needs_review'
        error: null,
      };
    } else if (parts.length === 2) {
      return {
        company: parts[0].charAt(0).toUpperCase() + parts[0].slice(1),
        role: parts[1].replace(/_/g, ' '),
        resume_id_tag: null,
        candidate_name: 'Candidate Name',
        status: 'needs_review',
        error: 'Missing candidate name or ID in filename',
      };
    }

    return {
      company: 'General',
      role: stem.replace(/_/g, ' '),
      resume_id_tag: null,
      candidate_name: stem.replace(/_/g, ' '),
      status: 'needs_review',
      error: 'Format should be Company_Role_Candidate.pdf',
    };
  };

  // Handle files selection
  const handleFilesSelected = (files) => {
    const pdfFiles = Array.from(files).filter(
      (file) => file.name.toLowerCase().endsWith('.pdf') || file.type === 'application/pdf'
    );

    if (pdfFiles.length === 0) {
      warning('PDF Only', 'Only PDF resume files are accepted.');
      return;
    }

    const newQueueItems = pdfFiles.map((file, idx) => {
      const parsed = parseFilename(file.name);
      return {
        id: `${file.name}-${Date.now()}-${idx}`,
        file,
        filename: file.name,
        size: (file.size / 1024).toFixed(1) + ' KB',
        company: parsed.company,
        role: parsed.role,
        resume_id_tag: parsed.resume_id_tag || '',
        candidate_name: parsed.candidate_name,
        status: parsed.status, // 'valid' | 'duplicate' | 'needs_review'
        error: parsed.error,
        isDuplicate: false,
        duplicateInfo: null,
        isEditing: false,
      };
    });

    setQueue((prev) => {
      const combined = [...prev, ...newQueueItems].slice(0, 200); // 1-200 files
      if (selectedClientId) {
        runDuplicateCheck(combined, selectedClientId);
      }
      return combined;
    });

    setUploadSuccessSummary(null);
  };

  // Run Duplicate Detection via Backend API: POST /api/resumes/check-duplicates
  const runDuplicateCheck = async (itemsToCheck, cId) => {
    if (!cId || itemsToCheck.length === 0) return;
    setIsCheckingDuplicates(true);
    try {
      const payload = {
        client_id: cId,
        items: itemsToCheck.map((it) => ({
          filename: it.filename,
          company: it.company,
          candidate_name: it.candidate_name,
          resume_id_tag: it.resume_id_tag || null,
        })),
      };

      const res = await api.post('/resumes/check-duplicates', payload);
      const results = res.data?.results || [];

      setQueue((prev) =>
        prev.map((item) => {
          const match = results.find((r) => r.filename === item.filename);
          if (match?.is_duplicate) {
            return {
              ...item,
              status: 'duplicate',
              isDuplicate: true,
              duplicateInfo: match,
            };
          }
          if (item.status === 'duplicate' && !match?.is_duplicate) {
            return {
              ...item,
              status: item.error ? 'needs_review' : 'valid',
              isDuplicate: false,
              duplicateInfo: null,
            };
          }
          return item;
        })
      );
    } catch (err) {
      console.warn('Duplicate check warning:', err);
    } finally {
      setIsCheckingDuplicates(false);
    }
  };

  // Re-run duplicate check if selectedClientId changes
  useEffect(() => {
    if (selectedClientId && queue.length > 0) {
      runDuplicateCheck(queue, selectedClientId);
    }
  }, [selectedClientId]);

  // Inline row updates
  const handleUpdateRow = (id, field, value) => {
    setQueue((prev) =>
      prev.map((it) => {
        if (it.id === id) {
          const updated = { ...it, [field]: value };
          // If valid inputs provided, clear needs_review
          if (updated.company && updated.role && updated.candidate_name && updated.status === 'needs_review') {
            updated.status = 'valid';
            updated.error = null;
          }
          return updated;
        }
        return it;
      })
    );
  };

  const handleRemoveRow = (id) => {
    setQueue((prev) => prev.filter((it) => it.id !== id));
  };

  // Skip duplicates helper
  const handleSkipDuplicates = () => {
    setQueue((prev) => prev.filter((it) => it.status !== 'duplicate'));
    success('Duplicates Skipped', 'Removed duplicate files from current upload batch.');
  };

  // Perform upload
  const handleCommitUpload = async (mode = 'all_valid') => {
    if (!selectedClientId) {
      toastError('Required', 'Please select an assigned Service Client.');
      return;
    }

    let filesToUpload = queue;
    if (mode === 'skip_duplicates') {
      filesToUpload = queue.filter((it) => it.status !== 'duplicate');
    }

    if (filesToUpload.length === 0) {
      toastError('No Files', 'No valid files selected for upload.');
      return;
    }

    setIsUploading(true);
    setUploadProgress(15);
    setUploadProgressCount({ current: 0, total: filesToUpload.length });

    const formData = new FormData();
    formData.append('client_id', selectedClientId);
    const validDate = resumeDate && resumeDate.trim() ? resumeDate.trim() : new Date().toISOString().split('T')[0];
    formData.append('resume_date', validDate);

    filesToUpload.forEach((item) => {
      if (item.file) {
        formData.append('files', item.file);
      }
    });

    let progressInterval;
    try {
        progressInterval = setInterval(() => {
          setUploadProgress((prev) => {
            if (prev >= 90) return prev;
            return prev + 15;
          });
          setUploadProgressCount((prev) => ({
            current: Math.min(prev.current + 5, filesToUpload.length),
            total: filesToUpload.length,
          }));
        }, 300);

        const res = await api.post('/resumes/upload', formData, {
          headers: {
            'Content-Type': undefined,
          },
        });

        clearInterval(progressInterval);
        setUploadProgress(100);
        setUploadProgressCount({ current: filesToUpload.length, total: filesToUpload.length });

        const uploaded = res.data?.saved_count ?? filesToUpload.length;
        const dupCount = queue.filter((it) => it.status === 'duplicate').length;
        const reviewedCount = queue.filter((it) => it.status === 'needs_review').length;

        setUploadSuccessSummary({
          uploaded: uploaded || 0,
          duplicates: dupCount || 0,
          reviewed: reviewedCount || 0,
        });

        setQueue([]);

        // Trigger immediate dashboard update event across the application
        window.dispatchEvent(new CustomEvent('resume-uploaded', { detail: { count: uploaded } }));
        window.dispatchEvent(new CustomEvent('application-created', { detail: { count: uploaded } }));
        window.dispatchEvent(new CustomEvent('application-updated', { detail: { count: uploaded } }));

        // Confetti celebration (safely guarded)
        try {
          if (typeof confetti === 'function') {
            confetti({
              particleCount: 80,
              spread: 70,
              origin: { y: 0.6 },
              colors: ['#0D6EFD', '#FF8A00', '#16A34A'],
            });
          }
        } catch (e) {
          // Ignore confetti error
        }

        success('Batch Ingested', `Successfully uploaded ${uploaded} candidate resumes.`);
      } catch (err) {
        if (progressInterval) clearInterval(progressInterval);
        const errorMsg =
          err.response?.data?.detail ||
          err.response?.data?.message ||
          err.message ||
          'Failed to upload batch.';
        toastError('Upload Failed', errorMsg);
      } finally {
        if (progressInterval) clearInterval(progressInterval);
        setIsUploading(false);
      }
  };

  const duplicateCount = queue.filter((it) => it.status === 'duplicate').length;
  const reviewCount = queue.filter((it) => it.status === 'needs_review').length;
  const validCount = queue.filter((it) => it.status === 'valid').length;

  if (loadingClients) {
    return <BrandedLoader size="lg" label="Loading Recruiter Upload Studio..." />;
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-h1 font-extrabold text-[#081226] tracking-tight">
              Upload Resumes
            </h1>
            <span className="text-caption font-bold px-2.5 py-0.5 rounded-full bg-[#FFF7ED] text-[#FF8A00] border border-[#FFEDD5]">
              Recruiter Ingestion Only
            </span>
          </div>
          <p className="text-small text-[#64748B] mt-1">
            Batch PDF ingestion with automatic entity extraction, pre-commit review, and duplicate detection.
          </p>
        </div>

        <Button
          variant="outline"
          size="md"
          onClick={() => navigate('/candidates')}
        >
          Candidate Workspace →
        </Button>
      </div>

      {/* Upload Configuration Form (1. Assigned Client, 2. Resume Date) */}
      <div className="bg-white p-6 rounded-3xl border border-[#E2E8F0] shadow-card space-y-5">
        <h3 className="text-small font-bold uppercase tracking-wider text-[#64748B] flex items-center gap-2">
          <Building2 className="w-4 h-4 text-[#0D6EFD]" />
          Batch Ingestion Settings
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          {/* 1. Service Client Dropdown (Show ONLY assigned clients!) */}
          <div>
            <label className="text-small font-semibold text-[#081226] block mb-1.5">
              Service Client <span className="text-[#EF4444]">*</span>
            </label>
            <select
              value={selectedClientId}
              onChange={(e) => setSelectedClientId(e.target.value)}
              className="w-full h-[48px] px-4 rounded-xl text-small font-medium bg-[#F8FAFC] text-[#081226] border border-[#E2E8F0] shadow-xs hover:border-[#CBD5E1] focus:outline-none focus:border-[#0D6EFD]"
              required
            >
              <option value="">Select Assigned Service Client...</option>
              {assignedClients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.company_name} ({c.contact_person || 'Client Account'})
                </option>
              ))}
            </select>
            <p className="text-caption text-[#64748B] mt-1">
              Showing only your assigned Service Clients.
            </p>
          </div>

          {/* 2. Resume Date (Batch date picker, default today, inherited by every resume) */}
          <div>
            <label className="text-small font-semibold text-[#081226] block mb-1.5">
              Resume Date (Batch Inherited) <span className="text-[#EF4444]">*</span>
            </label>
            <div className="relative">
              <input
                type="date"
                value={resumeDate}
                onChange={(e) => setResumeDate(e.target.value)}
                className="w-full h-[48px] px-4 rounded-xl text-small font-medium bg-[#F8FAFC] text-[#081226] border border-[#E2E8F0] shadow-xs hover:border-[#CBD5E1] focus:outline-none focus:border-[#0D6EFD]"
              />
            </div>
            <p className="text-caption text-[#64748B] mt-1">
              Every resume in this batch will inherit this date.
            </p>
          </div>
        </div>
      </div>

      {/* 3. Drag & Drop Upload Surface (Multi-file, PDF only, 1-200 files) */}
      <div className="bg-white p-6 rounded-3xl border border-[#E2E8F0] shadow-card">
        <h3 className="text-small font-bold uppercase tracking-wider text-[#64748B] mb-4 flex items-center gap-2">
          <UploadCloud className="w-4 h-4 text-[#0D6EFD]" />
          Drop PDF Resumes (1 – 200 files)
        </h3>

        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragOver(true);
          }}
          onDragLeave={(e) => {
            e.preventDefault();
            setIsDragOver(false);
          }}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragOver(false);
            if (e.dataTransfer.files?.length > 0) {
              handleFilesSelected(e.dataTransfer.files);
            }
          }}
          onClick={() => fileInputRef.current?.click()}
          className={cn(
            'p-10 rounded-2xl border-2 border-dashed transition-all duration-150 flex flex-col items-center justify-center text-center cursor-pointer select-none',
            isDragOver
              ? 'border-[#0D6EFD] bg-[#EFF6FF]'
              : 'border-[#CBD5E1] bg-[#F8FAFC]/70 hover:bg-[#F8FAFC] hover:border-[#94A3B8]'
          )}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,application/pdf"
            onChange={(e) => {
              if (e.target.files?.length > 0) {
                handleFilesSelected(e.target.files);
              }
            }}
            className="hidden"
          />

          <div className="w-16 h-16 rounded-2xl bg-[#EFF6FF] text-[#0D6EFD] flex items-center justify-center mb-4 border border-[#BFDBFE]">
            <UploadCloud className="w-8 h-8" />
          </div>

          <h4 className="text-h3 font-bold text-[#081226]">
            Drag & drop PDF resumes, or <span className="text-[#0D6EFD] underline underline-offset-4">browse</span>
          </h4>

          <p className="text-small text-[#64748B] max-w-md mt-1 mb-4">
            Supports batch ingestion up to 200 PDF files. Standard filename format like <code className="font-mono text-caption text-[#081226] bg-[#E2E8F0] px-1 py-0.5 rounded">TCS_JavaDeveloper_RES101.pdf</code> automatically extracts company and role.
          </p>

          <Button
            variant="primary"
            size="md"
            icon={FileText}
            onClick={(e) => {
              e.stopPropagation();
              fileInputRef.current?.click();
            }}
          >
            Choose PDF Files
          </Button>

          {queue.length > 0 && (
            <p className="text-caption font-bold text-[#0D6EFD] mt-4">
              {queue.length} files currently in staging queue
            </p>
          )}
        </div>
      </div>

      {/* Pre-Commit Batch Summary Table & Inline Review */}
      {queue.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-3xl border border-[#E2E8F0] shadow-card overflow-hidden space-y-0"
        >
          {/* Header & Status Badges */}
          <div className="p-6 bg-[#F8FAFC] border-b border-[#E2E8F0] flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2.5">
                <h3 className="text-h3 font-bold text-[#081226]">
                  Pre-Commit Batch Summary ({queue.length} Files)
                </h3>
                {isCheckingDuplicates && (
                  <span className="text-[11px] text-[#FF8A00] font-semibold flex items-center gap-1 animate-pulse">
                    <RefreshCw className="w-3 h-3 animate-spin" />
                    Checking duplicates...
                  </span>
                )}
              </div>
              <p className="text-caption text-[#64748B] mt-0.5">
                Verify parsed entities before saving to database. You can edit any field directly inline.
              </p>
            </div>

            {/* Status Breakdown Pills */}
            <div className="flex items-center gap-2 shrink-0">
              <span className="px-2.5 py-1 rounded-lg text-caption font-bold bg-[#F0FDF4] text-[#16A34A] border border-[#BBF7D0]">
                ✅ {validCount} Valid
              </span>
              {duplicateCount > 0 && (
                <span className="px-2.5 py-1 rounded-lg text-caption font-bold bg-[#FFFBEB] text-[#D97706] border border-[#FDE68A]">
                  ⚠️ {duplicateCount} Duplicates
                </span>
              )}
              {reviewCount > 0 && (
                <span className="px-2.5 py-1 rounded-lg text-caption font-bold bg-[#FEF2F2] text-[#EF4444] border border-[#FECACA]">
                  ❌ {reviewCount} Need Review
                </span>
              )}
            </div>
          </div>

          {/* Review Table with Inline Inputs */}
          <div className="overflow-x-auto max-h-[420px] overflow-y-auto">
            <table className="w-full text-left text-small border-collapse">
              <thead className="sticky top-0 bg-[#F8FAFC] border-b border-[#E2E8F0] text-caption font-bold text-[#64748B] uppercase select-none">
                <tr>
                  <th className="px-4 py-3">File Name</th>
                  <th className="px-4 py-3">Company (Parsed)</th>
                  <th className="px-4 py-3">Role Position</th>
                  <th className="px-4 py-3">Resume ID</th>
                  <th className="px-4 py-3">Candidate Name</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F1F5F9]">
                {queue.map((row) => (
                  <tr
                    key={row.id}
                    className={cn(
                      'transition-colors',
                      row.status === 'duplicate'
                        ? 'bg-[#FFFBEB]/40'
                        : row.status === 'needs_review'
                        ? 'bg-[#FEF2F2]/40'
                        : 'hover:bg-[#F8FAFC]'
                    )}
                  >
                    {/* File Name */}
                    <td className="px-4 py-3 max-w-[180px]">
                      <div className="flex items-center gap-2 min-w-0">
                        <FileText className="w-4 h-4 text-[#0D6EFD] shrink-0" />
                        <span className="font-mono text-caption text-[#081226] truncate" title={row.filename}>
                          {row.filename}
                        </span>
                      </div>
                    </td>

                    {/* Company (Editable) */}
                    <td className="px-4 py-3 w-32">
                      <input
                        type="text"
                        value={row.company}
                        onChange={(e) => handleUpdateRow(row.id, 'company', e.target.value)}
                        className="w-full h-[34px] px-2 rounded-lg text-caption font-bold bg-white text-[#081226] border border-[#E2E8F0] focus:border-[#0D6EFD] focus:outline-none"
                      />
                    </td>

                    {/* Role (Editable) */}
                    <td className="px-4 py-3 w-40">
                      <input
                        type="text"
                        value={row.role}
                        onChange={(e) => handleUpdateRow(row.id, 'role', e.target.value)}
                        className="w-full h-[34px] px-2 rounded-lg text-caption bg-white text-[#081226] border border-[#E2E8F0] focus:border-[#0D6EFD] focus:outline-none"
                      />
                    </td>

                    {/* Resume ID (Editable) */}
                    <td className="px-4 py-3 w-28">
                      <input
                        type="text"
                        value={row.resume_id_tag}
                        placeholder="e.g. RES101"
                        onChange={(e) => handleUpdateRow(row.id, 'resume_id_tag', e.target.value)}
                        className="w-full h-[34px] px-2 rounded-lg text-caption font-mono bg-white text-[#081226] border border-[#E2E8F0] focus:border-[#0D6EFD] focus:outline-none"
                      />
                    </td>

                    {/* Candidate Name (Editable) */}
                    <td className="px-4 py-3 w-40">
                      <input
                        type="text"
                        value={row.candidate_name}
                        onChange={(e) => handleUpdateRow(row.id, 'candidate_name', e.target.value)}
                        className="w-full h-[34px] px-2 rounded-lg text-caption font-semibold bg-white text-[#081226] border border-[#E2E8F0] focus:border-[#0D6EFD] focus:outline-none"
                      />
                    </td>

                    {/* Status Badge */}
                    <td className="px-4 py-3 whitespace-nowrap">
                      {row.status === 'valid' && (
                        <span className="px-2 py-0.5 rounded-md text-[11px] font-bold bg-[#F0FDF4] text-[#16A34A] border border-[#BBF7D0]">
                          ✅ Valid
                        </span>
                      )}
                      {row.status === 'duplicate' && (
                        <span
                          className="px-2 py-0.5 rounded-md text-[11px] font-bold bg-[#FFFBEB] text-[#D97706] border border-[#FDE68A]"
                          title={row.duplicateInfo?.existing_candidate ? `Matches candidate ${row.duplicateInfo.existing_candidate}` : 'Duplicate candidate'}
                        >
                          ⚠️ Duplicate Exists
                        </span>
                      )}
                      {row.status === 'needs_review' && (
                        <span className="px-2 py-0.5 rounded-md text-[11px] font-bold bg-[#FEF2F2] text-[#EF4444] border border-[#FECACA]">
                          ❌ Needs Review
                        </span>
                      )}
                    </td>

                    {/* Row delete */}
                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        onClick={() => handleRemoveRow(row.id)}
                        className="p-1.5 text-[#94A3B8] hover:text-[#EF4444] hover:bg-[#FEF2F2] rounded-lg transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Upload Progress Bar (When uploading) */}
          {isUploading && (
            <div className="p-6 bg-[#081226] text-white space-y-3">
              <div className="flex items-center justify-between text-small font-semibold">
                <span className="flex items-center gap-2">
                  <RefreshCw className="w-4 h-4 text-[#0D6EFD] animate-spin" />
                  Uploading batch to Google Drive & database repository...
                </span>
                <span className="font-mono text-[#FF8A00]">
                  {uploadProgressCount.current} / {uploadProgressCount.total} ({uploadProgress}%)
                </span>
              </div>
              <div className="w-full h-3 rounded-full bg-[#1E2E4E] overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-[#0D6EFD] to-[#FF8A00] rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {/* Action Buttons Row */}
          {!isUploading && (
            <div className="p-6 bg-[#F8FAFC] border-t border-[#E2E8F0] flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                {duplicateCount > 0 && (
                  <Button
                    variant="outline"
                    size="md"
                    icon={SkipForward}
                    onClick={handleSkipDuplicates}
                  >
                    Skip Duplicates ({duplicateCount})
                  </Button>
                )}
                <button
                  type="button"
                  onClick={() => setQueue([])}
                  className="text-small font-semibold text-[#64748B] hover:text-[#EF4444] px-3 py-2 transition-colors cursor-pointer"
                >
                  Clear Queue
                </button>
              </div>

              <div className="flex items-center gap-3">
                {duplicateCount > 0 ? (
                  <>
                    <Button
                      variant="outline"
                      size="md"
                      onClick={() => handleCommitUpload('skip_duplicates')}
                    >
                      Skip Duplicates & Upload New ({validCount + reviewCount})
                    </Button>
                    <Button
                      variant="primary"
                      size="lg"
                      icon={UploadCloud}
                      onClick={() => handleCommitUpload('replace_existing')}
                    >
                      Upload All (Replace Existing)
                    </Button>
                  </>
                ) : (
                  <Button
                    variant="primary"
                    size="lg"
                    icon={UploadCloud}
                    onClick={() => handleCommitUpload('all_valid')}
                    className="h-[48px] px-8"
                  >
                    Upload All Valid Resumes ({queue.length})
                  </Button>
                )}
              </div>
            </div>
          )}
        </motion.div>
      )}

      {/* Success Summary Screen */}
      {uploadSuccessSummary && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="bg-white rounded-3xl border border-[#BBF7D0] bg-[#F0FDF4]/30 shadow-card p-8 text-center space-y-6"
        >
          <div className="w-16 h-16 rounded-2xl bg-[#DCFCE7] text-[#16A34A] flex items-center justify-center mx-auto border border-[#86EFAC]">
            <CheckCircle2 className="w-8 h-8" />
          </div>

          <div>
            <h3 className="text-h2 font-extrabold text-[#081226] tracking-tight">
              Batch Upload Successful!
            </h3>
            <p className="text-body text-[#475569] max-w-md mx-auto mt-1">
              Candidate resumes have been parsed, validated, and stored in the ATS candidate repository.
            </p>
          </div>

          {/* Summary Stats Table */}
          <div className="max-w-md mx-auto bg-white rounded-2xl border border-[#E2E8F0] shadow-xs overflow-hidden">
            <div className="grid grid-cols-3 divide-x divide-[#F1F5F9] p-4 text-center">
              <div>
                <p className="text-caption font-bold uppercase text-[#16A34A]">Uploaded</p>
                <p className="text-h2 font-extrabold text-[#081226] mt-0.5">
                  {uploadSuccessSummary.uploaded}
                </p>
              </div>
              <div>
                <p className="text-caption font-bold uppercase text-[#FF8A00]">Duplicates</p>
                <p className="text-h2 font-extrabold text-[#081226] mt-0.5">
                  {uploadSuccessSummary.duplicates}
                </p>
              </div>
              <div>
                <p className="text-caption font-bold uppercase text-[#0D6EFD]">Reviewed</p>
                <p className="text-h2 font-extrabold text-[#081226] mt-0.5">
                  {uploadSuccessSummary.reviewed}
                </p>
              </div>
            </div>
          </div>

          {/* Success Action Buttons */}
          <div className="flex items-center justify-center gap-4 pt-2">
            <Button
              variant="primary"
              size="lg"
              onClick={() => navigate('/candidates')}
              className="h-[48px] px-8"
            >
              View Uploaded Resumes →
            </Button>
            <Button
              variant="outline"
              size="lg"
              onClick={() => setUploadSuccessSummary(null)}
              className="h-[48px]"
            >
              Upload More Resumes
            </Button>
          </div>
        </motion.div>
      )}
    </div>
  );
}

export default UploadPage;
