"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { ArrowUp, Loader2, RefreshCcw, Sparkles } from "lucide-react";

import { AssessmentCard } from "@/components/chat/assessment-card";
import { InsightPanel } from "@/components/chat/insight-panel";
import { MessageBubble } from "@/components/chat/message-bubble";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { sendChat } from "@/lib/api";
import type { ChatMessage, Recommendation } from "@/lib/types";

const starterPrompts = [
  "Hiring a mid-level Java developer who works with stakeholders.",
  "I need tests for a graduate analyst role. Cognitive ability matters.",
  "What is the difference between OPQ and GSA?"
];

const initialMessages: ChatMessage[] = [
  {
    role: "assistant",
    content:
      "Tell me the role, seniority, core skills, and what signal matters most. I'll keep recommendations grounded in SHL Individual Test Solutions."
  }
];

export function ChatShell() {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [error, setError] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const latestRecommendations = useMemo<Recommendation[]>(() => {
    return [...messages].reverse().find((message) => message.recommendations?.length)?.recommendations ?? [];
  }, [messages]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, streamingText, loading]);

  async function submitMessage(content: string) {
    const trimmed = content.trim();
    if (!trimmed || loading) return;
    setError("");
    setDraft("");
    const nextMessages: ChatMessage[] = [...messages, { role: "user", content: trimmed }];
    setMessages(nextMessages);
    setLoading(true);
    setStreamingText("");

    try {
      const response = await sendChat(nextMessages);
      await streamReply(response.reply);
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: response.reply,
          recommendations: response.recommendations
        }
      ]);
    } catch {
      setError("The API is not reachable. Start the FastAPI backend on port 8000 or set NEXT_PUBLIC_API_BASE_URL.");
    } finally {
      setLoading(false);
      setStreamingText("");
    }
  }

  async function streamReply(text: string) {
    const chunkSize = Math.max(3, Math.ceil(text.length / 42));
    for (let index = 0; index < text.length; index += chunkSize) {
      setStreamingText(text.slice(0, index + chunkSize));
      await new Promise((resolve) => setTimeout(resolve, 16));
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitMessage(draft);
  }

  return (
    <main className="min-h-screen p-3 sm:p-5">
      <div className="mx-auto flex min-h-[calc(100vh-2.5rem)] max-w-7xl overflow-hidden rounded-lg border bg-background/82 shadow-panel backdrop-blur-xl">
        <section className="flex min-w-0 flex-1 flex-col">
          <header className="flex items-center justify-between gap-4 border-b px-4 py-3 sm:px-5">
            <div className="flex min-w-0 items-center gap-3">
              <div className="flex size-10 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground shadow-glow">
                <Sparkles className="size-5" aria-hidden="true" />
              </div>
              <div className="min-w-0">
                <h1 className="truncate text-base font-semibold sm:text-lg">SHL Assessment Recommender</h1>
                <p className="truncate text-xs text-muted-foreground sm:text-sm">
                  Stateless RAG agent for recruiter assessment discovery
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="success" className="hidden sm:inline-flex">
                Catalog grounded
              </Badge>
              <ThemeToggle />
              <Button
                aria-label="Reset conversation"
                title="Reset conversation"
                variant="outline"
                size="icon"
                onClick={() => {
                  setMessages(initialMessages);
                  setError("");
                  setDraft("");
                }}
              >
                <RefreshCcw />
              </Button>
            </div>
          </header>

          <div className="flex min-h-0 flex-1 flex-col">
            <div className="min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:px-6">
              <div className="mx-auto grid max-w-4xl gap-5">
                {messages.map((message, index) => (
                  <MessageBubble key={`${message.role}-${index}-${message.content}`} role={message.role} content={message.content} />
                ))}

                {streamingText && <MessageBubble role="assistant" content={streamingText} />}

                {loading && !streamingText && (
                  <div className="grid gap-3">
                    <Skeleton className="h-16 w-4/5 rounded-lg" />
                    <div className="grid gap-3 sm:grid-cols-3">
                      <Skeleton className="h-28 rounded-lg" />
                      <Skeleton className="h-28 rounded-lg" />
                      <Skeleton className="h-28 rounded-lg" />
                    </div>
                  </div>
                )}

                {latestRecommendations.length > 0 && (
                  <motion.section
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="grid gap-3"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <h2 className="text-sm font-semibold">Recommended Assessments</h2>
                      <Badge variant="outline">{latestRecommendations.length} results</Badge>
                    </div>
                    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                      {latestRecommendations.map((item, index) => (
                        <AssessmentCard key={`${item.url}-${index}`} item={item} index={index} />
                      ))}
                    </div>
                  </motion.section>
                )}
                <div ref={scrollRef} />
              </div>
            </div>

            <footer className="border-t bg-card/58 p-4 backdrop-blur-xl sm:p-5">
              <div className="mx-auto max-w-4xl space-y-3">
                <div className="flex gap-2 overflow-x-auto pb-1">
                  {starterPrompts.map((prompt) => (
                    <Button
                      key={prompt}
                      type="button"
                      variant="subtle"
                      size="sm"
                      className="shrink-0"
                      onClick={() => void submitMessage(prompt)}
                    >
                      {prompt}
                    </Button>
                  ))}
                </div>
                <form onSubmit={handleSubmit} className="grid gap-3">
                  <div className="relative">
                    <Textarea
                      value={draft}
                      onChange={(event) => setDraft(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" && !event.shiftKey) {
                          event.preventDefault();
                          void submitMessage(draft);
                        }
                      }}
                      placeholder="Describe the role, seniority, skills, constraints, or assessment names to compare..."
                      aria-label="Recruiter message"
                      disabled={loading}
                      className="pr-14"
                    />
                    <Button
                      aria-label="Send message"
                      title="Send message"
                      type="submit"
                      size="icon"
                      variant="accent"
                      disabled={loading || !draft.trim()}
                      className="absolute bottom-3 right-3"
                    >
                      {loading ? <Loader2 className="animate-spin" /> : <ArrowUp />}
                    </Button>
                  </div>
                  {error && <p className="text-sm text-destructive">{error}</p>}
                </form>
              </div>
            </footer>
          </div>
        </section>

        <InsightPanel recommendations={latestRecommendations} />
      </div>
    </main>
  );
}
