"use client";

import { useEffect, useState } from "react";

import SocialMediaIntegration from "@/app/components/SocialMediaIntegration";
import {
  SocialMediaAccount,
  connectSocialMediaAccount,
  getSocialMediaAccounts,
} from "../actions";
import {
  Business,
  SystemPrompts,
  TeamMember,
  addTeamMember,
  getBusiness,
  getSystemPrompts,
  getTeamMembers,
  removeTeamMember,
  updateBusiness,
  updateSystemPrompts,
  updateTeamMemberRole,
} from "./actions";

const TABS = [
  { key: "profile", label: "Business profile" },
  { key: "prompts", label: "AI prompts" },
  { key: "integrations", label: "Integrations" },
  { key: "team", label: "Team" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

export default function SettingsPage() {
  const [businessId, setBusinessId] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>("profile");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [profile, setProfile] = useState({
    name: "",
    industry: "",
    description: "",
    website_url: "",
    phone: "",
    primary_color: "#3b82f6",
  });
  const [prompts, setPrompts] = useState<SystemPrompts>({
    social_media_system_prompt: "",
    research_system_prompt: "",
  });
  const [socialAccounts, setSocialAccounts] = useState<SocialMediaAccount[] | null>(null);
  const [team, setTeam] = useState<TeamMember[]>([]);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("user");

  useEffect(() => {
    const storedId = window.localStorage.getItem("business_id");
    if (!storedId) {
      window.location.href = "/businesses";
      return;
    }

    const id = parseInt(storedId);
    setBusinessId(id);

    const load = async () => {
      try {
        const [business, fetchedPrompts, accounts, members] = await Promise.all([
          getBusiness(id),
          getSystemPrompts(id),
          getSocialMediaAccounts(id),
          getTeamMembers(id),
        ]);

        applyBusiness(business);
        setPrompts(fetchedPrompts);
        setSocialAccounts(accounts);
        setTeam(members);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load settings");
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  const applyBusiness = (business: Business) => {
    setProfile({
      name: business.name ?? "",
      industry: business.industry ?? "",
      description: business.description ?? "",
      website_url: business.website_url ?? "",
      phone: business.phone ?? "",
      primary_color: business.primary_color || "#3b82f6",
    });
  };

  const flash = (text: string) => {
    setMessage(text);
    setError(null);
    window.setTimeout(() => setMessage(null), 4000);
  };

  const handleSaveProfile = async () => {
    if (!businessId) return;

    setSaving(true);
    try {
      await updateBusiness(businessId, profile);
      window.localStorage.setItem("business_name", profile.name);
      flash("Business profile saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save the profile");
    } finally {
      setSaving(false);
    }
  };

  const handleSavePrompts = async () => {
    if (!businessId) return;

    setSaving(true);
    try {
      await updateSystemPrompts(businessId, {
        social_media_system_prompt: prompts.social_media_system_prompt,
        research_system_prompt: prompts.research_system_prompt,
      });
      flash("Prompts saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save the prompts");
    } finally {
      setSaving(false);
    }
  };

  const handleConnect = async (platform: string) => {
    if (!businessId) return;
    const response = await connectSocialMediaAccount(businessId, platform);
    window.open(response.url, "_blank");
  };

  const handleInvite = async () => {
    if (!businessId || !inviteEmail.trim()) return;

    setSaving(true);
    try {
      await addTeamMember(businessId, inviteEmail.trim(), inviteRole);
      setTeam(await getTeamMembers(businessId));
      setInviteEmail("");
      flash("Team member added.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add the team member");
    } finally {
      setSaving(false);
    }
  };

  const handleRoleChange = async (member: TeamMember, role: string) => {
    if (!businessId) return;

    try {
      await updateTeamMemberRole(businessId, member.id, role);
      setTeam((current) =>
        current.map((m) => (m.id === member.id ? { ...m, role } : m))
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update the role");
    }
  };

  const handleRemove = async (member: TeamMember) => {
    if (!businessId) return;
    if (!window.confirm(`Remove ${member.user.email} from this business?`)) return;

    try {
      await removeTeamMember(businessId, member.id);
      setTeam((current) => current.filter((m) => m.id !== member.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove the team member");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-12 w-12 animate-spin rounded-full border-t-2 border-b-2 border-blue-500" />
      </div>
    );
  }

  const inputClass =
    "w-full rounded-lg border border-gray-700 bg-gray-900 px-4 py-3 text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:outline-none";

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Settings</h1>
        <p className="mt-1 text-sm text-gray-400">
          Brand details, AI behaviour, publishing accounts and access
        </p>
      </div>

      {error && (
        <div className="flex items-start justify-between rounded-lg border border-red-700 bg-red-900/30 p-4 text-sm text-red-300">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="ml-4 text-red-400">
            Dismiss
          </button>
        </div>
      )}

      {message && (
        <div className="rounded-lg border border-green-700 bg-green-900/20 p-4 text-sm text-green-300">
          {message}
        </div>
      )}

      <div className="flex flex-wrap gap-2 border-b border-gray-700">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`-mb-px border-b-2 px-4 py-2.5 text-sm transition-colors ${
              activeTab === tab.key
                ? "border-blue-500 text-white"
                : "border-transparent text-gray-400 hover:text-gray-200"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "profile" && (
        <div className="space-y-5 rounded-xl border border-gray-700 bg-gray-800/50 p-6 shadow-xl backdrop-blur-sm">
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-300">
                Business name
              </label>
              <input
                value={profile.name}
                onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                className={inputClass}
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-300">
                Industry
              </label>
              <input
                value={profile.industry}
                onChange={(e) => setProfile({ ...profile, industry: e.target.value })}
                className={inputClass}
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-300">
                Website
              </label>
              <input
                value={profile.website_url}
                onChange={(e) => setProfile({ ...profile, website_url: e.target.value })}
                placeholder="https://example.com"
                className={inputClass}
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-300">Phone</label>
              <input
                value={profile.phone}
                onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
                className={inputClass}
              />
            </div>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-300">
              Description
            </label>
            <textarea
              value={profile.description}
              onChange={(e) => setProfile({ ...profile, description: e.target.value })}
              rows={5}
              className={inputClass}
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-300">
              Brand colour
            </label>
            <div className="flex items-center gap-3">
              <input
                type="color"
                value={profile.primary_color}
                onChange={(e) =>
                  setProfile({ ...profile, primary_color: e.target.value })
                }
                className="h-10 w-16 cursor-pointer rounded border border-gray-700 bg-gray-900"
              />
              <input
                value={profile.primary_color}
                onChange={(e) =>
                  setProfile({ ...profile, primary_color: e.target.value })
                }
                className="w-32 rounded-lg border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-white"
              />
            </div>
          </div>

          <div className="flex justify-end border-t border-gray-700 pt-5">
            <button
              onClick={handleSaveProfile}
              disabled={saving}
              className="rounded-lg bg-blue-600 px-4 py-2 font-medium text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {saving ? "Saving…" : "Save changes"}
            </button>
          </div>
        </div>
      )}

      {activeTab === "prompts" && (
        <div className="space-y-5 rounded-xl border border-gray-700 bg-gray-800/50 p-6 shadow-xl backdrop-blur-sm">
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-300">
              Social media prompt
            </label>
            <p className="mb-2 text-xs text-gray-500">
              The brand voice guidelines handed to the writer for every post.
            </p>
            <textarea
              value={prompts.social_media_system_prompt}
              onChange={(e) =>
                setPrompts({ ...prompts, social_media_system_prompt: e.target.value })
              }
              rows={12}
              className={`${inputClass} font-mono text-sm`}
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-300">
              Research prompt
            </label>
            <p className="mb-2 text-xs text-gray-500">
              How the agent should summarise what it finds about a topic.
            </p>
            <textarea
              value={prompts.research_system_prompt}
              onChange={(e) =>
                setPrompts({ ...prompts, research_system_prompt: e.target.value })
              }
              rows={8}
              className={`${inputClass} font-mono text-sm`}
            />
          </div>

          <div className="flex justify-end border-t border-gray-700 pt-5">
            <button
              onClick={handleSavePrompts}
              disabled={saving}
              className="rounded-lg bg-blue-600 px-4 py-2 font-medium text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {saving ? "Saving…" : "Save prompts"}
            </button>
          </div>
        </div>
      )}

      {activeTab === "integrations" && (
        <SocialMediaIntegration
          socialAccounts={socialAccounts}
          onConnect={handleConnect}
          showManageLink={false}
          title="Connected accounts"
        />
      )}

      {activeTab === "team" && (
        <div className="space-y-6">
          <div className="rounded-xl border border-gray-700 bg-gray-800/50 p-6 shadow-xl backdrop-blur-sm">
            <h2 className="font-semibold text-white">Add a team member</h2>
            <p className="mt-1 text-xs text-gray-500">
              They need to have signed up already so we can match their email.
            </p>
            <div className="mt-4 flex flex-wrap gap-3">
              <input
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                placeholder="teammate@company.com"
                className={`${inputClass} flex-1`}
              />
              <select
                value={inviteRole}
                onChange={(e) => setInviteRole(e.target.value)}
                className="rounded-lg border border-gray-700 bg-gray-900 px-4 py-3 text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
              >
                <option value="user">User</option>
                <option value="admin">Admin</option>
              </select>
              <button
                onClick={handleInvite}
                disabled={saving || !inviteEmail.trim()}
                className="rounded-lg bg-blue-600 px-4 py-2 font-medium text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Add
              </button>
            </div>
          </div>

          <div className="overflow-hidden rounded-xl border border-gray-700 bg-gray-800/50 shadow-xl backdrop-blur-sm">
            {team.length === 0 ? (
              <p className="p-6 text-sm text-gray-400">
                No one else has access to this business yet.
              </p>
            ) : (
              <ul className="divide-y divide-gray-700">
                {team.map((member) => (
                  <li
                    key={member.id}
                    className="flex flex-wrap items-center justify-between gap-3 p-5"
                  >
                    <div>
                      <p className="font-medium text-white">
                        {member.user.name || member.user.email}
                      </p>
                      <p className="text-sm text-gray-400">{member.user.email}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <select
                        value={member.role}
                        onChange={(e) => handleRoleChange(member, e.target.value)}
                        className="rounded-lg border border-gray-700 bg-gray-900 px-3 py-1.5 text-sm text-white"
                      >
                        <option value="user">User</option>
                        <option value="admin">Admin</option>
                      </select>
                      <button
                        onClick={() => handleRemove(member)}
                        className="text-sm text-red-400 hover:text-red-300"
                      >
                        Remove
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
