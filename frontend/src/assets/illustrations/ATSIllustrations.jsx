import React from 'react';

export function UploadHeroIllustration({ className = 'w-24 h-24' }) {
  return (
    <svg className={className} viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="cloud-glow" x1="20" y1="20" x2="100" y2="100" gradientUnits="userSpaceOnUse">
          <stop stopColor="#EFF6FF" />
          <stop offset="1" stopColor="#DBEAFE" />
        </linearGradient>
        <linearGradient id="arrow-grad" x1="60" y1="35" x2="60" y2="75" gradientUnits="userSpaceOnUse">
          <stop stopColor="#2563EB" />
          <stop offset="1" stopColor="#1D4ED8" />
        </linearGradient>
      </defs>
      {/* Soft background glow circles */}
      <circle cx="60" cy="60" r="54" fill="#F0F7FF" />
      <circle cx="60" cy="60" r="44" fill="url(#cloud-glow)" stroke="#BFDBFE" strokeWidth="1.5" strokeDasharray="4 4" />
      
      {/* File shape */}
      <rect x="42" y="38" width="36" height="44" rx="6" fill="#FFFFFF" stroke="#93C5FD" strokeWidth="2" />
      <path d="M50 48H70" stroke="#94A3B8" strokeWidth="2" strokeLinecap="round" />
      <path d="M50 56H64" stroke="#94A3B8" strokeWidth="2" strokeLinecap="round" />
      <path d="M50 64H58" stroke="#94A3B8" strokeWidth="2" strokeLinecap="round" />

      {/* Upward Arrow Kinetic Element */}
      <g filter="drop-shadow(0px 4px 8px rgba(37, 99, 235, 0.35))">
        <circle cx="78" cy="74" r="16" fill="url(#arrow-grad)" />
        <path d="M78 68V80M78 68L74 72M78 68L82 72" stroke="#FFFFFF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </g>

      {/* Sparkle badge */}
      <circle cx="36" cy="42" r="4" fill="#F97316" />
    </svg>
  );
}

export function LoginBrandIllustration({ className = 'w-full max-w-[420px]' }) {
  return (
    <svg className={className} viewBox="0 0 420 320" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="card-grad" x1="40" y1="40" x2="380" y2="280" gradientUnits="userSpaceOnUse">
          <stop stopColor="#0B1B3D" />
          <stop offset="1" stopColor="#081226" />
        </linearGradient>
        <linearGradient id="line-grad" x1="80" y1="120" x2="320" y2="120" gradientUnits="userSpaceOnUse">
          <stop stopColor="#2563EB" />
          <stop offset="1" stopColor="#F97316" />
        </linearGradient>
      </defs>

      {/* Outer Glow Container */}
      <rect x="20" y="20" width="380" height="280" rx="20" fill="url(#card-grad)" stroke="#1E2E4E" strokeWidth="1.5" />
      
      {/* Decorative Grid Lines */}
      <path d="M60 40V280M120 40V280M180 40V280M240 40V280M300 40V280M360 40V280" stroke="#102347" strokeWidth="1" strokeDasharray="3 3" opacity="0.6" />
      <path d="M20 90H400M20 160H400M20 230H400" stroke="#102347" strokeWidth="1" strokeDasharray="3 3" opacity="0.6" />

      {/* Simulated Candidate Card 1 */}
      <rect x="50" y="55" width="140" height="80" rx="10" fill="#102042" stroke="#2563EB" strokeWidth="1" />
      <circle cx="75" cy="80" r="12" fill="#2563EB" opacity="0.4" />
      <rect x="95" y="72" width="75" height="8" rx="4" fill="#FFFFFF" opacity="0.9" />
      <rect x="95" y="85" width="50" height="6" rx="3" fill="#94A3B8" opacity="0.7" />
      <rect x="65" y="105" width="60" height="14" rx="4" fill="#2563EB" opacity="0.2" />
      <rect x="70" y="109" width="40" height="6" rx="3" fill="#60A5FA" />

      {/* Simulated Candidate Card 2 */}
      <rect x="230" y="55" width="140" height="80" rx="10" fill="#102042" stroke="#F97316" strokeWidth="1" />
      <circle cx="255" cy="80" r="12" fill="#F97316" opacity="0.4" />
      <rect x="275" y="72" width="75" height="8" rx="4" fill="#FFFFFF" opacity="0.9" />
      <rect x="275" y="85" width="45" height="6" rx="3" fill="#94A3B8" opacity="0.7" />
      <rect x="245" y="105" width="65" height="14" rx="4" fill="#F97316" opacity="0.2" />
      <rect x="250" y="109" width="45" height="6" rx="3" fill="#FB923C" />

      {/* ATS Pipeline Connector */}
      <path d="M120 135V190C120 200 130 210 140 210H270C280 210 290 200 290 190V135" stroke="url(#line-grad)" strokeWidth="2.5" strokeDasharray="5 5" />
      <circle cx="210" cy="210" r="18" fill="#081226" stroke="#2563EB" strokeWidth="2" />
      <path d="M205 210L209 214L216 206" stroke="#2563EB" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />

      {/* Floating Metrics Badge */}
      <rect x="130" y="248" width="160" height="34" rx="8" fill="#16294F" stroke="#2C4875" strokeWidth="1" />
      <circle cx="148" cy="265" r="5" fill="#10B981" />
      <text x="160" y="269" fill="#F8FAFC" fontSize="11" fontWeight="600" fontFamily="Inter, sans-serif">100% Target Met Today</text>
    </svg>
  );
}

export function EmptyStateIllustration({ className = 'w-32 h-32' }) {
  return (
    <svg className={className} viewBox="0 0 160 160" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="80" cy="80" r="70" fill="#F8FAFC" stroke="#E2E8F0" strokeWidth="1.5" />
      <rect x="52" y="44" width="56" height="72" rx="8" fill="#FFFFFF" stroke="#CBD5E1" strokeWidth="1.5" />
      <path d="M64 64H96" stroke="#E2E8F0" strokeWidth="3" strokeLinecap="round" />
      <path d="M64 78H88" stroke="#E2E8F0" strokeWidth="3" strokeLinecap="round" />
      <path d="M64 92H80" stroke="#E2E8F0" strokeWidth="3" strokeLinecap="round" />
      <circle cx="108" cy="112" r="20" fill="#EFF6FF" stroke="#3B82F6" strokeWidth="2" />
      <path d="M102 112H114M108 106V118" stroke="#2563EB" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}
