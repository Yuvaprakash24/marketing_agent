"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { logout } from "../auth/actions";
import { BusinessSummary, getBusinesses } from "./actions";

export default function BusinessesPage() {
  const router = useRouter();
  const [businesses, setBusinesses] = useState<BusinessSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getBusinesses()
      .then(setBusinesses)
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Failed to load your businesses")
      )
      .finally(() => setLoading(false));
  }, []);

  const selectBusiness = (business: BusinessSummary) => {
    window.localStorage.setItem("business_id", String(business.id));
    window.localStorage.setItem("business_name", business.name);
    router.push("/dashboard");
  };

  return (
    <div className="min-h-screen bg-gray-900">
      <header className="border-b border-gray-800">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-5">
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-purple-600">
              <span className="font-bold text-white">M</span>
            </div>
            <span className="text-lg font-semibold text-white">Marketing Agent</span>
          </div>
          <form action={logout}>
            <button className="text-sm text-gray-400 transition-colors hover:text-white">
              Sign out
            </button>
          </form>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-12">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-white">Your businesses</h1>
            <p className="mt-1 text-sm text-gray-400">
              Pick a business to work on, or add a new one
            </p>
          </div>
          <Link
            href="/businesses/new"
            className="glow flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 font-medium text-white transition-colors hover:bg-blue-500"
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
            Add business
          </Link>
        </div>

        {error && (
          <div className="mt-6 rounded-lg border border-red-700 bg-red-900/30 p-4 text-sm text-red-300">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-24">
            <div className="h-12 w-12 animate-spin rounded-full border-t-2 border-b-2 border-blue-500" />
          </div>
        ) : businesses.length === 0 ? (
          <div className="mt-10 rounded-xl border border-gray-700 bg-gray-800/50 p-12 text-center">
            <h2 className="text-lg font-medium text-white">No businesses yet</h2>
            <p className="mx-auto mt-2 max-w-md text-sm text-gray-400">
              Add your business and the agent will read your website, build a knowledge
              base and learn your brand voice.
            </p>
            <Link
              href="/businesses/new"
              className="mt-6 inline-block rounded-lg bg-blue-600 px-4 py-2 font-medium text-white transition-colors hover:bg-blue-500"
            >
              Get started
            </Link>
          </div>
        ) : (
          <div className="mt-10 grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
            {businesses.map((business) => (
              <button
                key={business.id}
                onClick={() => selectBusiness(business)}
                className="card-hover rounded-xl border border-gray-700 bg-gray-800/50 p-6 text-left shadow-xl backdrop-blur-sm"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 text-lg font-bold text-white">
                    {business.name.charAt(0).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <h3 className="truncate font-semibold text-white">{business.name}</h3>
                    <p className="truncate text-xs text-gray-400">{business.industry}</p>
                  </div>
                </div>
                <p className="mt-4 line-clamp-3 text-sm text-gray-400">
                  {business.description}
                </p>
                <span className="mt-4 inline-flex items-center gap-1 text-sm text-blue-400">
                  Open
                  <svg
                    className="h-4 w-4"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    viewBox="0 0 24 24"
                  >
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                </span>
              </button>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
