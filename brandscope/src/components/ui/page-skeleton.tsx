"use client";

import Skeleton from "react-loading-skeleton";
import "react-loading-skeleton/dist/skeleton.css";

export function MetricsSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="rounded-xl border border-border bg-card p-3">
          <Skeleton width={60} height={8} baseColor="var(--muted)" highlightColor="var(--border)" />
          <Skeleton width={80} height={24} className="mt-1.5" baseColor="var(--muted)" highlightColor="var(--border)" />
        </div>
      ))}
    </div>
  );
}

export function ChartSkeleton() {
  return (
    <div className="rounded-2xl border border-border bg-card p-5">
      <Skeleton width={120} height={10} className="mb-4" baseColor="var(--muted)" highlightColor="var(--border)" />
      <Skeleton height={180} borderRadius={12} baseColor="var(--muted)" highlightColor="var(--border)" />
    </div>
  );
}

export function PostListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="rounded-xl border border-border bg-card p-3.5">
          <div className="flex items-start gap-3">
            <Skeleton circle width={28} height={28} baseColor="var(--muted)" highlightColor="var(--border)" />
            <div className="flex-1">
              <Skeleton width="30%" height={10} baseColor="var(--muted)" highlightColor="var(--border)" />
              <Skeleton width="90%" height={12} className="mt-1.5" baseColor="var(--muted)" highlightColor="var(--border)" />
              <Skeleton width="60%" height={10} className="mt-1" baseColor="var(--muted)" highlightColor="var(--border)" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export function AnalysisSkeleton() {
  return (
    <div className="space-y-3">
      <Skeleton width={150} height={10} baseColor="var(--muted)" highlightColor="var(--border)" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="rounded-xl border border-border bg-card p-3.5">
            <Skeleton width="50%" height={12} baseColor="var(--muted)" highlightColor="var(--border)" />
            <Skeleton width="90%" height={8} className="mt-2" baseColor="var(--muted)" highlightColor="var(--border)" />
            <Skeleton width="70%" height={8} className="mt-1" baseColor="var(--muted)" highlightColor="var(--border)" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function PageSkeleton({ title, color }: { title: string; color: string }) {
  return (
    <div className="max-w-6xl mx-auto px-4 py-6 space-y-6">
      <div>
        <div className="flex items-center gap-3">
          <div className="w-5 h-5 rounded" style={{ backgroundColor: color, opacity: 0.3 }} />
          <Skeleton width={200} height={20} baseColor="var(--muted)" highlightColor="var(--border)" />
        </div>
        <Skeleton width={300} height={10} className="mt-1.5" baseColor="var(--muted)" highlightColor="var(--border)" />
      </div>
      <MetricsSkeleton />
      <AnalysisSkeleton />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ChartSkeleton />
        <ChartSkeleton />
      </div>
      <PostListSkeleton />
    </div>
  );
}
