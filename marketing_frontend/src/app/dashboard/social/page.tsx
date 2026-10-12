"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import SocialMediaIntegration from "@/app/components/SocialMediaIntegration";
import {
  SocialMediaAccount,
  connectSocialMediaAccount,
  getSocialMediaAccounts,
} from "../actions";
import {
  SocialMediaPost,
  createSocialMediaPosts,
  deleteSocialMediaPost,
  getPostCreationStatus,
  getSocialMediaPosts,
} from "./actions";
import PostCard from "./components/postCard";
import { PLATFORMS, PlatformIcon } from "./components/platformIcons";

const STATUS_FILTERS = ["All", "Draft", "Published", "Failed"];

export default function SocialMediaPage() {
  const [businessId, setBusinessId] = useState<number | null>(null);
  const [posts, setPosts] = useState<SocialMediaPost[]>([]);
  const [socialAccounts, setSocialAccounts] = useState<SocialMediaAccount[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [platformFilter, setPlatformFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("All");

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [topic, setTopic] = useState("");
  const [platform, setPlatform] = useState("twitter");
  const [numPosts, setNumPosts] = useState(1);
  const [isResearchNeeded, setIsResearchNeeded] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationMessage, setGenerationMessage] = useState<string | null>(null);

  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadPosts = useCallback(async (id: number) => {
    const fetched = await getSocialMediaPosts(id);
    setPosts(fetched);
    return fetched;
  }, []);

  useEffect(() => {
    const storedId = window.localStorage.getItem("business_id");
    if (!storedId) {
      window.location.href = "/businesses";
      return;
    }

    const id = parseInt(storedId);
    setBusinessId(id);

    const init = async () => {
      try {
        const [, accounts] = await Promise.all([
          loadPosts(id),
          getSocialMediaAccounts(id),
        ]);
        setSocialAccounts(accounts);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load posts");
      } finally {
        setLoading(false);
      }
    };

    init();
  }, [loadPosts]);

  // Generation runs in a background thread on the server, so poll for the result.
  useEffect(() => {
    if (!isGenerating || !businessId) return;

    const startedWith = posts.length;
    let attempts = 0;

    pollTimer.current = setInterval(async () => {
      attempts += 1;

      try {
        const status = await getPostCreationStatus(businessId);
        if (status.status === "completed") {
          const fetched = await loadPosts(businessId);
          if (fetched.length > startedWith) {
            setIsGenerating(false);
            setGenerationMessage(
              `${fetched.length - startedWith} new post${
                fetched.length - startedWith === 1 ? "" : "s"
              } ready.`
            );
            return;
          }
        }
      } catch (err) {
        console.error("Polling failed:", err);
      }

      // ~3 minutes at a 5s interval before we stop waiting.
      if (attempts >= 36) {
        setIsGenerating(false);
        setGenerationMessage(
          "Generation is taking longer than expected. Refresh in a moment to see the posts."
        );
      }
    }, 5000);

    return () => {
      if (pollTimer.current) clearInterval(pollTimer.current);
    };
  }, [isGenerating, businessId, posts.length, loadPosts]);

  const handleGenerate = async () => {
    if (!businessId || !topic.trim()) return;

    setError(null);
    setGenerationMessage(null);
    setIsGenerating(true);
    setShowCreateModal(false);

    try {
      await createSocialMediaPosts(
        businessId,
        topic.trim(),
        platform,
        numPosts,
        isResearchNeeded
      );
      setTopic("");
    } catch (err) {
      setIsGenerating(false);
      setError(err instanceof Error ? err.message : "Failed to start generation");
    }
  };

  const handleDelete = async (postId: number) => {
    if (!businessId) return;

    const previous = posts;
    setPosts((current) => current.filter((p) => p.id !== postId));

    try {
      await deleteSocialMediaPost(postId, businessId);
    } catch (err) {
      setPosts(previous);
      setError(err instanceof Error ? err.message : "Failed to delete the post");
    }
  };

  const handleStatusChange = (postId: number, newStatus: string) => {
    setPosts((current) =>
      current.map((p) => (p.id === postId ? { ...p, status: newStatus } : p))
    );
  };

  const handlePublished = (postId: number, postUrl: string) => {
    setPosts((current) =>
      current.map((p) =>
        p.id === postId ? { ...p, status: "Published", posted_link: postUrl } : p
      )
    );
  };

  const handleConnect = async (platformKey: string) => {
    if (!businessId) return;
    const response = await connectSocialMediaAccount(businessId, platformKey);
    window.open(response.url, "_blank");
  };

  const visiblePosts = posts.filter((post) => {
    const platformMatch =
      platformFilter === "all" || post.post_platform === platformFilter;
    const statusMatch = statusFilter === "All" || post.status === statusFilter;
    return platformMatch && statusMatch;
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white">Social Media</h1>
          <p className="mt-1 text-sm text-gray-400">
            Generate, review and publish on-brand posts
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          disabled={isGenerating}
          className="glow flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 font-medium text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
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
          Create posts
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

      {generationMessage && (
        <div className="flex items-start justify-between rounded-lg border border-green-700 bg-green-900/20 p-4 text-sm text-green-300">
          <span>{generationMessage}</span>
          <button
            onClick={() => setGenerationMessage(null)}
            className="ml-4 text-green-400"
          >
            Dismiss
          </button>
        </div>
      )}

      {isGenerating && (
        <div className="rounded-xl border border-blue-700/50 bg-blue-900/20 p-5">
          <div className="flex items-center gap-3">
            <div className="h-5 w-5 animate-spin rounded-full border-t-2 border-b-2 border-blue-400" />
            <div>
              <p className="font-medium text-white">Writing your posts…</p>
              <p className="text-sm text-gray-400">
                Researching the topic, drafting copy and generating images. This usually
                takes a minute or two.
              </p>
            </div>
          </div>
          <div className="mt-4 h-1.5 w-full overflow-hidden rounded-full bg-gray-700">
            <div className="animate-progress h-full rounded-full bg-blue-500" />
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setPlatformFilter("all")}
            className={`rounded-full px-3 py-1.5 text-sm transition-colors ${
              platformFilter === "all"
                ? "bg-blue-600 text-white"
                : "bg-gray-800 text-gray-300 hover:bg-gray-700"
            }`}
          >
            All platforms
          </button>
          {PLATFORMS.map((p) => (
            <button
              key={p.key}
              onClick={() => setPlatformFilter(p.key)}
              className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm transition-colors ${
                platformFilter === p.key
                  ? "bg-blue-600 text-white"
                  : "bg-gray-800 text-gray-300 hover:bg-gray-700"
              }`}
            >
              <PlatformIcon platform={p.key} />
              {p.label}
            </button>
          ))}
        </div>

        <div className="ml-auto">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
          >
            {STATUS_FILTERS.map((status) => (
              <option key={status} value={status}>
                {status === "All" ? "All statuses" : status}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="h-12 w-12 animate-spin rounded-full border-t-2 border-b-2 border-blue-500" />
        </div>
      ) : visiblePosts.length === 0 ? (
        <div className="rounded-xl border border-gray-700 bg-gray-800/50 p-12 text-center">
          <h3 className="text-lg font-medium text-white">No posts to show</h3>
          <p className="mx-auto mt-2 max-w-md text-sm text-gray-400">
            {posts.length === 0
              ? "Give the agent a topic and it will research it, write the copy and generate matching images."
              : "No posts match the current filters."}
          </p>
          {posts.length === 0 && (
            <button
              onClick={() => setShowCreateModal(true)}
              className="mt-6 rounded-lg bg-blue-600 px-4 py-2 font-medium text-white transition-colors hover:bg-blue-500"
            >
              Create your first post
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
          {visiblePosts.map((post) => (
            <PostCard
              key={post.id}
              post={post}
              onDelete={handleDelete}
              onStatusChange={handleStatusChange}
              onPublished={handlePublished}
            />
          ))}
        </div>
      )}

      <SocialMediaIntegration
        socialAccounts={socialAccounts}
        onConnect={handleConnect}
        title="Publishing accounts"
      />

      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="animate-scale-in w-full max-w-lg overflow-hidden rounded-xl border border-gray-700 bg-gray-800 shadow-2xl">
            <div className="flex items-center justify-between border-b border-gray-700 p-6">
              <h3 className="text-xl font-bold text-white">Create social posts</h3>
              <button
                onClick={() => setShowCreateModal(false)}
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

            <div className="space-y-5 p-6">
              <div>
                <label className="mb-2 block text-sm font-medium text-gray-300">
                  Topic
                </label>
                <textarea
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  rows={3}
                  placeholder="e.g. Why small teams should automate their reporting"
                  className="w-full rounded-lg border border-gray-700 bg-gray-900 px-4 py-3 text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-gray-300">
                  Platform
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {PLATFORMS.map((p) => (
                    <button
                      key={p.key}
                      onClick={() => setPlatform(p.key)}
                      className={`flex items-center justify-center gap-2 rounded-lg border px-3 py-2.5 text-sm transition-colors ${
                        platform === p.key
                          ? "border-blue-500 bg-blue-600/20 text-white"
                          : "border-gray-700 text-gray-300 hover:bg-gray-700"
                      }`}
                    >
                      <PlatformIcon platform={p.key} />
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-gray-300">
                  Number of posts: {numPosts}
                </label>
                <input
                  type="range"
                  min={1}
                  max={10}
                  value={numPosts}
                  onChange={(e) => setNumPosts(parseInt(e.target.value))}
                  className="w-full accent-blue-500"
                />
              </div>

              <label className="flex cursor-pointer items-start gap-3">
                <input
                  type="checkbox"
                  checked={isResearchNeeded}
                  onChange={(e) => setIsResearchNeeded(e.target.checked)}
                  className="mt-0.5 h-4 w-4 accent-blue-500"
                />
                <span className="text-sm text-gray-300">
                  Research the topic first
                  <span className="block text-xs text-gray-500">
                    Pulls current context from the web before writing. Slower, but more
                    specific.
                  </span>
                </span>
              </label>
            </div>

            <div className="flex justify-end gap-3 border-t border-gray-700 p-6">
              <button
                onClick={() => setShowCreateModal(false)}
                className="rounded-lg px-4 py-2 text-gray-300 transition-colors hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleGenerate}
                disabled={!topic.trim()}
                className="rounded-lg bg-blue-600 px-4 py-2 font-medium text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Generate
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
