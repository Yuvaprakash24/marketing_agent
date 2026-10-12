"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import SocialMediaIntegration from "../components/SocialMediaIntegration";
import {
  SocialMediaAccount,
  connectSocialMediaAccount,
  getBusinessDetails,
  getSocialMediaAccounts,
} from "./actions";
import { SocialMediaPost, getSocialMediaPosts } from "./social/actions";

interface BusinessDetails {
  id: number;
  name: string;
  industry: string;
}

export default function DashboardPage() {
  const [businessId, setBusinessId] = useState<number | null>(null);
  const [business, setBusiness] = useState<BusinessDetails | null>(null);
  const [socialAccounts, setSocialAccounts] = useState<SocialMediaAccount[] | null>(null);
  const [posts, setPosts] = useState<SocialMediaPost[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const storedId = window.localStorage.getItem("business_id");
    if (!storedId) {
      window.location.href = "/businesses";
      return;
    }

    const id = parseInt(storedId);
    setBusinessId(id);

    const fetchData = async () => {
      try {
        const [businessDetails, accounts, fetchedPosts] = await Promise.all([
          getBusinessDetails(id),
          getSocialMediaAccounts(id),
          getSocialMediaPosts(id),
        ]);
        setBusiness(businessDetails);
        setSocialAccounts(accounts);
        setPosts(fetchedPosts);
      } catch (error) {
        console.error("Failed to load the dashboard:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleConnect = async (platform: string) => {
    if (!businessId) return;
    const response = await connectSocialMediaAccount(businessId, platform);
    window.open(response.url, "_blank");
  };

  const publishedCount = posts.filter((p) => p.status === "Published").length;
  const draftCount = posts.filter((p) => p.status === "Draft").length;
  const failedCount = posts.filter((p) => p.status === "Failed").length;

  const stats = [
    { name: "Total posts", value: posts.length },
    { name: "Published", value: publishedCount },
    { name: "Drafts", value: draftCount },
    { name: "Connected accounts", value: socialAccounts?.length ?? 0 },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-12 w-12 animate-spin rounded-full border-t-2 border-b-2 border-blue-500" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-white">Dashboard</h1>
        {business && (
          <div className="flex items-center space-x-3">
            <span className="text-gray-400">{business.name}</span>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gray-700">
              <span className="font-medium text-white">{business.name.charAt(0)}</span>
            </div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <div
            key={stat.name}
            className="card-hover rounded-xl border border-gray-700 bg-gray-800/50 p-6 shadow-xl backdrop-blur-sm"
          >
            <p className="text-sm text-gray-400">{stat.name}</p>
            <p className="mt-1 text-3xl font-bold text-white">{stat.value}</p>
          </div>
        ))}
      </div>

      {failedCount > 0 && (
        <div className="rounded-xl border border-red-500/30 bg-red-900/20 p-4 text-sm text-red-300">
          {failedCount} post{failedCount === 1 ? "" : "s"} failed to publish. Open the
          Social Media page to review and retry.
        </div>
      )}

      <div>
        <h2 className="mb-4 text-xl font-semibold text-white">Quick actions</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <Link
            href="/dashboard/social"
            className="rounded-xl border border-gray-700 bg-gray-800/30 p-5 transition-colors hover:bg-gray-800/60"
          >
            <h3 className="font-medium text-white">Create social posts</h3>
            <p className="mt-1 text-sm text-gray-400">
              Generate on-brand posts with AI for any platform
            </p>
          </Link>
          <Link
            href="/dashboard/knowledge"
            className="rounded-xl border border-gray-700 bg-gray-800/30 p-5 transition-colors hover:bg-gray-800/60"
          >
            <h3 className="font-medium text-white">Knowledge base</h3>
            <p className="mt-1 text-sm text-gray-400">
              Teach the agent about your products and voice
            </p>
          </Link>
          <Link
            href="/dashboard/settings"
            className="rounded-xl border border-gray-700 bg-gray-800/30 p-5 transition-colors hover:bg-gray-800/60"
          >
            <h3 className="font-medium text-white">Settings</h3>
            <p className="mt-1 text-sm text-gray-400">
              Brand profile, team access and integrations
            </p>
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div>
          <h2 className="mb-4 text-xl font-semibold text-white">Recent posts</h2>
          <div className="rounded-xl border border-gray-700 bg-gray-800/50 p-4 shadow-xl backdrop-blur-sm">
            {posts.length === 0 ? (
              <p className="py-6 text-center text-sm text-gray-400">
                No posts yet.{" "}
                <Link href="/dashboard/social" className="text-blue-400 hover:text-blue-300">
                  Create your first one
                </Link>
                .
              </p>
            ) : (
              <div className="space-y-3">
                {posts.slice(0, 5).map((post) => (
                  <div
                    key={post.id}
                    className="flex items-center justify-between rounded-lg bg-gray-800/70 p-3"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm text-white">{post.post_text}</p>
                      <p className="mt-1 text-xs text-gray-400 capitalize">
                        {post.post_platform} ·{" "}
                        {new Date(post.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <span
                      className={`ml-3 rounded-full px-2 py-1 text-xs ${
                        post.status === "Published"
                          ? "bg-green-900/30 text-green-400"
                          : post.status === "Failed"
                            ? "bg-red-900/30 text-red-400"
                            : "bg-blue-900/30 text-blue-400"
                      }`}
                    >
                      {post.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <SocialMediaIntegration
          socialAccounts={socialAccounts}
          onConnect={handleConnect}
          showManageLink
        />
      </div>
    </div>
  );
}
