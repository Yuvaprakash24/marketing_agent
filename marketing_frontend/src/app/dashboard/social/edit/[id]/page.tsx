"use client";

import Image from "next/image";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  SocialMediaPost,
  generateAIImage,
  getSocialMediaPosts,
  updateSocialMediaPost,
} from "../../actions";
import { PlatformIcon } from "../../components/platformIcons";

const PLATFORM_LIMITS: Record<string, number> = {
  twitter: 280,
  instagram: 2200,
  facebook: 2000,
  linkedin: 3000,
};

export default function EditPostPage() {
  const router = useRouter();
  const params = useParams();
  const postId = parseInt(params.id as string);

  const [businessId, setBusinessId] = useState<number | null>(null);
  const [post, setPost] = useState<SocialMediaPost | null>(null);
  const [postText, setPostText] = useState("");
  const [hashtagInput, setHashtagInput] = useState("");
  const [imagePrompt, setImagePrompt] = useState("");
  const [images, setImages] = useState<string[]>([]);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [generatingImage, setGeneratingImage] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

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
        const posts = await getSocialMediaPosts(id);
        const found = posts.find((p) => p.id === postId);
        if (!found) {
          setError("That post could not be found.");
          return;
        }

        setPost(found);
        setPostText(found.post_text ?? "");
        setHashtagInput((found.hashtags ?? []).join(", "));
        setImagePrompt(found.image_prompt ?? "");
        setImages(found.post_images_urls ?? []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load the post");
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [postId]);

  const parsedHashtags = hashtagInput
    .split(",")
    .map((tag) => tag.trim().replace(/^#/, ""))
    .filter(Boolean);

  const handleSave = async () => {
    if (!businessId || !post) return;

    setSaving(true);
    setError(null);
    setSavedMessage(null);

    try {
      await updateSocialMediaPost(post.id, businessId, {
        post_text: postText,
        hashtags: parsedHashtags,
        image_prompt: imagePrompt,
        post_images_urls: images,
      });
      setSavedMessage("Changes saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save the post");
    } finally {
      setSaving(false);
    }
  };

  const handleGenerateImage = async () => {
    if (!imagePrompt.trim()) {
      setError("Describe the image you want before generating.");
      return;
    }

    setGeneratingImage(true);
    setError(null);

    try {
      const result = await generateAIImage(imagePrompt.trim());
      setImages((current) => [...current, result.image_url]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate the image");
    } finally {
      setGeneratingImage(false);
    }
  };

  const charLimit = post ? PLATFORM_LIMITS[post.post_platform] : undefined;
  const combinedLength =
    postText.length +
    (parsedHashtags.length ? parsedHashtags.join(" ").length + parsedHashtags.length + 2 : 0);
  const overLimit = charLimit !== undefined && combinedLength > charLimit;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-12 w-12 animate-spin rounded-full border-t-2 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (!post) {
    return (
      <div className="rounded-xl border border-gray-700 bg-gray-800/50 p-10 text-center">
        <p className="text-gray-300">{error ?? "Post not found."}</p>
        <Link
          href="/dashboard/social"
          className="mt-4 inline-block text-blue-400 hover:text-blue-300"
        >
          Back to Social Media
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/dashboard/social")}
            className="rounded-lg p-2 text-gray-400 transition-colors hover:bg-gray-800 hover:text-white"
            aria-label="Back"
          >
            <svg
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              viewBox="0 0 24 24"
            >
              <polyline points="15 18 9 12 15 6" />
            </svg>
          </button>
          <div>
            <h1 className="text-2xl font-bold text-white">Edit post</h1>
            <p className="flex items-center gap-1.5 text-sm text-gray-400 capitalize">
              <PlatformIcon platform={post.post_platform} />
              {post.post_platform} · {post.status}
            </p>
          </div>
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          className="rounded-lg bg-blue-600 px-4 py-2 font-medium text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save changes"}
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-700 bg-red-900/30 p-4 text-sm text-red-300">
          {error}
        </div>
      )}

      {savedMessage && (
        <div className="rounded-lg border border-green-700 bg-green-900/20 p-4 text-sm text-green-300">
          {savedMessage}
        </div>
      )}

      <div className="space-y-5 rounded-xl border border-gray-700 bg-gray-800/50 p-6 shadow-xl backdrop-blur-sm">
        <div>
          <div className="mb-2 flex items-center justify-between">
            <label className="text-sm font-medium text-gray-300">Post text</label>
            {charLimit !== undefined && (
              <span className={`text-xs ${overLimit ? "text-red-400" : "text-gray-500"}`}>
                {combinedLength} / {charLimit}
              </span>
            )}
          </div>
          <textarea
            value={postText}
            onChange={(e) => setPostText(e.target.value)}
            rows={8}
            className="w-full rounded-lg border border-gray-700 bg-gray-900 px-4 py-3 text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:outline-none"
          />
          {overLimit && (
            <p className="mt-1 text-xs text-red-400">
              This exceeds the {post.post_platform} limit and will be rejected on publish.
            </p>
          )}
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium text-gray-300">
            Hashtags
          </label>
          <input
            value={hashtagInput}
            onChange={(e) => setHashtagInput(e.target.value)}
            placeholder="marketing, automation, smallbusiness"
            className="w-full rounded-lg border border-gray-700 bg-gray-900 px-4 py-3 text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:outline-none"
          />
          <p className="mt-1 text-xs text-gray-500">
            Comma separated. The &ldquo;#&rdquo; is added automatically when publishing.
          </p>
          {parsedHashtags.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {parsedHashtags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-full bg-blue-900/30 px-2.5 py-1 text-xs text-blue-400"
                >
                  #{tag}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="space-y-5 rounded-xl border border-gray-700 bg-gray-800/50 p-6 shadow-xl backdrop-blur-sm">
        <h2 className="text-lg font-semibold text-white">Images</h2>

        <div>
          <label className="mb-2 block text-sm font-medium text-gray-300">
            Image prompt
          </label>
          <textarea
            value={imagePrompt}
            onChange={(e) => setImagePrompt(e.target.value)}
            rows={3}
            placeholder="A bright, minimal desk setup with a laptop showing a dashboard"
            className="w-full rounded-lg border border-gray-700 bg-gray-900 px-4 py-3 text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:outline-none"
          />
          <button
            onClick={handleGenerateImage}
            disabled={generatingImage}
            className="mt-3 flex items-center gap-2 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-purple-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {generatingImage && (
              <span className="h-4 w-4 animate-spin rounded-full border-t-2 border-b-2 border-white" />
            )}
            {generatingImage ? "Generating…" : "Generate image"}
          </button>
        </div>

        {images.length === 0 ? (
          <p className="text-sm text-gray-500">No images attached to this post yet.</p>
        ) : (
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
            {images.map((url, index) => (
              <div
                key={`${url}-${index}`}
                className="group relative aspect-square overflow-hidden rounded-lg border border-gray-700"
              >
                <Image
                  src={url}
                  alt={`Post image ${index + 1}`}
                  fill
                  sizes="(max-width: 768px) 50vw, 33vw"
                  className="object-cover"
                />
                <button
                  onClick={() => setImages((current) => current.filter((_, i) => i !== index))}
                  className="absolute top-2 right-2 rounded-full bg-black/60 p-1.5 text-white opacity-0 transition-opacity group-hover:opacity-100 hover:bg-red-600"
                  aria-label="Remove image"
                >
                  <svg
                    className="h-4 w-4"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
