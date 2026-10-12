"use client";

import { useEffect, useState } from "react";

import {
  KnowledgeBaseEntry,
  addKnowledgeBaseEntry,
  deleteKnowledgeBaseEntry,
  editKnowledgeBaseEntry,
  getKnowledgeBase,
} from "./actions";

type ModalState =
  | { mode: "closed" }
  | { mode: "add" }
  | { mode: "edit"; entry: KnowledgeBaseEntry };

export default function KnowledgeBasePage() {
  const [businessId, setBusinessId] = useState<number | null>(null);
  const [entries, setEntries] = useState<KnowledgeBaseEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [modal, setModal] = useState<ModalState>({ mode: "closed" });
  const [name, setName] = useState("");
  const [content, setContent] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const refresh = async (id: number) => {
    const fetched = await getKnowledgeBase(id);
    setEntries(fetched);
  };

  useEffect(() => {
    const storedId = window.localStorage.getItem("business_id");
    if (!storedId) {
      window.location.href = "/businesses";
      return;
    }

    const id = parseInt(storedId);
    setBusinessId(id);

    refresh(id)
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Failed to load the knowledge base")
      )
      .finally(() => setLoading(false));
  }, []);

  const openAdd = () => {
    setName("");
    setContent("");
    setModal({ mode: "add" });
  };

  const openEdit = (entry: KnowledgeBaseEntry) => {
    setName(entry.name);
    setContent(entry.content);
    setModal({ mode: "edit", entry });
  };

  const handleSave = async () => {
    if (!businessId || !name.trim() || !content.trim()) return;

    setSaving(true);
    setError(null);

    try {
      if (modal.mode === "edit") {
        await editKnowledgeBaseEntry(businessId, modal.entry.id, name.trim(), content.trim());
      } else {
        await addKnowledgeBaseEntry(businessId, name.trim(), content.trim());
      }
      await refresh(businessId);
      setModal({ mode: "closed" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save the entry");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (entry: KnowledgeBaseEntry) => {
    if (!businessId) return;
    if (!window.confirm(`Delete "${entry.name}"?`)) return;

    try {
      await deleteKnowledgeBaseEntry(businessId, entry.id);
      await refresh(businessId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete the entry");
    }
  };

  // The API returns the generated summary as entry 0; it is read-only.
  const summary = entries.find((entry) => entry.id === 0);
  const userEntries = entries.filter((entry) => entry.id !== 0);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white">Knowledge Base</h1>
          <p className="mt-1 text-sm text-gray-400">
            Everything here feeds into the posts the agent writes
          </p>
        </div>
        <button
          onClick={openAdd}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 font-medium text-white transition-colors hover:bg-blue-500"
        >
          <svg
            className="h-5 w-5"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Add entry
        </button>
      </div>

      {error && (
        <div className="flex items-start justify-between rounded-lg border border-red-700 bg-red-900/30 p-4 text-sm text-red-300">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="ml-4 text-red-400">
            Dismiss
          </button>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="h-12 w-12 animate-spin rounded-full border-t-2 border-b-2 border-blue-500" />
        </div>
      ) : (
        <>
          {summary && (
            <div className="rounded-xl border border-blue-700/40 bg-blue-900/10 p-6">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold text-white">Generated summary</h2>
                <span className="rounded-full bg-blue-900/40 px-2 py-1 text-xs text-blue-300">
                  Read only
                </span>
              </div>
              <p className="mt-3 text-sm whitespace-pre-wrap text-gray-300">
                {summary.content || "The summary is rebuilt whenever you change an entry."}
              </p>
            </div>
          )}

          {userEntries.length === 0 ? (
            <div className="rounded-xl border border-gray-700 bg-gray-800/50 p-12 text-center">
              <h3 className="text-lg font-medium text-white">No entries yet</h3>
              <p className="mx-auto mt-2 max-w-md text-sm text-gray-400">
                Add your products, tone of voice, offers or FAQs so the agent writes posts
                that sound like you.
              </p>
              <button
                onClick={openAdd}
                className="mt-6 rounded-lg bg-blue-600 px-4 py-2 font-medium text-white transition-colors hover:bg-blue-500"
              >
                Add your first entry
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {userEntries.map((entry) => {
                const isExpanded = expandedId === entry.id;

                return (
                  <div
                    key={entry.id}
                    className="rounded-xl border border-gray-700 bg-gray-800/50 shadow-xl backdrop-blur-sm"
                  >
                    <div className="flex items-start justify-between gap-4 p-5">
                      <button
                        onClick={() => setExpandedId(isExpanded ? null : entry.id)}
                        className="min-w-0 flex-1 text-left"
                      >
                        <h3 className="font-medium text-white">{entry.name}</h3>
                        <p
                          className={`mt-1 text-sm text-gray-400 ${
                            isExpanded ? "whitespace-pre-wrap" : "truncate"
                          }`}
                        >
                          {entry.content}
                        </p>
                        <p className="mt-2 text-xs text-gray-500">
                          Updated {new Date(entry.updated_at).toLocaleDateString()}
                        </p>
                      </button>

                      <div className="flex shrink-0 gap-2">
                        <button
                          onClick={() => openEdit(entry)}
                          className="rounded-lg p-2 text-gray-400 transition-colors hover:bg-gray-700 hover:text-white"
                          aria-label="Edit entry"
                        >
                          <svg
                            className="h-5 w-5"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            viewBox="0 0 24 24"
                          >
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                          </svg>
                        </button>
                        <button
                          onClick={() => handleDelete(entry)}
                          className="rounded-lg p-2 text-gray-400 transition-colors hover:bg-gray-700 hover:text-red-400"
                          aria-label="Delete entry"
                        >
                          <svg
                            className="h-5 w-5"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            viewBox="0 0 24 24"
                          >
                            <polyline points="3 6 5 6 21 6" />
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}

      {modal.mode !== "closed" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="animate-scale-in w-full max-w-2xl overflow-hidden rounded-xl border border-gray-700 bg-gray-800 shadow-2xl">
            <div className="flex items-center justify-between border-b border-gray-700 p-6">
              <h3 className="text-xl font-bold text-white">
                {modal.mode === "edit" ? "Edit entry" : "Add entry"}
              </h3>
              <button
                onClick={() => setModal({ mode: "closed" })}
                className="text-gray-400 transition-colors hover:text-white"
              >
                <svg
                  className="h-6 w-6"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2}
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="space-y-4 p-6">
              <div>
                <label className="mb-2 block text-sm font-medium text-gray-300">Title</label>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Product overview"
                  className="w-full rounded-lg border border-gray-700 bg-gray-900 px-4 py-3 text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-gray-300">
                  Content
                </label>
                <textarea
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  rows={10}
                  placeholder="Paste anything useful: features, pricing, customer quotes, tone of voice…"
                  className="w-full rounded-lg border border-gray-700 bg-gray-900 px-4 py-3 text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 border-t border-gray-700 p-6">
              <button
                onClick={() => setModal({ mode: "closed" })}
                className="rounded-lg px-4 py-2 text-gray-300 transition-colors hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving || !name.trim() || !content.trim()}
                className="rounded-lg bg-blue-600 px-4 py-2 font-medium text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {saving ? "Saving…" : "Save"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
