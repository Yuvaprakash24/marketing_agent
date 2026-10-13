"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";

import {
  SocialMediaPost,
  publishSocialMediaPost,
  updatePostFeedback,
} from "../actions";
import { PlatformIcon } from "./platformIcons";

interface PostCardProps {
  post: SocialMediaPost;
  onDelete: (postId: number) => void;
  onStatusChange: (postId: number, newStatus: string) => void;
  onPublished: (postId: number, postUrl: string) => void;
}

const FEEDBACK_CHOICES = ["Good", "Neutral", "Bad"];

const PLATFORM_ACCENTS: Record<string, string> = {
  twitter: "bg-blue-900/30 text-blue-400",
  facebook: "bg-indigo-900/30 text-indigo-400",
  instagram: "bg-purple-900/30 text-purple-400",
  linkedin: "bg-blue-900/30 text-blue-400",
};

function combinePostTextWithHashtags(postText: string, hashtags: string[]): string {
  if (!hashtags || hashtags.length === 0) {
    return postText;
  }

  const hashtagStr = hashtags.map((tag) => `#${tag.replace(/^#/, "")}`).join(" ");

  if (postText && !/[\s\n]$/.test(postText)) {
    return `${postText}\n\n${hashtagStr}`;
  }
  return `${postText}${hashtagStr}`;
}

