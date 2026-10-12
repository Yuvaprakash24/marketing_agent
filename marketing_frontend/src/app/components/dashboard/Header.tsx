'use client'

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { User } from "@supabase/supabase-js";

import { createClient } from "@/utils/supabase/client";
import { ThemeToggle } from "../theme-toggle";

export default function Header({ isBusinessPage = false }: { isBusinessPage?: boolean }) {
  const [isAccountOpen, setIsAccountOpen] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [businessName, setBusinessName] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data }) => setUser(data.user ?? null));
    setBusinessName(localStorage.getItem("business_name"));
  }, []);

  const handleLogout = async () => {
    const supabase = createClient();
    localStorage.removeItem("business_id");
    localStorage.removeItem("business_name");
    await supabase.auth.signOut();
    router.push("/auth");
  };

  return (
    <header className="flex h-16 items-center border-b border-gray-800 bg-gray-900 px-6">
      <div className="flex-1">
        {!isBusinessPage && businessName && (
          <span className="text-sm font-medium text-gray-300">{businessName}</span>
        )}
      </div>

      <div className="flex items-center space-x-4">
        <Link href="/businesses" className="text-sm text-gray-300 hover:text-white">
          Switch business
        </Link>

        <div className="h-8 w-px bg-gray-700" />

        <ThemeToggle />

        <div className="h-8 w-px bg-gray-700" />

        <div className="relative">
          <button
            className="flex items-center text-gray-300 hover:text-white"
            onClick={() => setIsAccountOpen(!isAccountOpen)}
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600">
              <span className="font-medium text-white">
                {user?.email?.charAt(0).toUpperCase()}
              </span>
            </div>
          </button>

          {isAccountOpen && (
            <div className="absolute right-0 z-20 mt-2 w-56 rounded-md border border-gray-700 bg-gray-800 shadow-lg">
              <div className="border-b border-gray-700 px-4 py-2 text-sm text-gray-300">
                {user?.email}
              </div>
              <button
                onClick={handleLogout}
                className="block w-full px-4 py-2 text-left text-sm text-gray-300 hover:bg-gray-700"
              >
                Logout
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
