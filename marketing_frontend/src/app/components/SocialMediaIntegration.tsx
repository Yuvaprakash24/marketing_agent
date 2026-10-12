"use client";

import Link from "next/link";

import { SocialMediaAccount } from "../dashboard/actions";

interface SocialMediaIntegrationProps {
  socialAccounts: SocialMediaAccount[] | null;
  onConnect: (platform: string) => Promise<void>;
  showManageLink?: boolean;
  title?: string;
}

// Facebook also covers Instagram, which publishes through the connected page.
const PLATFORMS = [
  {
    key: "facebook",
    connectAs: "facebook",
    name: "Meta Business Suite",
    subtitle: "Facebook Page & Instagram Business",
    description:
      "Connect your Facebook Page and Instagram account to publish posts and images",
    fallbackInitials: "FB",
    iconWrapper: "bg-gradient-to-br from-blue-600 to-purple-600",
    iconClass: "text-white",
    path: "M12 2.04c-5.5 0-10 4.49-10 10.02 0 5 3.66 9.15 8.44 9.9v-7H7.9v-2.9h2.54V9.85c0-2.51 1.49-3.89 3.78-3.89 1.09 0 2.23.19 2.23.19v2.47h-1.26c-1.24 0-1.63.77-1.63 1.56v1.88h2.78l-.45 2.9h-2.33v7a10 10 0 0 0 8.44-9.9c0-5.53-4.5-10.02-10-10.02z",
  },
  {
    key: "linkedin",
    connectAs: "linkedin",
    name: "LinkedIn",
    subtitle: "Profile or Company Page",
    description: "Share professional content and engage with your business network",
    fallbackInitials: "LI",
    iconWrapper: "bg-blue-900/30",
    iconClass: "text-blue-400",
    path: "M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.32 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.79M6.88 8.56a1.68 1.68 0 0 0 1.68-1.68c0-.93-.75-1.69-1.68-1.69a1.69 1.69 0 0 0-1.69 1.69c0 .93.76 1.68 1.69 1.68m1.39 9.94v-8.37H5.5v8.37h2.77z",
  },
  {
    key: "twitter",
    connectAs: "twitter",
    name: "Twitter",
    subtitle: "Twitter Account",
    description: "Share real-time updates and engage with your audience",
    fallbackInitials: "TW",
    iconWrapper: "bg-blue-900/30",
    iconClass: "text-blue-400",
    path: "M22.46 6c-.77.35-1.6.58-2.46.69.88-.53 1.56-1.37 1.88-2.38-.83.5-1.75.85-2.72 1.05C18.37 4.5 17.26 4 16 4c-2.35 0-4.27 1.92-4.27 4.29 0 .34.04.67.11.98C8.28 9.09 5.11 7.38 3 4.79c-.37.63-.58 1.37-.58 2.15 0 1.49.75 2.81 1.91 3.56-.71 0-1.37-.2-1.95-.5v.03c0 2.08 1.48 3.82 3.44 4.21a4.22 4.22 0 0 1-1.93.07 4.28 4.28 0 0 0 4 2.98 8.521 8.521 0 0 1-5.33 1.84c-.34 0-.68-.02-1.02-.06C3.44 20.29 5.7 21 8.12 21 16 21 20.33 14.46 20.33 8.79c0-.19 0-.37-.01-.56.84-.6 1.56-1.36 2.14-2.23z",
  },
];

function getInitials(name: string) {
  return name
    .split(" ")
    .map((part) => part.charAt(0))
    .join("")
    .toUpperCase()
    .substring(0, 2);
}

export default function SocialMediaIntegration({
  socialAccounts,
  onConnect,
  showManageLink = true,
  title = "Social Media Integrations",
}: SocialMediaIntegrationProps) {
  if (!socialAccounts) {
    return <div className="h-40 animate-pulse rounded-xl bg-gray-800/30" />;
  }

  return (
    <div>
      <h2 className="mb-4 text-xl font-semibold text-white">{title}</h2>
      <div className="overflow-hidden rounded-xl border border-gray-700 bg-gray-800/50 shadow-xl backdrop-blur-sm">
        <div className="space-y-4 p-6">
          {PLATFORMS.map((platform) => {
            const account = socialAccounts.find((a) => a.platform === platform.key);
            const isConnected = Boolean(account?.is_active);

            return (
              <div
                key={platform.key}
                className="overflow-hidden rounded-xl bg-gray-800/70 transition-all hover:bg-gray-800/90"
              >
                <div className="flex items-center p-5">
                  <div
                    className={`mr-5 flex h-14 w-14 items-center justify-center rounded-xl ${platform.iconWrapper}`}
                  >
                    <svg className={`h-7 w-7 ${platform.iconClass}`} viewBox="0 0 24 24">
                      <path fill="currentColor" d={platform.path} />
                    </svg>
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center space-x-3">
                      <h3 className="text-lg font-semibold text-white">{platform.name}</h3>
                      {isConnected ? (
                        <span className="rounded-full border border-green-500/30 bg-green-500/20 px-2 py-1 text-xs text-green-400">
                          Connected
                        </span>
                      ) : (
                        <span className="rounded-full bg-gray-700 px-2 py-1 text-xs text-gray-400">
                          Not connected
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-sm text-gray-400">{platform.description}</p>
                  </div>
                </div>

                <div className="border-t border-gray-700/50 bg-gray-900/30 p-4">
                  {isConnected && account ? (
                    <>
                      <div className="flex items-center space-x-4">
                        {account.profile_picture_url ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img
                            src={account.profile_picture_url}
                            className="h-10 w-10 rounded-full"
                            alt={account.account_username}
                          />
                        ) : (
                          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-600 font-medium text-white">
                            {getInitials(account.account_username || platform.fallbackInitials)}
                          </div>
                        )}
                        <div>
                          <p className="font-medium text-white">{account.account_username}</p>
                          <p className="text-sm text-gray-400">{platform.subtitle}</p>
                        </div>
                      </div>
                      <button
                        onClick={() => onConnect(platform.connectAs)}
                        className="mt-4 text-sm text-blue-400 hover:text-blue-300"
                      >
                        Reconnect
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={() => onConnect(platform.connectAs)}
                      className="text-sm text-blue-400 hover:text-blue-300"
                    >
                      Connect
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {showManageLink && (
          <div className="border-t border-gray-700 bg-gray-900/30 px-6 py-4">
            <Link
              href="/dashboard/settings"
              className="flex items-center text-sm font-medium text-blue-400 transition-colors hover:text-blue-300"
            >
              <span>Manage all integrations</span>
              <svg
                className="ml-2 h-4 w-4"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                viewBox="0 0 24 24"
              >
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
