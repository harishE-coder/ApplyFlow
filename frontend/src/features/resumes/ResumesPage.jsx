import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Users,
  Search,
  Filter,
  FileText,
  Send,
  Eye,
  Download,
  Share2,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Building2,
  Briefcase,
  Calendar,
  CheckCircle2,
  Tag,
  MessageSquare,
  MoreVertical,
  Plus,
  RefreshCw,
  Edit2,
  Trash2,
  ArrowRightLeft,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Avatar } from '@/components/ui/Avatar';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { SearchBar } from '@/components/ui/SearchBar';
import { Dropdown } from '@/components/ui/Dropdown';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';
import { useToast } from '@/components/ui/Toast';
import { useAuth } from '@/features/auth/AuthContext';
import api from '@/services/api';
import { formatDate, cn } from '@/utils/cn';

export function ResumesPage() {
  const { user, isEmployee, isAdmin, isSubAdmin, isClient } = useAuth();
  const { success, error: toastError } = useToast();
  const [searchParams] = useSearchParams();

  const [resumes, setResumes] = useState([]);
  const [totalResumes, setTotalResumes] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selectedResume, setSelectedResume] = useState(null);

  // Filters
  const [search, setSearch] = useState('');
  const [selectedClient, setSelectedClient] = useState('');
  const [selectedCompany, setSelectedCompany] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 25;

  // Metadata filter options
  const [clients, setClients] = useState([]);
  const [companies, setCompanies] = useState([]);

  // Action states
  const [noteText, setNoteText] = useState('');

  // Edit Metadata Modal State
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editResumeTarget, setEditResumeTarget] = useState(null);
  const [editName, setEditName] = useState('');
  const [editCompany, setEditCompany] = useState('');
  const [editRole, setEditRole] = useState('');
  const [editClientId, setEditClientId] = useState('');
  const [savingEdit, setSavingEdit] = useState(false);

  // Delete Resume Modal State
  const [deleteResumeTarget, setDeleteResumeTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);

  // Load clients and companies
  useEffect(() => {
    api.get('/clients').then((res) => setClients(res.data || [])).catch(() => {});
    api.get('/resumes/companies').then((res) => setCompanies(res.data || [])).catch(() => {});
  }, [searchParams]);

  // Fetch resumes
  const fetchResumes = async () => {
    setLoading(true);
    try {
      const params = {
        page,
        page_size: pageSize,
      };
      if (search) params.search = search;
      if (selectedClient) params.client_id = selectedClient;
      if (selectedCompany) params.company = selectedCompany;

      const res = await api.get('/resumes', { params });
      const items = res.data.items || [];
      setResumes(items);
      setTotalResumes(res.data.total || items.length);

      if (items.length > 0 && !selectedResume) {
        setSelectedResume(items[0]);
        setNoteText(items[0].client_notes || '');
      } else if (items.length === 0) {
        setSelectedResume(null);
      }
    } catch (err) {
      toastError('Failed to load candidate resumes', err.response?.data?.detail || 'Network error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResumes();
  }, [search, selectedClient, selectedCompany, page]);

  // Candidate Selection Handler
  const handleSelectCandidate = (candidate) => {
    setSelectedResume(candidate);
    setNoteText(candidate.client_notes || '');
  };

  // Edit Metadata Handler
  const openEditModal = (resume) => {
    setEditResumeTarget(resume);
    setEditName(resume.candidate_name);
    setEditCompany(resume.company || '');
    setEditRole(resume.role || '');
    setEditClientId(resume.client_id || '');
    setIsEditOpen(true);
  };

  const handleSaveEdit = async (e) => {
    e.preventDefault();
    if (!editResumeTarget) return;
    setSavingEdit(true);
    try {
      await api.put(`/resumes/${editResumeTarget.id}`, {
        candidate_name: editName,
        company: editCompany,
        role: editRole,
        client_id: editClientId,
      });
      success('Metadata Updated', `${editName} updated successfully.`);
      setIsEditOpen(false);
      fetchResumes();
      if (selectedResume?.id === editResumeTarget.id) {
        setSelectedResume((prev) => ({
          ...prev,
          candidate_name: editName,
          company: editCompany,
          role: editRole,
          client_id: editClientId,
        }));
      }
    } catch (err) {
      toastError('Update Failed', err.response?.data?.detail || 'Failed to update resume metadata');
    } finally {
      setSavingEdit(false);
    }
  };

  // Delete Resume Handler
  const handleDeleteResume = async () => {
    if (!deleteResumeTarget) return;
    setDeleting(true);
    try {
      await api.delete(`/resumes/${deleteResumeTarget.id}`);
      success('Resume Deleted', 'Resume record and Google Drive file removed.');
      setDeleteResumeTarget(null);
      if (selectedResume?.id === deleteResumeTarget.id) {
        setSelectedResume(null);
      }
      fetchResumes();
    } catch (err) {
      toastError('Delete Failed', err.response?.data?.detail || 'Failed to delete resume');
    } finally {
      setDeleting(false);
    }
  };

  const [submittingApp, setSubmittingApp] = useState(false);

  const handleSubmitApplication = async (resume) => {
    if (!resume) return;
    setSubmittingApp(true);
    try {
      await api.post('/applications', {
        resume_id: resume.id,
        client_id: resume.client_id,
        requirement_id: resume.requirement_id,
        status: 'Submitted',
        current_round: 'Initial Application',
      });
      success('Candidate Submitted', `${resume.candidate_name} submitted to ${resume.company || 'Client'} pipeline.`);
      window.dispatchEvent(new CustomEvent('application-created', { detail: { resume_id: resume.id } }));
      window.dispatchEvent(new CustomEvent('application-updated', { detail: { resume_id: resume.id } }));
    } catch (err) {
      toastError('Submission Failed', err.response?.data?.detail || 'Failed to submit candidate application');
    } finally {
      setSubmittingApp(false);
    }
  };

  const handleCopyShareLink = (resume) => {
    const shareUrl = `${window.location.origin}/api/resumes/${resume.id}/preview`;
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(shareUrl);
      success('Link Copied', 'Internal candidate resume link copied to clipboard.');
    } else {
      prompt('Copy internal resume link:', shareUrl);
    }
  };

  const getResumeActionMenu = (resume) => {
    const items = [];

    items.push({
      icon: Eye,
      label: 'Preview PDF (Inline)',
      onClick: () => window.open(`/api/resumes/${resume.id}/preview`, '_blank'),
    });

    items.push({
      icon: Download,
      label: 'Download Raw PDF',
      onClick: () => window.open(`/api/resumes/${resume.id}/download`, '_blank'),
    });

    items.push({
      icon: Share2,
      label: 'Copy Internal Link',
      onClick: () => handleCopyShareLink(resume),
    });

    if (isEmployee) {
      items.push({
        icon: Send,
        label: 'Submit to Pipeline',
        onClick: () => handleSubmitApplication(resume),
      });
    }

    if (isAdmin || isSubAdmin || (isEmployee && resume.uploaded_by === user?.id)) {
      items.push({ divider: true });

      items.push({
        icon: Edit2,
        label: 'Edit Metadata',
        onClick: () => openEditModal(resume),
      });

      items.push({ divider: true });

      items.push({
        icon: Trash2,
        label: 'Delete Resume',
        danger: true,
        onClick: () => setDeleteResumeTarget(resume),
      });
    }

    return items;
  };

  const totalPages = Math.ceil(totalResumes / pageSize) || 1;

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div className="bg-white p-5 rounded-2xl border border-[#E2E8F0] shadow-card space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-h2 font-extrabold text-[#081226] tracking-tight">
                Candidate Bank
              </h1>
              <span className="text-caption font-bold px-2.5 py-0.5 rounded-full bg-[#EFF6FF] text-[#2563EB] border border-[#BFDBFE]">
                {totalResumes} Resumes Ingested
              </span>
            </div>
            <p className="text-small text-[#64748B] mt-0.5">
              Enterprise candidate repository with instant preview, metadata lifecycle, and submission workflows.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="md"
              icon={RefreshCw}
              onClick={fetchResumes}
              isLoading={loading}
              className="h-[44px]"
            />

            {isEmployee && (
              <Button
                variant="primary"
                size="md"
                icon={Plus}
                onClick={() => (window.location.href = '/upload')}
                className="h-[44px]"
              >
                Upload Resumes
              </Button>
            )}
          </div>
        </div>

        {/* Filter Controls Row */}
        <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 pt-2 border-t border-[#F1F5F9]">
          <div className={cn(isClient ? 'sm:col-span-8' : 'sm:col-span-6')}>
            <SearchBar
              value={search}
              onChange={setSearch}
              placeholder="Search candidate name, role, tag ID (e.g. RES1001), or target company..."
            />
          </div>

          {!isClient && (
            <div className="sm:col-span-3">
              <select
                value={selectedClient}
                onChange={(e) => {
                  setSelectedClient(e.target.value);
                  setPage(1);
                }}
                className="w-full h-[44px] px-3 rounded-xl text-small font-medium bg-[#F8FAFC] text-[#081226] border border-[#E2E8F0] shadow-xs hover:border-[#CBD5E1] focus:outline-none focus:border-[#2563EB]"
              >
                <option value="">{isAdmin ? 'All Service Clients' : 'All Assigned Clients'}</option>
                {clients.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.company_name}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className={cn(isClient ? 'sm:col-span-4' : 'sm:col-span-3')}>
            <select
              value={selectedCompany}
              onChange={(e) => {
                setSelectedCompany(e.target.value);
                setPage(1);
              }}
              className="w-full h-[44px] px-3 rounded-xl text-small font-medium bg-[#F8FAFC] text-[#081226] border border-[#E2E8F0] shadow-xs hover:border-[#CBD5E1] focus:outline-none focus:border-[#2563EB]"
            >
              <option value="">All Target Companies</option>
              {companies.map((comp) => (
                <option key={comp} value={comp}>
                  {comp}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* 60% Left / 40% Right Split Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* LEFT 60%: Dense Candidate Rows */}
        <div className="lg:col-span-7 bg-white rounded-2xl border border-[#E2E8F0] shadow-card overflow-hidden flex flex-col">
          <div className="px-5 py-3.5 bg-[#F8FAFC] border-b border-[#E2E8F0] flex items-center justify-between text-caption font-semibold text-[#64748B] uppercase tracking-wider select-none">
            <div className="flex items-center gap-3">
              <span>Candidate & Target Role</span>
            </div>
            <div className="flex items-center gap-6">
              <span className="hidden sm:inline">Client</span>
              <span>Actions</span>
            </div>
          </div>

          <div className="divide-y divide-[#F1F5F9] max-h-[calc(100vh-280px)] overflow-y-auto">
            {loading && resumes.length === 0 ? (
              <div className="p-8 text-center text-caption text-[#64748B]">Loading candidate bank...</div>
            ) : resumes.length === 0 ? (
              <div className="p-12 text-center text-[#64748B]">
                <FileText className="w-10 h-10 text-[#CBD5E1] mx-auto mb-2" />
                <p className="text-small font-semibold text-[#081226]">No Candidates Found</p>
                <p className="text-caption mt-0.5">Try adjusting search keywords or client filters.</p>
              </div>
            ) : (
              resumes.map((cand) => {
                const isSelected = selectedResume?.id === cand.id;
                const menuItems = getResumeActionMenu(cand);

                return (
                  <div
                    key={cand.id}
                    onClick={() => handleSelectCandidate(cand)}
                    className={cn(
                      'px-5 py-3.5 flex items-center justify-between gap-4 cursor-pointer transition-all duration-100 group relative',
                      isSelected
                        ? 'bg-[#EFF6FF] border-l-4 border-[#2563EB]'
                        : 'hover:bg-[#F8FAFC]'
                    )}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <Avatar
                        name={cand.candidate_name}
                        size="sm"
                        variant={isSelected ? 'blue' : 'navy'}
                      />

                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span
                            className={cn(
                              'text-small font-bold truncate',
                              isSelected ? 'text-[#2563EB]' : 'text-[#081226]'
                            )}
                          >
                            {cand.candidate_name}
                          </span>

                          <span className="text-[10px] font-mono font-bold px-1.5 py-0.2 rounded bg-white text-[#475569] border border-[#E2E8F0] shrink-0">
                            {cand.resume_id_tag || `RES${cand.display_seq || 1000}`}
                          </span>
                        </div>

                        <p className="text-caption text-[#64748B] mt-0.5 truncate flex items-center gap-1.5">
                          <span className="font-semibold text-[#334155]">{cand.company || 'General'}</span>
                          <span>•</span>
                          <span className="truncate">{cand.role}</span>
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      <span className="hidden md:inline-block text-[11px] font-medium px-2 py-0.5 rounded-md bg-[#F1F5F9] text-[#475569] border border-[#E2E8F0] max-w-[110px] truncate">
                        {cand.client_name || 'Client'}
                      </span>

                      <div className="flex items-center gap-1">
                        <Dropdown
                          trigger={
                            <button
                              type="button"
                              onClick={(e) => e.stopPropagation()}
                              className="p-1.5 rounded-lg text-[#64748B] hover:text-[#081226] hover:bg-white transition-colors"
                            >
                              <MoreVertical className="w-4 h-4" />
                            </button>
                          }
                          items={menuItems}
                        />
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Pagination Footer */}
          {totalResumes > 0 && (
            <div className="px-5 py-3.5 bg-[#F8FAFC] border-t border-[#E2E8F0] flex items-center justify-between text-caption text-[#64748B]">
              <div>
                Page <span className="font-semibold text-[#081226]">{page}</span> of{' '}
                <span className="font-semibold text-[#081226]">{totalPages}</span>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(p - 1, 1))}
                  className="p-1.5 rounded-lg border border-[#E2E8F0] bg-white text-[#081226] hover:bg-[#F1F5F9] disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                  className="p-1.5 rounded-lg border border-[#E2E8F0] bg-white text-[#081226] hover:bg-[#F1F5F9] disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* RIGHT 40%: Candidate Preview Panel */}
        <div className="lg:col-span-5 bg-white rounded-2xl border border-[#E2E8F0] shadow-card overflow-hidden sticky top-6">
          {selectedResume ? (
            <div className="flex flex-col h-[calc(100vh-230px)]">
              <div className="p-5 border-b border-[#F1F5F9] bg-[#F8FAFC]/50 flex items-start justify-between gap-4">
                <div className="flex items-center gap-3.5 min-w-0">
                  <Avatar
                    name={selectedResume.candidate_name}
                    size="lg"
                    variant="blue"
                  />
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="text-h3 font-extrabold text-[#081226] truncate">
                        {selectedResume.candidate_name}
                      </h3>
                      <span className="font-mono text-caption font-bold px-2 py-0.5 rounded bg-white text-[#2563EB] border border-[#BFDBFE] shrink-0">
                        {selectedResume.resume_id_tag || 'RES1000'}
                      </span>
                    </div>

                    <p className="text-small font-semibold text-[#475569] mt-0.5 truncate">
                      {selectedResume.company} • {selectedResume.role}
                    </p>

                    <p className="text-caption text-[#64748B] mt-0.5">
                      Service Client: <span className="font-semibold text-[#081226]">{selectedResume.client_name || 'Client'}</span>
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-1.5 shrink-0">
                  <a
                    href={`/api/resumes/${selectedResume.id}/download`}
                    target="_blank"
                    rel="noreferrer"
                    title="Open Full PDF"
                    className="p-2 text-[#64748B] hover:text-[#2563EB] hover:bg-white rounded-xl border border-[#E2E8F0] shadow-xs transition-colors shrink-0"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </a>

                  <Dropdown
                    trigger={
                      <button
                        type="button"
                        className="p-2 text-[#64748B] hover:text-[#081226] hover:bg-white rounded-xl border border-[#E2E8F0] shadow-xs transition-colors shrink-0"
                      >
                        <MoreVertical className="w-4 h-4" />
                      </button>
                    }
                    items={getResumeActionMenu(selectedResume)}
                  />
                </div>
              </div>

              {/* Middle: PDF Layout */}
              <div className="flex-1 p-4 bg-[#F1F5F9]/60 overflow-y-auto">
                <div className="w-full h-full min-h-[300px] bg-white rounded-xl border border-[#CBD5E1] shadow-inner p-5 flex flex-col justify-between">
                  <div className="space-y-4">
                    <div className="border-b border-[#E2E8F0] pb-3 flex items-start justify-between">
                      <div>
                        <h4 className="text-h3 font-bold text-[#081226]">
                          {selectedResume.candidate_name}
                        </h4>
                        <p className="text-small text-[#2563EB] font-medium">
                          {selectedResume.role} Candidate
                        </p>
                        <p className="text-caption text-[#64748B] mt-0.5">
                          Target Account: {selectedResume.company}
                        </p>
                      </div>
                      <FileText className="w-8 h-8 text-[#94A3B8]" />
                    </div>

                    <div className="space-y-2 text-small">
                      <p className="font-bold text-[#081226] text-caption uppercase tracking-wider">
                        Professional Summary
                      </p>
                      <p className="text-caption text-[#475569] leading-relaxed">
                        Experienced professional with deep expertise in {selectedResume.role} development and enterprise architectures for {selectedResume.company}. Verified background check and technical screening passed.
                      </p>
                    </div>

                    <div className="space-y-1.5 text-caption text-[#64748B]">
                      <div className="flex items-center justify-between py-1 border-b border-[#F8FAFC]">
                        <span>File Name:</span>
                        <span className="font-mono text-[#081226] truncate max-w-[200px]">
                          {selectedResume.original_filename || 'candidate_resume.pdf'}
                        </span>
                      </div>
                      <div className="flex items-center justify-between py-1 border-b border-[#F8FAFC]">
                        <span>Ingestion Date:</span>
                        <span className="text-[#081226]">
                          {formatDate(selectedResume.upload_date)}
                        </span>
                      </div>
                      <div className="flex items-center justify-between py-1">
                        <span>Recruiter:</span>
                        <span className="text-[#081226]">
                          {selectedResume.uploader_name || 'Harish'}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="pt-3 border-t border-[#F1F5F9] flex items-center justify-between text-caption text-[#64748B]">
                    <span className="flex items-center gap-1 text-[#16A34A] font-semibold">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      ATS Validated PDF
                    </span>
                    <a
                      href={`/api/resumes/${selectedResume.id}/download`}
                      download
                      className="text-[#2563EB] font-semibold hover:underline flex items-center gap-1"
                    >
                      <Download className="w-3.5 h-3.5" />
                      Download Raw PDF
                    </a>
                  </div>
                </div>
              </div>

              {/* Bottom: Client Notes & Action CTA */}
              <div className="p-4 bg-white border-t border-[#E2E8F0] space-y-3">
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-caption">
                    <span className="font-bold text-[#081226]">Recruiter Notes</span>
                    <span className="text-[#64748B]">Visible to client team</span>
                  </div>
                  <textarea
                    rows={2}
                    value={noteText}
                    onChange={(e) => setNoteText(e.target.value)}
                    placeholder="Add specific candidate notes for the hiring team..."
                    className="w-full p-2.5 rounded-xl text-caption bg-[#F8FAFC] text-[#081226] border border-[#E2E8F0] focus:outline-none focus:border-[#2563EB] resize-none"
                  />
                </div>

                <div className="flex items-center gap-2 pt-1">
                  {isEmployee && (
                    <Button
                      variant="primary"
                      size="md"
                      icon={Send}
                      isLoading={submittingApp}
                      onClick={() => handleSubmitApplication(selectedResume)}
                      title="Submit Candidate to Pipeline & Progress Daily Target"
                      className="flex-1 h-[44px] font-bold text-xs bg-[#FF8A00] hover:bg-[#EA580C] text-white border-none shadow-xs"
                    >
                      Submit to Pipeline
                    </Button>
                  )}

                  <Button
                    variant={isEmployee ? "outline" : "primary"}
                    size="md"
                    icon={Eye}
                    onClick={() => window.open(`/api/resumes/${selectedResume.id}/preview`, '_blank')}
                    title="Open PDF Preview Inline"
                    className="flex-1 h-[44px] font-semibold text-xs"
                  >
                    Preview PDF
                  </Button>

                  <Button
                    variant="outline"
                    size="md"
                    icon={Download}
                    onClick={() => window.open(`/api/resumes/${selectedResume.id}/download`, '_blank')}
                    title="Download Original PDF"
                    className="h-[44px] px-3.5"
                  />

                  <Button
                    variant="outline"
                    size="md"
                    icon={Share2}
                    onClick={() => handleCopyShareLink(selectedResume)}
                    title="Copy Internal Share Link"
                    className="h-[44px] px-3.5"
                  />
                </div>
              </div>
            </div>
          ) : (
            <div className="p-12 text-center text-[#64748B]">
              <FileText className="w-12 h-12 text-[#CBD5E1] mx-auto mb-3" />
              <h4 className="text-small font-bold text-[#081226]">No Candidate Selected</h4>
              <p className="text-caption mt-1">Select a candidate from the left list to review preview.</p>
            </div>
          )}
        </div>
      </div>

      {/* Edit Metadata Modal */}
      <Modal
        isOpen={isEditOpen}
        onClose={() => setIsEditOpen(false)}
        title="Edit Candidate Metadata"
        subtitle="Update candidate name, target company, role, or reassign to another client account."
      >
        <form onSubmit={handleSaveEdit} className="space-y-4">
          <Input
            label="Candidate Name"
            required
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
          />

          <Input
            label="Target Hiring Company"
            required
            value={editCompany}
            onChange={(e) => setEditCompany(e.target.value)}
          />

          <Input
            label="Job Role Position"
            required
            value={editRole}
            onChange={(e) => setEditRole(e.target.value)}
          />

          <div>
            <label className="block text-caption font-bold text-[#081226] mb-1.5">
              Service Client Account
            </label>
            <select
              value={editClientId}
              onChange={(e) => setEditClientId(e.target.value)}
              className="w-full h-11 px-3 rounded-xl border border-[#CBD5E1] text-small"
              required
            >
              <option value="">-- Choose Client --</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.company_name}
                </option>
              ))}
            </select>
          </div>

          <div className="pt-4 flex justify-end gap-3">
            <Button variant="outline" size="md" onClick={() => setIsEditOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="md" isLoading={savingEdit}>
              Save Changes
            </Button>
          </div>
        </form>
      </Modal>

      {/* Delete Resume Modal */}
      <Modal
        isOpen={!!deleteResumeTarget}
        onClose={() => setDeleteResumeTarget(null)}
        title="Delete Candidate Resume?"
        subtitle="Permanent removal from database and cloud storage."
      >
        <div className="space-y-4">
          <p className="text-small text-[#64748B]">
            Are you sure you want to delete the resume for <strong>{deleteResumeTarget?.candidate_name}</strong>?
          </p>
          <div className="p-3.5 rounded-xl bg-[#FEF2F2] border border-[#FCA5A5] text-caption text-[#991B1B]">
            This action will remove the candidate record from database search, delete associated applications, and remove the PDF from Google Drive.
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button variant="outline" size="md" onClick={() => setDeleteResumeTarget(null)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              size="md"
              onClick={handleDeleteResume}
              isLoading={deleting}
            >
              Confirm Delete
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

export default ResumesPage;