export default function PostCard({
  post,
  onDelete,
  onStatusChange,
  onPublished,
}: PostCardProps) {
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const [isExpanded, setIsExpanded] = useState(false);
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [publishError, setPublishError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const images = post.post_images_urls ?? [];
  const hasImages = images.length > 0;
  const fullText = combinePostTextWithHashtags(post.post_text, post.hashtags);

  const navigateImages = (direction: "prev" | "next") => {
    if (!hasImages) return;
    setCurrentImageIndex((prev) =>
      direction === "prev"
        ? prev === 0
          ? images.length - 1
          : prev - 1
        : prev === images.length - 1
          ? 0
          : prev + 1
    );
  };

  const handleFeedbackSubmit = async (feedback: string) => {
    try {
      const businessId = localStorage.getItem("business_id");
      if (!businessId) throw new Error("Business ID not found");

      await updatePostFeedback(post.id, parseInt(businessId), feedback);
      setShowFeedbackModal(false);
    } catch (error) {
      console.error("Failed to submit feedback:", error);
    }
  };

  const handlePublish = async () => {
    setIsPublishing(true);
    setPublishError(null);

    try {
      const businessId = localStorage.getItem("business_id");
      if (!businessId) throw new Error("Business ID not found");

      const result = await publishSocialMediaPost(post.id, parseInt(businessId));
      onPublished(post.id, result.post_url);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to publish this post";
      setPublishError(message);
      onStatusChange(post.id, "Failed");
    } finally {
      setIsPublishing(false);
    }
  };

  const handleDownloadImage = (imageUrl: string) => {
    const link = document.createElement("a");
    link.href = imageUrl;
    link.download = `social-post-${post.id}-${Date.now()}.jpg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="card-hover flex min-h-[280px] flex-col overflow-hidden rounded-xl border border-gray-700 bg-gray-800/50 shadow-xl backdrop-blur-sm">
      {hasImages && (
        <div className="relative h-48 w-full shrink-0 overflow-hidden">
          <Image
            src={images[currentImageIndex]}
            alt={`Post image ${currentImageIndex + 1}`}
            fill
            sizes="(max-width: 768px) 100vw, 33vw"
            className="cursor-pointer object-cover"
            onClick={() => setIsFullscreen(true)}
          />

          {images.length > 1 && (
            <>
              <button
                onClick={() => navigateImages("prev")}
                className="absolute top-1/2 left-2 -translate-y-1/2 rounded-full bg-black/50 p-1 text-white transition-colors hover:bg-black/70"
                aria-label="Previous image"
              >
                <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path
                    fillRule="evenodd"
                    d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
              </button>
              <button
                onClick={() => navigateImages("next")}
                className="absolute top-1/2 right-2 -translate-y-1/2 rounded-full bg-black/50 p-1 text-white transition-colors hover:bg-black/70"
                aria-label="Next image"
              >
                <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path
                    fillRule="evenodd"
                    d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
              </button>
              <div className="absolute bottom-2 left-0 right-0 flex justify-center gap-1">
                {images.map((_, index) => (
                  <button
                    key={index}
                    className={`h-2 w-2 rounded-full ${
                      index === currentImageIndex ? "bg-white" : "bg-white/50"
                    }`}
                    aria-label={`Go to image ${index + 1}`}
                    onClick={() => setCurrentImageIndex(index)}
                  />
                ))}
              </div>
            </>
          )}

          <div className="absolute top-2 right-2 flex gap-1">
            <button
              onClick={() => handleDownloadImage(images[currentImageIndex])}
              className="rounded-full bg-black/50 p-1.5 text-white transition-colors hover:bg-black/70"
              aria-label="Download image"
            >
              <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path
                  fillRule="evenodd"
                  d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          </div>
        </div>
      )}

      <div className="flex flex-1 flex-col overflow-hidden p-5">
        <div className="mb-4 flex items-start justify-between">
          <div className="flex items-center">
            <div
              className={`mr-3 flex h-10 w-10 items-center justify-center rounded-full ${
                PLATFORM_ACCENTS[post.post_platform] ?? "bg-blue-900/30 text-blue-400"
              }`}
            >
              <PlatformIcon platform={post.post_platform} className="h-5 w-5" />
            </div>
            <div>
              <h3 className="font-medium text-white capitalize">{post.post_platform}</h3>
              <p className="text-xs text-gray-400">
                {new Date(post.created_at).toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </p>
            </div>
          </div>

          <span
            className={`rounded-full px-2 py-1 text-xs ${
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

        {post.posted_link && (
          <a
            href={post.posted_link}
            target="_blank"
            rel="noopener noreferrer"
            className="mb-3 flex items-center gap-1 text-sm text-blue-400 hover:text-blue-300"
          >
            <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
              <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
            </svg>
            View live post
          </a>
        )}

        <div className="mb-3 flex-1 overflow-hidden text-sm text-gray-300">
          <p
            className={`whitespace-pre-wrap ${
              isExpanded ? "max-h-56 overflow-y-auto pr-2" : "line-clamp-8"
            } ${fullText.trim() ? "" : "italic text-gray-500"}`}
          >
            {fullText.trim()
              ? fullText
              : "No copy was generated for this draft. Edit it to add text."}
          </p>
          {fullText.length > 180 && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="mt-1 text-xs text-blue-400 hover:text-blue-300"
            >
              {isExpanded ? "Show less" : "Show more"}
            </button>
          )}
        </div>

        {post.source && (
          <div className="mb-3 text-xs text-gray-400">
            <span className="font-medium">Source:</span>{" "}
            {post.source_url ? (
              <a
                href={post.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-400 hover:underline"
              >
                {post.source}
              </a>
            ) : (
              post.source
            )}
          </div>
        )}

        {publishError && (
          <div className="mb-3 rounded-md border border-red-700 bg-red-900/30 p-2 text-xs text-red-300">
            {publishError}
          </div>
        )}

        <div className="mt-auto flex items-center justify-between border-t border-gray-700 pt-4">
          <div className="flex space-x-3">
            <Link
              href={`/dashboard/social/edit/${post.id}`}
              className="text-gray-400 transition-colors hover:text-white"
              aria-label="Edit post"
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
            </Link>
            <button
              onClick={() => setShowFeedbackModal(true)}
              className="text-gray-400 transition-colors hover:text-white"
              aria-label="Provide feedback"
            >
              <svg
                className="h-5 w-5"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                viewBox="0 0 24 24"
              >
                <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
              </svg>
            </button>
            <button
              onClick={() => onDelete(post.id)}
              className="text-gray-400 transition-colors hover:text-red-400"
              aria-label="Delete post"
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

          {post.status !== "Published" && (
            <button
              onClick={handlePublish}
              disabled={isPublishing}
              className="flex items-center gap-1 rounded-full bg-green-600 px-3 py-1.5 text-xs text-white transition-colors hover:bg-green-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isPublishing ? (
                <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24">
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
              ) : (
                <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
              {isPublishing ? "Publishing..." : "Publish now"}
            </button>
          )}
        </div>
      </div>

      {showFeedbackModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="animate-scale-in w-full max-w-md overflow-hidden rounded-xl border border-gray-700 bg-gray-800 shadow-2xl">
            <div className="flex items-center justify-between border-b border-gray-700 p-6">
              <h3 className="text-xl font-bold text-white">Rate this post</h3>
              <button
                onClick={() => setShowFeedbackModal(false)}
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
              <p className="text-sm text-gray-400">
                Feedback is stored on the post so you can track which generations work.
              </p>
              <div className="grid grid-cols-3 gap-3">
                {FEEDBACK_CHOICES.map((choice) => (
                  <button
                    key={choice}
                    onClick={() => handleFeedbackSubmit(choice)}
                    className={`rounded-lg border border-gray-700 px-4 py-3 text-sm text-gray-300 transition-colors hover:bg-gray-700 ${
                      choice === "Good"
                        ? "hover:border-green-500 hover:text-green-400"
                        : choice === "Bad"
                          ? "hover:border-red-500 hover:text-red-400"
                          : "hover:border-yellow-500 hover:text-yellow-400"
                    } ${post.feedback === choice ? "bg-gray-700 text-white" : ""}`}
                  >
                    {choice}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {isFullscreen && hasImages && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90">
          <div className="relative h-full w-full">
            <div className="absolute top-0 right-0 left-0 z-10 flex items-center justify-between bg-gradient-to-b from-black/80 to-transparent p-4">
              <div className="text-sm text-white">
                Image {currentImageIndex + 1} of {images.length}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => handleDownloadImage(images[currentImageIndex])}
                  className="rounded-full bg-gray-800/80 p-2 text-white transition-colors hover:bg-gray-700"
                  aria-label="Download image"
                >
                  <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path
                      fillRule="evenodd"
                      d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z"
                      clipRule="evenodd"
                    />
                  </svg>
                </button>
                <button
                  onClick={() => setIsFullscreen(false)}
                  className="rounded-full bg-gray-800/80 p-2 text-white transition-colors hover:bg-gray-700"
                  aria-label="Close fullscreen"
                >
                  <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path
                      fillRule="evenodd"
                      d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                      clipRule="evenodd"
                    />
                  </svg>
                </button>
              </div>
            </div>

            <Image
              src={images[currentImageIndex]}
              alt={`Post image ${currentImageIndex + 1}`}
              fill
              sizes="100vw"
              className="object-contain"
              priority
            />
          </div>
        </div>
      )}
    </div>
  );
}
