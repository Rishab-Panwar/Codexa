"use client";

import { Github, ArrowRight, Loader2, Search, Database, Code2, FolderOpen } from "lucide-react";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

import { indexRepository, listRepos, fetchIndexStatus, RepoInfo } from "@/lib/api";

const STAGE_LABELS: Record<string, string> = {
  queued: "Queued for indexing...",
  cloning: "Cloning repository...",
  parsing: "Parsing AST nodes...",
  embedding: "Generating vector embeddings...",
};

export default function Home() {
  const [isIndexing, setIsIndexing] = useState(false);
  const [repoUrl, setRepoUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [statusLabel, setStatusLabel] = useState("Connecting to backend...");
  const [existingRepos, setExistingRepos] = useState<RepoInfo[]>([]);
  const router = useRouter();

  useEffect(() => {
    listRepos()
      .then((data) => setExistingRepos(data.repos || []))
      .catch(() => {});
  }, []);

  const openExistingRepo = (repoId: string) => {
    localStorage.setItem("current_repo_id", repoId);
    router.push("/workspace");
  };

  const goToWorkspace = (repoId: string) => {
    localStorage.setItem("current_repo_id", repoId);
    const repoName = repoUrl.trim().replace(/\/$/, "").split("/").pop() || repoId;
    localStorage.setItem("current_repo_name", repoName);
    router.push("/workspace");
  };

  const handleIndex = async () => {
    if (!repoUrl.trim()) return;
    setError(null);
    setIsIndexing(true);
    setStatusLabel("Connecting to backend...");

    try {
      const result = await indexRepository(repoUrl);
      const repoId = result?.repository_id;
      if (!repoId) throw new Error("Backend did not return a repository id.");

      // Poll real indexing status until ready/failed (max ~5 min).
      const startedAt = Date.now();
      const poll = setInterval(async () => {
        try {
          const status = await fetchIndexStatus(repoId);

          if (status.status === "ready") {
            clearInterval(poll);
            if ((status.record_count ?? 0) === 0) {
              setError(
                "Indexed, but no code was found on the default branch (e.g. README-only repo).",
              );
              setIsIndexing(false);
              return;
            }
            setStatusLabel("Finalizing index...");
            goToWorkspace(repoId);
          } else if (status.status === "failed") {
            clearInterval(poll);
            setError(status.error || "Indexing failed on the backend.");
            setIsIndexing(false);
          } else {
            setStatusLabel(STAGE_LABELS[status.stage || "queued"] || "Indexing...");
          }
        } catch {
          /* transient network hiccup — keep polling */
        }

        if (Date.now() - startedAt > 5 * 60 * 1000) {
          clearInterval(poll);
          setError("Indexing is taking unusually long. Check back later from the repo list.");
          setIsIndexing(false);
        }
      }, 1500);
    } catch (err: any) {
      setError(err.message || "Failed to index repository. Make sure the backend is running.");
      setIsIndexing(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm space-y-8">
        <div className="space-y-2 text-center text-accent">
          <div className="bg-white/5 w-12 h-12 rounded-xl flex items-center justify-center mx-auto mb-4 border border-border">
            <Code2 className="w-6 h-6" />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">Codexa AI</h1>
          <p className="text-sm text-muted">Intelligent codebase indexing and assistance.</p>
        </div>

        {isIndexing ? (
          <div className="space-y-6 pt-4">
            <div className="flex items-center gap-3 text-sm font-medium animate-pulse">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>{statusLabel}</span>
            </div>
            <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
              <div className="h-full w-1/3 bg-accent rounded-full animate-pulse" />
            </div>
            <p className="text-[11px] text-muted/60 text-center">
              Large repositories can take a minute or two. You&apos;ll be taken to the workspace automatically when ready.
            </p>
            <div className="grid grid-cols-2 gap-2 text-[10px] uppercase tracking-widest text-muted">
              <div className="flex items-center gap-1.5">
                <Search className="w-3 h-3" /> Search Index
              </div>
              <div className="flex items-center gap-1.5">
                <Database className="w-3 h-3" /> Vector Store
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="relative group">
              <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none text-muted group-focus-within:text-accent transition-colors">
                <Github className="w-4 h-4" />
              </div>
              <input
                type="text"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                placeholder="https://github.com/user/repo"
                className="w-full bg-card border border-border rounded-md pl-10 pr-4 py-2.5 text-sm focus:outline-none focus:border-muted transition-colors placeholder:text-muted/30"
              />
            </div>

            {error && (
              <p className="text-[11px] text-red-500 font-medium">{error}</p>
            )}

            <button
              onClick={handleIndex}
              disabled={!repoUrl.trim()}
              className="w-full bg-accent text-background rounded-md py-2.5 text-sm font-medium flex items-center justify-center gap-2 hover:opacity-90 transition-opacity mt-4 shadow-lg shadow-white/5 disabled:opacity-50"
            >
              Index Repository
              <ArrowRight className="w-4 h-4" />
            </button>

            {existingRepos.length > 0 && (
              <>
                <div className="relative flex items-center py-2">
                  <div className="flex-grow border-t border-border" />
                  <span className="px-3 text-[10px] text-muted/50 uppercase tracking-widest">previously indexed</span>
                  <div className="flex-grow border-t border-border" />
                </div>

                <div className="space-y-1.5 max-h-40 overflow-y-auto">
                  {existingRepos.map((repo) => (
                    <button
                      key={repo.repo_id}
                      onClick={() => openExistingRepo(repo.repo_id)}
                      className="w-full flex items-center gap-2 px-3 py-2 text-[12px] mono text-muted hover:text-accent bg-white/[0.03] hover:bg-white/[0.06] rounded border border-white/5 transition-colors text-left"
                    >
                      <FolderOpen className="w-3.5 h-3.5 flex-shrink-0" />
                      <span className="truncate">{repo.name}</span>
                      <ArrowRight className="w-3 h-3 ml-auto flex-shrink-0 opacity-0 group-hover:opacity-100" />
                    </button>
                  ))}
                </div>
              </>
            )}

            <div className="relative flex items-center py-2">
              <div className="flex-grow border-t border-border" />
              <span className="px-3 text-[10px] text-muted/50 uppercase tracking-widest">or</span>
              <div className="flex-grow border-t border-border" />
            </div>

            <button
              onClick={() => {
                localStorage.removeItem("current_repo_id");
                localStorage.removeItem("current_repo_name");
                router.push("/workspace");
              }}
              className="w-full border border-border text-foreground/70 rounded-md py-2.5 text-sm font-medium flex items-center justify-center gap-2 hover:bg-white/5 transition-colors"
            >
              Open Coding Workspace
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}

        <div className="pt-8 border-t border-border text-center">
          <p className="text-[10px] uppercase tracking-widest text-muted/50">
            Professional AI Developer Environment
          </p>
        </div>
      </div>
    </div>
  );
}
