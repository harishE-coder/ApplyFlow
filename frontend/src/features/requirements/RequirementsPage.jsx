import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Layers,
  Building2,
  Briefcase,
  Plus,
  Search,
  CheckCircle2,
  XCircle,
  FileText,
  RefreshCw,
  ExternalLink,
  ChevronRight,
  Target,
  Filter,
  MoreVertical,
  Edit2,
  Archive,
  Trash2,
  RotateCcw,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Table } from '@/components/ui/Table';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Dropdown } from '@/components/ui/Dropdown';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';
import { SearchBar } from '@/components/ui/SearchBar';
import { useToast } from '@/components/ui/Toast';
import { useAuth } from '@/features/auth/AuthContext';
import api from '@/services/api';

export function RequirementsPage() {
  const { user, isAdmin, isSubAdmin, isClient } = useAuth();
  const { success, error: toastError } = useToast();

  const [requirements, setRequirements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedClient, setSelectedClient] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [clients, setClients] = useState([]);

  // Create modal state
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [company, setCompany] = useState('');
  const [role, setRole] = useState('');
  const [roleCode, setRoleCode] = useState('');
  const [clientId, setClientId] = useState('');
  const [creating, setCreating] = useState(false);

  // Edit modal state
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editReqData, setEditReqData] = useState(null);
  const [editCompany, setEditCompany] = useState('');
  const [editRole, setEditRole] = useState('');
  const [editRoleCode, setEditRoleCode] = useState('');
  const [updating, setUpdating] = useState(false);

  const fetchRequirements = async () => {
    setLoading(true);
    try {
      const params = {};
      if (search) params.search = search;
      if (selectedClient) params.client_id = selectedClient;
      if (statusFilter && statusFilter !== 'all') params.status = statusFilter;

      const res = await api.get('/requirements', { params });
      setRequirements(res.data || []);
    } catch (err) {
      toastError('Error', 'Failed to load job requirements');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    api.get('/clients').then((res) => setClients(res.data || [])).catch(() => {});
  }, []);

  useEffect(() => {
    fetchRequirements();
  }, [search, selectedClient, statusFilter]);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!company || !role || !clientId) return;
    setCreating(true);
    try {
      await api.post('/requirements', {
        company,
        role,
        role_code: roleCode || `${company.slice(0, 3).toUpperCase()}-${role.slice(0, 2).toUpperCase()}-01`,
        client_id: clientId,
      });
      success('Job Opening Created', `${company} - ${role} created successfully.`);
      setIsCreateOpen(false);
      setCompany('');
      setRole('');
      setRoleCode('');
      fetchRequirements();
    } catch (err) {
      toastError('Failed', err.response?.data?.detail || 'Failed to create requirement');
    } finally {
      setCreating(false);
    }
  };

  const handleEdit = (req) => {
    setEditReqData(req);
    setEditCompany(req.company);
    setEditRole(req.role);
    setEditRoleCode(req.role_code);
    setIsEditOpen(true);
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    if (!editReqData) return;
    setUpdating(true);
    try {
      await api.put(`/requirements/${editReqData.id}`, {
        company: editCompany,
        role: editRole,
        role_code: editRoleCode,
      });
      success('Requirement Updated', `${editCompany} - ${editRole} updated.`);
      setIsEditOpen(false);
      fetchRequirements();
    } catch (err) {
      toastError('Update Failed', err.response?.data?.detail || 'Failed to update requirement');
    } finally {
      setUpdating(false);
    }
  };

  const handleCloseOpening = async (req) => {
    try {
      await api.post(`/requirements/${req.id}/close`);
      success('Opening Closed', `${req.role_code} closed successfully.`);
      fetchRequirements();
    } catch (err) {
      toastError('Action Failed', err.response?.data?.detail || 'Failed to close opening');
    }
  };

  const handleReopenOpening = async (req) => {
    try {
      await api.post(`/requirements/${req.id}/reopen`);
      success('Opening Reopened', `${req.role_code} reopened.`);
      fetchRequirements();
    } catch (err) {
      toastError('Action Failed', err.response?.data?.detail || 'Failed to reopen opening');
    }
  };

  const handleArchiveOpening = async (req) => {
    try {
      await api.post(`/requirements/${req.id}/archive`);
      success('Opening Archived', `${req.role_code} archived.`);
      fetchRequirements();
    } catch (err) {
      toastError('Action Failed', err.response?.data?.detail || 'Failed to archive opening');
    }
  };

  const handleDeleteOpening = async (req) => {
    try {
      await api.delete(`/requirements/${req.id}`);
      success('Opening Deleted', `${req.role_code} deleted.`);
      fetchRequirements();
    } catch (err) {
      toastError('Cannot Delete', err.response?.data?.detail || 'This opening has candidate submissions.');
    }
  };

  const getReqActions = (req) => {
    const items = [];
    if (isAdmin || isSubAdmin || isClient) {
      items.push({
        icon: Edit2,
        label: 'Edit Opening',
        onClick: () => handleEdit(req),
      });

      if (req.status === 'active') {
        items.push({
          icon: XCircle,
          label: 'Close Opening',
          onClick: () => handleCloseOpening(req),
        });
      } else {
        items.push({
          icon: RotateCcw,
          label: 'Reopen Opening',
          onClick: () => handleReopenOpening(req),
        });
      }

      if (req.status !== 'archived') {
        items.push({
          icon: Archive,
          label: 'Archive Opening',
          onClick: () => handleArchiveOpening(req),
        });
      }

      items.push({
        icon: ExternalLink,
        label: 'View Candidates',
        onClick: () => (window.location.href = `/candidates?requirement_id=${req.id}`),
      });

      if (isAdmin) {
        items.push({ divider: true });
        items.push({
          icon: Trash2,
          label: 'Safe Delete',
          danger: true,
          onClick: () => handleDeleteOpening(req),
        });
      }
    }
    return items;
  };

  const columns = [
    {
      title: 'Target Company',
      key: 'company',
      render: (val) => <span className="font-bold text-[#081226] text-small">{val}</span>,
    },
    {
      title: 'Role Position',
      key: 'role',
      render: (val) => <span className="font-medium text-[#334155]">{val}</span>,
    },
    {
      title: 'Role Code',
      key: 'role_code',
      render: (val) => (
        <span className="font-mono text-caption font-semibold px-2 py-0.5 rounded bg-[#F8FAFC] border border-[#E2E8F0] text-[#475569]">
          {val || '—'}
        </span>
      ),
    },
    {
      title: 'Service Client',
      key: 'client_name',
      render: (val) => <span className="text-[#081226] font-medium">{val || 'Client'}</span>,
    },
    {
      title: 'Status',
      key: 'status',
      render: (val) => (
        <StatusBadge
          status={val === 'closed' ? 'inactive' : val === 'archived' ? 'archived' : 'active'}
        />
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      align: 'right',
      render: (_, row) => {
        const menuItems = getReqActions(row);
        return (
          <div className="flex items-center justify-end gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => (window.location.href = `/candidates?requirement_id=${row.id}`)}
            >
              Candidates ({row.total_resumes ?? 0})
            </Button>
            {menuItems.length > 0 && (
              <Dropdown
                trigger={
                  <button
                    type="button"
                    className="p-1.5 rounded-lg text-[#64748B] hover:text-[#081226] hover:bg-[#F1F5F9] transition-colors"
                  >
                    <MoreVertical className="w-4 h-4" />
                  </button>
                }
                items={menuItems}
              />
            )}
          </div>
        );
      },
    },
  ];

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="bg-white p-5 rounded-2xl border border-[#E2E8F0] shadow-card space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-h2 font-extrabold text-[#081226] tracking-tight">
                Job Openings & Requirements
              </h1>
              <span className="text-caption font-bold px-2.5 py-0.5 rounded-full bg-[#EFF6FF] text-[#2563EB] border border-[#BFDBFE]">
                {requirements.length} Openings
              </span>
            </div>
            <p className="text-small text-[#64748B] mt-0.5">
              Client requirements mapped to candidate pipeline queues and sourcing targets.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="md"
              icon={RefreshCw}
              onClick={fetchRequirements}
              isLoading={loading}
              className="h-[44px]"
            />

            {(isAdmin || isClient || isSubAdmin) && (
              <Button
                variant="primary"
                size="md"
                icon={Plus}
                onClick={() => setIsCreateOpen(true)}
                className="h-[44px]"
              >
                New Job Opening
              </Button>
            )}
          </div>
        </div>

        {/* Filter Controls Row */}
        <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 pt-2 border-t border-[#F1F5F9]">
          <div className="sm:col-span-6">
            <SearchBar
              value={search}
              onChange={setSearch}
              placeholder="Search target company (TCS, Amazon, Google), role, or code..."
            />
          </div>

          <div className="sm:col-span-3">
            <select
              value={selectedClient}
              onChange={(e) => setSelectedClient(e.target.value)}
              className="w-full h-[44px] px-3 rounded-xl text-small font-medium bg-[#F8FAFC] text-[#081226] border border-[#E2E8F0] shadow-xs hover:border-[#CBD5E1] focus:outline-none focus:border-[#2563EB]"
            >
              <option value="">All Service Clients</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.company_name}
                </option>
              ))}
            </select>
          </div>

          <div className="sm:col-span-3">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full h-[44px] px-3 rounded-xl text-small font-medium bg-[#F8FAFC] text-[#081226] border border-[#E2E8F0] shadow-xs hover:border-[#CBD5E1] focus:outline-none focus:border-[#2563EB]"
            >
              <option value="all">All Statuses</option>
              <option value="active">Active</option>
              <option value="closed">Closed</option>
              <option value="archived">Archived</option>
            </select>
          </div>
        </div>
      </div>

      {/* Table Display */}
      <Table
        columns={columns}
        data={requirements}
        loading={loading}
        emptyMessage="No job requirements matching filters."
      />

      {/* Create Modal */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Add New Job Opening"
        subtitle="Create a targeted requirement code for candidate delivery."
      >
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="block text-caption font-bold text-[#081226] mb-1.5">
              Service Client
            </label>
            <select
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
              className="w-full h-11 px-3 rounded-xl border border-[#CBD5E1] text-small"
              required
            >
              <option value="">-- Select Client Account --</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.company_name}
                </option>
              ))}
            </select>
          </div>

          <Input
            label="Target Hiring Company"
            placeholder="e.g. TCS, Amazon, Infosys"
            required
            value={company}
            onChange={(e) => setCompany(e.target.value)}
          />

          <Input
            label="Job Role Position"
            placeholder="e.g. Senior Java Developer"
            required
            value={role}
            onChange={(e) => setRole(e.target.value)}
          />

          <Input
            label="Role Code (Optional)"
            placeholder="e.g. TCS-JAVA-01 (Auto-generated if blank)"
            value={roleCode}
            onChange={(e) => setRoleCode(e.target.value)}
          />

          <div className="pt-4 flex justify-end gap-3">
            <Button variant="outline" size="md" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="md" isLoading={creating}>
              Create Requirement
            </Button>
          </div>
        </form>
      </Modal>

      {/* Edit Modal */}
      <Modal
        isOpen={isEditOpen}
        onClose={() => setIsEditOpen(false)}
        title="Edit Job Requirement"
        subtitle="Update opening position details and role code."
      >
        <form onSubmit={handleUpdate} className="space-y-4">
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

          <Input
            label="Role Code"
            required
            value={editRoleCode}
            onChange={(e) => setEditRoleCode(e.target.value)}
          />

          <div className="pt-4 flex justify-end gap-3">
            <Button variant="outline" size="md" onClick={() => setIsEditOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="md" isLoading={updating}>
              Save Changes
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
