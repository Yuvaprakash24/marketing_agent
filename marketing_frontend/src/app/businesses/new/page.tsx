"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { createBusiness, getBusinessProcessingStatus } from "../actions";

const STEP_HINTS: Record<string, string> = {
  pending: "Queued",
  processing: "Reading your website and documents",
  completed: "Done",
  failed: "Something went wrong",
};

export default function NewBusinessPage() {
  const router = useRouter();

  const [form, setForm] = useState({
    name: "",
    industry: "",
    description: "",
    website_url: "",
    twitter_url: "",
    facebook_url: "",
    instagram_url: "",
    linkedin_url: "",
  });
  const [logo, setLogo] = useState<File | null>(null);
  const [documents, setDocuments] = useState<File[]>([]);

  const [requestId, setRequestId] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [statusKey, setStatusKey] = useState<string>("pending");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!requestId) return;

    pollTimer.current = setInterval(async () => {
      try {
        const status = await getBusinessProcessingStatus(requestId);
        setStatusKey(status.status);
        setStatusMessage(status.message || STEP_HINTS[status.status] || "");

        if (status.status === "completed" && status.business) {
          window.localStorage.setItem("business_id", String(status.business.id));
          window.localStorage.setItem("business_name", status.business.name);
          router.push("/dashboard");
        }

        if (status.status === "failed") {
          setSubmitting(false);
          setRequestId(null);
          setError(status.message || "Onboarding failed. Please try again.");
        }
      } catch (err) {
        console.error("Polling failed:", err);
      }
    }, 3000);

    return () => {
      if (pollTimer.current) clearInterval(pollTimer.current);
    };
  }, [requestId, router]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!form.name.trim() || !form.industry.trim() || !form.description.trim()) {
      setError("Name, industry and description are required.");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const formData = new FormData();
      Object.entries(form).forEach(([key, value]) => formData.append(key, value));
      if (logo) formData.append("logo", logo);
      documents.forEach((file) => formData.append("knowledge_base", file));

      const result = await createBusiness(formData);
      setStatusMessage(result.message);
      setRequestId(result.request_id);
    } catch (err) {
      setSubmitting(false);
      setError(err instanceof Error ? err.message : "Failed to start onboarding");
    }
  };

  const inputClass =
    "w-full rounded-lg border border-gray-700 bg-gray-900 px-4 py-3 text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:outline-none";

  if (submitting && requestId) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-900 px-6">
        <div className="w-full max-w-md rounded-xl border border-gray-700 bg-gray-800/50 p-8 text-center shadow-xl">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-t-2 border-b-2 border-blue-500" />
          <h2 className="mt-6 text-xl font-semibold text-white">
            Setting up {form.name}
          </h2>
          <p className="mt-2 text-sm text-gray-400">
            {statusMessage || STEP_HINTS[statusKey]}
          </p>
          <div className="mt-6 h-1.5 w-full overflow-hidden rounded-full bg-gray-700">
            <div className="animate-progress h-full rounded-full bg-blue-500" />
          </div>
          <p className="mt-6 text-xs text-gray-500">
            We are reading your website and documents to build a knowledge base and learn
            your brand voice. This usually takes a minute.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900">
      <div className="mx-auto max-w-3xl px-6 py-12">
        <Link
          href="/businesses"
          className="inline-flex items-center gap-1 text-sm text-gray-400 transition-colors hover:text-white"
        >
          <svg
            className="h-4 w-4"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            viewBox="0 0 24 24"
          >
            <polyline points="15 18 9 12 15 6" />
          </svg>
          Back to businesses
        </Link>

        <h1 className="mt-6 text-3xl font-bold text-white">Add a business</h1>
        <p className="mt-1 text-sm text-gray-400">
          The more context you give, the better the posts sound like you.
        </p>

        {error && (
          <div className="mt-6 rounded-lg border border-red-700 bg-red-900/30 p-4 text-sm text-red-300">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-8 space-y-6">
          <div className="space-y-5 rounded-xl border border-gray-700 bg-gray-800/50 p-6 shadow-xl backdrop-blur-sm">
            <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
              <div>
                <label className="mb-2 block text-sm font-medium text-gray-300">
                  Business name <span className="text-red-400">*</span>
                </label>
                <input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="Acme Analytics"
                  className={inputClass}
                />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-gray-300">
                  Industry <span className="text-red-400">*</span>
                </label>
                <input
                  value={form.industry}
                  onChange={(e) => setForm({ ...form, industry: e.target.value })}
                  placeholder="B2B SaaS"
                  className={inputClass}
                />
              </div>
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-gray-300">
                Description <span className="text-red-400">*</span>
              </label>
              <textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                rows={4}
                placeholder="What you sell, who you sell it to, and what makes you different."
                className={inputClass}
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-gray-300">
                Website
              </label>
              <input
                value={form.website_url}
                onChange={(e) => setForm({ ...form, website_url: e.target.value })}
                placeholder="https://acme.com"
                className={inputClass}
              />
              <p className="mt-1 text-xs text-gray-500">
                We read this to build the initial knowledge base.
              </p>
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-gray-300">Logo</label>
              <input
                type="file"
                accept="image/*"
                onChange={(e) => setLogo(e.target.files?.[0] ?? null)}
                className="w-full cursor-pointer rounded-lg border border-gray-700 bg-gray-900 px-4 py-2.5 text-sm text-gray-300 file:mr-3 file:rounded file:border-0 file:bg-gray-700 file:px-3 file:py-1.5 file:text-white"
              />
            </div>
          </div>

          <div className="space-y-5 rounded-xl border border-gray-700 bg-gray-800/50 p-6 shadow-xl backdrop-blur-sm">
            <h2 className="font-semibold text-white">Social profiles</h2>
            <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
              {(
                [
                  ["twitter_url", "Twitter"],
                  ["linkedin_url", "LinkedIn"],
                  ["facebook_url", "Facebook"],
                  ["instagram_url", "Instagram"],
                ] as const
              ).map(([field, label]) => (
                <div key={field}>
                  <label className="mb-2 block text-sm font-medium text-gray-300">
                    {label}
                  </label>
                  <input
                    value={form[field]}
                    onChange={(e) => setForm({ ...form, [field]: e.target.value })}
                    placeholder={`https://${label.toLowerCase()}.com/acme`}
                    className={inputClass}
                  />
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-500">
              These are for reference only. You connect accounts for publishing from
              Settings once the business is set up.
            </p>
          </div>

          <div className="space-y-4 rounded-xl border border-gray-700 bg-gray-800/50 p-6 shadow-xl backdrop-blur-sm">
            <h2 className="font-semibold text-white">Knowledge base documents</h2>
            <p className="text-xs text-gray-500">
              Optional. PDFs, Word documents or text files — brand guides, product
              one-pagers, FAQs.
            </p>
            <input
              type="file"
              multiple
              accept=".pdf,.docx,.doc,.txt,.md"
              onChange={(e) => setDocuments(Array.from(e.target.files ?? []))}
              className="w-full cursor-pointer rounded-lg border border-gray-700 bg-gray-900 px-4 py-2.5 text-sm text-gray-300 file:mr-3 file:rounded file:border-0 file:bg-gray-700 file:px-3 file:py-1.5 file:text-white"
            />
            {documents.length > 0 && (
              <ul className="space-y-1 text-sm text-gray-400">
                {documents.map((file) => (
                  <li key={file.name}>• {file.name}</li>
                ))}
              </ul>
            )}
          </div>

          <div className="flex justify-end gap-3">
            <Link
              href="/businesses"
              className="rounded-lg px-4 py-2 text-gray-300 transition-colors hover:text-white"
            >
              Cancel
            </Link>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-lg bg-blue-600 px-5 py-2.5 font-medium text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {submitting ? "Starting…" : "Create business"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
